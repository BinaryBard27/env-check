#!/usr/bin/env python3
"""
env-check: validate .env files using JSON/YAML schema + Phase 3 capabilities
"""
import sys
import argparse
import json
import os
from typing import Tuple

from .loader import SchemaLoader
from .schema_validator import SchemaValidator
from .env_linter import EnvLinter
from .secret_analyzer import SecretAnalyzer

# Phase3 modules
from . import migrate as migrate_mod
from . import ci as ci_mod
from . import plugins as plugins_mod
from .autofix import AutoFixer
from .anomaly import SimpleAnomalyDetector  # optional - keep if present

VERSION = "1.1.0"


def load_env_file(path: str) -> Tuple[dict, list]:
    """
    Reads .env file. Returns (env_vars, raw_lines)
    env_vars: {KEY: value}
    raw_lines: list of (line_no, original_line)
    """
    env_vars = {}
    env_vars_raw = []
    line_no = 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line_no += 1
                original_line = line.rstrip("\n")
                env_vars_raw.append((line_no, original_line))
                sline = original_line.strip()

                if not sline or sline.startswith("#"):
                    continue

                if "=" not in sline:
                    # keep as invalid/ignored line
                    continue

                key, value = sline.split("=", 1)
                key = key.strip()
                value = value.strip()
                if len(value) >= 2 and ((value[0] == value[-1]) and value[0] in ("'", '"')):
                    value = value[1:-1]
                env_vars[key] = value

    except FileNotFoundError:
        print(f"ERROR: env file not found: {path}", file=sys.stderr)
        sys.exit(2)

    return env_vars, env_vars_raw


def print_header(args):
    print(f"env-check v{VERSION} — Environment File Validator")
    if not args.quiet:
        print()


def build_json_result(status: str, file: str, errors: list, warnings: list, infos: list):
    sev = {"error": sum(1 for e in errors if e.get("severity", "error") == "error"),
           "warning": len(warnings),
           "info": len(infos)}
    return {
        "status": status,
        "version": VERSION,
        "file": file,
        "severity_count": sev,
        "error_count": len(errors),
        "errors": errors,
        "warnings": warnings,
        "infos": infos
    }


def main():
    parser = argparse.ArgumentParser(prog="env-check",
        description="env-check: validate .env files using JSON schema and extras (migration, CI init, plugins)")
    parser.add_argument("--schema", "-s", default=None, help="path to schema file (optional)")
    parser.add_argument("--env", "-e", default=".env", help="path to .env file")
    parser.add_argument("--strict", action="store_true", help="enable strict mode (extra keys fail etc.)")
    parser.add_argument("--quiet", action="store_true", help="suppress OK output, only show errors")
    parser.add_argument("--minimal", action="store_true", help="minimal output mode (summary only)")
    parser.add_argument("--verbose", action="store_true", help="verbose output for debugging")
    parser.add_argument("--json", action="store_true", help="output machine-readable JSON")
    parser.add_argument("--fix", action="store_true", help="run autofix")
    parser.add_argument("--fix-mode", choices=["a", "b"], default="a", help="autofix behavior (a=aggressive,b=backup)")
    parser.add_argument("--version", action="store_true", help="print version")
    # Phase2 options (already present)
    parser.add_argument("--parallel", action="store_true", help="run validation in parallel (cached)")
    parser.add_argument("--no-cache", action="store_true", help="bypass cache")
    parser.add_argument("--cache-path", default=".cache", help="cache directory")
    parser.add_argument("--max-workers", type=int, default=4, help="max workers for parallel")
    parser.add_argument("--sync", help="sync multiple env files (comma separated)")
    parser.add_argument("--exposure", action="store_true", help="scan for exposed secrets in values")
    parser.add_argument("--scan-repo", help="scan repository to detect usage of env vars (glob paths)")
    parser.add_argument("--flag-coverage", action="store_true", help="report feature-flag coverage")
    # Phase3 options
    parser.add_argument("--migrate", choices=["to-json", "to-yaml", "json-to-env", "yaml-to-env"], help="migrate env <-> json/yaml")
    parser.add_argument("--migrate-src", help="migrate source path")
    parser.add_argument("--migrate-dst", help="migrate destination path")
    parser.add_argument("--ci-init", action="store_true", help="generate CI workflow files")
    parser.add_argument("--ci-provider", choices=["github", "gitlab"], default="github", help="CI provider for ci-init")
    parser.add_argument("--ci-out", default=".github/workflows/env-check.yml", help="output path for CI template")
    parser.add_argument("--ci-overwrite", action="store_true", help="overwrite existing CI file")
    parser.add_argument("--plugin", action="append", help="load and run plugin file(s)")
    parser.add_argument("--plugins-dir", help="directory with plugins to load")
    parser.add_argument("--anomaly", action="store_true", help="run anomaly detector")
    parser.add_argument("--anomaly-no-persist", action="store_true", help="do not persist anomaly baseline")
    parser.add_argument("--drift-save", action="store_true", help="save config snapshot for drift detection")
    parser.add_argument("--drift-compare", nargs=2, metavar=("FILE1", "FILE2"), help="Compare two .env files for drift (missing keys, extra keys, differing values).")
    # migration helper
    parser.add_argument("--generate-example", action="store_true", help="generate .env.example from schema")
    args = parser.parse_args()

    if args.version:
        print(f"env-check {VERSION}")
        sys.exit(0)

    print_header(args)

    if args.drift_compare:
        from .drift_detection import compare_env_files, format_drift_report
        file1, file2 = args.drift_compare
        result = compare_env_files(file1, file2)
        print(format_drift_report(result, file1, file2))
        sys.exit(0)

    # --------------- MIGRATE (phase 3) ----------------
    if args.migrate:
        # validate src/dst
        src = args.migrate_src or args.env
        dst = args.migrate_dst
        try:
            if args.migrate == "to-json":
                migrate_mod.env_to_json(src, dst or src + ".json")
            elif args.migrate == "to-yaml":
                migrate_mod.env_to_yaml(src, dst or src + ".yaml")
            elif args.migrate == "json-to-env":
                migrate_mod.json_to_env(args.migrate_src, args.migrate_dst or ".env.migrated")
            elif args.migrate == "yaml-to-env":
                migrate_mod.yaml_to_env(args.migrate_src, args.migrate_dst or ".env.migrated")
            print("✔ Migration completed.")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: Migration failed: {e}", file=sys.stderr)
            sys.exit(2)

    # --------------- CI init ----------------
    if args.ci_init:
        try:
            ci_mod.init_ci(provider=args.ci_provider, out_path=args.ci_out, overwrite=args.ci_overwrite)
            print("✔ CI template written to", args.ci_out)
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: CI init failed: {e}", file=sys.stderr)
            sys.exit(2)

    # --------------- Load schema / env ----------------
    try:
        if args.schema:
            schema = SchemaLoader(args.schema).load()
        else:
            schema = SchemaLoader().load()
    except Exception as e:
        print(f"ERROR: Failed to load schema: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        env_vars, env_raw = load_env_file(args.env)
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: Failed to load env file: {e}", file=sys.stderr)
        sys.exit(2)

    # --------------- Linting ----------------
    linter = EnvLinter(env_raw)
    lint_issues = linter.lint()

    # --------------- Validation ----------------
    validator = SchemaValidator(schema, env_vars, strict=args.strict)
    schema_issues = validator.validate()

    # --------------- Secret analysis exposures (optional) ----------------
    exposure_issues = []
    if args.exposure:
        for k, v in env_vars.items():
            # naive exposure check: URL containing credentials or plain password-like pattern
            if "@" in v and (v.startswith("http://") or v.startswith("https://")) and "@" in v:
                exposure_issues.append({
                    "type": "exposed_credential",
                    "key": k,
                    "message": f"Value of {k} looks like a URL with embedded credentials."
                })

    # --------------- Plugins ----------------
    plugin_issues = []
    if args.plugin or args.plugins_dir:
        loaded = plugins_mod.load_plugins(plugin_paths=args.plugin, plugins_dir=args.plugins_dir)
        plugin_issues = plugins_mod.run_plugins(loaded, env_vars, schema)

    # --------------- Anomaly detection ----------------
    anomaly_notes = []
    anomaly_issues_list = []
    if args.anomaly:
        try:
            detector = SimpleAnomalyDetector(env_vars)
            issues_anom, info_anom = detector.analyze(persist_baseline_if_missing=not args.anomaly_no_persist)
            anomaly_notes.extend(info_anom)
            for ai in issues_anom:
                ai["severity"] = "warning"
                anomaly_issues_list.append(ai)
        except Exception as e:
            print(f"ERROR: anomaly detector failed: {e}", file=sys.stderr)

    # collate issues
    issues = []
    issues.extend(schema_issues)
    issues.extend(lint_issues)
    issues.extend(plugin_issues)
    issues.extend(exposure_issues)
    issues.extend(anomaly_issues_list)
    
    # --------------- Autofix ----------------
    if args.fix:
        print("\nRunning autofix...")
        fixer = AutoFixer(env_path=args.env, backup=True)
        applied, bak = fixer.apply(mode=args.fix_mode)
        if applied:
            if bak:
                print(f"✔ Autofix complete. Backup created: {bak}")
            else:
                print("✔ Autofix complete.")
        else:
            print("✔ No changes necessary.")
        sys.exit(0)
    # add severity normalization
    errors = [i for i in issues if i.get("type", "").startswith("missing") or i.get("type","") in ("pattern_mismatch","weak_secret","missing_key")]
    warnings = [i for i in issues if i not in errors]
    infos = anomaly_notes

    # JSON output
    if args.json:
        status = "fail" if errors else "success"
        result = build_json_result(status=status, file=args.env, errors=errors, warnings=warnings, infos=infos)
        print(json.dumps(result, indent=2))
        sys.exit(1 if errors else 0)

    # Minimal
    if args.minimal:
        if errors:
            print("Validation failed.")
            sys.exit(1)
        else:
            print("Validation passed.")
            sys.exit(0)

    # Human readable output
    if errors:
        print("\n❌ Validation Errors Found\n")
        # group similar to your format
        for e in errors:
            print(f"   ➤ {e.get('message')}")
        print()
    else:
        print("\n✅ All checks passed.\n")

    if warnings:
        print("⚠ Warnings")
        for w in warnings:
            print(f"   ➤ {w.get('message')}")
        print()

    if infos:
        print("ℹ Info")
        for info in infos:
            print(f"   ➤ {info}")
        print()

    # Plugins may have written files or made changes, always exit non-zero on errors
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
