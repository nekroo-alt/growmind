import os
import hashlib
import subprocess
from typing import List, Dict, Optional, Tuple, Set
from v1.data.semantic_mapper import SemanticMapper
from v1.data.cache_manager import get_cache_manager
from v1.logic.task_impact_analyzer import TaskImpactAnalyzer
from v1.logic.dependency_traverser import DependencyTraverser


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

    def get_pruned_context(self, task_query, files, use_smart_scoping=True, task_title="", acceptance_criteria="", force_refresh=False):
        """
        Returns a string containing relevant code snippets or summaries for the given files.
        
        Args:
            task_query: Query string to match against code
            files: List of file paths to analyze
            use_smart_scoping: If True, use AST-based impact analysis (default: True)
            task_title: Title of the task (for smart scoping)
            acceptance_criteria: Acceptance criteria for the task (for smart scoping)
        
        Returns:
            str: Formatted context with relevant code snippets
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
        
        # Use smart file scoping if enabled and task information is provided
        if use_smart_scoping and task_title:
            scored_files = self.get_smart_file_scope(
                task_title, acceptance_criteria, files
            )
            # Filter files by relevance score (threshold: 0.05 to be more inclusive)
            files = [f["file_path"] for f in scored_files if f["relevance_score"] >= 0.05]
        
        context = []
        keywords = {
            w for w in task_query.lower().replace("_", " ").split() if len(w) > 2
        }

        for path in files:
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
                context.append(f"--- File: {path} (Content) ---\n{snippet}")
                continue

            try:
                mapper = SemanticMapper(file_content)
            except SyntaxError:
                snippet = file_content[:1000] + (
                    "..." if len(file_content) > 1000 else ""
                )
                context.append(
                    f"--- File: {path} (Raw Content due to SyntaxError) ---\n{snippet}"
                )
                continue

            summary = mapper.get_summary()
            matches = []

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
                context.append(f"--- File: {path} ---\n{snippets}")
            else:
                # Provide a shallow summary if no direct matches found
                summ_parts = []
                for cls in summary["classes"]:
                    methods = ", ".join([m["name"] for m in cls["methods"]])
                    summ_parts.append(f"Class: {cls['name']} (Methods: {methods})")
                for func in summary["functions"]:
                    summ_parts.append(f"Function: {func['name']}")

                summ_str = "\n".join(summ_parts)
                context.append(f"--- File: {path} (Summary) ---\n{summ_str}")

        final_context = "\n\n".join(context)
        
        # Store in cache for future reuse
        self._cache_context(
            cache_key,
            final_context,
            task_query,
            task_title,
            files,
            use_smart_scoping
        )
        
        return final_context

    def get_smart_file_scope(
        self,
        task_title: str,
        acceptance_criteria: str,
        candidate_files: Optional[List[str]] = None,
        max_depth: int = 3
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
                "confidence": f["confidence"]
            }
            for f in impact_analysis["affected_files"]
        }
        
        # If candidate_files provided, filter to those in candidate list
        if candidate_files:
            candidate_set = set(candidate_files)
            impact_files = {
                k: v for k, v in impact_files.items() 
                if k in candidate_set
            }
        
        # Step 2: Load semantic mappers for dependency analysis
        semantic_mappers = self._load_semantic_mappers(impact_files.keys())
        
        # Step 3: Use DependencyTraverser to find indirect dependencies
        dependency_traverser = DependencyTraverser(semantic_mappers)
        dependency_scores = self._analyze_dependency_chains(
            impact_files,
            impact_analysis,
            dependency_traverser,
            max_depth
        )
        
        # Step 4: Combine impact and dependency scores
        scoped_files = self._combine_scores(
            impact_files,
            dependency_scores,
            impact_analysis
        )
        
        # Step 5: Sort by combined relevance score (descending)
        scoped_files.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return scoped_files
    
    def _load_semantic_mappers(self, file_paths: List[str]) -> Dict[str, SemanticMapper]:
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
        max_depth: int
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
        self,
        impact_files: Dict,
        dependency_scores: Dict,
        impact_analysis: Dict
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
            relevance_score = (impact_score * impact_weight) + (dependency_score * dependency_weight)
            
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
                "reason": "Direct impact" if dependency_score < 0.1 else "Impact + dependency chain"
            }
            
            scoped_files.append({
                "file_path": file_path,
                "relevance_score": relevance_score,
                "impact_score": impact_score,
                "dependency_score": round(dependency_score, 3),
                "confidence": confidence,
                "match_details": match_details
            })
        
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
        acceptance_criteria: str
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
        key_components = [
            keywords_str,
            files_str,
            str(use_smart_scoping)
        ]
        
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
        use_smart_scoping: bool
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
            "context_size": len(context)
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
        self,
        task_query: str,
        task_title: str,
        similarity_threshold: float = 0.6
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
                entry["task_query"],
                entry["task_title"]
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
                        "shared_keywords": target_keywords & cached_keywords
                    }
        
        return best_match
    
    def update_context_incrementally(
        self,
        modified_files: List[str],
        task_title: str,
        acceptance_criteria: str = "",
        max_depth: int = 3
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
                "dependency_chains_updated": 0
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
        context_entries_invalidated = self.invalidate_cache_for_files(list(all_affected_files))
        
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
                    force_refresh=True
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
            "dependency_chains_updated": dependency_chains_updated
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
                text=True
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
        self,
        modified_files: List[str],
        max_depth: int
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
            "os", "sys", "re", "json", "math", "random", "datetime",
            "time", "collections", "itertools", "functools", "typing",
            "pathlib", "io", "csv", "pickle", "sqlite3", "logging",
            "unittest", "pytest", "argparse", "configparser", "hashlib",
            "base64", "urllib", "http", "email", "xml", "html",
            "ast", "inspect", "types", "copy", "weakref", "gc"
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
            "total_requests": total_requests
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
