# Multi-Model Comparison Report

Generated: 2025-08-03T01:03:55.419541

## Test Configuration

- Models: gpt-4o-mini
- Task Types: simple_task
- Prompt Types: baseline, optimal
- Instances per Type: 1

## Model Performance Comparison

| Model | Success Rate | Full/Partial | Avg Score | Phase2 Score | Quality Score | Baseline | Optimal | Improvement |
|-------|--------------|-------------|-----------|--------------|---------------|----------|---------|-------------|
| gpt-4o-mini | 100.0% | 50%/50% | 0.829 | 0.829 | 0.766 | 0.818 | 0.841 | +0.022 |

## Comprehensive Evaluation Metrics

- **Weighted Success Score**: 0.750
- **Average Execution Steps**: 5.5
- **Tool Coverage Rate**: 13.3%
- **Tool Selection Accuracy**: 100.0%
- **Sequence Correctness Rate**: 50.0%
- **Prompt Sensitivity Index**: 0.011

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
| gpt-4o-mini | 100% | 100% | +0.022 |

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
| gpt-4o-mini | 0.829 | 0.766 | 0.829 | 6.1s | 85.7% |

## Recommendations

- Best overall model (Phase2): **gpt-4o-mini** (Full Success: 50.0%, Phase2 Score: 0.829)

### Best Models by Task Type:

- simple_task: gpt-4o-mini (Success: 100%, Score: 0.829)
