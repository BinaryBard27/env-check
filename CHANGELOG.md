# Changelog

## v1.0.2

### Fixed
- Packaging: `env_check.validators` and `env_check.output` subpackages are now
  included in the wheel (`find_packages`), so `pip install` no longer raises
  `ModuleNotFoundError`
- `pattern` schema rule now works as an alias for `regex` (previously silently
  ignored as an "unknown rule key" warning)
- Unknown `type` names now produce a warning instead of silently passing
- Range check on a non-numeric value reports the type failure when a `type`
  rule is present
- Schema objects are no longer mutated during validation (shorthand
  `min`/`max` normalization now merges with an explicit `range`)
- `--fix` no longer overwrites an existing `.backup` (uses `.backup.1`, …) and
  appends `# TODO VAR=<value>` comments for keys without a default instead of
  fake empty values
- `.gitignore` contained unresolved merge-conflict markers; rewritten
- `env-check.yml` CI workflow ran a nonexistent `--no-cache` flag and failed
  on every push; now validates the example schema/env pair

### Changed
- Secret handling: flagged variables with healthy values are **reported but no
  longer fail the run**. Weak/placeholder values (empty, `changeme`,
  `undefined`, repeated characters, …) fail with exit code 3. New
  `--fail-on-secrets` flag restores fail-on-any-value behavior. Exit-code
  precedence: 3 (weak secret) > 1 (validation error) > 0
- README rewritten to document the actual CLI, schema rules, exit codes and
  secret behavior (the previous version documented an API that did not exist)

### Removed
- Dead code: `env_check/loader.py`, `env_check/output/color.py`,
  `env_check/output/json_output.py`, stray empty `python` file at repo root

## v1.0.1
- Fix packaging issue causing ModuleNotFoundError for env_check.validators

## v1.0.0

- Initial stable open-source release
- Schema-based environment validation
- CI-safe exit codes
- Secret flag enforcement
- Drift detection support
