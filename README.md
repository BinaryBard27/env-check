🚀 env-check
A fast, developer-friendly environment file validator, secret scanner, and drift detector.

env-check is a CLI tool that helps developers validate, secure, and synchronize environment variables across projects.
Built for real-world workflows — simple enough for solo devs, powerful enough for CI/CD automation.

⭐ Features
🔒 Secret Scanning

Detect leaked API keys, tokens, and credentials

Entropy-based heuristics + pattern-based matching

Supports HIGH → LOW severity levels

CI-friendly JSON output (--ci)

📁 Repo-Wide Scanning

Scan your whole project for:

env files

secrets

misconfigurations

drift between environments

unused variables

Command:

env-check --scan-repo .

⚙ Configurable With .envcheck.yml

Supports:

exclude_dirs

exclude_patterns

exclude_keys

Example:

exclude_dirs:
  - node_modules
  - __pycache__
  - .git

exclude_patterns:
  - "*.pyc"
  - "*.zip"

exclude_keys:
  - DEBUG

🔍 Drift Detection

Detect differences between two env files:

env-check drift .env .env.example


Shows:

missing keys

removed keys

changed values

🧠 Anomaly Detection (Basic)

Detect suspicious env file values:

too short

too long

high entropy

empty

unusual patterns

env-check --anomaly --env .env

🎯 Severity Filtering

Keep output clean:

env-check --scan-repo . --secret-scan --severity HIGH

🛠 CI Mode

Minimal, machine-readable JSON output for pipelines:

env-check --scan-repo . --secret-scan --ci


Perfect for:

GitHub Actions

GitLab CI

Bitbucket Pipelines

📦 Installation (Local Development)

Clone the repo:

git clone https://github.com/BinaryBard27/env-check.git
cd env-check
pip install -e .


Run:

env-check --help

🧪 Example Outputs
Secret Scan (Normal Mode)
[HIGH]  .env:2 -> sk_live_...
[MEDIUM] src/app.py:10 -> 32-char hex string
[LOW]  settings.py:4 -> public URL

CI Mode
{"high":1, "medium":2, "low":5, "info":13}

🗂 Roadmap
Phase 6 (Upcoming)

Packaging (PyPI release)

Improved README (full version)

GitHub Actions CI

Drift diff preview (--diff)

Template generator (generate-example)

Usage checker (detect unused variables)

🤝 Contributing

Contributions welcome! Create a pull request or open an issue.

📄 License

MIT License.
