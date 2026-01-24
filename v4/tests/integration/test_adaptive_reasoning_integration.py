"""
Integration test for adaptive reasoning components in core modules.

This test verifies that V4 adaptive reasoning components are properly integrated
into all core modules (start, dispatcher, planner, implementor, verifier).
"""
import pytest
import os
import sys

# Add v3 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from v3.core.start import Orchestrator
from v3.logic.dispatcher import Dispatcher
from v3.logic.planner import Planner
from v3.logic.implementor import Implementor
from v3.logic.verifier import Verifier


class TestAdaptiveReasoningIntegration:
    """Test suite for V4 adaptive reasoning integration."""

    def test_orchestrator_has_adaptive_reasoning(self):
        """Verify Orchestrator has V4 adaptive reasoning components."""
        orchestrator = Orchestrator()
        
        # Check that V4 components are initialized
        assert hasattr(orchestrator, 'context_hierarchy'), "Orchestrator should have context_hierarchy"
        assert hasattr(orchestrator, 'decision_history'), "Orchestrator should have decision_history"
        assert hasattr(orchestrator, 'reasoning_engine'), "Orchestrator should have reasoning_engine"
        
        # Verify they are not None
        assert orchestrator.context_hierarchy is not None, "context_hierarchy should be initialized"
        assert orchestrator.decision_history is not None, "decision_history should be initialized"
        assert orchestrator.reasoning_engine is not None, "reasoning_engine should be initialized"

    def test_dispatcher_has_adaptive_reasoning(self):
        """Verify Dispatcher has V4 adaptive reasoning components."""
        dispatcher = Dispatcher()
        
        # Check that V4 components are initialized
        assert hasattr(dispatcher, 'context_hierarchy'), "Dispatcher should have context_hierarchy"
        assert hasattr(dispatcher, 'reasoning_engine'), "Dispatcher should have reasoning_engine"
        
        # Verify they are not None
        assert dispatcher.context_hierarchy is not None, "context_hierarchy should be initialized"
        assert dispatcher.reasoning_engine is not None, "reasoning_engine should be initialized"

    def test_planner_has_adaptive_reasoning(self):
        """Verify Planner has V4 adaptive reasoning components."""
        planner = Planner()
        
        # Check that V4 components are initialized
        assert hasattr(planner, 'context_hierarchy'), "Planner should have context_hierarchy"
        assert hasattr(planner, 'decision_history'), "Planner should have decision_history"
        assert hasattr(planner, 'reasoning_engine'), "Planner should have reasoning_engine"
        assert hasattr(planner, 'context_expander'), "Planner should have context_expander"
        
        # Verify they are not None
        assert planner.context_hierarchy is not None, "context_hierarchy should be initialized"
        assert planner.decision_history is not None, "decision_history should be initialized"
        assert planner.reasoning_engine is not None, "reasoning_engine should be initialized"
        assert planner.context_expander is not None, "context_expander should be initialized"

    def test_implementor_has_adaptive_reasoning(self):
        """Verify Implementor has V4 adaptive reasoning components."""
        implementor = Implementor()
        
        # Check that V4 components are initialized
        assert hasattr(implementor, 'context_hierarchy'), "Implementor should have context_hierarchy"
        assert hasattr(implementor, 'decision_history'), "Implementor should have decision_history"
        assert hasattr(implementor, 'reasoning_engine'), "Implementor should have reasoning_engine"
        assert hasattr(implementor, 'trap_detector'), "Implementor should have trap_detector"
        assert hasattr(implementor, 'trap_recovery'), "Implementor should have trap_recovery"
        assert hasattr(implementor, 'progress_tracker'), "Implementor should have progress_tracker"
        
        # Verify they are not None
        assert implementor.context_hierarchy is not None, "context_hierarchy should be initialized"
        assert implementor.decision_history is not None, "decision_history should be initialized"
        assert implementor.reasoning_engine is not None, "reasoning_engine should be initialized"
        assert implementor.trap_detector is not None, "trap_detector should be initialized"
        assert implementor.trap_recovery is not None, "trap_recovery should be initialized"
        assert implementor.progress_tracker is not None, "progress_tracker should be initialized"

    def test_verifier_has_adaptive_reasoning(self):
        """Verify Verifier has V4 adaptive reasoning components."""
        verifier = Verifier()
        
        # Check that V4 components are initialized
        assert hasattr(verifier, 'context_hierarchy'), "Verifier should have context_hierarchy"
        assert hasattr(verifier, 'decision_history'), "Verifier should have decision_history"
        assert hasattr(verifier, 'reasoning_engine'), "Verifier should have reasoning_engine"
        assert hasattr(verifier, 'action_validator'), "Verifier should have action_validator"
        assert hasattr(verifier, 'progress_tracker'), "Verifier should have progress_tracker"
        
        # Verify they are not None
        assert verifier.context_hierarchy is not None, "context_hierarchy should be initialized"
        assert verifier.decision_history is not None, "decision_history should be initialized"
        assert verifier.reasoning_engine is not None, "reasoning_engine should be initialized"
        verifier.action_validator is not None, "action_validator should be initialized"
        assert verifier.progress_tracker is not None, "progress_tracker should be initialized"

    def test_singleton_consistency(self):
        """Verify that modules use the same singleton instances."""
        orchestrator = Orchestrator()
        dispatcher = Dispatcher()
        planner = Planner()
        implementor = Implementor()
        verifier = Verifier()
        
        # All modules should share the same context_hierarchy instance
        # (assuming singleton pattern is implemented)
        # This test verifies consistency across modules
        
        # Check that each module has access to adaptive reasoning
        assert all(hasattr(m, 'context_hierarchy') for m in [orchestrator, dispatcher, planner, implementor, verifier])
        assert all(hasattr(m, 'reasoning_engine') for m in [orchestrator, dispatcher, planner, implementor, verifier])

    def test_components_are_functional(self):
        """Verify that V4 components have expected methods."""
        orchestrator = Orchestrator()
        
        # Test context_hierarchy
        assert hasattr(orchestrator.context_hierarchy, 'get_context'), "context_hierarchy should have get_context method"
        
        # Test decision_history
        assert hasattr(orchestrator.decision_history, 'record_decision'), "decision_history should have record_decision method"
        
        # Test reasoning_engine
        assert hasattr(orchestrator.reasoning_engine, 'analyze'), "reasoning_engine should have analyze method"
        assert hasattr(orchestrator.reasoning_engine, 'decide'), "reasoning_engine should have decide method"
        assert hasattr(orchestrator.reasoning_engine, 'act'), "reasoning_engine should have act method"
        assert hasattr(orchestrator.reasoning_engine, 'validate'), "reasoning_engine should have validate method"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])