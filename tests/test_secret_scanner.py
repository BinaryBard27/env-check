from env_check.secret_heuristics import run_secret_scan

def test_secret_scanner_runs():
    # The function should not crash and must return a list
    results = run_secret_scan("tests/fixtures")

    assert isinstance(results, list), "Secret scan should return a list"

    # Every result must contain required keys
    if results:
        for item in results:
            assert "pattern" in item
            assert "value_snippet" in item
            assert "severity" in item
