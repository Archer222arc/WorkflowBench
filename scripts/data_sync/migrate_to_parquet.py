#!/usr/bin/env python3
"""
迁移JSON数据到Parquet格式
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from parquet_data_manager import ParquetDataManager
import sys

def migrate_json_to_parquet(json_path: Path, manager: ParquetDataManager = None):
    """
    将JSON数据库迁移到Parquet格式
    """
    if manager is None:
        manager = ParquetDataManager()
    
    print(f"\n迁移文件: {json_path}")
    print("="*60)
    
    # 读取JSON数据
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    print(f"数据库版本: {json_data.get('version', 'unknown')}")
    print(f"最后更新: {json_data.get('last_updated', 'unknown')}")
    
    # 统计信息
    total_records = 0
    model_count = len(json_data.get('models', {}))
    print(f"模型数量: {model_count}")
    
    # 展平JSON数据为表格格式
    records = []
    
    for model_name, model_data in json_data.get('models', {}).items():
        print(f"\n处理模型: {model_name}")
        model_records = 0
        
        # 处理by_prompt_type层次
        if 'by_prompt_type' in model_data:
            for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                
                # 处理by_tool_success_rate层次
                if 'by_tool_success_rate' in prompt_data:
                    for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                        
                        # 处理by_difficulty层次
                        if 'by_difficulty' in rate_data:
                            for diff, diff_data in rate_data['by_difficulty'].items():
                                
                                # 处理by_task_type层次
                                if 'by_task_type' in diff_data:
                                    for task, task_data in diff_data['by_task_type'].items():
                                        
                                        # 获取测试数量
                                        total_tests = task_data.get('total', 0)
                                        success_count = task_data.get('successful', task_data.get('success', 0))
                                        partial_count = task_data.get('partial', 0)
                                        failed_count = task_data.get('failed', task_data.get('failure', 0))
                                        
                                        # 为每个测试创建一条记录
                                        # 注意：我们根据统计数据重建记录，因为原始测试细节已丢失
                                        for i in range(total_tests):
                                            # 决定这个测试的结果
                                            if i < success_count:
                                                success = True
                                                partial = False
                                            elif i < success_count + partial_count:
                                                success = False
                                                partial = True
                                            else:
                                                success = False
                                                partial = False
                                            
                                            record = {
                                                # 基本信息
                                                'model': model_name,
                                                'prompt_type': prompt_type,
                                                'tool_success_rate': float(rate),
                                                'difficulty': diff,
                                                'task_type': task,
                                                
                                                # 测试结果
                                                'success': success,
                                                'partial_success': partial,
                                                'test_index': i,
                                                
                                                # 平均指标（从统计数据获取）
                                                'avg_execution_time': task_data.get('avg_execution_time', 0),
                                                'avg_turns': task_data.get('avg_turns', 0),
                                                'avg_tool_calls': task_data.get('avg_tool_calls', 0),
                                                'tool_coverage_rate': task_data.get('tool_coverage_rate', 0),
                                                
                                                # 分数指标
                                                'avg_workflow_score': task_data.get('avg_workflow_score', 0),
                                                'avg_phase2_score': task_data.get('avg_phase2_score', 0),
                                                'avg_quality_score': task_data.get('avg_quality_score', 0),
                                                'avg_final_score': task_data.get('avg_final_score', 0),
                                                
                                                # 元数据
                                                'imported_from': json_path.name,
                                                'import_time': datetime.now().isoformat(),
                                                'data_type': 'reconstructed'  # 标记为重建的数据
                                            }
                                            
                                            records.append(record)
                                            model_records += 1
                
                # 处理没有tool_success_rate的旧数据
                elif 'total_tests' in prompt_data:
                    # 这是旧格式，直接在prompt_type下有统计
                    total_tests = prompt_data.get('total_tests', 0)
                    for i in range(total_tests):
                        record = {
                            'model': model_name,
                            'prompt_type': prompt_type,
                            'tool_success_rate': 0.8,  # 默认值
                            'difficulty': 'easy',  # 默认值
                            'task_type': 'unknown',
                            'success': i < prompt_data.get('total_success', 0),
                            'imported_from': json_path.name,
                            'import_time': datetime.now().isoformat(),
                            'data_type': 'legacy'
                        }
                        records.append(record)
                        model_records += 1
        
        print(f"  -> 生成 {model_records} 条记录")
        total_records += model_records
    
    print(f"\n总计: {total_records} 条记录待写入")
    
    if records:
        # 批量写入到Parquet
        print("\n写入Parquet文件...")
        success = manager.batch_append_results(records)
        
        if success:
            print("✅ 迁移成功!")
            
            # 合并增量数据
            print("\n合并增量数据...")
            manager.consolidate_incremental_data()
            
            # 验证
            print("\n验证迁移结果...")
            df = manager.query_model_stats()
            print(f"  Parquet中的记录数: {len(df)}")
            print(f"  模型数: {df['model'].nunique()}")
            print(f"  Prompt类型数: {df['prompt_type'].nunique()}")
            
            # 显示数据分布
            print("\n数据分布:")
            model_dist = df['model'].value_counts().head(10)
            for model, count in model_dist.items():
                print(f"  {model}: {count} 条记录")
            
            return True
        else:
            print("❌ 迁移失败!")
            return False
    else:
        print("⚠️ 没有找到可迁移的数据")
        return False

def main():
    """主函数"""
    print("="*60)
    print("JSON到Parquet数据迁移工具")
    print("="*60)
    
    # 创建Parquet管理器
    manager = ParquetDataManager()
    
    # 要迁移的文件列表
    files_to_migrate = [
        # 优先迁移merge前的备份
        Path("pilot_bench_cumulative_results/master_database_before_merge_20250816_112056.json"),
        # 当前的主数据库
        Path("pilot_bench_cumulative_results/master_database.json"),
    ]
    
    # 检查其他备份文件
    backup_pattern = Path("pilot_bench_cumulative_results").glob("*.backup")
    for backup_file in backup_pattern:
        if backup_file not in files_to_migrate:
            files_to_migrate.append(backup_file)
    
    print(f"\n找到 {len(files_to_migrate)} 个文件待迁移:")
    for i, f in enumerate(files_to_migrate, 1):
        exists = "✅" if f.exists() else "❌"
        print(f"  {i}. {exists} {f.name}")
    
    # 逐个迁移
    migrated_count = 0
    for file_path in files_to_migrate:
        if file_path.exists():
            if migrate_json_to_parquet(file_path, manager):
                migrated_count += 1
        else:
            print(f"\n⚠️ 文件不存在: {file_path}")
    
    print("\n" + "="*60)
    print(f"迁移完成: {migrated_count}/{len(files_to_migrate)} 个文件")
    
    if migrated_count > 0:
        # 最终统计
        print("\n最终数据统计:")
        df = manager.query_model_stats()
        stats = manager.compute_statistics(df)
        
        print(f"  总记录数: {stats['total_tests']}")
        print(f"  总成功数: {stats['success_count']}")
        print(f"  成功率: {stats['success_rate']:.2%}")
        print(f"  模型数: {len(stats['models'])}")
        print(f"  Prompt类型: {', '.join(stats['prompt_types'][:5])}")
        
        # 导出为JSON备份
        print("\n导出JSON备份...")
        export_path = Path("pilot_bench_parquet_data/migrated_database.json")
        if manager.export_to_json(export_path):
            print(f"  已导出到: {export_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 支持指定单个文件
        file_path = Path(sys.argv[1])
        if file_path.exists():
            manager = ParquetDataManager()
            migrate_json_to_parquet(file_path, manager)
        else:
            print(f"文件不存在: {file_path}")
    else:
        # 默认迁移所有文件
        main()