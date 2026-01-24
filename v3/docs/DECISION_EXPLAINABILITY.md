# Decision Explainability

## Overview

The Decision Explainability system provides complete traceability and transparency for all decisions made by L4D V4. It tracks full reasoning chains, generates natural language explanations, and provides visualization for debugging and audit purposes.

## Table of Contents

1. [Architecture](#architecture)
2. [Decision Trace Logging](#decision-trace-logging)
3. [Natural Language Explanations](#natural-language-explanations)
4. [Decision Visualization](#decision-visualization)
5. [Query and Search Interface](#query-and-search-interface)
6. [Integration](#integration)
7. [Configuration](#configuration)
8. [Usage Examples](#usage-examples)
9. [Performance](#performance)

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│                Decision Tracer                      │
│  ┌─────────────────────────────────────────────┐ │
│  │         Trace Logging                        │ │
│  │  • Log decision with full context          │ │
│  │  • Log reasoning chain                     │ │
│  │  • Log alternatives considered             │ │
│  │  • Log outcome and resources              │ │
│  └─────────────────────────────────────────────┘ │
│                          │                   │
│                          ▼                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         Explanation Generator               │ │
│  │  • Generate natural language explanations   │ │
│  │  • Tailor to audience (developer/manager/user)│ │
│  │  • Support multiple formats (brief/detailed)  │ │
│  └─────────────────────────────────────────────┘ │
│                          │                   │
│                          ▼                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         Decision Visualizer                │ │
│  │  • Display decision trees                 │ │
│  │  • Show reasoning chains                  │ │
│  │  • Visualize confidence over time          │ │
│  │  • Export visualizations                 │ │
│  └─────────────────────────────────────────────┘ │
│                          │                   │
│                          ▼                   │
│  ┌─────────────────────────────────────────────┐ │
│  │         Query and Search Interface         │ │
│  │  • Search by task/operation/time         │ │
│  │  • Search by context pattern              │ │
│  │  • Search by outcome/confidence          │ │
│  │  • Export search results                │ │
│  └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Key Principles

1. **Complete Traceability**: Track every decision with full context
2. **Human-Readable**: Generate natural language explanations
3. **Multi-Format**: Support brief, detailed, and technical formats
4. **Audience-Aware**: Tailor explanations to different audiences
5. **Visual**: Provide visual representations of decisions
6. **Searchable**: Easy to query and search decision history

---

## Decision Trace Logging

### Decision Trace Format

```json
{
  "decision_id": "uuid",
  "timestamp": "2026-01-23T10:00:00Z",
  "operation_id": "uuid",
  "task_id": 42,
  
  "context_snapshot": {
    "task_type": "implementation",
    "strategy": "balanced",
    "resources": {"tokens": 1000, "time": 60},
    "recent_errors": [],
    "progress": 0.3
  },
  
  "reasoning_chain": [
    {
      "step": 1,
      "thought": "Analyze current context and situation",
      "conclusion": "Situation is normal, use balanced strategy"
    },
    {
      "step": 2,
      "thought": "Evaluate alternative actions",
      "conclusion": "Implement code has highest expected value"
    },
    {
      "step": 3,
      "thought": "Select best action based on scores",
      "conclusion": "Selected 'implement_code' with confidence 0.85"
    }
  ],
  
  "alternatives": [
    {
      "action": "refactor_code",
      "score": 0.72,
      "reason_for_rejection": "Lower expected value than implementation"
    },
    {
      "action": "add_feature",
      "score": 0.78,
      "reason_for_rejection": "Higher risk than implementation"
    }
  ],
  
  "selected_action": "implement_code",
  "confidence": 0.85,
  
  "outcome": "success",
  "time_elapsed": 120.5,
  
  "resources": {
    "tokens": 1250,
    "time": 120.5,
    "memory": "45MB"
  }
}
```

### Trace Logging Methods

```python
def log_decision(self, decision: Decision):
    """Log decision with full trace."""
    
    cursor = self.db.cursor()
    cursor.execute('''
        INSERT INTO decision_traces (
                decision_id, timestamp, operation_id, task_id,
                context_snapshot, reasoning_chain, alternatives,
                selected_action, confidence, outcome, time_elapsed,
                resources
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        decision.decision_id,
        decision.timestamp,
        decision.operation_id,
        decision.task_id,
        json.dumps(decision.context_snapshot),
        json.dumps(decision.reasoning_chain),
        json.dumps(decision.alternatives),
        decision.selected_action,
        decision.confidence,
        decision.outcome or 'pending',
        decision.time_elapsed,
        json.dumps(decision.resources)
    ))
    self.db.commit()
    
    return decision.decision_id
```

---

## Natural Language Explanations

### Explanation Formats

#### Brief Format

```
Chose to implement feature X (85% confidence) because it has the highest
expected value and lowest risk among alternatives.
```

#### Detailed Format

```
I decided to implement feature X with 85% confidence. 

My reasoning process:
1. I analyzed the current context: task type is 'implementation', 
   no recent errors, progress is at 30%, resources are adequate.
2. Based on this analysis, I identified the situation as 'normal'.
3. I evaluated three alternative actions:
   - Refactor code: Score 0.72, risk 0.15
   - Implement code: Score 0.85, risk 0.10
   - Add feature: Score 0.78, risk 0.20
4. I selected 'implement code' because it has the highest score
   considering both expected value (0.7 weight) and risk (0.2 weight).

I rejected the other alternatives:
- Refactor code: Lower expected value (0.72 vs 0.85)
- Add feature: Higher risk (0.20 vs 0.10)
```

#### Technical Format

```
Decision ID: dec_001
Timestamp: 2026-01-23T10:00:00Z
Context: Implementation task, normal situation, balanced strategy
Reasoning Chain: 3 steps
Alternatives Evaluated: 3
Selected Action: Implement code
Confidence: 0.85
Decision Factors: Success probability: 0.92, Cost: 0.30, 
Risk: 0.10, Time: 0.25, Value: 0.80
Calculated Score: 0.85
Outcome: Success (pending)
Resources: Tokens: 1250, Time: 120.5s
```

### Audience Types

#### Developer Audience

```
I'm implementing feature X using the balanced strategy. 
After analyzing the code structure and dependencies, 
I determined that implementing the feature directly 
is the best approach (85% confidence) rather than 
refactoring first, which would delay the implementation.
```

#### Manager Audience

```
I've chosen to implement feature X now. This decision was made
after evaluating three options: refactoring (low value),
implementing directly (high value, low risk), and adding
extra features (high risk). Implementation directly was selected
as it provides the best balance of speed and quality
(85% confidence). Estimated completion time: 2 hours.
```

#### User Audience

```
I'm working on feature X now. This feature will add new
functionality to help users manage their tasks more efficiently.
I chose to implement it directly rather than refactoring first,
which means we'll be able to deliver it faster while still
maintaining good code quality.
```

### Explanation Generation

```python
def generate_explanation(self, decision_id: str, 
                        format: str = 'detailed',
                        audience: str = 'developer') -> Explanation:
    """Generate natural language explanation."""
    
    # Get decision trace
    trace = self.get_decision_trace(decision_id)
    
    if not trace:
        return Explanation(
            decision_id=decision_id,
            text="Decision not found",
            format=format,
            audience=audience
        )
    
    # Generate based on format
    if format == 'brief':
        text = self._generate_brief_explanation(trace, audience)
    elif format == 'detailed':
        text = self._generate_detailed_explanation(trace, audience)
    elif format == 'technical':
        text = self._generate_technical_explanation(trace, audience)
    else:
        text = self._generate_detailed_explanation(trace, audience)
    
    return Explanation(
        decision_id=decision_id,
        text=text,
        format=format,
        audience=audience,
        confidence=trace['confidence'],
        timestamp=trace['timestamp']
    )
```

---

## Decision Visualization

### Decision Tree Visualization

```
Decision Tree for Task 42

┌─────────────────────────────────────────┐
│              Analyze Context            │
│         Situation: normal (100%)      │
└────────────────┬────────────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
   Conservative  Balanced  Aggressive
    (20%)    (60%)   (20%)
        │        │        │
    ┌───────┐    │
    │       │    │
   Score   Score   Score
   0.72   0.85   0.78
    │       │    │
    └───────┴────┘
            │
       Implement Code
         (Selected)
            │
       Confidence: 85%
```

### Reasoning Chain Visualization

```
Reasoning Chain for Decision dec_001

Step 1: Analyze Context
├─ Thought: Analyze current context and situation
├─ Conclusion: Situation is normal, use balanced strategy
└─ Confidence: 0.90

Step 2: Evaluate Alternatives
├─ Thought: Evaluate alternative actions
├─ Alternatives: 3 evaluated
└─ Scores: [0.72, 0.85, 0.78]

Step 3: Select Action
├─ Thought: Select best action based on scores
├─ Selected: Implement code (score: 0.85)
└─ Confidence: 0.85
```

### Confidence Heatmap

```
Confidence Heatmap for Session

Time      │ 10:00  10:15  10:30  10:45  11:00
──────────┼────────────────────────────────────────
Decision 1│  90%    85%    88%    87%    86%
Decision 2│  85%    82%    80%    78%    75%
Decision 3│  88%    90%    85%    82%    80%
Decision 4│  75%    78%    82%    85%    88%
Decision 5│  80%    75%    78%    80%    82%

Legend: █ 90-100%  ▓ 80-89%  ▒ 70-79%  ░ 60-69%
```

### Visualization Methods

```python
def display_decision_tree(self, task_id: int, max_depth: int = 3):
    """Display decision tree for task."""
    
    # Get decisions for task
    decisions = self.get_decisions_by_task(task_id)
    
    if not decisions:
        print("No decisions found for task")
        return
    
    # Build tree structure
    tree = self._build_decision_tree(decisions, max_depth)
    
    # Display tree
    print(f"\nDecision Tree for Task {task_id}")
    print("=" * 50)
    self._print_tree(tree, indent=0)
    print("=" * 50)

def display_reasoning_chain(self, decision_id: str):
    """Display reasoning chain for decision."""
    
    # Get decision trace
    trace = self.get_decision_trace(decision_id)
    
    if not trace:
        print("Decision not found")
        return
    
    # Display reasoning chain
    print(f"\nReasoning Chain for Decision {decision_id}")
    print("=" * 50)
    
    for step in trace['reasoning_chain']:
        print(f"\nStep {step['step']}:")
        print(f"  Thought: {step['thought']}")
        print(f"  Conclusion: {step['conclusion']}")
    
    print("\n" + "=" * 50)
    print(f"\nSelected Action: {trace['selected_action']}")
    print(f"Confidence: {trace['confidence']:.2%}")

def display_confidence_heatmap(self, task_id: int, 
                           metric: str = 'confidence'):
    """Display confidence heatmap for task."""
    
    # Get decisions for task
    decisions = self.get_decisions_by_task(task_id)
    
    if not decisions:
        print("No decisions found for task")
        return
    
    # Extract metric values
    matrix = []
    timestamps = sorted(set(d['timestamp'] for d in decisions))
    
    for timestamp in timestamps:
        row = []
        for decision in decisions:
            if decision['timestamp'] == timestamp:
                value = decision.get(metric, 0)
                row.append(value)
        
        matrix.append(row)
    
    # Display heatmap
    print(f"\n{metric.capitalize()} Heatmap for Task {task_id}")
    print("=" * 50)
    
    # Print header
    print(f"{'Time':<15}", end="")
    for decision in decisions[:5]:
        print(f"  {decision['decision_id']:<10}", end="")
    print()
    
    # Print rows
    for i, timestamp in enumerate(timestamps):
        print(f"{str(timestamp):<15}", end="")
        for value in matrix[i]:
            if value >= 0.9:
                print("  █", end="")
            elif value >= 0.8:
                print("  ▓", end="")
            elif value >= 0.7:
                print("  ▒", end="")
            elif value >= 0.6:
                print("  ░", end="")
            else:
                print("  ·", end="")
        print()
    
    print("=" * 50)
```

---

## Query and Search Interface

### Search by Task

```python
def search_by_task(self, task_id: int) -> list:
    """Search all decisions for a task."""
    
    cursor = self.db.cursor()
    cursor.execute('''
        SELECT * FROM decision_traces
        WHERE task_id = ?
        ORDER BY timestamp ASC
    ''', (task_id,))
    
    rows = cursor.fetchall()
    return [self._row_to_dict(row) for row in rows]
```

### Search by Operation

```python
def search_by_operation(self, operation_id: str) -> list:
    """Search all decisions for an operation."""
    
    cursor = self.db.cursor()
    cursor.execute('''
        SELECT * FROM decision_traces
        WHERE operation_id = ?
        ORDER BY timestamp ASC
    ''', (operation_id,))
    
    rows = cursor.fetchall()
    return [self._row_to_dict(row) for row in rows]
```

### Search by Time Range

```python
def search_by_time_range(self, start_time: datetime, 
                         end_time: datetime) -> list:
    """Search decisions within time range."""
    
    cursor = self.db.cursor()
    cursor.execute('''
        SELECT * FROM decision_traces
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    ''', (start_time, end_time))
    
    rows = cursor.fetchall()
    return [self._row_to_dict(row) for row in rows]
```

### Search by Context Pattern

```python
def search_by_context_pattern(self, pattern: str) -> list:
    """Search decisions by context pattern."""
    
    cursor = self.db.cursor()
    cursor.execute('''
        SELECT * FROM decision_traces
        WHERE json_extract(context_snapshot, '$.task_type') LIKE ?
           OR json_extract(context_snapshot, '$.strategy') LIKE ?
        ORDER BY timestamp DESC
    ''', (f'%{pattern}%', f'%{pattern}%'))
    
    rows = cursor.fetchall()
    return [self._row_to_dict(row) for row in rows]
```

### Search by Outcome

```python
def search_by_outcome(self, outcome: str) -> list:
    """Search decisions by outcome."""
    
    cursor = self.db.cursor()
    cursor.execute('''
        SELECT * FROM decision_traces
        WHERE outcome = ?
        ORDER BY timestamp DESC
    ''', (outcome,))
    
    rows = cursor.fetchall()
    return [self._row_to_dict(row) for row in rows]
```

### Search by Confidence

```python
def search_by_confidence(self, min_confidence: float,
                        max_confidence: float) -> list:
    """Search decisions by confidence range."""
    
    cursor = self.db.cursor()
    cursor.execute('''
        SELECT * FROM decision_traces
        WHERE confidence BETWEEN ? AND ?
        ORDER BY confidence DESC
    ''', (min_confidence, max_confidence))
    
    rows = cursor.fetchall()
    return [self._row_to_dict(row) for row in rows]
```

### Export Search Results

```python
def export_decisions(self, decisions: list, 
                   output_file: str, 
                   format: str = 'json'):
    """Export decisions to file."""
    
    if format == 'json':
        with open(output_file, 'w') as f:
            json.dump(decisions, f, indent=2)
    
    elif format == 'csv':
        if decisions:
            import csv
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=decisions[0].keys())
                writer.writeheader()
                writer.writerows(decisions)
    
    return output_file
```

---

## Integration

### CLI Commands

```bash
# Explain specific decision
l4-dev explain --decision-id dec_001

# Explain last N decisions
l4-dev explain --last 5

# Show decision tree
l4-dev explain --tree --task-id 42

# Show reasoning chain
l4-dev explain --reasoning --decision-id dec_001

# Show confidence heatmap
l4-dev explain --heatmap --task-id 42

# Export decisions
l4-dev explain --export decisions.json --task-id 42
```

### Programmatic Usage

```python
from v3.logic.explanation_generator import ExplanationGenerator
from v3.data.decision_tracer import DecisionTracer

# Initialize
tracer = DecisionTracer()
generator = ExplanationGenerator()

# Log decision
decision_id = tracer.log_decision(decision)

# Generate explanation
explanation = generator.generate_explanation(
    decision_id=decision_id,
    format='detailed',
    audience='developer'
)

print(f"Explanation: {explanation.text}")
```

---

## Configuration

### Environment Variables

```bash
# Decision Tracing
L4_DECISION_TRACE_ENABLED=true          # Enable/disable decision tracing
L4_DECISION_TRACE_MAX_AGE_DAYS=30      # Max age for traces
L4_DECISION_TRACE_EXPORT_FORMAT=json    # Default export format

# Explanation Generation
L4_EXPLANATION_GENERATOR_ENABLED=true   # Enable/disable explanation generator
L4_EXPLANATION_DEFAULT_FORMAT=detailed  # Default explanation format
L4_EXPLANATION_DEFAULT_AUDIENCE=developer  # Default audience

# Visualization
L4_DECISION_VISUALIZATION_ENABLED=true # Enable/disable visualization
L4_VISUALIZATION_MAX_DEPTH=3            # Max depth for decision tree
```

### Programmatic Configuration

```python
from v3.logic.explanation_generator import ExplanationGeneratorConfig
from v3.data.decision_tracer import DecisionTracerConfig

# Decision Tracer Configuration
tracer_config = DecisionTracerConfig(
    enabled=True,
    max_age_days=30,
    export_format='json'
)

# Explanation Generator Configuration
generator_config = ExplanationGeneratorConfig(
    enabled=True,
    default_format='detailed',
    default_audience='developer',
    cache_explanations=True
)

# Visualization Configuration
viz_config = VisualizationConfig(
    enabled=True,
    max_depth=3,
    show_confidence=True,
    show_alternatives=True
)
```

---

## Usage Examples

### Example 1: Explain Decision

```python
from v3.logic.explanation_generator import ExplanationGenerator

generator = ExplanationGenerator()

# Generate explanation
explanation = generator.generate_explanation(
    decision_id='dec_001',
    format='detailed',
    audience='developer'
)

print(f"Decision: {explanation.decision_id}")
print(f"Explanation: {explanation.text}")
print(f"Confidence: {explanation.confidence:.2%}")
```

### Example 2: Search Decisions

```python
from v3.data.decision_tracer import DecisionTracer

tracer = DecisionTracer()

# Search by task
decisions = tracer.search_by_task(task_id=42)

print(f"Found {len(decisions)} decisions for task 42")
for decision in decisions:
    print(f"  - {decision['decision_id']}: {decision['selected_action']}")

# Search by outcome
failures = tracer.search_by_outcome(outcome='failure')

print(f"Found {len(failures)} failed decisions")
for decision in failures:
    print(f"  - {decision['decision_id']}: {decision['selected_action']}")
```

### Example 3: Visualize Decisions

```python
from v3.core.ui import DecisionVisualizer

visualizer = DecisionVisualizer()

# Display decision tree
visualizer.display_decision_tree(task_id=42, max_depth=3)

# Display reasoning chain
visualizer.display_reasoning_chain(decision_id='dec_001')

# Display confidence heatmap
visualizer.display_confidence_heatmap(task_id=42)
```

### Example 4: Export Decisions

```python
from v3.data.decision_tracer import DecisionTracer

tracer = DecisionTracer()

# Search and export
decisions = tracer.search_by_task(task_id=42)

# Export to JSON
tracer.export_decisions(
    decisions=decisions,
    output_file='decisions_task_42.json',
    format='json'
)

print(f"Exported {len(decisions)} decisions to decisions_task_42.json")
```

---

## Performance

### Tracing Performance

| Operation | Time | Overhead |
|-----------|------|-----------|
| Log Decision | 15ms | 1.5% |
| Get Decision Trace | 10ms | 1% |
| Search by Task | 25ms | 2.5% |
| Search by Context | 50ms | 5% |
| Export Decisions | 100ms | 10% |

### Explanation Generation Performance

| Format | Time | Overhead |
|--------|------|-----------|
| Brief | 50ms | 5% |
| Detailed | 200ms | 20% |
| Technical | 100ms | 10% |

### Visualization Performance

| Visualization | Time | Overhead |
|--------------|------|-----------|
| Decision Tree | 150ms | 15% |
| Reasoning Chain | 100ms | 10% |
| Confidence Heatmap | 200ms | 20% |

---

## Best Practices

1. **Log All Decisions**: Track every decision with full context
2. **Include Reasoning**: Capture complete reasoning chain
3. **Document Alternatives**: Track all considered alternatives
4. **Use Appropriate Format**: Choose format based on audience
5. **Visualize When Helpful**: Use visualizations for complex decisions
6. **Export Regularly**: Export decisions for external analysis
7. **Search Effectively**: Use appropriate search methods
8. **Maintain Traceability**: Ensure all decisions can be traced

---

## Related Documentation

- [V4_ARCHITECTURE.md](V4_ARCHITECTURE.md) - Complete V4 architecture
- [ADAPTIVE_REASONING.md](ADAPTIVE_REASONING.md) - Adaptive reasoning system
- [META_COGNITION.md](META_COGNITION.md) - Meta-cognition and learning
- [STRATEGY_MANAGEMENT.md](STRATEGY_MANAGEMENT.md) - Strategy management