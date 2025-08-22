#!/usr/bin/env python3
"""
分析flawed项目在数据库中不稳定的问题
"""

import json
from pathlib import Path
from collections import defaultdict
import time

def count_flawed_items(db_path):
    """统计数据库中的flawed项目"""
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    flawed_counts = {
        'models_with_flawed': [],
        'flawed_prompt_types': defaultdict(int),
        'total_flawed_tests': 0
    }
    
    for model_name, model_data in db.get('models', {}).items():
        if 'by_prompt_type' in model_data:
            for prompt_type in model_data['by_prompt_type'].keys():
                if 'flawed' in prompt_type:
                    flawed_counts['flawed_prompt_types'][prompt_type] += 1
                    flawed_counts['models_with_flawed'].append(f"{model_name}:{prompt_type}")
                    
                    # 统计测试数
                    prompt_data = model_data['by_prompt_type'][prompt_type]
                    if 'by_tool_success_rate' in prompt_data:
                        for rate_data in prompt_data['by_tool_success_rate'].values():
                            if 'by_difficulty' in rate_data:
                                for diff_data in rate_data['by_difficulty'].values():
                                    if 'by_task_type' in diff_data:
                                        for task_data in diff_data['by_task_type'].values():
                                            flawed_counts['total_flawed_tests'] += task_data.get('total', 0)
    
    return flawed_counts

def monitor_changes(db_path, interval=2, count=5):
    """监控数据库中flawed项目的变化"""
    print(f"监控数据库变化 ({count}次，间隔{interval}秒)...")
    print("="*60)
    
    results = []
    for i in range(count):
        counts = count_flawed_items(db_path)
        results.append(counts)
        
        print(f"\n第{i+1}次检查:")
        print(f"  包含flawed的模型数: {len(set([m.split(':')[0] for m in counts['models_with_flawed']]))}")
        print(f"  flawed prompt类型分布:")
        for prompt_type, count in sorted(counts['flawed_prompt_types'].items()):
            print(f"    {prompt_type}: {count}个模型")
        print(f"  总flawed测试数: {counts['total_flawed_tests']}")
        
        if i > 0:
            # 比较变化
            prev = results[i-1]
            curr = results[i]
            
            if prev['models_with_flawed'] != curr['models_with_flawed']:
                print("  ⚠️ 检测到变化!")
                added = set(curr['models_with_flawed']) - set(prev['models_with_flawed'])
                removed = set(prev['models_with_flawed']) - set(curr['models_with_flawed'])
                if added:
                    print(f"    新增: {added}")
                if removed:
                    print(f"    消失: {removed}")
        
        if i < count - 1:
            time.sleep(interval)
    
    # 分析稳定性
    print("\n" + "="*60)
    print("稳定性分析:")
    
    all_flawed_items = set()
    for r in results:
        all_flawed_items.update(r['models_with_flawed'])
    
    stable_items = set(results[0]['models_with_flawed'])
    for r in results[1:]:
        stable_items &= set(r['models_with_flawed'])
    
    unstable_items = all_flawed_items - stable_items
    
    print(f"  总共出现过的flawed项: {len(all_flawed_items)}")
    print(f"  稳定存在的项: {len(stable_items)}")
    print(f"  不稳定的项: {len(unstable_items)}")
    
    if unstable_items:
        print("\n  不稳定项目详情:")
        for item in sorted(unstable_items):
            appearances = sum(1 for r in results if item in r['models_with_flawed'])
            print(f"    {item}: 出现{appearances}/{count}次")

def check_concurrent_processes():
    """检查是否有并发进程在运行"""
    import subprocess
    
    print("\n检查并发进程...")
    cmd = "ps aux | grep -E 'python.*(batch|ultra|smart)' | grep -v grep"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("发现可能的并发进程:")
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split()
                pid = parts[1]
                cmd_part = ' '.join(parts[10:])[:100]
                print(f"  PID {pid}: {cmd_part}...")
    else:
        print("未发现并发进程")

def analyze_test_groups(db_path):
    """分析test_groups中的flawed相关条目"""
    with open(db_path, 'r') as f:
        db = json.load(f)
    
    print("\n分析test_groups...")
    flawed_groups = []
    
    for group_id, group_data in db.get('test_groups', {}).items():
        if 'flawed' in group_data.get('prompt_type', ''):
            flawed_groups.append({
                'id': group_id,
                'model': group_data.get('model'),
                'prompt_type': group_data.get('prompt_type'),
                'total_tests': group_data.get('total_tests', 0),
                'timestamp': group_data.get('timestamp', '')
            })
    
    if flawed_groups:
        print(f"找到 {len(flawed_groups)} 个flawed test groups:")
        for g in sorted(flawed_groups, key=lambda x: x['timestamp'])[-5:]:  # 显示最近5个
            print(f"  {g['timestamp']}: {g['model']} - {g['prompt_type']} ({g['total_tests']}个测试)")
    else:
        print("未找到flawed test groups")

if __name__ == "__main__":
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        exit(1)
    
    print("分析flawed项目不稳定问题")
    print("="*60)
    
    # 1. 监控变化
    monitor_changes(db_path, interval=3, count=5)
    
    # 2. 检查并发进程
    check_concurrent_processes()
    
    # 3. 分析test_groups
    analyze_test_groups(db_path)
    
    print("\n分析完成!")