#\!/usr/bin/env python3
"""分析格式错误检测逻辑是否过于激进"""

import json
from pathlib import Path

def analyze_format_error_logic():
    """分析为什么这么多测试被分类为format error"""
    
    print("🔍 分析format error检测逻辑...")
    print("=" * 60)
    
    # 检查测试日志或数据，看实际的失败情况
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print("📊 当前格式错误检测逻辑分析:")
    print("  规则: 如果 tool_calls==[] 且 executed_tools==[]，则判定为format_error")
    print("")
    
    high_format_models = []
    for model, model_data in db['models'].items():
        for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
            for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                for diff, diff_data in rate_data.get('by_difficulty', {}).items():
                    for task, task_data in diff_data.get('by_task_type', {}).items():
                        total = task_data.get('total', 0)
                        success = task_data.get('success', 0)
                        format_errors = task_data.get('tool_call_format_errors', 0)
                        
                        if total > 0 and format_errors > 0:
                            failure_count = total - success
                            if failure_count > 0:
                                format_rate = format_errors / failure_count if failure_count > 0 else 0
                                if format_rate > 0.5:  # 超过50%的失败被归为格式错误
                                    high_format_models.append((model, format_rate, format_errors, failure_count, total))
    
    print("⚠️ 高格式错误率模型分析:")
    for model, rate, format_errs, failures, total in high_format_models:
        print(f"  {model}:")
        print(f"    总测试: {total}, 失败: {failures}, 格式错误: {format_errs}")
        print(f"    格式错误占失败的比例: {rate:.1%}")
        print(f"    问题分析: {'可能过度分类' if rate > 0.8 else '需要进一步分析'}")
        print("")
    
    print("🤔 可能的问题:")
    print("1. 检测逻辑过于激进:")
    print("   - 某些模型可能因为API问题、超时等原因没有执行工具调用")
    print("   - 但这不一定是Agent的格式错误，可能是环境问题")
    print("")
    print("2. 特别是qwen系列100%格式错误率很可疑:")
    print("   - 可能是API配置问题")
    print("   - 可能是模型响应格式与预期不符")
    print("   - 可能是系统环境问题")
    print("")
    print("3. DeepSeek-R1的高格式错误率:")
    print("   - 可能确实是格式问题")
    print("   - 但也可能是其他原因被误分类")
    
    print("\n💡 建议修复:")
    print("1. 增加更精确的格式错误检测条件")
    print("2. 区分'没有工具调用'的不同原因:")
    print("   - Agent确实不知道如何调用工具 (真正的格式错误)")
    print("   - API/环境问题导致工具调用失败 (应该归为other_errors)")
    print("   - 超时导致没有工具调用 (应该归为timeout_errors)")

if __name__ == "__main__":
    analyze_format_error_logic()
