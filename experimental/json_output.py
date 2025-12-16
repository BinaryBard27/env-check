# src/env_check/json_output.py

import json

def to_json(data, pretty=False):
    """Convert result dict into JSON string."""
    if pretty:
        return json.dumps(data, indent=4, ensure_ascii=False)
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def wrap_json_response(
        action: str,
        success: bool,
        errors=None,
        warnings=None,
        details=None
    ):
    """Standardize JSON output structure."""
    return {
        "tool": "env-check",
        "version": "1.1.0",
        "action": action,
        "success": success,
        "errors": errors or [],
        "warnings": warnings or [],
        "details": details or {},
    }
