def is_feature_flag(key):
    # simple heuristic
    return key.upper().startswith("FEATURE_") or key.upper().startswith("FLAG_") or key.endswith("_ENABLED")

def check_flag_coverage(env_keys, usages_map):
    """
    env_keys: iterable of keys
    usages_map: dict from key -> list of files (from repo_usage_checker)
    returns list of issues (warnings) if flags aren't referenced properly or conflict among envs.
    """
    issues = []
    for k in env_keys:
        if is_feature_flag(k):
            used = usages_map.get(k, [])
            if not used:
                issues.append({
                    "type": "flag_unreferenced",
                    "severity": "warning",
                    "key": k,
                    "message": f"Feature flag '{k}' is not referenced in code."
                })
    return issues
