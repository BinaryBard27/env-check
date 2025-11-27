import re
import math
from collections import Counter
from typing import List, Dict, Optional

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
SEVERITY = ["low", "medium", "high", "critical"]


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
# 🔥 5. Severity Scoring
# -----------------------------------------

def determine_severity(pattern: Optional[str], entropy: float, length: int, context: int) -> str:
    index = 0  # low severity

    if pattern:
        if "PRIVATE_KEY" in pattern or "JWT" in pattern:
            index = 3
        elif "AWS" in pattern or "GITHUB" in pattern or "STRIPE" in pattern:
            index = 2
        else:
            index = 1
    else:
        # No signature → heuristic score
        if entropy >= 4.0 and length >= 20:
            index = 2
        elif entropy >= 3.5 and length >= 12:
            index = 1

    # context boosts severity
    if context > 0:
        index = min(index + 1, 3)

    return SEVERITY[index]


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
            "severity": determine_severity(pattern, entropy, length, ctx),
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
                results.append({
                    "file": path,
                    "line": line_no,
                    "excerpt": line.strip()[:180],
                    **f
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
