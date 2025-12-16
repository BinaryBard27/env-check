from .base import BaseValidator
from typing import Tuple, Any

class NonEmptyValidator(BaseValidator):
    def validate(self, value: str, rule_spec: Any) -> Tuple[bool, str]:
        if not rule_spec:
            return True, "no non_empty rule"
        if value is None or str(value).strip() == "":
            return False, "value is empty"
        return True, "ok"
