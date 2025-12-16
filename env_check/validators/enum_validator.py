from .base import BaseValidator
from typing import Tuple, Any

class EnumValidator(BaseValidator):
    def validate(self, value: str, rule_spec: Any) -> Tuple[bool, str]:
        allowed = rule_spec
        if not isinstance(allowed, (list, tuple, set)):
            return False, "enum rule must be a list"
        if value in allowed:
            return True, "ok"
        return False, f"value not in allowed set: {allowed}"
