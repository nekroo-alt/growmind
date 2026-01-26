"""
Data Module

Provides database management, telemetry, checkpointing, and caching.
"""

from .telemetry_manager import TelemetryManager, get_telemetry_manager
from .cache_manager import CacheManager
from .semantic_mapper import SemanticMapper
from .decision_history import DecisionHistoryManager
from .decision_tracer import DecisionTracer
from .context_hierarchy import ContextHierarchyManager, ContextLevel, get_context_hierarchy
from .llm_cache_manager import LLMLLMCacheManager
from .cost_tracker import CostTracker

# V4 components
from .decision_history import get_decision_history

# CheckpointManager excluded from __init__ to avoid circular import with v5.core.transactions
# Import directly from v5.data.checkpoint_manager when needed

# db_manager only has functions, no class
# from .db_manager import DBManager, get_db_manager

# V5 modules (not yet implemented)
# from .usage_tracker import UsageTracker
# from .dependency_analyzer import DependencyAnalyzer
# from .context_quality_tracker import ContextQualityTracker

__all__ = [
    'TelemetryManager',
    'get_telemetry_manager',
    'CacheManager',
    'SemanticMapper',
    'DecisionHistoryManager',
    'get_decision_history',
    'DecisionTracer',
    'ContextHierarchyManager',
    'ContextLevel',
    'get_context_hierarchy',
    'LLMLLMCacheManager',
    'CostTracker',
]
