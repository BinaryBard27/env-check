# env-check

A pre-deployment environment validation tool. Validates type correctness, required presence, and environment-specific rules before your application starts — not after it crashes.

---

## The Problem

Most `.env` loaders (dotenv, python-dotenv) only check if the file exists and load its values into the process. They do not validate those values. Common failures that reach production:

- `PORT=banana` — present, but not a valid integer
- `DATABASE_URL=` — present, but empty
- `API_KEY=undefined` — present, but a literal string "undefined"

These pass a presence check. They fail at runtime — usually deep inside application logic, far from where the bad config was loaded.

**env-check validates before execution.** If your config is broken, your app refuses to start. The error is explicit, structured, and caught at startup — not in production.

---

## How It Differs from Other Tools

| Feature                  | env-check        | dotenv    | envalid   | python-dotenv |
|--------------------------|------------------|-----------|-----------|---------------|
| Philosophy               | Gatekeeper       | Loader    | Validator | Loader        |
| Type enforcement         | Yes              | No        | Yes       | No            |
| Empty value detection    | Yes              | No        | Partial   | No            |
| Environment-specific rules | Yes            | No        | Partial   | No            |
| CI/CD-friendly output    | JSON + exit code | Noisy     | Partial   | Silent errors |
| Auto-loads env into app  | No (by design)   | Yes       | Yes       | Yes           |

env-check does not load your environment. It validates it. You handle loading separately — this keeps the tool composable and safe for pipelines.

---

## Installation

```bash
pip install env-check
```

**Requirements:** Python 3.8+

---

## Quick Start

**1. Define a schema**

```json
// env.schema.json
{
  "PORT": {
    "type": "integer",
    "required": true,
    "range": [1024, 65535]
  },
  "DATABASE_URL": {
    "type": "url",
    "required": true,
    "environments": ["production", "staging"]
  },
  "DEBUG": {
    "type": "boolean",
    "default": false
  },
  "API_KEY": {
    "type": "string",
    "required": true,
    "disallow": ["undefined", "null", ""]
  }
}
```

**2. Run validation in your app entrypoint**

```python
from env_check import EnvGuard

guard = EnvGuard(schema="env.schema.json")
guard.protect()  # Raises EnvValidationError if config is invalid. App exits here.

# Your application logic starts only after this point.
```

**3. Or run from the CLI**

```bash
env-check --schema env.schema.json --env production
```

---

## CLI Reference

```
Usage: env-check [OPTIONS]

Options:
  --schema  PATH       Path to the schema file (JSON or YAML). [required]
  --file    PATH       Path to the .env file. Defaults to .env
  --env     TEXT       Environment name (e.g. production, staging, dev)
  --output  [json|text] Output format. Defaults to text
  --strict             Fail on any unknown keys not defined in schema
  --help               Show this message and exit.
```

**Exit codes:**
- `0` — All validations passed
- `1` — One or more validations failed
- `2` — Schema or config file not found

**JSON output example (for CI pipelines):**

```json
{
  "status": "failed",
  "errors": [
    { "key": "PORT", "error": "Expected integer, got 'banana'" },
    { "key": "API_KEY", "error": "Value is disallowed: 'undefined'" }
  ]
}
```

---

## Python API Reference

### `EnvGuard(schema, env_file=".env", environment=None, strict=False)`

| Parameter     | Type   | Description |
|---------------|--------|-------------|
| `schema`      | `str`  | Path to your schema file (JSON or YAML) |
| `env_file`    | `str`  | Path to the `.env` file. Defaults to `.env` |
| `environment` | `str`  | Current environment name for env-specific rules |
| `strict`      | `bool` | Fail on keys present in `.env` but not in schema |

### `guard.protect()`

Runs validation. Raises `EnvValidationError` with a detailed report if any rule fails. Does not return a value — either passes or halts execution.

### `guard.validate()`

Same as `protect()` but returns a result object instead of raising. Useful if you want to handle the error yourself.

```python
result = guard.validate()
if not result.valid:
    for error in result.errors:
        print(error.key, error.message)
```

---

## Schema Rules Reference

| Rule          | Types supported         | Description |
|---------------|--------------------------|-------------|
| `type`        | `string`, `integer`, `float`, `boolean`, `url`, `email`, `json` | Enforces value type |
| `required`    | All                      | Fails if key is missing or empty |
| `default`     | All                      | Used when key is absent (only if not `required`) |
| `disallow`    | `string`                 | List of values that are explicitly rejected |
| `range`       | `integer`, `float`       | `[min, max]` bounds check |
| `pattern`     | `string`                 | Regex the value must match |
| `environments`| All                      | Rule applies only to specified environments |

---

## CI/CD Integration

**GitHub Actions example:**

```yaml
- name: Validate environment config
  run: env-check --schema env.schema.json --env production --output json
```

Pipe the JSON output to any log aggregator or slack notifier. Exit code `1` will fail the pipeline automatically.

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push and open a pull request

Please open an issue before submitting large changes.

---

## License

MIT — see [LICENSE](LICENSE) for details.