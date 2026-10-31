from typing import Dict, Any, List
import os
from .severity import Severity

# Import validator classes dynamically
from env_check.validators.base import BaseValidator
from env_check.validators.type_validator import TypeValidator
from env_check.validators.regex_validator import RegexValidator
from env_check.validators.enum_validator import EnumValidator
from env_check.validators.range_validator import RangeValidator
from env_check.validators.file_exists_validator import FileExistsValidator
from env_check.validators.non_empty_validator import NonEmptyValidator

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
    KNOWN_TYPES = ("int", "integer", "float", "bool", "boolean", "str", "string")

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

            # Copy so we never mutate the caller's schema
            rules = dict(rules)

            # 'pattern' is an accepted alias for 'regex'
            if "pattern" in rules:
                rules.setdefault("regex", rules.pop("pattern"))

            # Normalize shorthand min/max into range (merged with explicit range)
            if "min" in rules or "max" in rules:
                base_range = rules.get("range")
                if not isinstance(base_range, dict):
                    base_range = {}
                range_dict = dict(base_range)
                for k in ("min", "max"):
                    if k in rules:
                        range_dict[k] = rules[k]
                rules["range"] = range_dict

            warnings = []

            allowed_keys = {
                "required", "type", "regex", "enum",
                "range", "file_exists", "non_empty", "severity",
                "min", "max", "pattern", "secret"
            }

            unknown = set(rules.keys()) - allowed_keys
            if unknown:
                warnings.append(f"Unknown rule keys: {sorted(unknown)}")

            # Unknown type names are a warning, not a failure
            if "type" in rules and str(rules["type"]).lower() not in self.KNOWN_TYPES:
                warnings.append(f"Unknown type '{rules['type']}' (treated as ok)")

            # Base severity for non-required failures
            severity = Severity.from_name(rules.get("severity"))

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
                        # A range failure on a non-numeric value is really a
                        # type failure when a type rule is present
                        if key == "range" and msg == "value is not numeric" and "type" in rules:
                            msg = f"not a valid {str(rules['type']).lower()}"
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
                final_severity = Severity.WARN
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
