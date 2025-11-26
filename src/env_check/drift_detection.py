
def load_env_file(path):
    """Load any .env file into a dict."""
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def compare_env_files(file1, file2):
    """Compare two env files and return drift details."""
    env1 = load_env_file(file1)
    env2 = load_env_file(file2)

    keys1 = set(env1.keys())
    keys2 = set(env2.keys())

    missing_in_f1 = keys2 - keys1
    missing_in_f2 = keys1 - keys2

    different_values = {
        key: (env1[key], env2[key])
        for key in keys1 & keys2
        if env1[key] != env2[key]
    }

    return {
        "missing_in_file1": list(missing_in_f1),
        "missing_in_file2": list(missing_in_f2),
        "different_values": different_values
    }


def format_drift_report(result, file1, file2):
    """Format drift comparison nicely."""
    missing_f1 = result["missing_in_file1"]
    missing_f2 = result["missing_in_file2"]
    diff_vals = result["different_values"]

    output = []
    output.append(f"Drift Detection Between:\n  {file1}\n  {file2}\n")

    if missing_f1:
        output.append(f"❌ Keys missing in {file1}:")
        for k in missing_f1:
            output.append(f"   ➤ {k}")
    else:
        output.append(f"✔ No missing keys in {file1}")

    if missing_f2:
        output.append(f"❌ Keys missing in {file2}:")
        for k in missing_f2:
            output.append(f"   ➤ {k}")
    else:
        output.append(f"✔ No missing keys in {file2}")

    if diff_vals:
        output.append("⚠ Keys with different values:")
        for k, (v1, v2) in diff_vals.items():
            output.append(f"   ➤ {k}\n      {file1}: {v1}\n      {file2}: {v2}")
    else:
        output.append("✔ No value differences")

    return "\n".join(output)
