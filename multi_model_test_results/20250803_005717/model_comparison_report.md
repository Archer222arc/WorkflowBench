# Multi-Model Comparison Report

Generated: 2025-08-03T00:57:24.596537

## Test Configuration

- Models: gpt-4o-mini
- Task Types: simple_task
- Prompt Types: baseline
- Instances per Type: 1

## Model Performance Comparison

| Model | Success Rate | Full/Partial | Avg Score | Phase2 Score | Quality Score | Baseline | Optimal | Improvement |
|-------|--------------|-------------|-----------|--------------|---------------|----------|---------|-------------|
| gpt-4o-mini | 100.0% | 0%/100% | 0.932 | 0.932 | 0.881 | 0.932 | 0.000 | -0.932 |

## Comprehensive Evaluation Metrics

- **Weighted Success Score**: 0.500
- **Average Execution Steps**: 3.0
- **Tool Coverage Rate**: 10.0%
- **Tool Selection Accuracy**: 100.0%
- **Sequence Correctness Rate**: 100.0%
- **Prompt Sensitivity Index**: 0.000

### Task Difficulty Breakdown

| Difficulty | Success Rate |
|------------|--------------|
| Simple | 100.0% |
| Medium | 0.0% |
| Hard | 0.0% |

## Performance by Task Type


### simple_task

| Model | Baseline Success | Optimal Success | Score Improvement |
|-------|------------------|-----------------|-------------------|
| gpt-4o-mini | 100% | 0% | -0.932 |

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
| gpt-4o-mini | 0.932 | 0.881 | 0.932 | 4.7s | 100.0% |

## Recommendations

- Best overall model (Phase2): **gpt-4o-mini** (Full Success: 0.0%, Phase2 Score: 0.932)

### Best Models by Task Type:

- simple_task: gpt-4o-mini (Success: 100%, Score: 0.932)
