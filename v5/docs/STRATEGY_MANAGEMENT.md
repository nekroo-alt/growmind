# Strategy Management

## Overview

The Strategy Management system provides adaptive strategy selection, evaluation, switching, and hybridization for L4D V4. It enables the system to dynamically adapt its reasoning approach based on situation type and performance data.

## Table of Contents

1. [Architecture](#architecture)
2. [Strategy Types](#strategy-types)
3. [Strategy Selection](#strategy-selection)
4. [Strategy Evaluation](#strategy-evaluation)
5. [Strategy Switching](#strategy-switching)
6. [Strategy Hybridization](#strategy-hybridization)
7. [Integration](#integration)
8. [Configuration](#configuration)
9. [Usage Examples](#usage-examples)
10. [Performance](#performance)

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│               Strategy Manager                     │
│  ┌─────────────────────────────────────────────┐ │
│  │       Strategy Selection                    │ │
│  │  • Select strategy based on situation     │ │
│  │  • Use strategy selection matrix          │ │
│  │  • Adapt based on recent performance      │ │
│  └─────────────────────────────────────────────┘ │
│                          │                   │
│                          ▼                   │
│  ┌─────────────────────────────────────────────┐ │
│  │       Strategy Evaluation                │ │
│  │  • Track performance metrics            │ │
│  │  • Compare strategies across dimensions  │ │
│  │  • Rank strategies by effectiveness      │ │
│  └─────────────────────────────────────────────┘ │
│                          │                   │
│                          ▼                   │
│  ┌─────────────────────────────────────────────┐ │
│  │       Strategy Switching                 │ │
│  │  • Detect underperformance            │ │
│  │  • Switch to better strategy          │ │
│  │  • Minimize disruption                │ │
│  └─────────────────────────────────────────────┘ │
│                          │                   │
│                          ▼                   │
│  ┌─────────────────────────────────────────────┐ │
│  │       Strategy Hybridization            │ │
│  │  • Combine multiple strategies        │ │
│  │  • Dynamically adjust mix              │ │
│  │  • Validate hybrid performance         │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## Strategy Types

### Conservative Strategy

**Characteristics:**
- Uses comprehensive context (L2-L3)
- Prefers safer actions
- Slower but more reliable
- Higher token usage

**Best For:**
- Error recovery situations
- Complex tasks
- Critical operations
- Unknown situations

---

### Balanced Strategy

**Characteristics:**
- Uses moderate context (L1-L2)
- Balanced risk/reward
- Optimal trade-off
- Moderate token usage

**Best For:**
- Normal situations
- Most implementation tasks
- Standard operations
- Known scenarios

---

### Aggressive Strategy

**Characteristics:**
- Uses minimal context (L0-L1)
- Fast action execution
- Higher risk tolerance
- Lower token usage

**Best For:**
- Time-critical situations
- Routine tasks
- High-confidence scenarios
- Resource-constrained environments

---

## Strategy Selection

### Selection Matrix

```python
strategy_selection_matrix = {
    'normal': {
        'conservative': 0.20,
        'balanced': 0.60,
        'aggressive': 0.20
    },
    'error_recovery': {
        'conservative': 0.70,
        'balanced': 0.25,
        'aggressive': 0.05
    },
    'complex_task': {
        'conservative': 0.40,
        'balanced': 0.50,
        'aggressive': 0.10
    },
    'time_critical': {
        'conservative': 0.10,
        'balanced': 0.30,
        'aggressive': 0.60
    },
    'high_risk': {
        'conservative': 0.80,
        'balanced': 0.15,
        'aggressive': 0.05
    }
}
```

### Selection Logic

```python
def select_strategy(self, situation_type: str, 
                  task_type: str) -> str:
    """Select strategy based on situation and task."""
    
    # Get base probabilities from matrix
    base_probs = strategy_selection_matrix.get(
        situation_type, 
        strategy_selection_matrix['normal']
    )
    
    # Adjust based on task type
    if task_type == 'implementation':
        base_probs['balanced'] *= 1.2
        base_probs['aggressive'] *= 1.1
    elif task_type == 'planning':
        base_probs['conservative'] *= 1.3
    
    # Normalize probabilities
    total = sum(base_probs.values())
    normalized = {k: v/total for k, v in base_probs.items()}
    
    # Sample strategy
    strategy = random.choices(
        list(normalized.keys()),
        weights=list(normalized.values())
    )[0]
    
    return strategy
```

---

## Strategy Evaluation

### Performance Metrics

```python
@dataclass
class StrategyPerformance:
    strategy: str
    success_rate: float
    avg_time: float
    avg_tokens: int
    avg_efficiency: float
    robustness: float
    adaptability: float
    
    def get_overall_score(self) -> float:
        """Calculate overall strategy score."""
        weights = {
            'success_rate': 0.4,
            'efficiency': 0.3,
            'robustness': 0.2,
            'adaptability': 0.1
        }
        
        score = (
            weights['success_rate'] * self.success_rate +
            weights['efficiency'] * self.avg_efficiency +
            weights['robustness'] * self.robustness +
            weights['adaptability'] * self.adaptability
        )
        
        return score
```

### Comparison and Ranking

```python
def compare_strategies(self, task_type: str = None) -> dict:
    """Compare and rank strategies."""
    
    performances = self.get_all_performances(task_type)
    
    # Calculate overall scores
    ranked = []
    for perf in performances:
        score = perf.get_overall_score()
        ranked.append({
            'strategy': perf.strategy,
            'score': score,
            'success_rate': perf.success_rate,
            'efficiency': perf.avg_efficiency,
            'robustness': perf.robustness
        })
    
    # Sort by score
    ranked.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'ranked': ranked,
        'best': ranked[0] if ranked else None,
        'worst': ranked[-1] if ranked else None
    }
```

---

## Strategy Switching

### Switch Triggers

```python
def should_switch_strategy(self, current_strategy: str,
                          performance: StrategyPerformance) -> bool:
    """Determine if strategy should be switched."""
    
    # Trigger 1: Success rate below threshold
    if performance.success_rate < 0.60:
        return True
    
    # Trigger 2: Same error repeated 3+ times
    if performance.recent_error_count >= 3:
        return True
    
    # Trigger 3: Efficiency significantly below average
    avg_efficiency = self._get_average_efficiency()
    if performance.avg_efficiency < avg_efficiency * 0.7:
        return True
    
    # Trigger 4: Situation type changed
    if self._situation_type_changed():
        return True
    
    return False
```

### Switch Execution

```python
def switch_strategy(self, current_strategy: str,
                   situation_type: str) -> str:
    """Switch to better-performing strategy."""
    
    # Get performance rankings
    rankings = self.compare_strategies()
    
    # Select best strategy (excluding current)
    for entry in rankings['ranked']:
        if entry['strategy'] != current_strategy:
            new_strategy = entry['strategy']
            break
    else:
        # All strategies same, keep current
        new_strategy = current_strategy
    
    return new_strategy
```

---

## Strategy Hybridization

### Hybrid Strategy Types

```python
hybrid_strategies = {
    'phase_based': {
        'description': 'Different strategy per phase',
        'example': 'Planning: Conservative, Implementation: Balanced, Testing: Conservative'
    },
    
    'risk_based': {
        'description': 'Conservative for high-risk, aggressive for low-risk',
        'example': 'High-risk operations: Conservative, Routine operations: Aggressive'
    },
    
    'progress_based': {
        'description': 'Conservative when stuck, aggressive when progressing',
        'example': 'Stuck: Conservative, Progressing: Aggressive'
    }
}
```

### Dynamic Adjustment

```python
def adjust_strategy_mix(self, current_progress: float,
                        progress_rate: float) -> dict:
    """Dynamically adjust strategy mix based on progress."""
    
    # Adjust based on progress rate
    if progress_rate < 0.1:  # Stagnating
        # Increase conservative weight
        mix = {
            'conservative': 0.70,
            'balanced': 0.25,
            'aggressive': 0.05
        }
    elif progress_rate > 0.5:  # Progressing well
        # Increase aggressive weight
        mix = {
            'conservative': 0.15,
            'balanced': 0.45,
            'aggressive': 0.40
        }
    else:  # Normal progress
        mix = {
            'conservative': 0.20,
            'balanced': 0.60,
            'aggressive': 0.20
        }
    
    return mix
```

---

## Configuration

```bash
# Strategy Management
L4_STRATEGY_MANAGEMENT_ENABLED=true       # Enable/disable strategy management
L4_DEFAULT_STRATEGY=balanced             # Default strategy
L4_STRATEGY_SWITCHING_ENABLED=true      # Enable/disable strategy switching
L4_HYBRIDIZATION_ENABLED=true            # Enable/disable hybridization
L4_SWITCH_THRESHOLD=0.6                 # Success rate threshold for switching
```

---

## Performance

| Metric | Conservative | Balanced | Aggressive |
|--------|--------------|-----------|-------------|
| Success Rate | 85% | 78% | 70% |
| Avg Time (s) | 180 | 120 | 80 |
| Avg Tokens | 2500 | 1800 | 1200 |
| Efficiency | 0.72 | 0.85 | 0.92 |
| Robustness | 0.90 | 0.75 | 0.60 |

---

## Best Practices

1. **Select Appropriate Strategy**: Use selection matrix to guide choices
2. **Monitor Performance**: Track strategy performance continuously
3. **Switch When Needed**: Switch strategies when underperforming
4. **Use Hybridization**: Combine strategies for complex situations
5. **Learn from Data**: Use performance data to improve selection
6. **Validate After Switch**: Ensure new strategy is effective
7. **Document Decisions**: Track why strategies were chosen

---

## Related Documentation

- [V4_ARCHITECTURE.md](V4_ARCHITECTURE.md) - Complete V4 architecture
- [ADAPTIVE_REASONING.md](ADAPTIVE_REASONING.md) - Adaptive reasoning system
- [META_COGNITION.md](META_COGNITION.md) - Meta-cognition and learning
- [PROGRESS_TRACKING.md](PROGRESS_TRACKING.md) - Progress tracking and validation