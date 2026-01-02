import argparse
import sys
import os
import json
from typing import Dict, Any

from env_check.config_loader import load_config
from env_check.validator import ValidatorEngine
from env_check.output.table import print_table
from env_check import __version__


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
    """Detect potential secrets in environment variables based on schema 'secret: true' flags."""
    findings = []
    for var, rules in schema.items():
        if isinstance(rules, dict) and rules.get("secret", False):
            value = env.get(var)
            if value:
                findings.append({
                    "variable": var,
                    "reason": "Flagged as secret in schema"
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
            # Create backup
            backup_path = args.env + ".backup"
            try:
                with open(args.env, "r", encoding="utf-8") as f:
                    backup_content = f.read()
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(backup_content)
                
                # Append missing keys
                with open(args.env, "a", encoding="utf-8") as f:
                    f.write("\n# Added by env-check --fix\n")
                    for var in missing:
                        default = schema[var].get("default", "") if isinstance(schema[var], dict) else ""
                        f.write(f"{var}={default}\n")
                
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
            print("\n⚠️  Secret risk detected:", file=sys.stderr)
            for finding in secret_findings:
                print(f"  {finding['variable']}: {finding['reason']}", file=sys.stderr)
    
    # Compute exit code according to spec:
    # 0 = success
    # 1 = validation errors
    # 2 = schema errors (already handled above)
    # 3 = secret risk detected
    exit_code = 0
    
    # Check for secrets (exit code 3 takes precedence)
    if secret_findings:
        exit_code = 3
        return exit_code
    
    # Check validation results
    # validator returns: 0=OK, 1=ERROR, 2=CRITICAL
    # We map both ERROR and CRITICAL to validation error (1)
    validation_exit_code = engine.summarize_exit_code(results)
    if validation_exit_code > 0:
        exit_code = 1
    
    # Apply --strict: treat warnings as errors
    if args.strict:
        has_warnings = any(not r.ok and r.severity.name in ("WARN", "WARNING") for r in results)
        if has_warnings:
            exit_code = 1
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
