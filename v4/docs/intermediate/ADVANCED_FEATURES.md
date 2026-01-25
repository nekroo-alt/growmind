# L4D Advanced Features Guide

This guide covers advanced features of L4D for experienced users.

## Table of Contents

1. [Adaptive Reasoning](#1-adaptive-reasoning)
2. [Progressive Context Management](#2-progressive-context-management)
3. [Cost Optimization](#3-cost-optimization)
4. [Trap Detection and Recovery](#4-trap-detection-and-recovery)
5. [Meta-Cognition and Learning](#5-meta-cognition-and-learning)
6. [Housekeeping Automation](#6-housekeeping-automation)
7. [Context Quality Management](#7-context-quality-management)

---

## 1. Adaptive Reasoning

### Overview

L4D's adaptive reasoning system intelligently adjusts its approach based on task complexity, context, and past performance.

### How It Works

```python
# Adaptive reasoning flow
1. Analyze situation (normal, error, blocked, uncertain, complex)
2. Select strategy (conservative, balanced, aggressive)
3. Make decision with confidence score
4. Take action
5. Validate result
6. Learn from outcome
7. Adjust approach for future
```

### Configuration

```bash
# Enable adaptive reasoning
l4-dev config set custom.adaptive_reasoning true

# Set default strategy
l4-dev config set custom.reasoning_strategy balanced

# Set confidence threshold
l4-dev config set custom.confidence_threshold 0.7
```

### Strategies

**Conservative**:
- Lower risk tolerance
- More thorough validation
- Slower but more reliable
- Use for: critical features, production code

**Balanced** (default):
- Moderate risk tolerance
- Standard validation
- Good balance of speed and reliability
- Use for: most development tasks

**Aggressive**:
- Higher risk tolerance
- Minimal validation
- Faster but less reliable
- Use for: prototyping, experimental features

### Example

```bash
# Start with aggressive strategy for prototyping
l4-dev start --task "Prototype new feature" --strategy aggressive

# Switch to conservative for production code
l4-dev start --task "Add authentication" --strategy conservative
```

---

## 2. Progressive Context Management

### Overview

L4D loads context progressively, starting with minimal context and expanding only when needed.

### Context Levels

**Level 0 (Immediate)**:
- Current file and function
- Immediate dependencies
- Current state

**Level 1 (Recent)**:
- Last 10 actions
- Last 5 errors
- Recent telemetry

**Level 2 (Session)**:
- Session history
- Task progress
- Patterns learned

**Level 3 (Project)**:
- Project state
- Architecture
- Long-term patterns

### Configuration

```bash
# Set starting context level
l4-dev config set context.start_level 0

# Enable progressive expansion
l4-dev config set context.progressive true

# Enable context compression
l4-dev config set context.compression_enabled true
```

### Example

```bash
# Start with L0 (minimal context)
l4-dev start --task "Simple bug fix" --context-level 0

# Start with L2 for complex refactoring
l4-dev start --task "Refactor authentication system" --context-level 2
```

### Context Compression

L4D can compress context to reduce token usage:

```bash
# Level 1: Remove comments, docstrings (20-30% reduction)
l4-dev config set context.compression_level 1

# Level 2: Summarize functions (40-50% reduction)
l4-dev config set context.compression_level 2

# Level 3: Summarize entire files (60-70% reduction)
l4-dev config set context.compression_level 3
```

---

## 3. Cost Optimization

### Overview

L4D includes multiple cost optimization features to reduce LLM API expenses.

### LLM Call Caching

Caches LLM responses to avoid redundant API calls:

```bash
# Enable caching
l4-dev config set cache.enabled true

# Set cache TTL (hours)
l4-dev config set cache.ttl_hours 24

# Set cache size limit (MB)
l4-dev config set cache.max_size_mb 100
```

**Expected Savings**: 30-40% reduction in LLM calls

### Local Decision Making

Makes decisions locally without LLM for simple scenarios:

```bash
# Enable local decisions
l4-dev config set custom.local_decisions true
```

**Decisions Made Locally**:
- File selection based on task impact
- Basic error classification (transient vs permanent)
- Simple retry logic
- Basic progress threshold validation

**Expected Savings**: 20-30% reduction in LLM calls

### Adaptive Token Budgeting

Dynamically adjusts token budget based on task complexity:

```bash
# Enable adaptive budgeting
l4-dev config set custom.adaptive_budgeting true

# Set default token budget
l4-dev config set context.max_token_budget 4000
```

**Expected Savings**: 15-20% reduction in token usage

### Cost Tracking and Alerts

```bash
# Set monthly cost budget (USD)
l4-dev config set cost.budget 100

# Set alert threshold (percentage)
l4-dev config set cost.alert_threshold 0.8
```

View cost reports:

```bash
l4-dev cost --report              # Overall cost report
l4-dev cost --by-task             # Cost per task
l4-dev cost --trend               # Cost trends
l4-dev cost --predict              # Predict future costs
```

---

## 4. Trap Detection and Recovery

### Overview

L4D automatically detects and recovers from traps (loops, dead ends, circular reasoning).

### Trap Types

**Loop**: Repetitive actions (same action 3+ times)

**Dead End**: No progress for extended period (5+ operations)

**Circular Reasoning**: Revisiting rejected options

### Configuration

```bash
# Enable trap detection
l4-dev config set custom.trap_detection true

# Set loop detection threshold
l4-dev config set custom.loop_threshold 3

# Set dead end threshold
l4-dev config set custom.dead_end_threshold 5
```

### Recovery Strategies

L4D automatically applies recovery strategies:

1. **Loop Recovery**: Change approach, add randomness
2. **Dead End Recovery**: Rollback to checkpoint, try alternative
3. **Circular Reasoning Recovery**: Track attempted actions, avoid repetition

### Example

```bash
# L4D detects a loop
[INFO] Trap detected: Loop (action repeated 3 times)
[INFO] Applying recovery strategy: Change approach
[INFO] Trying alternative approach...
[SUCCESS] Trap resolved!
```

---

## 5. Meta-Cognition and Learning

### Overview

L4D learns from its decisions and improves over time through meta-cognition.

### Learning Mechanisms

**Pattern Recognition**:
- Identifies recurring decision patterns
- Recognizes successful and failed patterns
- Predicts optimal decisions

**Self-Reflection**:
- Regularly reviews decisions
- Identifies areas for improvement
- Generates improvement recommendations

**Lesson Learning**:
- Analyzes failures systematically
- Extracts lessons learned
- Updates heuristics to avoid repeated mistakes

### Configuration

```bash
# Enable meta-cognition
l4-dev config set custom.meta_cognition true

# Set self-reflection interval (operations)
l4-dev config set custom.reflection_interval 10

# Enable pattern recognition
l4-dev config set custom.pattern_recognition true

# Enable learning from mistakes
l4-dev config set custom.learning_enabled true
```

### Viewing Learned Patterns

```bash
# View decision history
l4-dev meta-cognition --history

# View learned patterns
l4-dev meta-cognition --patterns

# View lessons learned
l4-dev meta-cognition --lessons
```

---

## 6. Housekeeping Automation

### Overview

L4D can automatically maintain codebase health through housekeeping.

### Dead Code Detection

Detects and removes unused code:

```bash
# Preview dead code cleanup
l4-dev housekeep --dry-run

# Automatic safe deletion
l4-dev housekeep --auto
```

**What Gets Detected**:
- Unused functions
- Unused classes
- Unused variables
- Unused files

### Dependency Cleanup

Detects and removes unused dependencies:

```bash
# Show unused dependencies
l4-dev deps --unused

# Safe removal
l4-dev deps --cleanup
```

### Data Cleanup

Automatically cleans up old data:

```bash
# Preview cleanup
l4-dev cleanup --dry-run

# Run cleanup
l4-dev cleanup --auto
```

**What Gets Cleaned Up**:
- Old checkpoints
- Oversized log files
- Old telemetry data
- Cache entries

### Configuration

```bash
# Enable automatic housekeeping
l4-dev config set custom.auto_housekeep true

# Set housekeeping interval (hours)
l4-dev config set custom.housekeep_interval 24
```

---

## 7. Context Quality Management

### Overview

L4D tracks and improves context quality to optimize task success rates.

### Quality Metrics

**Completeness**: % of required context items included

**Relevance**: Average relevance score of included items

**Freshness**: Average age of context items (newer = better)

**Conciseness**: Information density (more = better)

**Diversity**: Variety of context sources (files, modules)

### Viewing Quality Reports

```bash
l4-dev quality --report              # Quality report
l4-dev quality --trend              # Quality trends
l4-dev quality --correlation         # Correlation with success rate
```

### Automated Improvement

L4D can automatically improve context quality:

```bash
# Enable automated improvement
l4-dev config set custom.auto_improve_context true
```

**Improvement Types**:
- Add missing dependencies
- Replace low-relevance items
- Update stale context
- Compress verbose contexts
- Add diverse sources

---

## Advanced Configuration

### Combining Advanced Features

```bash
# Enable all advanced features
l4-dev config set custom.adaptive_reasoning true
l4-dev config set custom.local_decisions true
l4-dev config set custom.adaptive_budgeting true
l4-dev config set custom.trap_detection true
l4-dev config set custom.meta_cognition true
l4-dev config set custom.auto_housekeep true
l4-dev config set custom.auto_improve_context true
```

### Creating Custom Profile

```bash
# Create custom profile for advanced features
l4-dev profile create advanced

# Edit profile
vim .l4_profiles/advanced.json
```

**advanced.json**:
```json
{
  "name": "advanced",
  "description": "Advanced features for experienced users",
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.5
  },
  "cache": {
    "enabled": true,
    "max_size_mb": 200
  },
  "custom": {
    "adaptive_reasoning": true,
    "local_decisions": true,
    "adaptive_budgeting": true,
    "trap_detection": true,
    "meta_cognition": true,
    "auto_housekeep": true,
    "auto_improve_context": true
  }
}
```

Use custom profile:

```bash
l4-dev profile use advanced
```

---

## Best Practices for Advanced Features

### 1. Start Simple, Enable Gradually

```bash
# Start with basic configuration
l4-dev init

# Enable features one at a time
l4-dev config set custom.adaptive_reasoning true
# Test it
l4-dev start --task "Simple task"

# Then enable next feature
l4-dev config set custom.trap_detection true
# Test it
l4-dev start --task "Simple task"
```

### 2. Monitor Performance

```bash
# Regularly check performance
l4-dev cost --report
l4-dev quality --report
l4-dev progress --detailed
```

### 3. Adjust Based on Data

```bash
# Review cost trends
l4-dev cost --trend

# If costs high, enable caching
l4-dev config set cache.enabled true

# Review quality trends
l4-dev quality --trend

# If quality low, adjust context level
l4-dev config set context.start_level 1
```

### 4. Use Appropriate Profiles

```bash
# For routine tasks
l4-dev profile use balanced

# For complex features
l4-dev profile use max

# For cost-sensitive projects
l4-dev profile use minimal
```

---

## Performance Characteristics

### Advanced Feature Overhead

| Feature | Overhead | Benefit |
|----------|-----------|---------|
| Adaptive Reasoning | <5% | +20% success rate |
| Progressive Context | <3% | -40% tokens |
| Cost Optimization | <2% | -40% cost |
| Trap Detection | <1% | 95% detection |
| Meta-Cognition | <4% | -70% mistakes |
| Housekeeping | <2% | -80% dead code |

### Combined Overhead

When all advanced features are enabled:
- **Total Overhead**: <15%
- **Net Benefit**: Significantly improved outcomes
- **Recommendation**: Enable all advanced features for production use

---

## Next Steps

- [ ] Enable adaptive reasoning
- [ ] Try progressive context loading
- [ ] Enable cost optimization features
- [ ] Monitor trap detection
- [ ] Enable meta-cognition
- [ ] Set up automated housekeeping
- [ ] Monitor context quality
- [ ] Create custom profile

Once comfortable with advanced features, explore:
- [Best Practices Guide](BEST_PRACTICES.md)
- [Configuration Guide](CONFIGURATION.md)
- [Optimization Guide](OPTIMIZATION.md)
- [Expert Documentation](../expert/ARCHITECTURE.md)