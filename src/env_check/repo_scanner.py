# src/env_check/repo_scanner.py

import os
import re
from .drift_detection import load_env_file, compare_env_files


SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",                          # AWS Access Key
    r"AIza[0-9A-Za-z\-_]{35}",                    # Google API Key
    r"sk_live_[0-9a-zA-Z]{24}",                   # Stripe live key
    r"sk_test_[0-9a-zA-Z]{24}",                   # Stripe test key
    r"[A-Za-z0-9-_]{20,}\.[A-Za-z0-9-_]{20,}\.[A-Za-z0-9-_]{20,}",  # JWT
    r"-----BEGIN PRIVATE KEY-----",
    r"ghp_[A-Za-z0-9]{36}",                       # GitHub token
    r"[0-9a-fA-F]{32}",                           # generic hex secrets
]


def find_env_files(root):
    matches = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.startswith(".env"):
                matches.append(os.path.join(dirpath, f))
    return matches


def detect_secret_leaks(root):
    leaks = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith((".py", ".js", ".ts", ".go", ".json", ".yml", ".yaml", ".env")):
                path = os.path.join(dirpath, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        for pattern in SECRET_PATTERNS:
                            if re.search(pattern, content):
                                leaks.append((path, pattern))
                except:
                    pass
    return leaks


def analyze_env_usage(root, env_files):
    """Find variables used in source code but missing in env files."""
    used_vars = set()

    getenv_pattern = re.compile(r"os\.getenv\(['\"]([A-Z0-9_]+)['\"]\)")
    dotenv_pattern = re.compile(r"process\.env\.([A-Z0-9_]+)")

    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith((".py", ".js", ".ts", ".go")):
                path = os.path.join(dirpath, f)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                        used_vars.update(getenv_pattern.findall(content))
                        used_vars.update(dotenv_pattern.findall(content))
                except:
                    pass

    defined_vars = set()
    for f in env_files:
        data = load_env_file(f)
        defined_vars.update(data.keys())

    missing_in_env = used_vars - defined_vars
    unused_in_code = defined_vars - used_vars

    return list(missing_in_env), list(unused_in_code)


def run_repo_scan(root):
    report = {}

    # 1. Find all env files
    env_files = find_env_files(root)
    report["env_files"] = env_files

    # 2. Drift detection across each pair
    drift_results = []
    for i in range(len(env_files)):
        for j in range(i + 1, len(env_files)):
            f1, f2 = env_files[i], env_files[j]
            result = compare_env_files(f1, f2)
            drift_results.append((f1, f2, result))
    report["drift"] = drift_results

    # 3. Secret leak detection
    leaks = detect_secret_leaks(root)
    report["secret_leaks"] = leaks

    # 4. Env usage analysis
    missing, unused = analyze_env_usage(root, env_files)
    report["missing_env_vars"] = missing
    report["unused_env_vars"] = unused

    return report
