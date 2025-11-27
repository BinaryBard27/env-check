# src/env_check/repo_scanner.py

import os
from .loader import load_env_file
from .drift import compare_env_dicts
from .secret_heuristics import scan_paths, SEVERITY

def find_env_files(root):
    """Find all .env-like files in the repository."""
    env_files = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            lower = f.lower()
            if lower.startswith(".env") or lower.endswith(".env") or ".env" in lower:
                env_files.append(os.path.join(dirpath, f))
    return env_files


def run_repo_scan(root):
    """
    Scan entire repo for:
    - env files
    - drift between them
    """
    result = {}
    env_files = find_env_files(root)
    result["env_files"] = env_files

    # DRIFT DETECTION
    drift_results = []
    for i in range(len(env_files)):
        for j in range(i + 1, len(env_files)):
            f1, f2 = env_files[i], env_files[j]
            env1 = load_env_file(f1)
            env2 = load_env_file(f2)
            drift_results.append((f1, f2, compare_env_dicts(env1, env2)))

    result["drift"] = drift_results

    # UNUSED / MISSING KEYS (simple linter)
    all_keys = set()
    per_file_keys = {}

    for f in env_files:
        data = load_env_file(f)
        keys = set(data.keys())
        per_file_keys[f] = keys
        all_keys |= keys

    missing = {}
    unused = {}

    for f, keys in per_file_keys.items():
        missing[f] = list(all_keys - keys)
        unused[f] = list(keys - all_keys)

    result["missing_env_vars"] = missing
    result["unused_env_vars"] = list(all_keys)

    return result


def detect_secret_leaks(root):
    """
    Apply advanced secret heuristics to all relevant files.
    """
    candidates = []

    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            fp = os.path.join(dirpath, f)

            # Scan programming & config files
            if f.lower().endswith((
                ".py", ".js", ".ts", ".go", ".java", ".rb",
                ".json", ".yml", ".yaml", ".env", ".ini", ".cfg",
                ".sh", ".bash"
            )) or f.lower().startswith(".env"):
                candidates.append(fp)

    findings = scan_paths(candidates)

    # Deduplicate (same file + line + snippet)
    unique = {}
    for f in findings:
        key = (f.get("file"), f.get("line"), f.get("value_snippet"))
        if key not in unique:
            unique[key] = f
        else:
            # If duplicate exists, pick higher severity
            old = unique[key]
            try:
                old_sev = SEVERITY.index(old["severity"])
                new_sev = SEVERITY.index(f["severity"])
                if new_sev > old_sev:
                    unique[key] = f
            except:
                pass

    return list(unique.values())
