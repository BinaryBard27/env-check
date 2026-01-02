"""Test JSON output - JSON output must never break consumers."""
import subprocess
import sys
import json
from pathlib import Path


def get_fixture_path(name):
    """Get path to test fixture."""
    return Path(__file__).parent / "fixtures" / name


def run_env_check_json(args):
    """Run env-check with JSON output and return parsed JSON."""
    cmd = [sys.executable, "-m", "env_check"] + args + ["--format", "json"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    if result.returncode not in [0, 1, 3]:  # Allow success, validation error, or secret
        raise RuntimeError(f"env-check failed with exit code {result.returncode}: {result.stderr}")
    
    return result.stdout, result.stderr


def test_json_output_is_valid():
    """JSON output must be valid JSON."""
    schema = get_fixture_path("schema.json")
    env_file = get_fixture_path("valid.env")
    
    stdout, stderr = run_env_check_json([
        "--schema", str(schema),
        "--env", str(env_file)
    ])
    
    # Should parse as valid JSON
    try:
        data = json.loads(stdout)
        assert isinstance(data, dict), "JSON output should be a dictionary"
    except json.JSONDecodeError as e:
        raise AssertionError(f"JSON output is invalid: {e}\nOutput: {stdout}")


def test_json_has_required_keys():
    """Required top-level keys must exist."""
    schema = get_fixture_path("schema.json")
    env_file = get_fixture_path("valid.env")
    
    stdout, stderr = run_env_check_json([
        "--schema", str(schema),
        "--env", str(env_file)
    ])
    
    data = json.loads(stdout)
    
    assert "results" in data, "JSON output must have 'results' key"
    assert isinstance(data["results"], list), "'results' must be a list"
    
    # Check that results have expected structure
    if data["results"]:
        result = data["results"][0]
        assert "variable" in result, "Each result must have 'variable' key"
        assert "ok" in result, "Each result must have 'ok' key"
        assert "severity" in result, "Each result must have 'severity' key"
        assert "detail" in result, "Each result must have 'detail' key"


def test_json_no_stdout_noise():
    """No random stdout noise - only JSON on stdout."""
    schema = get_fixture_path("schema.json")
    env_file = get_fixture_path("valid.env")
    
    stdout, stderr = run_env_check_json([
        "--schema", str(schema),
        "--env", str(env_file)
    ])
    
    # stdout should be parseable JSON (no extra text)
    try:
        json.loads(stdout)
    except json.JSONDecodeError:
        raise AssertionError(f"stdout contains non-JSON content: {stdout}")
    
    # Check that stdout starts with { or [ (valid JSON start)
    stripped = stdout.strip()
    assert stripped.startswith("{") or stripped.startswith("["), "stdout should start with JSON"


def test_json_deterministic_structure():
    """Deterministic structure - same input produces same structure."""
    schema = get_fixture_path("schema.json")
    env_file = get_fixture_path("valid.env")
    
    # Run twice
    stdout1, stderr1 = run_env_check_json([
        "--schema", str(schema),
        "--env", str(env_file)
    ])
    
    stdout2, stderr2 = run_env_check_json([
        "--schema", str(schema),
        "--env", str(env_file)
    ])
    
    data1 = json.loads(stdout1)
    data2 = json.loads(stdout2)
    
    # Structure should be the same
    assert set(data1.keys()) == set(data2.keys()), "JSON structure should be deterministic"
    assert len(data1["results"]) == len(data2["results"]), "Number of results should be deterministic"
    
    # Results should have same variables (order may vary, but structure should be same)
    vars1 = {r["variable"] for r in data1["results"]}
    vars2 = {r["variable"] for r in data2["results"]}
    assert vars1 == vars2, "Result variables should be deterministic"


def test_json_includes_secrets_when_present():
    """JSON output includes secrets array when secrets are detected."""
    schema = get_fixture_path("schema_with_secret.json")
    
    # Create .env with secret
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("DATABASE_URL=postgresql://localhost:5432/mydb\n")
        f.write("API_KEY=sk_test_123456789012345678901234567890\n")
        env_file = f.name
    
    try:
        stdout, stderr = run_env_check_json([
            "--schema", str(schema),
            "--env", env_file
        ])
        
        data = json.loads(stdout)
        assert "secrets" in data, "JSON output must have 'secrets' key when secrets are present"
        assert isinstance(data["secrets"], list), "'secrets' must be a list"
    finally:
        os.unlink(env_file)

