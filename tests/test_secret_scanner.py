from env_check.cli import detect_secrets

def test_secret_scanner_detection():
    # Setup connection
    schema = {
        "AWS_SECRET_ACCESS_KEY": {
            "required": True,
            "secret": True
        },
        "DB_PASSWORD": {
            "secret": True
        },
        "PUBLIC_VAR": {
            "secret": False
        }
    }
    
    env = {
        "AWS_SECRET_ACCESS_KEY": "AKIA1234567890",
        "DB_PASSWORD": "supersecretpassword",
        "PUBLIC_VAR": "public_value"
    }

    findings = detect_secrets(schema, env)

    assert isinstance(findings, list)
    assert len(findings) == 2

    flagged_vars = {f["variable"] for f in findings}
    assert "AWS_SECRET_ACCESS_KEY" in flagged_vars
    assert "DB_PASSWORD" in flagged_vars
    assert "PUBLIC_VAR" not in flagged_vars

    # Healthy values are not flagged as weak
    by_var = {f["variable"]: f for f in findings}
    assert by_var["AWS_SECRET_ACCESS_KEY"]["weak"] is False
    assert by_var["DB_PASSWORD"]["weak"] is False

def test_secret_scanner_no_findings():
    schema = {"VAR": {"secret": False}}
    env = {"VAR": "some-value"}

    findings = detect_secrets(schema, env)
    assert len(findings) == 0

def test_secret_scanner_weak_values_flagged():
    schema = {"VAR": {"secret": True}}
    env = {"VAR": "changeme"}

    findings = detect_secrets(schema, env)
    assert len(findings) == 1
    assert findings[0]["weak"] is True

def test_secret_scanner_missing_value_is_weak():
    """A missing required secret value is reported as weak (empty)."""
    schema = {"VAR": {"secret": True, "required": True}}
    env = {}

    findings = detect_secrets(schema, env)
    assert len(findings) == 1
    assert findings[0]["weak"] is True

def test_secret_scanner_absent_optional_secret_skipped():
    """An absent optional secret is not reported (nothing to leak)."""
    schema = {"VAR": {"secret": True}}
    env = {}

    findings = detect_secrets(schema, env)
    assert len(findings) == 0
