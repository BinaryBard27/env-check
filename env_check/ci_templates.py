import os

GITHUB_ACTION_TEMPLATE = """name: Env Check

on:
  push:
  pull_request:

jobs:
  env-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      - name: Install
        run: pip install -e .
      - name: Run env-check
        run: python -m env_check --no-cache --strict
"""

def write_github_action(out_dir=".github/workflows"):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "env-check.yml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(GITHUB_ACTION_TEMPLATE)
    return path
