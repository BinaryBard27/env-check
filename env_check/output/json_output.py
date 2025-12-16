import json
from typing import List
from ..validator import ValidationResult

def render_json(results: List[ValidationResult]) -> str:
    return json.dumps([r.to_dict() for r in results], indent=2)
