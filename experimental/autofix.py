import re
import shutil
import os

MALFORMED_MSG = "Malformed line (missing '=')"

class AutoFixer:
    def __init__(self, env_path=".env", backup=True):
        self.env_path = env_path
        self.backup = backup

    def _read_lines(self):
        with open(self.env_path, "r", encoding="utf-8") as f:
            return f.readlines()

    def _write_lines(self, lines):
        with open(self.env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def make_backup(self):
        if not os.path.exists(self.env_path):
            return False
        bak = self.env_path + ".bak"
        shutil.copy2(self.env_path, bak)
        return bak

    def _normalize_quotes_and_trim(self, line):
        # remove trailing whitespace (but keep newline)
        stripped = line.rstrip("\n").rstrip()
        # normalize quotes around value (if pattern KEY="value" or KEY='value')
        if "=" in stripped:
            k, v = stripped.split("=", 1)
            v = v.strip()
            if len(v) >= 2 and ((v[0] == v[-1]) and v[0] in ("'", '"')):
                v = v[1:-1]
            return f"{k.strip()}={v}\n"
        return stripped + ("\n" if not stripped.endswith("\n") else "")

    def apply(self, mode="a"):
        """
        mode "a" = default fixes (remove malformed lines)
        mode "b" = comment malformed lines (prefix with "# ")
        """
        lines = self._read_lines()
        new_lines = []
        seen_keys = {}
        modified = False

        for idx, raw in enumerate(lines, start=1):
            original = raw
            # keep newline char behavior
            line_no_n = original.rstrip("\n")

            # Preserve comments and blank lines immediately
            if not line_no_n.strip() or line_no_n.strip().startswith("#"):
                new_lines.append(original)
                continue

            if "=" not in line_no_n:
                # MALFORMED
                if mode == "b":
                    # comment it out
                    commented = f"# {line_no_n}\n"
                    new_lines.append(commented)
                else:
                    # remove line (mode a)
                    # skip appending to new_lines
                    pass
                modified = True
                continue

            # process valid key=value
            key, val = line_no_n.split("=", 1)
            key = key.strip()
            val = val.strip()

            # dedupe: if seen, keep first occurrence; later duplicates removed
            if key in seen_keys:
                # skip duplicate (we consider keeping first)
                modified = True
                continue
            seen_keys[key] = idx

            # normalize: trim & remove surrounding quotes
            normalized = self._normalize_quotes_and_trim(f"{key}={val}\n")
            new_lines.append(normalized)
            if normalized != original:
                modified = True

        if modified:
            bak = None
            if self.backup:
                bak = self.make_backup()
            self._write_lines(new_lines)
            return True, bak
        return False, None
