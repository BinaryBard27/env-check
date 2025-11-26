"""
plugins.py - load and run custom plugins
"""
import importlib.util
import os
import sys
from types import ModuleType
from typing import List

def _load_module_from_path(path: str) -> ModuleType:
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    name = f"env_check_plugin_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_plugins(plugin_paths: list = None, plugins_dir: str = None):
    modules = []
    plugin_paths = plugin_paths or []
    for p in plugin_paths:
        modules.append(_load_module_from_path(p))

    if plugins_dir:
        for fname in os.listdir(plugins_dir):
            if fname.endswith(".py"):
                modules.append(_load_module_from_path(os.path.join(plugins_dir, fname)))
    return modules

def run_plugins(modules: list, env_vars: dict, schema: dict):
    """
    Each plugin must expose run(env_vars, schema) -> list_of_issues (or None)
    Issue format: { "type": "...", "message": "...", "severity": "warning"/"error" }
    """
    all_issues = []
    for mod in modules:
        if hasattr(mod, "run") and callable(mod.run):
            try:
                result = mod.run(env_vars, schema)
                if isinstance(result, list):
                    all_issues.extend(result)
            except Exception as e:
                all_issues.append({
                    "type": "plugin_error",
                    "message": f"Plugin {getattr(mod, '__name__', 'unknown')} failed: {e}",
                    "severity": "warning"
                })
        else:
            all_issues.append({
                "type": "plugin_error",
                "message": f"Plugin {getattr(mod, '__name__', 'unknown')} missing run(env_vars, schema)",
                "severity": "warning"
            })
    return all_issues
