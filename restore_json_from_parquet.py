#!/usr/bin/env python3
"""从Parquet文件恢复JSON数据库"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def restore_json_from_parquet():
    """从Parquet文件恢复JSON数据库"""
    
    # 备份当前的JSON文件
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    if json_path.exists():
        backup_path = json_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        json_path.rename(backup_path)
        print(f"✅ 备份当前JSON到: {backup_path}")
    
    # 读取Parquet文件
    parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
    if not parquet_path.exists():
        print("❌ Parquet文件不存在")
        return False
    
    df = pd.read_parquet(parquet_path)
    print(f"📊 从Parquet读取 {len(df)} 条记录")
    
    # 构建JSON数据库结构
    db = {
        "version": "3.0",
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "test_groups": {},
        "models": defaultdict(lambda: {
            "overall_stats": {
                "total_tests": 0,
                "successful_tests": 0,
                "partial_tests": 0,
                "failed_tests": 0,
                "success_rate": 0.0,
                "partial_rate": 0.0,
                "failure_rate": 0.0,
                "weighted_success_score": 0.0,
                "avg_execution_time": 0.0,
                "avg_turns": 0.0,
                "avg_tool_calls": 0.0,
                "tool_coverage_rate": 0.0
            },
            "experiment_metrics": {},
            "by_prompt_type": defaultdict(lambda: {
                "total_tests": 0,
                "success_rate": 0.0,
                "by_tool_success_rate": defaultdict(lambda: {
                    "by_difficulty": defaultdict(lambda: {
                        "by_task_type": defaultdict(lambda: {
                            "total": 0,
                            "successful": 0,
                            "partial": 0,
                            "failed": 0,
                            "success_rate": 0.0,
                            "partial_rate": 0.0,
                            "failure_rate": 0.0,
                            "weighted_success_score": 0.0,
                            "avg_execution_time": 0.0,
                            "avg_turns": 0.0,
                            "tool_coverage_rate": 0.0,
                            "avg_tool_calls": 0.0
                        })
                    })
                })
            })
        }),
        "summary": {
            "total_tests": 0,
            "total_success": 0,
            "total_partial": 0,
            "total_failure": 0,
            "models_tested": [],
            "last_test_time": None
        }
    }
    
    # 处理每条记录
    for _, row in df.iterrows():
        model = row.get('model', 'unknown')
        prompt_type = row.get('prompt_type', 'baseline')
        difficulty = row.get('difficulty', 'easy')
        task_type = row.get('task_type', 'unknown')
        tool_success_rate = str(round(row.get('tool_success_rate', 0.8), 4))
        
        # 确保模型存在
        if model not in db['models']:
            db['models'][model] = {
                "overall_stats": {
                    "total_tests": 0,
                    "successful_tests": 0,
                    "partial_tests": 0,
                    "failed_tests": 0,
                    "success_rate": 0.0,
                    "partial_rate": 0.0,
                    "failure_rate": 0.0,
                    "weighted_success_score": 0.0,
                    "avg_execution_time": 0.0,
                    "avg_turns": 0.0,
                    "avg_tool_calls": 0.0,
                    "tool_coverage_rate": 0.0
                },
                "experiment_metrics": {},
                "by_prompt_type": {}
            }
        
        # 确保prompt_type层级存在
        if prompt_type not in db['models'][model]['by_prompt_type']:
            db['models'][model]['by_prompt_type'][prompt_type] = {
                "total_tests": 0,
                "success_rate": 0.0,
                "by_tool_success_rate": {}
            }
        
        # 确保tool_success_rate层级存在
        if tool_success_rate not in db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate']:
            db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][tool_success_rate] = {
                "by_difficulty": {}
            }
        
        # 确保difficulty层级存在
        if difficulty not in db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][tool_success_rate]['by_difficulty']:
            db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][tool_success_rate]['by_difficulty'][difficulty] = {
                "by_task_type": {}
            }
        
        # 确保task_type层级存在
        if task_type not in db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][tool_success_rate]['by_difficulty'][difficulty]['by_task_type']:
            db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][tool_success_rate]['by_difficulty'][difficulty]['by_task_type'][task_type] = {
                "total": 0,
                "successful": 0,
                "partial": 0,
                "failed": 0,
                "success_rate": 0.0,
                "partial_rate": 0.0,
                "failure_rate": 0.0,
                "weighted_success_score": 0.0,
                "avg_execution_time": 0.0,
                "avg_turns": 0.0,
                "tool_coverage_rate": 0.0,
                "avg_tool_calls": 0.0
            }
        
        # 获取任务类型数据的引用
        task_data = db['models'][model]['by_prompt_type'][prompt_type]['by_tool_success_rate'][tool_success_rate]['by_difficulty'][difficulty]['by_task_type'][task_type]
        
        # 更新统计
        task_data['total'] += 1
        
        success_value = row.get('success', False)
        if pd.isna(success_value):
            success_value = False
        
        if success_value:
            task_data['successful'] += 1
            db['models'][model]['overall_stats']['successful_tests'] += 1
            db['summary']['total_success'] += 1
        else:
            # 检查是否是部分成功
            success_level = row.get('success_level', 'failure')
            if success_level == 'partial':
                task_data['partial'] += 1
                db['models'][model]['overall_stats']['partial_tests'] += 1
                db['summary']['total_partial'] += 1
            else:
                task_data['failed'] += 1
                db['models'][model]['overall_stats']['failed_tests'] += 1
                db['summary']['total_failure'] += 1
        
        # 更新总数
        db['models'][model]['overall_stats']['total_tests'] += 1
        db['summary']['total_tests'] += 1
        
        # 累加其他指标（用于计算平均值）
        exec_time = row.get('execution_time', 0)
        if pd.notna(exec_time):
            task_data['avg_execution_time'] += exec_time
        
        turns = row.get('turns', 0)
        if pd.notna(turns):
            task_data['avg_turns'] += turns
            db['models'][model]['overall_stats']['avg_turns'] += turns
        
        tool_calls = row.get('tool_calls', 0)
        if pd.notna(tool_calls):
            task_data['avg_tool_calls'] += tool_calls
            db['models'][model]['overall_stats']['avg_tool_calls'] += tool_calls
        
        # 更新tool_coverage_rate
        tool_coverage = row.get('tool_coverage_rate', 0)
        if pd.notna(tool_coverage):
            task_data['tool_coverage_rate'] += tool_coverage
            db['models'][model]['overall_stats']['tool_coverage_rate'] += tool_coverage
    
    # 计算平均值和比率
    for model, model_data in db['models'].items():
        total = model_data['overall_stats']['total_tests']
        if total > 0:
            model_data['overall_stats']['success_rate'] = model_data['overall_stats']['successful_tests'] / total
            model_data['overall_stats']['partial_rate'] = model_data['overall_stats']['partial_tests'] / total
            model_data['overall_stats']['failure_rate'] = model_data['overall_stats']['failed_tests'] / total
            model_data['overall_stats']['avg_turns'] /= total
            model_data['overall_stats']['avg_tool_calls'] /= total
            model_data['overall_stats']['tool_coverage_rate'] /= total
        
        # 处理每个prompt_type
        for prompt_type, prompt_data in model_data['by_prompt_type'].items():
            prompt_total = 0
            prompt_success = 0
            
            for rate_key, rate_data in prompt_data['by_tool_success_rate'].items():
                for diff_key, diff_data in rate_data['by_difficulty'].items():
                    for task_key, task_data in diff_data['by_task_type'].items():
                        if task_data['total'] > 0:
                            # 计算比率
                            task_data['success_rate'] = task_data['successful'] / task_data['total']
                            task_data['partial_rate'] = task_data['partial'] / task_data['total']
                            task_data['failure_rate'] = task_data['failed'] / task_data['total']
                            
                            # 计算平均值
                            task_data['avg_execution_time'] /= task_data['total']
                            task_data['avg_turns'] /= task_data['total']
                            task_data['avg_tool_calls'] /= task_data['total']
                            task_data['tool_coverage_rate'] /= task_data['total']
                            
                            # 累计prompt级别统计
                            prompt_total += task_data['total']
                            prompt_success += task_data['successful']
            
            # 更新prompt级别统计
            prompt_data['total_tests'] = prompt_total
            if prompt_total > 0:
                prompt_data['success_rate'] = prompt_success / prompt_total
    
    # 更新模型列表
    db['summary']['models_tested'] = list(db['models'].keys())
    
    # 保存到JSON文件
    json_path = Path('pilot_bench_cumulative_results/master_database.json')
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(dict(db), f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ 成功恢复JSON数据库")
    print(f"   总测试数: {db['summary']['total_tests']}")
    print(f"   成功: {db['summary']['total_success']}")
    print(f"   部分: {db['summary']['total_partial']}")
    print(f"   失败: {db['summary']['total_failure']}")
    print(f"   模型数: {len(db['models'])}")
    
    return True

if __name__ == "__main__":
    restore_json_from_parquet()