# sample plugin: check that PORT is numeric and > 1024
def run(env_vars, schema):
    issues = []
    port = env_vars.get("PORT")
    if port:
        try:
            p = int(port)
            if p <= 1024:
                issues.append({"type":"plugin_port_low", "message": "PORT should be > 1024", "severity":"warning"})
        except ValueError:
            issues.append({"type":"plugin_port_invalid", "message":"PORT is not an integer", "severity":"error"})
    return issues
