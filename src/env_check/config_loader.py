# src/env_check/config_loader.py
import os
import yaml

DEFAULT_CONFIG = {
    "exclude_dirs": [
        ".git",
        ".env-check-cache",
        "env-check-clean",
        "__pycache__"
    ],
    "exclude_patterns": [
        "*.pyc",
        "*.zip",
        "*.tar",
        "*.gz",
        "*.db",
        "*.sqlite"
    ],
    "exclude_keys": []
}

def load_config(repo_root: str) -> dict:
    """
    Load .envcheck.yml from repo_root (if present) and merge with defaults.
    Returns a dict with keys: exclude_dirs, exclude_patterns, exclude_keys.
    """
    cfg = DEFAULT_CONFIG.copy()
    path = os.path.join(repo_root, ".envcheck.yml")
    if not os.path.exists(path):
        return cfg

    try:
        with open(path, "r", encoding="utf-8") as fh:
            user = yaml.safe_load(fh) or {}
            # Merge lists, prefer user-defined additions
            for key in ("exclude_dirs", "exclude_patterns", "exclude_keys"):
                if key in user and isinstance(user[key], list):
                    cfg[key] = list(dict.fromkeys(cfg[key] + user[key]))
    except Exception:
        # If anything fails, return defaults (fail-safe)
        return cfg

    return cfg
