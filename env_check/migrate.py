"""
migrate.py
Simple migration helpers between env <-> json/yaml
"""
import os
import json

try:
    import yaml
    YAML_AVAILABLE = True
except Exception:
    YAML_AVAILABLE = False


def read_env(path: str) -> dict:
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip()
            if len(v) >= 2 and ((v[0] == v[-1]) and v[0] in ("'", '"')):
                v = v[1:-1]
            env[k] = v
    return env


def write_env(env: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        for k, v in env.items():
            # quote if contains spaces
            if " " in v or "#" in v:
                fv = json.dumps(v)  # safe quoting via JSON
                f.write(f"{k}={fv}\n")
            else:
                f.write(f"{k}={v}\n")


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(env: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)


def read_yaml(path: str) -> dict:
    if not YAML_AVAILABLE:
        raise RuntimeError("PyYAML not available. pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(env: dict, path: str):
    if not YAML_AVAILABLE:
        raise RuntimeError("PyYAML not available. pip install pyyaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(env, f, default_flow_style=False)


# High-level convenience:
def env_to_json(src: str, dst: str):
    env = read_env(src)
    write_json(env, dst)


def env_to_yaml(src: str, dst: str):
    env = read_env(src)
    write_yaml(env, dst)


def json_to_env(src: str, dst: str):
    env = read_json(src)
    write_env(env, dst)


def yaml_to_env(src: str, dst: str):
    env = read_yaml(src)
    write_env(env, dst)
