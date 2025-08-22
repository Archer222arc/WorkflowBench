# Multi-Model Comparison Report

Generated: 2025-08-03T00:53:51.098953

## Test Configuration

- Models: gpt-4o-mini
- Task Types: simple_task
- Prompt Types: baseline, optimal
- Instances per Type: 2

## Model Performance Comparison

| Model | Success Rate | Full/Partial | Avg Score | Phase2 Score | Quality Score | Baseline | Optimal | Improvement |
|-------|--------------|-------------|-----------|--------------|---------------|----------|---------|-------------|
| gpt-4o-mini | 100.0% | 50%/50% | 0.828 | 0.828 | 0.762 | 0.883 | 0.772 | -0.111 |

## Performance by Task Type


### simple_task

| Model | Baseline Success | Optimal Success | Score Improvement |
|-------|------------------|-----------------|-------------------|
| gpt-4o-mini | 100% | 100% | -0.111 |

## Error Analysis

### Error Type Distribution

| Error Type | Rate |
|------------|------|
| Tool Selection | 0.0% |
| Parameter Config | 0.0% |
| Sequence Order | 0.0% |
| Dependency | 0.0% |

## Phase 2 Scoring Analysis

| Model | Phase2 Score | Quality Score | Workflow Score | Execution Time | Tool Success Rate |
|-------|--------------|---------------|----------------|----------------|-------------------|
| gpt-4o-mini | 0.828 | 0.762 | 0.828 | 4.9s | 76.2% |

## Recommendations

- Best overall model (Phase2): **gpt-4o-mini** (Full Success: 50.0%, Phase2 Score: 0.828)

### Best Models by Task Type:

- simple_task: gpt-4o-mini (Success: 100%, Score: 0.828)
