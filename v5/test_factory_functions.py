"""
Test script to verify all factory functions work correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_progressive_context_loader():
    """Test ProgressiveContextLoader factory function"""
    print("\n=== Testing ProgressiveContextLoader ===")
    try:
        from logic.progressive_context_loader import get_progressive_context_loader
        
        # Get singleton instance
        loader = get_progressive_context_loader()
        print(f"✓ Created ProgressiveContextLoader instance: {type(loader).__name__}")
        
        # Get same instance again
        loader2 = get_progressive_context_loader()
        assert loader is loader2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        # Reset
        from logic.progressive_context_loader import reset_progressive_context_loader
        reset_progressive_context_loader()
        print(f"✓ Reset successful")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_compressor():
    """Test ContextCompressor factory function"""
    print("\n=== Testing ContextCompressor ===")
    try:
        from logic.context_compressor import get_context_compressor
        
        # Get singleton instance
        compressor = get_context_compressor()
        print(f"✓ Created ContextCompressor instance: {type(compressor).__name__}")
        
        # Get same instance again
        compressor2 = get_context_compressor()
        assert compressor is compressor2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_quality_analyzer():
    """Test ContextQualityAnalyzer factory function"""
    print("\n=== Testing ContextQualityAnalyzer ===")
    try:
        from logic.context_quality_analyzer import get_context_quality_analyzer
        
        # Get singleton instance
        analyzer = get_context_quality_analyzer()
        print(f"✓ Created ContextQualityAnalyzer instance: {type(analyzer).__name__}")
        
        # Get same instance again
        analyzer2 = get_context_quality_analyzer()
        assert analyzer is analyzer2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_token_budget_manager():
    """Test TokenBudgetManager factory function"""
    print("\n=== Testing TokenBudgetManager ===")
    try:
        from logic.token_budget_manager import get_token_budget_manager
        
        # Get singleton instance
        manager = get_token_budget_manager()
        print(f"✓ Created TokenBudgetManager instance: {type(manager).__name__}")
        
        # Get same instance again
        manager2 = get_token_budget_manager()
        assert manager is manager2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_reasoning_engine():
    """Test ReasoningEngine factory function"""
    print("\n=== Testing ReasoningEngine ===")
    try:
        from logic.reasoning_engine import get_reasoning_engine
        
        # Get singleton instance
        engine = get_reasoning_engine()
        print(f"✓ Created ReasoningEngine instance: {type(engine).__name__}")
        
        # Get same instance again
        engine2 = get_reasoning_engine()
        assert engine is engine2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_expander():
    """Test ContextExpander factory function"""
    print("\n=== Testing ContextExpander ===")
    try:
        from logic.context_expander import get_context_expander
        
        # Get singleton instance
        expander = get_context_expander()
        print(f"✓ Created ContextExpander instance: {type(expander).__name__}")
        
        # Get same instance again
        expander2 = get_context_expander()
        assert expander is expander2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_scorer():
    """Test ContextScorer factory function"""
    print("\n=== Testing ContextScorer ===")
    try:
        from logic.context_scorer import get_context_scorer
        
        # Get singleton instance
        scorer = get_context_scorer()
        print(f"✓ Created ContextScorer instance: {type(scorer).__name__}")
        
        # Get same instance again
        scorer2 = get_context_scorer()
        assert scorer is scorer2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_progress_tracker():
    """Test ProgressTracker factory function"""
    print("\n=== Testing ProgressTracker ===")
    try:
        from logic.progress_tracker import get_progress_tracker
        
        # Get singleton instance
        tracker = get_progress_tracker()
        print(f"✓ Created ProgressTracker instance: {type(tracker).__name__}")
        
        # Get same instance again
        tracker2 = get_progress_tracker()
        assert tracker is tracker2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trap_detector():
    """Test TrapDetector factory function"""
    print("\n=== Testing TrapDetector ===")
    try:
        from logic.trap_detector import get_trap_detector
        
        # Get singleton instance
        detector = get_trap_detector()
        print(f"✓ Created TrapDetector instance: {type(detector).__name__}")
        
        # Get same instance again
        detector2 = get_trap_detector()
        assert detector is detector2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_trap_recovery():
    """Test TrapRecovery factory function"""
    print("\n=== Testing TrapRecovery ===")
    try:
        from logic.trap_recovery import get_trap_recovery
        
        # Get singleton instance
        recovery = get_trap_recovery()
        print(f"✓ Created TrapRecovery instance: {type(recovery).__name__}")
        
        # Get same instance again
        recovery2 = get_trap_recovery()
        assert recovery is recovery2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pattern_recognizer():
    """Test PatternRecognizer factory function"""
    print("\n=== Testing PatternRecognizer ===")
    try:
        from logic.pattern_recognizer import get_pattern_recognizer
        
        # Get singleton instance
        recognizer = get_pattern_recognizer()
        print(f"✓ Created PatternRecognizer instance: {type(recognizer).__name__}")
        
        # Get same instance again
        recognizer2 = get_pattern_recognizer()
        assert recognizer is recognizer2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adaptive_heuristics():
    """Test AdaptiveHeuristics factory function"""
    print("\n=== Testing AdaptiveHeuristics ===")
    try:
        from logic.adaptive_heuristics import get_adaptive_heuristics
        
        # Get singleton instance
        heuristics = get_adaptive_heuristics()
        print(f"✓ Created AdaptiveHeuristics instance: {type(heuristics).__name__}")
        
        # Get same instance again
        heuristics2 = get_adaptive_heuristics()
        assert heuristics is heuristics2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_self_reflection():
    """Test SelfReflection factory function"""
    print("\n=== Testing SelfReflection ===")
    try:
        from logic.self_reflection import get_self_reflection
        
        # Get singleton instance
        reflection = get_self_reflection()
        print(f"✓ Created SelfReflection instance: {type(reflection).__name__}")
        
        # Get same instance again
        reflection2 = get_self_reflection()
        assert reflection is reflection2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_lesson_learner():
    """Test LessonLearner factory function"""
    print("\n=== Testing LessonLearner ===")
    try:
        from logic.lesson_learner import get_lesson_learner
        
        # Get singleton instance
        learner = get_lesson_learner()
        print(f"✓ Created LessonLearner instance: {type(learner).__name__}")
        
        # Get same instance again
        learner2 = get_lesson_learner()
        assert learner is learner2, "Should return same singleton instance"
        print(f"✓ Singleton pattern verified")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing V5 Factory Functions")
    print("=" * 60)
    
    # Test V5 Phase 6 modules
    tests = [
        test_progressive_context_loader,
        test_context_compressor,
        test_context_quality_analyzer,
        test_token_budget_manager,
    ]
    
    # Test V4 modules
    tests += [
        test_reasoning_engine,
        test_context_expander,
        test_context_scorer,
        test_progress_tracker,
        test_trap_detector,
        test_trap_recovery,
        test_pattern_recognizer,
        test_adaptive_heuristics,
        test_self_reflection,
        test_lesson_learner,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All factory functions working correctly!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())