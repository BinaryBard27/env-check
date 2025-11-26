import re
from .secret_analyzer import SecretAnalyzer

class SchemaValidator:
    _compiled_patterns = {}

    def __init__(self, schema: dict, env_vars: dict, strict=False):
        self.schema = schema
        self.env = env_vars
        self.strict = strict
        self.issues = []

    # ---------------------------
    # Required key validation
    # ---------------------------
    def check_required(self):
        required_keys = self.schema.get("required", [])
        for key in required_keys:
            if key not in self.env:
                self.issues.append({
                    "type": "missing_key",
                    "key": key,
                    "message": f"{key} is required but missing."
                })

    # ---------------------------
    # Pattern-based validation
    # ---------------------------
    def check_patterns(self):
        patterns = self.schema.get("patterns", {})
        for key, regex in patterns.items():
            if key in self.env:
                value = self.env[key]
                
                if key not in self._compiled_patterns:
                    self._compiled_patterns[key] = re.compile(regex)

                if not self._compiled_patterns[key].fullmatch(value):
                    self.issues.append({
                        "type": "pattern_mismatch",
                        "key": key,
                        "value": value,
                        "expected": regex,
                        "message": f"{key} does not match required pattern."
                    })

    # ---------------------------
    # Combine all checks
    # ---------------------------
    def validate(self):
        self.check_required()
        self.check_patterns()
        if self.strict:
            self.check_extra_keys()
        
        self.check_unused()
        self.check_secrets()
        return self.issues

    def check_extra_keys(self):
        schema_keys = set(self.schema.get("required", [])) | set(self.schema.get("patterns", {}).keys())
        for key in self.env.keys():
            if key not in schema_keys:
                self.issues.append({
                    "type": "extra",
                    "severity": "error",
                    "key": key,
                    "message": f"Key '{key}' is not allowed in strict mode."
                })

    def check_unused(self):
        schema_keys = (
            set(self.schema.get("required", []))
            | set(self.schema.get("patterns", {}).keys())
            | set(self.schema.get("secret", []))
        )

        for key in self.env.keys():
            if key not in schema_keys:
                self.issues.append({
                    "type": "unused",
                    "severity": "info",
                    "key": key,
                    "message": f"Key '{key}' is not used in schema."
                })

    def check_secrets(self):
        secret_keys = self.schema.get("secret", [])
        for key in secret_keys:
            if key in self.env:
                value = self.env[key]
                status, entropy, token_type = SecretAnalyzer.score(value)
                
                if status == "exposed":
                    self.issues.append({
                        "type": "secret_exposed",
                        "severity": "error",
                        "key": key,
                        "message": f"CRITICAL: Secret '{key}' appears to be exposed (type: {token_type})."
                    })
                elif status == "weak":
                    self.issues.append({
                        "type": "weak_secret",
                        "severity": "warning",
                        "key": key,
                        "message": f"Secret '{key}' has low entropy ({entropy:.2f}). Consider generating a stronger secret."
                    })

    def run_all_checks_parallel(self):
        from concurrent.futures import ThreadPoolExecutor

        checks = [
            self.check_required,
            self.check_patterns,
            self.check_secrets
        ]

        with ThreadPoolExecutor() as executor:
            executor.map(lambda fn: fn(), checks)

        return self.issues
