# Multi-Model Comparison Report

Generated: 2025-08-03T00:32:35.290644

## Test Configuration

- Models: gpt-4o-mini, claude37_sonnet
- Task Types: simple_task
- Prompt Types: baseline, optimal
- Instances per Type: 1

## Model Performance Comparison

| Model | Success Rate | Avg Score | Baseline Score | Optimal Score | Improvement |
|-------|--------------|-----------|----------------|---------------|-------------|
| gpt-4o-mini | 100.0% | 0.803 | 0.777 | 0.829 | +0.052 |
| claude37_sonnet | 100.0% | 0.854 | 0.905 | 0.803 | -0.102 |

## Performance by Task Type


### simple_task

| Model | Baseline Success | Optimal Success | Score Improvement |
|-------|------------------|-----------------|-------------------|
| gpt-4o-mini | 100% | 100% | +0.052 |
| claude37_sonnet | 100% | 100% | -0.102 |

## Error Analysis


## Recommendations

- Best overall model: **claude37_sonnet** (Success: 100.0%, Avg Score: 0.854)

### Best Models by Task Type:

- simple_task: claude37_sonnet (Success: 100%, Score: 0.854)
