"""
User Interface Components for L4D V3

This module provides UI components including progress indicators, status displays,
and interactive elements for enhanced user experience.
"""

import sys
import time
import threading
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field

# Try to import rich for rich terminal output
try:
    from rich.console import Console
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TaskID
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Progress = None


@dataclass
class ProgressState:
    """State for tracking progress of an operation"""
    total: int = 100
    completed: int = 0
    description: str = ""
    start_time: float = field(default_factory=time.time)
    eta: Optional[float] = None
    cancelled: bool = False
    success: bool = False


class ProgressIndicator:
    """
    Progress indicator for long-running operations.
    
    Supports both TTY and non-TTY environments with automatic fallback.
    Uses rich library when available for enhanced display.
    """
    
    def __init__(self, description: str = "Processing"):
        """
        Initialize progress indicator.
        
        Args:
            description: Description of the operation
        """
        self.description = description
        self.state = ProgressState(description=description)
        self._lock = threading.Lock()
        self._console = Console() if RICH_AVAILABLE else None
        self._rich_progress: Optional[Progress] = None
        self._task_id: Optional[TaskID] = None
        self._is_tty = sys.stdout.isatty()
        
        # Track operation ID for telemetry correlation
        self.operation_id: Optional[str] = None
    
    def start(self, total: int = 100) -> None:
        """
        Start progress tracking.
        
        Args:
            total: Total number of steps (default: 100)
        """
        with self._lock:
            self.state.total = total
            self.state.completed = 0
            self.state.start_time = time.time()
            self.state.cancelled = False
            self.state.success = False
            self.state.eta = None
            
            if RICH_AVAILABLE and self._is_tty:
                self._rich_progress = Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                    TextColumn("({task.completed}/{task.total})"),
                    TimeRemainingColumn(),
                    console=self._console,
                    transient=True
                )
                self._rich_progress.start()
                self._task_id = self._rich_progress.add_task(
                    self.description,
                    total=total
                )
            else:
                # Simple text progress for non-TTY or without rich
                print(f"{self.description} started (0/{total})")
    
    def update(self, completed: int, description: Optional[str] = None) -> None:
        """
        Update progress.
        
        Args:
            completed: Number of steps completed
            description: Optional new description
        """
        with self._lock:
            if self.state.cancelled:
                return
            
            self.state.completed = min(completed, self.state.total)
            
            # Update ETA
            elapsed = time.time() - self.state.start_time
            if self.state.completed > 0:
                rate = self.state.completed / elapsed
                remaining = self.state.total - self.state.completed
                self.state.eta = remaining / rate if rate > 0 else None
            
            if description:
                self.state.description = description
            
            if RICH_AVAILABLE and self._rich_progress and self._task_id is not None:
                update_kwargs = {"completed": completed}
                if description:
                    update_kwargs["description"] = description
                self._rich_progress.update(self._task_id, **update_kwargs)
            elif self._is_tty:
                # Simple progress bar for TTY without rich
                percentage = (self.state.completed / self.state.total) * 100
                bar_length = 40
                filled = int(bar_length * self.state.completed / self.state.total)
                bar = '█' * filled + '░' * (bar_length - filled)
                print(f"\r{self.description}: [{bar}] {percentage:.1f}% ({self.state.completed}/{self.state.total})", end='', flush=True)
    
    def advance(self, delta: int = 1, description: Optional[str] = None) -> None:
        """
        Advance progress by delta steps.
        
        Args:
            delta: Number of steps to advance
            description: Optional new description
        """
        with self._lock:
            new_completed = self.state.completed + delta
            self.update(new_completed, description)
    
    def complete(self, success: bool = True) -> None:
        """
        Mark progress as complete.
        
        Args:
            success: Whether the operation succeeded
        """
        with self._lock:
            self.state.completed = self.state.total
            self.state.success = success
            
            if RICH_AVAILABLE and self._rich_progress and self._task_id is not None:
                self._rich_progress.update(self._task_id, completed=self.state.total)
                status = "✓" if success else "✗"
                self._rich_progress.stop()
                print(f"\n{self.description} {status}")
            elif self._is_tty:
                print(f"\n{self.description}: Complete ({'✓' if success else '✗'})")
            else:
                print(f"{self.description} completed ({'✓' if success else '✗'})")
    
    def cancel(self) -> None:
        """Cancel the operation."""
        with self._lock:
            self.state.cancelled = True
            
            if RICH_AVAILABLE and self._rich_progress:
                self._rich_progress.stop()
            print(f"\n{self.description} cancelled")
    
    def set_operation_id(self, operation_id: str) -> None:
        """
        Set operation ID for telemetry correlation.
        
        Args:
            operation_id: Operation ID from telemetry system
        """
        self.operation_id = operation_id
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current progress status.
        
        Returns:
            Dictionary with current progress state
        """
        with self._lock:
            elapsed = time.time() - self.state.start_time
            return {
                "operation_id": self.operation_id,
                "description": self.state.description,
                "total": self.state.total,
                "completed": self.state.completed,
                "percentage": (self.state.completed / self.state.total) * 100 if self.state.total > 0 else 0,
                "elapsed_seconds": elapsed,
                "eta_seconds": self.state.eta,
                "cancelled": self.state.cancelled,
                "success": self.state.success
            }
    
    @contextmanager
    def track(self, total: int = 100):
        """
        Context manager for automatic progress tracking.
        
        Args:
            total: Total number of steps
            
        Yields:
            ProgressIndicator instance
            
        Example:
            with progress.track(total=5) as p:
                for i in range(5):
                    do_work()
                    p.advance()
        """
        self.start(total)
        try:
            yield self
            self.complete(success=True)
        except Exception as e:
            self.complete(success=False)
            raise


class MultiStepProgress:
    """
    Progress indicator for multi-step operations with named steps.
    
    Shows current step and overall progress.
    """
    
    def __init__(self, description: str = "Processing", steps: List[str] = None):
        """
        Initialize multi-step progress.
        
        Args:
            description: Overall operation description
            steps: List of step names
        """
        self.description = description
        self.steps = steps or []
        self.current_step_index = 0
        self.indicator = ProgressIndicator()
        self.operation_id: Optional[str] = None
    
    def set_steps(self, steps: List[str]) -> None:
        """
        Set step names.
        
        Args:
            steps: List of step names
        """
        self.steps = steps
        self.current_step_index = 0
    
    def start(self) -> None:
        """Start progress tracking."""
        self.indicator.description = self.description
        if self.steps:
            total = len(self.steps)
            self.indicator.start(total)
            self._update_step_description()
        else:
            self.indicator.start()
    
    def next_step(self) -> None:
        """Advance to next step."""
        if self.current_step_index < len(self.steps):
            self.current_step_index += 1
            self.indicator.advance()
            self._update_step_description()
    
    def _update_step_description(self) -> None:
        """Update progress description with current step."""
        if self.steps and self.current_step_index < len(self.steps):
            step_name = self.steps[self.current_step_index]
            step_num = self.current_step_index + 1
            total_steps = len(self.steps)
            new_description = f"{self.description}: Step {step_num}/{total_steps} - {step_name}"
            self.indicator.update(self.current_step_index, description=new_description)
    
    def complete(self, success: bool = True) -> None:
        """
        Mark all steps as complete.
        
        Args:
            success: Whether the operation succeeded
        """
        self.indicator.complete(success)
    
    def cancel(self) -> None:
        """Cancel the operation."""
        self.indicator.cancel()
    
    def set_operation_id(self, operation_id: str) -> None:
        """
        Set operation ID for telemetry correlation.
        
        Args:
            operation_id: Operation ID from telemetry system
        """
        self.operation_id = operation_id
        self.indicator.set_operation_id(operation_id)
    
    @contextmanager
    def track(self):
        """
        Context manager for automatic multi-step tracking.
        
        Yields:
            MultiStepProgress instance
            
        Example:
            with progress.track() as p:
                for step_name in steps:
                    do_step()
                    p.next_step()
        """
        self.start()
        try:
            yield self
            self.complete(success=True)
        except Exception as e:
            self.complete(success=False)
            raise


def create_progress(description: str = "Processing") -> ProgressIndicator:
    """
    Factory function to create a progress indicator.
    
    Args:
        description: Description of the operation
        
    Returns:
        ProgressIndicator instance
    """
    return ProgressIndicator(description)


def create_multi_step_progress(description: str = "Processing", steps: List[str] = None) -> MultiStepProgress:
    """
    Factory function to create a multi-step progress indicator.
    
    Args:
        description: Overall operation description
        steps: List of step names
        
    Returns:
        MultiStepProgress instance
    """
    return MultiStepProgress(description, steps)
