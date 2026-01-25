import os
import json
from typing import List, Dict, Tuple, Optional
from data.semantic_mapper import SemanticMapper
from llm_base.provider import LLMProvider


class TaskImpactAnalyzer:
    """
    Analyzes task descriptions to predict which code modules/files will be affected.

    Uses LLM to parse natural language task descriptions and maps identified entities
    to actual code elements using semantic maps. Calculates impact scores to prioritize
    context collection.
    """

    def __init__(self, workspace_root="."):
        """
        Initialize the TaskImpactAnalyzer.

        Args:
            workspace_root: Root directory of the project
        """
        self.workspace_root = workspace_root
        self.llm = LLMProvider()
        self.semantic_cache = {}  # Cache semantic maps for files

    def analyze_task_impact(
        self,
        task_title: str,
        acceptance_criteria: str = "",
        project_modules: Optional[List[str]] = None,
    ) -> Dict:
        """
        Analyze a task to predict which files and code elements it will affect.

        Args:
            task_title: Title of the task
            acceptance_criteria: Acceptance criteria for the task
            project_modules: List of project module names for classification

        Returns:
            dict: Impact analysis with keys:
                - target_modules: List of modules likely to be affected
                - target_classes: List of classes likely to be affected
                - target_functions: List of functions likely to be affected
                - affected_files: List of files with impact scores (sorted by score)
                - entity_mappings: Mapping of identified entities to actual code locations
                - analysis_metadata: Metadata about the analysis process
        """
        # Step 1: Parse task description to extract entities
        entities = self._extract_entities_from_task(task_title, acceptance_criteria)

        # Step 2: Scan project files for matching entities
        file_matches = self._find_files_with_entities(entities, project_modules)

        # Step 3: Calculate impact scores for each file
        scored_files = self._calculate_impact_scores(file_matches, entities)

        # Step 4: Sort files by impact score (descending)
        scored_files.sort(key=lambda x: x["impact_score"], reverse=True)

        # Step 5: Extract structured information
        result = {
            "target_modules": entities.get("modules", []),
            "target_classes": entities.get("classes", []),
            "target_functions": entities.get("functions", []),
            "affected_files": scored_files,
            "entity_mappings": file_matches,
            "analysis_metadata": {
                "task_title": task_title,
                "entities_found": sum(
                    len(v) for v in entities.values() if isinstance(v, list)
                ),
                "files_scanned": len(file_matches),
                "high_impact_files": len(
                    [f for f in scored_files if f["impact_score"] >= 0.7]
                ),
            },
        }

        return result

    def _extract_entities_from_task(
        self, task_title: str, acceptance_criteria: str
    ) -> Dict:
        """
        Use LLM to extract module, class, and function references from task description.

        Args:
            task_title: Title of the task
            acceptance_criteria: Acceptance criteria for the task

        Returns:
            dict: Extracted entities with keys: modules, classes, functions, keywords
        """
        system_prompt = (
            "You are a code analysis expert. Extract all references to code entities "
            "from the task description. Return a JSON object with the following keys:\n"
            "- modules: List of module/package names mentioned\n"
            "- classes: List of class names mentioned\n"
            "- functions: List of function/method names mentioned\n"
            "- keywords: List of technical keywords or concepts (e.g., 'database', 'API', 'test')\n"
            "Only extract explicit references. Do not hallucinate entities."
        )

        user_prompt = (
            f"Task Title: {task_title}\n"
            f"Acceptance Criteria: {acceptance_criteria}\n\n"
            "Extract all code entities mentioned above."
        )

        result = self.llm.call(
            system_prompt, user_prompt, temperature=0.3, max_tokens=1024
        )
        response = result["content"]

        # Parse JSON response
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()

            entities = json.loads(response)

            # Ensure all expected keys exist
            entities.setdefault("modules", [])
            entities.setdefault("classes", [])
            entities.setdefault("functions", [])
            entities.setdefault("keywords", [])

        except json.JSONDecodeError:
            # Fallback: Extract entities using regex-based method
            entities = self._extract_keywords_fallback(task_title, acceptance_criteria)

        return entities

    def _extract_keywords_fallback(
        self, task_title: str, acceptance_criteria: str
    ) -> Dict:
        """
        Fallback method to extract entities when LLM is not available or fails.

        Args:
            task_title: Title of the task
            acceptance_criteria: Acceptance criteria for the task

        Returns:
            dict: Extracted entities (modules, classes, functions, keywords)
        """
        import re

        text = f"{task_title} {acceptance_criteria}"

        # Extract potential class names (capitalized words followed by context patterns)
        class_pattern = r"\b([A-Z][a-zA-Z0-9_]*)\b"
        potential_classes = re.findall(class_pattern, text)

        # Filter common non-class capitalized words
        excluded = ["The", "A", "An", "In", "On", "For", "To", "With", "From", "About"]
        classes = list(
            set([c for c in potential_classes if c not in excluded and len(c) > 2])
        )

        # Extract potential function/method names (lowercase_with_underscores or camelCase)
        func_pattern = r"\b([a-z_][a-z0-9_]*)\b"
        potential_functions = re.findall(func_pattern, text)

        # Filter to likely function names (contains underscore or is a common verb)
        common_verbs = [
            "get",
            "set",
            "add",
            "create",
            "update",
            "delete",
            "find",
            "load",
            "save",
            "parse",
            "analyze",
            "build",
            "run",
            "execute",
            "construct",
            "track",
            "implement",
            "identify",
        ]
        functions = list(
            set(
                [
                    f
                    for f in potential_functions
                    if "_" in f or any(verb in f for verb in common_verbs)
                ]
            )
        )

        # Extract module names (lowercase words that appear in file contexts)
        module_pattern = r"\b([a-z][a-z0-9_]*)\b"
        all_lower_words = re.findall(module_pattern, text.lower())

        # Filter to likely module names
        common_modules = [
            "semantic",
            "task",
            "dependency",
            "context",
            "mapper",
            "analyzer",
            "traverser",
            "pruner",
            "engine",
            "planner",
            "implementor",
            "verifier",
            "dispatcher",
            "git_guard",
        ]
        modules = list(
            set(
                [
                    w
                    for w in all_lower_words
                    if any(mod in w for mod in common_modules) or len(w.split("_")) > 1
                ]
            )
        )

        # Common technical keywords
        tech_keywords = [
            "database",
            "api",
            "test",
            "cache",
            "logger",
            "config",
            "import",
            "export",
            "model",
            "view",
            "controller",
            "service",
            "repository",
            "interface",
            "abstract",
            "async",
            "sync",
            "http",
            "json",
            "xml",
            "call",
            "graph",
            "ast",
            "tree",
            "node",
            "edge",
            "upstream",
            "downstream",
            "chain",
            "traversal",
            "bfs",
            "dfs",
            "dependency",
            "semantic",
            "impact",
            "score",
            "prune",
            "scope",
        ]

        text_lower = text.lower()
        keywords = list(set([kw for kw in tech_keywords if kw in text_lower]))

        return {
            "modules": modules,
            "classes": classes,
            "functions": functions,
            "keywords": keywords,
        }

    def _find_files_with_entities(
        self, entities: Dict, project_modules: Optional[List[str]]
    ) -> Dict:
        """
        Scan project files to find those containing the extracted entities.

        Args:
            entities: Extracted entities from task description
            project_modules: List of project module names

        Returns:
            dict: Mapping of file paths to matched entities
        """
        file_matches = {}

        # Get all Python files in the workspace
        python_files = self._get_python_files()

        for file_path in python_files:
            full_path = os.path.join(self.workspace_root, file_path)

            # Get or create semantic map for this file
            semantic_map = self._get_semantic_map(full_path)

            if semantic_map is None:
                continue

            # Check for entity matches
            matches = {
                "modules_matched": [],
                "classes_matched": [],
                "functions_matched": [],
                "keywords_matched": [],
                "file_info": {
                    "path": file_path,
                    "classes": [c["name"] for c in semantic_map.get("classes", [])],
                    "functions": [f["name"] for f in semantic_map.get("functions", [])],
                    "has_classes": len(semantic_map.get("classes", [])) > 0,
                    "has_functions": len(semantic_map.get("functions", [])) > 0,
                },
            }

            # Check for module matches (in file path)
            file_path_lower = file_path.lower()
            for module in entities.get("modules", []):
                if module.lower() in file_path_lower:
                    matches["modules_matched"].append(module)

            # Check for class matches
            file_classes = [c["name"] for c in semantic_map.get("classes", [])]
            for class_name in entities.get("classes", []):
                if class_name in file_classes:
                    matches["classes_matched"].append(class_name)

            # Check for function matches
            file_functions = [f["name"] for f in semantic_map.get("functions", [])]
            for func_name in entities.get("functions", []):
                if func_name in file_functions:
                    matches["functions_matched"].append(func_name)

            # Also check methods within classes
            for cls in semantic_map.get("classes", []):
                for method in cls.get("methods", []):
                    for func_name in entities.get("functions", []):
                        if func_name == method["name"]:
                            matches["functions_matched"].append(
                                f"{cls['name']}.{method['name']}"
                            )

            # Check for keyword matches (lower confidence)
            file_content_lower = semantic_map.get("raw_content", "").lower()
            for keyword in entities.get("keywords", []):
                if keyword.lower() in file_content_lower:
                    matches["keywords_matched"].append(keyword)

            # Only include files with at least one match
            total_matches = (
                len(matches["modules_matched"])
                + len(matches["classes_matched"])
                + len(matches["functions_matched"])
                + len(matches["keywords_matched"])
            )

            if total_matches > 0:
                file_matches[file_path] = matches

        return file_matches

    def _calculate_impact_scores(
        self, file_matches: Dict, entities: Dict
    ) -> List[Dict]:
        """
        Calculate impact scores for each file based on match types and count.

        Args:
            file_matches: Dictionary of file matches from _find_files_with_entities
            entities: Extracted entities from task description

        Returns:
            list: List of files with calculated impact scores
        """
        scored_files = []

        for file_path, matches in file_matches.items():
            # Base score calculation
            score = 0.0

            # High confidence matches (module, class, direct function)
            module_weight = 0.4
            class_weight = 0.3
            function_weight = 0.3
            keyword_weight = 0.1

            # Calculate normalized scores based on number of entities found
            total_modules = len(entities.get("modules", [])) or 1
            total_classes = len(entities.get("classes", [])) or 1
            total_functions = len(entities.get("functions", [])) or 1
            total_keywords = len(entities.get("keywords", [])) or 1

            module_score = (
                len(matches["modules_matched"]) / total_modules
            ) * module_weight
            class_score = (
                len(matches["classes_matched"]) / total_classes
            ) * class_weight
            function_score = (
                len(matches["functions_matched"]) / total_functions
            ) * function_weight
            keyword_score = (
                len(matches["keywords_matched"]) / total_keywords
            ) * keyword_weight

            score = module_score + class_score + function_score + keyword_score

            # Cap score at 1.0
            score = min(score, 1.0)

            # Boost score for files with multiple match types
            match_types = sum(
                [
                    1 if matches["modules_matched"] else 0,
                    1 if matches["classes_matched"] else 0,
                    1 if matches["functions_matched"] else 0,
                    1 if matches["keywords_matched"] else 0,
                ]
            )

            if match_types >= 3:
                score = min(score + 0.1, 1.0)
            elif match_types >= 2:
                score = min(score + 0.05, 1.0)

            # Confidence levels (lowered threshold to "medium" for more inclusive results)
            if score >= 0.5:
                confidence = "high"
            elif score >= 0.2:
                confidence = "medium"
            else:
                confidence = "low"

            scored_files.append(
                {
                    "file_path": file_path,
                    "impact_score": round(score, 3),
                    "confidence": confidence,
                    "matches": {
                        "modules": matches["modules_matched"],
                        "classes": matches["classes_matched"],
                        "functions": matches["functions_matched"],
                        "keywords": matches["keywords_matched"],
                    },
                    "match_count": (
                        len(matches["modules_matched"])
                        + len(matches["classes_matched"])
                        + len(matches["functions_matched"])
                        + len(matches["keywords_matched"])
                    ),
                }
            )

        # Sort by impact score descending
        scored_files.sort(key=lambda x: x["impact_score"], reverse=True)

        return scored_files

    def _get_python_files(self) -> List[str]:
        """
        Get list of all Python files in the workspace.

        Returns:
            list: Relative paths to Python files
        """
        python_files = []

        for root, dirs, files in os.walk(self.workspace_root):
            # Skip common ignore directories
            dirs[:] = [
                d
                for d in dirs
                if d
                not in {
                    ".git",
                    "__pycache__",
                    "node_modules",
                    "build",
                    "dist",
                    "logs",
                    ".idea",
                }
            ]

            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_root)
                    python_files.append(rel_path)

        return python_files

    def _get_semantic_map(self, file_path: str) -> Optional[Dict]:
        """
        Get semantic map for a file, using cache if available.

        Args:
            file_path: Full path to the file

        Returns:
            dict or None: Semantic map or None if file cannot be parsed
        """
        # Check cache first
        if file_path in self.semantic_cache:
            return self.semantic_cache[file_path]

        # Read and parse file
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            mapper = SemanticMapper(source_code)
            summary = mapper.get_summary()

            # Add raw content for keyword matching
            summary["raw_content"] = source_code

            # Cache the result
            self.semantic_cache[file_path] = summary

            return summary

        except Exception as e:
            # Skip files that cannot be parsed
            return None

    def clear_cache(self):
        """Clear the semantic map cache."""
        self.semantic_cache.clear()

    def get_recommended_files(
        self,
        task_title: str,
        acceptance_criteria: str = "",
        max_files: int = 10,
        min_confidence: str = "low",
    ) -> List[str]:
        """
        Get a list of recommended files for a task, filtered by confidence.

        Args:
            task_title: Title of the task
            acceptance_criteria: Acceptance criteria for the task
            max_files: Maximum number of files to return
            min_confidence: Minimum confidence level (low, medium, high)

        Returns:
            list: List of file paths sorted by impact score
        """
        analysis = self.analyze_task_impact(task_title, acceptance_criteria)

        # Filter by confidence level
        confidence_levels = {"low": 0, "medium": 1, "high": 2}
        min_level = confidence_levels.get(min_confidence, 0)

        filtered_files = []
        for file_info in analysis["affected_files"]:
            file_confidence = confidence_levels.get(file_info["confidence"], 0)
            if file_confidence >= min_level:
                filtered_files.append(file_info["file_path"])

        # Return top N files
        return filtered_files[:max_files]
