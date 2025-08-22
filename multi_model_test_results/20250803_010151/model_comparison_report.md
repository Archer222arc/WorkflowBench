# Multi-Model Comparison Report

Generated: 2025-08-03T01:02:00.360038

## Test Configuration

- Models: gpt-4o-mini
- Task Types: simple_task
- Prompt Types: baseline
- Instances per Type: 1

## Model Performance Comparison

| Model | Success Rate | Full/Partial | Avg Score | Phase2 Score | Quality Score | Baseline | Optimal | Improvement |
|-------|--------------|-------------|-----------|--------------|---------------|----------|---------|-------------|
| gpt-4o-mini | 100.0% | 100%/0% | 0.841 | 0.841 | 0.881 | 0.841 | N/A | N/A |

## Comprehensive Evaluation Metrics

- **Weighted Success Score**: 1.000
- **Average Execution Steps**: 4.0
- **Tool Coverage Rate**: 13.3%
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
| gpt-4o-mini | 100% | 0% | -0.841 |

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
| gpt-4o-mini | 0.841 | 0.881 | 0.841 | 6.3s | 100.0% |

## Recommendations

- Best overall model (Phase2): **gpt-4o-mini** (Full Success: 100.0%, Phase2 Score: 0.841)

### Best Models by Task Type:

- simple_task: gpt-4o-mini (Success: 100%, Score: 0.841)
