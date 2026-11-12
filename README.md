# env-check

A strict, CI-ready environment variable validator. It checks your `.env` values against a schema — type, presence, pattern, range, enum, and more — **before** your application starts, detects configuration drift across environments, and returns CI-friendly exit codes.

`env-check` does not modify your environment and does not load variables into your process. It validates, reports, and exits with a code. You handle loading separately.

---

## Installation

```bash
pip install env-check   # package name: envcheck-cli
```

**Requirements:** Python 3.9+

---

## Quick Start

**1. Write a schema** (JSON or YAML) mapping each variable to its rules:

```json
// envcheck.json
{
  "DATABASE_URL": {
    "required": true,
    "type": "str",
    "non_empty": true
  },
  "PORT": {
    "required": true,
    "type": "int",
    "min": 1024,
    "max": 65535
  },
  "MODE": {
    "required": true,
    "enum": ["dev", "staging", "prod"]
  },
  "API_KEY": {
    "secret": true,
    "pattern": "^sk_[a-zA-Z0-9]+$"
  }
}
```

**2. Run validation:**

```bash
env-check --schema envcheck.json --env .env
```

By default the schema file is `envcheck.yml` in the current directory, and the source is `os.environ` if no `--env` file is given. If `--env` is omitted the process environment itself is checked — useful in CI where the runner already has the variables.

---

## Environment Drift Detection

`env-check drift` compares multiple environment files against a base environment (source of truth) to detect configuration divergence before deployment:

```bash
env-check drift \
  --base examples/.env.base \
  --compare examples/.env.staging \
  --compare examples/.env.prod
```

### What it detects

1. **Missing variables:** Variables defined in the base environment (or required by schema) that are absent in a target environment.
2. **Unexpected variables:** Variables found in a target environment that are absent from base and undeclared in schema.
3. **Empty values:** Variables that are empty when non-empty values are required.
4. **Type inconsistencies:** Variables whose values violate declared types or diverge from inferred base types (e.g. integer vs string).
5. **Value divergences:** Inconsistent values across environments when values are required to match.
6. **Consistency rule violations:** Violations of cross-environment rules such as `same_value`, `allowed_in`, or `required_in`.

### Drift CLI Reference

```
Usage: env-check drift [OPTIONS]

Options:
  --base, -b      PATH   Path to base .env file (source of truth). Required.
  --compare, -c   PATH   Path to comparison .env file. Can be specified multiple
                         times or with multiple file arguments. Required.
  --schema, -s    PATH   Path to schema file (JSON or YAML).
  --format        [json|table]
                         Output format. Default: table
  --strict               Treat warnings (e.g. unexpected variables) as errors
  --fail-on       [warning|warn|error|critical]
                         Fail run if maximum issue severity meets or exceeds threshold
  --mask-names           Mask sensitive variable names in output
```

### Drift Example Output

**Table (default):**

```
              Environment Drift Report (Base: examples/.env.base)              
+-----------------------------------------------------------------------------+
| ENVIRONMENT       | VARIABLE | ISSUE TYPE      | SEVERITY | DETAIL          |
|-------------------+----------+-----------------+----------+-----------------|
| examples/.env.stg | API_KEY  | unexpected_var  | WARN     | Unexpected ...  |
| examples/.env.stg | BAZ      | missing_variab  | ERROR    | Variable 'BAZ'  |
| examples/.env.prd | BAZ      | value_mismatch  | WARN     | Value for 'BAZ' |
+-----------------------------------------------------------------------------+

Summary: 2 environment(s) checked, 3 drift issue(s) detected (0 critical, 1 error, 2 warning, 0 info).
```

**JSON (`--format json`):**

```json
{
  "base": "examples/.env.base",
  "schema": "examples/envcheck.json",
  "environments": [
    {
      "environment": "examples/.env.staging",
      "status": "drift_detected",
      "issues_count": 2,
      "issues": [
        {
          "variable": "API_KEY",
          "type": "unexpected_variable",
          "severity": "WARN",
          "message": "Unexpected variable 'API_KEY' present in 'examples/.env.staging' but not in base",
          "environment": "examples/.env.staging",
          "is_secret": true,
          "base_value": null,
          "compare_value": "[MASKED]"
        }
      ]
    }
  ],
  "summary": {
    "total_environments": 1,
    "total_issues": 1,
    "has_drift": true,
    "max_severity": "WARN",
    "exit_code": 0
  }
}
```

---

## CLI Reference

```
Usage: env-check [OPTIONS] [COMMAND]

Commands:
  drift                  Detect configuration drift across multiple environment files

Options:
  --schema, -s   PATH   Path to schema file (JSON or YAML).
                        Default: envcheck.yml (falls back to envcheck.yaml,
                        schema.json, schema.yml, schema.yaml)
  --env, -e      PATH   Path to .env file to check. Default: os.environ
  --strict               Treat warnings (e.g. unknown rule keys) as errors
  --fail-on-secrets      Fail the run if any secret-flagged variable has a
                         value (default: only weak/placeholder values fail)
  --fix                  Append missing required keys to the .env file
                         (with backup). Requires --env
  --format       [json|table]
                         Output format. Default: table
  --version              Show version and exit
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | All validations passed / environments in sync (warnings allowed without `--strict`) |
| `1`  | One or more validation errors, drift exceeding failure threshold, or warnings with `--strict` |
| `2`  | Schema or env file not found / unparseable |
| `3`  | A secret-flagged variable has a **weak or placeholder value** (e.g. empty, `changeme`, repeated characters), or any secret-flagged value with `--fail-on-secrets` |

Exit code `3` takes precedence over `1`.

---

## Schema Rules

| Rule | Applies to | Description |
|------|-----------|-------------|
| `required` | All | Fails (CRITICAL) if the variable is missing or empty |
| `type` | All | One of `int`/`integer`, `float`, `bool`/`boolean`, `str`/`string`. Unknown type names produce a warning |
| `regex` | All | The value must fully match this pattern |
| `pattern` | All | Accepted alias for `regex` |
| `enum` | All | The value must be one of the listed values. Shorthand: `VAR: ["a", "b"]` means `{"enum": ["a", "b"]}` |
| `range` | Numeric | Object with `min` and/or `max` |
| `min` / `max` | Numeric | Shorthand for `range`; merged with an explicit `range` if both are present |
| `file_exists` | All | Truthy: the value must be an existing path |
| `non_empty` | All | Truthy: the value must not be empty or whitespace-only |
| `severity` | All | `info`, `warn`/`warning`, `error`, `critical` — severity used when a rule fails (default `error`; missing required is always `critical`) |
| `secret` | All | Truthy: the variable is treated as a secret (never printed in plaintext). See [Secrets](#secrets) |
| `same_value` | Drift | Truthy: variable must have the exact same value across all environments |
| `allow_different_values` | Drift | Truthy: variable is permitted to have differing values across environments |
| `allowed_in` | Drift | List of environment names/patterns where variable is permitted (e.g. `["prod"]`) |
| `required_in` | Drift | List of environment names where variable is strictly required (e.g. `["prod", "staging"]` or `["all"]`) |

Unknown rule keys produce a warning (exit code stays `0` unless `--strict`).

---

## Secrets & Safe Masking

Security is enforced unconditionally across both validation and drift detection:

- **Never printed in plaintext:** Sensitive variables and schema-declared secrets (`"secret": true` or matching sensitive patterns like `*_KEY`, `*_SECRET`, `*_PASSWORD`, `*_TOKEN`) are masked with `[MASKED]`.
- **Never included in JSON reports:** Values of sensitive variables are replaced with `[MASKED]` in JSON outputs.
- **Timing-safe comparison:** Internal secret comparisons utilize `hmac.compare_digest` to prevent timing attacks.
- **Weak value detection:** Placeholders (such as `changeme`, `placeholder`, `undefined`, `xxxx`) fail immediately with exit code 3.
- **Never written to cache or logs:** Secrets are evaluated in memory and never persisted unmasked.

---

## CI/CD Integration

**GitHub Actions - Drift Detection:**

```yaml
- name: Check Environment Drift
  run: |
    env-check drift \
      --base examples/.env.base \
      --compare examples/.env.staging \
      --compare examples/.env.prod \
      --schema examples/envcheck.json \
      --fail-on error \
      --format json
```

**GitHub Actions - Single Environment Validation:**

```yaml
- name: Validate environment config
  run: env-check --schema envcheck.json --env .env.prod --format json
```

---

## Python API

`env-check` is also usable programmatically:

```python
# Validation
from env_check.validator import ValidatorEngine

schema = {
    "PORT": {"required": True, "type": "int", "min": 1024, "max": 65535},
    "MODE": ["dev", "staging", "prod"],
}

engine = ValidatorEngine(schema, env=os.environ)
results = engine.run()
exit_code = engine.summarize_exit_code(results)

# Drift Detection
from env_check.drift import DriftDetector

detector = DriftDetector(schema=schema, strict=False)
report = detector.compare_files(
    base_file="examples/.env.base",
    compare_files=["examples/.env.staging", "examples/.env.prod"]
)
exit_code = report.compute_exit_code()
report_dict = report.to_dict()
```

---

## Development

```bash
pip install -e ".[dev]"   # or: pip install -e . && pip install pytest
pytest -q
```

- `env_check/` — the package: CLI, drift detection, config loader, validation engine, validators, output
- `tests/` — unit, drift detection, and CLI subprocess tests
- `examples/` — sample schemas and env files (all values are fake)

## License

MIT — see [LICENSE](LICENSE).
