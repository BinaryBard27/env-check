from env_check.validator import ValidatorEngine

def test_required_variable_missing():
    cfg = {
        "FOO": {"required": True}
    }
    engine = ValidatorEngine(cfg, env={})
    results = engine.run()
    assert results[0].ok is False
    assert results[0].severity.name == "CRITICAL"
