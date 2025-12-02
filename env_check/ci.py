"""
ci.py - generate CI workflow templates
"""
import os
from pathlib import Path

GITHUB_TEMPLATE = """name: env-check

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
          python-version: "3.10"
      - name: Install deps
        run: pip install -r requirements.txt || true
      - name: Run env-check
        run: python -m env_check --json --strict
"""

GITLAB_TEMPLATE = """stages:
  - test

env_check:
  image: python:3.10
  stage: test
  script:
    - pip install -r requirements.txt || true
    - python -m env_check --json --strict
"""

def init_ci(provider: str = "github", out_path: str = ".github/workflows/env-check.yml", overwrite: bool = False):
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and not overwrite:
        raise FileExistsError(str(out))

    if provider == "github":
        content = GITHUB_TEMPLATE
    elif provider == "gitlab":
        content = GITLAB_TEMPLATE
    else:
        raise ValueError("unsupported provider")

    out.write_text(content, encoding="utf-8")
    return str(out)
