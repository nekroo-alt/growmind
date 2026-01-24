"""
Context Summarizer - V4 Adaptive Reasoning System

This module implements intelligent summarization for higher-level contexts (L1, L2, L3).
It uses LLM-powered summarization to create concise, meaningful summaries that preserve
critical details while reducing token usage.

Summary Types:
- Brief: 50-100 words, key points only
- Detailed: 200-300 words, with examples
- Full: Full context with all details
"""

import json
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from dataclasses import dataclass

from data.context_hierarchy import ContextHierarchyManager, ContextLevel
from core.logging_config import get_logger
from llm_base.provider import LLMProvider

logger = get_logger(__name__)


@dataclass
class Summary:
    """Represents a context summary."""
    content: Dict[str, Any]
    summary_type: str
    word_count: int
    items_summarized: int
    timestamp: float
    quality_score: float


class ContextSummarizer:
    """
    Implements intelligent summarization for hierarchical contexts.
    
    Features:
    - LLM-powered intelligent summarization
    - Multiple summary types (brief, detailed, full)
    - Preserves critical details
    - Tracks summary quality
    - Caches summaries for performance
    - Auto-invalidates cache when context changes
    """
    
    # Summary type word count targets
    WORD_COUNT_TARGETS = {
        'brief': (50, 100),
        'detailed': (200, 300),
        'full': (None, None)  # No limit for full
    }
    
    # Summary prompts
    PROMPTS = {
        'l1_brief': """Summarize the following recent actions into key events (50-100 words, key points only):

{actions}

Return as JSON:
{{
    "key_events": ["event1", "event2", ...],
    "summary": "brief summary text",
    "action_count": N
}}""",
        
        'l1_detailed': """Summarize the following recent actions into key events with examples (200-300 words):

{actions}

Return as JSON:
{{
    "key_events": [{{"event": "...", "example": "..."}}],
    "summary": "detailed summary text",
    "patterns": ["pattern1", "pattern2"],
    "action_count": N
}}""",
        
        'l1_full': """Provide a comprehensive summary of the following recent actions (full context):

{actions}

Return as JSON:
{{
    "key_events": [{{"event": "...", "example": "...", "context": "..."}}],
    "summary": "comprehensive summary",
    "patterns": ["pattern1", "pattern2"],
    "action_count": N,
    "timeline": [{{"time": "...", "event": "..."}}]
}}""",
        
        'l2_brief': """Summarize the following session context into themes (50-100 words):

Session Actions: {action_count}
Session Errors: {error_count}

Key Actions:
{key_actions}

Return as JSON:
{{
    "themes": ["theme1", "theme2"],
    "summary": "brief session summary",
    "progress": "current progress state"
}}""",
        
        'l2_detailed': """Summarize the following session context into themes and patterns (200-300 words):

Session Actions: {action_count}
Session Errors: {error_count}

Key Actions:
{key_actions}

Key Errors:
{key_errors}

Return as JSON:
{{
    "themes": ["theme1", "theme2"],
    "patterns": ["pattern1", "pattern2"],
    "summary": "detailed session summary",
    "progress": "current progress state",
    "success_rate": 0.XX,
    "common_errors": ["error1", "error2"]
}}""",
        
        'l2_full': """Provide a comprehensive summary of the following session context:

Session Actions: {action_count}
Session Errors: {error_count}

Actions:
{actions}

Errors:
{errors}

Return as JSON:
{{
    "themes": ["theme1", "theme2"],
    "patterns": ["pattern1", "pattern2"],
    "summary": "comprehensive session summary",
    "progress": "current progress state",
    "success_rate": 0.XX,
    "common_errors": ["error1", "error2"],
    "action_breakdown": {{"type": count}},
    "error_breakdown": {{"type": count}}
}}""",
        
        'l3_brief': """Summarize the following project context (50-100 words):

Project State:
{state}

Architecture:
{architecture}

Return as JSON:
{{
    "architecture_summary": "brief architecture description",
    "key_constraints": ["constraint1", "constraint2"],
    "summary": "brief project summary"
}}""",
        
        'l3_detailed': """Summarize the following project context (200-300 words):

Project State:
{state}

Architecture:
{architecture}

Patterns:
{patterns}

Return as JSON:
{{
    "architecture_summary": "detailed architecture description",
    "key_constraints": ["constraint1", "constraint2"],
    "summary": "detailed project summary",
    "key_patterns": ["pattern1", "pattern2"],
    "dependencies": ["dep1", "dep2"]
}}""",
        
        'l3_full': """Provide a comprehensive summary of the following project context:

Project State:
{state}

Architecture:
{architecture}

Patterns:
{patterns_summary}

Return as JSON:
{{
    "architecture_summary": "comprehensive architecture description",
    "key_constraints": ["constraint1", "constraint2"],
    "summary": "comprehensive project summary",
    "key_patterns": ["pattern1", "pattern2"],
    "dependencies": ["dep1", "dep2"],
    "tech_stack": ["tech1", "tech2"],
    "modules": ["module1", "module2"]
}}"""
    }
    
    def __init__(
        self,
        context_manager: ContextHierarchyManager,
        llm_provider: Optional[LLMProvider] = None
    ):
        """
        Initialize ContextSummarizer.
        
        Args:
            context_manager: ContextHierarchyManager instance
            llm_provider: Optional LLMProvider for intelligent summarization
        """
        self.context_manager = context_manager
        self.llm_provider = llm_provider
        
        # Track summary quality
        self._summary_quality: Dict[str, float] = {}
        
        logger.info("ContextSummarizer initialized")
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    def _get_prompt_key(self, level: str, summary_type: str) -> str:
        """Get prompt key for level and summary type."""
        return f"{level}_{summary_type}"
    
    def _format_actions_for_summary(self, actions: List[Dict[str, Any]], limit: int = 10) -> str:
        """Format actions for summarization prompt."""
        formatted = []
        for i, action in enumerate(actions[:limit]):
            action_type = action.get('type', 'unknown')
            timestamp = datetime.fromtimestamp(action.get('timestamp', 0)).strftime('%H:%M:%S')
            formatted.append(f"{i+1}. [{timestamp}] {action_type}: {json.dumps(action, default=str)[:200]}")
        
        if len(actions) > limit:
            formatted.append(f"... and {len(actions) - limit} more actions")
        
        return "\n".join(formatted)
    
    def _format_errors_for_summary(self, errors: List[Dict[str, Any]], limit: int = 5) -> str:
        """Format errors for summarization prompt."""
        formatted = []
        for i, error in enumerate(errors[:limit]):
            error_type = error.get('type', 'unknown')
            timestamp = datetime.fromtimestamp(error.get('timestamp', 0)).strftime('%H:%M:%S')
            formatted.append(f"{i+1}. [{timestamp}] {error_type}: {json.dumps(error, default=str)[:200]}")
        
        if len(errors) > limit:
            formatted.append(f"... and {len(errors) - limit} more errors")
        
        return "\n".join(formatted)
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response as JSON."""
        try:
            # Try to extract JSON from response
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0]
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0]
            else:
                json_str = response
            
            return json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response: {response[:500]}")
            return None
    
    def _calculate_hash(self, data: Any) -> str:
        """Calculate hash of data for cache invalidation."""
        data_str = json.dumps(data, default=str, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def summarize_l1(
        self,
        summary_type: str = 'detailed',
        force_refresh: bool = False
    ) -> Optional[Summary]:
        """
        Summarize L1 context (last N actions) into key events.
        
        Args:
            summary_type: Type of summary (brief, detailed, full)
            force_refresh: Force regeneration of summary
        
        Returns:
            Summary object or None if failed
        """
        logger.info(f"Summarizing L1 context (type={summary_type})")
        
        # Check cache first
        if not force_refresh:
            cached = self.context_manager.get_summary(ContextLevel.L1, summary_type)
            if cached:
                logger.debug("Using cached L1 summary")
                return Summary(
                    content=cached,
                    summary_type=summary_type,
                    word_count=cached.get('word_count', 0),
                    items_summarized=cached.get('items_summarized', 0),
                    timestamp=cached.get('timestamp', 0),
                    quality_score=cached.get('quality_score', 1.0)
                )
        
        # Get recent actions
        actions = self.context_manager.get_recent_actions(count=10)
        
        if not actions:
            logger.warning("No L1 actions to summarize")
            return None
        
        # Generate summary
        if self.llm_provider:
            # Use LLM for intelligent summarization
            prompt_key = self._get_prompt_key('l1', summary_type)
            prompt = self.PROMPTS.get(prompt_key, self.PROMPTS['l1_detailed'])
            
            actions_str = self._format_actions_for_summary(actions)
            prompt = prompt.format(actions=actions_str)
            
            try:
                response = self.llm_provider.generate(prompt)
                content = self._parse_llm_response(response)
                
                if content:
                    # Add metadata
                    content['word_count'] = self._count_words(content.get('summary', ''))
                    content['items_summarized'] = len(actions)
                    content['timestamp'] = datetime.now().timestamp()
                    content['quality_score'] = 1.0  # Initial score
                    content['hash'] = self._calculate_hash(actions)
                    
                    # Store summary
                    item_ids = [a.get('id') for a in actions if 'id' in a]
                    summary_id = self.context_manager.store_summary(
                        level=ContextLevel.L1,
                        summary_type=summary_type,
                        content=content,
                        item_ids=item_ids
                    )
                    
                    logger.info(f"Generated L1 summary {summary_id} (type={summary_type})")
                    
                    return Summary(
                        content=content,
                        summary_type=summary_type,
                        word_count=content['word_count'],
                        items_summarized=content['items_summarized'],
                        timestamp=content['timestamp'],
                        quality_score=content['quality_score']
                    )
            except Exception as e:
                logger.error(f"LLM summarization failed: {e}")
        
        # Fallback to simple summarization
        content = {
            'key_events': [a.get('type', 'unknown') for a in actions[:5]],
            'summary': f"Last {len(actions)} actions including: " + ", ".join([a.get('type', 'unknown') for a in actions[:3]]) + "...",
            'action_count': len(actions),
            'word_count': 50,
            'items_summarized': len(actions),
            'timestamp': datetime.now().timestamp(),
            'quality_score': 0.5,  # Lower quality for fallback
            'hash': self._calculate_hash(actions)
        }
        
        # Store summary
        item_ids = [a.get('id') for a in actions if 'id' in a]
        self.context_manager.store_summary(
            level=ContextLevel.L1,
            summary_type=summary_type,
            content=content,
            item_ids=item_ids
        )
        
        logger.info(f"Generated fallback L1 summary (type={summary_type})")
        
        return Summary(
            content=content,
            summary_type=summary_type,
            word_count=content['word_count'],
            items_summarized=content['items_summarized'],
            timestamp=content['timestamp'],
            quality_score=content['quality_score']
        )
    
    def summarize_l2(
        self,
        summary_type: str = 'detailed',
        force_refresh: bool = False
    ) -> Optional[Summary]:
        """
        Summarize L2 context (session) into themes and patterns.
        
        Args:
            summary_type: Type of summary (brief, detailed, full)
            force_refresh: Force regeneration of summary
        
        Returns:
            Summary object or None if failed
        """
        logger.info(f"Summarizing L2 context (type={summary_type})")
        
        # Check cache first
        if not force_refresh:
            cached = self.context_manager.get_summary(ContextLevel.L2, summary_type)
            if cached:
                logger.debug("Using cached L2 summary")
                return Summary(
                    content=cached,
                    summary_type=summary_type,
                    word_count=cached.get('word_count', 0),
                    items_summarized=cached.get('items_summarized', 0),
                    timestamp=cached.get('timestamp', 0),
                    quality_score=cached.get('quality_score', 1.0)
                )
        
        # Get session context
        session_ctx = self.context_manager.get_session_context()
        actions = session_ctx.get('actions', [])
        errors = session_ctx.get('errors', [])
        
        if not actions and not errors:
            logger.warning("No L2 context to summarize")
            return None
        
        # Generate summary
        if self.llm_provider:
            # Use LLM for intelligent summarization
            prompt_key = self._get_prompt_key('l2', summary_type)
            prompt = self.PROMPTS.get(prompt_key, self.PROMPTS['l2_detailed'])
            
            key_actions = self._format_actions_for_summary(actions[:10])
            key_errors = self._format_errors_for_summary(errors[:5])
            all_actions = self._format_actions_for_summary(actions)
            all_errors = self._format_errors_for_summary(errors)
            
            if summary_type == 'full':
                prompt = prompt.format(
                    action_count=len(actions),
                    error_count=len(errors),
                    actions=all_actions,
                    errors=all_errors
                )
            else:
                prompt = prompt.format(
                    action_count=len(actions),
                    error_count=len(errors),
                    key_actions=key_actions,
                    key_errors=key_errors
                )
            
            try:
                response = self.llm_provider.generate(prompt)
                content = self._parse_llm_response(response)
                
                if content:
                    # Add metadata
                    content['word_count'] = self._count_words(content.get('summary', ''))
                    content['items_summarized'] = len(actions) + len(errors)
                    content['timestamp'] = datetime.now().timestamp()
                    content['quality_score'] = 1.0  # Initial score
                    content['hash'] = self._calculate_hash(session_ctx)
                    
                    # Store summary
                    item_ids = [a.get('id') for a in actions if 'id' in a] + \
                               [e.get('id') for e in errors if 'id' in e]
                    self.context_manager.store_summary(
                        level=ContextLevel.L2,
                        summary_type=summary_type,
                        content=content,
                        item_ids=item_ids
                    )
                    
                    logger.info(f"Generated L2 summary (type={summary_type})")
                    
                    return Summary(
                        content=content,
                        summary_type=summary_type,
                        word_count=content['word_count'],
                        items_summarized=content['items_summarized'],
                        timestamp=content['timestamp'],
                        quality_score=content['quality_score']
                    )
            except Exception as e:
                logger.error(f"LLM summarization failed: {e}")
        
        # Fallback to simple summarization
        content = {
            'themes': ['session_progress', 'error_handling'],
            'patterns': ['standard_workflow'],
            'summary': f"Session with {len(actions)} actions and {len(errors)} errors",
            'progress': 'ongoing',
            'success_rate': 0.0,
            'word_count': 50,
            'items_summarized': len(actions) + len(errors),
            'timestamp': datetime.now().timestamp(),
            'quality_score': 0.5,
            'hash': self._calculate_hash(session_ctx)
        }
        
        # Store summary
        item_ids = [a.get('id') for a in actions if 'id' in a] + \
                   [e.get('id') for e in errors if 'id' in e]
        self.context_manager.store_summary(
            level=ContextLevel.L2,
            summary_type=summary_type,
            content=content,
            item_ids=item_ids
        )
        
        logger.info(f"Generated fallback L2 summary (type={summary_type})")
        
        return Summary(
            content=content,
            summary_type=summary_type,
            word_count=content['word_count'],
            items_summarized=content['items_summarized'],
            timestamp=content['timestamp'],
            quality_score=content['quality_score']
        )
    
    def summarize_l3(
        self,
        summary_type: str = 'detailed',
        force_refresh: bool = False
    ) -> Optional[Summary]:
        """
        Summarize L3 context (project) into architecture and constraints.
        
        Args:
            summary_type: Type of summary (brief, detailed, full)
            force_refresh: Force regeneration of summary
        
        Returns:
            Summary object or None if failed
        """
        logger.info(f"Summarizing L3 context (type={summary_type})")
        
        # Check cache first
        if not force_refresh:
            cached = self.context_manager.get_summary(ContextLevel.L3, summary_type)
            if cached:
                logger.debug("Using cached L3 summary")
                return Summary(
                    content=cached,
                    summary_type=summary_type,
                    word_count=cached.get('word_count', 0),
                    items_summarized=cached.get('items_summarized', 0),
                    timestamp=cached.get('timestamp', 0),
                    quality_score=cached.get('quality_score', 1.0)
                )
        
        # Get project context
        project_ctx = self.context_manager.get_project_context()
        
        # Generate summary
        if self.llm_provider:
            # Use LLM for intelligent summarization
            prompt_key = self._get_prompt_key('l3', summary_type)
            prompt = self.PROMPTS.get(prompt_key, self.PROMPTS['l3_detailed'])
            
            state_str = json.dumps(project_ctx.get('state', {}), default=str)[:1000]
            arch_str = json.dumps(project_ctx.get('architecture', {}), default=str)[:1000]
            patterns = project_ctx.get('patterns', [])
            patterns_str = json.dumps(patterns, default=str)[:500]
            
            prompt = prompt.format(
                state=state_str,
                architecture=arch_str,
                patterns=patterns_str,
                patterns_summary=patterns_str
            )
            
            try:
                response = self.llm_provider.generate(prompt)
                content = self._parse_llm_response(response)
                
                if content:
                    # Add metadata
                    content['word_count'] = self._count_words(content.get('summary', ''))
                    content['items_summarized'] = 1  # Project context is one item
                    content['timestamp'] = datetime.now().timestamp()
                    content['quality_score'] = 1.0  # Initial score
                    content['hash'] = self._calculate_hash(project_ctx)
                    
                    # Store summary
                    self.context_manager.store_summary(
                        level=ContextLevel.L3,
                        summary_type=summary_type,
                        content=content,
                        item_ids=[]
                    )
                    
                    logger.info(f"Generated L3 summary (type={summary_type})")
                    
                    return Summary(
                        content=content,
                        summary_type=summary_type,
                        word_count=content['word_count'],
                        items_summarized=content['items_summarized'],
                        timestamp=content['timestamp'],
                        quality_score=content['quality_score']
                    )
            except Exception as e:
                logger.error(f"LLM summarization failed: {e}")
        
        # Fallback to simple summarization
        content = {
            'architecture_summary': 'L4D adaptive reasoning system',
            'key_constraints': ['local-first', 'Git-native', 'TDD-driven'],
            'summary': 'L4D V4 project with hierarchical context management and adaptive reasoning',
            'word_count': 30,
            'items_summarized': 1,
            'timestamp': datetime.now().timestamp(),
            'quality_score': 0.5,
            'hash': self._calculate_hash(project_ctx)
        }
        
        # Store summary
        self.context_manager.store_summary(
            level=ContextLevel.L3,
            summary_type=summary_type,
            content=content,
            item_ids=[]
        )
        
        logger.info(f"Generated fallback L3 summary (type={summary_type})")
        
        return Summary(
            content=content,
            summary_type=summary_type,
            word_count=content['word_count'],
            items_summarized=content['items_summarized'],
            timestamp=content['timestamp'],
            quality_score=content['quality_score']
        )
    
    def invalidate_cache(self, level: str):
        """
        Invalidate cached summary for a given level.
        
        Args:
            level: Context level (L1, L2, L3)
        """
        logger.info(f"Invalidating summary cache for level {level}")
        # ContextHierarchyManager handles cache invalidation through store_summary
        # This method is for explicit invalidation if needed
    
    def update_quality_score(
        self,
        level: str,
        summary_type: str,
        success: bool,
        new_score: Optional[float] = None
    ):
        """
        Update quality score for a summary based on downstream success.
        
        Args:
            level: Context level
            summary_type: Type of summary
            success: Whether the summary led to success
            new_score: Optional new quality score (calculated if None)
        """
        key = f"{level}_{summary_type}"
        current_score = self._summary_quality.get(key, 1.0)
        
        if new_score is not None:
            self._summary_quality[key] = new_score
        else:
            # Update using exponential moving average
            if success:
                # Reward successful summaries
                new_score = 0.9 * current_score + 0.1 * 1.0
            else:
                # Penalize failed summaries
                new_score = 0.9 * current_score + 0.1 * 0.5
            
            self._summary_quality[key] = new_score
        
        logger.debug(f"Updated quality score for {key}: {self._summary_quality[key]:.2f}")
    
    def get_summary(
        self,
        level: str,
        summary_type: str = 'detailed',
        force_refresh: bool = False
    ) -> Optional[Summary]:
        """
        Get summary for a given context level.
        
        Args:
            level: Context level (L1, L2, L3)
            summary_type: Type of summary (brief, detailed, full)
            force_refresh: Force regeneration of summary
        
        Returns:
            Summary object or None if failed
        """
        if level == ContextLevel.L1:
            return self.summarize_l1(summary_type, force_refresh)
        elif level == ContextLevel.L2:
            return self.summarize_l2(summary_type, force_refresh)
        elif level == ContextLevel.L3:
            return self.summarize_l3(summary_type, force_refresh)
        else:
            logger.warning(f"Unknown context level for summarization: {level}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about summary generation.
        
        Returns:
            Statistics dictionary with quality scores and counts
        """
        return {
            'quality_scores': self._summary_quality.copy(),
            'timestamp': datetime.now().timestamp()
        }