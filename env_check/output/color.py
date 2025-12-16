try:
    from rich.console import Console
    console = Console()
except Exception:
    console = None

def print_line(text: str):
    if console:
        console.print(text)
    else:
        print(text)
