#!/usr/bin/env python3
"""
增强成功率报告 - 确保所有表格都包含完整的成功率指标
"""

def enhance_success_rate_in_tables():
    """
    确保以下表格都包含完整的成功率指标：
    1. 4.1.2 任务类型分解性能表
    2. 4.2.1 提示优化敏感性表  
    3. 4.3.1 缺陷工作流鲁棒性表
    4. 4.3.2 工具可靠性敏感性表
    
    每个都应该包含：
    - Total Success Rate = Full + Partial
    - Full Success Rate
    - Partial Success Rate
    """
    
    # 示例：增强后的任务类型分解性能表
    enhanced_task_type_table = """
### 4.1.2 任务类型分解性能表（增强版）

| 模型名称 | 任务类型 | 总成功率 | 完全成功率 | 部分成功率 |
|---------|---------|----------|-----------|-----------|
| GPT-4o-mini | 简单任务 | 95.0% | 80.0% | 15.0% |
| GPT-4o-mini | 数据管道 | 85.0% | 65.0% | 20.0% |
| GPT-4o-mini | API集成 | 75.0% | 50.0% | 25.0% |
| GPT-4o-mini | 多阶段管道 | 70.0% | 45.0% | 25.0% |
"""

    # 示例：增强后的提示优化敏感性表
    enhanced_prompt_table = """
### 4.2.1 提示优化敏感性表（增强版）

| 模型名称 | 提示类型 | 总成功率 | 完全成功率 | 部分成功率 | 平均分数 |
|---------|---------|----------|-----------|-----------|---------|
| GPT-4o-mini | Baseline | 80.0% | 60.0% | 20.0% | 0.75 |
| GPT-4o-mini | Optimal | 85.0% | 70.0% | 15.0% | 0.82 |
| GPT-4o-mini | CoT | 82.5% | 65.0% | 17.5% | 0.78 |
| **敏感性指数** | - | 0.025 | 0.050 | 0.025 | 0.035 |
"""

    # 示例：增强后的缺陷工作流鲁棒性表
    enhanced_robustness_table = """
### 4.3.1 缺陷工作流鲁棒性表（增强版）

| 模型名称 | 缺陷类型 | 总成功率 | 完全成功率 | 部分成功率 |
|---------|---------|----------|-----------|-----------|
| GPT-4o-mini | 顺序错误 | 75.0% | 50.0% | 25.0% |
| GPT-4o-mini | 工具误用 | 40.0% | 20.0% | 20.0% |
| GPT-4o-mini | 参数错误 | 80.0% | 60.0% | 20.0% |
| GPT-4o-mini | 缺失步骤 | 65.0% | 40.0% | 25.0% |
| GPT-4o-mini | 冗余操作 | 85.0% | 70.0% | 15.0% |
| GPT-4o-mini | 逻辑不连续 | 60.0% | 35.0% | 25.0% |
| GPT-4o-mini | 语义漂移 | 55.0% | 30.0% | 25.0% |
"""

    # 示例：增强后的工具可靠性敏感性表
    enhanced_reliability_table = """
### 4.3.2 工具可靠性敏感性表（增强版）

| 模型名称 | 工具成功率 | 任务总成功率 | 完全成功率 | 部分成功率 |
|---------|-----------|-------------|-----------|-----------|
| GPT-4o-mini | 90% | 85.0% | 70.0% | 15.0% |
| GPT-4o-mini | 80% | 72.5% | 55.0% | 17.5% |
| GPT-4o-mini | 70% | 58.0% | 40.0% | 18.0% |
| GPT-4o-mini | 60% | 42.5% | 25.0% | 17.5% |
"""

    return {
        'task_type_table': enhanced_task_type_table,
        'prompt_table': enhanced_prompt_table,
        'robustness_table': enhanced_robustness_table,
        'reliability_table': enhanced_reliability_table
    }


def get_report_generation_code_patch():
    """
    获取需要添加到报告生成代码中的补丁
    """
    
    patch = '''
# 在生成任务类型分解表时（4.1.2）
def generate_task_type_table_with_full_rates(results, models, task_types):
    """生成包含完整成功率的任务类型分解表"""
    table_lines = []
    table_lines.append("| 模型名称 | 任务类型 | 总成功率 | 完全成功率 | 部分成功率 |")
    table_lines.append("|---------|---------|----------|-----------|-----------|")
    
    for model in models:
        for task_type in task_types:
            task_results = [r for r in results 
                          if getattr(r, 'model', '') == model 
                          and r.task_type == task_type]
            if task_results:
                total_count = len(task_results)
                full_success = sum(1 for r in task_results 
                                 if getattr(r, 'success_level', '') == 'full_success')
                partial_success = sum(1 for r in task_results 
                                    if getattr(r, 'success_level', '') == 'partial_success')
                
                total_rate = (full_success + partial_success) / total_count * 100
                full_rate = full_success / total_count * 100
                partial_rate = partial_success / total_count * 100
                
                table_lines.append(f"| {model} | {task_type} | "
                                 f"{total_rate:.1f}% | {full_rate:.1f}% | {partial_rate:.1f}% |")
    
    return "\\n".join(table_lines)

# 在生成缺陷工作流表时（4.3.1）
def generate_robustness_table_with_full_rates(results, models, flaw_types):
    """生成包含完整成功率的缺陷工作流表"""
    table_lines = []
    table_lines.append("| 模型名称 | 缺陷类型 | 总成功率 | 完全成功率 | 部分成功率 |")
    table_lines.append("|---------|---------|----------|-----------|-----------|")
    
    for model in models:
        for flaw_type in flaw_types:
            flaw_results = [r for r in results 
                          if getattr(r, 'model', '') == model 
                          and getattr(r, 'flaw_type', '') == flaw_type]
            if flaw_results:
                total_count = len(flaw_results)
                full_success = sum(1 for r in flaw_results 
                                 if getattr(r, 'success_level', '') == 'full_success')
                partial_success = sum(1 for r in flaw_results 
                                    if getattr(r, 'success_level', '') == 'partial_success')
                
                total_rate = (full_success + partial_success) / total_count * 100
                full_rate = full_success / total_count * 100
                partial_rate = partial_success / total_count * 100
                
                table_lines.append(f"| {model} | {flaw_type} | "
                                 f"{total_rate:.1f}% | {full_rate:.1f}% | {partial_rate:.1f}% |")
    
    return "\\n".join(table_lines)
'''
    
    return patch


if __name__ == "__main__":
    print("="*60)
    print("成功率报告增强方案")
    print("="*60)
    
    print("\n目标：确保所有表格都包含三个成功率指标")
    print("- Total Success Rate (总成功率) = Full + Partial")
    print("- Full Success Rate (完全成功率)")
    print("- Partial Success Rate (部分成功率)")
    
    print("\n需要增强的表格：")
    print("1. 4.1.2 任务类型分解性能表")
    print("2. 4.2.1 提示优化敏感性表")
    print("3. 4.3.1 缺陷工作流鲁棒性表")
    print("4. 4.3.2 工具可靠性敏感性表")
    
    print("\n示例增强后的表格格式：")
    print("-"*60)
    
    enhanced_tables = enhance_success_rate_in_tables()
    
    print(enhanced_tables['task_type_table'])
    print("\n" + "-"*60)
    print(enhanced_tables['robustness_table'])
    
    print("\n实现建议：")
    print("1. 修改 multi_model_batch_tester_v2.py 中的报告生成部分")
    print("2. 确保每个表格都计算并显示三个成功率")
    print("3. 在汇总时也要分别统计 full 和 partial")
    print("4. 可以添加注释说明：总成功率 = 完全成功率 + 部分成功率")