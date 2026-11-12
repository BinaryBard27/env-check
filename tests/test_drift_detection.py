"""Comprehensive test suite for Environment Drift Detection in env-check."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from env_check.drift import (
    DriftDetector,
    DriftIssue,
    EnvironmentComparison,
    DriftReport,
    is_sensitive_variable,
    mask_secret_value,
    mask_sensitive_name,
    safe_compare_secrets,
)
from env_check.severity import Severity


def run_env_check(args, cwd=None):
    """Run env-check via python -m env_check and return (code, stdout, stderr)."""
    cmd = [sys.executable, "-m", "env_check"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or Path(__file__).parent.parent,
    )
    return result.returncode, result.stdout, result.stderr


def make_tmp_file(content: str, suffix: str = ".env") -> str:
    """Create a temporary file with given content and return its path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


# ==============================================================================
# 1. Identical Environment Files
# ==============================================================================

def test_identical_environments_in_sync():
    """Identical environment files should produce no drift and exit code 0."""
    base = make_tmp_file("PORT=8080\nHOST=localhost\nDEBUG=false\n")
    comp = make_tmp_file("PORT=8080\nHOST=localhost\nDEBUG=false\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", base, "--compare", comp])
        assert code == 0
        assert "No drift detected" in stdout or "in sync" in stdout
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 2. Missing Variables
# ==============================================================================

def test_missing_variables_detected():
    """Variables present in base but missing in compare should be flagged."""
    base = make_tmp_file("DATABASE_URL=postgres://localhost\nPORT=5432\nCACHE_ENABLED=true\n")
    comp = make_tmp_file("PORT=5432\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", base, "--compare", comp, "--format", "json"])
        assert code == 1
        data = json.loads(stdout)
        missing = [i for i in data["environments"][0]["issues"] if i["type"] == "missing_variable"]
        missing_vars = {m["variable"] for m in missing}
        assert "DATABASE_URL" in missing_vars
        assert "CACHE_ENABLED" in missing_vars
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 3. Unexpected Additional Variables
# ==============================================================================

def test_unexpected_variables_detected():
    """Variables present in compare but not in base should be flagged as unexpected."""
    base = make_tmp_file("PORT=8080\n")
    comp = make_tmp_file("PORT=8080\nEXTRA_DEBUG=true\nLEFTOVER_VAR=123\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", base, "--compare", comp, "--format", "json"])
        data = json.loads(stdout)
        unexpected = [i for i in data["environments"][0]["issues"] if i["type"] == "unexpected_variable"]
        unexpected_vars = {u["variable"] for u in unexpected}
        assert "EXTRA_DEBUG" in unexpected_vars
        assert "LEFTOVER_VAR" in unexpected_vars
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 4. Inconsistent Values
# ==============================================================================

def test_different_values_detected():
    """Different values between base and compare should be detected."""
    base = make_tmp_file("TIMEOUT=30\nSERVICE_URL=https://api.internal\n")
    comp = make_tmp_file("TIMEOUT=60\nSERVICE_URL=https://api.external\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", base, "--compare", comp, "--format", "json"])
        data = json.loads(stdout)
        diffs = [i for i in data["environments"][0]["issues"] if i["type"] == "value_mismatch"]
        diff_vars = {d["variable"] for d in diffs}
        assert "TIMEOUT" in diff_vars
        assert "SERVICE_URL" in diff_vars
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 5. Inconsistent Types
# ==============================================================================

def test_different_data_types_with_schema():
    """Type mismatches declared by schema should be detected as ERROR."""
    schema = make_tmp_file(json.dumps({
        "PORT": {"type": "int"},
        "IS_ACTIVE": {"type": "bool"}
    }), suffix=".json")
    base = make_tmp_file("PORT=8080\nIS_ACTIVE=true\n")
    comp = make_tmp_file("PORT=not_a_number\nIS_ACTIVE=maybe\n")
    try:
        code, stdout, stderr = run_env_check([
            "drift", "--base", base, "--compare", comp, "--schema", schema, "--format", "json"
        ])
        assert code == 1
        data = json.loads(stdout)
        type_issues = [i for i in data["environments"][0]["issues"] if i["type"] == "type_mismatch"]
        vars_with_type_mismatch = {t["variable"] for t in type_issues}
        assert "PORT" in vars_with_type_mismatch
        assert "IS_ACTIVE" in vars_with_type_mismatch
    finally:
        os.unlink(schema)
        os.unlink(base)
        os.unlink(comp)


def test_inferred_data_types_without_schema():
    """Without schema, inferred types from base (int, bool) should flag type errors."""
    base = make_tmp_file("PORT=8080\n")
    comp = make_tmp_file("PORT=banana\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", base, "--compare", comp, "--format", "json"])
        assert code == 1
        data = json.loads(stdout)
        type_issues = [i for i in data["environments"][0]["issues"] if i["type"] == "type_mismatch"]
        assert len(type_issues) >= 1
        assert type_issues[0]["variable"] == "PORT"
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 6. Empty Variables
# ==============================================================================

def test_empty_variables_detected():
    """Empty values where non-empty values are expected should be flagged."""
    schema = make_tmp_file(json.dumps({
        "DB_PASS": {"non_empty": True},
        "APP_NAME": {"required": True}
    }), suffix=".json")
    base = make_tmp_file("DB_PASS=somepassword\nAPP_NAME=my_app\n")
    comp = make_tmp_file("DB_PASS=\nAPP_NAME=\n")
    try:
        code, stdout, stderr = run_env_check([
            "drift", "--base", base, "--compare", comp, "--schema", schema, "--format", "json"
        ])
        assert code == 1
        data = json.loads(stdout)
        empty_issues = [i for i in data["environments"][0]["issues"] if i["type"] == "empty_value"]
        empty_vars = {e["variable"] for e in empty_issues}
        assert "DB_PASS" in empty_vars
        assert "APP_NAME" in empty_vars
    finally:
        os.unlink(schema)
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 7. Secret Masking & Protection (Critical Requirement)
# ==============================================================================

def test_secret_values_never_printed_or_in_json():
    """Secret values must NEVER appear in stdout, stderr, or JSON reports."""
    secret_raw_1 = "sk_live_supersecrettoken_1111111111"
    secret_raw_2 = "sk_live_supersecrettoken_2222222222"
    pass_raw = "super_secure_db_pass_12345"

    schema = make_tmp_file(json.dumps({
        "API_KEY": {"secret": True, "type": "str"},
        "DATABASE_PASSWORD": {"secret": True, "type": "str"},
    }), suffix=".json")
    base = make_tmp_file(f"API_KEY={secret_raw_1}\nDATABASE_PASSWORD={pass_raw}\n")
    comp = make_tmp_file(f"API_KEY={secret_raw_2}\nDATABASE_PASSWORD={pass_raw}\n")

    try:
        # Test 1: JSON format
        code_json, stdout_json, stderr_json = run_env_check([
            "drift", "--base", base, "--compare", comp, "--schema", schema, "--format", "json"
        ])
        assert secret_raw_1 not in stdout_json
        assert secret_raw_2 not in stdout_json
        assert pass_raw not in stdout_json
        assert secret_raw_1 not in stderr_json
        assert secret_raw_2 not in stderr_json
        assert pass_raw not in stderr_json

        data = json.loads(stdout_json)
        for issue in data["environments"][0]["issues"]:
            if issue["variable"] == "API_KEY":
                assert issue["is_secret"] is True
                assert issue["base_value"] == "[MASKED]"
                assert issue["compare_value"] == "[MASKED]"
                assert secret_raw_1 not in issue["message"]
                assert secret_raw_2 not in issue["message"]

        # Test 2: Table format
        code_tbl, stdout_tbl, stderr_tbl = run_env_check([
            "drift", "--base", base, "--compare", comp, "--schema", schema, "--format", "table"
        ])
        assert secret_raw_1 not in stdout_tbl
        assert secret_raw_2 not in stdout_tbl
        assert pass_raw not in stdout_tbl
        assert secret_raw_1 not in stderr_tbl
        assert secret_raw_2 not in stderr_tbl
        assert pass_raw not in stderr_tbl
    finally:
        os.unlink(schema)
        os.unlink(base)
        os.unlink(comp)


def test_heuristic_secret_detection_without_schema():
    """Variables with sensitive names (e.g. *_SECRET, *_PASSWORD) are masked even without schema."""
    token1 = "verysecretbearer_token_val_1"
    token2 = "verysecretbearer_token_val_2"
    base = make_tmp_file(f"AUTH_TOKEN={token1}\n")
    comp = make_tmp_file(f"AUTH_TOKEN={token2}\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", base, "--compare", comp, "--format", "json"])
        assert token1 not in stdout
        assert token2 not in stdout
        data = json.loads(stdout)
        assert data["environments"][0]["issues"][0]["is_secret"] is True
        assert data["environments"][0]["issues"][0]["base_value"] == "[MASKED]"
        assert data["environments"][0]["issues"][0]["compare_value"] == "[MASKED]"
    finally:
        os.unlink(base)
        os.unlink(comp)


def test_mask_names_flag():
    """--mask-names flag masks sensitive variable names."""
    base = make_tmp_file("DATABASE_PASSWORD=secretval1\n")
    comp = make_tmp_file("DATABASE_PASSWORD=secretval2\n")
    try:
        code, stdout, stderr = run_env_check([
            "drift", "--base", base, "--compare", comp, "--mask-names", "--format", "json"
        ])
        data = json.loads(stdout)
        var = data["environments"][0]["issues"][0]["variable"]
        assert "DATABASE_PASSWORD" not in var
        assert "*" in var
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 8. Multiple Comparison Files
# ==============================================================================

def test_multiple_comparison_files():
    """Can compare base against multiple environments simultaneously."""
    base = make_tmp_file("PORT=8080\nMODE=dev\n")
    staging = make_tmp_file("PORT=8080\nMODE=staging\n")
    prod = make_tmp_file("PORT=80\nMODE=prod\nEXTRA=1\n")

    try:
        code, stdout, stderr = run_env_check([
            "drift", "--base", base, "--compare", staging, "--compare", prod, "--format", "json"
        ])
        data = json.loads(stdout)
        assert data["summary"]["total_environments"] == 2
        assert len(data["environments"]) == 2
        env_names = {e["environment"] for e in data["environments"]}
        assert staging in env_names
        assert prod in env_names
    finally:
        os.unlink(base)
        os.unlink(staging)
        os.unlink(prod)


# ==============================================================================
# 9. Invalid File Paths
# ==============================================================================

def test_invalid_base_path():
    """Missing base file should exit with code 2 and helpful error."""
    comp = make_tmp_file("PORT=8080\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", "nonexistent_base.env", "--compare", comp])
        assert code == 2
        assert "Base environment file not found" in stderr
    finally:
        os.unlink(comp)


def test_invalid_compare_path():
    """Missing compare file should exit with code 2 and helpful error."""
    base = make_tmp_file("PORT=8080\n")
    try:
        code, stdout, stderr = run_env_check(["drift", "--base", base, "--compare", "nonexistent_comp.env"])
        assert code == 2
        assert "Comparison environment file not found" in stderr
    finally:
        os.unlink(base)


# ==============================================================================
# 10. Invalid Schemas
# ==============================================================================

def test_invalid_schema_file_path():
    """Missing schema file should exit with code 2."""
    base = make_tmp_file("PORT=8080\n")
    comp = make_tmp_file("PORT=8080\n")
    try:
        code, stdout, stderr = run_env_check([
            "drift", "--base", base, "--compare", comp, "--schema", "nonexistent_schema.json"
        ])
        assert code == 2
        assert "Schema file not found" in stderr
    finally:
        os.unlink(base)
        os.unlink(comp)


def test_unparseable_schema_syntax():
    """Malformed schema file should exit with code 2."""
    schema = make_tmp_file("{invalid json here}", suffix=".json")
    base = make_tmp_file("PORT=8080\n")
    comp = make_tmp_file("PORT=8080\n")
    try:
        code, stdout, stderr = run_env_check([
            "drift", "--base", base, "--compare", comp, "--schema", schema
        ])
        assert code == 2
        assert "Failed to load schema" in stderr
    finally:
        os.unlink(schema)
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 11. Strict Mode
# ==============================================================================

def test_strict_mode_escalates_warnings():
    """With --strict, warnings (like unexpected variables) escalate to exit code 1."""
    base = make_tmp_file("PORT=8080\n")
    comp = make_tmp_file("PORT=8080\nEXTRA_VAL=foo\n")
    try:
        # Without --strict, unexpected variable is a warning (exit code 0)
        code_normal, stdout_normal, _ = run_env_check(["drift", "--base", base, "--compare", comp])
        assert code_normal == 0

        # With --strict, warning causes exit code 1
        code_strict, stdout_strict, _ = run_env_check(["drift", "--base", base, "--compare", comp, "--strict"])
        assert code_strict == 1
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 12. --fail-on Threshold Flag
# ==============================================================================

def test_fail_on_flag():
    """--fail-on sets the threshold severity for exiting with code 1."""
    base = make_tmp_file("PORT=8080\n")
    comp = make_tmp_file("PORT=8080\nEXTRA_VAR=1\n")  # Generates WARN
    try:
        # Fail on warning -> exit 1
        code_warn, _, _ = run_env_check(["drift", "--base", base, "--compare", comp, "--fail-on", "warning"])
        assert code_warn == 1

        # Fail on error -> exit 0 because only WARN is present
        code_err, _, _ = run_env_check(["drift", "--base", base, "--compare", comp, "--fail-on", "error"])
        assert code_err == 0
    finally:
        os.unlink(base)
        os.unlink(comp)


# ==============================================================================
# 13. Schema Consistency Rules (same_value, allow_different_values, allowed_in)
# ==============================================================================

def test_schema_same_value_rule():
    """Variable with 'same_value: true' must have identical values across envs."""
    schema = make_tmp_file(json.dumps({
        "APP_VERSION": {"same_value": True},
        "ENVIRONMENT": {"allow_different_values": True}
    }), suffix=".json")
    base = make_tmp_file("APP_VERSION=1.0.0\nENVIRONMENT=base\n")
    comp_ok = make_tmp_file("APP_VERSION=1.0.0\nENVIRONMENT=staging\n")
    comp_bad = make_tmp_file("APP_VERSION=2.0.0\nENVIRONMENT=staging\n")

    try:
        # Same value -> passes
        code_ok, _, _ = run_env_check([
            "drift", "--base", base, "--compare", comp_ok, "--schema", schema
        ])
        assert code_ok == 0

        # Different value on same_value: true -> fails
        code_bad, stdout_bad, _ = run_env_check([
            "drift", "--base", base, "--compare", comp_bad, "--schema", schema, "--format", "json"
        ])
        assert code_bad == 1
        data = json.loads(stdout_bad)
        issues = data["environments"][0]["issues"]
        assert any(i["variable"] == "APP_VERSION" and i["type"] == "value_mismatch" for i in issues)
        # ENVIRONMENT allowed different values -> not flagged as an error
        assert not any(i["variable"] == "ENVIRONMENT" for i in issues)
    finally:
        os.unlink(schema)
        os.unlink(base)
        os.unlink(comp_ok)
        os.unlink(comp_bad)


def test_schema_allowed_in_rule():
    """Variable with 'allowed_in: [prod]' is flagged if present in staging."""
    schema = make_tmp_file(json.dumps({
        "PROD_ONLY_FEATURE": {"allowed_in": ["prod", ".env.prod"]}
    }), suffix=".json")
    base = make_tmp_file("PORT=8080\n")
    # File named staging should violate allowed_in: ["prod"]
    staging_file = make_tmp_file("PORT=8080\nPROD_ONLY_FEATURE=true\n", suffix=".staging.env")

    try:
        code, stdout, _ = run_env_check([
            "drift", "--base", base, "--compare", staging_file, "--schema", schema, "--format", "json"
        ])
        assert code == 1
        data = json.loads(stdout)
        rule_violations = [i for i in data["environments"][0]["issues"] if i["type"] == "rule_violation"]
        assert len(rule_violations) == 1
        assert rule_violations[0]["variable"] == "PROD_ONLY_FEATURE"
    finally:
        os.unlink(schema)
        os.unlink(base)
        os.unlink(staging_file)


# ==============================================================================
# 14. Weak Secret Exit Code 3
# ==============================================================================

def test_weak_secret_causes_exit_code_3():
    """Weak or placeholder secret in compare env triggers exit code 3."""
    schema = make_tmp_file(json.dumps({
        "API_KEY": {"secret": True}
    }), suffix=".json")
    base = make_tmp_file("API_KEY=sk_live_9f8a7b6c5d4e3f2a1b0c\n")
    comp = make_tmp_file("API_KEY=changeme\n")

    try:
        code, stdout, stderr = run_env_check([
            "drift", "--base", base, "--compare", comp, "--schema", schema, "--format", "json"
        ])
        assert code == 3
        data = json.loads(stdout)
        weak_issues = [i for i in data["environments"][0]["issues"] if i["type"] == "weak_secret"]
        assert len(weak_issues) >= 1
    finally:
        os.unlink(schema)
        os.unlink(base)
        os.unlink(comp)
