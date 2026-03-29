# env-check

> A strict, CI-ready environment variable validator with schema enforcement, drift detection, and secret scanning.

[![CI](https://github.com/BinaryBard27/env-check/actions/workflows/ci.yml/badge.svg)](https://github.com/BinaryBard27/env-check/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Stop broken .env files, silent misconfigurations, and leaked secrets before they reach production.**

---

 Why env-check exists

Most projects rely on `.env` files that:

- Drift between environments** — dev, staging, and prod configurations diverge
- Miss required variables** — critical settings are missing until runtime
- Contain invalid values** — wrong formats, out-of-range numbers, invalid URLs
- Accidentally leak secrets** — API keys and passwords committed to repos  
- Fail silently until runtime** — errors only surface in production

Existing tools validate presence.
env-check validates correctness, consistency, and safety.

What env-check does

-Validates .env files against a schema** — enforce structure and types
-Enforces required keys and patterns** — regex, enums, ranges, types
-Detects environment drift** — compare configurations across environments
-Scans for high-risk secrets** — heuristic detection of leaked credentials
-Produces CI-friendly output** — JSON format for automation
-Fails fast with meaningful exit codes** — integrate seamlessly into pipelines

>This is prevention, not cleanup.

---

##  Installation

### Standard Installation

```bash
pip install envcheck-cli
```

### Recommended for CI / Global Usage

```bash
pipx install envcheck-cli
```

### Development Installation

```bash
git clone https://github.com/BinaryBard27/env-check
cd env-check
pip install -e .
```

---

##  Quick Start

### Basic Validation

Validate your `.env` file against a schema:

```bash
env-check --schema schema.json --env .env
```

### Strict Mode (Recommended)

Treat warnings as errors and fail on any issues:

```bash
env-check --strict
```

### CI-Friendly JSON Output

Get machine-readable output for automation:

```bash
env-check --format json
```

### Autofix Missing Keys

Automatically add missing required keys (with backup):

```bash
env-check --fix
```

### Using Configuration File

Use a YAML or JSON configuration file:

```bash
env-check --config envcheck.yml
```

---

##  Schema Examples

### JSON Schema Format

```json
{
  "PORT": {
    "required": true,
    "pattern": "^[0-9]+$",
    "type": "int",
    "range": "1024-65535"
  },
  "MODE": {
    "required": true,
    "enum": ["dev", "staging", "prod"]
  },
  "API_KEY": {
    "required": true,
    "secret": true,
    "pattern": "^sk-[A-Za-z0-9]{20,}$"
  },
  "DATABASE_URL": {
    "required": true,
    "type": "url",
    "non_empty": true
  },
  "LOG_LEVEL": {
    "required": false,
    "enum": ["DEBUG", "INFO", "WARNING", "ERROR"],
    "default": "INFO"
  }
}
```

### YAML Configuration Format

```yaml
variables:
  PORT:
    required: true
    type: int
    range: "1024-65535"
  
  MODE:
    required: true
    enum: ["dev", "staging", "prod"]
  
  API_KEY:
    required: true
    secret: true
    pattern: "^sk-[A-Za-z0-9]{20,}$"
  
  DATABASE_URL:
    required: true
    type: url
    non_empty: true
```

Schema capabilities:

- Enforces presence — required variables must exist
- Prevents invalid values — type checking, regex patterns, enums
- Flags sensitive keys — secret scanning for leaked credentials
- Range validation — numeric ranges for ports, timeouts, etc.
- File existence — validate file paths exist
- URL validation — ensure URLs are properly formatted

---

##  Available Validators

env-check supports multiple validation types:

| Validator | Description | Example |
|-----------|-------------|---------|
| `required` | Variable must be present | `"required": true` |
| `type` | Type checking (int, float, bool, url) | `"type": "int"` |
| `pattern` | Regex pattern matching | `"pattern": "^[0-9]+$"` |
| `enum` | Value must be in allowed list | `"enum": ["dev", "prod"]` |
| `range` | Numeric range validation | `"range": "1-100"` |
| `non_empty` | Value cannot be empty string | `"non_empty": true` |
| `file_exists` | File path must exist | `"file_exists": true` |
| `secret` | Flag for secret scanning | `"secret": true` |

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Validate Environment

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install env-check
        run: pip install env-check
      
      - name: Validate environment
        run: env-check --strict --format json
```

### GitLab CI

```yaml
validate_env:
  image: python:3.9
  before_script:
    - pip install env-check
  script:
    - env-check --strict --format json
```

### CircleCI

```yaml
jobs:
  validate:
    docker:
      - image: cimg/python:3.9
    steps:
      - checkout
      - run: pip install env-check
      - run: env-check --strict --format json
```

If validation fails:

-  CI fails immediately
-  Deployment stops
-  Broken config never ships

---

## 📊 Exit Codes

| Code | Meaning | When It Occurs |
|------|---------|----------------|
| `0` | Validation passed | All checks pass |
| `1` | Validation errors | Missing required vars, invalid values |
| `2` | Schema errors | Invalid schema file, parsing errors |
| `3` | Secret risk detected | Potential secrets found in .env |

> **Designed for automation** — use exit codes in your CI/CD pipelines.

---

## How env-check Compares

| Feature | env-check | check-env | envalid (Node) |
|---------|-----------|-----------|----------------|
| Schema Validation | ✅ | ✅ | ✅ |
| Drift Detection | ✅ | ❌ | ❌ |
| Secret Scanning | ✅ | ❌ | ❌ |
| CI Output (JSON) | ✅ | ❌ | ❌ |
| Type Validation | ✅ | ❌ | ✅ |
| Range Validation | ✅ | ❌ | ❌ |
| File Existence | ✅ | ❌ | ❌ |

**env-check focuses on preventing configuration failure, not just detecting missing keys.**

---

##  Security & Limitations

### Secret Detection

env-check provides basic secret detection through schema flags. Understanding its limitations is critical for security-conscious teams.

**What env-check does:**
- Flags environment variables marked with `secret: true` in your schema
- Returns exit code 3 when secrets are detected
- Provides preventive checks before deployment

**What env-check does NOT do:**
- **No automatic secret scanning** — Only variables explicitly marked `secret: true` in the schema are flagged
- **No pattern matching** — Does not automatically detect secret patterns or signatures
- **Not a forensic tool** — Cannot detect secrets already committed or leaked
- **Not a replacement for dedicated scanners** — Should be used alongside tools like TruffleHog, GitGuardian, or GitHub's secret scanning

**Important limitations:**
-  **Heuristic-based** — Detection relies on schema flags, not content analysis
-  **False positives possible** — Variables marked as secrets may not actually contain sensitive data
-  **Manual configuration required** — You must explicitly mark variables as secrets in your schema
-  **Preventive only** — Designed to catch mistakes before deployment, not to audit existing repositories

**Example:**
```json
{
  "API_KEY": {
    "required": true,
    "secret": true
  }
}
```
Only variables with `"secret": true` will trigger exit code 3. Variables without this flag are not checked for secret patterns.

### Drift Detection

**What is drift?**
Environment drift occurs when configuration files (`.env` files) diverge between environments (development, staging, production). For example:
- Development has `PORT=3000` but production has `PORT=8080`
- Staging includes `DEBUG=true` but production is missing it
- Different API endpoints are configured across environments

**How env-check detects drift:**
env-check validates each environment file against a shared schema. It does not automatically compare files between environments, but ensures all environments conform to the same validation rules.

**What env-check does:**
- Validates `.env` files against a schema to ensure required variables exist
- Enforces consistent validation rules across all environments
- Catches missing or invalid variables before deployment

**What env-check does NOT do:**
- **No automatic comparison** — Does not directly compare `.env.dev` vs `.env.prod`
- **No drift visualization** — Does not generate diff reports between environments
- **No inference** — Does not guess which variables should differ between environments

**Example workflow:**
```bash
# Validate development environment
env-check --schema schema.json --env .env.dev

# Validate staging environment  
env-check --schema schema.json --env .env.staging

# Validate production environment
env-check --schema schema.json --env .env.prod --strict
```

Each environment is validated independently. To detect actual drift, you would need to run env-check on each environment file and compare results, or use additional tooling.

**Example drift detection output:**
If production is missing a required variable that exists in development:
```bash
$ env-check --schema schema.json --env .env.prod
DATABASE_URL | MISSING   | CRITICAL | Required variable missing
```
This indicates drift (missing variable), but env-check does not automatically identify which other environments have this variable.

### Best Practices

-  **Use it early in the pipeline** — validate before deployment
-  **Combine with other tools** — use alongside dedicated secret scanners
-  **Review flagged items** — investigate all secret warnings
-  **Keep schemas updated** — maintain schema as your config evolves

---

##  Usage Examples

### Example 1: Basic Validation

```bash
# Create schema.json
cat > schema.json << EOF
{
  "DATABASE_URL": {
    "required": true,
    "type": "url"
  },
  "API_KEY": {
    "required": true,
    "secret": true
  }
}
EOF

# Validate
env-check --schema schema.json --env .env
```

### Example 2: Strict Mode with JSON Output

```bash
env-check --strict --format json > validation-results.json
```

### Example 3: Multiple Environment Validation

```bash
# Validate dev environment
env-check --schema schema.json --env .env.dev

# Validate production environment
env-check --schema schema.json --env .env.prod --strict
```

---

##  Troubleshooting

### Common Issues

**Issue:** `Config file not found: envcheck.yml`

**Solution:** Create a configuration file or specify the path:
```bash
env-check --config path/to/your/config.yml
```

**Issue:** Schema validation fails

**Solution:** Check your schema format. Ensure it's valid JSON or YAML:
```bash
# Validate JSON
python -m json.tool schema.json

# Validate YAML
python -c "import yaml; yaml.safe_load(open('schema.yml'))"
```

**Issue:** False positives in secret scanning

**Solution:** Review flagged variables and adjust your schema if needed. Secret scanning is heuristic-based and may require tuning.

---

## 🤝 Contributing

Contributions are welcome! We appreciate your help in making env-check better.

Please see [CONTRIBUTING.md](CONTRIBUTING.md) before submitting PRs.

### Ways to Contribute

- 🐛 Report bugs
- 💡 Suggest new features
- 📝 Improve documentation
- 🔧 Add new validators
- 🧪 Write tests

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

- **Repository:** [https://github.com/BinaryBard27/env-check](https://github.com/BinaryBard27/env-check)
- **Issues:** [https://github.com/BinaryBard27/env-check/issues](https://github.com/BinaryBard27/env-check/issues)
- **PyPI:** [https://pypi.org/project/env-check/](https://pypi.org/project/env-check/)

---

**Made with ❤️ for developers who care about configuration safety.**
