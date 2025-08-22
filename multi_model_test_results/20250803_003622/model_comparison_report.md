# Multi-Model Comparison Report

Generated: 2025-08-03T00:37:37.731433

## Test Configuration

- Models: gpt-4o-mini, claude37_sonnet
- Task Types: simple_task
- Prompt Types: baseline, optimal
- Instances per Type: 1

## Model Performance Comparison

| Model | Success Rate | Full/Partial | Avg Score | Phase2 Score | Quality Score | Baseline | Optimal | Improvement |
|-------|--------------|-------------|-----------|--------------|---------------|----------|---------|-------------|
| gpt-4o-mini | 100.0% | 50%/50% | 0.813 | 0.813 | 0.734 | 0.750 | 0.876 | +0.126 |
| claude37_sonnet | 100.0% | 50%/50% | 0.781 | 0.781 | 0.825 | 0.841 | 0.722 | -0.119 |

## Performance by Task Type


### simple_task

| Model | Baseline Success | Optimal Success | Score Improvement |
|-------|------------------|-----------------|-------------------|
| gpt-4o-mini | 100% | 100% | +0.126 |
| claude37_sonnet | 100% | 100% | -0.119 |

## Error Analysis


## Phase 2 Scoring Analysis

| Model | Phase2 Score | Quality Score | Workflow Score | Execution Time | Tool Success Rate |
|-------|--------------|---------------|----------------|----------------|-------------------|
| gpt-4o-mini | 0.813 | 0.734 | 0.813 | 6.8s | 73.2% |
| claude37_sonnet | 0.781 | 0.825 | 0.781 | 29.5s | 87.5% |

## Recommendations

- Best overall model (Phase2): **gpt-4o-mini** (Full Success: 50.0%, Phase2 Score: 0.813)

### Best Models by Task Type:

- simple_task: gpt-4o-mini (Success: 100%, Score: 0.813)
