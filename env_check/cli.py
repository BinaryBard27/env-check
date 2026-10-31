import argparse
import os
import sys
import json
import shutil
from typing import Dict, Any

from env_check.config_loader import load_config
from env_check.validator import ValidatorEngine
from env_check.output.table import print_table
from env_check import __version__

# Values that look like placeholders rather than real secrets. Flagged
# secrets with these values fail the run (exit code 3); others are reported
# but do not fail the run.
WEAK_SECRET_VALUES = {
    "", "changeme", "change_me", "changeme123", "change-me",
    "placeholder", "xxx", "xxxx", "xxxxxx",
    "todo", "fixme", "none", "null", "nil",
    "undefined", "notset", "not-set", "missing", "redacted",
    "sk_test_", "yourkeyhere", "your-key-here", "your-api-key",
    "dummy", "test", "fake", "secret",
}

WEAK_SECRET_PREFIXES = ("pk_test_", "ghp_", "gho_", "ghs_")


def is_weak_secret(value: str) -> bool:
    """True if a secret value looks like a placeholder rather than a real secret."""
    v = value.strip().strip("'\"")
    low = v.lower()
    if not low or low in WEAK_SECRET_VALUES:
        return True
    if low.startswith(WEAK_SECRET_PREFIXES):
        return True
    # All one repeated character, e.g. "aaaaaaaaaa"
    if len(v) >= 4 and len(set(v)) == 1:
        return True
    return False


def load_env_file(path: str) -> Dict[str, str]:
    """Load environment variables from a .env file."""
    env = {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"Environment file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse KEY=VALUE format
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                env[key] = value
    return env


def detect_secrets(schema: Dict[str, Any], env: Dict[str, str]) -> list:
    """Detect potential secrets in environment variables based on schema 'secret: true' flags.

    A flagged variable is reported when it has a value, or when it is required
    and missing. Each finding carries a 'weak' flag: True when the value looks
    like a placeholder (empty, 'changeme', test-mode key, ...).
    """
    findings = []
    for var, rules in schema.items():
        if not (isinstance(rules, dict) and rules.get("secret", False)):
            continue
        value = env.get(var, "")
        if not value and not rules.get("required", False):
            continue
        findings.append({
            "variable": var,
            "reason": "Flagged as secret in schema",
            "weak": is_weak_secret(value),
        })
    return findings


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="env-check",
        description="env-check: validate environment variables using schema enforcement, drift detection, and secret scanning."
    )
    parser.add_argument(
        "--schema", "-s",
        help="Path to schema file (JSON or YAML)"
    )
    parser.add_argument(
        "--env", "-e",
        help="Path to .env file (default: use os.environ)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--fail-on-secrets",
        action="store_true",
        help="Fail the run if any secret-flagged variable has a non-empty value "
             "(default: only fail on empty/placeholder secret values)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically add missing required keys to .env file (with backup)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"env-check {__version__}"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    
    # Determine schema file path
    schema_path = args.schema or "envcheck.yml"
    if not os.path.exists(schema_path):
        # Try common alternatives
        for alt in ["envcheck.yaml", "schema.json", "schema.yml", "schema.yaml"]:
            if os.path.exists(alt):
                schema_path = alt
                break
        else:
            print(f"Schema file not found: {schema_path}", file=sys.stderr)
            print("Use --schema to specify a schema file, or create envcheck.yml", file=sys.stderr)
            return 2  # Schema error
    
    # Load schema
    try:
        schema = load_config(schema_path)
    except Exception as e:
        print(f"Failed to load schema: {e}", file=sys.stderr)
        return 2  # Schema error
    
    # Load environment variables
    if args.env:
        try:
            env = load_env_file(args.env)
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            return 2  # Schema/file error
        except Exception as e:
            print(f"Failed to load environment file: {e}", file=sys.stderr)
            return 2  # Schema/file error
    else:
        env = os.environ.copy()
    
    # Handle --fix flag
    if args.fix:
        if not args.env:
            print("--fix requires --env to specify the .env file to modify", file=sys.stderr)
            return 2
        
        # Find missing required keys
        missing = []
        for var, rules in schema.items():
            if isinstance(rules, dict) and rules.get("required", False):
                if var not in env or not env[var]:
                    missing.append(var)
        
        if missing:
            # Create backup (never overwrite an existing one)
            backup_path = args.env + ".backup"
            try:
                counter = 1
                while os.path.exists(backup_path):
                    backup_path = f"{args.env}.backup.{counter}"
                    counter += 1
                shutil.copyfile(args.env, backup_path)
                
                # Append missing keys with their default value, or a TODO marker
                with open(args.env, "a", encoding="utf-8") as f:
                    f.write("\n# Added by env-check --fix\n")
                    for var in missing:
                        default = schema[var].get("default", "") if isinstance(schema[var], dict) else ""
                        if default:
                            f.write(f"{var}={default}\n")
                        else:
                            f.write(f"# TODO {var}=<value>  # required by schema, set a real value\n")
                
                print(f"Added {len(missing)} missing required keys to {args.env} (backup: {backup_path})", file=sys.stderr)
            except Exception as e:
                print(f"Failed to fix .env file: {e}", file=sys.stderr)
                return 2
        else:
            print("No missing required keys found", file=sys.stderr)
        # Continue with validation after fix
    
    # Run validation
    try:
        engine = ValidatorEngine(schema, env)
        results = engine.run()
    except Exception as e:
        print(f"Validation error: {e}", file=sys.stderr)
        return 2  # Schema/validation error
    
    # Check for secrets
    secret_findings = detect_secrets(schema, env)
    
    # Output results
    if args.format == "json":
        output_data = {
            "results": [r.to_dict() for r in results],
            "secrets": secret_findings
        }
        print(json.dumps(output_data, indent=2))
    else:
        print_table(results)
        if secret_findings:
            weak = [f for f in secret_findings if f["weak"]]
            label = "⚠️  Secret risk detected:" if weak else "ℹ️  Secret-flagged variables:"
            print(label, file=sys.stderr)
            for finding in secret_findings:
                if finding["weak"]:
                    print(f"  {finding['variable']}: weak/placeholder value ({finding['reason']})", file=sys.stderr)
                else:
                    print(f"  {finding['variable']}: {finding['reason']} (value present, not shown)", file=sys.stderr)
    
    # Compute exit code:
    # 0 = success
    # 1 = validation errors (or warnings with --strict)
    # 2 = schema errors (already handled above)
    # 3 = weak/placeholder secret value (or any secret with --fail-on-secrets)
    exit_code = 0
    
    # Check validation results: engine maps ERROR/CRITICAL to 1/2 -> both become 1
    validation_exit_code = engine.summarize_exit_code(results)
    if validation_exit_code > 0:
        exit_code = 1
    
    # Apply --strict: treat warnings as errors
    if args.strict:
        has_warnings = any(not r.ok and r.severity.name in ("WARN", "WARNING") for r in results)
        if has_warnings:
            exit_code = 1
    
    # Check secrets: weak values always fail; healthy secrets only with --fail-on-secrets
    weak_findings = [f for f in secret_findings if f["weak"]]
    if weak_findings or (args.fail_on_secrets and secret_findings):
        exit_code = 3
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
