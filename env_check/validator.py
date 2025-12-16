from typing import Dict, Any, List
import os
from .severity import Severity

# Import validator classes dynamically
from .validators.base import BaseValidator
from .validators.type_validator import TypeValidator
from .validators.regex_validator import RegexValidator
from .validators.enum_validator import EnumValidator
from .validators.range_validator import RangeValidator
from .validators.file_exists_validator import FileExistsValidator
from .validators.non_empty_validator import NonEmptyValidator

DEFAULT_SEVERITY = Severity.ERROR

class ValidationResult:
    def __init__(self, variable: str, ok: bool, severity: Severity, detail: str):
        self.variable = variable
        self.ok = ok
        self.severity = severity
        self.detail = detail

    def to_dict(self):
        return {
            "variable": self.variable,
            "ok": self.ok,
            "severity": self.severity.name,
            "detail": self.detail,
        }

class ValidatorEngine:
    """
    Runs configured validators on environment variables.
    config: dict mapping variable -> rule dict
    env: mapping to check (defaults to os.environ)
    """
    def __init__(self, config: Dict[str, Any], env: Dict[str, str] = None):
        self.config = config or {}
        self.env = env if env is not None else os.environ.copy()
        self.validators_map = {
            "type": TypeValidator(),
            "regex": RegexValidator(),
            "enum": EnumValidator(),
            "range": RangeValidator(),
            "file_exists": FileExistsValidator(),
            "non_empty": NonEmptyValidator(),
        }

    def run(self) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for var, rules in self.config.items():
            # Normalize rules
            if rules is None:
                rules = {}

            # Allow shorthand enum: VAR: [a, b, c]
            if isinstance(rules, list):
                rules = {"enum": rules}

            # Normalize shorthand min/max into range
            if "min" in rules or "max" in rules:
                rules["range"] = {
                    k: rules[k] for k in ("min", "max") if k in rules
                }

            # Hard fail on invalid rule types
            if not isinstance(rules, dict):
                results.append(
                    ValidationResult(
                        var,
                        False,
                        Severity.ERROR,
                        f"Invalid rule format (expected object, got {type(rules).__name__})"
                    )
                )
                continue

            warnings = []

            allowed_keys = {
                "required", "type", "regex", "enum",
                "range", "file_exists", "non_empty", "severity",
                "min", "max"
            }

            unknown = set(rules.keys()) - allowed_keys
            if unknown:
                warnings.append(f"Unknown rule keys: {sorted(unknown)}")
            # Base severity for non-required failures
            severity = Severity.from_name(rules.get("severity")) if isinstance(rules, dict) else DEFAULT_SEVERITY

            # check presence
            val = self.env.get(var)
            if rules.get("required", False) and (val is None or val == ""):
                detail = "Required variable missing"
                # Missing required vars are ALWAYS CRITICAL
                results.append(
                    ValidationResult(var, False, Severity.CRITICAL, detail)
                )
                continue

            # If not present and not required, this is OK (but might have default)
            if val is None:
                # no further checks
                results.append(ValidationResult(var, True, Severity.INFO, "Not set (optional)"))
                continue

            # Run validators in deterministic order
            invalid_reasons = []
            for key, validator in self.validators_map.items():
                if key in rules:
                    ok, msg = validator.validate(val, rules.get(key))
                    if not ok:
                        invalid_reasons.append(f"{key}: {msg}")

            detail = "; ".join(invalid_reasons + warnings) if invalid_reasons else (
                "; ".join(warnings) if warnings else f"Value: {val}"
            )
            
            final_severity = severity
            final_ok = True

            if invalid_reasons:
                final_ok = False
            elif warnings:
                final_ok = False
                final_severity = Severity.WARN # Demote to WARN if only unknown keys
            else:
                final_severity = Severity.INFO

            results.append(ValidationResult(var, final_ok, final_severity, detail))
        return results

    def summarize_exit_code(self, results: List[ValidationResult]) -> int:
        """
        Determine exit code:
         OK or only INFO/WARN -> 0
         any ERROR -> 1
         any CRITICAL -> 2
        """
        max_sev = Severity.INFO
        for r in results:
            if not r.ok:
                if r.severity > max_sev:
                    max_sev = r.severity
        if max_sev >= Severity.CRITICAL:
            return 2
        if max_sev >= Severity.ERROR:
            return 1
        return 0
