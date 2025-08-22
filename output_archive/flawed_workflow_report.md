# Flawed Workflow Test Report

Generated: 2025-06-24 03:50:01

## Executive Summary


## Success Rate by Completion Threshold

This section shows how success rates vary under different task completion requirements.

### Overall Success Rates by Threshold

| Completion Requirement | Without MDP | With MDP | Improvement |
|----------------------|-------------|----------|-------------|
| Partial (50%+) | 0.0% | 0.0% | +0.0% |
| Basic (60%+) | 0.0% | 0.0% | +0.0% |
| Standard (70%+) ⭐ | 0.0% | 0.0% | +0.0% |
| High (80%+) | 0.0% | 0.0% | +0.0% |
| Very High (90%+) | 0.0% | 0.0% | +0.0% |
| Perfect (100%) | 0.0% | 0.0% | +0.0% |

*⭐ = Current default threshold*

### Success Rates by Task Type and Threshold


### Interpretation Guide

- **Partial (50%+)**: Task achieves at least half of the objectives
- **Basic (60%+)**: Most core objectives completed
- **Standard (70%+)**: Current evaluation threshold - good overall completion
- **High (80%+)**: Near-complete task execution
- **Very High (90%+)**: Only minor elements missing
- **Perfect (100%)**: All required tools executed successfully with correct dependencies

- **Task Types Tested**: 5
- **Severity Levels**: light, medium, severe
- **Total Flaw Types**: 180

### Overall Performance by Prompt Type

| Prompt Type | Total Tests | Success Rate |
|------------|-------------|-------------|
| Without MDP | 9000 | 11.1% |
| With MDP | 9000 | 15.7% |
| Flawed Optimal | 9000 | 0.6% |

### Performance by Severity Level


#### Light Severity

| Prompt Type | Success Rate | Total Tests |
|------------|--------------|-------------|
| Without MDP | 11.8% | 3000 |
| With MDP | 16.4% | 3000 |
| Flawed Optimal | 1.2% | 3000 |

#### Medium Severity

| Prompt Type | Success Rate | Total Tests |
|------------|--------------|-------------|
| Without MDP | 10.7% | 3000 |
| With MDP | 16.6% | 3000 |
| Flawed Optimal | 0.2% | 3000 |

#### Severe Severity

| Prompt Type | Success Rate | Total Tests |
|------------|--------------|-------------|
| Without MDP | 10.8% | 3000 |
| With MDP | 14.2% | 3000 |
| Flawed Optimal | 0.3% | 3000 |

## Detailed Results by Task Type


### Task: api_integration


#### Light Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (6.0%)
    - Without MDP: 2.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: Without MDP (2.0%)
    - Without MDP: 2.0%
    - With MDP: 2.0%
    - Flawed Optimal: 2.0%
- **param_wrong_type**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 4.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (6.0%)
    - Without MDP: 2.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: Without MDP (4.0%)
    - Without MDP: 4.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%

#### Medium Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: Without MDP (2.0%)
    - Without MDP: 2.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

#### Severe Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (6.0%)
    - Without MDP: 2.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 2.0%
- **param_wrong_type**
  - Best: With MDP (12.0%)
    - Without MDP: 0.0%
    - With MDP: 12.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

### Task: basic_task


#### Light Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (12.0%)
    - Without MDP: 0.0%
    - With MDP: 12.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (20.0%)
    - Without MDP: 0.0%
    - With MDP: 20.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (12.0%)
    - Without MDP: 0.0%
    - With MDP: 12.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (26.0%)
    - Without MDP: 0.0%
    - With MDP: 26.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (18.0%)
    - Without MDP: 0.0%
    - With MDP: 18.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (10.0%)
    - Without MDP: 0.0%
    - With MDP: 10.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
  - Best: With MDP (12.0%)
    - Without MDP: 0.0%
    - With MDP: 12.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (16.0%)
    - Without MDP: 0.0%
    - With MDP: 16.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (14.0%)
    - Without MDP: 0.0%
    - With MDP: 14.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: With MDP (22.0%)
    - Without MDP: 0.0%
    - With MDP: 22.0%
    - Flawed Optimal: 0.0%

#### Medium Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%

#### Severe Severity


**Logic Flaws:**

- **logic_break_format**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

### Task: data_pipeline


#### Light Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

#### Medium Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (24.0%)
    - Without MDP: 0.0%
    - With MDP: 24.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (24.0%)
    - Without MDP: 0.0%
    - With MDP: 24.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (22.0%)
    - Without MDP: 0.0%
    - With MDP: 22.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (26.0%)
    - Without MDP: 0.0%
    - With MDP: 26.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (22.0%)
    - Without MDP: 0.0%
    - With MDP: 22.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (16.0%)
    - Without MDP: 0.0%
    - With MDP: 16.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (24.0%)
    - Without MDP: 0.0%
    - With MDP: 24.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
  - Best: With MDP (16.0%)
    - Without MDP: 0.0%
    - With MDP: 16.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (12.0%)
    - Without MDP: 0.0%
    - With MDP: 12.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (20.0%)
    - Without MDP: 0.0%
    - With MDP: 20.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (20.0%)
    - Without MDP: 0.0%
    - With MDP: 20.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%

#### Severe Severity


**Logic Flaws:**

- **logic_break_format**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%

### Task: multi_stage_pipeline


#### Light Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: Without MDP (62.0%)
    - Without MDP: 62.0%
    - With MDP: 60.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: Without MDP (66.0%)
    - Without MDP: 66.0%
    - With MDP: 48.0%
    - Flawed Optimal: 2.0%

**Missing Flaws:**

- **missing_middle**
  - Best: Without MDP (62.0%)
    - Without MDP: 62.0%
    - With MDP: 52.0%
    - Flawed Optimal: 10.0%
- **missing_validation**
  - Best: With MDP (54.0%)
    - Without MDP: 52.0%
    - With MDP: 54.0%
    - Flawed Optimal: 16.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (66.0%)
    - Without MDP: 60.0%
    - With MDP: 66.0%
    - Flawed Optimal: 12.0%
- **order_flaw_dependency**
  - Best: Without MDP (56.0%)
    - Without MDP: 56.0%
    - With MDP: 56.0%
    - Flawed Optimal: 6.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (62.0%)
    - Without MDP: 52.0%
    - With MDP: 62.0%
    - Flawed Optimal: 12.0%
- **param_wrong_type**
  - Best: Without MDP (64.0%)
    - Without MDP: 64.0%
    - With MDP: 60.0%
    - Flawed Optimal: 6.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (56.0%)
    - Without MDP: 50.0%
    - With MDP: 56.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: Without MDP (60.0%)
    - Without MDP: 60.0%
    - With MDP: 60.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: Without MDP (62.0%)
    - Without MDP: 62.0%
    - With MDP: 50.0%
    - Flawed Optimal: 2.0%
- **tool_misuse_wrong_category**
  - Best: With MDP (58.0%)
    - Without MDP: 52.0%
    - With MDP: 58.0%
    - Flawed Optimal: 0.0%

#### Medium Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: Without MDP (56.0%)
    - Without MDP: 56.0%
    - With MDP: 54.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (58.0%)
    - Without MDP: 54.0%
    - With MDP: 58.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (56.0%)
    - Without MDP: 52.0%
    - With MDP: 56.0%
    - Flawed Optimal: 2.0%
- **missing_validation**
  - Best: With MDP (48.0%)
    - Without MDP: 46.0%
    - With MDP: 48.0%
    - Flawed Optimal: 2.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (70.0%)
    - Without MDP: 52.0%
    - With MDP: 70.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: Without MDP (54.0%)
    - Without MDP: 54.0%
    - With MDP: 36.0%
    - Flawed Optimal: 6.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (64.0%)
    - Without MDP: 48.0%
    - With MDP: 64.0%
    - Flawed Optimal: 2.0%
- **param_wrong_type**
  - Best: With MDP (64.0%)
    - Without MDP: 62.0%
    - With MDP: 64.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: Without MDP (52.0%)
    - Without MDP: 52.0%
    - With MDP: 52.0%
    - Flawed Optimal: 2.0%
- **redundant_unnecessary**
  - Best: Without MDP (60.0%)
    - Without MDP: 60.0%
    - With MDP: 56.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: Without MDP (48.0%)
    - Without MDP: 48.0%
    - With MDP: 46.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: Without MDP (56.0%)
    - Without MDP: 56.0%
    - With MDP: 48.0%
    - Flawed Optimal: 0.0%

#### Severe Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: Without MDP (44.0%)
    - Without MDP: 44.0%
    - With MDP: 44.0%
    - Flawed Optimal: 2.0%
- **logic_break_unrelated**
  - Best: Without MDP (56.0%)
    - Without MDP: 56.0%
    - With MDP: 48.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (58.0%)
    - Without MDP: 48.0%
    - With MDP: 58.0%
    - Flawed Optimal: 4.0%
- **missing_validation**
  - Best: With MDP (66.0%)
    - Without MDP: 52.0%
    - With MDP: 66.0%
    - Flawed Optimal: 2.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: Without MDP (56.0%)
    - Without MDP: 56.0%
    - With MDP: 54.0%
    - Flawed Optimal: 2.0%
- **order_flaw_dependency**
  - Best: With MDP (54.0%)
    - Without MDP: 52.0%
    - With MDP: 54.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (60.0%)
    - Without MDP: 46.0%
    - With MDP: 60.0%
    - Flawed Optimal: 4.0%
- **param_wrong_type**
  - Best: With MDP (72.0%)
    - Without MDP: 56.0%
    - With MDP: 72.0%
    - Flawed Optimal: 2.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: Without MDP (58.0%)
    - Without MDP: 58.0%
    - With MDP: 42.0%
    - Flawed Optimal: 2.0%
- **redundant_unnecessary**
  - Best: Without MDP (66.0%)
    - Without MDP: 66.0%
    - With MDP: 64.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (60.0%)
    - Without MDP: 56.0%
    - With MDP: 60.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: Without MDP (60.0%)
    - Without MDP: 60.0%
    - With MDP: 48.0%
    - Flawed Optimal: 0.0%

### Task: simple_task


#### Light Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (10.0%)
    - Without MDP: 0.0%
    - With MDP: 10.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
    - Without MDP: 0.0%
    - With MDP: 0.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%

#### Medium Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (12.0%)
    - Without MDP: 0.0%
    - With MDP: 12.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (10.0%)
    - Without MDP: 0.0%
    - With MDP: 10.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: With MDP (2.0%)
    - Without MDP: 0.0%
    - With MDP: 2.0%
    - Flawed Optimal: 0.0%

#### Severe Severity


**Logic Flaws:**

- **logic_break_format**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%
- **logic_break_unrelated**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Missing Flaws:**

- **missing_middle**
  - Best: With MDP (4.0%)
    - Without MDP: 0.0%
    - With MDP: 4.0%
    - Flawed Optimal: 0.0%
- **missing_validation**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Order Flaws:**

- **order_flaw_swap**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%
- **order_flaw_dependency**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%

**Param Flaws:**

- **param_missing**
  - Best: With MDP (14.0%)
    - Without MDP: 0.0%
    - With MDP: 14.0%
    - Flawed Optimal: 0.0%
- **param_wrong_type**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

**Redundant Flaws:**

- **redundant_duplicate**
  - Best: With MDP (8.0%)
    - Without MDP: 0.0%
    - With MDP: 8.0%
    - Flawed Optimal: 0.0%
- **redundant_unnecessary**
  - Best: With MDP (10.0%)
    - Without MDP: 0.0%
    - With MDP: 10.0%
    - Flawed Optimal: 0.0%

**Tool Flaws:**

- **tool_misuse_similar**
  - Best: With MDP (10.0%)
    - Without MDP: 0.0%
    - With MDP: 10.0%
    - Flawed Optimal: 0.0%
- **tool_misuse_wrong_category**
  - Best: With MDP (6.0%)
    - Without MDP: 0.0%
    - With MDP: 6.0%
    - Flawed Optimal: 0.0%

## Summary and Recommendations

- MDP-guided prompts show +4.6% improvement over baseline

### Key Findings:

1. **Robustness varies by flaw type**: Different prompts handle different flaws better
2. **Severity impact**: Performance generally decreases with increased severity
3. **Task-specific patterns**: Some tasks are more resilient to flaws

## Dependency Analysis

### Dependency Satisfaction by Task Type
| Task Type | Avg Dependency Score | Common Violations | Success Correlation |
|-----------|---------------------|-------------------|--------------------|

### Execution Order Analysis
| Prompt Type | Order Compliance | Avg Steps | Efficiency |
|-------------|-----------------|-----------|------------|
