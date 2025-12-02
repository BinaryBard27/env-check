import re

class EnvLinter:
    INVISIBLE_PATTERN = re.compile(r"[\u200B\u200C\u200D\uFEFF]")  # zero-width chars

    def __init__(self, env_vars_raw):
        """
        env_vars_raw: list of tuples (line_no, raw_line)
        """
        self.lines = env_vars_raw
        self.issues = []

    def check_duplicate_keys(self):
        seen = {}
        for line_no, line in self.lines:
            if "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if not key:
                continue
            if key in seen:
                self.issues.append({
                    "type": "duplicates",
                    "key": key,
                    "message": f"Duplicate key '{key}' on line {line_no} (previously on line {seen[key]})."
                })
            else:
                seen[key] = line_no

    def check_trailing_whitespace(self):
        for line_no, line in self.lines:
            # ignore pure comment/empty lines
            if not line or line.strip().startswith("#"):
                continue
            if line.endswith(" ") or line.endswith("\t"):
                self.issues.append({
                    "type": "invisible_ws",
                    "message": f"Trailing whitespace found on line {line_no}."
                })

    def check_invisible_characters(self):
        for line_no, line in self.lines:
            if self.INVISIBLE_PATTERN.search(line):
                self.issues.append({
                    "type": "invisible_ws",
                    "message": f"Zero-width or invisible character found on line {line_no}."
                })

    def check_empty_values(self):
        for line_no, line in self.lines:
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if value.strip() == "":
                self.issues.append({
                    "type": "missing_value",
                    "key": key.strip(),
                    "message": f"Key '{key.strip()}' has an empty value (line {line_no})."
                })

    def check_spacing(self):
        for line_no, line in self.lines:
            if "=" not in line:
                continue
            before, after = line.split("=", 1)
            # flag spaces before or after '=' (conservative)
            if before.endswith(" ") or after.startswith(" "):
                self.issues.append({
                    "type": "spacing",
                    "message": f"Inconsistent spacing around '=' on line {line_no}."
                })

    def lint(self):
        self.check_duplicate_keys()
        self.check_trailing_whitespace()
        self.check_invisible_characters()
        self.check_empty_values()
        self.check_spacing()
        # self.check_malformed()
        return self.issues
