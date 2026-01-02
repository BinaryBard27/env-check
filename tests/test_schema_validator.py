from env_check.validator import ValidatorEngine
from env_check.cli import load_env_file
import json
import os

def test_schema_validation():
    # Load fixtures
    schema_path = os.path.join(os.path.dirname(__file__), "fixtures/schema.json")
    env_path = os.path.join(os.path.dirname(__file__), "fixtures/sample.env")
    
    with open(schema_path) as f:
        schema = json.load(f)
    env = load_env_file(env_path)

    # Run validation
    validator = ValidatorEngine(schema, env)
    results = validator.run()
    
    # Filter for failures
    failures = [r for r in results if not r.ok]
    
    # Expected failures:
    # 1. API_KEY (pattern mismatch)
    # 2. DATABASE_URL (missing required)
    # 3. MODE (missing required)
    
    assert len(failures) == 3
    
    failed_vars = {r.variable for r in failures}
    assert "API_KEY" in failed_vars
    assert "DATABASE_URL" in failed_vars
    assert "MODE" in failed_vars
