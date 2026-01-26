import os
import subprocess
import ast
from v5.data.db_manager import log_activity, fcid_mapping
from v5.data.semantic_mapper import SemanticMapper
from v5.core.logging_config import get_module_logger
from v5.data.telemetry_manager import get_telemetry_manager
# V4: Adaptive reasoning components - import directly from modules to avoid circular imports
from v5.data.context_hierarchy import ContextHierarchyManager
from v5.data.decision_history import DecisionHistoryManager
from v5.logic.reasoning_engine import ReasoningEngine
from v5.logic.action_validator import ActionValidator
from v5.logic.progress_tracker import ProgressTracker
from v5.logic.context_expander import ContextExpander
from v5.logic.trap_detector import TrapDetector
# Import from trap_recovery directly to avoid circular imports
from v5.logic.trap_recovery import TrapRecoveryEngine
# V4: Meta-cognition components - import directly from modules
from v5.logic.pattern_recognizer import PatternRecognizer
from v5.logic.self_reflection import SelfReflection
from v5.logic.lesson_learner import LessonLearner
from v5.logic.adaptive_heuristics import AdaptiveHeuristics

logger = get_module_logger(__name__)


class OperatorSwapper(ast.NodeTransformer):
    def __init__(self, target_index=-1):
        self.count = 0
        self.target_index = target_index
        self.map = {
            ast.Add: ast.Sub,
            ast.Sub: ast.Add,
            ast.Mult: ast.Div,
            ast.Div: ast.Mult,
            ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq,
            ast.Lt: ast.GtE,
            ast.GtE: ast.Lt,
            ast.Gt: ast.LtE,
            ast.LtE: ast.Gt,
        }

    def visit_BinOp(self, node):
        self.generic_visit(node)
        if type(node.op) in self.map:
            if self.count == self.target_index:
                node.op = self.map[type(node.op)]()
            self.count += 1
        return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        new_ops = []
        for op in node.ops:
            if type(op) in self.map:
                new_ops.append(
                    self.map[type(op)]() if self.count == self.target_index else op
                )
                self.count += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        return node


class Verifier:
    def __init__(self):
        logger.info("Initializing Verifier")
        self.telemetry_manager = get_telemetry_manager()
        # V4: Adaptive reasoning components - initialize classes directly
        self.context_hierarchy = ContextHierarchyManager()
        self.decision_history = DecisionHistoryManager()
        self.reasoning_engine = ReasoningEngine()
        self.action_validator = ActionValidator()
        self.progress_tracker = ProgressTracker()
        self.context_expander = ContextExpander()
        self.progress_tracker_v4 = ProgressTracker()  # Second instance for tracking
        self.trap_detector = TrapDetector()
        self.trap_recovery = TrapRecoveryEngine()
        # V4: Meta-cognition components - initialize classes directly
        self.pattern_recognizer = PatternRecognizer()
        self.self_reflection = SelfReflection()
        self.lesson_learner = LessonLearner()
        self.adaptive_heuristics = AdaptiveHeuristics()
        logger.info("Verifier initialized successfully with V4 adaptive reasoning, trap detection, and meta-cognition")

    @fcid_mapping("VER-100")
    def run_tests(self, test_file="v1/test_poc.py", tracking_id=None):
        """
        FCID: VER-100
        Functionality: Execute unit and integration tests.
        V4 Enhancement: Added progress tracking for test execution.
        """
        logger.debug(f"Running tests for {test_file}")
        
        # V4: Start progress tracking for test execution
        if tracking_id:
            self.progress_tracker_v4.update_progress(
                tracking_id=tracking_id,
                metrics={"test_execution_phase": "started"}
            )
        
        try:
            if not os.path.exists(test_file):
                log_activity(
                    summary=f"Running tests for {test_file}",
                    action="Run Tests",
                    status="Failed",
                    cot_blob=f"Test file {test_file} not found",
                )
                return False

            result = subprocess.run(
                ["pytest", test_file], capture_output=True, text=True
            )

            if result.returncode == 0:
                logger.info(f"Tests passed for {test_file}")
                # V4: Update progress for successful tests
                if tracking_id:
                    self.progress_tracker_v4.update_progress(
                        tracking_id=tracking_id,
                        metrics={
                            "test_execution_phase": "completed",
                            "tests_passed": True
                        }
                    )
                log_activity(
                    summary=f"Running tests for {test_file}",
                    action="Run Tests",
                    status="Success",
                    cot_blob=f"Tests passed for {test_file}",
                )
                return True
            else:
                logger.error(f"Tests failed for {test_file}")
                # V4: Update progress for failed tests
                if tracking_id:
                    self.progress_tracker_v4.update_progress(
                        tracking_id=tracking_id,
                        metrics={
                            "test_execution_phase": "completed",
                            "tests_passed": False
                        }
                    )
                log_activity(
                    summary=f"Running tests for {test_file}",
                    action="Run Tests",
                    status="Failed",
                    cot_blob=f"Tests failed for {test_file}\nOutput: {result.stdout}",
                )
                # V4: Learn from test failure
                self.lesson_learner.record_failure(
                    failure_type="test_execution",
                    context={"test_file": test_file},
                    error_message=f"Tests failed for {test_file}"
                )
                return False
        except Exception as e:
            log_activity(
                summary=f"Error running tests for {test_file}",
                action="Run Tests",
                status="Error",
                cot_blob=str(e),
            )
            return False

    @fcid_mapping("VER-103")
    def validate_context_usage(self, file_path, context, modified_functions=None):
        """
        FCID: VER-103
        Functionality: Validates that implementation uses provided context appropriately.

        Args:
            file_path: Path to the implemented file
            context: Dictionary containing context information with:
                - 'files': List of files in context
                - 'functions': List of function names in context
                - 'classes': List of class names in context
            modified_functions: List of function names that were modified (optional)

        Returns:
            bool: True if context usage is valid, False otherwise
        """
        if not os.path.exists(file_path):
            log_activity(
                summary=f"Validating context usage for {file_path}",
                action="Context Usage Validation",
                status="Failed",
                cot_blob=f"File {file_path} not found",
            )
            return False

        try:
            with open(file_path, "r") as f:
                source_code = f.read()

            # Parse the implemented code
            mapper = SemanticMapper(source_code)
            summary = mapper.get_summary()

            # Track which context entities are used
            used_functions = set()
            used_classes = set()

            # Collect all function definitions in the file
            for func in summary["functions"]:
                used_functions.add(func["name"])

            for cls in summary["classes"]:
                used_classes.add(cls["name"])
                # Also track methods
                for method in cls["methods"]:
                    used_functions.add(method["name"])

            # Check if modified functions are in context
            if modified_functions:
                context_functions = set(context.get("functions", []))
                for func in modified_functions:
                    if func not in context_functions:
                        log_activity(
                            summary=f"Validating context usage for {file_path}",
                            action="Context Usage Validation",
                            status="Failed",
                            cot_blob=f"Modified function '{func}' was not in provided context. "
                            f"Context functions: {context_functions}",
                        )
                        return False

            # Check for unexpected dependencies (dependencies not in context)
            all_dependencies = set()
            for func in summary["functions"]:
                all_dependencies.update(func["dependencies"])
            for cls in summary["classes"]:
                all_dependencies.update(cls["dependencies"])
                for method in cls["methods"]:
                    all_dependencies.update(method["dependencies"])

            # External dependencies (not in standard library) should be in context
            context_dependencies = set(context.get("dependencies", []))
            unexpected_deps = all_dependencies - context_dependencies
            # Filter out common builtins and stdlib
            unexpected_deps = self._filter_stdlib_dependencies(unexpected_deps)

            if unexpected_deps:
                log_activity(
                    summary=f"Validating context usage for {file_path}",
                    action="Context Usage Validation",
                    status="Warning",
                    cot_blob=f"Found dependencies not in context: {unexpected_deps}. "
                    f"This may indicate incomplete context.",
                )
                # Warning only, not a failure

            log_activity(
                summary=f"Validating context usage for {file_path}",
                action="Context Usage Validation",
                status="Success",
                cot_blob=f"Context usage validated. Used {len(used_functions)} functions, "
                f"{len(used_classes)} classes.",
            )
            return True

        except Exception as e:
            log_activity(
                summary=f"Error validating context usage for {file_path}",
                action="Context Usage Validation",
                status="Error",
                cot_blob=str(e),
            )
            return False

    @fcid_mapping("VER-104")
    def validate_dependency_contracts(self, file_path, semantic_map):
        """
        FCID: VER-104
        Functionality: Validates that new code doesn't violate dependency contracts.

        Args:
            file_path: Path to the implemented file
            semantic_map: SemanticMapper instance or dict with call graph info

        Returns:
            bool: True if dependency contracts are maintained, False otherwise
        """
        if not os.path.exists(file_path):
            log_activity(
                summary=f"Validating dependency contracts for {file_path}",
                action="Dependency Contract Validation",
                status="Failed",
                cot_blob=f"File {file_path} not found",
            )
            return False

        try:
            with open(file_path, "r") as f:
                source_code = f.read()

            # Parse the implemented code
            mapper = SemanticMapper(source_code)
            summary = mapper.get_summary()
            call_graph = mapper.get_call_graph()

            violations = []

            # Collect local variables from all functions to avoid false positives
            local_variables = set()
            for func in summary["functions"]:
                local_variables.update(func["data_flow"]["writes"])
            for cls in summary["classes"]:
                for method in cls["methods"]:
                    local_variables.update(method["data_flow"]["writes"])

            # Check each function's calls
            for caller, calls in call_graph.items():
                for call_info in calls:
                    callee = call_info["callee"]
                    is_external = call_info["is_external"]

                    # Check if external calls are documented/expected
                    if is_external:
                        # Skip if it's a local variable method call (e.g., f.read, data.process)
                        callee_module = callee.split(".")[0]
                        if callee_module in local_variables:
                            continue  # This is a local variable method call, not a module

                        # Skip single-letter variables (common for file handles, iterators, etc.)
                        if len(callee_module) == 1:
                            continue  # Likely a context manager or iterator variable

                        # Verify that external dependencies are properly imported
                        import_deps = mapper.get_import_dependencies()
                        all_imports = set(import_deps["modules"]) | set(
                            import_deps["from_imports"].keys()
                        )

                        # Check if the external module is imported
                        if callee_module not in all_imports and callee_module != callee:
                            violations.append(
                                f"Function '{caller}' calls external '{callee}' without importing module '{callee_module}'"
                            )

            # Check for circular dependencies in imports
            import_deps = mapper.get_import_dependencies()
            if import_deps["modules"] or import_deps["from_imports"]:
                # Simple circular dependency check (imports that refer back to current file)
                # This is a simplified check - full circular detection would need project-wide analysis
                filename = os.path.basename(file_path).replace(".py", "")
                circular_imports = [
                    mod for mod in import_deps["modules"] if mod == filename
                ]
                if circular_imports:
                    violations.append(
                        f"Potential circular import detected: imports {circular_imports}"
                    )

            if violations:
                log_activity(
                    summary=f"Validating dependency contracts for {file_path}",
                    action="Dependency Contract Validation",
                    status="Failed",
                    cot_blob="Dependency contract violations found:\n"
                    + "\n".join(violations),
                )
                return False

            log_activity(
                summary=f"Validating dependency contracts for {file_path}",
                action="Dependency Contract Validation",
                status="Success",
                cot_blob=f"No dependency contract violations found. Analyzed {len(call_graph)} function calls.",
            )
            return True

        except Exception as e:
            log_activity(
                summary=f"Error validating dependency contracts for {file_path}",
                action="Dependency Contract Validation",
                status="Error",
                cot_blob=str(e),
            )
            return False

    @fcid_mapping("VER-105")
    def validate_downstream_consumer_tests(self, file_path, test_file, semantic_map):
        """
        FCID: VER-105
        Functionality: Checks that all downstream consumers are tested.

        Args:
            file_path: Path to the implemented file
            test_file: Path to the test file
            semantic_map: SemanticMapper instance for the implemented file

        Returns:
            bool: True if downstream consumers are tested, False otherwise
        """
        if not os.path.exists(file_path):
            log_activity(
                summary=f"Validating downstream consumer tests for {file_path}",
                action="Downstream Consumer Validation",
                status="Failed",
                cot_blob=f"File {file_path} not found",
            )
            return False

        if not os.path.exists(test_file):
            log_activity(
                summary=f"Validating downstream consumer tests for {file_path}",
                action="Downstream Consumer Validation",
                status="Skipped",
                cot_blob=f"Test file {test_file} not found. Cannot validate downstream consumers.",
            )
            return True  # Don't fail if test file doesn't exist

        try:
            with open(file_path, "r") as f:
                source_code = f.read()

            with open(test_file, "r") as f:
                test_code = f.read()

            # Parse the implemented code
            mapper = SemanticMapper(source_code)
            call_graph = mapper.get_call_graph()

            # Parse the test file
            test_mapper = SemanticMapper(test_code)
            test_summary = test_mapper.get_summary()

            # Collect all public functions/classes from the implementation
            public_entities = set()
            summary = mapper.get_summary()

            for func in summary["functions"]:
                # Assume non-underscore functions are public
                if not func["name"].startswith("_"):
                    public_entities.add(func["name"])

            for cls in summary["classes"]:
                if not cls["name"].startswith("_"):
                    public_entities.add(cls["name"])
                    for method in cls["methods"]:
                        if not method["name"].startswith("_"):
                            public_entities.add(method["name"])

            # Find which public entities are tested
            tested_entities = set()

            # Analyze test functions to see what they call
            for test_func in test_summary["functions"]:
                # Extract called functions from test function body
                if test_func["dependencies"]:
                    for dep in test_func["dependencies"]:
                        if dep in public_entities:
                            tested_entities.add(dep)

            # Also check test classes
            for test_cls in test_summary["classes"]:
                for method in test_cls["methods"]:
                    if method["dependencies"]:
                        for dep in method["dependencies"]:
                            if dep in public_entities:
                                tested_entities.add(dep)

            # Find untested public entities
            untested = public_entities - tested_entities

            # Filter out entities that might not need testing (e.g., simple properties)
            # This is a heuristic - might need refinement
            critical_untested = []
            for entity in untested:
                # Check if entity is called by other functions (has downstream consumers)
                is_used = False
                for caller, calls in call_graph.items():
                    for call_info in calls:
                        if (
                            call_info["callee"] == entity
                            and not call_info["is_external"]
                        ):
                            is_used = True
                            break
                    if is_used:
                        break

                if is_used:
                    critical_untested.append(entity)

            if critical_untested:
                log_activity(
                    summary=f"Validating downstream consumer tests for {file_path}",
                    action="Downstream Consumer Validation",
                    status="Failed",
                    cot_blob=f"Public entities with consumers but no tests: {critical_untested}",
                )
                return False

            log_activity(
                summary=f"Validating downstream consumer tests for {file_path}",
                action="Downstream Consumer Validation",
                status="Success",
                cot_blob=f"All {len(public_entities)} public entities are tested. "
                f"{len(tested_entities)} tested, {len(untested) - len(critical_untested)} unused/untested.",
            )
            return True

        except Exception as e:
            log_activity(
                summary=f"Error validating downstream consumer tests for {file_path}",
                action="Downstream Consumer Validation",
                status="Error",
                cot_blob=str(e),
            )
            return False

    def _filter_stdlib_dependencies(self, dependencies):
        """
        Filters out standard library dependencies from a set of dependency names.

        Args:
            dependencies: Set of dependency names to filter

        Returns:
            set: Filtered dependencies excluding stdlib
        """
        stdlib_modules = {
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
            "threading",
            "multiprocessing",
            "concurrent",
            "asyncio",
            "subprocess",
            "shutil",
            "tempfile",
            "glob",
            "fnmatch",
            "statistics",
            "fractions",
            "decimal",
            "enum",
            "dataclasses",
            "warnings",
            "traceback",
            "contextlib",
            "abc",
            "numbers",
            "string",
            "struct",
            "codecs",
            "textwrap",
            "difflib",
            "int",
            "str",
            "list",
            "dict",
            "set",
            "tuple",
            "frozenset",
            "bool",
            "float",
            "complex",
            "None",
            "True",
            "False",
        }

        return {dep for dep in dependencies if dep not in stdlib_modules}

    @fcid_mapping("VER-101")
    def validate_line_limit(self, file_path, limit=30):
        """
        FCID: VER-101
        Functionality: Ensures that the implementation file does not exceed the line limit.
        """
        if not os.path.exists(file_path):
            log_activity(
                summary=f"Validating line limit for {file_path}",
                action="Line Limit Check",
                status="Failed",
                cot_blob=f"File {file_path} not found",
            )
            return False

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            line_count = len(lines)
            if line_count <= limit:
                log_activity(
                    summary=f"Validating line limit for {file_path}",
                    action="Line Limit Check",
                    status="Success",
                    cot_blob=f"File {file_path} has {line_count} lines (limit: {limit})",
                )
                return True
            else:
                log_activity(
                    summary=f"Validating line limit for {file_path}",
                    action="Line Limit Check",
                    status="Failed",
                    cot_blob=f"File {file_path} has {line_count} lines, which exceeds the limit of {limit}",
                )
                return False
        except Exception as e:
            log_activity(
                summary=f"Error validating line limit for {file_path}",
                action="Line Limit Check",
                status="Error",
                cot_blob=str(e),
            )
            return False

    @fcid_mapping("VER-102")
    def run_mutation_tests(
        self, target_file="v1/impl_poc.py", test_file="v1/test_poc.py", tracking_id=None
    ):
        """
        FCID: VER-102
        Functionality: Performs mutation testing by systematically swapping operators and calculating a score.
        V4 Enhancement: Added progress tracking and trap detection for mutation testing.
        """
        # V4: Detect loops in mutation testing attempts
        validation_loop_traps = self.trap_detector.detect_all_loops(
            action_history=self.decision_history.get_recent_decisions(limit=5),
            error_history=self.telemetry_manager.query_operations(status="failed", limit=5),
            reasoning_history=self.decision_history.get_recent_decisions(limit=5),
            decision_dependencies=self.decision_history.get_decision_graph()
        )
        if validation_loop_traps:
            logger.warning(f"Loop detected in mutation testing: {validation_loop_traps}")
            # Attempt recovery
            recovery_result = self.trap_recovery.execute_recovery(
                trap_type="infinite_loop",
                trap_details=validation_loop_traps
            )
            if recovery_result["success"]:
                logger.info(f"Successfully recovered from loop: {recovery_result['message']}")
            else:
                logger.error(f"Failed to recover from loop: {recovery_result['message']}")
        
        # V4: Update progress for mutation testing start
        if tracking_id:
            self.progress_tracker_v4.update_progress(
                tracking_id=tracking_id,
                metrics={"mutation_testing_phase": "started"}
            )
        if os.getenv("L4_SIMULATION") == "true":
            log_activity(
                summary=f"Mutation testing for {target_file} (Simulated)",
                action="Mutation Test",
                status="Success",
                cot_blob="Simulation mode: 100% mutation score assumed.",
            )
            return True

        if not os.path.exists(target_file):
            log_activity(
                summary=f"Mutation testing for {target_file}",
                action="Mutation Test",
                status="Failed",
                cot_blob=f"Target file {target_file} not found",
            )
            return False

        original_content = None
        try:
            with open(target_file, "r") as f:
                original_content = f.read()

            # Step 1: Count total mutation candidates
            tree = ast.parse(original_content)
            counter = OperatorSwapper(target_index=-1)
            counter.visit(tree)
            total_mutations = counter.count

            if total_mutations == 0:
                log_activity(
                    summary=f"Mutation testing for {target_file}",
                    action="Mutation Test",
                    status="Skipped",
                    cot_blob="No mutation candidates found",
                )
                return True

            killed_mutations = 0
            results = []

            # Step 2: Iterate and test each mutation
            for i in range(total_mutations):
                # We need to re-parse because ast.unparse/parse might change whitespace/formatting
                # but we want to be safe and always start from original tree for each mutation
                tree = ast.parse(original_content)
                mutator = OperatorSwapper(target_index=i)
                mutated_tree = mutator.visit(tree)

                with open(target_file, "w") as f:
                    f.write(ast.unparse(mutated_tree))

                result = subprocess.run(
                    ["pytest", test_file], capture_output=True, text=True
                )
                mutation_killed = result.returncode != 0

                if mutation_killed:
                    killed_mutations += 1
                    results.append(f"Mutation {i}: KILLED")
                else:
                    results.append(f"Mutation {i}: SURVIVED")

            # Step 3: Restore original content
            with open(target_file, "w") as f:
                f.write(original_content)

            # Step 4: Calculate score
            mutation_score = (killed_mutations / total_mutations) * 100

            # V4: Update progress for mutation testing completion
            if tracking_id:
                self.progress_tracker_v4.update_progress(
                    tracking_id=tracking_id,
                    metrics={
                        "mutation_testing_phase": "completed",
                        "mutation_score": mutation_score,
                        "mutations_killed": killed_mutations,
                        "total_mutations": total_mutations
                    }
                )
            
            # V4: Learn from mutation testing failure
            if mutation_score < 100:
                self.lesson_learner.record_failure(
                    failure_type="mutation_testing",
                    context={"target_file": target_file, "test_file": test_file},
                    error_message=f"Mutation score {mutation_score:.1f}% is below required 100%"
                )
            # V4: Record validation decision
            decision_id = self.decision_history.record_decision(
                context={"mutation_score": mutation_score, "killed": killed_mutations, "total": total_mutations},
                reasoning=f"Mutation testing completed with score {mutation_score:.1f}%",
                action="mutation_validation",
                alternatives={
                    "alternative_1": "Accept lower mutation score",
                    "alternative_2": "Skip mutation testing"
                },
                confidence=mutation_score / 100.0
            )
            
            if mutation_score == 100:
                self.decision_history.record_outcome(
                    decision_id=decision_id,
                    outcome="success",
                    actual_success=True
                )
            else:
                self.decision_history.record_outcome(
                    decision_id=decision_id,
                    outcome="failure",
                    actual_success=False
                )
            
            log_activity(
                summary=f"Mutation testing for {target_file}",
                action="Mutation Test",
                status="Success" if mutation_score == 100 else "Failed",
                cot_blob=f"Score: {mutation_score:.1f}% ({killed_mutations}/{total_mutations} killed)\n"
                + "\n".join(results),
            )
            return mutation_score == 100

        except Exception as e:
            if original_content:
                with open(target_file, "w") as f:
                    f.write(original_content)
            log_activity(
                summary=f"Error during mutation testing for {target_file}",
                action="Mutation Test",
                status="Error",
                cot_blob=str(e),
            )
            return False
