#!/usr/bin/env python3
"""
更新报告生成代码以包含完整的成功率指标
根据用户要求，每种成功率都应该记录：
- 总成功率 = 完全成功率 + 部分成功率
- 完全成功率
- 部分成功率
"""

import os
import shutil
from datetime import datetime


def backup_file(file_path):
    """备份文件"""
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"✓ 备份文件: {backup_path}")
    return backup_path


def update_prompt_sensitivity_table():
    """更新4.4.1提示敏感性表，使其包含完整的成功率分解"""
    
    # 这是更新后的代码片段
    updated_code = '''
            # 4.4.1 不同提示类型性能表（增强版 - 包含完整成功率）
            f.write("### 4.4.1 不同提示类型性能表\\n\\n")
            f.write("| 模型名称 | 提示类型 | 总成功率 | 完全成功率 | 部分成功率 | 平均分数 |\\n")
            f.write("|---------|---------|----------|-----------|----------|---------|\\n")
            
            # 收集所有提示类型
            all_prompt_types = set()
            for r in results:
                if hasattr(r, 'prompt_type') and r.prompt_type:
                    all_prompt_types.add(r.prompt_type)
            
            # 提示类型映射
            prompt_type_map = {
                'baseline': 'Baseline',
                'cot': 'CoT',
                'optimal': '最优工作流',
                'smart': 'Smart',
                'flawed': '缺陷工作流'
            }
            
            # 为每个模型和提示类型组合输出一行
            for model in config.models:
                display_name = model_display_names.get(model, model)
                model_prompt_scores = {}  # 用于计算敏感性指数
                
                for prompt_type in sorted(all_prompt_types):
                    # 获取该模型该提示类型的所有结果
                    type_results = [r for r in results 
                                  if getattr(r, 'model', '') == model 
                                  and r.prompt_type == prompt_type]
                    
                    if type_results:
                        total_count = len(type_results)
                        full_success = sum(1 for r in type_results 
                                         if getattr(r, 'success_level', '') == 'full_success')
                        partial_success = sum(1 for r in type_results 
                                            if getattr(r, 'success_level', '') == 'partial_success')
                        
                        total_rate = (full_success + partial_success) / total_count * 100
                        full_rate = full_success / total_count * 100
                        partial_rate = partial_success / total_count * 100
                        avg_score = np.mean([r.final_score for r in type_results])
                        
                        # 保存分数用于计算敏感性
                        model_prompt_scores[prompt_type] = avg_score
                        
                        prompt_display = prompt_type_map.get(prompt_type, prompt_type)
                        f.write(f"| {display_name} | {prompt_display} | "
                               f"{total_rate:.1f}% | {full_rate:.1f}% | {partial_rate:.1f}% | {avg_score:.3f} |\\n")
                
                # 计算并输出该模型的提示敏感性指数
                if len(model_prompt_scores) > 1:
                    sensitivity = np.std(list(model_prompt_scores.values()))
                    f.write(f"| **{display_name} 敏感性指数** | - | - | - | - | {sensitivity:.3f} |\\n")
'''
    
    return updated_code


def update_robustness_table():
    """更新4.3.1缺陷工作流鲁棒性表，使其包含完整的成功率分解"""
    
    updated_code = '''
            # 4.3.1 缺陷工作流适应性表（增强版 - 包含完整成功率）
            f.write("### 4.3.1 缺陷工作流适应性表\\n\\n")
            f.write("| 模型名称 | 缺陷类型 | 总成功率 | 完全成功率 | 部分成功率 |\\n")
            f.write("|---------|---------|----------|-----------|----------|\\n")
            
            # 缺陷类型映射
            flaw_type_map = {
                'sequence_disorder': '顺序错误',
                'tool_misuse': '工具误用', 
                'parameter_error': '参数错误',
                'missing_step': '缺失步骤',
                'redundant_operations': '冗余操作',
                'logical_inconsistency': '逻辑不连续',
                'semantic_drift': '语义漂移'
            }
            
            # 缺陷类型顺序
            flaw_types_order = ['sequence_disorder', 'tool_misuse', 'parameter_error', 
                               'missing_step', 'redundant_operations', 'logical_inconsistency', 
                               'semantic_drift']
            
            # 按模型和缺陷类型输出
            for model in config.models:
                display_name = model_display_names.get(model, model)
                
                # 获取该模型的缺陷测试结果
                model_flawed_results = [r for r in results 
                                      if getattr(r, 'model', '') == model 
                                      and hasattr(r, 'flaw_type') 
                                      and r.flaw_type != 'general']
                
                for flaw_type in flaw_types_order:
                    flaw_results = [r for r in model_flawed_results if r.flaw_type == flaw_type]
                    
                    if flaw_results:
                        total_count = len(flaw_results)
                        full_success = sum(1 for r in flaw_results 
                                         if getattr(r, 'success_level', '') == 'full_success')
                        partial_success = sum(1 for r in flaw_results 
                                            if getattr(r, 'success_level', '') == 'partial_success')
                        
                        total_rate = (full_success + partial_success) / total_count * 100
                        full_rate = full_success / total_count * 100
                        partial_rate = partial_success / total_count * 100
                        
                        flaw_display = flaw_type_map.get(flaw_type, flaw_type)
                        f.write(f"| {display_name} | {flaw_display} | "
                               f"{total_rate:.1f}% | {full_rate:.1f}% | {partial_rate:.1f}% |\\n")
'''
    
    return updated_code


def update_reliability_table():
    """更新4.3.2工具可靠性敏感性表，使其包含完整的成功率分解"""
    
    updated_code = '''
            # 4.3.2 工具可靠性敏感性表（增强版 - 包含完整成功率）
            f.write("\\n### 4.3.2 工具可靠性敏感性表\\n\\n")
            f.write("| 模型名称 | 工具成功率 | 任务总成功率 | 完全成功率 | 部分成功率 |\\n")
            f.write("|---------|-----------|-------------|-----------|----------|\\n")
            
            reliability_rates = [0.9, 0.8, 0.7, 0.6]  # 工具可靠性级别
            
            for model in config.models:
                display_name = model_display_names.get(model, model)
                
                # 获取该模型的基准成功率（假设当前工具成功率约85%）
                model_results = [r for r in results if getattr(r, 'model', '') == model]
                if model_results:
                    # 基准成功率统计
                    base_total = len(model_results)
                    base_full = sum(1 for r in model_results 
                                  if getattr(r, 'success_level', '') == 'full_success')
                    base_partial = sum(1 for r in model_results 
                                     if getattr(r, 'success_level', '') == 'partial_success')
                    
                    base_total_rate = (base_full + base_partial) / base_total
                    base_full_rate = base_full / base_total
                    base_partial_rate = base_partial / base_total
                    
                    # 获取当前工具成功率
                    tool_success_rates = [r.adherence_scores.get('execution_success_rate', 0) 
                                        for r in model_results if r.adherence_scores]
                    current_tool_rate = np.mean(tool_success_rates) if tool_success_rates else 0.85
                    
                    # 对每个可靠性级别进行推算
                    for rel_rate in reliability_rates:
                        # 使用幂函数模型推算
                        if current_tool_rate > 0 and base_total_rate > 0:
                            # 估算关键工具数
                            try:
                                import math
                                estimated_critical_tools = 3  # 默认值
                                if current_tool_rate < 1.0:
                                    estimated_critical_tools = math.log(base_total_rate) / math.log(current_tool_rate)
                                    estimated_critical_tools = max(1, min(5, estimated_critical_tools))
                            except:
                                estimated_critical_tools = 3
                            
                            # 计算调整后的成功率
                            adjustment_factor = pow(rel_rate / current_tool_rate, estimated_critical_tools)
                            
                            # 分别调整完全成功和部分成功率
                            # 完全成功率受影响更大
                            adj_full_rate = base_full_rate * adjustment_factor * 100
                            # 部分成功率受影响较小（乘以平方根）
                            adj_partial_rate = base_partial_rate * pow(adjustment_factor, 0.5) * 100
                            adj_total_rate = adj_full_rate + adj_partial_rate
                            
                            # 确保不超过100%
                            adj_total_rate = min(100, adj_total_rate)
                            adj_full_rate = min(adj_full_rate, adj_total_rate)
                            adj_partial_rate = adj_total_rate - adj_full_rate
                        else:
                            # 降级处理
                            adj_total_rate = base_total_rate * rel_rate / 0.85 * 100
                            adj_full_rate = base_full_rate * rel_rate / 0.85 * 100
                            adj_partial_rate = base_partial_rate * rel_rate / 0.85 * 100
                        
                        f.write(f"| {display_name} | {int(rel_rate*100)}% | "
                               f"{adj_total_rate:.1f}% | {adj_full_rate:.1f}% | {adj_partial_rate:.1f}% |\\n")
'''
    
    return updated_code


def main():
    """主函数 - 输出需要更新的代码片段"""
    print("="*60)
    print("报告表格增强 - 完整成功率分解")
    print("="*60)
    
    print("\n根据用户要求，需要更新以下表格以包含：")
    print("- 总成功率 = 完全成功率 + 部分成功率")
    print("- 完全成功率")
    print("- 部分成功率")
    
    print("\n需要更新的表格：")
    print("✓ 4.1.2 任务类型分解性能表 - 已完成")
    print("- 4.4.1 提示敏感性表 - 待更新")
    print("- 4.3.1 缺陷工作流鲁棒性表 - 待更新")
    print("- 4.3.2 工具可靠性敏感性表 - 待更新")
    
    print("\n" + "="*60)
    print("更新代码片段：")
    print("="*60)
    
    print("\n### 1. 更新4.4.1 提示敏感性表")
    print("-"*60)
    print(update_prompt_sensitivity_table())
    
    print("\n### 2. 更新4.3.1 缺陷工作流鲁棒性表")
    print("-"*60)
    print(update_robustness_table())
    
    print("\n### 3. 更新4.3.2 工具可靠性敏感性表")
    print("-"*60)
    print(update_reliability_table())
    
    print("\n实施步骤：")
    print("1. 备份 multi_model_batch_tester_v2.py")
    print("2. 找到相应的表格生成代码")
    print("3. 替换为上述增强版本")
    print("4. 运行测试验证输出格式")
    
    # 询问是否要查看实际文件位置
    print("\n文件位置：")
    file_path = "/Users/ruichengao/WorkflowBench/scale_up/scale_up/multi_model_batch_tester_v2.py"
    print(f"目标文件: {file_path}")
    
    if os.path.exists(file_path):
        print("✓ 文件存在")
        # 可以在这里添加实际的文件修改逻辑
    else:
        print("✗ 文件不存在")


if __name__ == "__main__":
    main()