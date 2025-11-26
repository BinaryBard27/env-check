import os
import re
from glob import glob

def find_env_usage(root_paths, keys):
    # root_paths: list of paths/globs to search (e.g., ["src/**/*.py", "templates/**/*.html"])
    # keys: iterable of variable names to search for
    usages = {k: [] for k in keys}
    key_patterns = {k: re.compile(r"\b" + re.escape(k) + r"\b") for k in keys}
    files = []
    for p in root_paths:
        # allow simple globs, handle directories by walking
        if os.path.isdir(p):
            for dirpath, _, filenames in os.walk(p):
                for fn in filenames:
                    files.append(os.path.join(dirpath, fn))
        else:
            files.extend(glob(p, recursive=True))
    files = sorted(set(files))
    for file in files:
        # skip binaries
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        except Exception:
            continue
        for k, pat in key_patterns.items():
            if pat.search(txt):
                usages[k].append(file)
    # unused keys = keys with empty usage lists
    unused = [k for k, v in usages.items() if not v]
    issues = []
    for k in unused:
        issues.append({
            "type": "unused_key",
            "severity": "warning",
            "key": k,
            "message": f"Key '{k}' appears unused in scanned paths."
        })
    return issues, usages
