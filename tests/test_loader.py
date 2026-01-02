from env_check.cli import load_env_file

def test_load_env_file_basic():
    env = load_env_file("tests/fixtures/sample.env")
    assert env["API_KEY"] == "abc123"
    assert env["PORT"] == "8080"
    assert env["DEBUG"] == "true"
