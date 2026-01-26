"""
Pytest configuration and common fixtures for L4D V5 test suite

This file provides reusable fixtures to reduce code duplication across tests.
Fixtures are grouped by category: databases, file systems, managers, and mocks.
"""

import sys
import os
import tempfile
import shutil
import sqlite3
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


# ============================================================================
# CODE SAMPLES FIXTURES
# ============================================================================

@pytest.fixture
def sample_code():
    """Fixture providing sample code for testing."""
    return '''
import os
from typing import List, Optional

class DataProcessor:
    """Process data with various methods"""
    
    def __init__(self, name: str):
        self.name = name
        self.data: List[str] = []
    
    def add_item(self, item: str) -> None:
        """Add an item to data"""
        self.data.append(item)
    
    def process_items(self) -> Optional[List[str]]:
        """Process all items"""
        if not self.data:
            return None
        
        result = []
        for item in self.data:
            if item:
                result.append(item.upper())
        
        return result

def helper_function(x: int) -> int:
    """A simple helper function"""
    return x * 2
'''


@pytest.fixture
def sample_complex_code():
    """Fixture providing complex code for testing edge cases."""
    return '''
import sys
from typing import Dict, List, Any

class ComplexClass:
    """Complex class with many methods"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._cache = {}
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize complex class"""
        if self._initialized:
            return True
        
        try:
            self._load_config()
            self._setup_cache()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Initialization failed: {e}")
            return False
    
    def _load_config(self) -> None:
        """Load configuration"""
        for key, value in self.config.items():
            if isinstance(value, dict):
                self._process_nested_config(key, value)
            else:
                self._cache[key] = value
    
    def _process_nested_config(self, prefix: str, config: Dict[str, Any]) -> None:
        """Process nested configuration"""
        for key, value in config.items():
            full_key = f"{prefix}.{key}"
            if isinstance(value, dict):
                self._process_nested_config(full_key, value)
            else:
                self._cache[full_key] = value
    
    def _setup_cache(self) -> None:
        """Setup cache with default values"""
        self._cache.setdefault('initialized', True)
        self._cache.setdefault('count', 0)
    
    def get_value(self, key: str) -> Any:
        """Get a value from cache"""
        return self._cache.get(key)
    
    def set_value(self, key: str, value: Any) -> None:
        """Set a value in cache"""
        self._cache[key] = value


def complex_function(x: int, y: int) -> int:
    """A function with multiple decision points"""
    if x < 0:
        if y < 0:
            return 0
        else:
            return y
    else:
        if y < 0:
            return x
        else:
            for i in range(x):
                if i == y:
                    return i * y
            return x + y
'''


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing.
    
    The database is automatically cleaned up after the test.
    Returns the path to the temporary database.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def empty_sqlite_db(temp_db):
    """Create an empty SQLite database connection.
    
    Returns a sqlite3 connection to the temporary database.
    """
    conn = sqlite3.connect(temp_db)
    yield conn
    conn.close()


@pytest.fixture
def test_database_with_tables(empty_sqlite_db):
    """Create a test database with common tables.
    
    Creates a database with typical tables used across the codebase:
    - test_table (id, data)
    - session_state (id, status, data)
    """
    empty_sqlite_db.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT)")
    empty_sqlite_db.execute(
        """
        CREATE TABLE session_state (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            status TEXT,
            data TEXT
        )
    """
    )
    empty_sqlite_db.commit()
    return empty_sqlite_db


@pytest.fixture
def populated_test_database(test_database_with_tables):
    """Create a test database with sample data."""
    # Insert test data
    test_database_with_tables.execute(
        "INSERT INTO test_table VALUES (1, 'row 1')"
    )
    test_database_with_tables.execute(
        "INSERT INTO test_table VALUES (2, 'row 2')"
    )
    test_database_with_tables.execute(
        "INSERT INTO session_state VALUES (1, 42, 'in_progress', 'some data')"
    )
    test_database_with_tables.commit()
    return test_database_with_tables


# ============================================================================
# FILE SYSTEM FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing.
    
    The directory and all its contents are automatically cleaned up after the test.
    Returns the path to the temporary directory.
    """
    temp = tempfile.mkdtemp()
    yield temp
    try:
        shutil.rmtree(temp)
    except:
        pass


@pytest.fixture
def temp_project_dir(temp_dir):
    """Create a temporary directory structure mimicking a Python project.
    
    Creates a typical project structure:
    - temp_dir/
      - package/
        - __init__.py
        - module.py
      - tests/
        - __init__.py
        - test_module.py
      - main.py
    """
    # Create package directory
    pkg_dir = os.path.join(temp_dir, "package")
    os.makedirs(pkg_dir, exist_ok=True)
    
    # Create __init__.py
    with open(os.path.join(pkg_dir, "__init__.py"), 'w') as f:
        f.write('')
    
    # Create module.py
    with open(os.path.join(pkg_dir, "module.py"), 'w') as f:
        f.write('''
def public_function():
    """A public function."""
    return "public"

def _private_function():
    """A private function."""
    return "private"

class TestClass:
    """A test class."""
    
    def __init__(self):
        self.value = 0
    
    def method(self):
        return self.value
''')
    
    # Create tests directory
    tests_dir = os.path.join(temp_dir, "tests")
    os.makedirs(tests_dir, exist_ok=True)
    
    # Create test __init__.py
    with open(os.path.join(tests_dir, "__init__.py"), 'w') as f:
        f.write('')
    
    # Create test_module.py
    with open(os.path.join(tests_dir, "test_module.py"), 'w') as f:
        f.write('''
def test_public_function():
    result = public_function()
    assert result == "public"
''')
    
    # Create main.py
    with open(os.path.join(temp_dir, "main.py"), 'w') as f:
        f.write('''
from package.module import public_function

def main():
    result = public_function()
    print(result)

if __name__ == '__main__':
    main()
''')
    
    return temp_dir


# ============================================================================
# MANAGER FIXTURES
# ============================================================================

@pytest.fixture
def telemetry_manager(temp_db):
    """Create a TelemetryManager instance with a temporary database.
    
    The TelemetryManager is automatically cleaned up after the test.
    """
    from data.telemetry_manager import TelemetryManager
    
    tm = TelemetryManager(db_path=temp_db)
    yield tm
    # Clean up is handled by temp_db fixture


@pytest.fixture
def reset_global_telemetry():
    """Reset global telemetry manager singleton.
    
    Use this fixture when you need a fresh global telemetry manager
    for a test.
    """
    from data import telemetry_manager

    with telemetry_manager._telemetry_lock:
        telemetry_manager._telemetry_manager = None
    yield
    with telemetry_manager._telemetry_lock:
        telemetry_manager._telemetry_manager = None


@pytest.fixture
def checkpoint_manager(temp_dir):
    """Create a CheckpointManager instance with a temporary directory.
    
    The checkpoint directory is automatically cleaned up after the test.
    """
    from data.checkpoint_manager import CheckpointManager
    
    manager = CheckpointManager(
        checkpoint_dir=os.path.join(temp_dir, "checkpoints")
    )
    yield manager
    # Clean up is handled by temp_dir fixture


@pytest.fixture
def checkpoint_manager_with_db(temp_dir):
    """Create a CheckpointManager with a test database.
    
    Creates a test database and CheckpointManager for testing
    checkpoint/restore functionality.
    """
    from data.checkpoint_manager import CheckpointManager
    
    # Create test database
    db_path = os.path.join(temp_dir, "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, data TEXT)")
    conn.execute("INSERT INTO test_table VALUES (1, 'original data')")
    conn.commit()
    conn.close()
    
    manager = CheckpointManager(
        checkpoint_dir=os.path.join(temp_dir, "checkpoints")
    )
    yield manager, db_path
    # Clean up is handled by temp_dir fixture


@pytest.fixture
def dead_code_detector(temp_dir, temp_db):
    """Create a DeadCodeDetector instance with temporary directories.
    
    Creates a temporary project structure and call graph database
    for testing dead code detection.
    """
    from logic.dead_code_detector import DeadCodeDetector
    
    # Create test files
    test_file = os.path.join(temp_dir, "test_module.py")
    with open(test_file, 'w') as f:
        f.write('''
def used_function():
    """This function is called."""
    return 42

def unused_function():
    """This function is never called."""
    return 24

class UsedClass:
    """This class is used."""
    def method(self):
        return 1

class UnusedClass:
    """This class is never used."""
    def method(self):
        return 2
''')
    
    detector = DeadCodeDetector(
        project_root=temp_dir,
        call_graph_db=temp_db,
        low_usage_threshold=3
    )
    yield detector
    # Clean up is handled by temp_dir and temp_db fixtures


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider for testing.
    
    The mock provider simulates LLM responses without making
    actual API calls. Returns a MagicMock instance.
    """
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Mock response"
    mock_provider.generate_chat.return_value = "Mock chat response"
    return mock_provider


@pytest.fixture
def mock_llm_provider_with_error():
    """Create a mock LLM provider that raises errors.
    
    Useful for testing error handling in code that calls LLMs.
    """
    mock_provider = MagicMock()
    mock_provider.generate.side_effect = Exception("LLM API error")
    mock_provider.generate_chat.side_effect = Exception("LLM API error")
    return mock_provider


@pytest.fixture
def mock_llm_provider_with_retry():
    """Create a mock LLM provider that fails then succeeds.
    
    Simulates transient LLM errors for testing retry logic.
    """
    mock_provider = MagicMock()
    call_count = [0]
    
    def fail_then_succeed(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise Exception("Transient error")
        return "Success"
    
    mock_provider.generate.side_effect = fail_then_succeed
    mock_provider.generate_chat.side_effect = fail_then_succeed
    return mock_provider


@pytest.fixture
def mock_session_manager():
    """Create a mock SessionManager for testing.
    
    Returns a MagicMock instance with common session methods mocked.
    """
    from core.session_manager import SessionManager
    
    mock_session = MagicMock(spec=SessionManager)
    mock_session.session_id = "test-session-123"
    mock_session.start_time = datetime.now()
    mock_session.get_status.return_value = "active"
    return mock_session


# ============================================================================
# CONFIGURATION FIXTURES
# ============================================================================

@pytest.fixture
def test_config():
    """Provide a test configuration dictionary.
    
    Returns a dict with common configuration values used across tests.
    """
    return {
        "project_root": "/tmp/test_project",
        "cache_enabled": True,
        "cache_dir": "/tmp/test_cache",
        "llm_provider": "openai",
        "llm_model": "gpt-4",
        "llm_temperature": 0.7,
        "max_token_budget": 4000,
        "telemetry_enabled": True,
        "checkpoint_enabled": True,
        "log_level": "INFO",
    }


@pytest.fixture
def minimal_test_config():
    """Provide a minimal test configuration.
    
    Returns a dict with only essential configuration values.
    """
    return {
        "project_root": "/tmp/test_project",
        "llm_provider": "openai",
        "llm_model": "gpt-4",
    }


# ============================================================================
# SEMANTIC MAPPER FIXTURES
# ============================================================================

@pytest.fixture
def semantic_mapper():
    """Create a SemanticMapper instance for testing AST analysis.
    
    The SemanticMapper is used for code analysis in many tests.
    """
    from data.semantic_mapper import SemanticMapper
    
    mapper = SemanticMapper()
    return mapper


# ============================================================================
# CACHE MANAGER FIXTURES
# ============================================================================

@pytest.fixture
def cache_manager(temp_dir):
    """Create a CacheManager instance with a temporary directory.
    
    The cache is automatically cleaned up after the test.
    """
    from data.cache_manager import CacheManager
    
    manager = CacheManager(
        cache_dir=os.path.join(temp_dir, "cache"),
        max_size_mb=10
    )
    yield manager
    # Clean up is handled by temp_dir fixture


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to run slow tests last."""
    # Sort tests so slow tests run last
    slow_items = []
    normal_items = []
    
    for item in items:
        if item.get_closest_marker("slow"):
            slow_items.append(item)
        else:
            normal_items.append(item)
    
    items[:] = normal_items + slow_items