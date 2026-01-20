"""
Pytest configuration for L4D V2 test suite
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture
def sample_code():
    """Fixture providing sample code for testing"""
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
    """Fixture providing complex code for testing edge cases"""
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
