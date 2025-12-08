import subprocess

def test_cli_version():
    result = subprocess.run(
        ["env-check", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "env-check" in result.stdout
