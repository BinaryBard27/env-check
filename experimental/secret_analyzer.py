import math
import re

class SecretAnalyzer:
    WEAK_PATTERNS = [
        "123", "1234", "12345", "abc", "abcd", "password", "pass",
        "admin", "qwerty", "letmein"
    ]

    TOKEN_TYPES = {
        "JWT": r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$",
        "BASE64": r"^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$",
        "AWS_ACCESS_KEY": r"^AKIA[0-9A-Z]{16}$",
        "HEX": r"^[A-Fa-f0-9]{32,}$",
    }

    @staticmethod
    def calculate_entropy(secret: str) -> float:
        if not secret:
            return 0.0
        freq = {c: secret.count(c) for c in set(secret)}
        length = len(secret)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def detect_token_type(secret: str):
        for token_type, pattern in SecretAnalyzer.TOKEN_TYPES.items():
            if re.fullmatch(pattern, secret):
                return token_type
        return "UNKNOWN"

    @staticmethod
    def contains_weak_pattern(secret: str):
        s = (secret or "").lower()
        return any(p in s for p in SecretAnalyzer.WEAK_PATTERNS)

    @staticmethod
    def score(secret: str):
        entropy = SecretAnalyzer.calculate_entropy(secret)
        token_type = SecretAnalyzer.detect_token_type(secret)
        weak = SecretAnalyzer.contains_weak_pattern(secret)
        length = len(secret or "")

        if length < 12 or weak or entropy < 2.5:
            return "weak", entropy, token_type
        if length < 24 or entropy < 3.5:
            return "medium", entropy, token_type
        return "strong", entropy, token_type
