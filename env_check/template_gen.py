import os
import json

def generate_example(schema, out_path=".env.example"):
    """
    Given schema dict, produce a .env.example.
    schema partial expected: { "required": [...], "patterns": {...} , "secret": [...] , "defaults": {key: value}}
    """
    lines = []
    required = schema.get("required", [])
    defaults = schema.get("defaults", {}) if isinstance(schema.get("defaults", {}), dict) else {}
    for key in required:
        val = defaults.get(key, "")
        lines.append(f"{key}={val}")
    # also include non-required patterns as commented templates
    for key in schema.get("patterns", {}).keys():
        if key not in required:
            lines.append(f"# {key}=<value matching {schema['patterns'][key]}>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return out_path
