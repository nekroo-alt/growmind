import sys
import os
import subprocess
from rich.console import Console
from rich.table import Table
from v5.data import TASK_DB_PATH, ACTIVITY_DB_PATH

console = Console()


def check_python():
    version = sys.version_info
    success = version.major == 3 and version.minor >= 10
    status = (
        "[green]OK[/green]" if success else "[red]FAIL[/red] (Requires Python 3.10+)"
    )
    return "Python Version", f"{sys.version.split()[0]}", status


def check_git():
    try:
        result = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, check=True
        )
        return "Git", result.stdout.strip(), "[green]OK[/green]"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Git", "Not Found", "[red]FAIL[/red]"


def check_api_keys():
    keys = {
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
    }

    results = []
    for name, value in keys.items():
        if value:
            # Mask the key
            masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
            results.append((name, masked, "[green]OK[/green]"))
        else:
            # Google is the default in v1, so it might be more critical
            if name == "GOOGLE_API_KEY":
                results.append((name, "Missing", "[yellow]MISSING (Default)[/yellow]"))
            else:
                results.append((name, "Missing", "[blue]OPTIONAL[/blue]"))
    return results


def check_sqlite():
    try:
        import sqlite3

        return "SQLite3", f"v{sqlite3.sqlite_version}", "[green]OK[/green]"
    except ImportError:
        return "SQLite3", "Import Error", "[red]FAIL[/red]"


def check_databases():
    results = []
    for name, path in [("Task DB", TASK_DB_PATH), ("Activity DB", ACTIVITY_DB_PATH)]:
        exists = os.path.exists(path)
        status = "[green]OK[/green]" if exists else "[red]MISSING[/red]"
        results.append((name, path, status))
    return results


def check_static_files():
    results = []
    for f in ["product.md", "technical.md"]:
        exists = os.path.exists(f)
        status = "[green]OK[/green]" if exists else "[red]MISSING[/red]"
        results.append((f, "Project Root", status))
    return results


def run_doctor():
    table = Table(title="L4 Doctor - Environment Verification")
    console.print(f"Project Root: [bold]{os.getcwd()}[/bold]")
    table.add_column("Component", style="cyan")
    table.add_column("Details", style="magenta")
    table.add_column("Status", style="bold")

    # Python
    table.add_row(*check_python())

    # Git
    table.add_row(*check_git())

    # SQLite
    table.add_row(*check_sqlite())

    table.add_section()

    # API Keys
    for row in check_api_keys():
        table.add_row(*row)

    table.add_section()

    # Databases
    for row in check_databases():
        table.add_row(*row)

    table.add_section()

    # Static Files
    for row in check_static_files():
        table.add_row(*row)

    console.print(table)

    # Final verdict
    console.print(
        "\n[bold yellow]Note:[/bold yellow] If any critical components are [red]FAIL[/red], the platform may not function correctly."
    )


if __name__ == "__main__":
    run_doctor()
