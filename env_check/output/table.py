from typing import List
from ..validator import ValidationResult
try:
    from rich.table import Table
    from rich.console import Console
    from rich import box
    console = Console()
    RICH = True
except Exception:
    RICH = False

def print_table(results: List[ValidationResult]):
    if RICH:
        table = Table(box=box.MINIMAL_DOUBLE_HEAD, show_lines=False)
        table.add_column("VARIABLE", style="bold")
        table.add_column("STATUS")
        table.add_column("SEVERITY")
        table.add_column("DETAIL")
        for r in results:
            status = "OK" if r.ok else "MISSING" if "missing" in r.detail.lower() else "INVALID"
            table.add_row(r.variable, status, r.severity.name, r.detail)
        console.print(table)
    else:
        # fallback plain text
        for r in results:
            status = "OK" if r.ok else "MISSING" if "missing" in r.detail.lower() else "INVALID"
            print(f"{r.variable:20} | {status:8} | {r.severity.name:8} | {r.detail}")
