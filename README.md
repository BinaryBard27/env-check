# env-check

Environment File Validator and Linter.

## Installation

```bash
pip install .
```

## Usage

```bash
env-check
env-check --json
env-check --strict
env-check --fix
env-check --schema schema/custom.json
env-check --generate-example
```

## Schema Format

```json
{
  "required": ["API_KEY", "SERVICE_URL"],
  "patterns": {
    "API_KEY": "^[A-Za-z0-9_]{32,}$"
  },
  "secret": ["API_KEY"]
}
```

## Phase 1 Features

- Schema-driven validation
- Secret analyzer (entropy + patterns)
- .env linter
- Autofix
- JSON output mode
- Warnings vs errors
- Clean CLI
