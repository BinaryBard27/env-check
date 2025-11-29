import re

SECRET_PATTERNS = {
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),

    "aws_secret_key": re.compile(
        r"(?i)aws(.{0,20})?(secret|access)[^a-z0-9]?([A-Za-z0-9/+=]{40})"
    ),

    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}"),

    "google_api_key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),

    "stripe_live_key": re.compile(r"sk_live_[0-9a-zA-Z]{20,}"),
    "stripe_test_key": re.compile(r"sk_test_[0-9a-zA-Z]{20,}"),

    "twilio_key": re.compile(r"SK[0-9a-fA-F]{32}"),

    "slack_token": re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,48}"),

    "jwt_token": re.compile(
        r"eyJ[A-Za-z0-9-_]+?\.[A-Za-z0-9-_]+?\.[A-Za-z0-9-_]+"
    ),

    "ssh_private_key": re.compile(
        r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"
    ),

    "private_key_block": re.compile(r"-----BEGIN PRIVATE KEY-----"),

    "base64_secret": re.compile(r"[A-Za-z0-9+/]{30,}={0,2}"),

    "hex_32": re.compile(r"[0-9a-fA-F]{32}"),

    "password_variable": re.compile(
        r"(?i)(password|passwd|pwd)[^a-z0-9]?[:=]"
    ),

    "token_variable": re.compile(
        r"(?i)(token|apikey|api_key|secret)[^a-z0-9]?[:=]"
    ),

    "generic_api_token": re.compile(r"[A-Za-z0-9_\-]{24,}"),
}
