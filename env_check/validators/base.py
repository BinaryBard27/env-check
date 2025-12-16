from typing import Tuple, Any

class BaseValidator:
    """
    Base class for validators.
    validate(value, rule_spec) -> (bool_ok, message)
    """
    def validate(self, value: str, rule_spec: Any) -> Tuple[bool, str]:
        raise NotImplementedError()
