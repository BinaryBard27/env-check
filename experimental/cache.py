import json
import hashlib
import os
from typing import Dict

def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

class ResultCache:
    def __init__(self, cache_path=".env-check-cache.json"):
        self.cache_path = cache_path
        self.data = {}
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}

    def make_key(self, env_path, schema_path):
        # composite key
        k = f"{env_path}|{schema_path}"
        return hashlib.sha256(k.encode()).hexdigest()

    def get(self, env_path, schema_path):
        key = self.make_key(env_path, schema_path)
        env_h = file_hash(env_path) if os.path.exists(env_path) else None
        entry = self.data.get(key)
        if entry and entry.get("env_hash") == env_h:
            return entry.get("issues", []), entry.get("meta", {})
        return None, None

    def set(self, env_path, schema_path, issues, meta=None):
        key = self.make_key(env_path, schema_path)
        env_h = file_hash(env_path) if os.path.exists(env_path) else None
        self.data[key] = {
            "env_hash": env_h,
            "issues": issues,
            "meta": meta or {}
        }
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)
