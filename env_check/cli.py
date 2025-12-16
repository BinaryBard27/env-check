import argparse
import sys
import os

# try import loader from existing loader/config_loader
try:
    from .loader import load_config
except Exception:
    try:
        from .config_loader import load_config
    except Exception:
        def load_config(path):
            # minimal fallback: try YAML or JSON via PyYAML or json
            import yaml, json
            with open(path, "r", encoding="utf-8") as fh:
                if path.endswith(".yml") or path.endswith(".yaml"):
                    return yaml.safe_load(fh)
                return json.load(fh)

from .validator import ValidatorEngine
from .output.table import print_table
from .output.json_output import render_json

def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="env-check", description="env-check: validate environment variables using config")
    p.add_argument("--config", "-c", default="envcheck.yml", help="path to config file (yaml/json)")
    p.add_argument("--json", action="store_true", help="output JSON")
    p.add_argument("--ci", action="store_true", help="CI mode (machine friendly)")
    p.add_argument("--strict", action="store_true", help="treat warnings as errors")
    return p.parse_args(argv)

def main(argv=None):
    args = parse_args(argv)
    if not os.path.exists(args.config):
        print(f"Config file not found: {args.config}", file=sys.stderr)
        return 2

    try:
        cfg = load_config(args.config) or {}
    except Exception as e:
        print(f"Failed to load config: {e}", file=sys.stderr)
        return 2

    # config expected to be mapping variable -> rule dict
    engine = ValidatorEngine(cfg)
    results = engine.run()

    if args.json:
        print(render_json(results))
    else:
        print_table(results)

    # compute exit code
    code = engine.summarize_exit_code(results)
    if args.strict and code == 0:
        # if strict, convert WARN -> ERROR (we use severity levels)
        highest = max((r.severity for r in results if not r.ok), default=None)
        if highest and highest < 30 and highest >= 20:
            code = 1
    return code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
