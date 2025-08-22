# Workflow Quality Test Report

Generated: 2025-07-15T02:13:59.740494

## Executive Summary

- Total tests: 20055
- Baseline success rate: 88.81%
- Optimal success rate: 93.54%
- CoT success rate: 90.19%
- Success rate improvement: +4.73%
- Score improvement: +0.020

## Overall Performance Analysis

### Performance by Prompt Strategy

| Prompt Type | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |
|-------------|-------------|--------------------|--------------|-----------------|------------|
| Baseline | 6685 | 86.70% | 30.58% | 56.13% | 0.770 |
| Optimal | 6685 | 91.41% | 39.69% | 51.73% | 0.789 |
| Cot | 6685 | 85.53% | 33.69% | 51.85% | 0.761 |

### Performance by Flawed Severity

| Severity Level | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |
|----------------|-------------|--------------------|--------------|-----------------|------------|
| Light | 4305 | 90.57% | 27.97% | 62.60% | 0.790 |
| Medium | 4305 | 86.13% | 22.72% | 63.41% | 0.771 |
| Severe | 4305 | 86.92% | 25.60% | 61.32% | 0.782 |

### Performance by Flaw Type

| Flaw Type | Total Tests | Total Success Rate | Full Success | Partial Success | Avg Score |
|-----------|-------------|--------------------|--------------|-----------------|------------|
| Missing Middle | 4305 | 86.92% | 25.60% | 61.32% | 0.782 |
| Order Flaw Swap | 4305 | 90.57% | 27.97% | 62.60% | 0.790 |
| Semantic Mismatch | 4305 | 86.13% | 22.72% | 63.41% | 0.771 |

## Detailed Results by Task Type

### api_integration

#### Basic Performance

| Metric | Baseline | Optimal | CoT |
|--------|----------|---------|-----|
| Success Rate | 89.71% | 92.97% | 80.77% |
| Full Success | 24.15% | 34.44% | 15.91% |
| Partial Success | 65.56% | 58.53% | 64.86% |
| Avg Score | 0.714 | 0.728 | 0.664 |
| Test Count | 1565 | 1565 | 1565 |

#### Flawed Workflow Performance

| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |
|----------|-------------------|--------------|-----------------|-----------|-------|
| Light | 91.58% | 25.17% | 66.41% | 0.712 | 1021 |
| Medium | 79.04% | 8.81% | 70.23% | 0.662 | 1021 |
| Severe | 80.51% | 15.18% | 65.33% | 0.686 | 1021 |

### basic_task

#### Basic Performance

| Metric | Baseline | Optimal | CoT |
|--------|----------|---------|-----|
| Success Rate | 96.55% | 96.42% | 93.10% |
| Full Success | 66.77% | 66.45% | 71.82% |
| Partial Success | 29.78% | 29.97% | 21.28% |
| Avg Score | 0.813 | 0.819 | 0.791 |
| Test Count | 1565 | 1565 | 1565 |

#### Flawed Workflow Performance

| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |
|----------|-------------------|--------------|-----------------|-----------|-------|
| Light | 95.20% | 61.70% | 33.50% | 0.814 | 1021 |
| Medium | 94.61% | 60.92% | 33.69% | 0.814 | 1021 |
| Severe | 96.77% | 62.98% | 33.79% | 0.820 | 1021 |

### data_pipeline

#### Basic Performance

| Metric | Baseline | Optimal | CoT |
|--------|----------|---------|-----|
| Success Rate | 81.47% | 90.61% | 84.41% |
| Full Success | 20.00% | 32.78% | 22.94% |
| Partial Success | 61.47% | 57.83% | 61.47% |
| Avg Score | 0.772 | 0.805 | 0.791 |
| Test Count | 1565 | 1565 | 1565 |

#### Flawed Workflow Performance

| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |
|----------|-------------------|--------------|-----------------|-----------|-------|
| Light | 90.70% | 13.71% | 76.98% | 0.824 | 1021 |
| Medium | 88.05% | 12.63% | 75.42% | 0.809 | 1021 |
| Severe | 87.56% | 13.52% | 74.05% | 0.811 | 1021 |

### multi_stage_pipeline

#### Basic Performance

| Metric | Baseline | Optimal | CoT |
|--------|----------|---------|-----|
| Success Rate | 74.87% | 82.79% | 79.55% |
| Full Success | 8.53% | 16.08% | 10.49% |
| Partial Success | 66.34% | 66.72% | 69.06% |
| Avg Score | 0.777 | 0.798 | 0.792 |
| Test Count | 1325 | 1325 | 1325 |

#### Flawed Workflow Performance

| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |
|----------|-------------------|--------------|-----------------|-----------|-------|
| Light | 81.97% | 5.72% | 76.25% | 0.805 | 821 |
| Medium | 78.93% | 3.78% | 75.15% | 0.793 | 821 |
| Severe | 78.68% | 4.26% | 74.42% | 0.799 | 821 |

### simple_task

#### Basic Performance

| Metric | Baseline | Optimal | CoT |
|--------|----------|---------|-----|
| Success Rate | 92.33% | 95.04% | 93.53% |
| Full Success | 29.32% | 52.33% | 57.29% |
| Partial Success | 63.01% | 42.71% | 36.24% |
| Avg Score | 0.777 | 0.810 | 0.784 |
| Test Count | 665 | 665 | 665 |

#### Flawed Workflow Performance

| Severity | Total Success Rate | Full Success | Partial Success | Avg Score | Count |
|----------|-------------------|--------------|-----------------|-----------|-------|
| Light | 93.35% | 30.88% | 62.47% | 0.811 | 421 |
| Medium | 92.16% | 25.18% | 66.98% | 0.797 | 421 |
| Severe | 93.11% | 31.12% | 62.00% | 0.813 | 421 |

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
| Phase2 Score | 0.776 | 0.151 | 0.121 | 0.965 |
| Quality Score | 0.714 | 0.151 | 0.049 | 0.883 |
| Workflow Score | 0.801 | 0.092 | 0.252 | 0.915 |

---
*Report generated at 2025-07-15T02:13:59.740494*
