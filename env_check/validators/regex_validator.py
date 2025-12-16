from .base import BaseValidator
from typing import Tuple, Any
import re

class RegexValidator(BaseValidator):
    def validate(self, value: str, rule_spec: Any) -> Tuple[bool, str]:
        pattern = rule_spec
        try:
            if not pattern:
                return True, "no pattern"
            if re.fullmatch(pattern, value):
                return True, "ok"
            return False, f"value does not match pattern: {pattern}"
        except re.error as e:
            return False, f"invalid regex: {e}"
