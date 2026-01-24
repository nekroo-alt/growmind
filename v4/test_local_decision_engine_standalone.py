"""
Standalone test for LocalDecisionEngine to verify implementation.
"""
import sys
import os

# Add v4 to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logic.local_decision_engine import LocalDecisionEngine, DecisionOutcome

def test_basic_functionality():
    """Test basic functionality of LocalDecisionEngine"""
    print("Testing LocalDecisionEngine...")
    
    engine = LocalDecisionEngine()
    
    # Test error classification
    print("\n1. Testing error classification...")
    assert engine.classify_error("Rate limit exceeded") == 'transient'
    assert engine.classify_error("Authentication failed") == 'permanent'
    assert engine.classify_error("Connection refused") in ['transient', 'network']
    assert engine.classify_error("Unknown error") is None
    print("   ✓ Error classification works")
    
    # Test retry decisions
    print("\n2. Testing retry decisions...")
    assert engine.should_retry_error("Rate limit exceeded", 0) == True
    assert engine.should_retry_error("Rate limit exceeded", 3) == False
    assert engine.should_retry_error("Authentication failed", 0) == False
    assert engine.should_retry_error("Unknown error", 0) is None
    print("   ✓ Retry decisions work")
    
    # Test progress detection
    print("\n3. Testing progress detection...")
    assert engine.is_progress_stagnant([0.1, 0.3, 0.5, 0.7, 0.9]) == False
    assert engine.is_progress_stagnant([0.5, 0.51, 0.52, 0.51, 0.50]) == True
    assert engine.is_regression(0.5, 0.7) == True
    assert engine.is_regression(0.7, 0.6) == False
    print("   ✓ Progress detection works")
    
    # Test token budget selection
    print("\n4. Testing token budget selection...")
    assert engine.select_token_budget('simple') == 1000
    assert engine.select_token_budget('medium') == 3000
    assert engine.select_token_budget('complex') == 5000
    assert engine.select_token_budget('unknown') == 3000
    print("   ✓ Token budget selection works")
    
    # Test context expansion
    print("\n5. Testing context expansion...")
    assert engine.should_expand_context(0, 'simple', 0) == False
    assert engine.should_expand_context(0, 'complex', 0) == True
    assert engine.should_expand_context(2, 'medium', 1) == False
    assert engine.should_expand_context(0, 'complex', 3) == False
    print("   ✓ Context expansion works")
    
    # Test file selection validation
    print("\n6. Testing file selection validation...")
    assert engine.validate_file_selection("Fix bug", ['auth.py'], ['auth.py', 'user.py']) == True
    assert engine.validate_file_selection("Fix bug", ['missing.py'], ['auth.py']) == False
    assert engine.validate_file_selection("Fix bug", [], ['auth.py']) == False
    print("   ✓ File selection validation works")
    
    # Test statistics
    print("\n7. Testing statistics...")
    engine._record_decision('test', {}, True, False, DecisionOutcome.LOCAL_SUCCESS, 0.9)
    stats = engine.get_statistics()
    assert stats['total_decisions'] == 1
    assert stats['local_decisions'] == 1
    print("   ✓ Statistics tracking works")
    
    # Test report generation
    print("\n8. Testing report generation...")
    report = engine.get_report()
    assert 'Local Decision Engine Report' in report
    assert 'Total Decisions: 1' in report
    print("   ✓ Report generation works")
    
    print("\n" + "="*60)
    print("✅ All tests passed! LocalDecisionEngine is working correctly.")
    print("="*60)

if __name__ == '__main__':
    test_basic_functionality()