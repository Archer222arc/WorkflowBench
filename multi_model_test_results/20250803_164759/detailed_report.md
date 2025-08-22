# Workflow Quality Test Report

Generated: 2025-08-03T16:49:44.102234

## Executive Summary

- Total tests: 18
- Baseline success rate: 50.00%
- Optimal success rate: 100.00%
- CoT success rate: 0.00%
- Success rate improvement: +50.00%
- Score improvement: +0.122

## Overall Performance Analysis

### Performance by Prompt Strategy

| Prompt Type | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |
|-------------|-------------|--------------------|--------------|-----------------|------------|
| Baseline | 2 | 50.00% | 0.00% | 50.00% | 0.665 |
| Optimal | 2 | 100.00% | 0.00% | 100.00% | 0.788 |

### Performance by Flawed Severity

| Severity Level | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |
|----------------|-------------|--------------------|--------------|-----------------|------------|
| Severe | 14 | 92.86% | 21.43% | 71.43% | 0.808 |

### Performance by Flaw Type

| Flaw Type | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |
|-----------|-------------|--------------------|--------------|-----------------|------------|
| Logical Inconsistency | 2 | 100.00% | 50.00% | 50.00% | 0.839 |
| Missing Step | 2 | 100.00% | 0.00% | 100.00% | 0.819 |
| Parameter Error | 2 | 100.00% | 0.00% | 100.00% | 0.814 |
| Redundant Operations | 2 | 100.00% | 50.00% | 50.00% | 0.849 |
| Semantic Drift | 2 | 50.00% | 0.00% | 50.00% | 0.631 |
| Sequence Disorder | 2 | 100.00% | 0.00% | 100.00% | 0.863 |
| Tool Misuse | 2 | 100.00% | 50.00% | 50.00% | 0.840 |

## Detailed Results by Task Type

### data_pipeline

#### Basic Performance

| Metric | Baseline | Optimal | CoT |
|--------|----------|---------|-----|
| Success Rate | 0.00% | 100.00% | 0.00% |
| Full Success | 0.00% | 0.00% | 0.00% |
| Partial Success | 0.00% | 100.00% | 0.00% |
| Avg Score | 0.508 | 0.799 | 0.000 |
| Test Count | 1 | 1 | 0 |

#### Flawed Workflow Performance

| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |
|----------|-------------------|--------------|-----------------|-----------|-------|
| Severe | 100.00% | 0.00% | 100.00% | 0.847 | 7 |

### simple_task

#### Basic Performance

| Metric | Baseline | Optimal | CoT |
|--------|----------|---------|-----|
| Success Rate | 100.00% | 100.00% | 0.00% |
| Full Success | 0.00% | 0.00% | 0.00% |
| Partial Success | 100.00% | 100.00% | 0.00% |
| Avg Score | 0.822 | 0.776 | 0.000 |
| Test Count | 1 | 1 | 0 |

#### Flawed Workflow Performance

| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |
|----------|-------------------|--------------|-----------------|-----------|-------|
| Severe | 85.71% | 42.86% | 42.86% | 0.769 | 7 |

## Flawed Workflow Detailed Analysis

### Performance by Flaw Type

| Flaw Type | Total | Success Rate | Avg Score | Light SR | Medium SR | Severe SR |
|-----------|--------|--------------|-----------|----------|-----------|------------|

### Severity Impact Analysis

#### Success Rate Trends by Severity


#### Recommendations


## Phase 2 Scoring Analysis

### Score Distribution

| Metric | Mean | Std Dev | Min | Max |
|--------|------|---------|-----|-----|
| Phase2 Score | 0.790 | 0.121 | 0.425 | 0.927 |
| Quality Score | 0.679 | 0.139 | 0.299 | 0.882 |
| Workflow Score | 0.792 | 0.066 | 0.670 | 0.909 |

---
*Report generated at 2025-08-03T16:49:44.102234*
