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

def test_secret_scanner_no_findings():
    schema = {"VAR": {"secret": True}}
    env = {} # Value is missing
    
    findings = detect_secrets(schema, env)
    assert len(findings) == 0
