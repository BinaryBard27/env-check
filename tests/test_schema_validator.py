from env_check.schema_validator import SchemaValidator
from env_check.loader import load_env_file
import json

def test_schema_validation():
    schema = json.load(open("tests/fixtures/schema.json"))
    env = load_env_file("tests/fixtures/sample.env")

    validator = SchemaValidator(schema, env, strict=False)
    issues = validator.validate()

    # Expect 2 issues: PORT is extra + unused key checks
    assert len(issues) == 2
