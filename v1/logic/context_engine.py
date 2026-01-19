import os
from typing import List, Dict, Optional, Tuple
from v1.data.semantic_mapper import SemanticMapper
from v1.logic.task_impact_analyzer import TaskImpactAnalyzer
from v1.logic.dependency_traverser import DependencyTraverser


class ContextEngine:
    """
    Context Engine responsible for pruning and selecting relevant code snippets
    based on the task scope.
    """

    def __init__(self, workspace_root="."):
        self.root = workspace_root

    def get_pruned_context(self, task_query, files, use_smart_scoping=True, task_title="", acceptance_criteria=""):
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

        return "\n\n".join(context)

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
        
        # If no match found, return original
        return name
