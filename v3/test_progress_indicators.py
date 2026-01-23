"""
Unit tests for Progress Indicators (Task 6.1)
"""

import time
import threading
import pytest
from v3.core.ui import (
    ProgressIndicator,
    MultiStepProgress,
    create_progress,
    create_multi_step_progress,
)


class TestProgressIndicator:
    """Test ProgressIndicator class"""

    def test_init(self):
        """Test initialization"""
        progress = ProgressIndicator("Test Operation")
        assert progress.description == "Test Operation"
        assert progress.state.completed == 0
        assert progress.state.total == 100
        assert progress.operation_id is None

    def test_start(self):
        """Test starting progress tracking"""
        progress = ProgressIndicator("Test")
        progress.start(total=10)
        assert progress.state.total == 10
        assert progress.state.completed == 0
        assert progress.state.cancelled is False
        assert progress.state.success is False

    def test_update(self):
        """Test updating progress"""
        progress = ProgressIndicator("Test")
        progress.start(total=100)
        progress.update(50)
        assert progress.state.completed == 50
        assert progress.state.eta is not None

        # Test with description change
        progress.update(75, description="Updated")
        assert progress.state.completed == 75
        assert progress.state.description == "Updated"

    def test_advance(self):
        """Test advancing progress"""
        progress = ProgressIndicator("Test")
        progress.start(total=10)
        progress.advance(3)
        assert progress.state.completed == 3
        progress.advance(2)
        assert progress.state.completed == 5

    def test_complete(self):
        """Test completing progress"""
        progress = ProgressIndicator("Test")
        progress.start(total=10)
        progress.update(5)
        progress.complete(success=True)
        assert progress.state.completed == 10
        assert progress.state.success is True

    def test_cancel(self):
        """Test cancelling progress"""
        progress = ProgressIndicator("Test")
        progress.start(total=10)
        progress.cancel()
        assert progress.state.cancelled is True

        # Test that update doesn't work after cancel
        progress.update(5)
        assert progress.state.completed == 0

    def test_set_operation_id(self):
        """Test setting operation ID"""
        progress = ProgressIndicator("Test")
        progress.set_operation_id("op-123")
        assert progress.operation_id == "op-123"

    def test_get_status(self):
        """Test getting progress status"""
        progress = ProgressIndicator("Test")
        progress.start(total=100)
        progress.update(50)
        progress.set_operation_id("op-456")

        status = progress.get_status()
        assert status["total"] == 100
        assert status["completed"] == 50
        assert status["percentage"] == 50.0
        assert status["operation_id"] == "op-456"
        assert "elapsed_seconds" in status
        assert status["eta_seconds"] is not None

    def test_context_manager_success(self):
        """Test context manager with success"""
        progress = ProgressIndicator("Test")
        with progress.track(total=5):
            for i in range(5):
                progress.advance()

        assert progress.state.completed == 5
        assert progress.state.success is True

    def test_context_manager_failure(self):
        """Test context manager with exception"""
        progress = ProgressIndicator("Test")
        with pytest.raises(ValueError):
            with progress.track(total=5):
                progress.advance(2)
                raise ValueError("Test error")

        assert progress.state.completed == 5  # Should complete on error
        assert progress.state.success is False

    def test_eta_calculation(self):
        """Test ETA calculation"""
        progress = ProgressIndicator("Test")
        progress.start(total=100)

        # Simulate some work
        progress.update(25)
        time.sleep(0.1)  # Small delay
        progress.update(50)

        # ETA should be calculated
        assert progress.state.eta is not None
        assert progress.state.eta > 0

    def test_thread_safety(self):
        """Test thread-safe operations"""
        progress = ProgressIndicator("Test")
        progress.start(total=100)

        def update_progress():
            for _ in range(10):
                progress.advance(1)
                time.sleep(0.01)

        # Start multiple threads
        threads = [threading.Thread(target=update_progress) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have advanced 50 times (10 * 5 threads)
        assert progress.state.completed == 50


class TestMultiStepProgress:
    """Test MultiStepProgress class"""

    def test_init(self):
        """Test initialization"""
        steps = ["Step 1", "Step 2", "Step 3"]
        progress = MultiStepProgress("Test", steps)
        assert progress.description == "Test"
        assert progress.steps == steps
        assert progress.current_step_index == 0

    def test_set_steps(self):
        """Test setting steps"""
        progress = MultiStepProgress("Test")
        steps = ["A", "B", "C"]
        progress.set_steps(steps)
        assert progress.steps == steps
        assert progress.current_step_index == 0

    def test_start(self):
        """Test starting multi-step progress"""
        steps = ["Step 1", "Step 2", "Step 3"]
        progress = MultiStepProgress("Test", steps)
        progress.start()
        assert progress.indicator.state.total == 3

    def test_next_step(self):
        """Test advancing to next step"""
        steps = ["Step 1", "Step 2", "Step 3"]
        progress = MultiStepProgress("Test", steps)
        progress.start()

        progress.next_step()
        assert progress.current_step_index == 1
        assert progress.indicator.state.completed == 1

        progress.next_step()
        assert progress.current_step_index == 2
        assert progress.indicator.state.completed == 2

    def test_complete(self):
        """Test completing all steps"""
        steps = ["Step 1", "Step 2", "Step 3"]
        progress = MultiStepProgress("Test", steps)
        progress.start()
        progress.next_step()
        progress.next_step()
        progress.next_step()
        progress.complete(success=True)

        assert progress.current_step_index == 3
        assert progress.indicator.state.success is True

    def test_cancel(self):
        """Test cancelling multi-step progress"""
        steps = ["Step 1", "Step 2", "Step 3"]
        progress = MultiStepProgress("Test", steps)
        progress.start()
        progress.next_step()
        progress.cancel()

        assert progress.indicator.state.cancelled is True

    def test_set_operation_id(self):
        """Test setting operation ID"""
        steps = ["Step 1", "Step 2"]
        progress = MultiStepProgress("Test", steps)
        progress.set_operation_id("op-123")
        assert progress.operation_id == "op-123"
        assert progress.indicator.operation_id == "op-123"

    def test_context_manager(self):
        """Test context manager for multi-step progress"""
        steps = ["Step 1", "Step 2", "Step 3"]
        progress = MultiStepProgress("Test", steps)

        with progress.track():
            for step in steps:
                time.sleep(0.01)
                progress.next_step()

        assert progress.current_step_index == 3
        assert progress.indicator.state.success is True


class TestFactoryFunctions:
    """Test factory functions"""

    def test_create_progress(self):
        """Test create_progress factory function"""
        progress = create_progress("Test Operation")
        assert isinstance(progress, ProgressIndicator)
        assert progress.description == "Test Operation"

    def test_create_multi_step_progress(self):
        """Test create_multi_step_progress factory function"""
        steps = ["A", "B", "C"]
        progress = create_multi_step_progress("Test", steps)
        assert isinstance(progress, MultiStepProgress)
        assert progress.description == "Test"
        assert progress.steps == steps


class TestProgressScenarios:
    """Test real-world usage scenarios"""

    def test_file_processing_scenario(self):
        """Test progress indicator for file processing"""
        files = [f"file_{i}.txt" for i in range(10)]
        progress = ProgressIndicator("Processing files")
        progress.start(total=len(files))

        for file in files:
            # Simulate processing
            time.sleep(0.01)
            progress.advance(1)

        progress.complete(success=True)
        assert progress.state.completed == len(files)

    def test_multi_step_deployment_scenario(self):
        """Test multi-step progress for deployment"""
        steps = ["Building", "Testing", "Packaging", "Deploying", "Verifying"]
        progress = MultiStepProgress("Deployment", steps)
        progress.start()

        for step in steps:
            # Simulate step execution
            time.sleep(0.01)
            progress.next_step()

        progress.complete(success=True)
        assert progress.current_step_index == len(steps)

    def test_download_progress_scenario(self):
        """Test progress indicator for download with dynamic total"""
        progress = ProgressIndicator("Downloading file")
        progress.start(total=1000)

        for i in range(0, 1000, 100):
            progress.update(i)

        progress.complete(success=True)
        assert progress.state.completed == 1000

    def test_partial_completion_scenario(self):
        """Test partial completion before error"""
        progress = ProgressIndicator("Processing items")
        progress.start(total=10)

        # Complete 5 items
        for i in range(5):
            progress.advance()

        # Then complete (simulating error handling)
        progress.complete(success=False)
        assert progress.state.completed == 10
        assert progress.state.success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
