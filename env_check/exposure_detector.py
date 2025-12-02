import re

EXPOSURE_PATTERNS = {
    "url_with_creds": re.compile(r"https?://[^/\s:@]+:[^/\s:@]+@"),  # user:pass@host
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "potential_jwt": re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"),
    "pem_key": re.compile(r"-----BEGIN (RSA|PRIVATE|ENCRYPTED) PRIVATE KEY-----"),
    "base64_long": re.compile(r"^[A-Za-z0-9+/]{40,}={0,2}$"),
    # add more as needed
}

def detect_exposure(env_vars: dict):
    issues = []
    for k, v in env_vars.items():
        for name, pat in EXPOSURE_PATTERNS.items():
            try:
                if pat.search(v):
                    issues.append({
                        "type": "exposure",
                        "severity": "error",
                        "key": k,
                        "pattern": name,
                        "message": f"Value for {k} matches exposure pattern '{name}'."
                    })
            except re.error:
                continue
    return issues
