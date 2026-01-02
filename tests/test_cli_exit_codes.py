"""Test CLI exit codes - CI must trust exit codes."""
import subprocess
import sys
import os
import tempfile
from pathlib import Path


def get_fixture_path(name):
    """Get path to test fixture."""
    return Path(__file__).parent / "fixtures" / name


def run_env_check(args):
    """Run env-check and return result."""
    cmd = [sys.executable, "-m", "env_check"] + args
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result.returncode, result.stdout, result.stderr


def test_exit_code_0_valid_env():
    """Valid .env → exit code 0"""
    schema = get_fixture_path("schema.json")
    env_file = get_fixture_path("valid.env")
    
    exit_code, stdout, stderr = run_env_check([
        "--schema", str(schema),
        "--env", str(env_file)
    ])
    
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}. stderr: {stderr}"


def test_exit_code_1_missing_required():
    """Missing required key → exit code 1"""
    schema = get_fixture_path("schema.json")
    env_file = get_fixture_path("invalid.env")
    
    exit_code, stdout, stderr = run_env_check([
        "--schema", str(schema),
        "--env", str(env_file)
    ])
    
    assert exit_code == 1, f"Expected exit code 1, got {exit_code}. stderr: {stderr}"


def test_exit_code_2_invalid_schema():
    """Invalid schema → exit code 2"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{"invalid": json}')  # Invalid JSON
        invalid_schema = f.name
    
    try:
        exit_code, stdout, stderr = run_env_check([
            "--schema", invalid_schema
        ])
        
        assert exit_code == 2, f"Expected exit code 2, got {exit_code}. stderr: {stderr}"
    finally:
        os.unlink(invalid_schema)


def test_exit_code_2_schema_not_found():
    """Schema file not found → exit code 2"""
    exit_code, stdout, stderr = run_env_check([
        "--schema", "nonexistent_schema.json"
    ])
    
    assert exit_code == 2, f"Expected exit code 2, got {exit_code}. stderr: {stderr}"


def test_exit_code_3_secret_detected():
    """Secret detected → exit code 3"""
    schema = get_fixture_path("schema_with_secret.json")
    
    # Create a temporary .env file with a secret
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("DATABASE_URL=postgresql://localhost:5432/mydb\n")
        f.write("API_KEY=sk_test_123456789012345678901234567890\n")
        env_file = f.name
    
    try:
        exit_code, stdout, stderr = run_env_check([
            "--schema", str(schema),
            "--env", env_file
        ])
        
        assert exit_code == 3, f"Expected exit code 3, got {exit_code}. stderr: {stderr}"
    finally:
        os.unlink(env_file)

