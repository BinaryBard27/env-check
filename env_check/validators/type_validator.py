from .base import BaseValidator
from typing import Tuple, Any

class TypeValidator(BaseValidator):
    def validate(self, value: str, rule_spec: Any) -> Tuple[bool, str]:
        if not rule_spec:
            return True, "no type specified"
        expected = str(rule_spec).lower()
        try:
            if expected in ("int", "integer"):
                int(value)
                return True, "ok"
            if expected in ("float",):
                float(value)
                return True, "ok"
            if expected in ("bool", "boolean"):
                lv = value.lower()
                if lv in ("true", "false", "1", "0", "yes", "no"):
                    return True, "ok"
                return False, f"invalid boolean value: {value}"
            if expected in ("str", "string"):
                return True, "ok"
            return True, "unknown type (treated as ok)"
        except Exception as e:
            return False, f"type conversion failed: {e}"
