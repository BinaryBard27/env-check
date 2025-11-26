import importlib.util
import os
import sys
from types import ModuleType
from typing import List, Dict

def _load_file_module(path: str) -> ModuleType:
    name = f"env_check_plugin_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None:
        raise ImportError(f"Cannot load plugin {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_plugins(plugin_paths: List[str], plugins_dir: str = None):
    modules = []
    # explicit paths
    for p in plugin_paths or []:
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        modules.append(_load_file_module(os.path.abspath(p)))
    # directory
    if plugins_dir:
        if not os.path.isdir(plugins_dir):
            raise NotADirectoryError(plugins_dir)
        for fname in sorted(os.listdir(plugins_dir)):
            if fname.endswith(".py"):
                modules.append(_load_file_module(os.path.join(plugins_dir, fname)))
    return modules

def run_plugins(modules, env_vars: dict, schema: dict):
    results = []
    for mod in modules:
        # plugin should expose run(env_vars, schema)
        if hasattr(mod, "run"):
            try:
                out = mod.run(env_vars, schema)
                if out:
                    results.extend(out)
            except Exception as e:
                results.append({
                    "type": "plugin_error",
                    "message": f"Plugin {getattr(mod, '__file__', str(mod))} raised: {e}"
                })
        else:
            results.append({
                "type": "plugin_error",
                "message": f"Plugin {getattr(mod, '__file__', str(mod))} has no run(env_vars, schema)"
            })
    return results
