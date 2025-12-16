import json
import yaml
from typing import Dict, Any


def load_config(path: str) -> Dict[str, Any]:
    if not path:
        raise ValueError("Config path is empty")

    with open(path, "r", encoding="utf-8") as f:
        if path.endswith((".yml", ".yaml")):
            data = yaml.safe_load(f)
        elif path.endswith(".json"):
            data = json.load(f)
        else:
            raise ValueError("Unsupported config format (use .yml, .yaml, or .json)")

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping of ENV_VAR -> rules")

    return data
