#!/usr/bin/env python3
"""
快速测试数据保存机制
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

def main():
    """测试数据保存"""
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    # 备份原数据库
    backup_path = db_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    
    if db_path.exists():
        with open(db_path, 'r') as f:
            original_db = json.load(f)
        
        # 保存备份
        with open(backup_path, 'w') as f:
            json.dump(original_db, f, indent=2)
        
        print(f"✅ 已备份数据库到: {backup_path}")
        print(f"原始total_tests: {original_db['summary']['total_tests']}")
        
        # 计算某个模型的测试数
        if 'gpt-4o-mini' in original_db.get('models', {}):
            model_data = original_db['models']['gpt-4o-mini']
            if 'by_prompt_type' in model_data:
                print("\ngpt-4o-mini现有配置:")
                for prompt_type in model_data['by_prompt_type']:
                    pt_data = model_data['by_prompt_type'][prompt_type]
                    if 'by_tool_success_rate' in pt_data:
                        for rate in pt_data['by_tool_success_rate']:
                            rate_data = pt_data['by_tool_success_rate'][rate]
                            if 'by_difficulty' in rate_data:
                                for diff in rate_data['by_difficulty']:
                                    diff_data = rate_data['by_difficulty'][diff]
                                    if 'by_task_type' in diff_data:
                                        for task in diff_data['by_task_type']:
                                            task_data = diff_data['by_task_type'][task]
                                            total = task_data.get('total', 0)
                                            if total > 0:
                                                print(f"  {prompt_type}/{rate}/{diff}/{task}: {total} tests")
    
    # 运行一个特定的未测试组合
    print("\n运行新测试组合...")
    cmd = [
        'python', 'smart_batch_runner.py',
        '--model', 'gpt-4o-mini',
        '--prompt-types', 'baseline',  # 不同的prompt type
        '--difficulty', 'very_hard',   # 不同的难度
        '--task-types', 'debugging',   # 不同的任务类型
        '--num-instances', '1',
        '--tool-success-rate', '0.95', # 不同的成功率
        '--batch-commit',
        '--checkpoint-interval', '1',
        '--max-workers', '1',
        '--no-adaptive',
        '--qps', '10',
        '--no-save-logs'
    ]
    
    print(f"命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    
    print(f"退出码: {result.returncode}")
    
    # 检查输出
    if "已保存" in result.stdout or "saved" in result.stdout.lower():
        print("✅ 输出显示数据已保存")
    
    # 等待数据写入
    time.sleep(3)
    
    # 重新加载数据库
    with open(db_path, 'r') as f:
        new_db = json.load(f)
    
    new_total = new_db['summary']['total_tests']
    print(f"\n新的total_tests: {new_total}")
    
    if new_total > original_db['summary']['total_tests']:
        print(f"✅ 数据保存成功！增加了 {new_total - original_db['summary']['total_tests']} 个测试")
    else:
        print("⚠️ total_tests未增加")
        
        # 检查具体的模型数据
        if 'gpt-4o-mini' in new_db.get('models', {}):
            model_data = new_db['models']['gpt-4o-mini']
            if 'by_prompt_type' in model_data:
                if 'baseline' in model_data['by_prompt_type']:
                    baseline_data = model_data['by_prompt_type']['baseline']
                    if 'by_tool_success_rate' in baseline_data:
                        if '0.95' in baseline_data['by_tool_success_rate']:
                            print("✅ 找到新的0.95 tool_success_rate数据")
                            rate_data = baseline_data['by_tool_success_rate']['0.95']
                            if 'by_difficulty' in rate_data:
                                if 'very_hard' in rate_data['by_difficulty']:
                                    print("✅ 找到very_hard难度数据")
                                    diff_data = rate_data['by_difficulty']['very_hard']
                                    if 'by_task_type' in diff_data:
                                        if 'debugging' in diff_data['by_task_type']:
                                            task_data = diff_data['by_task_type']['debugging']
                                            print(f"✅ 找到debugging任务数据: {task_data.get('total', 0)} tests")
                                            print("📝 数据已保存到正确的层次结构中！")
    
    return 0

if __name__ == "__main__":
    exit(main())