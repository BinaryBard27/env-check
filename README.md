# env-check

A strict, CI-ready environment variable validator. It checks your `.env` values against a schema — type, presence, pattern, range, enum, and more — **before** your application starts, and returns CI-friendly exit codes.

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

## CLI Reference

```
Usage: env-check [OPTIONS]

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
| `0`  | All validations passed (warnings allowed without `--strict`) |
| `1`  | One or more validation errors, or warnings with `--strict` |
| `2`  | Schema or env file not found / unparseable |
| `3`  | A secret-flagged variable has a **weak or placeholder value** (e.g. empty, `changeme`, repeated characters), or any secret-flagged value with `--fail-on-secrets` |

Exit code `3` takes precedence over `1`.

### Output

**Table (default):**

```
VARIABLE       STATUS   SEVERITY  DETAIL
DATABASE_URL   OK       INFO      Value: postgresql://localhost:5432/mydb
PORT           OK       INFO      Value: 8080
MODE           INVALID  ERROR     enum: value not in allowed set: ['dev', 'staging', 'prod']
```

**JSON (`--format json`)** — only JSON goes to stdout, safe for pipelines:

```json
{
  "results": [
    { "variable": "PORT", "ok": true, "severity": "INFO", "detail": "Value: 8080" },
    { "variable": "MODE", "ok": false, "severity": "ERROR", "detail": "enum: value not in allowed set: ['dev', 'staging', 'prod']" }
  ],
  "secrets": [
    { "variable": "API_KEY", "reason": "Flagged as secret in schema", "weak": true }
  ]
}
```

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
| `secret` | All | Truthy: the variable is reported as a secret (never printed). See [Secrets](#secrets) |

Unknown rule keys produce a warning (exit code stays `0` unless `--strict`).

Missing required variables are **always** CRITICAL. Validation errors and criticals both map to exit code `1` in the CLI.

## Secrets

Variables with `"secret": true` are never printed with their values. Behavior:

- **Healthy value present** → reported (`ℹ️` in table mode, `"weak": false` in JSON), run **passes**.
- **Weak/placeholder value** (empty, `changeme`, `undefined`, `null`, repeated characters like `aaaaaaaa`, …) → run **fails with exit code 3**.
- **`--fail-on-secrets`** → any present value fails with exit code 3, for maximum strictness.
- Missing **required** secrets are reported as weak (empty).

## `--fix`

With `--fix --env .env`, missing required keys are appended to the `.env` file:

- a `.backup` copy is made first (`.backup.1`, `.backup.2`, … if one already exists — backups are never overwritten),
- keys with a `default` in the schema get that default,
- keys without a default get a `# TODO VAR=<value>` comment instead of a fake empty value.

Validation then continues on the updated file.

---

## CI/CD Integration

**GitHub Actions:**

```yaml
- name: Validate environment config
  run: env-check --schema envcheck.json --env .env.prod --format json
```

Exit code `1` or `3` fails the step automatically; pipe the JSON output to any log aggregator.

To validate the runner's own environment (where secrets come from GitHub secrets, not a file):

```yaml
- name: Validate runner environment
  run: env-check --schema envcheck.json
```

---

## Python API

The engine is also usable as a library:

```python
from env_check.validator import ValidatorEngine, ValidationResult

schema = {
    "PORT": {"required": True, "type": "int", "min": 1024, "max": 65535},
    "MODE": ["dev", "staging", "prod"],   # shorthand enum
}

engine = ValidatorEngine(schema, env=os.environ)
results = engine.run()
exit_code = engine.summarize_exit_code(results)  # 0, 1 or 2

for r in results:
    print(r.variable, r.ok, r.severity.name, r.detail)
```

---

## Development

```bash
pip install -e ".[dev]"   # or: pip install -e . && pip install pytest
pytest -q
```

- `env_check/` — the package: CLI, config loader, validation engine, pluggable validators, output
- `tests/` — unit + subprocess-based CLI tests (exit codes, JSON output, secrets)
- `experimental/` — standalone prototypes (drift detection, anomaly detection, repo scanning, plugins). **Not part of the package, not imported, not tested.**
- `examples/` — sample schemas and env files (all values are fake)

## License

MIT — see [LICENSE](LICENSE).
