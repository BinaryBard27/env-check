import os
import re
import json
import hmac
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set

from env_check.severity import Severity
from env_check.validators.type_validator import TypeValidator
from env_check.validators.non_empty_validator import NonEmptyValidator
from env_check.validator import ValidationResult
from env_check.cli import is_weak_secret, load_env_file

try:
    from rich.table import Table
    from rich.console import Console
    from rich import box
    console = Console()
    RICH = True
except Exception:
    RICH = False

SENSITIVE_NAME_PATTERNS = re.compile(
    r"(secret|password|passwd|api_key|access_key|private_key|auth_token|bearer_token|token|credential|private)",
    re.IGNORECASE
)


def is_sensitive_variable(var_name: str, rules: Optional[Dict[str, Any]] = None) -> bool:
    """Determine whether a variable contains sensitive data / secrets."""
    if rules and isinstance(rules, dict) and rules.get("secret", False):
        return True
    if SENSITIVE_NAME_PATTERNS.search(var_name):
        return True
    return False


def mask_secret_value(value: Optional[str]) -> Optional[str]:
    """Return a masked representation of a secret value, never revealing plaintext."""
    if value is None:
        return None
    return "[MASKED]"


def mask_sensitive_name(name: str) -> str:
    """Mask characters of a sensitive variable name (e.g. API_KEY -> A*****Y)."""
    if len(name) <= 3:
        return "***"
    return name[:1] + "*" * (len(name) - 2) + name[-1:]


def safe_compare_secrets(val1: Optional[str], val2: Optional[str]) -> bool:
    """Compare two secret strings in constant time to prevent timing attacks."""
    if val1 is None or val2 is None:
        return val1 == val2
    return hmac.compare_digest(val1.encode("utf-8"), val2.encode("utf-8"))


def extract_environment_names(file_path: str) -> Set[str]:
    """Extract environment identifiers from a file path."""
    p = Path(file_path)
    names = {p.name.lower(), p.as_posix().lower()}
    
    stem = p.stem.lower()
    suffix = p.suffix.lower()
    
    if suffix.startswith("."):
        names.add(suffix[1:])
    
    parts = re.split(r"[-._]", p.name.lower())
    for part in parts:
        if part and part != "env":
            names.add(part)
            
    return names


class DriftIssue:
    """Represents a single detected drift issue."""

    def __init__(
        self,
        variable: str,
        issue_type: str,
        severity: Severity,
        message: str,
        environment: str,
        base_value: Optional[str] = None,
        compare_value: Optional[str] = None,
        is_secret: bool = False,
    ):
        self.variable = variable
        self.issue_type = issue_type
        self.severity = severity
        self.message = message
        self.environment = environment
        self.is_secret = is_secret
        self.base_value = mask_secret_value(base_value) if is_secret else base_value
        self.compare_value = mask_secret_value(compare_value) if is_secret else compare_value

    def to_dict(self, mask_names: bool = False) -> Dict[str, Any]:
        var_display = mask_sensitive_name(self.variable) if (mask_names and self.is_secret) else self.variable
        return {
            "variable": var_display,
            "type": self.issue_type,
            "severity": self.severity.name,
            "message": self.message,
            "environment": self.environment,
            "is_secret": self.is_secret,
            "base_value": self.base_value,
            "compare_value": self.compare_value,
        }


class EnvironmentComparison:
    """Container for comparison results between base and a target environment."""

    def __init__(self, environment: str, issues: Optional[List[DriftIssue]] = None):
        self.environment = environment
        self.issues: List[DriftIssue] = issues or []

    @property
    def has_drift(self) -> bool:
        return len(self.issues) > 0

    def to_dict(self, mask_names: bool = False) -> Dict[str, Any]:
        return {
            "environment": self.environment,
            "status": "drift_detected" if self.has_drift else "in_sync",
            "issues_count": len(self.issues),
            "issues": [issue.to_dict(mask_names=mask_names) for issue in self.issues],
        }


class DriftReport:
    """Overall drift report across all compared environments."""

    def __init__(
        self,
        base: str,
        comparisons: List[EnvironmentComparison],
        schema_path: Optional[str] = None,
    ):
        self.base = base
        self.comparisons = comparisons
        self.schema_path = schema_path

    @property
    def all_issues(self) -> List[DriftIssue]:
        issues = []
        for comp in self.comparisons:
            issues.extend(comp.issues)
        return issues

    @property
    def max_severity(self) -> Severity:
        issues = self.all_issues
        if not issues:
            return Severity.INFO
        return max(issue.severity for issue in issues)

    def compute_exit_code(
        self,
        strict: bool = False,
        fail_on: Optional[str] = None,
    ) -> int:
        """
        Compute CLI exit code:
        - 0: success / in sync / below failure threshold
        - 1: drift issues detected meeting or exceeding failure threshold
        - 3: weak or placeholder secret detected
        """
        issues = self.all_issues
        if not issues:
            return 0

        # Check for weak secrets in any environment (exit code 3)
        if any(issue.issue_type == "weak_secret" for issue in issues):
            return 3

        # Determine threshold
        if fail_on:
            threshold = Severity.from_name(fail_on)
        elif strict:
            threshold = Severity.WARN
        else:
            threshold = Severity.ERROR

        if self.max_severity >= threshold:
            return 1

        return 0

    def to_dict(self, mask_names: bool = False) -> Dict[str, Any]:
        issues = self.all_issues
        severity_counts = {
            "critical": sum(1 for i in issues if i.severity == Severity.CRITICAL),
            "error": sum(1 for i in issues if i.severity == Severity.ERROR),
            "warning": sum(1 for i in issues if i.severity == Severity.WARN),
            "info": sum(1 for i in issues if i.severity == Severity.INFO),
        }
        return {
            "base": self.base,
            "schema": self.schema_path,
            "environments": [c.to_dict(mask_names=mask_names) for c in self.comparisons],
            "summary": {
                "total_environments": len(self.comparisons),
                "total_issues": len(issues),
                "has_drift": len(issues) > 0,
                "max_severity": self.max_severity.name,
                "severity_counts": severity_counts,
                "exit_code": self.compute_exit_code(strict=False, fail_on=None),
            },
        }


class DriftDetector:
    """Core drift detection engine with schema validation, consistency rules, and secret masking."""

    def __init__(
        self,
        schema: Optional[Dict[str, Any]] = None,
        schema_path: Optional[str] = None,
        strict: bool = False,
        fail_on: Optional[str] = None,
    ):
        self.schema = schema or {}
        self.schema_path = schema_path
        self.strict = strict
        self.fail_on = fail_on
        self.type_validator = TypeValidator()
        self.non_empty_validator = NonEmptyValidator()

    def _infer_type(self, value: str) -> str:
        """Infer basic type of a value when no schema type is provided."""
        v = value.strip()
        if v.lower() in ("true", "false", "yes", "no"):
            return "bool"
        if re.match(r"^[+-]?\d+$", v):
            return "int"
        if re.match(r"^[+-]?\d+\.\d+$", v):
            return "float"
        return "str"

    def compare_environments(
        self,
        base_name: str,
        base_env: Dict[str, str],
        compare_envs: Dict[str, Dict[str, str]],
    ) -> DriftReport:
        """Compare base environment mapping against multiple target environments."""
        comparisons: List[EnvironmentComparison] = []

        # Check base itself for weak secrets
        base_issues: List[DriftIssue] = []
        for b_key, b_val in base_env.items():
            b_rules = self.schema.get(b_key, {})
            if isinstance(b_rules, dict) and is_sensitive_variable(b_key, b_rules):
                if is_weak_secret(b_val):
                    base_issues.append(
                        DriftIssue(
                            variable=b_key,
                            issue_type="weak_secret",
                            severity=Severity.CRITICAL,
                            message=f"Secret variable '{b_key}' has a weak or placeholder value in base '{base_name}'",
                            environment=base_name,
                            base_value=b_val,
                            compare_value=None,
                            is_secret=True,
                        )
                    )

        for comp_name, comp_env in compare_envs.items():
            issues: List[DriftIssue] = list(base_issues)
            env_tags = extract_environment_names(comp_name)

            # Combined set of keys
            all_keys = set(base_env.keys()) | set(comp_env.keys()) | set(self.schema.keys())

            for key in sorted(all_keys):
                rules = self.schema.get(key)
                if rules is not None and not isinstance(rules, dict):
                    if isinstance(rules, list):
                        rules = {"enum": rules}
                    else:
                        rules = {}
                else:
                    rules = dict(rules) if rules else {}

                is_sec = is_sensitive_variable(key, rules)
                base_has_key = key in base_env
                comp_has_key = key in comp_env
                base_val = base_env.get(key)
                comp_val = comp_env.get(key)

                # Check 1: Allowed environments rule (e.g. allowed_in: ["prod"])
                allowed_in = rules.get("allowed_in") or rules.get("allowed_only_in")
                if allowed_in:
                    allowed_set = {str(x).lower() for x in (allowed_in if isinstance(allowed_in, list) else [allowed_in])}
                    if comp_has_key and not (env_tags & allowed_set):
                        issues.append(
                            DriftIssue(
                                variable=key,
                                issue_type="rule_violation",
                                severity=Severity.ERROR,
                                message=f"Variable '{key}' is allowed only in {sorted(allowed_set)}, but present in '{comp_name}'",
                                environment=comp_name,
                                base_value=base_val,
                                compare_value=comp_val,
                                is_secret=is_sec,
                            )
                        )

                # Check 2: Required in environments (required_in: ["all"] or ["prod", ...])
                required_in = rules.get("required_in")
                is_explicitly_required = rules.get("required", False)
                if required_in:
                    req_set = {str(x).lower() for x in (required_in if isinstance(required_in, list) else [required_in])}
                    if "all" in req_set or (env_tags & req_set):
                        is_explicitly_required = True

                # Check 3: Missing variables in compare environment
                if not comp_has_key:
                    if is_explicitly_required:
                        issues.append(
                            DriftIssue(
                                variable=key,
                                issue_type="missing_variable",
                                severity=Severity.CRITICAL,
                                message=f"Required variable '{key}' is missing in '{comp_name}'",
                                environment=comp_name,
                                base_value=base_val,
                                compare_value=None,
                                is_secret=is_sec,
                            )
                        )
                    elif base_has_key:
                        # Present in base, missing in compare
                        base_sev = Severity.from_name(rules.get("severity")) if "severity" in rules else Severity.ERROR
                        issues.append(
                            DriftIssue(
                                variable=key,
                                issue_type="missing_variable",
                                severity=base_sev,
                                message=f"Variable '{key}' present in base ('{base_name}') but missing in '{comp_name}'",
                                environment=comp_name,
                                base_value=base_val,
                                compare_value=None,
                                is_secret=is_sec,
                            )
                        )
                    continue

                # Check 4: Unexpected additional variables (present in compare, not in base or schema)
                if not base_has_key:
                    if key not in self.schema:
                        issues.append(
                            DriftIssue(
                                variable=key,
                                issue_type="unexpected_variable",
                                severity=Severity.WARN,
                                message=f"Unexpected variable '{key}' present in '{comp_name}' but not in base ('{base_name}')",
                                environment=comp_name,
                                base_value=None,
                                compare_value=comp_val,
                                is_secret=is_sec,
                            )
                        )
                    elif not is_explicitly_required and not allowed_in:
                        # In schema but not base
                        issues.append(
                            DriftIssue(
                                variable=key,
                                issue_type="unexpected_variable",
                                severity=Severity.INFO,
                                message=f"Variable '{key}' present in '{comp_name}' (defined in schema, but not set in base)",
                                environment=comp_name,
                                base_value=None,
                                compare_value=comp_val,
                                is_secret=is_sec,
                            )
                        )

                # Check 5: Secret security & weak placeholder checks
                if is_sec and comp_val is not None:
                    if is_weak_secret(comp_val):
                        issues.append(
                            DriftIssue(
                                variable=key,
                                issue_type="weak_secret",
                                severity=Severity.CRITICAL,
                                message=f"Secret variable '{key}' has a weak or placeholder value in '{comp_name}'",
                                environment=comp_name,
                                base_value=base_val,
                                compare_value=comp_val,
                                is_secret=True,
                            )
                        )

                # Check 6: Empty values where non-empty is required
                non_empty_required = rules.get("non_empty", False) or is_explicitly_required
                if non_empty_required and (comp_val is None or comp_val.strip() == ""):
                    issues.append(
                        DriftIssue(
                            variable=key,
                            issue_type="empty_value",
                            severity=Severity.CRITICAL if is_explicitly_required else Severity.ERROR,
                            message=f"Variable '{key}' is empty in '{comp_name}' (non-empty value required)",
                            environment=comp_name,
                            base_value=base_val,
                            compare_value=comp_val,
                            is_secret=is_sec,
                        )
                    )
                elif base_has_key and base_val and base_val.strip() != "" and (comp_val is None or comp_val.strip() == ""):
                    # Base is non-empty, compare is empty
                    issues.append(
                        DriftIssue(
                            variable=key,
                            issue_type="empty_value",
                            severity=Severity.WARN,
                            message=f"Variable '{key}' is empty in '{comp_name}' but has non-empty value in base",
                            environment=comp_name,
                            base_value=base_val,
                            compare_value=comp_val,
                            is_secret=is_sec,
                        )
                    )

                # Check 7: Type consistency
                expected_type = rules.get("type")
                if expected_type:
                    ok, detail = self.type_validator.validate(comp_val, expected_type)
                    if not ok:
                        type_err_desc = "type validation failed" if is_sec else detail
                        issues.append(
                            DriftIssue(
                                variable=key,
                                issue_type="type_mismatch",
                                severity=Severity.ERROR,
                                message=f"Type mismatch for '{key}' in '{comp_name}': expected {expected_type} ({type_err_desc})",
                                environment=comp_name,
                                base_value=base_val,
                                compare_value=comp_val,
                                is_secret=is_sec,
                            )
                        )
                elif base_has_key and base_val is not None and comp_val is not None:
                    # Schema-less type consistency check based on inferred base type
                    base_inferred = self._infer_type(base_val)
                    comp_inferred = self._infer_type(comp_val)
                    if base_inferred in ("int", "bool", "float") and comp_inferred != base_inferred:
                        ok, _ = self.type_validator.validate(comp_val, base_inferred)
                        if not ok:
                            issues.append(
                                DriftIssue(
                                    variable=key,
                                    issue_type="type_mismatch",
                                    severity=Severity.ERROR,
                                    message=f"Inconsistent type for '{key}': base is {base_inferred}, '{comp_name}' value cannot be parsed as {base_inferred}",
                                    environment=comp_name,
                                    base_value=base_val,
                                    compare_value=comp_val,
                                    is_secret=is_sec,
                                )
                            )

                # Check 8: Value consistency / drift
                if base_has_key and base_val is not None and comp_val is not None:
                    if is_sec:
                        values_equal = safe_compare_secrets(base_val, comp_val)
                    else:
                        values_equal = (base_val == comp_val)

                    must_have_same_value = rules.get("same_value", False)
                    allow_diff = rules.get("allow_different_values", False) or (rules.get("same_value") is False)

                    if not values_equal:
                        if must_have_same_value:
                            issues.append(
                                DriftIssue(
                                    variable=key,
                                    issue_type="value_mismatch",
                                    severity=Severity.ERROR,
                                    message=f"Variable '{key}' must have identical value across environments ('same_value: true' violated)",
                                    environment=comp_name,
                                    base_value=base_val,
                                    compare_value=comp_val,
                                    is_secret=is_sec,
                                )
                            )
                        elif not allow_diff:
                            val_msg = (
                                f"Secret value differs for '{key}' between base and '{comp_name}'"
                                if is_sec
                                else f"Value for '{key}' differs: base='{base_val}', '{comp_name}'='{comp_val}'"
                            )
                            issues.append(
                                DriftIssue(
                                    variable=key,
                                    issue_type="value_mismatch",
                                    severity=Severity.WARN,
                                    message=val_msg,
                                    environment=comp_name,
                                    base_value=base_val,
                                    compare_value=comp_val,
                                    is_secret=is_sec,
                                )
                            )

            comparisons.append(EnvironmentComparison(comp_name, issues))

        return DriftReport(base_name, comparisons, self.schema_path)

    def compare_files(self, base_file: str, compare_files: List[str]) -> DriftReport:
        """Load and compare base environment file against comparison files."""
        if not os.path.exists(base_file):
            raise FileNotFoundError(f"Base environment file not found: {base_file}")

        base_env = load_env_file(base_file)
        compare_envs = {}

        for c_file in compare_files:
            if not os.path.exists(c_file):
                raise FileNotFoundError(f"Comparison environment file not found: {c_file}")
            compare_envs[c_file] = load_env_file(c_file)

        return self.compare_environments(base_file, base_env, compare_envs)


def print_drift_table(report: DriftReport, mask_names: bool = False) -> None:
    """Render human-readable drift report table to console."""
    all_issues = report.all_issues

    if RICH:
        table = Table(
            title=f"Environment Drift Report (Base: {report.base})",
            box=box.MINIMAL_DOUBLE_HEAD,
            show_lines=False
        )
        table.add_column("ENVIRONMENT", style="cyan")
        table.add_column("VARIABLE", style="bold")
        table.add_column("ISSUE TYPE")
        table.add_column("SEVERITY")
        table.add_column("DETAIL")

        if not all_issues:
            console.print(f"[green][OK] All {len(report.comparisons)} environment(s) in sync with base '{report.base}'. No drift detected.[/green]")
            return

        for issue in all_issues:
            var_name = mask_sensitive_name(issue.variable) if (mask_names and issue.is_secret) else issue.variable
            sev_style = {
                Severity.CRITICAL: "[bold red]CRITICAL[/bold red]",
                Severity.ERROR: "[red]ERROR[/red]",
                Severity.WARN: "[yellow]WARN[/yellow]",
                Severity.INFO: "[blue]INFO[/blue]",
            }.get(issue.severity, issue.severity.name)

            table.add_row(
                issue.environment,
                var_name,
                issue.issue_type,
                sev_style,
                issue.message
            )
        console.print(table)
    else:
        if not all_issues:
            print(f"[OK] All {len(report.comparisons)} environment(s) in sync with base '{report.base}'. No drift detected.")
            return

        print(f"Drift Detection Report (Base: {report.base})")
        print("-" * 80)
        print(f"{'ENVIRONMENT':<25} | {'VARIABLE':<20} | {'TYPE':<18} | {'SEVERITY':<8} | DETAIL")
        print("-" * 80)
        for issue in all_issues:
            var_name = mask_sensitive_name(issue.variable) if (mask_names and issue.is_secret) else issue.variable
            print(f"{issue.environment:<25} | {var_name:<20} | {issue.issue_type:<18} | {issue.severity.name:<8} | {issue.message}")
        print("-" * 80)

    counts = report.to_dict()["summary"]["severity_counts"]
    print(f"\nSummary: {len(report.comparisons)} environment(s) checked, {len(all_issues)} drift issue(s) detected "
          f"({counts['critical']} critical, {counts['error']} error, {counts['warning']} warning, {counts['info']} info).")
