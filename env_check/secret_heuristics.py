import re
import math
from collections import Counter
from typing import List, Dict, Optional
from .patterns import SECRET_PATTERNS

# -----------------------------------------
# 🔥 1. Regex Signature Patterns
# -----------------------------------------

SIGNATURES = {
    "AWS_ACCESS_KEY": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GITHUB_PAT": re.compile(r"ghp_[A-Za-z0-9]{36}"),
    "JWT_TOKEN": re.compile(r"[A-Za-z0-9-_]{20,}\.[A-Za-z0-9-_]{20,}\.[A-Za-z0-9-_]{20,}"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    "STRIPE_LIVE_KEY": re.compile(r"sk_live_[0-9a-zA-Z]{24}"),
    "STRIPE_TEST_KEY": re.compile(r"sk_test_[0-9a-zA-Z]{24}"),
    "GOOGLE_API_KEY": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "HEX_32": re.compile(r"\b[0-9a-fA-F]{32}\b"),
    "BASE64_LONG": re.compile(r"\b[A-Za-z0-9+/]{20,}={0,2}\b"),
}

# Keywords around values that increase suspicion
CONTEXT_KEYWORDS = [
    "secret", "password", "passwd", "pwd", "token",
    "apikey", "api_key", "auth", "private", "jwt", "rsa", "ssh"
]

# Severity Levels
SEVERITY = {
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFO": 0
}


def classify_severity(pattern_name, value=None):
    """Return severity based on pattern type."""
    critical_patterns = [
        "aws_access_key",
        "aws_secret_key",
        "stripe_live_key",
        "private_key_block",
        "google_api_key",
        "slack_token",
        "jwt_token",
        "AWS_ACCESS_KEY",
        "GITHUB_PAT",
        "JWT_TOKEN",
        "PRIVATE_KEY",
        "STRIPE_LIVE_KEY",
        "GOOGLE_API_KEY"
    ]

    medium_patterns = [
        "stripe_test_key",
        "cryptographic_material",
        "password",
        "db_url",
        "STRIPE_TEST_KEY",
        "BASE64_LONG"
    ]

    low_patterns = [
        "suspicious_short_value",
        "looks_like_token",
        "random_hex",
        "HEX_32"
    ]

    if pattern_name in critical_patterns:
        return "HIGH"
    elif pattern_name in medium_patterns:
        return "MEDIUM"
    elif pattern_name in low_patterns:
        return "LOW"
    return "INFO"


# -----------------------------------------
# 🔥 2. Entropy Calculation
# -----------------------------------------

def shannon_entropy(value: str) -> float:
    """Compute Shannon entropy for the string."""
    if not value:
        return 0.0
    freq = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in freq.values())


# -----------------------------------------
# 🔥 3. Pattern Classification
# -----------------------------------------

def match_signature(value: str) -> Optional[str]:
    """Return signature name if a pattern matches."""
    for name, pattern in SIGNATURES.items():
        if pattern.search(value):
            return name
    return None


# -----------------------------------------
# 🔥 4. Context Score (keyword detection)
# -----------------------------------------

def context_score(line: str) -> int:
    """Bonus if suspicious keywords appear near the value."""
    score = 0
    line_low = line.lower()
    for keyword in CONTEXT_KEYWORDS:
        if keyword in line_low:
            score += 1
    return score


# -----------------------------------------
# 🔥 5. Severity Scoring (Legacy / Helper)
# -----------------------------------------

def determine_severity(pattern: Optional[str], entropy: float, length: int, context: int) -> str:
    # This function is kept for compatibility if needed, but we rely on classify_severity now.
    # Mapping old logic to new keys if necessary, or just returning a default.
    return "INFO"


# -----------------------------------------
# 🔥 6. Scan a single string for secrets
# -----------------------------------------

def scan_string(value: str, surrounding_line: str = "") -> List[Dict]:
    findings = []

    pattern = match_signature(value)
    entropy = shannon_entropy(value)
    length = len(value)
    ctx = context_score(surrounding_line + " " + value)

    # heuristic: skip extremely short values
    if length < 8:
        return findings

    if pattern or entropy >= 3.5 or length >= 12:
        findings.append({
            "value_snippet": value[:60] + ("..." if len(value) > 60 else ""),
            "pattern": pattern,
            "entropy": round(entropy, 3),
            "length": length,
            "context_score": ctx,
            # We will override severity in scan_file using classify_severity
            "severity": "INFO", 
        })

    return findings


# -----------------------------------------
# 🔥 7. Scan a file for secrets
# -----------------------------------------

def scan_file(path: str) -> List[Dict]:
    results = []

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as file:
            lines = file.readlines()
    except:
        return results

    for line_no, line in enumerate(lines, start=1):
        snippet = line.strip()
        for pattern_name, regex in SECRET_PATTERNS.items():
            if regex.search(snippet):
                results.append({
                    "file": path,
                    "line": line_no,
                    "value_snippet": snippet,
                    "pattern": pattern_name,
                    "severity": classify_severity(pattern_name, snippet)
                })
                continue

        # capture quoted values OR long tokens
        tokens = re.findall(r"['\"]([^'\"]{6,200})['\"]|([A-Za-z0-9\-_\.\/\+]{12,200})", line)
        tokens = [t[0] or t[1] for t in tokens]

        # also capture env-style values after "="
        if "=" in line:
            key, val = line.split("=", 1)
            tokens.append(val.strip())

        for token in tokens:
            findings = scan_string(token, surrounding_line=line)
            for f in findings:
                # Use the new classify_severity function
                pattern_name = f["pattern"]
                snippet = f["value_snippet"]
                
                # If no pattern matched but we found it via heuristics (entropy/length),
                # assign a default pattern name for classification if needed, 
                # or rely on classify_severity returning INFO/LOW.
                if not pattern_name:
                    if f["entropy"] > 4.5:
                        pattern_name = "random_hex" # or similar high entropy category
                    else:
                        pattern_name = "suspicious_short_value"

                results.append({
                    "file": path,
                    "line": line_no,
                    "value_snippet": snippet,
                    "pattern": pattern_name,
                    "severity": classify_severity(pattern_name, snippet)
                })

    return results


# -----------------------------------------
# 🔥 8. Scan multiple files
# -----------------------------------------

def scan_paths(paths: List[str]) -> List[Dict]:
    all_results = []
    for p in paths:
        all_results.extend(scan_file(p))
    return all_results


def run_secret_scan(path):
    import os
    candidates = []
    if os.path.isfile(path):
        candidates.append(path)
    else:
        for dirpath, _, filenames in os.walk(path):
            for f in filenames:
                candidates.append(os.path.join(dirpath, f))

    findings = scan_paths(candidates)
    print(f"Scanning secrets in {path}...")
    for f in findings:
        print(f"[{f['severity']}] {f['file']}:{f['line']} {f['pattern']} -> {f['value_snippet']}")

