# Multi-Model Comparison Report

Generated: 2025-08-03T01:03:35.326662

## Test Configuration

- Models: gpt-4o-mini
- Task Types: simple_task
- Prompt Types: baseline
- Instances per Type: 1

## Model Performance Comparison

| Model | Success Rate | Full/Partial | Avg Score | Phase2 Score | Quality Score | Baseline | Optimal | Improvement |
|-------|--------------|-------------|-----------|--------------|---------------|----------|---------|-------------|
| gpt-4o-mini | 100.0% | 0%/100% | 0.806 | 0.806 | 0.624 | 0.806 | N/A | N/A |

## Comprehensive Evaluation Metrics

- **Weighted Success Score**: 0.500
- **Average Execution Steps**: 9.0
- **Tool Coverage Rate**: 16.7%
- **Tool Selection Accuracy**: 100.0%
- **Sequence Correctness Rate**: 0.0%
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
| gpt-4o-mini | 100% | 0% | -0.806 |

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
| gpt-4o-mini | 0.806 | 0.624 | 0.806 | 9.7s | 66.7% |

## Recommendations

- Best overall model (Phase2): **gpt-4o-mini** (Full Success: 0.0%, Phase2 Score: 0.806)

### Best Models by Task Type:

- simple_task: gpt-4o-mini (Success: 100%, Score: 0.806)
