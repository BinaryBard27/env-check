"""Regression tests for the 1.0.2 fixes:
- 'pattern' works as an alias for 'regex'
- unknown type names produce a warning, not a silent pass
- range on non-numeric values reports a type failure when a type rule exists
- secrets: healthy values are reported but pass; weak/placeholder values fail (exit 3)
- --strict escalates unknown-rule-key warnings to exit 1
- --fix uses timestamped-safe backups and TODO markers for keys without defaults
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from env_check.validator import ValidatorEngine
from env_check.cli import is_weak_secret


def get_fixture_path(name):
    return Path(__file__).parent / "fixtures" / name


def run_env_check(args, cwd=None):
    cmd = [sys.executable, "-m", "env_check"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or Path(__file__).parent.parent,
    )
    return result.returncode, result.stdout, result.stderr


def write_tmp(content, suffix):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


# ---------------------------------------------------------------- pattern alias


def test_pattern_rule_enforced():
    """A value violating the 'pattern' rule must fail validation."""
    cfg = {"KEY": {"pattern": "^sk_[a-zA-Z0-9]+$"}}
    results = ValidatorEngine(cfg, env={"KEY": "bad-key"}).run()
    assert results[0].ok is False
    assert "pattern" in results[0].detail or "regex" in results[0].detail


def test_pattern_rule_passes():
    cfg = {"KEY": {"pattern": "^sk_[a-zA-Z0-9]+$"}}
    results = ValidatorEngine(cfg, env={"KEY": "sk_abc123"}).run()
    assert results[0].ok is True


# ------------------------------------------------------- unknown type warning


def test_unknown_type_is_warning_not_failure():
    cfg = {"KEY": {"type": "url", "required": True}}
    results = ValidatorEngine(cfg, env={"KEY": "anything"}).run()
    assert results[0].ok is False
    assert results[0].severity.name == "WARN"
    assert "Unknown type" in results[0].detail


# ------------------------------------------------------------ range/type combo


def test_range_on_non_numeric_with_type_reports_type():
    cfg = {"PORT": {"type": "int", "min": 1, "max": 10}}
    results = ValidatorEngine(cfg, env={"PORT": "banana"}).run()
    assert results[0].ok is False
    assert "not a valid int" in results[0].detail


# ------------------------------------------------------------------- secrets


def test_weak_secret_values():
    weak = ["", "changeme", "PLACEHOLDER", "undefined", "aaaaaaaaaa", "xxxx",
            "pk_test_abc"]
    for v in weak:
        assert is_weak_secret(v), f"{v!r} should be weak"
    healthy = ["sk_live_9f8a7b6c5d4e3f2a1b0c", "S3cur3!Passphrase", "prod-key-2026"]
    for v in healthy:
        assert not is_weak_secret(v), f"{v!r} should not be weak"


def test_healthy_secret_passes_run():
    """A healthy secret value is reported but does not fail the run."""
    schema = write_tmp(json.dumps({
        "API_KEY": {"required": True, "secret": True},
        "PORT": {"required": True, "type": "int", "min": 1, "max": 65535},
    }), ".json")
    env_file = write_tmp("API_KEY=sk_live_9f8a7b6c5d4e3f2a1b0c\nPORT=8080\n", ".env")
    try:
        exit_code, stdout, stderr = run_env_check(
            ["--schema", schema, "--env", env_file, "--format", "json"]
        )
        assert exit_code == 0
        data = json.loads(stdout)
        # Healthy secret: reported, not weak, and does not fail the run
        assert data["secrets"] == [
            {"variable": "API_KEY", "reason": "Flagged as secret in schema", "weak": False}
        ]
        # Table mode must report the healthy secret without failing
        exit_code2, stdout2, stderr2 = run_env_check(
            ["--schema", schema, "--env", env_file]
        )
        assert exit_code2 == 0
        assert "not shown" in stderr2
    finally:
        os.unlink(schema)
        os.unlink(env_file)


def test_weak_secret_fails_run():
    """A weak/placeholder secret value fails the run with exit code 3."""
    schema = write_tmp(json.dumps({
        "API_KEY": {"required": True, "secret": True},
        "PORT": {"required": True, "type": "int", "min": 1, "max": 65535},
    }), ".json")
    env_file = write_tmp("API_KEY=changeme\nPORT=8080\n", ".env")
    try:
        exit_code, stdout, stderr = run_env_check(
            ["--schema", schema, "--env", env_file, "--format", "json"]
        )
        assert exit_code == 3
        data = json.loads(stdout)
        assert data["secrets"][0]["weak"] is True
    finally:
        os.unlink(schema)
        os.unlink(env_file)


def test_fail_on_secrets_flag():
    """--fail-on-secrets makes even healthy flagged secrets fail with exit 3."""
    schema = write_tmp(json.dumps({
        "API_KEY": {"required": True, "secret": True},
        "PORT": {"required": True, "type": "int", "min": 1, "max": 65535},
    }), ".json")
    env_file = write_tmp("API_KEY=sk_live_9f8a7b6c5d4e3f2a1b0c\nPORT=8080\n", ".env")
    try:
        exit_code, stdout, stderr = run_env_check(
            ["--schema", schema, "--env", env_file, "--fail-on-secrets"]
        )
        assert exit_code == 3
    finally:
        os.unlink(schema)
        os.unlink(env_file)


def test_weak_secret_exit_3_precedes_validation_error():
    """A weak secret wins over validation errors (exit 3, not 1)."""
    schema = write_tmp(json.dumps({
        "API_KEY": {"required": True, "secret": True},
        "PORT": {"required": True, "type": "int", "min": 1024, "max": 65535},
    }), ".json")
    env_file = write_tmp("API_KEY=changeme\nPORT=80\n", ".env")
    try:
        exit_code, stdout, stderr = run_env_check(
            ["--schema", schema, "--env", env_file]
        )
        assert exit_code == 3
    finally:
        os.unlink(schema)
        os.unlink(env_file)


# ------------------------------------------------------------------- --strict


def test_strict_escalates_unknown_key_warning():
    schema = write_tmp(json.dumps({"PORT": {"required": True, "type": "int", "bogus": 1}}), ".json")
    env_file = write_tmp("PORT=8080\n", ".env")
    try:
        exit_code, stdout, stderr = run_env_check(
            ["--schema", schema, "--env", env_file, "--strict"]
        )
        assert exit_code == 1
    finally:
        os.unlink(schema)
        os.unlink(env_file)


# -------------------------------------------------------------------- --fix


def test_fix_appends_defaults_and_todo():
    schema = write_tmp(json.dumps({
        "A": {"required": True, "default": "1"},
        "B": {"required": True},
    }), ".json")
    env_file = write_tmp("# empty\n", ".env")
    try:
        exit_code, stdout, stderr = run_env_check(["--schema", schema, "--env", env_file, "--fix"])
        assert "backup:" in stderr
        with open(env_file) as f:
            content = f.read()
        assert "A=1" in content
        assert "# TODO B=" in content
        # No default for B, so no fake empty value was appended
        assert "\nB=" not in content
    finally:
        os.unlink(schema)
        os.unlink(env_file)


def test_fix_backup_never_overwritten():
    schema = write_tmp(json.dumps({"A": {"required": True}}), ".json")
    env_file = write_tmp("", ".env")
    try:
        run_env_check(["--schema", schema, "--env", env_file, "--fix"])
        first_backup = env_file + ".backup"
        assert os.path.exists(first_backup)
        # Second run must not clobber the first backup
        run_env_check(["--schema", schema, "--env", env_file, "--fix"])
        assert os.path.exists(first_backup)
        assert os.path.exists(env_file + ".backup.1")
        with open(first_backup) as f:
            assert f.read() == ""
    finally:
        for p in (schema, env_file, env_file + ".backup", env_file + ".backup.1"):
            if os.path.exists(p):
                os.unlink(p)
