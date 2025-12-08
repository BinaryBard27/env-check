# 🚀 What This Tool Solves

Misconfigured `.env` files break builds, cause silent bugs, and waste hours.
**env-check** eliminates that by:

*   **Enforcing strict schema validation**
*   **Catching missing/empty/invalid values early**
*   **Providing CI-safe JSON output**
*   **Supporting custom rule plugins**
*   **Speeding repeat runs using content hashing cache**

You run it → it tells you exactly what’s wrong → CI fails fast → no surprises in production.

## 🔧 Key Features

### ✔ Robust Rule Engine
*   `required`, `choices`, `regex`, `int`, `float`, `bool`, `path`, `url`, `range`, and more.
*   Severity levels: `error`, `warning`, `info`.

### ✔ Plugin System (Phase 6)
Extend validation using Python modules:
*   Add custom validators
*   Override defaults
*   Auto-load via flags or entry points

### ✔ CI Mode
*   JSON structured output
*   Pipeline-friendly exit codes
*   Zero noise formatting

### ✔ Smart Caching
*   Skips validating unchanged env files.
*   Invalidates automatically when schema or plugins change.

### ✔ Multi-Source Configuration
*   `envcheck.toml`
*   Rule overrides
*   Project-specific plugins

## 📦 Installation

**Stable:**
```bash
pip install env-check
```

**Development:**
```bash
git clone https://github.com/BinaryBard27/env-check
cd env-check
pip install -e .
```

## 🧪 Quick Start

**Validate .env**
```bash
env-check validate .env
```

**Use a schema file**
```bash
env-check validate .env --config envcheck.toml
```

**CI-mode JSON output**
```bash
env-check validate .env --ci
```

**Load custom plugins**
```bash
env-check validate .env --plugins validators/my_plugin.py
```

## 🧩 Plugin Example

**`my_plugin.py`**
```python
from env_check.plugins import register_validator

@register_validator("is_port")
def is_port(value: str) -> bool:
    return value.isdigit() and 1 <= int(value) <= 65535
```

**`envcheck.toml`**
```toml
[variables.PORT]
rules = ["required", "is_port"]
```

**Run:**
```bash
env-check validate .env --plugins my_plugin.py
```

## 📑 Schema Example (`envcheck.toml`)

```toml
[ENV]
MODE = "development"

[variables]

[variables.DATABASE_URL]
rules = ["required", "url"]

[variables.API_KEY]
rules = ["required", "regex:^sk-[A-Za-z0-9]{20}$"]

[variables.PORT]
rules = ["required", "int", "range:1024-65535"]
severity = "warning"
```

## 📝 Output Examples

### Terminal Output
```text
❌ DATABASE_URL missing (required)
⚠️ PORT out of recommended range
✔ MODE valid
```

### CI JSON
```json
{
  "errors": [
    {"key": "DATABASE_URL", "rule": "required", "message": "missing"}
  ],
  "warnings": [
    {"key": "PORT", "rule": "range", "message": "expected 1024-65535"}
  ],
  "status": "failed"
}
```

## 📁 Project Structure
```text
env_check/
│── __init__.py
│── cli.py                 # Command-line interface
│── main.py                # Validation orchestration
│── core/                  # Rule engine + execution logic
│── config_loader.py       # Schema loader (TOML)
│── plugins.py             # Plugin registry + hooks
│── output/                # Output formatters (Human + CI)
│── cache.py               # Cache engine
│── ci.py                  # CI helpers
│── migrate.py             # Legacy config migration
```

## 🔚 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Passed |
| 1 | Validation failed |
| 2 | Internal error |

## 🧰 Development

**Run locally:**
```bash
python -m env_check validate .env
```

**Tests:**
```bash
pytest -q
```

**Linting:**
```bash
ruff check .
```

## 🤝 Contributing

Contributions are welcome — especially new validators, plugin patterns, and rule enhancements.

1.  Fork
2.  Branch
3.  Build
4.  Test
5.  PR
