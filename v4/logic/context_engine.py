import os
import hashlib
import subprocess
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass
from data.semantic_mapper import SemanticMapper
from data.cache_manager import get_cache_manager
from logic.task_impact_analyzer import TaskImpactAnalyzer
from logic.dependency_traverser import DependencyTraverser


class ContextLevel(Enum):
    """Context hierarchy levels for progressive loading."""
    IMMEDIATE = 0  # Current file and immediate dependencies only
    RECENT = 1      # Add upstream/downstream functions
    SESSION = 2      # Add session history and patterns
    PROJECT = 3      # Full project context


@dataclass
class ContextLevelInfo:
    """Information about a specific context level."""
    level: ContextLevel
    name: str
    description: str
    token_multiplier: float  # Multiplier for estimated tokens at this level
    average_success_rate: float  # Historical success rate at this level
    expansion_count: int  # Number of times expanded to this level


class ContextEngine:
    """
    Context Engine responsible for pruning and selecting relevant code snippets
    based on the task scope.

    Enhanced with context memoization to cache and reuse context collections
    for similar tasks, reducing redundant AST parsing and context generation.
    """

    def __init__(self, workspace_root="."):
        self.root = workspace_root

        # Memoization cache for context collections
        self._context_cache: Dict[str, Dict] = {}

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_updates = 0

        # Integration with CacheManager for AST caching
        self.cache_manager = get_cache_manager()

        # V5: Progressive context loading
        self._context_levels = self._initialize_context_levels()
        self._optimal_levels: Dict[str, ContextLevel] = {}  # Task type -> optimal level
        self._expansion_stats: Dict[str, Dict] = {}  # Task type -> expansion statistics
        self._level_usage_stats: Dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}

    def get_pruned_context(
        self,
        task_query,
        files,
        use_smart_scoping=True,
        task_title="",
        acceptance_criteria="",
        force_refresh=False,
    ):
        """
        Returns a string containing relevant code snippets or summaries for the given files.

        Enhanced in V2 to use AST-based impact analysis via TaskImpactAnalyzer for more
        precise context collection. This replaces the V1 keyword matching approach with
        intelligent dependency-aware context selection.

        Args:
            task_query: Query string to match against code (legacy, used for fallback)
            files: List of file paths to analyze
            use_smart_scoping: If True, use AST-based impact analysis (default: True)
            task_title: Title of the task (required for smart scoping)
            acceptance_criteria: Acceptance criteria for the task (enhances impact analysis)
            force_refresh: If True, bypass cache and regenerate context

        Returns:
            str: Formatted context with relevant code snippets and summaries

        Examples:
            >>> engine = ContextEngine(workspace_root=".")
            >>> context = engine.get_pruned_context(
            ...     task_query="cache invalidation",
            ...     files=["v1/data/cache_manager.py"],
            ...     task_title="Implement cache invalidation",
            ...     acceptance_criteria="Cache must be invalidated when source files change"
            ... )

        Note:
            - For best results, provide both task_title and acceptance_criteria
            - Smart scoping (V2) is enabled by default and uses TaskImpactAnalyzer
            - Legacy keyword matching is used only as fallback when smart scoping is disabled
        """
        # Generate cache key for memoization
        cache_key = self._generate_cache_key(
            task_query, files, use_smart_scoping, task_title, acceptance_criteria
        )

        # Check cache if not forcing refresh
        if not force_refresh and cache_key in self._context_cache:
            self._cache_hits += 1
            cached_entry = self._context_cache[cache_key]
            return cached_entry["context"]

        # Cache miss - generate new context
        self._cache_misses += 1

        # V2 Enhancement: Use smart file scoping with AST-based impact analysis
        if use_smart_scoping and task_title:
            # Use TaskImpactAnalyzer to score files by relevance
            scored_files = self.get_smart_file_scope(
                task_title, acceptance_criteria, files
            )

            # Filter files by relevance score (more inclusive threshold: 0.05)
            # This ensures borderline dependencies are included
            filtered_files = [f for f in scored_files if f["relevance_score"] >= 0.05]

            # Extract file paths with relevance info for context generation
            files_with_scores = [
                (f["file_path"], f["relevance_score"], f["match_details"])
                for f in filtered_files
            ]
        else:
            # Legacy V1 behavior: Use all files with uniform scoring
            files_with_scores = [
                (f, 1.0, {"reason": "Legacy keyword mode"}) for f in files
            ]

        context = []

        # Extract keywords for fallback matching (legacy support)
        keywords = {
            w for w in task_query.lower().replace("_", " ").split() if len(w) > 2
        }

        for path, relevance_score, match_details in files_with_scores:
            full_path = os.path.join(self.root, path)
            if not os.path.exists(full_path):
                continue

            with open(full_path, "r") as f:
                file_content = f.read()

            # Only use SemanticMapper for Python files
            if not path.endswith(".py"):
                # For non-python files, just provide a snippet of the content
                snippet = file_content[:1000] + (
                    "..." if len(file_content) > 1000 else ""
                )
                reason = match_details.get("reason", "Non-Python file")
                context.append(
                    f"--- File: {path} (Relevance: {relevance_score:.2f}, {reason}) ---\n{snippet}"
                )
                continue

            try:
                mapper = SemanticMapper(file_content)
            except SyntaxError:
                snippet = file_content[:1000] + (
                    "..." if len(file_content) > 1000 else ""
                )
                context.append(
                    f"--- File: {path} (Raw Content due to SyntaxError, Relevance: {relevance_score:.2f}) ---\n{snippet}"
                )
                continue

            summary = mapper.get_summary()
            matches = []

            # V2: If smart scoping is active and we have direct matches from impact analysis
            # Use those matches instead of keyword matching
            if use_smart_scoping and match_details.get("direct_matches"):
                # Use direct matches from TaskImpactAnalyzer
                direct_matches = match_details["direct_matches"]

                # Process function matches
                for func_name in direct_matches.get("functions", []):
                    # Handle both simple names and qualified names (Class.method)
                    if "." in func_name:
                        # Qualified name - add as-is
                        matches.append(func_name)
                    else:
                        # Simple name - check if it's a top-level function
                        for func in summary["functions"]:
                            if func["name"] == func_name:
                                matches.append(func_name)

                # Process class matches
                for class_name in direct_matches.get("classes", []):
                    matches.append(class_name)
                    # Add all methods for matched classes
                    for cls in summary["classes"]:
                        if cls["name"] == class_name:
                            for method in cls["methods"]:
                                matches.append(method["name"])

                # Process module matches (include entire file)
                if direct_matches.get("modules"):
                    # If module matches, include all top-level items
                    for func in summary["functions"]:
                        matches.append(func["name"])
                    for cls in summary["classes"]:
                        matches.append(cls["name"])
                        for method in cls["methods"]:
                            matches.append(method["name"])

                # Also include keyword matches for broader coverage
                for keyword in direct_matches.get("keywords", []):
                    # Try to find functions/methods containing this keyword
                    for func in summary["functions"]:
                        if keyword.lower() in func["name"].lower():
                            matches.append(func["name"])
                    for cls in summary["classes"]:
                        if keyword.lower() in cls["name"].lower():
                            matches.append(cls["name"])
                        for method in cls["methods"]:
                            if keyword.lower() in method["name"].lower():
                                matches.append(method["name"])

                # If still no matches, fall back to keyword matching
                if not matches:
                    for func in summary["functions"]:
                        if any(kw in func["name"].lower() for kw in keywords):
                            matches.append(func["name"])
                    for cls in summary["classes"]:
                        if any(kw in cls["name"].lower() for kw in keywords):
                            matches.append(cls["name"])
                        else:
                            for method in cls["methods"]:
                                if any(kw in method["name"].lower() for kw in keywords):
                                    matches.append(method["name"])
            else:
                # Legacy V1: Fallback to keyword matching
                # Check top-level functions
                for func in summary["functions"]:
                    if any(kw in func["name"].lower() for kw in keywords):
                        matches.append(func["name"])

                # Check classes and their methods
                for cls in summary["classes"]:
                    if any(kw in cls["name"].lower() for kw in keywords):
                        matches.append(cls["name"])
                    else:
                        for method in cls["methods"]:
                            if any(kw in method["name"].lower() for kw in keywords):
                                matches.append(method["name"])

            if matches:
                snippets = mapper.get_relevant_nodes(list(set(matches)))
                reason = match_details.get("reason", "Matched by keywords")
                context.append(
                    f"--- File: {path} (Relevance: {relevance_score:.2f}, {reason}) ---\n{snippets}"
                )
            else:
                # Provide a shallow summary if no direct matches found
                summ_parts = []
                for cls in summary["classes"]:
                    methods = ", ".join([m["name"] for m in cls["methods"]])
                    summ_parts.append(f"Class: {cls['name']} (Methods: {methods})")
                for func in summary["functions"]:
                    summ_parts.append(f"Function: {func['name']}")

                summ_str = "\n".join(summ_parts)
                reason = match_details.get("reason", "Summary only - no direct matches")
                context.append(
                    f"--- File: {path} (Relevance: {relevance_score:.2f}, {reason}) ---\n{summ_str}"
                )

        final_context = "\n\n".join(context)

        # Store in cache for future reuse
        self._cache_context(
            cache_key, final_context, task_query, task_title, files, use_smart_scoping
        )

        return final_context

    def get_progressive_context(
        self,
        task_query: str,
        files: List[str],
        task_type: str = "general",
        initial_level: ContextLevel = ContextLevel.IMMEDIATE,
        max_level: ContextLevel = ContextLevel.PROJECT,
        use_smart_scoping: bool = True,
        task_title: str = "",
        acceptance_criteria: str = "",
        force_refresh: bool = False,
    ) -> Tuple[str, Dict]:
        """
        Get progressive context starting from minimal level, expanding as needed.

        Implements V5 progressive context loading:
        - Starts with minimal context (L0: immediate file only)
        - Expands to higher levels only if needed
        - Learns optimal starting level per task type
        - Tracks expansion statistics for learning

        Args:
            task_query: Query string for matching code
            files: List of file paths to analyze
            task_type: Type of task (e.g., "bug_fix", "new_feature", "refactor")
            initial_level: Starting context level (default: L0)
            max_level: Maximum context level to expand to
            use_smart_scoping: Use AST-based impact analysis
            task_title: Title of task
            acceptance_criteria: Acceptance criteria for task
            force_refresh: Force refresh of cache

        Returns:
            Tuple of (context_string, context_info_dict)
            - context_string: The context content
            - context_info_dict: Information about context including level, expansion, etc.

        Examples:
            >>> engine = ContextEngine(workspace_root=".")
            >>> context, info = engine.get_progressive_context(
            ...     task_query="add user authentication",
            ...     files=["auth.py"],
            ...     task_type="new_feature",
            ...     initial_level=ContextLevel.IMMEDIATE
            ... )
            >>> print(f"Context at level {info['final_level']}")
            >>> print(f"Expanded {info['expansion_count']} times")
        """
        # Step 1: Determine starting level (use learned optimal or default)
        starting_level = self._get_starting_level(task_type, initial_level)

        # Step 2: Initialize context info
        context_info = {
            "starting_level": starting_level.value,
            "final_level": starting_level.value,
            "expansion_count": 0,
            "task_type": task_type,
            "files_analyzed": len(files),
            "estimated_tokens": 0,
            "expansion_reason": None,
        }

        # Step 3: Get context at starting level
        current_level = starting_level
        context = self._get_context_at_level(
            current_level,
            task_query,
            files,
            use_smart_scoping,
            task_title,
            acceptance_criteria,
            force_refresh,
            context_info,
        )

        # Step 4: Check if context is sufficient
        while current_level < max_level and not self._is_context_sufficient(
            context, current_level, task_type, context_info
        ):
            # Expand to next level
            next_level = ContextLevel(current_level.value + 1)
            context_info["expansion_count"] += 1
            current_level = next_level

            # Get expanded context
            context = self._get_context_at_level(
                current_level,
                task_query,
                files,
                use_smart_scoping,
                task_title,
                acceptance_criteria,
                force_refresh,
                context_info,
            )

            # Track expansion reason
            if current_level == ContextLevel.RECENT:
                context_info["expansion_reason"] = "Insufficient immediate context"
            elif current_level == ContextLevel.SESSION:
                context_info["expansion_reason"] = "Insufficient recent context"
            elif current_level == ContextLevel.PROJECT:
                context_info["expansion_reason"] = "Insufficient session context"

        # Step 5: Update final level in info
        context_info["final_level"] = current_level.value

        # Step 6: Update statistics
        self._update_context_level_stats(current_level.value)
        self._update_expansion_stats(task_type, starting_level, current_level)

        # Step 7: Learn optimal level if task succeeded
        # (This is called separately after task completion)
        # self._record_task_outcome(task_type, starting_level, current_level, success)

        return context, context_info

    def _initialize_context_levels(self) -> Dict[ContextLevel, ContextLevelInfo]:
        """
        Initialize context level definitions.

        Returns:
            Dictionary mapping ContextLevel to ContextLevelInfo
        """
        return {
            ContextLevel.IMMEDIATE: ContextLevelInfo(
                level=ContextLevel.IMMEDIATE,
                name="Immediate",
                description="Current file and immediate dependencies only",
                token_multiplier=1.0,
                average_success_rate=0.70,  # Conservative estimate
                expansion_count=0,
            ),
            ContextLevel.RECENT: ContextLevelInfo(
                level=ContextLevel.RECENT,
                name="Recent",
                description="Add upstream/downstream functions",
                token_multiplier=2.5,
                average_success_rate=0.85,
                expansion_count=0,
            ),
            ContextLevel.SESSION: ContextLevelInfo(
                level=ContextLevel.SESSION,
                name="Session",
                description="Add session history and patterns",
                token_multiplier=5.0,
                average_success_rate=0.92,
                expansion_count=0,
            ),
            ContextLevel.PROJECT: ContextLevelInfo(
                level=ContextLevel.PROJECT,
                name="Project",
                description="Full project context",
                token_multiplier=10.0,
                average_success_rate=0.98,
                expansion_count=0,
            ),
        }

    def _get_starting_level(
        self, task_type: str, default_level: ContextLevel
    ) -> ContextLevel:
        """
        Get starting context level for a task type.

        Uses learned optimal level if available, otherwise uses default.

        Args:
            task_type: Type of task
            default_level: Default starting level

        Returns:
            ContextLevel to start with
        """
        # Use learned optimal level if we have enough data
        if task_type in self._optimal_levels:
            level_info = self._context_levels[self._optimal_levels[task_type]]
            if level_info.expansion_count >= 5:  # Require minimum samples
                return self._optimal_levels[task_type]

        # Use default
        return default_level

    def _get_context_at_level(
        self,
        level: ContextLevel,
        task_query: str,
        files: List[str],
        use_smart_scoping: bool,
        task_title: str,
        acceptance_criteria: str,
        force_refresh: bool,
        context_info: Dict,
    ) -> str:
        """
        Get context at a specific context level.

        Args:
            level: Context level to retrieve
            task_query: Task query string
            files: List of file paths
            use_smart_scoping: Whether to use smart scoping
            task_title: Task title
            acceptance_criteria: Acceptance criteria
            force_refresh: Force refresh cache
            context_info: Context info dictionary to update

        Returns:
            Context string at specified level
        """
        level_info = self._context_levels[level]

        # Adjust file scope based on level
        if level == ContextLevel.IMMEDIATE:
            # Only current file
            scoped_files = files[:1] if files else files
            max_depth = 0  # No dependency traversal
        elif level == ContextLevel.RECENT:
            # Current file + direct dependencies
            scoped_files = files
            max_depth = 1  # One level of dependency
        elif level == ContextLevel.SESSION:
            # All files in task + dependencies
            scoped_files = files
            max_depth = 2  # Two levels of dependency
        else:  # PROJECT
            # All files + full dependencies
            scoped_files = files
            max_depth = 3  # Full dependency traversal

        # Get context using existing get_pruned_context method
        context = self.get_pruned_context(
            task_query=task_query,
            files=scoped_files,
            use_smart_scoping=use_smart_scoping,
            task_title=task_title,
            acceptance_criteria=acceptance_criteria,
            force_refresh=force_refresh,
        )

        # Update context info with estimated tokens
        estimated_tokens = len(context.split()) * level_info.token_multiplier
        context_info["estimated_tokens"] = int(estimated_tokens)

        return context

    def _is_context_sufficient(
        self,
        context: str,
        current_level: ContextLevel,
        task_type: str,
        context_info: Dict,
    ) -> bool:
        """
        Determine if current context is sufficient for the task.

        Uses heuristics to predict if expansion is needed:
        - Check context size (too small = insufficient)
        - Check task complexity (complex tasks need more context)
        - Check historical success rate at current level
        - Check expansion frequency (if always expanding, start higher)

        Args:
            context: Current context string
            current_level: Current context level
            task_type: Type of task
            context_info: Context info dictionary

        Returns:
            True if context is sufficient, False if expansion needed
        """
        # Heuristic 1: Check context size
        context_lines = context.count("\n")
        min_lines = 10 * (current_level.value + 1)  # More lines needed at higher levels
        if context_lines < min_lines:
            return False

        # Heuristic 2: Check estimated token count
        # If very low tokens, might be insufficient
        if context_info.get("estimated_tokens", 0) < 500:
            return False

        # Heuristic 3: Check task type complexity
        # Complex tasks typically need more context
        complex_tasks = {"refactor", "architecture", "multi_file_feature"}
        if task_type in complex_tasks and current_level.value < 2:
            return False

        # Heuristic 4: Check historical expansion frequency
        # If this task type always requires expansion, start higher
        if task_type in self._expansion_stats:
            stats = self._expansion_stats[task_type]
            avg_final_level = stats.get("avg_final_level", 0)
            if avg_final_level > current_level.value + 1:
                return False  # Usually needs higher level

        # Heuristic 5: Check success rate at current level
        level_info = self._context_levels[current_level]
        if level_info.average_success_rate < 0.75 and current_level.value < 3:
            return False

        # Default: context is sufficient
        return True

    def _update_context_level_stats(self, level: int) -> None:
        """
        Update usage statistics for context level.

        Args:
            level: Context level value (0-3)
        """
        self._level_usage_stats[level] = self._level_usage_stats.get(level, 0) + 1

    def _update_expansion_stats(
        self, task_type: str, starting_level: ContextLevel, final_level: ContextLevel
    ) -> None:
        """
        Update expansion statistics for task type.

        Tracks:
        - Average final level
        - Average expansion count
        - Starting level success rate

        Args:
            task_type: Type of task
            starting_level: Starting context level
            final_level: Final context level
        """
        if task_type not in self._expansion_stats:
            self._expansion_stats[task_type] = {
                "count": 0,
                "total_final_level": 0,
                "total_expansion_count": 0,
                "avg_final_level": 0.0,
                "avg_expansion_count": 0.0,
            }

        stats = self._expansion_stats[task_type]
        stats["count"] += 1
        stats["total_final_level"] += final_level.value
        stats["total_expansion_count"] += (final_level.value - starting_level.value)

        # Calculate averages
        stats["avg_final_level"] = stats["total_final_level"] / stats["count"]
        stats["avg_expansion_count"] = stats["total_expansion_count"] / stats["count"]

    def record_task_outcome(
        self,
        task_type: str,
        starting_level: ContextLevel,
        final_level: ContextLevel,
        success: bool,
    ) -> None:
        """
        Record task outcome for learning optimal levels.

        Updates success rates for context levels and learns optimal starting level.

        Args:
            task_type: Type of task
            starting_level: Starting context level
            final_level: Final context level
            success: Whether task succeeded at this level

        Examples:
            >>> engine = ContextEngine()
            >>> engine.get_progressive_context(...)  # Task executed
            >>> engine.record_task_outcome(
            ...     task_type="bug_fix",
            ...     starting_level=ContextLevel.IMMEDIATE,
            ...     final_level=ContextLevel.RECENT,
            ...     success=True
            ... )
        """
        # Update success rate for final level
        level_info = self._context_levels[final_level]
        total_attempts = level_info.expansion_count + 1
        success_rate = (
            (level_info.average_success_rate * level_info.expansion_count + (1.0 if success else 0.0))
            / total_attempts
        )
        level_info.average_success_rate = success_rate
        level_info.expansion_count = total_attempts

        # Learn optimal starting level for this task type
        # Optimal level = highest level that consistently succeeds without expansion
        if task_type not in self._optimal_levels:
            self._optimal_levels[task_type] = starting_level
        else:
            current_optimal = self._optimal_levels[task_type]
            stats = self._expansion_stats.get(task_type, {})

            # If starting level succeeds without expansion > 80% of time, it's optimal
            if success and starting_level == final_level:
                success_rate_no_expansion = stats.get("avg_expansion_count", 0) < 0.2
                if success_rate_no_expansion:
                    self._optimal_levels[task_type] = starting_level

    def get_optimal_levels(self) -> Dict[str, ContextLevel]:
        """
        Get learned optimal context levels per task type.

        Returns:
            Dictionary mapping task type to optimal context level
        """
        return self._optimal_levels.copy()

    def get_expansion_stats(self) -> Dict[str, Dict]:
        """
        Get expansion statistics for all task types.

        Returns:
            Dictionary of task type to expansion statistics
        """
        return self._expansion_stats.copy()

    def get_level_usage_stats(self) -> Dict[int, int]:
        """
        Get usage statistics for context levels.

        Returns:
            Dictionary mapping level value to usage count
        """
        return self._level_usage_stats.copy()

    def get_context_level_info(self, level: ContextLevel) -> Optional[ContextLevelInfo]:
        """
        Get information about a specific context level.

        Args:
            level: Context level to query

        Returns:
            ContextLevelInfo or None if level not found
        """
        return self._context_levels.get(level)

    def get_all_context_levels(self) -> Dict[ContextLevel, ContextLevelInfo]:
        """
        Get all context level definitions.

        Returns:
            Dictionary mapping ContextLevel to ContextLevelInfo
        """
        return self._context_levels.copy()

    def get_smart_file_scope(
        self,
        task_title: str,
        acceptance_criteria: str,
        candidate_files: Optional[List[str]] = None,
        max_depth: int = 3,
    ) -> List[Dict]:
        """
        Implement intelligent file scoping based on task impact analysis.

        Automatically determines which files to analyze for a given task by:
        1. Using TaskImpactAnalyzer to identify directly affected files
        2. Using DependencyTraverser to find indirect dependencies in dependency chains
        3. Combining both sources to create a comprehensive file list with relevance scores
        4. Filtering out files that are irrelevant (low impact scores)

        Args:
            task_title: Title of the task
            acceptance_criteria: Acceptance criteria for the task
            candidate_files: Optional list of candidate files (if None, scans all files)
            max_depth: Maximum depth for dependency traversal (default: 3)

        Returns:
            List of dictionaries with keys:
                - file_path: Relative path to the file
                - relevance_score: Combined relevance score (0-1)
                - impact_score: From TaskImpactAnalyzer (0-1)
                - dependency_score: From dependency chain analysis (0-1)
                - confidence: Overall confidence level (low/medium/high)
                - match_details: Details about why this file was included
        """
        # Step 1: Use TaskImpactAnalyzer to get initial file list
        impact_analyzer = TaskImpactAnalyzer(self.root)
        impact_analysis = impact_analyzer.analyze_task_impact(
            task_title, acceptance_criteria
        )

        # Get impact files from analysis (include low confidence for better coverage)
        impact_files = {
            f["file_path"]: {
                "impact_score": f["impact_score"],
                "matches": f["matches"],
                "confidence": f["confidence"],
            }
            for f in impact_analysis["affected_files"]
        }

        # If candidate_files provided, filter to those in candidate list
        if candidate_files:
            candidate_set = set(candidate_files)
            impact_files = {k: v for k, v in impact_files.items() if k in candidate_set}

        # Step 2: Load semantic mappers for dependency analysis
        semantic_mappers = self._load_semantic_mappers(impact_files.keys())

        # Step 3: Use DependencyTraverser to find indirect dependencies
        dependency_traverser = DependencyTraverser(semantic_mappers)
        dependency_scores = self._analyze_dependency_chains(
            impact_files, impact_analysis, dependency_traverser, max_depth
        )

        # Step 4: Combine impact and dependency scores
        scoped_files = self._combine_scores(
            impact_files, dependency_scores, impact_analysis
        )

        # Step 5: Sort by combined relevance score (descending)
        scoped_files.sort(key=lambda x: x["relevance_score"], reverse=True)

        return scoped_files

    def _load_semantic_mappers(
        self, file_paths: List[str]
    ) -> Dict[str, SemanticMapper]:
        """
        Load semantic mappers for the given file paths.

        Args:
            file_paths: List of relative file paths

        Returns:
            Dictionary mapping file paths to SemanticMapper instances
        """
        mappers = {}

        for file_path in file_paths:
            full_path = os.path.join(self.root, file_path)

            if not os.path.exists(full_path):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    source_code = f.read()

                mapper = SemanticMapper(source_code)
                mappers[file_path] = mapper

            except Exception as e:
                # Skip files that cannot be parsed
                continue

        return mappers

    def _analyze_dependency_chains(
        self,
        impact_files: Dict,
        impact_analysis: Dict,
        dependency_traverser: DependencyTraverser,
        max_depth: int,
    ) -> Dict:
        """
        Analyze dependency chains to find indirect dependencies.

        Args:
            impact_files: Dictionary of impact files from TaskImpactAnalyzer
            impact_analysis: Full impact analysis results
            dependency_traverser: DependencyTraverser instance
            max_depth: Maximum traversal depth

        Returns:
            Dictionary mapping file paths to dependency scores
        """
        dependency_scores = {}

        # Get all target entities from impact analysis
        target_functions = impact_analysis.get("target_functions", [])
        target_classes = impact_analysis.get("target_classes", [])

        # For each impact file, analyze its dependency chain
        for file_path in impact_files.keys():
            if file_path not in dependency_traverser.semantic_mappers:
                continue

            mapper = dependency_traverser.semantic_mappers[file_path]
            call_graph = mapper.get_call_graph()

            # For each target entity in this file, analyze its dependencies
            file_dependency_score = 0.0
            analyzed_entities = set()

            # Check target functions
            for func_name in target_functions:
                normalized_name = self._normalize_function_name(func_name, call_graph)
                if normalized_name in call_graph:
                    analyzed_entities.add(normalized_name)

            # Check target classes and their methods
            for cls_name in target_classes:
                summary = mapper.get_summary()
                for cls in summary["classes"]:
                    if cls["name"] == cls_name:
                        for method in cls["methods"]:
                            method_full_name = f"{cls['name']}.{method['name']}"
                            if method_full_name in call_graph:
                                analyzed_entities.add(method_full_name)

            # For each analyzed entity, get its transitive impact
            entity_count = len(analyzed_entities)
            if entity_count > 0:
                total_upstream = 0
                total_downstream = 0

                for entity_name in analyzed_entities:
                    impact = dependency_traverser.get_transitive_impact(
                        entity_name, file_path, max_depth
                    )
                    total_upstream += impact["total_upstream"]
                    total_downstream += impact["total_downstream"]

                # Calculate dependency score
                # Higher score = more dependencies = more likely to be in impact chain
                avg_upstream = total_upstream / entity_count
                avg_downstream = total_downstream / entity_count

                # Normalize to 0-1 range
                dependency_score = min((avg_upstream + avg_downstream) / 20.0, 1.0)

                # Boost score if both upstream and downstream exist
                if avg_upstream > 0 and avg_downstream > 0:
                    dependency_score = min(dependency_score * 1.2, 1.0)

                dependency_scores[file_path] = dependency_score

        return dependency_scores

    def _combine_scores(
        self, impact_files: Dict, dependency_scores: Dict, impact_analysis: Dict
    ) -> List[Dict]:
        """
        Combine impact scores and dependency scores into final relevance scores.

        Args:
            impact_files: Dictionary of impact files with impact scores
            dependency_scores: Dictionary of dependency scores
            impact_analysis: Full impact analysis results

        Returns:
            List of file dictionaries with combined relevance scores
        """
        scoped_files = []

        # Weights for combining scores
        impact_weight = 0.7  # Direct impact is more important
        dependency_weight = 0.3  # Dependency chain is secondary

        for file_path, impact_data in impact_files.items():
            impact_score = impact_data["impact_score"]
            dependency_score = dependency_scores.get(file_path, 0.0)

            # Combined relevance score
            relevance_score = (impact_score * impact_weight) + (
                dependency_score * dependency_weight
            )

            # Round to 3 decimal places
            relevance_score = round(relevance_score, 3)

            # Determine overall confidence
            if relevance_score >= 0.7:
                confidence = "high"
            elif relevance_score >= 0.4:
                confidence = "medium"
            else:
                confidence = "low"

            # Create match details
            match_details = {
                "direct_matches": impact_data["matches"],
                "in_impact_chain": dependency_score > 0.1,
                "reason": (
                    "Direct impact"
                    if dependency_score < 0.1
                    else "Impact + dependency chain"
                ),
            }

            scoped_files.append(
                {
                    "file_path": file_path,
                    "relevance_score": relevance_score,
                    "impact_score": impact_score,
                    "dependency_score": round(dependency_score, 3),
                    "confidence": confidence,
                    "match_details": match_details,
                }
            )

        return scoped_files

    def _normalize_function_name(self, name: str, call_graph: Dict[str, List]) -> str:
        """
        Normalize function name to handle different naming conventions.

        Args:
            name: Function/method name to normalize
            call_graph: Call graph to use for normalization

        Returns:
            Normalized function name
        """
        # If the exact name exists, return it
        if name in call_graph:
            return name

        # Check if it's a simple method name that exists as 'Class.method'
        for key in call_graph.keys():
            if key.endswith(f".{name}"):
                return key

        return name

    def _generate_cache_key(
        self,
        task_query: str,
        files: List[str],
        use_smart_scoping: bool,
        task_title: str,
        acceptance_criteria: str,
    ) -> str:
        """
        Generate a unique cache key for context memoization.

        The key is based on:
        - Task keywords (extracted from query and title)
        - Set of files being analyzed
        - Smart scoping mode

        Args:
            task_query: Task query string
            files: List of file paths
            use_smart_scoping: Whether smart scoping is enabled
            task_title: Task title
            acceptance_criteria: Acceptance criteria

        Returns:
            str: Unique cache key (MD5 hash)
        """
        # Extract keywords from task_query and task_title
        keywords = self._extract_keywords(task_query, task_title)
        keywords_str = "|".join(sorted(keywords))

        # Create normalized file set string
        files_str = "|".join(sorted(files))

        # Combine all factors
        key_components = [keywords_str, files_str, str(use_smart_scoping)]

        key_string = "::".join(key_components)

        # Generate MD5 hash for compact key
        return hashlib.md5(key_string.encode()).hexdigest()

    def _extract_keywords(self, task_query: str, task_title: str) -> Set[str]:
        """
        Extract meaningful keywords from task query and title.

        Args:
            task_query: Task query string
            task_title: Task title

        Returns:
            Set of keywords (lowercase, >2 chars)
        """
        keywords = set()

        # Extract from task_query
        for word in task_query.lower().replace("_", " ").split():
            if len(word) > 2:
                keywords.add(word)

        # Extract from task_title
        for word in task_title.lower().replace("_", " ").split():
            if len(word) > 2:
                keywords.add(word)

        return keywords

    def _cache_context(
        self,
        cache_key: str,
        context: str,
        task_query: str,
        task_title: str,
        files: List[str],
        use_smart_scoping: bool,
    ) -> None:
        """
        Store context collection in memoization cache.

        Args:
            cache_key: Unique cache key
            context: Context string to cache
            task_query: Task query for metadata
            task_title: Task title for metadata
            files: List of files for metadata
            use_smart_scoping: Whether smart scoping was used
        """
        self._context_cache[cache_key] = {
            "context": context,
            "task_query": task_query,
            "task_title": task_title,
            "files": sorted(files),
            "use_smart_scoping": use_smart_scoping,
            "timestamp": self._get_file_modification_time(files),
            "context_size": len(context),
        }

    def _get_file_modification_time(self, files: List[str]) -> float:
        """
        Get the latest modification time among all files.

        Used for cache invalidation when files change.

        Args:
            files: List of file paths (relative to root)

        Returns:
            float: Latest modification timestamp
        """
        latest_time = 0.0

        for file_path in files:
            full_path = os.path.join(self.root, file_path)
            if os.path.exists(full_path):
                mtime = os.path.getmtime(full_path)
                latest_time = max(latest_time, mtime)

        return latest_time

    def invalidate_cache_for_files(self, modified_files: List[str]) -> int:
        """
        Invalidate cache entries that reference modified files.

        Should be called after git commits to keep cache consistent.

        Args:
            modified_files: List of file paths that were modified

        Returns:
            int: Number of cache entries invalidated
        """
        invalidated_count = 0
        keys_to_remove = []

        # Find cache entries that reference modified files
        for cache_key, entry in self._context_cache.items():
            entry_files = set(entry["files"])
            modified_set = set(modified_files)

            # Check if any file in cache entry was modified
            if entry_files & modified_set:
                keys_to_remove.append(cache_key)

        # Remove invalidated entries
        for key in keys_to_remove:
            del self._context_cache[key]
            invalidated_count += 1

        return invalidated_count

    def get_similar_cached_context(
        self, task_query: str, task_title: str, similarity_threshold: float = 0.6
    ) -> Optional[Dict]:
        """
        Find cached context with similar task keywords (fuzzy matching).

        Useful for reusing context from similar tasks even when exact match fails.

        Args:
            task_query: Task query string
            task_title: Task title
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Dictionary with cached context and similarity info, or None
        """
        target_keywords = self._extract_keywords(task_query, task_title)

        best_match = None
        best_similarity = 0.0

        for cache_key, entry in self._context_cache.items():
            cached_keywords = self._extract_keywords(
                entry["task_query"], entry["task_title"]
            )

            # Calculate Jaccard similarity
            intersection = len(target_keywords & cached_keywords)
            union = len(target_keywords | cached_keywords)

            if union > 0:
                similarity = intersection / union

                if similarity > best_similarity and similarity >= similarity_threshold:
                    best_similarity = similarity
                    best_match = {
                        "context": entry["context"],
                        "similarity": similarity,
                        "cache_key": cache_key,
                        "original_task": entry["task_title"],
                        "shared_keywords": target_keywords & cached_keywords,
                    }

        return best_match

    def update_context_incrementally(
        self,
        modified_files: List[str],
        task_title: str,
        acceptance_criteria: str = "",
        max_depth: int = 3,
    ) -> Dict[str, int]:
        """
        Update cached contexts incrementally after task completion.

        This method:
        1. Uses git diff to identify changed files if not provided
        2. Re-analyzes only changed files (not entire codebase)
        3. Invalidates AST cache entries for modified files
        4. Updates dependency chains affected by changes
        5. Maintains cache consistency across task executions

        Args:
            modified_files: List of files that were modified (if None, uses git diff)
            task_title: Title of the completed task
            acceptance_criteria: Acceptance criteria (for smart scoping)
            max_depth: Maximum depth for dependency chain analysis

        Returns:
            dict: Statistics about the update including:
                - files_analyzed: Number of files re-analyzed
                - cache_entries_updated: Number of context cache entries updated
                - ast_cache_invalidated: Number of AST cache entries invalidated
                - dependency_chains_updated: Number of dependency chains updated
        """
        self._cache_updates += 1

        # Step 1: If no modified files provided, use git diff to detect changes
        if modified_files is None or len(modified_files) == 0:
            modified_files = self._get_changed_files_from_git()

        if not modified_files:
            return {
                "files_analyzed": 0,
                "cache_entries_updated": 0,
                "ast_cache_invalidated": 0,
                "dependency_chains_updated": 0,
            }

        # Step 2: Invalidate AST cache for modified files
        ast_cache_invalidated = 0
        for file_path in modified_files:
            full_path = os.path.join(self.root, file_path)
            if os.path.exists(full_path):
                # Invalidate AST cache entries for this file
                self.cache_manager.invalidate(full_path)
                ast_cache_invalidated += 1

        # Step 3: Identify affected dependency chains
        affected_dependency_files = self._identify_affected_dependencies(
            modified_files, max_depth
        )

        # Step 4: Invalidate context cache entries that reference affected files
        all_affected_files = set(modified_files) | set(affected_dependency_files)
        context_entries_invalidated = self.invalidate_cache_for_files(
            list(all_affected_files)
        )

        # Step 5: Re-analyze only changed files and update dependency chains
        files_analyzed = len(modified_files)
        dependency_chains_updated = len(affected_dependency_files)

        # Update cache entries that were affected
        cache_entries_updated = 0
        for cache_key, entry in self._context_cache.items():
            entry_files = set(entry["files"])

            # Check if this cache entry references any affected file
            if entry_files & all_affected_files:
                # Re-generate context for affected entry
                new_context = self.get_pruned_context(
                    entry["task_query"],
                    entry["files"],
                    entry["use_smart_scoping"],
                    entry["task_title"],
                    "",
                    force_refresh=True,
                )

                # Update the cache entry
                entry["context"] = new_context
                entry["timestamp"] = self._get_file_modification_time(entry["files"])
                entry["context_size"] = len(new_context)
                cache_entries_updated += 1

        return {
            "files_analyzed": files_analyzed,
            "cache_entries_updated": cache_entries_updated,
            "ast_cache_invalidated": ast_cache_invalidated,
            "dependency_chains_updated": dependency_chains_updated,
        }

    def _get_changed_files_from_git(self) -> List[str]:
        """
        Use git diff to identify changed files since last commit.

        Returns:
            List of changed file paths relative to workspace root
        """
        try:
            # Get list of changed Python files
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=self.root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return []

            changed_files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip() and line.strip().endswith(".py"):
                    # Get relative path from workspace root
                    file_path = line.strip()
                    if os.path.exists(os.path.join(self.root, file_path)):
                        changed_files.append(file_path)

            return changed_files

        except (subprocess.SubprocessError, FileNotFoundError):
            # Git not available or error running git
            return []

    def _identify_affected_dependencies(
        self, modified_files: List[str], max_depth: int
    ) -> List[str]:
        """
        Identify files that are in the dependency chain of modified files.

        This ensures that if a function/class is modified, we also update
        context for files that depend on it.

        Args:
            modified_files: List of files that were modified
            max_depth: Maximum depth for dependency traversal

        Returns:
            List of file paths that are affected by the modifications
        """
        affected_files = set()

        # For each modified file, analyze its dependencies
        for file_path in modified_files:
            full_path = os.path.join(self.root, file_path)

            if not os.path.exists(full_path) or not file_path.endswith(".py"):
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    source_code = f.read()

                mapper = SemanticMapper(source_code)
                call_graph = mapper.get_call_graph()
                summary = mapper.get_summary()

                # Find all functions/classes in this file
                entities = []
                for func in summary["functions"]:
                    entities.append(("function", func["name"]))
                for cls in summary["classes"]:
                    entities.append(("class", cls["name"]))
                    for method in cls["methods"]:
                        entities.append(("method", f"{cls['name']}.{method['name']}"))

                # For each entity, find files that depend on it
                for entity_type, entity_name in entities:
                    # This is a simplified approach - in a full implementation,
                    # we would scan all files to find reverse dependencies
                    # For now, we add files that might be affected based on imports
                    import_deps = mapper.get_import_dependencies()

                    # Check for internal module imports
                    for module in import_deps["modules"]:
                        # If this file imports from another internal module,
                        # that module might be affected by changes here
                        if self._is_internal_module(module):
                            # Try to find the corresponding file
                            potential_file = self._module_to_file_path(module)
                            if potential_file and potential_file not in modified_files:
                                affected_files.add(potential_file)

                    # Check for from imports
                    for module, names in import_deps["from_imports"].items():
                        if self._is_internal_module(module):
                            potential_file = self._module_to_file_path(module)
                            if potential_file and potential_file not in modified_files:
                                affected_files.add(potential_file)

            except (SyntaxError, IOError):
                # Skip files that cannot be parsed
                continue

        return list(affected_files)

    def _is_internal_module(self, module_name: str) -> bool:
        """
        Check if a module name is likely an internal project module.

        This is a heuristic - in a full implementation, this would check
        against a list of known project modules.

        Args:
            module_name: Module name to check

        Returns:
            bool: True if module appears to be internal
        """
        # External packages and stdlib modules are not internal
        external_packages = {
            "os",
            "sys",
            "re",
            "json",
            "math",
            "random",
            "datetime",
            "time",
            "collections",
            "itertools",
            "functools",
            "typing",
            "pathlib",
            "io",
            "csv",
            "pickle",
            "sqlite3",
            "logging",
            "unittest",
            "pytest",
            "argparse",
            "configparser",
            "hashlib",
            "base64",
            "urllib",
            "http",
            "email",
            "xml",
            "html",
            "ast",
            "inspect",
            "types",
            "copy",
            "weakref",
            "gc",
        }

        # Check if any part of the module path is external
        for part in module_name.split("."):
            if part in external_packages:
                return False

        return True

    def _module_to_file_path(self, module_name: str) -> Optional[str]:
        """
        Convert a module name to a potential file path.

        Args:
            module_name: Module name (e.g., 'v1.logic.context_engine')

        Returns:
            str or None: File path if found, None otherwise
        """
        # Try different possible file paths
        possible_paths = [
            module_name.replace(".", "/") + ".py",
            module_name.replace(".", "/", 1) + "/__init__.py",
        ]

        for path in possible_paths:
            full_path = os.path.join(self.root, path)
            if os.path.exists(full_path):
                return path

        return None

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache hit/miss/update counts and rates
        """
        total_requests = self._cache_hits + self._cache_misses

        if total_requests == 0:
            hit_rate = 0.0
        else:
            hit_rate = self._cache_hits / total_requests

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_updates": self._cache_updates,
            "cache_entries": len(self._context_cache),
            "hit_rate": round(hit_rate, 3),
            "total_requests": total_requests,
        }

    def clear_cache(self) -> None:
        """
        Clear all cached contexts.

        Useful for testing or when cache becomes stale.
        """
        self._context_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_updates = 0
