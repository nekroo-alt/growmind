"""
Explanation Generator Module

Generates natural language explanations for decisions made by the adaptive reasoning system.

This module provides:
- Multiple explanation formats (brief, detailed, technical)
- Audience-tailored explanations (developer, manager, user)
- Reasoning chain explanations
- Alternative rejection explanations
- Confidence and uncertainty explanations
"""

import json
from typing import Dict, List, Optional, Any
from enum import Enum
import time
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ExplanationFormat(Enum):
    """Explanation format types."""
    BRIEF = "brief"  # 1-2 sentences, high-level summary
    DETAILED = "detailed"  # Paragraph, step-by-step reasoning
    TECHNICAL = "technical"  # Include technical details and metrics


class AudienceType(Enum):
    """Target audience for explanations."""
    DEVELOPER = "developer"  # Technical audience
    MANAGER = "manager"  # Business audience
    USER = "user"  # End-user audience


@dataclass
class Explanation:
    """Explanation data structure."""
    decision_id: str
    format: ExplanationFormat
    audience: AudienceType
    explanation: str
    reasoning_steps: List[Dict[str, str]] = field(default_factory=list)
    alternatives_considered: List[Dict[str, str]] = field(default_factory=list)
    confidence: Optional[float] = None
    uncertainty: Optional[str] = None
    expected_outcome: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


class ExplanationGenerator:
    """
    Generates natural language explanations for decisions.
    
    Uses template-based generation with support for different formats and audiences.
    """
    
    def __init__(self):
        """Initialize the explanation generator."""
        self.explanation_cache = {}
        
        # Explanation templates for different formats and audiences
        self.templates = {
            (ExplanationFormat.BRIEF, AudienceType.DEVELOPER):
                "I chose to {action} because {reason}.",
            
            (ExplanationFormat.BRIEF, AudienceType.MANAGER):
                "I selected {action} to achieve {goal}.",
            
            (ExplanationFormat.BRIEF, AudienceType.USER):
                "I {action} to help you with {goal}.",
            
            (ExplanationFormat.DETAILED, AudienceType.DEVELOPER):
                "After analyzing the context, I identified that {situation}. "
                "I considered {num_alternatives} alternative actions and selected {action} "
                "because it offers the best balance of success probability ({success_prob}), "
                "efficiency ({efficiency}), and risk mitigation ({risk}). "
                "This decision is expected to {expected_outcome}.",
            
            (ExplanationFormat.DETAILED, AudienceType.MANAGER):
                "Given the current situation of {situation}, I evaluated multiple approaches "
                "and selected {action} as it provides the optimal balance of effectiveness "
                "and resource utilization. The decision has a {confidence}% confidence level "
                "and is expected to deliver {expected_outcome}.",
            
            (ExplanationFormat.DETAILED, AudienceType.USER):
                "I noticed that {situation}. After considering different options, "
                "I chose {action} because it's the most reliable way to {goal}. "
                "I'm {confidence}% confident this will help you.",
            
            (ExplanationFormat.TECHNICAL, AudienceType.DEVELOPER):
                "Decision Analysis:\n"
                "- Context: {context}\n"
                "- Situation Type: {situation_type}\n"
                "- Alternatives Considered: {num_alternatives}\n"
                "- Selected Action: {action}\n"
                "- Decision Factors:\n"
                "  * Success Probability: {success_prob}\n"
                "  * Cost (tokens/time): {cost}\n"
                "  * Risk Level: {risk}\n"
                "  * Time to Complete: {time}\n"
                "- Confidence: {confidence}\n"
                "- Reasoning: {reasoning}\n"
                "- Expected Outcome: {expected_outcome}",
        }
    
    def generate_explanation(
        self,
        decision_data: Dict[str, Any],
        format: ExplanationFormat = ExplanationFormat.DETAILED,
        audience: AudienceType = AudienceType.DEVELOPER
    ) -> Explanation:
        """
        Generate a natural language explanation for a decision.
        
        Args:
            decision_data: Dictionary containing decision information
            format: Explanation format (brief, detailed, technical)
            audience: Target audience (developer, manager, user)
        
        Returns:
            Explanation object with generated text
        """
        try:
            # Generate explanation text
            explanation = self._generate_explanation_text(decision_data, format, audience)
            
            # Generate reasoning steps
            reasoning_steps = self._generate_reasoning_steps(decision_data, format)
            
            # Generate alternatives considered
            alternatives_considered = self._generate_alternatives(decision_data, format)
            
            # Generate uncertainty explanation
            uncertainty = self._generate_uncertainty_explanation(decision_data, format)
            
            # Generate expected outcome
            expected_outcome = self._generate_expected_outcome(decision_data, format)
            
            # Create explanation object
            result = Explanation(
                decision_id=decision_data.get('decision_id', ''),
                format=format,
                audience=audience,
                explanation=explanation,
                reasoning_steps=reasoning_steps,
                alternatives_considered=alternatives_considered,
                confidence=decision_data.get('confidence'),
                uncertainty=uncertainty,
                expected_outcome=expected_outcome,
                timestamp=time.time()
            )
            
            # Cache the explanation
            cache_key = self._get_cache_key(decision_data, format, audience)
            self.explanation_cache[cache_key] = result
            
            logger.debug(f"Generated {format.value} explanation for {audience.value}: {result.decision_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}", exc_info=True)
            # Return a minimal fallback explanation
            return Explanation(
                decision_id=decision_data.get('decision_id', ''),
                format=format,
                audience=audience,
                explanation=f"I decided to {decision_data.get('action', 'take this action')}.",
                timestamp=time.time()
            )
    
    def _generate_explanation_text(
        self,
        decision_data: Dict[str, Any],
        format: ExplanationFormat,
        audience: AudienceType
    ) -> str:
        """Generate the main explanation text."""
        
        # Get template for this format and audience
        template_key = (format, audience)
        template = self.templates.get(
            template_key,
            self.templates[(ExplanationFormat.DETAILED, AudienceType.DEVELOPER)]
        )
        
        # Prepare template variables
        variables = self._prepare_template_variables(decision_data, audience)
        
        # Fill template
        try:
            explanation = template.format(**variables)
        except KeyError as e:
            logger.warning(f"Missing template variable {e}, using fallback")
            explanation = f"I chose to {decision_data.get('action', 'take this action')}."
        
        return explanation
    
    def _prepare_template_variables(
        self,
        decision_data: Dict[str, Any],
        audience: AudienceType
    ) -> Dict[str, str]:
        """Prepare variables for template filling."""
        
        action = decision_data.get('action', 'take action')
        reason = decision_data.get('reasoning', 'it was the best option')
        goal = decision_data.get('goal', 'complete the task')
        situation = decision_data.get('situation', 'the current context')
        situation_type = decision_data.get('situation_type', 'normal')
        
        # Decision factors
        success_prob = decision_data.get('success_probability', 'unknown')
        cost = decision_data.get('cost', 'unknown')
        risk = decision_data.get('risk', 'unknown')
        time_to_complete = decision_data.get('time_to_complete', 'unknown')
        
        # Calculate efficiency
        efficiency = decision_data.get('efficiency', 'good')
        
        # Confidence
        confidence = decision_data.get('confidence', 0.5)
        confidence_pct = int(confidence * 100)
        
        # Alternatives
        num_alternatives = len(decision_data.get('alternatives', []))
        
        # Expected outcome
        expected_outcome = decision_data.get('expected_outcome', 'achieve the goal')
        
        # Context
        context = decision_data.get('context', {})
        context_summary = self._summarize_context(context)
        
        # Reasoning
        reasoning = decision_data.get('reasoning', reason)
        
        return {
            'action': action,
            'reason': reason,
            'goal': goal,
            'situation': situation,
            'situation_type': situation_type,
            'success_prob': success_prob,
            'cost': cost,
            'risk': risk,
            'time': time_to_complete,
            'efficiency': efficiency,
            'confidence': confidence_pct,
            'num_alternatives': num_alternatives,
            'expected_outcome': expected_outcome,
            'context': context_summary,
            'reasoning': reasoning
        }
    
    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """Summarize context for explanation."""
        if not context:
            return "no specific context"
        
        # Extract key information
        context_parts = []
        
        if 'current_action' in context:
            context_parts.append(f"current action: {context['current_action']}")
        
        if 'recent_errors' in context and context['recent_errors']:
            num_errors = len(context['recent_errors'])
            context_parts.append(f"{num_errors} recent errors")
        
        if 'task_progress' in context:
            progress = context['task_progress']
            context_parts.append(f"progress: {progress}")
        
        if 'constraints' in context:
            constraints = context['constraints']
            if isinstance(constraints, list) and constraints:
                context_parts.append(f"constraints: {', '.join(constraints[:3])}")
        
        return '; '.join(context_parts) if context_parts else "standard context"
    
    def _generate_reasoning_steps(
        self,
        decision_data: Dict[str, Any],
        format: ExplanationFormat
    ) -> List[Dict[str, str]]:
        """Generate step-by-step reasoning."""
        
        if format == ExplanationFormat.BRIEF:
            # Brief format doesn't include reasoning steps
            return []
        
        reasoning_chain = decision_data.get('reasoning_chain', [])
        
        if not reasoning_chain:
            # Generate default reasoning steps
            return [
                {
                    'step': 1,
                    'thought': decision_data.get('reasoning', 'Analyzed the situation'),
                    'conclusion': 'Identified the optimal action'
                }
            ]
        
        # Format reasoning chain
        steps = []
        for i, step in enumerate(reasoning_chain, 1):
            steps.append({
                'step': i,
                'thought': step.get('thought', ''),
                'conclusion': step.get('conclusion', '')
            })
        
        return steps
    
    def _generate_alternatives(
        self,
        decision_data: Dict[str, Any],
        format: ExplanationFormat
    ) -> List[Dict[str, str]]:
        """Generate alternatives considered and their rejection reasons."""
        
        if format == ExplanationFormat.BRIEF:
            # Brief format doesn't include alternatives
            return []
        
        alternatives = decision_data.get('alternatives', [])
        
        formatted = []
        for alt in alternatives:
            formatted.append({
                'action': alt.get('action', ''),
                'reason_for_rejection': alt.get('reason_for_rejection', '')
            })
        
        return formatted
    
    def _generate_uncertainty_explanation(
        self,
        decision_data: Dict[str, Any],
        format: ExplanationFormat
    ) -> Optional[str]:
        """Generate explanation of uncertainty."""
        
        if format == ExplanationFormat.BRIEF:
            return None
        
        confidence = decision_data.get('confidence', 0.5)
        
        if confidence >= 0.9:
            return "High confidence based on strong evidence"
        elif confidence >= 0.7:
            return "Moderate confidence, likely to succeed"
        elif confidence >= 0.5:
            return "Uncertain outcome, proceeding with caution"
        else:
            return "Low confidence, decision may need revision"
    
    def _generate_expected_outcome(
        self,
        decision_data: Dict[str, Any],
        format: ExplanationFormat
    ) -> Optional[str]:
        """Generate expected outcome description."""
        
        if format == ExplanationFormat.BRIEF:
            return None
        
        return decision_data.get('expected_outcome', 'Achieve the primary goal')
    
    def _get_cache_key(
        self,
        decision_data: Dict[str, Any],
        format: ExplanationFormat,
        audience: AudienceType
    ) -> str:
        """Generate cache key for explanation."""
        decision_id = decision_data.get('decision_id', '')
        return f"{decision_id}_{format.value}_{audience.value}"
    
    def get_cached_explanation(
        self,
        decision_id: str,
        format: ExplanationFormat = ExplanationFormat.DETAILED,
        audience: AudienceType = AudienceType.DEVELOPER
    ) -> Optional[Explanation]:
        """
        Retrieve a cached explanation if available.
        
        Args:
            decision_id: Decision identifier
            format: Explanation format
            audience: Target audience
        
        Returns:
            Cached explanation if found, None otherwise
        """
        cache_key = f"{decision_id}_{format.value}_{audience.value}"
        return self.explanation_cache.get(cache_key)
    
    def clear_cache(self):
        """Clear the explanation cache."""
        self.explanation_cache.clear()
        logger.debug("Explanation cache cleared")
    
    def generate_brief(
        self,
        decision_data: Dict[str, Any],
        audience: AudienceType = AudienceType.DEVELOPER
    ) -> Explanation:
        """Generate a brief explanation (1-2 sentences)."""
        return self.generate_explanation(
            decision_data,
            format=ExplanationFormat.BRIEF,
            audience=audience
        )
    
    def generate_detailed(
        self,
        decision_data: Dict[str, Any],
        audience: AudienceType = AudienceType.DEVELOPER
    ) -> Explanation:
        """Generate a detailed explanation (paragraph with step-by-step reasoning)."""
        return self.generate_explanation(
            decision_data,
            format=ExplanationFormat.DETAILED,
            audience=audience
        )
    
    def generate_technical(
        self,
        decision_data: Dict[str, Any],
        audience: AudienceType = AudienceType.DEVELOPER
    ) -> Explanation:
        """Generate a technical explanation (with technical details and metrics)."""
        return self.generate_explanation(
            decision_data,
            format=ExplanationFormat.TECHNICAL,
            audience=audience
        )
    
    def export_explanation(self, explanation: Explanation) -> Dict[str, Any]:
        """
        Export explanation as dictionary for serialization.
        
        Args:
            explanation: Explanation object to export
        
        Returns:
            Dictionary representation of explanation
        """
        return {
            'decision_id': explanation.decision_id,
            'format': explanation.format.value,
            'audience': explanation.audience.value,
            'explanation': explanation.explanation,
            'reasoning_steps': explanation.reasoning_steps,
            'alternatives_considered': explanation.alternatives_considered,
            'confidence': explanation.confidence,
            'uncertainty': explanation.uncertainty,
            'expected_outcome': explanation.expected_outcome,
            'timestamp': explanation.timestamp
        }
    
    def validate_explanation(self, explanation: Explanation) -> bool:
        """
        Validate explanation clarity and accuracy.
        
        Args:
            explanation: Explanation object to validate
        
        Returns:
            True if explanation is valid, False otherwise
        """
        # Check required fields
        if not explanation.decision_id:
            logger.warning("Explanation missing decision_id")
            return False
        
        if not explanation.explanation:
            logger.warning("Explanation missing explanation text")
            return False
        
        # Check explanation length
        if len(explanation.explanation) < 10:
            logger.warning(f"Explanation too short: {len(explanation.explanation)} chars")
            return False
        
        if len(explanation.explanation) > 2000:
            logger.warning(f"Explanation too long: {len(explanation.explanation)} chars")
            return False
        
        # For detailed/technical formats, check reasoning steps
        if explanation.format in [ExplanationFormat.DETAILED, ExplanationFormat.TECHNICAL]:
            if not explanation.reasoning_steps:
                logger.warning("Detailed explanation missing reasoning steps")
                return False
        
        return True


# Global singleton instance
_explanation_generator_instance = None


def get_explanation_generator() -> ExplanationGenerator:
    """
    Get the global ExplanationGenerator singleton instance.
    
    Returns:
        ExplanationGenerator singleton instance
    """
    global _explanation_generator_instance
    
    if _explanation_generator_instance is None:
        _explanation_generator_instance = ExplanationGenerator()
    
    return _explanation_generator_instance