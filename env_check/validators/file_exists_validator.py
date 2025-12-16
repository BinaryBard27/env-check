from .base import BaseValidator
from typing import Tuple, Any
import os

class FileExistsValidator(BaseValidator):
    def validate(self, value: str, rule_spec: Any) -> Tuple[bool, str]:
        # rule_spec truthy means it must exist; falsy means ignore
        if not rule_spec:
            return True, "no file_exists rule"
        if os.path.exists(value):
            return True, "ok"
        return False, "path does not exist"
