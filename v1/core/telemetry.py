import logging
import sys
import os
from datetime import datetime
from rich.console import Console, Group
from rich.logging import RichHandler
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.text import Text


class Telemetry:
    """
    Handles structured logging to console and file.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Telemetry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.console = Console()
        self.live = None
        self.layout = None
        self.current_task = "Waiting..."
        self.stats = {"tokens": 0, "cost": 0.0, "tasks_completed": 0}

        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.log_file = os.path.join(
            self.log_dir, f"l4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Configure logging
        self.logger = logging.getLogger("L4")
        self.logger.setLevel(logging.DEBUG)

        # File Handler (JSON or structured text)
        file_handler = logging.FileHandler(self.log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)

        # Rich Console Handler
        rich_handler = RichHandler(console=self.console, show_time=True, show_path=True)
        rich_handler.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(rich_handler)

        self._initialized = True

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def log_task_start(self, task_title: str):
        self.info(f"🚀 Starting Task: [bold cyan]{task_title}[/bold cyan]")

    def log_task_success(self, task_title: str):
        self.info(
            f"✅ Task Completed Successfully: [bold green]{task_title}[/bold green]"
        )

    def log_task_failure(self, task_title: str, reason: str):
        self.error(
            f"❌ Task Failed: [bold red]{task_title}[/bold red] - Reason: {reason}"
        )

    def start_dashboard(self):
        """
        Starts the live dashboard display.
        """
        if self.live:
            return
        self.layout = self._create_layout()
        self.live = Live(
            self.layout, console=self.console, refresh_per_second=4, transient=False
        )
        self.live.start()
        self.update_dashboard()

    def stop_dashboard(self):
        """
        Stops the live dashboard display.
        """
        if self.live:
            self.live.stop()
            self.live = None
            self.layout = None

    def _create_layout(self) -> Layout:
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", size=7),
        )
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1),
        )
        return layout

    def update_dashboard(
        self,
        task: str = None,
        tokens: int = None,
        cost: float = None,
        tasks_completed: int = None,
    ):
        """
        Updates the dashboard with new data.
        """
        if task:
            self.current_task = task
        if tokens is not None:
            self.stats["tokens"] = tokens
        if cost is not None:
            self.stats["cost"] = cost
        if tasks_completed is not None:
            self.stats["tasks_completed"] = tasks_completed

        if not self.layout:
            return

        # Header
        self.layout["header"].update(
            Panel(
                Text(
                    "L4 Self-Evolving Platform v1.0",
                    justify="center",
                    style="bold magenta",
                ),
                border_style="magenta",
            )
        )

        # Left Panel - Current Activity
        task_panel = Panel(
            f"\n  [bold blue]Status:[/bold blue] Running\n  [bold blue]Current Task:[/bold blue] {self.current_task}\n",
            title="[bold cyan]Main Activity[/bold cyan]",
            border_style="cyan",
        )
        self.layout["left"].update(task_panel)

        # Right Panel - Stats
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_row(
            "Tokens Used", f"[bold cyan]{self.stats['tokens']}[/bold cyan]"
        )
        stats_table.add_row(
            "Est. Cost", f"[bold green]${self.stats['cost']:.4f}[/bold green]"
        )
        stats_table.add_row(
            "Tasks Done", f"[bold yellow]{self.stats['tasks_completed']}[/bold yellow]"
        )

        self.layout["right"].update(
            Panel(
                stats_table,
                title="[bold yellow]Telemetry[/bold yellow]",
                border_style="yellow",
            )
        )


# Global telemetry instance
telemetry = Telemetry()
