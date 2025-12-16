from .base import BaseValidator
from typing import Tuple, Any

class RangeValidator(BaseValidator):
    def _to_number(self, v):
        try:
            if "." in str(v):
                return float(v)
            return int(v)
        except Exception:
            return None

    def validate(self, value: str, rule_spec: Any) -> Tuple[bool, str]:
        if not isinstance(rule_spec, dict):
            return False, "range rule must be object with min/max"
        vnum = self._to_number(value)
        if vnum is None:
            return False, "value is not numeric"
        if "min" in rule_spec:
            minv = self._to_number(rule_spec["min"])
            if minv is not None and vnum < minv:
                return False, f"value {vnum} < min {minv}"
        if "max" in rule_spec:
            maxv = self._to_number(rule_spec["max"])
            if maxv is not None and vnum > maxv:
                return False, f"value {vnum} > max {maxv}"
        return True, "ok"
