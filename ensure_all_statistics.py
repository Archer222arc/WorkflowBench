#!/usr/bin/env python3
"""
确保所有测试都计算并保存完整的统计字段
"""

import json
from pathlib import Path
from datetime import datetime
import shutil

def analyze_current_state():
    """分析当前统计字段的状态"""
    print("=" * 60)
    print("分析当前统计字段状态")
    print("=" * 60)
    
    # 读取数据库
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    with open(json_path, 'r') as f:
        db = json.load(f)
    
    # 统计各字段的缺失情况
    fields_to_check = [
        'avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score',
        'total_errors', 'tool_selection_errors', 'parameter_config_errors',
        'tool_coverage_rate', 'avg_tool_calls',
        'assisted_success', 'assisted_failure', 'assistance_rate'
    ]
    
    field_stats = {field: {'total': 0, 'non_zero': 0} for field in fields_to_check}
    
    for model_name, model_data in db.get('models', {}).items():
        if 'by_prompt_type' not in model_data:
            continue
        for prompt_type, prompt_data in model_data['by_prompt_type'].items():
            if 'by_tool_success_rate' not in prompt_data:
                continue
            for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                if 'by_difficulty' not in rate_data:
                    continue
                for diff, diff_data in rate_data['by_difficulty'].items():
                    if 'by_task_type' not in diff_data:
                        continue
                    for task, task_data in diff_data['by_task_type'].items():
                        for field in fields_to_check:
                            field_stats[field]['total'] += 1
                            if task_data.get(field, 0) != 0:
                                field_stats[field]['non_zero'] += 1
    
    print("\n字段统计（非零值比例）：")
    print("-" * 40)
    
    categories = {
        '质量分数': ['avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score'],
        '错误统计': ['total_errors', 'tool_selection_errors', 'parameter_config_errors'],
        '工具覆盖': ['tool_coverage_rate', 'avg_tool_calls'],
        '辅助统计': ['assisted_success', 'assisted_failure', 'assistance_rate']
    }
    
    for category, fields in categories.items():
        print(f"\n{category}:")
        for field in fields:
            if field in field_stats:
                stats = field_stats[field]
                if stats['total'] > 0:
                    percentage = stats['non_zero'] / stats['total'] * 100
                    status = "✅" if percentage > 50 else "⚠️" if percentage > 0 else "❌"
                    print(f"  {status} {field}: {stats['non_zero']}/{stats['total']} ({percentage:.1f}%)")
    
    return field_stats

def fix_batch_test_runner():
    """修改batch_test_runner.py确保所有统计都被计算"""
    print("\n" + "=" * 60)
    print("修复batch_test_runner.py")
    print("=" * 60)
    
    file_path = Path("batch_test_runner.py")
    
    # 备份
    backup_path = file_path.parent / f"{file_path.stem}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_path.suffix}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ 已备份到: {backup_path.name}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 查找需要修改的位置
    modifications = []
    
    # 1. 确保quality_tester总是被正确初始化
    for i, line in enumerate(lines):
        if "self.quality_tester = WorkflowQualityTester(" in line:
            print(f"  找到quality_tester初始化位置: 第{i+1}行")
            # 检查是否有use_phase2_scoring=True
            j = i
            while j < min(i+10, len(lines)):
                if "use_phase2_scoring=True" in lines[j]:
                    print("    ✅ 已启用Phase2评分")
                    break
                j += 1
    
    # 2. 检查分数计算是否始终执行（不依赖于quality_tester的存在）
    for i, line in enumerate(lines):
        if "if hasattr(self.quality_tester, 'stable_scorer')" in line:
            print(f"  ⚠️ 找到条件性分数计算: 第{i+1}行")
            modifications.append({
                'line': i,
                'action': 'ensure_always_calculate',
                'description': '确保分数总是被计算'
            })
    
    # 3. 确保错误分类总是执行
    for i, line in enumerate(lines):
        if "# AI错误分类（如果启用且测试失败）" in line:
            print(f"  找到AI错误分类位置: 第{i+1}行")
            # 检查后续是否有条件判断
            if i+1 < len(lines) and "if" in lines[i+1]:
                print("    ⚠️ AI分类是条件性的")
                modifications.append({
                    'line': i+1,
                    'action': 'always_classify',
                    'description': '确保AI分类总是执行'
                })
    
    print(f"\n需要进行 {len(modifications)} 处修改")
    
    # 如果没有需要修改的地方，分数计算可能已经正确
    if len(modifications) == 0:
        print("✅ batch_test_runner.py看起来已经正确配置")
        print("\n可能的问题：")
        print("1. quality_tester.stable_scorer未正确初始化")
        print("2. 测试执行时跳过了分数计算")
        print("3. 分数计算结果未正确传递到record")
    
    return len(modifications) == 0

def check_enhanced_cumulative_manager():
    """检查enhanced_cumulative_manager.py是否正确处理统计字段"""
    print("\n" + "=" * 60)
    print("检查enhanced_cumulative_manager.py")
    print("=" * 60)
    
    file_path = Path("enhanced_cumulative_manager.py")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 检查关键功能
    checks = {
        'AI分类器初始化': 'self.ai_classifier = EnhancedAIErrorClassifier' in content,
        '质量分数更新': 'avg_workflow_score' in content and 'workflow_score' in content,
        '错误统计更新': 'tool_selection_errors' in content,
        '辅助统计更新': 'assisted_success' in content,
        '工具覆盖率计算': 'tool_coverage_rate' in content
    }
    
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}")
    
    # 检查AI分类器是否默认启用
    if 'use_ai_classification=True' in content or 'use_ai_classification: bool = True' in content:
        print("  ✅ AI分类器默认启用")
    else:
        print("  ⚠️ AI分类器可能未默认启用")
    
    return all(checks.values())

def create_test_with_all_stats():
    """创建一个测试脚本验证所有统计都被计算"""
    print("\n" + "=" * 60)
    print("创建统计验证测试")
    print("=" * 60)
    
    test_script = '''#!/usr/bin/env python3
"""
验证所有统计字段都被正确计算和保存
"""

from batch_test_runner import BatchTestRunner, TestTask
from pathlib import Path
import json

def test_all_statistics():
    print("测试所有统计字段...")
    
    # 创建测试运行器
    runner = BatchTestRunner(
        debug=True,
        save_logs=False,
        use_ai_classification=True  # 强制启用AI分类
    )
    
    # 创建测试任务
    task = TestTask(
        model='test-model',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        tool_success_rate=0.8
    )
    
    # 运行单个测试
    result = runner.run_single_test(
        model=task.model,
        task_type=task.task_type,
        prompt_type=task.prompt_type,
        is_flawed=False,
        flaw_type=None,
        tool_success_rate=task.tool_success_rate
    )
    
    # 检查结果
    print("\\n检查返回的结果：")
    print(f"  Success: {result.get('success')}")
    print(f"  Workflow Score: {result.get('workflow_score')}")
    print(f"  Phase2 Score: {result.get('phase2_score')}")
    print(f"  Quality Score: {result.get('quality_score')}")
    print(f"  Final Score: {result.get('final_score')}")
    print(f"  Tool Coverage: {result.get('tool_coverage_rate')}")
    
    # 检查是否所有分数都有值
    scores = ['workflow_score', 'phase2_score', 'quality_score', 'final_score']
    all_scores_present = all(result.get(score) is not None for score in scores)
    
    if all_scores_present:
        print("\\n✅ 所有质量分数都已计算！")
    else:
        print("\\n❌ 某些质量分数缺失")
        for score in scores:
            if result.get(score) is None:
                print(f"    缺失: {score}")
    
    return all_scores_present

if __name__ == "__main__":
    success = test_all_statistics()
    exit(0 if success else 1)
'''
    
    test_file = Path("test_all_statistics.py")
    with open(test_file, 'w') as f:
        f.write(test_script)
    
    print(f"✅ 创建测试脚本: {test_file}")
    return test_file

def main():
    """主函数"""
    print("=" * 60)
    print("确保所有统计字段都被计算和保存")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 分析当前状态
    field_stats = analyze_current_state()
    
    # 2. 检查batch_test_runner
    runner_ok = fix_batch_test_runner()
    
    # 3. 检查enhanced_cumulative_manager
    manager_ok = check_enhanced_cumulative_manager()
    
    # 4. 创建测试脚本
    test_file = create_test_with_all_stats()
    
    # 5. 总结
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    
    if runner_ok and manager_ok:
        print("✅ 代码配置看起来正确")
        print("\n下一步：")
        print(f"1. 运行测试脚本: python {test_file}")
        print("2. 如果分数仍为None，检查WorkflowQualityTester的初始化")
        print("3. 确保stable_scorer被正确创建")
    else:
        print("⚠️ 发现配置问题")
        print("\n需要修复：")
        if not runner_ok:
            print("- batch_test_runner.py需要确保分数总是被计算")
        if not manager_ok:
            print("- enhanced_cumulative_manager.py需要正确处理统计字段")

if __name__ == "__main__":
    main()