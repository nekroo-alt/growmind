from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from ..data.semantic_mapper import SemanticMapper


@dataclass
class DependencyNode:
    """
    Represents a node in the dependency chain.
    """

    name: str
    node_type: str  # "function" or "method"
    context: Optional[str]  # Class name if it's a method, None otherwise
    depth: int
    file_path: str


class DependencyTraverser:
    """
    Traverses dependency chains to collect upstream and downstream dependencies.
    Uses BFS to traverse call graphs with depth limiting to prevent exponential explosion.
    """

    def __init__(self, semantic_mappers: Dict[str, SemanticMapper]):
        """
        Initialize the dependency traverser with semantic mappers for multiple files.

        Args:
            semantic_mappers: Dictionary mapping file paths to SemanticMapper instances
        """
        self.semantic_mappers = semantic_mappers

    def get_upstream_dependencies(
        self, target_name: str, file_path: str, max_depth: int = 5
    ) -> Tuple[List[DependencyNode], Dict[str, List[str]]]:
        """
        Collect all upstream dependencies (what the target calls).

        Args:
            target_name: Name of the function/method to analyze
            file_path: Path to the file containing the target
            max_depth: Maximum traversal depth (default: 5)

        Returns:
            Tuple containing:
                - List of DependencyNode objects in dependency chain
                - Dictionary mapping depth levels to lists of node names
        """
        if file_path not in self.semantic_mappers:
            return [], {}

        mapper = self.semantic_mappers[file_path]
        call_graph = mapper.get_call_graph()

        # Normalize target name
        normalized_target = self._normalize_function_name(target_name, call_graph)

        visited = set()
        dependency_chain = []
        depth_levels = {}

        # Use BFS to traverse upstream dependencies
        queue = [(normalized_target, file_path, 0)]

        while queue:
            current_name, current_file, depth = queue.pop(0)

            if depth > max_depth:
                continue

            # Skip if already visited at this or higher depth
            visit_key = f"{current_name}:{current_file}"
            if visit_key in visited:
                continue
            visited.add(visit_key)

            # Get function information
            node_info = self._get_function_info(current_name, current_file)
            if not node_info:
                continue

            # Create dependency node
            dep_node = DependencyNode(
                name=current_name,
                node_type=node_info["type"],
                context=node_info.get("context"),
                depth=depth,
                file_path=current_file,
            )
            dependency_chain.append(dep_node)

            # Track depth levels
            if depth not in depth_levels:
                depth_levels[depth] = []
            depth_levels[depth].append(current_name)

            # Get calls from this function
            if current_name in call_graph:
                for call_info in call_graph[current_name]:
                    # Skip external calls (system boundaries)
                    if call_info["is_external"]:
                        continue

                    callee_name = call_info["callee"]

                    # Try to get function info to verify it exists
                    # This handles cases where method names might be ambiguous
                    func_info = self._get_function_info(callee_name, current_file)

                    if func_info:
                        # For inter-file calls, we'd need to resolve the file path
                        # For now, assume same file
                        queue.append((callee_name, current_file, depth + 1))

        return dependency_chain, depth_levels

    def get_downstream_consumers(
        self, target_name: str, file_path: str, max_depth: int = 5
    ) -> Tuple[List[DependencyNode], Dict[str, List[str]]]:
        """
        Collect all downstream consumers (functions that call the target).

        Args:
            target_name: Name of the function/method to analyze
            file_path: Path to the file containing the target
            max_depth: Maximum traversal depth (default: 5)

        Returns:
            Tuple containing:
                - List of DependencyNode objects in consumer chain
                - Dictionary mapping depth levels to lists of node names
        """
        consumer_chain = []
        depth_levels = {}

        # Normalize target name
        if file_path in self.semantic_mappers:
            mapper = self.semantic_mappers[file_path]
            call_graph = mapper.get_call_graph()
            normalized_target = self._normalize_function_name(target_name, call_graph)
        else:
            return [], {}

        visited = set()

        # Use BFS to traverse downstream consumers
        queue = [(normalized_target, file_path, 0)]

        while queue:
            current_name, current_file, depth = queue.pop(0)

            if depth > max_depth:
                continue

            # Skip if already visited at this or higher depth
            visit_key = f"{current_name}:{current_file}"
            if visit_key in visited:
                continue
            visited.add(visit_key)

            # Get function information
            node_info = self._get_function_info(current_name, current_file)
            if not node_info:
                continue

            # Create dependency node (skip the root node at depth 0)
            if depth > 0:
                dep_node = DependencyNode(
                    name=current_name,
                    node_type=node_info["type"],
                    context=node_info.get("context"),
                    depth=depth,
                    file_path=current_file,
                )
                consumer_chain.append(dep_node)

                # Track depth levels
                if depth not in depth_levels:
                    depth_levels[depth] = []
                depth_levels[depth].append(current_name)

            # Find all functions that call this one
            for fp in self.semantic_mappers:
                mapper = self.semantic_mappers[fp]
                cg = mapper.get_call_graph()

                for caller_name, calls in cg.items():
                    for call_info in calls:
                        if call_info["callee"] == current_name:
                            caller_node_info = self._get_function_info(caller_name, fp)
                            if caller_node_info:
                                visit_key_caller = f"{caller_name}:{fp}"
                                if visit_key_caller not in visited:
                                    queue.append((caller_name, fp, depth + 1))

        return consumer_chain, depth_levels

    def get_full_dependency_chain(
        self, target_name: str, file_path: str, max_depth: int = 5
    ) -> Dict[str, any]:
        """
        Get both upstream and downstream dependencies in a single call.

        Args:
            target_name: Name of the function/method to analyze
            file_path: Path to the file containing the target
            max_depth: Maximum traversal depth (default: 5)

        Returns:
            Dictionary containing:
                - upstream: List of upstream DependencyNode objects
                - downstream: List of downstream DependencyNode objects
                - upstream_depth_levels: Dict mapping depth to node names (upstream)
                - downstream_depth_levels: Dict mapping depth to node names (downstream)
                - total_nodes: Total number of nodes in dependency chain
        """
        upstream, upstream_levels = self.get_upstream_dependencies(
            target_name, file_path, max_depth
        )
        downstream, downstream_levels = self.get_downstream_consumers(
            target_name, file_path, max_depth
        )

        return {
            "upstream": upstream,
            "downstream": downstream,
            "upstream_depth_levels": upstream_levels,
            "downstream_depth_levels": downstream_levels,
            "total_nodes": len(upstream) + len(downstream),
        }

    def _normalize_function_name(self, name: str, call_graph: Dict[str, List]) -> str:
        """
        Normalize function name to handle different naming conventions.
        For example, 'method' might be referred to as 'Class.method' or just 'method'.

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

    def _get_function_info(self, name: str, file_path: str) -> Optional[Dict]:
        """
        Get information about a function or method from its semantic map.

        Args:
            name: Function/method name
            file_path: Path to the file

        Returns:
            Dictionary with function info or None if not found
        """
        if file_path not in self.semantic_mappers:
            return None

        mapper = self.semantic_mappers[file_path]
        summary = mapper.get_summary()

        # Check top-level functions
        for func in summary["functions"]:
            if func["name"] == name or name == f"{func['name']}":
                return {
                    "type": "function",
                    "context": None,
                    "start_line": func["start_line"],
                    "end_line": func["end_line"],
                }

        # Check class methods
        for cls in summary["classes"]:
            for method in cls["methods"]:
                method_full_name = f"{cls['name']}.{method['name']}"
                if name == method["name"] or name == method_full_name:
                    return {
                        "type": "method",
                        "context": cls["name"],
                        "start_line": method["start_line"],
                        "end_line": method["end_line"],
                    }

        return None

    def get_transitive_impact(
        self, target_name: str, file_path: str, max_depth: int = 5
    ) -> Dict[str, any]:
        """
        Calculate the transitive impact of modifying a function.
        Useful for understanding how far changes will propagate.

        Args:
            target_name: Name of the function/method to analyze
            file_path: Path to the file containing the target
            max_depth: Maximum traversal depth (default: 5)

        Returns:
            Dictionary with impact metrics:
                - direct_callers: List of functions that directly call target
                - direct_callees: List of functions directly called by target
                - total_upstream: Total number of upstream dependencies
                - total_downstream: Total number of downstream consumers
                - max_reach: Maximum depth reached in both directions
                - impact_score: Overall impact score (0-100)
        """
        if file_path not in self.semantic_mappers:
            return {
                "direct_callers": [],
                "direct_callees": [],
                "total_upstream": 0,
                "total_downstream": 0,
                "max_reach": 0,
                "impact_score": 0,
            }

        mapper = self.semantic_mappers[file_path]
        call_graph = mapper.get_call_graph()

        # Normalize target name
        normalized_target = self._normalize_function_name(target_name, call_graph)

        # Get full dependency chain
        chain = self.get_full_dependency_chain(target_name, file_path, max_depth)

        # Get direct callees (depth 1 upstream)
        direct_callees = []
        if normalized_target in call_graph:
            for call_info in call_graph[normalized_target]:
                if not call_info["is_external"]:
                    direct_callees.append(call_info["callee"])

        # Get direct callers (depth 1 downstream)
        direct_callers = []
        for fp in self.semantic_mappers:
            cg = self.semantic_mappers[fp].get_call_graph()
            for caller_name, calls in cg.items():
                for call_info in calls:
                    if call_info["callee"] == normalized_target:
                        direct_callers.append(caller_name)

        # Calculate impact score (0-100)
        # Higher score = more impact
        total_upstream = len(chain["upstream"])
        total_downstream = len(chain["downstream"])
        max_reach = max(
            (
                max(chain["upstream_depth_levels"].keys())
                if chain["upstream_depth_levels"]
                else 0
            ),
            (
                max(chain["downstream_depth_levels"].keys())
                if chain["downstream_depth_levels"]
                else 0
            ),
        )

        # Weighted impact score
        # Direct connections matter more (weight: 10)
        # Indirect connections matter less (weight: 2)
        direct_impact = (len(direct_callers) + len(direct_callees)) * 10
        indirect_impact = (total_upstream + total_downstream) * 2
        depth_impact = max_reach * 5

        total_impact = direct_impact + indirect_impact + depth_impact
        impact_score = min(100, total_impact)  # Cap at 100

        return {
            "direct_callers": direct_callers,
            "direct_callees": direct_callees,
            "total_upstream": total_upstream,
            "total_downstream": total_downstream,
            "max_reach": max_reach,
            "impact_score": impact_score,
        }
