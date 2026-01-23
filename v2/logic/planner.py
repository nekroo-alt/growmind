import os
import glob
import json
from typing import Dict, List, Optional
from v1.data.db_manager import log_task, log_activity, fcid_mapping, task_exists
from v1.logic.context_engine import ContextEngine
from v1.logic.task_impact_analyzer import TaskImpactAnalyzer
from v1.logic.complexity_estimator import ComplexityEstimator
from v1.data.semantic_mapper import SemanticMapper
from v1.llm_base.provider import LLMProvider
from v2.data.telemetry_manager import get_telemetry_manager
from v2.core.telemetry import telemetry
from v2.core.logging_config import get_module_logger, log_error_with_context

logger = get_module_logger(__name__)


class Planner:
    def __init__(self, workspace_root="."):
        logger.info("Initializing Planner")
        self.workspace_root = workspace_root
        self.context_engine = ContextEngine(workspace_root)
        self.task_impact_analyzer = TaskImpactAnalyzer(workspace_root)
        self.llm = LLMProvider()
        self.semantic_mappers = {}  # Cache of semantic mappers
        self.telemetry_manager = get_telemetry_manager()  # V3 telemetry
        logger.info("Planner initialized successfully")

    @fcid_mapping("PLAN-0100")
    def breakdown_requirements(
        self, product_content, technical_content, task_to_break=None
    ):
        """
        Analyzes requirements and breaks them down into atomic tasks (<30 lines).
        If task_to_break is provided, it breaks down that specific task.
        
        Enhanced with AST-based impact analysis to:
        - Use existing code structure to suggest natural task boundaries
        - Break down tasks at logical code units
        - Estimate token impact of proposed tasks
        - Validate that subtasks don't overlap in code modifications
        - Generate context-aware acceptance criteria
        
        V3 Enhancement: Integrated telemetry tracking for planning operations.
        """
        # V3: Track planning operation
        task_title = task_to_break["title"] if task_to_break else "Initial requirement analysis and task breakdown"
        
        logger.info(f"Starting task breakdown: {task_title}")
        
        with self.telemetry_manager.track_operation(
            operation_type="planning",
            title=f"Task breakdown: {task_title}"
        ) as op:
            # Step 1: Analyze task impact using AST analysis
            acceptance_criteria = task_to_break["acceptance_criteria"] if task_to_break else ""
            logger.debug(f"Analyzing task impact for: {task_title}")
            
            impact_analysis = self.task_impact_analyzer.analyze_task_impact(
                task_title, acceptance_criteria
            )
            
            # Step 2: Build semantic mappers for affected files
            logger.debug(f"Building semantic mappers for {len(impact_analysis['affected_files'])} files")
            self._build_semantic_mappers(impact_analysis["affected_files"])
            
            # Step 3: Get relevant project files using impact-based selection
            relevant_files = self._get_relevant_files(impact_analysis)
            logger.debug(f"Selected {len(relevant_files)} relevant files")
            
            query = task_title
            pruned_context = self.context_engine.get_pruned_context(query, relevant_files)
            
            # Step 4: Prepare code structure information for LLM
            code_structure_info = self._prepare_code_structure_info(impact_analysis)
            
            # Step 5: Build enhanced prompt with AST insights
            system_prompt = self._build_enhanced_system_prompt(code_structure_info)
            user_prompt = self._build_enhanced_user_prompt(
                product_content, technical_content, task_to_break, 
                pruned_context, code_structure_info, impact_analysis
            )

            # Step 6: Call LLM with enhanced context
            result = self.llm.call(
                system_prompt, user_prompt, temperature=0.2, max_tokens=4096
            )
            response = result["content"]

            try:
                if "Error: All LLM providers failed" in response:
                    raise ValueError(response)

                # Parse JSON response
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()
                subtasks_data = json.loads(response)
                
                # Step 7: Validate subtasks for overlap and estimate impact
                validated_subtasks = self._validate_and_estimate_subtasks(
                    subtasks_data, impact_analysis
                )
                
                # Step 8: Enhance acceptance criteria with context-aware checks
                context_aware_subtasks = self._enhance_acceptance_criteria(
                    validated_subtasks, impact_analysis, code_structure_info
                )
                
                subtasks = [
                    (t["title"], t["acceptance_criteria"], t.get("module"))
                    for t in context_aware_subtasks
                ]
            except Exception as e:
                # Improved error handling: No more hardcoded platform tasks
                log_error_with_context(logger, e, task_title=task_title, operation="planning")
                log_activity(
                    summary="Task Breakdown Failed",
                    action="PLANNING",
                    status="Failed",
                    cot_blob=f"Error parsing LLM response or LLM failed: {str(e)}",
                )
                # V3: Record failure event
                op.record_event(
                    event_type="breakdown_failed",
                    severity="error",
                    message=f"Task breakdown failed: {str(e)}",
                    context={"target": task_title, "error": str(e)}
                )
                # Return 0 to signify planning failed
                return 0

            parent_id = task_to_break["id"] if task_to_break else None
            module = task_to_break["module"] if task_to_break else None

            new_tasks_added = 0
            for title, ac, mod in subtasks:
                if not task_exists(title):
                    log_task(
                        title=title,
                        status="pending",
                        acceptance_criteria=ac,
                        parent_id=parent_id,
                        module=mod or module,
                    )
                    new_tasks_added += 1
                    logger.debug(f"Added new task: {title}")

            # Calculate context size metrics
            context_size_chars = len(pruned_context)
            context_size_lines = pruned_context.count('\n')
            
            # Calculate average complexity score
            avg_complexity = sum(
                t.get("complexity_score", 0) for t in context_aware_subtasks
            ) / len(context_aware_subtasks) if context_aware_subtasks else 0
            
            # V3: Record planning metrics and events
            op.record_event(
                event_type="breakdown_completed",
                severity="info",
                message=f"Successfully broke down into {len(subtasks)} tasks, added {new_tasks_added} new tasks",
                context={
                    "target": task_title,
                    "total_subtasks": len(subtasks),
                    "new_tasks": new_tasks_added,
                    "affected_files": len(impact_analysis['affected_files']),
                    "target_classes": len(impact_analysis['target_classes']),
                    "target_functions": len(impact_analysis['target_functions']),
                    "context_size_chars": context_size_chars,
                    "context_size_lines": context_size_lines,
                    "avg_complexity": avg_complexity
                }
            )
            
            op.record_metric("subtasks_generated", len(subtasks))
            op.record_metric("new_tasks_added", new_tasks_added)
            op.record_metric("affected_files_count", len(impact_analysis['affected_files']))
            op.record_metric("context_size_chars", context_size_chars)
            
            log_activity(
                summary="Task Breakdown",
                action="PLANNING",
                status="Success",
                cot_blob=(
                    f"Broke down {'project' if not task_to_break else task_to_break['title']} into {len(subtasks)} tasks. "
                    f"Added {new_tasks_added} new tasks. "
                    f"AST analysis identified {len(impact_analysis['affected_files'])} relevant files with "
                    f"{len(impact_analysis['target_classes'])} classes and {len(impact_analysis['target_functions'])} functions. "
                    f"Context size: {context_size_chars} chars ({context_size_lines} lines). "
                    f"Average task complexity: {avg_complexity:.1f}. "
                    f"Token usage: {result['usage']['total_tokens']} (prompt: {result['usage']['prompt_tokens']}, completion: {result['usage']['completion_tokens']})."
                ),
                tokens_used=result["usage"]["total_tokens"],
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                estimated_cost=result["cost"],
            )
            
            logger.info(f"Task breakdown completed: {len(subtasks)} tasks, {new_tasks_added} new tasks added")
            telemetry.info(f"Task breakdown completed: {len(subtasks)} tasks, {new_tasks_added} new tasks added")
            return new_tasks_added
    
    def _build_semantic_mappers(self, affected_files: List[Dict]):
        """
        Build semantic mappers for files identified by impact analysis.
        
        Args:
            affected_files: List of files with impact scores from TaskImpactAnalyzer
        """
        logger.debug(f"Building semantic mappers for {min(len(affected_files), 15)} files")
        for file_info in affected_files[:15]:  # Limit to top 15 files
            file_path = os.path.join(self.workspace_root, file_info["file_path"])
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()
                
                mapper = SemanticMapper(source_code)
                # Also create complexity estimator for each mapper
                mapper.complexity_estimator = ComplexityEstimator(mapper)
                self.semantic_mappers[file_path] = mapper
                logger.debug(f"Created semantic mapper for {file_path}")
            except Exception as e:
                # Skip files that cannot be parsed
                logger.warning(f"Failed to create semantic mapper for {file_path}: {e}")
                continue
    
    def _get_relevant_files(self, impact_analysis: Dict) -> List[str]:
        """
        Get list of relevant files based on impact analysis.
        
        Args:
            impact_analysis: Impact analysis result from TaskImpactAnalyzer
        
        Returns:
            List of file paths sorted by relevance
        """
        # Extract file paths from impact analysis, sorted by impact score
        relevant_files = [
            f["file_path"] for f in impact_analysis["affected_files"]
            if f["confidence"] in ["high", "medium"]
        ]
        
        return relevant_files
    
    def _prepare_code_structure_info(self, impact_analysis: Dict) -> Dict:
        """
        Prepare code structure information for LLM context.
        
        Args:
            impact_analysis: Impact analysis result from TaskImpactAnalyzer
        
        Returns:
            Dictionary with code structure information
        """
        structure_info = {
            "target_modules": impact_analysis["target_modules"],
            "target_classes": [],
            "target_functions": [],
            "file_structure": {}
        }
        
        # Extract detailed information about affected classes and functions
        for file_info in impact_analysis["affected_files"][:10]:
            file_path = file_info["file_path"]
            full_path = os.path.join(self.workspace_root, file_path)
            
            if full_path not in self.semantic_mappers:
                continue
            
            mapper = self.semantic_mappers[full_path]
            summary = mapper.get_summary()
            
            # Extract class information
            for cls in summary.get("classes", []):
                if cls["name"] in impact_analysis["target_classes"]:
                    structure_info["target_classes"].append({
                        "name": cls["name"],
                        "file": file_path,
                        "methods": [m["name"] for m in cls["methods"]],
                        "start_line": cls["start_line"],
                        "end_line": cls["end_line"]
                    })
            
            # Extract function information
            for func in summary.get("functions", []):
                if func["name"] in impact_analysis["target_functions"]:
                    structure_info["target_functions"].append({
                        "name": func["name"],
                        "file": file_path,
                        "start_line": func["start_line"],
                        "end_line": func["end_line"]
                    })
            
            # Build file structure summary
            structure_info["file_structure"][file_path] = {
                "classes": [c["name"] for c in summary.get("classes", [])],
                "functions": [f["name"] for f in summary.get("functions", [])],
                "impact_score": file_info["impact_score"]
            }
        
        return structure_info
    
    def _build_enhanced_system_prompt(self, code_structure_info: Dict) -> str:
        """
        Build enhanced system prompt with AST-based insights.
        
        Args:
            code_structure_info: Code structure information from AST analysis
        
        Returns:
            Enhanced system prompt
        """
        prompt = (
            "You are a Senior Architect with deep knowledge of AST-based code analysis. "
            "Break down the given requirements into atomic tasks (<30 lines of code).\n\n"
            
            "**AST-Based Task Breakdown Guidelines:**\n"
            "1. Respect existing code structure - break tasks at natural boundaries (classes, methods, functions)\n"
            "2. Each task should modify a single logical code unit\n"
            "3. Avoid overlapping modifications across tasks\n"
            "4. Leverage existing code patterns and conventions\n"
            "5. Consider dependency chains when proposing tasks\n\n"
            
            "**Code Structure Available:**\n"
        )
        
        if code_structure_info["target_classes"]:
            prompt += f"- Target Classes: {', '.join([c['name'] for c in code_structure_info['target_classes']])}\n"
        
        if code_structure_info["target_functions"]:
            prompt += f"- Target Functions: {', '.join([f['name'] for f in code_structure_info['target_functions']])}\n"
        
        if code_structure_info["target_modules"]:
            prompt += f"- Target Modules: {', '.join(code_structure_info['target_modules'])}\n"
        
        prompt += (
            "\n**Output Format:**\n"
            "Return a JSON list of objects with keys:\n"
            "- 'title': Clear task title\n"
            "- 'acceptance_criteria': Specific, testable criteria\n"
            "- 'module': Target module/file (optional)\n"
            "- 'estimated_lines': Estimated lines of code (must be <30)\n"
            "- 'target_class': Class being modified (if applicable)\n"
            "- 'target_function': Function/method being modified (if applicable)\n"
        )
        
        return prompt
    
    def _build_enhanced_user_prompt(
        self, 
        product_content: str,
        technical_content: str,
        task_to_break: Optional[Dict],
        pruned_context: str,
        code_structure_info: Dict,
        impact_analysis: Dict
    ) -> str:
        """
        Build enhanced user prompt with AST context.
        
        Args:
            product_content: Product requirements content
            technical_content: Technical design content
            task_to_break: Task to break down (optional)
            pruned_context: Pruned context from ContextEngine
            code_structure_info: Code structure information
            impact_analysis: Impact analysis result
        
        Returns:
            Enhanced user prompt
        """
        prompt = f"Product Requirements:\n{product_content}\n\n"
        prompt += f"Technical Design:\n{technical_content}\n\n"
        
        if task_to_break:
            prompt += f"**Task to Break Down:**\n"
            prompt += f"Title: {task_to_break['title']}\n"
            prompt += f"Acceptance Criteria: {task_to_break['acceptance_criteria']}\n\n"
        
        # Add code structure insights
        prompt += "**AST-Based Code Analysis:**\n"
        prompt += f"High-impact files identified: {len(impact_analysis['affected_files'])}\n"
        prompt += f"Classes likely affected: {len(code_structure_info['target_classes'])}\n"
        prompt += f"Functions likely affected: {len(code_structure_info['target_functions'])}\n\n"
        
        # Add file structure details
        prompt += "**Affected File Structure:**\n"
        for file_path, info in code_structure_info["file_structure"].items():
            prompt += f"\n{file_path} (impact: {info['impact_score']:.2f}):\n"
            if info["classes"]:
                prompt += f"  Classes: {', '.join(info['classes'])}\n"
            if info["functions"]:
                prompt += f"  Functions: {', '.join(info['functions'])}\n"
        
        prompt += "\n"
        
        if pruned_context.strip():
            prompt += f"**Relevant Code Context:**\n{pruned_context}\n\n"
        
        prompt += "**Instructions:**\n"
        prompt += "1. Break down the requirements into atomic tasks based on the code structure provided\n"
        prompt += "2. Each task should target a specific class or function identified above\n"
        prompt += "3. Ensure tasks don't overlap in what they modify\n"
        prompt += "4. Estimate lines of code for each task (must be <30)\n"
        prompt += "5. Provide specific acceptance criteria that can be tested\n\n"
        
        return prompt
    
    def _validate_and_estimate_subtasks(
        self, 
        subtasks_data: List[Dict],
        impact_analysis: Dict
    ) -> List[Dict]:
        """
        Validate subtasks for overlap and estimate token impact.
        
        Enhanced with ComplexityEstimator to validate 30-line limit using AST metrics.
        
        Args:
            subtasks_data: List of subtasks from LLM
            impact_analysis: Impact analysis result
        
        Returns:
            Validated list of subtasks with impact estimates
        """
        validated_tasks = []
        task_targets = set()  # Track (file, class, function) to detect overlaps
        
        for task in subtasks_data:
            # Check for overlap
            task_key = self._create_task_key(task, impact_analysis)
            
            if task_key in task_targets:
                # Overlapping task - mark for review
                task["validation_warning"] = "Potential overlap with another task"
            
            task_targets.add(task_key)
            
            # Use ComplexityEstimator to validate 30-line limit
            validation_result = self._validate_task_complexity(task, impact_analysis)
            
            # Apply validation results
            task["estimated_lines"] = validation_result["estimated_lines"]
            task["complexity_score"] = validation_result["complexity_score"]
            
            if validation_result["needs_breakdown"]:
                task["validation_warning"] = validation_result["reasoning"]
                if task["estimated_lines"] > 30:
                    task["validation_warning"] += " | Requires breakdown"
            
            validated_tasks.append(task)
        
        return validated_tasks
    
    def _validate_task_complexity(
        self, 
        task: Dict,
        impact_analysis: Dict
    ) -> Dict:
        """
        Validate task complexity using ComplexityEstimator.
        
        Args:
            task: Task dictionary from LLM
            impact_analysis: Impact analysis result
        
        Returns:
            dict: Validation result with:
                - estimated_lines: Validated line estimate
                - complexity_score: AST-based complexity score
                - needs_breakdown: Boolean if task needs breaking down
                - reasoning: Explanation of validation decision
        """
        # Extract target entities for complexity analysis
        target_entities = []
        
        target_class = task.get("target_class")
        target_function = task.get("target_function")
        module = task.get("module", "")
        
        if target_class:
            target_entities.append(target_class)
        if target_function:
            target_entities.append(target_function)
        
        # If no explicit targets, try to infer from title and impact analysis
        if not target_entities:
            title = task.get("title", "").lower()
            
            # Check against target classes/functions from impact analysis
            for cls in impact_analysis["target_classes"]:
                if cls.lower() in title:
                    target_entities.append(cls)
                    break
            
            for func in impact_analysis["target_functions"]:
                if func.lower() in title:
                    target_entities.append(func)
                    break
        
        # Use LLM's estimate as baseline
        llm_estimate = task.get("estimated_lines", 25)
        
        # If we have semantic mappers and target entities, validate with AST
        if target_entities and self.semantic_mappers:
            # Find the appropriate semantic mapper
            semantic_mapper = None
            for file_info in impact_analysis["affected_files"]:
                file_path = os.path.join(self.workspace_root, file_info["file_path"])
                if file_path in self.semantic_mappers:
                    semantic_mapper = self.semantic_mappers[file_path]
                    break
            
            if semantic_mapper and hasattr(semantic_mapper, 'complexity_estimator'):
                estimator = semantic_mapper.complexity_estimator
                
                # Check if task will exceed 30-line limit
                limit_check = estimator.will_exceed_line_limit(target_entities, threshold=30)
                
                return {
                    "estimated_lines": min(int(limit_check["estimated_lines"]), 30),
                    "complexity_score": limit_check["total_complexity"],
                    "needs_breakdown": limit_check["will_exceed"],
                    "reasoning": limit_check["reasoning"]
                }
        
        # Fallback: Use LLM estimate with basic validation
        if llm_estimate > 30:
            return {
                "estimated_lines": 30,
                "complexity_score": 15,  # Conservative estimate
                "needs_breakdown": True,
                "reasoning": f"LLM estimate ({llm_estimate} lines) exceeds 30-line limit"
            }
        
        return {
            "estimated_lines": llm_estimate,
            "complexity_score": 5,  # Assume simple if no AST data
            "needs_breakdown": False,
            "reasoning": "Using LLM estimate (within acceptable range)"
        }
    
    def _create_task_key(self, task: Dict, impact_analysis: Dict) -> tuple:
        """
        Create a unique key for a task to detect overlaps.
        
        Args:
            task: Task dictionary
            impact_analysis: Impact analysis result
        
        Returns:
            Tuple representing the task's target
        """
        # Use module/target_class/target_function to create unique key
        module = task.get("module", "")
        target_class = task.get("target_class", "")
        target_function = task.get("target_function", "")
        
        # If not specified, try to infer from title
        if not (target_class or target_function):
            title = task.get("title", "").lower()
            
            # Check against target classes/functions from impact analysis
            for cls in impact_analysis["target_classes"]:
                if cls.lower() in title:
                    target_class = cls
                    break
            
            if not target_class:
                for func in impact_analysis["target_functions"]:
                    if func.lower() in title:
                        target_function = func
                        break
        
        return (module, target_class, target_function)
        
    def _enhance_acceptance_criteria(
        self,
        subtasks: List[Dict],
        impact_analysis: Dict,
        code_structure_info: Dict
    ) -> List[Dict]:
        """
        Enhance acceptance criteria with context-aware checks.
        
        Acceptance criteria should include:
        - Checks for proper context integration
        - Verification of dependency contracts
        - Criteria for not breaking downstream consumers
        - Testing both direct functionality and side effects
        
        Args:
            subtasks: Validated list of subtasks
            impact_analysis: Impact analysis result
            code_structure_info: Code structure information
        
        Returns:
            Enhanced subtasks with context-aware acceptance criteria
        """
        enhanced_tasks = []
        
        for task in subtasks:
            original_criteria = task.get("acceptance_criteria", "")
            
            # Build context-aware additions
            context_additions = []
            
            # 1. Context integration checks
            context_additions.extend(self._generate_context_integration_checks(
                task, impact_analysis, code_structure_info
            ))
            
            # 2. Dependency contract verification
            context_additions.extend(self._generate_dependency_contract_checks(
                task, impact_analysis
            ))
            
            # 3. Downstream consumer protection
            context_additions.extend(self._generate_downstream_consumer_checks(
                task, impact_analysis
            ))
            
            # 4. Side effect testing
            context_additions.extend(self._generate_side_effect_checks(
                task, impact_analysis
            ))
            
            # 5. Integration test requirements
            context_additions.extend(self._generate_integration_test_requirements(
                task, impact_analysis
            ))
            
            # 6. Mutation testing requirements
            context_additions.extend(self._generate_mutation_test_requirements(
                task
            ))
            
            # 7. Public API breaking change checks
            context_additions.extend(self._generate_api_change_checks(
                task, impact_analysis
            ))
            
            # Combine original criteria with context-aware additions
            if context_additions:
                enhanced_criteria = original_criteria
                if not enhanced_criteria.endswith(('\n', '.', '!', '?')):
                    enhanced_criteria += ".\n\n"
                
                enhanced_criteria += "**Context-Aware Requirements:**\n"
                enhanced_criteria += "\n".join(f"- {check}" for check in context_additions)
                
                task["acceptance_criteria"] = enhanced_criteria
            
            enhanced_tasks.append(task)
        
        return enhanced_tasks
    
    def _generate_context_integration_checks(
        self,
        task: Dict,
        impact_analysis: Dict,
        code_structure_info: Dict
    ) -> List[str]:
        """
        Generate checks for proper context integration.
        """
        checks = []
        
        target_class = task.get("target_class")
        target_function = task.get("target_function")
        
        if target_class:
            checks.append(
                f"Integration with existing {target_class} class context is maintained"
            )
            # Check if class has specific methods that need context awareness
            for cls_info in code_structure_info["target_classes"]:
                if cls_info["name"] == target_class:
                    if cls_info.get("methods"):
                        checks.append(
                            f"Context correctly propagated to methods: {', '.join(cls_info['methods'])}"
                        )
                    break
        
        if target_function:
            checks.append(
                f"Function {target_function} properly integrates with its surrounding context"
            )
        
        return checks
    
    def _generate_dependency_contract_checks(
        self,
        task: Dict,
        impact_analysis: Dict
    ) -> List[str]:
        """
        Generate checks for maintaining dependency contracts.
        """
        checks = []
        
        # Check for upstream dependencies
        if impact_analysis.get("upstream_dependencies"):
            upstream = impact_analysis["upstream_dependencies"][:3]  # Limit to top 3
            if upstream:
                checks.append(
                    f"Maintains contract with upstream dependencies: {', '.join(upstream)}"
                )
        
        # Check for type hints consistency
        target_class = task.get("target_class")
        target_function = task.get("target_function")
        
        for file_info in impact_analysis["affected_files"]:
            file_path = file_info["file_path"]
            full_path = os.path.join(self.workspace_root, file_path)
            
            if full_path not in self.semantic_mappers:
                continue
            
            mapper = self.semantic_mappers[full_path]
            summary = mapper.get_summary()
            
            # Check function type hints
            for func in summary.get("functions", []):
                if func["name"] == target_function:
                    if func.get("return_type"):
                        checks.append(
                            f"Return type {func['return_type']} contract is maintained"
                        )
                    if func.get("parameters"):
                        param_types = [p for p in func["parameters"] if ":" in str(p)]
                        if param_types:
                            checks.append(
                                f"Type contracts for parameters are respected"
                            )
                    break
            
            # Check class type hints
            for cls in summary.get("classes", []):
                if cls["name"] == target_class:
                    if cls.get("methods"):
                        checks.append(
                            f"Method signatures and type contracts are preserved"
                        )
                    break
        
        return checks
    
    def _generate_downstream_consumer_checks(
        self,
        task: Dict,
        impact_analysis: Dict
    ) -> List[str]:
        """
        Generate checks for not breaking downstream consumers.
        """
        checks = []
        
        # Check for downstream consumers
        if impact_analysis.get("downstream_consumers"):
            consumers = impact_analysis["downstream_consumers"][:3]  # Limit to top 3
            if consumers:
                checks.append(
                    f"Changes do not break downstream consumers: {', '.join(consumers)}"
                )
        
        # Check for public API modifications
        target_class = task.get("target_class")
        if target_class:
            checks.append(
                f"Public API of {target_class} remains backward compatible"
            )
        
        return checks
    
    def _generate_side_effect_checks(
        self,
        task: Dict,
        impact_analysis: Dict
    ) -> List[str]:
        """
        Generate checks for testing side effects.
        """
        checks = []
        
        target_class = task.get("target_class")
        target_function = task.get("target_function")
        
        # Check for mutable state
        for file_info in impact_analysis["affected_files"]:
            file_path = file_info["file_path"]
            full_path = os.path.join(self.workspace_root, file_path)
            
            if full_path not in self.semantic_mappers:
                continue
            
            mapper = self.semantic_mappers[full_path]
            
            # Check if function has side effects
            if target_function and hasattr(mapper, "call_graph"):
                call_graph = mapper.call_graph
                # Check for calls that might have side effects
                side_effect_calls = ["print", "open", "write", "append", "extend"]
                for caller, callees in call_graph.items():
                    if target_function in caller:
                        for callee in callees:
                            if any(se in callee for se in side_effect_calls):
                                checks.append(
                                    f"Side effects from {callee} are properly tested"
                                )
                                break
        
        if target_class:
            checks.append(
                f"Class-level state mutations are properly isolated and tested"
            )
        
        return checks
    
    def _generate_integration_test_requirements(
        self,
        task: Dict,
        impact_analysis: Dict
    ) -> List[str]:
        """
        Generate integration test requirements.
        """
        checks = []
        
        target_module = task.get("module")
        
        # Require integration tests if task affects multiple files
        affected_files = [f["file_path"] for f in impact_analysis["affected_files"][:5]]
        if len(affected_files) > 1:
            checks.append(
                f"Integration tests verify behavior across affected files"
            )
        
        # Require integration tests for class modifications
        target_class = task.get("target_class")
        if target_class:
            checks.append(
                f"Integration tests verify {target_class} interacts correctly with dependencies"
            )
        
        return checks
    
    def _generate_mutation_test_requirements(
        self,
        task: Dict
    ) -> List[str]:
        """
        Generate mutation testing requirements.
        """
        checks = []
        
        # Require mutation testing for critical acceptance criteria
        checks.append(
            "Tests include mutation testing to verify test quality"
        )
        checks.append(
            "Mutations in critical code paths cause test failures"
        )
        
        return checks
    
    def _generate_api_change_checks(
        self,
        task: Dict,
        impact_analysis: Dict
    ) -> List[str]:
        """
        Generate checks for public API breaking changes.
        """
        checks = []
        
        target_class = task.get("target_class")
        target_function = task.get("target_function")
        
        # Check for public API modifications
        if target_class or target_function:
            checks.append(
                "No breaking changes to public interfaces"
            )
            checks.append(
                "Backward compatibility is maintained for existing consumers"
            )
        
        # Check if task involves modifying existing methods
        for file_info in impact_analysis["affected_files"]:
            file_path = file_info["file_path"]
            full_path = os.path.join(self.workspace_root, file_path)
            
            if full_path not in self.semantic_mappers:
                continue
            
            mapper = self.semantic_mappers[full_path]
            summary = mapper.get_summary()
            
            # Check if modifying existing methods
            if target_class:
                for cls in summary.get("classes", []):
                    if cls["name"] == target_class:
                        # If class has existing methods, check for modifications
                        if cls.get("methods"):
                            checks.append(
                                f"Existing method signatures in {target_class} are preserved"
                            )
                        break
        
        return checks
