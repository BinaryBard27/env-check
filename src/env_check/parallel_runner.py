from concurrent.futures import ThreadPoolExecutor, as_completed

# tasks are callables that return list-of-issues (or [])
def run_tasks_in_parallel(tasks, max_workers=4):
    results = []
    issues = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {ex.submit(t): idx for idx, t in enumerate(tasks)}
        for fut in as_completed(future_map):
            try:
                r = fut.result()
                if r:
                    issues.extend(r)
            except Exception as e:
                issues.append({
                    "type": "internal_error",
                    "message": f"Parallel task failed: {e}"
                })
    return issues
