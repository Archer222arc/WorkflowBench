#!/usr/bin/env python3
"""
测试ResultMerger的简单脚本
"""

import os
import json
import time
import threading
from pathlib import Path

# 设置环境变量
os.environ['USE_RESULT_COLLECTOR'] = 'true'
os.environ['STORAGE_FORMAT'] = 'json'

from result_merger import ResultMerger, start_auto_merge, stop_auto_merge, force_merge

def create_test_data():
    """创建测试数据文件"""
    temp_dir = Path("temp_results")
    temp_dir.mkdir(exist_ok=True)
    
    models = ['DeepSeek-V3-0324', 'qwen2.5-72b-instruct', 'gpt-4o-mini']
    created_files = []
    
    for i in range(2):
        for model in models:
            # 创建测试结果
            result = {
                'model': model,
                'results': []
            }
            
            # 添加3个测试结果
            for j in range(3):
                test_result = {
                    'model': model,
                    'task_type': 'simple_task',
                    'prompt_type': 'optimal',
                    'difficulty': 'easy',
                    'success': True if j % 2 == 0 else False,
                    'execution_time': 30 + j * 10,
                    'turns': 10,
                    'tool_calls': 5,
                    'workflow_score': 0.8,
                    'phase2_score': 0.85,
                    'quality_score': 0.82,
                    'final_score': 0.85,
                    'tool_success_rate': 0.8,
                    'tool_coverage_rate': 0.9,
                    'timestamp': time.time()
                }
                result['results'].append(test_result)
            
            # 写入临时文件
            filename = f'test_{model}_{i}_{int(time.time()*1000)}.json'
            filepath = temp_dir / filename
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2)
            created_files.append(filename)
            print(f'  ✅ 创建测试文件: {filename}')
        
        time.sleep(1)  # 稍微间隔一下
    
    return created_files

def check_database():
    """检查数据库状态"""
    db_path = Path('pilot_bench_cumulative_results/master_database.json')
    if db_path.exists():
        with open(db_path, 'r') as f:
            db = json.load(f)
        
        print('\n📊 数据库状态:')
        models = db.get('models', {})
        total_tests = 0
        for model_name in models:
            # 从整个模型数据中统计总测试数
            model_data = models[model_name]
            model_total = 0
            
            # 遍历所有层级统计
            if 'by_prompt_type' in model_data:
                for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                    if 'by_tool_success_rate' in prompt_data:
                        for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                            if 'by_difficulty' in rate_data:
                                for diff, diff_data in rate_data['by_difficulty'].items():
                                    if 'by_task_type' in diff_data:
                                        for task_type, task_data in diff_data['by_task_type'].items():
                                            model_total += task_data.get('total', 0)
            
            if model_total > 0:
                print(f'  - {model_name}: {model_total} tests')
                total_tests += model_total
        
        print(f'  📈 总计: {total_tests} tests')
    else:
        print('❌ 数据库文件不存在')

def main():
    """主函数"""
    print("🔍 测试ResultMerger合并机制")
    print("=" * 50)
    
    # 清理旧文件
    print("\n1. 清理旧的临时文件...")
    temp_dir = Path("temp_results")
    if temp_dir.exists():
        for f in temp_dir.glob("*.json"):
            f.unlink()
        print("  ✅ 清理完成")
    
    # 检查初始数据库状态
    print("\n2. 初始数据库状态:")
    check_database()
    
    # 启动合并器
    print("\n3. 启动ResultMerger...")
    merger = start_auto_merge(interval=3)  # 每3秒检查一次
    print(f"  ✅ Merger已启动，间隔{merger.merge_interval}秒")
    
    # 创建测试数据
    print("\n4. 创建测试数据...")
    files = create_test_data()
    print(f"  📝 创建了{len(files)}个测试文件")
    
    # 等待合并
    print("\n5. 等待合并处理...")
    for i in range(3):
        time.sleep(3)
        print(f"  ⏰ 等待中... {(i+1)*3}秒")
    
    # 强制合并剩余文件
    print("\n6. 强制合并剩余文件...")
    count = force_merge()
    print(f"  ✅ 合并了{count}个文件")
    
    # 停止合并器
    print("\n7. 停止合并器...")
    stop_auto_merge()
    print("  ✅ Merger已停止")
    
    # 检查最终数据库状态
    print("\n8. 最终数据库状态:")
    check_database()
    
    # 检查临时文件
    temp_files = list(temp_dir.glob("*.json"))
    print(f"\n9. 剩余临时文件: {len(temp_files)}个")
    if temp_files:
        for f in temp_files[:5]:  # 只显示前5个
            print(f"  - {f.name}")
    
    print("\n✅ 测试完成！")

if __name__ == "__main__":
    main()