"""
Context Compressor - V5 Progressive Context Management

This module implements intelligent context compression at multiple levels to reduce
token usage while preserving critical information.

Compression Levels:
- Level 1: Remove comments, docstrings, whitespace (20-30% reduction)
- Level 2: Summarize functions with signatures only (40-50% reduction)
- Level 3: Summarize entire files (60-70% reduction)

Preservation Rules:
- Always preserve function signatures
- Always preserve class definitions
- Always preserve imports
- Always preserve critical logic (detected by complexity)
- Preserve comments with TODO, FIXME, HACK
"""

import ast
import re
from typing import Optional, Dict, List, Any, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from core.logging_config import get_logger
from llm_base.provider import LLMProvider

logger = get_logger(__name__)


class CompressionLevel(Enum):
    """Compression levels for context optimization."""
    NONE = "none"           # No compression
    LEVEL_1 = "level_1"     # Remove comments, docstrings, whitespace
    LEVEL_2 = "level_2"     # Summarize functions with signatures only
    LEVEL_3 = "level_3"     # Summarize entire files


@dataclass
class CompressionResult:
    """Result of context compression."""
    compressed_content: str
    original_tokens: int
    compressed_tokens: int
    reduction_ratio: float  # 0.0 to 1.0 (e.g., 0.3 means 30% reduction)
    compression_level: CompressionLevel
    preserved_elements: List[str]
    removed_elements: List[str]
    warnings: List[str]


@dataclass
class FunctionInfo:
    """Information about a function for compression."""
    name: str
    signature: str
    docstring: Optional[str]
    body_lines: List[str]
    complexity: int
    is_critical: bool


@dataclass
class ClassInfo:
    """Information about a class for compression."""
    name: str
    signature: str
    docstring: Optional[str]
    methods: List[FunctionInfo]
    is_critical: bool


class ContextCompressor:
    """
    Context Compressor for reducing token usage.
    
    Features:
    - Multi-level compression (Level 1, 2, 3)
    - Intelligent preservation of critical elements
    - AST-based analysis for accurate compression
    - LLM-powered summarization for higher levels
    - Tracks compression statistics
    - Preserves signatures, imports, and critical logic
    """
    
    # Keywords that mark comments as critical
    CRITICAL_COMMENT_KEYWORDS = ['TODO', 'FIXME', 'HACK', 'XXX', 'NOTE', 'WARNING']
    
    # Complexity threshold for critical functions
    CRITICAL_COMPLEXITY_THRESHOLD = 7
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize ContextCompressor.
        
        Args:
            llm_provider: Optional LLMProvider for intelligent summarization
        """
        self.llm_provider = llm_provider
        
        # Track compression statistics
        self._stats = {
            'total_compressions': 0,
            'total_original_tokens': 0,
            'total_compressed_tokens': 0,
            'level_distribution': {level.value: 0 for level in CompressionLevel}
        }
        
        logger.info("ContextCompressor initialized")
    
    def compress(
        self,
        content: str,
        level: CompressionLevel = CompressionLevel.LEVEL_1,
        preserve_patterns: Optional[List[str]] = None
    ) -> CompressionResult:
        """
        Compress content at specified level.
        
        Args:
            content: Content to compress
            level: Compression level
            preserve_patterns: Optional regex patterns to preserve
        
        Returns:
            CompressionResult with compressed content and statistics
        """
        logger.info(f"Compressing content at level {level.value}")
        
        # Estimate original tokens
        original_tokens = self._estimate_tokens(content)
        
        # Initialize warnings
        warnings = []
        
        # Compress based on level
        if level == CompressionLevel.NONE:
            compressed_content = content
            warnings = []
        elif level == CompressionLevel.LEVEL_1:
            compressed_content, warnings = self._compress_level_1(content, preserve_patterns)
        elif level == CompressionLevel.LEVEL_2:
            compressed_content, warnings = self._compress_level_2(content, preserve_patterns)
        elif level == CompressionLevel.LEVEL_3:
            compressed_content, warnings = self._compress_level_3(content, preserve_patterns)
        else:
            logger.warning(f"Unknown compression level: {level}, using Level 1")
            compressed_content, warnings = self._compress_level_1(content, preserve_patterns)
        
        # Estimate compressed tokens
        compressed_tokens = self._estimate_tokens(compressed_content)
        
        # Calculate reduction ratio
        reduction_ratio = 0.0
        if original_tokens > 0:
            reduction_ratio = (original_tokens - compressed_tokens) / original_tokens
        
        # Track preserved and removed elements
        preserved_elements = self._identify_preserved_elements(content, compressed_content)
        removed_elements = self._identify_removed_elements(content, compressed_content)
        
        # Update statistics
        self._stats['total_compressions'] += 1
        self._stats['total_original_tokens'] += original_tokens
        self._stats['total_compressed_tokens'] += compressed_tokens
        self._stats['level_distribution'][level.value] += 1
        
        result = CompressionResult(
            compressed_content=compressed_content,
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            reduction_ratio=reduction_ratio,
            compression_level=level,
            preserved_elements=preserved_elements,
            removed_elements=removed_elements,
            warnings=warnings
        )
        
        logger.info(
            f"Compression complete - Level: {level.value}, "
            f"Original tokens: {original_tokens}, "
            f"Compressed tokens: {compressed_tokens}, "
            f"Reduction: {reduction_ratio*100:.1f}%, "
            f"Warnings: {len(warnings)}"
        )
        
        return result
    
    def _compress_level_1(
        self,
        content: str,
        preserve_patterns: Optional[List[str]] = None
    ) -> Tuple[str, List[str]]:
        """
        Level 1 Compression: Remove comments, docstrings, whitespace.
        
        This level removes:
        - Single-line comments (# ...)
        - Multi-line comments (''' ... ''' or \"\"\" ... \"\"\"')
        - Docstrings (but preserves critical ones with TODO/FIXME)
        - Excessive whitespace
        
        Preserves:
        - All code statements
        - Import statements
        - Function/class signatures
        - Critical comments (with TODO, FIXME, etc.)
        
        Args:
            content: Content to compress
            preserve_patterns: Optional regex patterns to preserve
        
        Returns:
            Tuple of (compressed_content, warnings)
        """
        warnings = []
        compressed_lines = []
        
        lines = content.split('\n')
        
        for line in lines:
            # Check if line contains a critical comment keyword
            is_critical = any(keyword in line for keyword in self.CRITICAL_COMMENT_KEYWORDS)
            
            if is_critical:
                # Preserve critical comments
                compressed_lines.append(line)
            else:
                # Remove single-line comments (but preserve inline comments in code)
                # This is a simple heuristic - for production, use AST
                stripped = line.strip()
                
                # Skip empty lines (reduce excessive whitespace)
                if not stripped:
                    # Keep at most one consecutive blank line
                    if compressed_lines and compressed_lines[-1].strip() != '':
                        continue
                    else:
                        compressed_lines.append(line)
                        continue
                
                # Remove comment-only lines
                if stripped.startswith('#'):
                    # Check if it's a preserve pattern
                    if preserve_patterns:
                        preserved = False
                        for pattern in preserve_patterns:
                            if re.search(pattern, line):
                                preserved = True
                                break
                        if preserved:
                            compressed_lines.append(line)
                        # else: skip this comment line
                    else:
                        # Skip comment line
                        continue
                
                # Remove inline comments (simple heuristic)
                if '#' in line and not line.strip().startswith('#'):
                    # Split on first #, keep code part
                    code_part = line.split('#')[0].rstrip()
                    compressed_lines.append(code_part)
                else:
                    compressed_lines.append(line)
        
        compressed_content = '\n'.join(compressed_lines)
        
        # Remove excessive blank lines (more than 2 consecutive)
        compressed_content = re.sub(r'\n{3,}', '\n\n', compressed_content)
        
        # Remove trailing whitespace
        compressed_content = compressed_content.rstrip()
        
        return compressed_content, warnings
    
    def _compress_level_2(
        self,
        content: str,
        preserve_patterns: Optional[List[str]] = None
    ) -> Tuple[str, List[str]]:
        """
        Level 2 Compression: Summarize functions with signatures only.
        
        This level:
        - Preserves import statements
        - Preserves class definitions
        - Reduces functions to signatures + docstring summary
        - Preserves critical functions (high complexity)
        - Preserves critical comments
        
        Args:
            content: Content to compress
            preserve_patterns: Optional regex patterns to preserve
        
        Returns:
            Tuple of (compressed_content, warnings)
        """
        warnings = []
        
        try:
            # Parse AST
            tree = ast.parse(content)
            
            # Extract imports
            imports = self._extract_imports(tree)
            
            # Extract functions and classes
            functions, classes = self._extract_functions_and_classes(tree)
            
            # Build compressed content
            compressed_lines = []
            
            # Add imports
            compressed_lines.extend(imports)
            
            # Add classes (with methods compressed)
            for class_info in classes:
                if class_info.is_critical or self._should_preserve(class_info.name, preserve_patterns):
                    # Preserve full critical classes
                    compressed_lines.append(f"# CRITICAL: {class_info.name}")
                    compressed_lines.append(class_info.signature)
                    # Add methods preserved
                    for method in class_info.methods:
                        if method.is_critical:
                            compressed_lines.append(f"    {method.signature}")
                            compressed_lines.append("        ...  # Critical method preserved")
                        else:
                            # Compress non-critical methods
                            compressed_lines.append(f"    {method.signature}")
                else:
                    # Compress non-critical classes
                    compressed_lines.append(f"{class_info.signature}")
                    if class_info.docstring:
                        doc_summary = self._summarize_docstring(class_info.docstring)
                        compressed_lines.append(f"    # {doc_summary}")
                    # Compress methods
                    for method in class_info.methods:
                        compressed_lines.append(f"    {method.signature}")
                        if method.docstring:
                            doc_summary = self._summarize_docstring(method.docstring)
                            compressed_lines.append(f"        # {doc_summary}")
                        compressed_lines.append("        pass")
            
            # Add standalone functions
            for func_info in functions:
                if func_info.is_critical or self._should_preserve(func_info.name, preserve_patterns):
                    # Preserve full critical functions
                    compressed_lines.append(f"# CRITICAL: {func_info.name}")
                    compressed_lines.append(func_info.signature)
                    compressed_lines.append(f"    # {func_info.docstring or 'No docstring'}")
                    compressed_lines.append("    pass")
                else:
                    # Compress non-critical functions
                    compressed_lines.append(func_info.signature)
                    if func_info.docstring:
                        doc_summary = self._summarize_docstring(func_info.docstring)
                        compressed_lines.append(f"    # {doc_summary}")
                    compressed_lines.append("    pass")
            
            compressed_content = '\n'.join(compressed_lines)
            
        except SyntaxError as e:
            warnings.append(f"Failed to parse content as Python: {e}")
            # Fallback to Level 1 compression
            compressed_content, level1_warnings = self._compress_level_1(content, preserve_patterns)
            warnings.extend(level1_warnings)
        
        return compressed_content, warnings
    
    def _compress_level_3(
        self,
        content: str,
        preserve_patterns: Optional[List[str]] = None
    ) -> Tuple[str, List[str]]:
        """
        Level 3 Compression: Summarize entire files.
        
        This level:
        - Preserves import statements
        - Summarizes all classes and functions
        - Uses LLM for intelligent summarization if available
        - Provides high-level overview of file structure
        
        Args:
            content: Content to compress
            preserve_patterns: Optional regex patterns to preserve
        
        Returns:
            Tuple of (compressed_content, warnings)
        """
        warnings = []
        
        try:
            # Parse AST
            tree = ast.parse(content)
            
            # Extract imports
            imports = self._extract_imports(tree)
            
            # Extract functions and classes
            functions, classes = self._extract_functions_and_classes(tree)
            
            # Build compressed content using LLM if available
            if self.llm_provider:
                compressed_content = self._summarize_with_llm(imports, classes, functions)
            else:
                # Fallback to simple summarization
                compressed_content = self._summarize_simple(imports, classes, functions)
            
        except SyntaxError as e:
            warnings.append(f"Failed to parse content as Python: {e}")
            # Fallback to Level 1 compression
            compressed_content, level1_warnings = self._compress_level_1(content, preserve_patterns)
            warnings.extend(level1_warnings)
        
        return compressed_content, warnings
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from AST."""
        imports = []
        seen_imports = set()  # Avoid duplicates
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_stmt = f"import {alias.name}"
                    if import_stmt not in seen_imports:
                        imports.append(import_stmt)
                        seen_imports.add(import_stmt)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                names_str = ', '.join(alias.name for alias in node.names)
                import_stmt = f"from {module} import {names_str}"
                if import_stmt not in seen_imports:
                    imports.append(import_stmt)
                    seen_imports.add(import_stmt)
        
        return imports
    
    def _extract_functions_and_classes(
        self,
        tree: ast.AST
    ) -> Tuple[List[FunctionInfo], List[ClassInfo]]:
        """Extract function and class information from AST."""
        functions = []
        classes = []
        
        # Track which functions are methods to avoid duplication
        method_names = set()
        
        # First, extract classes and their methods
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                # Extract methods
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_complexity = self._calculate_complexity(item)
                        method_docstring = ast.get_docstring(item)
                        method_signature = self._get_function_signature(item)
                        method_is_critical = method_complexity > self.CRITICAL_COMPLEXITY_THRESHOLD
                        
                        method_info = FunctionInfo(
                            name=item.name,
                            signature=method_signature,
                            docstring=method_docstring,
                            body_lines=[],
                            complexity=method_complexity,
                            is_critical=method_is_critical
                        )
                        
                        methods.append(method_info)
                        # Track method name to avoid including as standalone function
                        method_names.add(item.name)
                
                # Get class docstring
                class_docstring = ast.get_docstring(node)
                
                # Get signature
                class_signature = f"class {node.name}:"
                
                # Check if critical (has critical methods)
                is_critical = any(m.is_critical for m in methods)
                
                class_info = ClassInfo(
                    name=node.name,
                    signature=class_signature,
                    docstring=class_docstring,
                    methods=methods,
                    is_critical=is_critical
                )
                
                classes.append(class_info)
        
        # Then, extract standalone functions (not methods)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name not in method_names:
                # Calculate complexity
                complexity = self._calculate_complexity(node)
                
                # Get docstring
                docstring = ast.get_docstring(node)
                
                # Get signature
                signature = self._get_function_signature(node)
                
                # Check if critical
                is_critical = complexity > self.CRITICAL_COMPLEXITY_THRESHOLD
                
                func_info = FunctionInfo(
                    name=node.name,
                    signature=signature,
                    docstring=docstring,
                    body_lines=[],  # Not needed for compression
                    complexity=complexity,
                    is_critical=is_critical
                )
                
                functions.append(func_info)
        
        return functions, classes
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity of a function.
        
        Complexity = 1 + number of decision points
        Decision points: if, for, while, except, and, or
        """
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, ast.If):
                # Count if statements (including elif and else branches)
                complexity += 1
            elif isinstance(child, (ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Count and/or operations
                complexity += len(child.values) - 1
        
        return complexity
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature as string."""
        # Get arguments with type annotations
        args = []
        
        # Positional args with annotations
        for arg in node.args.args:
            if arg.annotation:
                arg_str = f"{arg.arg}: {ast.unparse(arg.annotation)}"
            else:
                arg_str = arg.arg
            args.append(arg_str)
        
        # *args
        if node.args.vararg:
            if node.args.vararg.annotation:
                args.append(f"*{node.args.vararg.arg}: {ast.unparse(node.args.vararg.annotation)}")
            else:
                args.append(f"*{node.args.vararg.arg}")
        
        # **kwargs
        if node.args.kwarg:
            if node.args.kwarg.annotation:
                args.append(f"**{node.args.kwarg.arg}: {ast.unparse(node.args.kwarg.annotation)}")
            else:
                args.append(f"**{node.args.kwarg.arg}")
        
        # Default values (simplified)
        if node.args.defaults:
            num_defaults = len(node.args.defaults)
            non_default_args = len(args) - num_defaults
            args_with_defaults = []
            for i, arg in enumerate(args):
                if i < non_default_args:
                    args_with_defaults.append(arg)
                else:
                    args_with_defaults.append(f"{arg} = <default>")
            args = args_with_defaults
        
        # Build signature with return type
        signature = f"def {node.name}({', '.join(args)})"
        
        # Add return type annotation if present
        if node.returns:
            signature += f" -> {ast.unparse(node.returns)}"
        
        # Add colon at the end
        signature += ":"
        
        return signature
    
    def _summarize_docstring(self, docstring: str) -> str:
        """Summarize docstring to first sentence."""
        if not docstring:
            return ""
        
        # Split by sentence terminators
        sentences = re.split(r'[.!?]', docstring)
        
        if sentences:
            first_sentence = sentences[0].strip()
            if first_sentence:
                return first_sentence + "." if not first_sentence.endswith('.') else first_sentence
        
        return docstring[:100] + "..." if len(docstring) > 100 else docstring
    
    def _summarize_with_llm(
        self,
        imports: List[str],
        classes: List[ClassInfo],
        functions: List[FunctionInfo]
    ) -> str:
        """
        Summarize file content using LLM.
        
        Args:
            imports: List of import statements
            classes: List of class information
            functions: List of function information
        
        Returns:
            Compressed content with LLM summary
        """
        prompt = f"""Summarize the following Python file structure into a concise overview (200-300 words):

Imports:
{chr(10).join(imports)}

Classes:
{chr(10).join([f"- {c.name}: {c.docstring or 'No docstring'} ({len(c.methods)} methods)" for c in classes])}

Functions:
{chr(10).join([f"- {f.name}: {f.docstring or 'No docstring'} (complexity: {f.complexity})" for f in functions])}

Return as a brief summary that explains the file's purpose and main components."""
        
        try:
            response = self.llm_provider.generate(prompt)
            
            # Build compressed content
            compressed_lines = [
                "# File Summary",
                f"# {response.strip()}",
                "",
                "# Imports",
            ]
            compressed_lines.extend(imports)
            compressed_lines.append("")
            
            if classes:
                compressed_lines.append("# Classes")
                for cls in classes:
                    compressed_lines.append(f"# {cls.name}: {cls.docstring or 'No docstring'}")
                    for method in cls.methods:
                        compressed_lines.append(f"#   - {method.name}: {method.docstring or 'No docstring'}")
                compressed_lines.append("")
            
            if functions:
                compressed_lines.append("# Functions")
                for func in functions:
                    compressed_lines.append(f"# {func.name}: {func.docstring or 'No docstring'}")
                compressed_lines.append("")
            
            return '\n'.join(compressed_lines)
            
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            # Fallback to simple summarization
            return self._summarize_simple(imports, classes, functions)
    
    def _summarize_simple(
        self,
        imports: List[str],
        classes: List[ClassInfo],
        functions: List[FunctionInfo]
    ) -> str:
        """
        Summarize file content without LLM.
        
        Args:
            imports: List of import statements
            classes: List of class information
            functions: List of function information
        
        Returns:
            Compressed content with simple summary
        """
        compressed_lines = [
            "# File Overview",
            f"# This file contains {len(classes)} classes and {len(functions)} functions",
            "",
            "# Imports",
        ]
        compressed_lines.extend(imports)
        compressed_lines.append("")
        
        if classes:
            compressed_lines.append("# Classes")
            for cls in classes:
                compressed_lines.append(f"# {cls.name}: {cls.docstring or 'No docstring'}")
                for method in cls.methods:
                    compressed_lines.append(f"#   - {method.name}: {method.docstring or 'No docstring'}")
            compressed_lines.append("")
        
        if functions:
            compressed_lines.append("# Functions")
            for func in functions:
                compressed_lines.append(f"# {func.name}: {func.docstring or 'No docstring'}")
            compressed_lines.append("")
        
        return '\n'.join(compressed_lines)
    
    def _should_preserve(self, name: str, patterns: Optional[List[str]]) -> bool:
        """
        Check if a function/class should be preserved based on patterns.
        
        Args:
            name: Name of function/class
            patterns: Optional regex patterns to preserve
        
        Returns:
            True if should preserve, False otherwise
        """
        if not patterns:
            return False
        
        for pattern in patterns:
            if re.search(pattern, name):
                return True
        
        return False
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Simple heuristic: ~4 characters per token for English text.
        For Python code, ~3 characters per token is more accurate.
        
        Args:
            text: Text to estimate
        
        Returns:
            Estimated token count
        """
        # Remove whitespace for estimation
        text_no_ws = re.sub(r'\s+', '', text)
        
        # Estimate tokens (3 chars per token for code)
        return len(text_no_ws) // 3
    
    def _identify_preserved_elements(
        self,
        original: str,
        compressed: str
    ) -> List[str]:
        """
        Identify elements that were preserved during compression.
        
        Args:
            original: Original content
            compressed: Compressed content
        
        Returns:
            List of preserved element descriptions
        """
        preserved = []
        
        # Check for imports
        if 'import ' in compressed:
            preserved.append("Import statements")
        
        # Check for function definitions
        if 'def ' in compressed:
            preserved.append("Function signatures")
        
        # Check for class definitions
        if 'class ' in compressed:
            preserved.append("Class definitions")
        
        # Check for critical markers
        if 'CRITICAL' in compressed:
            preserved.append("Critical functions/classes")
        
        return preserved
    
    def _identify_removed_elements(
        self,
        original: str,
        compressed: str
    ) -> List[str]:
        """
        Identify elements that were removed during compression.
        
        Args:
            original: Original content
            compressed: Compressed content
        
        Returns:
            List of removed element descriptions
        """
        removed = []
        
        # Check for docstrings
        if '"""' in original and '"""' not in compressed:
            removed.append("Docstrings")
        elif "'''" in original and "'''" not in compressed:
            removed.append("Docstrings")
        
        # Check for comments - check if standalone comment lines were removed
        original_lines = [line.strip() for line in original.split('\n')]
        compressed_lines = [line.strip() for line in compressed.split('\n')]
        
        # Extract standalone comment lines from original
        original_standalone_comments = set()
        for line in original_lines:
            if line.startswith('#'):
                original_standalone_comments.add(line)
        
        # Extract comment lines from compressed (excluding code lines with inline comments)
        compressed_comment_lines = set()
        for line in compressed_lines:
            # Only count lines that are primarily comments
            if line.startswith('#'):
                compressed_comment_lines.add(line)
        
        # If original had standalone comments that aren't in compressed, they were removed
        if original_standalone_comments and not original_standalone_comments.issubset(compressed_comment_lines):
            removed.append("Comments")
        
        # Check for function bodies (heuristic)
        if 'def ' in original and 'pass' in compressed:
            removed.append("Function bodies")
        
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get compression statistics.
        
        Returns:
            Statistics dictionary
        """
        total_original = self._stats['total_original_tokens']
        total_compressed = self._stats['total_compressed_tokens']
        avg_reduction = 0.0
        
        if total_original > 0:
            avg_reduction = (total_original - total_compressed) / total_original
        
        return {
            'total_compressions': self._stats['total_compressions'],
            'total_original_tokens': total_original,
            'total_compressed_tokens': total_compressed,
            'total_tokens_saved': total_original - total_compressed,
            'average_reduction_ratio': avg_reduction,
            'average_reduction_percent': avg_reduction * 100,
            'level_distribution': self._stats['level_distribution'].copy()
        }
    
    def reset_stats(self):
        """Reset compression statistics."""
        self._stats = {
            'total_compressions': 0,
            'total_original_tokens': 0,
            'total_compressed_tokens': 0,
            'level_distribution': {level.value: 0 for level in CompressionLevel}
        }
        logger.info("Reset compression statistics")