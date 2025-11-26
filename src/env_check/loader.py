import json
import os

_SCHEMA_CACHE = None

class SchemaLoader:
    def __init__(self, path=None):
        # Get root directory of project
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # Default schema path: <project_root>/schema/schema.json
        default_path = os.path.join(project_root, "schema", "schema.json")

        self.path = path or default_path

    def load(self):
        global _SCHEMA_CACHE

        if _SCHEMA_CACHE is not None:
            return _SCHEMA_CACHE

        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Schema file not found at: {self.path}")

        with open(self.path, "r") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("Schema file must contain a JSON object.")

        # Sanity check
        required_keys = ["required", "patterns", "secret"]
        for key in required_keys:
            if key not in data:
                print(f"WARNING: Schema missing '{key}'.")

        _SCHEMA_CACHE = data
        return data
