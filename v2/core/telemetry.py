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
from collections import deque
from contextlib import contextmanager
from typing import Optional, Dict, Any

# Import V3 TelemetryManager
from v2.data.telemetry_manager import get_telemetry_manager


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
        self.current_step = ""
        self.stats = {
            "tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost": 0.0,
            "tasks_completed": 0,
        }
        self.log_history = deque(maxlen=10)
        
        # V3 Telemetry Manager Integration
        self.telemetry_manager = get_telemetry_manager()
        self.current_operation_id: Optional[str] = None

        self.log_dir = "logs"
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.log_file = os.path.join(
            self.log_dir, f"l4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        self.llm_log_file = os.path.join(
            self.log_dir, f"llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
        rich_handler = RichHandler(
            console=self.console, show_time=True, show_path=True, markup=True
        )
        rich_handler.setLevel(logging.INFO)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(rich_handler)

        self._initialized = True

    def _add_to_history(self, level: str, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = "white"
        if level == "INFO":
            color = "cyan"
        elif level == "ERROR":
            color = "red"
        elif level == "WARNING":
            color = "yellow"
        elif level == "DEBUG":
            color = "grey70"

        # Strip rich tags for history if needed, or keep them for display
        self.log_history.append(f"[{color}]{timestamp} | {level} | {message}[/{color}]")

    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.logger.info(message)
        self._add_to_history("INFO", message)
        
        # V3 Integration: Record log reference if we have an active operation
        if self.current_operation_id:
            self.telemetry_manager.record_log_reference(
                operation_id=self.current_operation_id,
                log_level="INFO",
                logger_name="L4",
                message=message,
                log_data=context
            )

    def error(self, message: str, exc_info=False, context: Optional[Dict[str, Any]] = None):
        self.logger.error(message, exc_info=exc_info)
        self._add_to_history("ERROR", message)
        
        # V3 Integration: Record log reference if we have an active operation
        if self.current_operation_id:
            self.telemetry_manager.record_log_reference(
                operation_id=self.current_operation_id,
                log_level="ERROR",
                logger_name="L4",
                message=message,
                log_data=context
            )

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.logger.debug(message)
        self._add_to_history("DEBUG", message)
        
        # V3 Integration: Record log reference if we have an active operation
        if self.current_operation_id:
            self.telemetry_manager.record_log_reference(
                operation_id=self.current_operation_id,
                log_level="DEBUG",
                logger_name="L4",
                message=message,
                log_data=context
            )

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.logger.warning(message)
        self._add_to_history("WARNING", message)
        
        # V3 Integration: Record log reference if we have an active operation
        if self.current_operation_id:
            self.telemetry_manager.record_log_reference(
                operation_id=self.current_operation_id,
                log_level="WARNING",
                logger_name="L4",
                message=message,
                log_data=context
            )

    def log_task_start(self, task_title: str, task_id: Optional[int] = None):
        self.current_task = task_title
        self.current_step = ""
        self.info(f"🚀 Starting Task: [bold cyan]{task_title}[/bold cyan]")
        
        # V3 Integration: Start telemetry operation
        self.current_operation_id = self.telemetry_manager.start_operation(
            operation_type="task_execution",
            title=task_title,
            metadata={"task_id": task_id} if task_id else None
        )
        self.telemetry_manager.record_event(
            self.current_operation_id,
            "started",
            "info",
            f"Task started: {task_title}",
            {"task_id": task_id} if task_id else None
        )

    def log_task_success(self, task_title: str):
        self.info(
            f"✅ Task Completed Successfully: [bold green]{task_title}[/bold green]"
        )
        self.current_task = "Waiting..."
        self.current_step = ""
        
        # V3 Integration: End telemetry operation
        if self.current_operation_id:
            self.telemetry_manager.record_event(
                self.current_operation_id,
                "completed",
                "info",
                f"Task completed successfully: {task_title}"
            )
            self.telemetry_manager.end_operation(self.current_operation_id, "completed")
            self.current_operation_id = None

    def log_task_failure(self, task_title: str, reason: str):
        self.error(
            f"❌ Task Failed: [bold red]{task_title}[/bold red] - Reason: {reason}"
        )
        self.current_task = "Waiting..."
        self.current_step = ""
        
        # V3 Integration: End telemetry operation with failure
        if self.current_operation_id:
            self.telemetry_manager.record_event(
                self.current_operation_id,
                "failed",
                "error",
                f"Task failed: {task_title}",
                {"reason": reason}
            )
            self.telemetry_manager.end_operation(self.current_operation_id, "failed", {"failure_reason": reason})
            self.current_operation_id = None

    def track_step(self, step_name: str, context: Optional[Dict[str, Any]] = None):
        """Sets the current active step within a task."""
        self.current_step = step_name
        self.info(f"  ↳ [bold blue]Step:[/bold blue] {step_name}", context=context)
        
        # V3 Integration: Record step event
        if self.current_operation_id:
            self.telemetry_manager.record_event(
                self.current_operation_id,
                "step",
                "info",
                f"Step: {step_name}",
                context
            )

    def log_llm_usage(
        self, tokens: int, cost: float, p_tokens: int = 0, c_tokens: int = 0
    ):
        """Updates LLM usage stats."""
        self.stats["tokens"] += tokens
        self.stats["prompt_tokens"] += p_tokens
        self.stats["completion_tokens"] += c_tokens
        self.stats["cost"] += cost
        self.update_dashboard()
        
        # V3 Integration: Record metrics
        if self.current_operation_id:
            self.telemetry_manager.record_metric(self.current_operation_id, "tokens_used", tokens, "tokens")
            self.telemetry_manager.record_metric(self.current_operation_id, "prompt_tokens", p_tokens, "tokens")
            self.telemetry_manager.record_metric(self.current_operation_id, "completion_tokens", c_tokens, "tokens")
            self.telemetry_manager.record_metric(self.current_operation_id, "cost", cost, "USD")

    def log_llm_interaction(
        self, provider, model, system_prompt, user_prompt, response
    ):
        """Logs the full LLM interaction for traceability."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (
            f"--- INTERACTION START {timestamp} ---\n"
            f"Provider: {provider} | Model: {model}\n"
            f"SYSTEM PROMPT:\n{system_prompt}\n"
            f"USER PROMPT:\n{user_prompt}\n"
            f"RESPONSE:\n{response}\n"
            f"--- INTERACTION END ---\n\n"
        )
        with open(self.llm_log_file, "a") as f:
            f.write(log_entry)
        self.debug(f"LLM interaction logged to {self.llm_log_file}")

    @contextmanager
    def task_context(self, task_title: str, task_id: Optional[int] = None, operation_type: str = "task_execution"):
        """
        Context manager for task execution with V3 telemetry integration.
        
        Args:
            task_title: Title of the task
            task_id: Optional task ID for tracking
            operation_type: Type of operation for telemetry
        """
        # V3 Integration: Use TelemetryManager context manager
        with self.telemetry_manager.track_operation(
            operation_type=operation_type,
            title=task_title,
            metadata={"task_id": task_id} if task_id else None
        ) as op:
            self.current_operation_id = op.operation_id
            self.log_task_start(task_title, task_id)
            outcome = {"success": True}
            try:
                yield outcome
                if outcome["success"]:
                    self.log_task_success(task_title)
            except Exception as e:
                self.log_task_failure(task_title, str(e))
                self.error(f"Error in task '{task_title}'", exc_info=True)
                raise
            finally:
                self.current_operation_id = None

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
            Layout(name="main", ratio=1),
        )
        layout["main"].split_column(
            Layout(name="top", size=10),
            Layout(name="bottom", ratio=1),
        )
        layout["top"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1),
        )
        return layout

    def update_dashboard(
        self,
        task: str = None,
        step: str = None,
        tokens: int = None,
        cost: float = None,
        tasks_completed: int = None,
        prompt_tokens: int = None,
        completion_tokens: int = None,
    ):
        """
        Updates the dashboard with new data.
        """
        if task:
            self.current_task = task
        if step:
            self.current_step = step
        if tokens is not None:
            # We treat these as absolute updates from start.py, or incremental from provider.py
            # For simplicity in v1, start.py overrides them with DB totals.
            self.stats["tokens"] = tokens
        if prompt_tokens is not None:
            self.stats["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            self.stats["completion_tokens"] = completion_tokens
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
        activity_text = f"\n  [bold blue]Status:[/bold blue] Running\n  [bold blue]Current Task:[/bold blue] {self.current_task}"
        if self.current_step:
            activity_text += (
                f"\n  [bold blue]Current Step:[/bold blue] {self.current_step}"
            )

        task_panel = Panel(
            activity_text,
            title="[bold cyan]Main Activity[/bold cyan]",
            border_style="cyan",
        )
        self.layout["left"].update(task_panel)

        # Right Panel - Stats
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_row(
            "Tokens Used",
            f"[bold cyan]{self.stats['tokens']:,}[/bold cyan] [grey70](P:{self.stats['prompt_tokens']:,}|C:{self.stats['completion_tokens']:,})[/grey70]",
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

        # Bottom Panel - Log History
        log_text = Text.from_markup("\n".join(self.log_history))
        self.layout["bottom"].update(
            Panel(
                log_text,
                title="[bold white]Recent Logs[/bold white]",
                border_style="white",
            )
        )


# Global telemetry instance
telemetry = Telemetry()
