# src/env_check/output.py
import json
from collections import defaultdict
from typing import List, Dict

# Severity ordering (higher index = more severe)
SEVERITY_ORDER = ["INFO", "LOW", "MEDIUM", "HIGH"]
SEVERITY_SCORE = {s: i for i, s in enumerate(SEVERITY_ORDER)}

class Color:
    RESET = "\033[0m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    MAGENTA = "\033[95m"

def color_for_severity(sev: str) -> str:
    if sev == "HIGH":
        return Color.RED
    if sev == "MEDIUM":
        return Color.YELLOW
    if sev == "LOW":
        return Color.BLUE
    return Color.GREEN

def filter_by_min_severity(findings: List[Dict], min_sev: str) -> List[Dict]:
    if min_sev is None:
        return findings
    if min_sev not in SEVERITY_SCORE:
        return findings
    min_score = SEVERITY_SCORE[min_sev]
    return [f for f in findings if SEVERITY_SCORE.get(f.get("severity","INFO"),0) >= min_score]

def group_findings_by_file(findings: List[Dict]) -> Dict[str, List[Dict]]:
    grouped = defaultdict(list)
    for f in findings:
        grouped[f["file"]].append(f)
    return grouped

def print_findings(findings: List[Dict], ci: bool=False):
    """Pretty print grouped findings. If ci=True, produce compact JSON with counts."""
    summary = {"HIGH":0, "MEDIUM":0, "LOW":0, "INFO":0}
    findings = sorted(findings, key=lambda x: (x.get("file"), -SEVERITY_SCORE.get(x.get("severity","INFO"),0)))
    grouped = group_findings_by_file(findings)

    for file, items in grouped.items():
        print(f"\n{file}")
        for it in items:
            sev = it.get("severity","INFO")
            summary.setdefault(sev, 0)
            summary[sev] += 1
            if ci:
                # minimal one-line per finding for CI logs
                print(f"{sev} {file}:{it.get('line', '?')} {it.get('pattern','')} {it.get('value_snippet','')}")
            else:
                col = color_for_severity(sev)
                print(f"  {col}[{sev}]{Color.RESET} {it.get('line','?')} {it.get('pattern','')} -> {it.get('value_snippet','')}")
    # summary footer
    if ci:
        print(json.dumps({"high": summary["HIGH"], "medium": summary["MEDIUM"], "low": summary["LOW"], "info": summary["INFO"]}))
    else:
        print("\nSummary:")
        print(f"  HIGH:   {summary['HIGH']}")
        print(f"  MEDIUM: {summary['MEDIUM']}")
        print(f"  LOW:    {summary['LOW']}")
        print(f"  INFO:   {summary['INFO']}")

def print_scan_report_text(report: dict, min_sev: str=None, ci: bool=False):
    # report expected to contain "env_files" and "advanced_secret_findings"
    print("=== REPO SCAN REPORT ===\n")
    print("Env Files Found:")
    for f in report.get("env_files", []):
        print(f"  - {f}")
    findings = report.get("advanced_secret_findings", [])
    findings = filter_by_min_severity(findings, min_sev)
    if not findings:
        if ci:
            print(json.dumps({"high":0,"medium":0,"low":0,"info":0}))
        else:
            print("\nNo findings (after threshold).\n")
        return
    print("\nAdvanced Secret Findings:")
    print_findings(findings, ci=ci)
