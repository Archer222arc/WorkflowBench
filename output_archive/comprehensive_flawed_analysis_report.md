# Comprehensive Flawed Workflow Analysis Report

Generated: 2025-06-24 08:45:24

## Data Source

This report is based on the raw output from workflow_quality_test.py
All success rates and metrics are directly from the test execution results.

### Data Validation

✅ All data points have required fields

## Dataset Overview

- Total tests conducted: 27000
- Severities tested: light, medium, severe
- Flaw types: 13
- Task types: api, basic, data, multi, simple

## Scoring Standards

**Note**: All scores shown are from the test execution, not recalculated.
The test code uses the following evaluation:
- Task requirements from generated task instances
- Tool dependencies from tool_task_generator
- Objective scoring based on tool coverage and dependency satisfaction

## Scoring Standards

**Composite Score** = 0.7×Success Rate + 0.3×Tool Accuracy

## Key Findings

### Overall Performance

| Prompt Type | Mean Success Rate | Std Dev | Total Tests |
|-------------|-------------------|---------|-------------|
| Baseline (No MDP) | 11.1% | 22.2% | 9000 |
| Optimal (With MDP) | 15.8% | 21.0% | 9000 |
| Flawed (All) | 0.6% | 2.1% | 9000 |

### Performance by Severity


**Light Severity:**

| Prompt Type | Mean Success Rate | Sample Size |
|-------------|-------------------|-------------|
| Baseline | 11.8% | 60 |
| Optimal | 16.4% | 60 |
| Flawed | 1.2% | 60 |

**Medium Severity:**

| Prompt Type | Mean Success Rate | Sample Size |
|-------------|-------------------|-------------|
| Baseline | 10.7% | 60 |
| Optimal | 16.6% | 60 |
| Flawed | 0.2% | 60 |

**Severe Severity:**

| Prompt Type | Mean Success Rate | Sample Size |
|-------------|-------------------|-------------|
| Baseline | 10.9% | 60 |
| Optimal | 14.2% | 60 |
| Flawed | 0.3% | 60 |

## Data Quality Check

### Data Balance

✅ Data is reasonably balanced across severities.

## Recommendations

1. MDP guidance shows 42% improvement over baseline.
