#!/usr/bin/env python3
"""
将master_database.json转换为Parquet格式
保留所有层次结构和数据完整性
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import pyarrow as pa
import pyarrow.parquet as pq

def flatten_hierarchical_data(db_data):
    """
    将层次化的JSON数据展平为DataFrame格式
    保留所有维度信息
    """
    records = []
    
    # 遍历models数据
    models_data = db_data.get('models', {})
    
    for model_name, model_data in models_data.items():
        # 提取overall_stats
        overall_stats = model_data.get('overall_stats', {})
        
        # 遍历prompt types
        by_prompt = model_data.get('by_prompt_type', {})
        
        for prompt_type, prompt_data in by_prompt.items():
            # 遍历tool_success_rate
            by_rate = prompt_data.get('by_tool_success_rate', {})
            
            for rate, rate_data in by_rate.items():
                # 遍历difficulty
                by_diff = rate_data.get('by_difficulty', {})
                
                for difficulty, diff_data in by_diff.items():
                    # 遍历task_type
                    by_task = diff_data.get('by_task_type', {})
                    
                    for task_type, task_data in by_task.items():
                        # 构建记录
                        record = {
                            # 基本维度
                            'model': model_name,
                            'prompt_type': prompt_type,
                            'tool_success_rate': float(rate),
                            'difficulty': difficulty,
                            'task_type': task_type,
                            
                            # 测试统计
                            'total': task_data.get('total', 0),
                            'successful': task_data.get('successful', 0),
                            'partial': task_data.get('partial', 0),
                            'failed': task_data.get('failed', 0),
                            
                            # 成功率指标
                            'success_rate': task_data.get('success_rate', 0),
                            'partial_rate': task_data.get('partial_rate', 0),
                            'failure_rate': task_data.get('failure_rate', 0),
                            'weighted_success_score': task_data.get('weighted_success_score', 0),
                            
                            # 执行指标
                            'avg_execution_time': task_data.get('avg_execution_time', 0),
                            'avg_turns': task_data.get('avg_turns', 0),
                            'tool_coverage_rate': task_data.get('tool_coverage_rate', 0),
                            'avg_tool_calls': task_data.get('avg_tool_calls', 0),
                            
                            # 元数据
                            'timestamp': datetime.now().isoformat(),
                            'source': 'master_database.json'
                        }
                        
                        # 使用正确的字段名
                        full_success = task_data.get('full_success', 0) or task_data.get('successful', 0)
                        partial_success = task_data.get('partial_success', 0) or task_data.get('partial', 0)
                        failures = task_data.get('total', 0) - full_success - partial_success
                        
                        # 为每个成功的测试创建记录（保持原子性）
                        for i in range(full_success):
                            test_record = record.copy()
                            test_record['test_id'] = f"{model_name}_{prompt_type}_{rate}_{difficulty}_{task_type}_success_{i}"
                            test_record['success'] = True
                            test_record['partial_success'] = False
                            records.append(test_record)
                        
                        # 为每个部分成功的测试创建记录
                        for i in range(partial_success):
                            test_record = record.copy()
                            test_record['test_id'] = f"{model_name}_{prompt_type}_{rate}_{difficulty}_{task_type}_partial_{i}"
                            test_record['success'] = False
                            test_record['partial_success'] = True
                            records.append(test_record)
                        
                        # 为每个失败的测试创建记录
                        for i in range(failures):
                            test_record = record.copy()
                            test_record['test_id'] = f"{model_name}_{prompt_type}_{rate}_{difficulty}_{task_type}_failed_{i}"
                            test_record['success'] = False
                            test_record['partial_success'] = False
                            records.append(test_record)
    
    return records

def convert_json_to_parquet():
    """主转换函数"""
    # 路径配置
    json_path = Path("pilot_bench_cumulative_results/master_database.json")
    parquet_dir = Path("pilot_bench_parquet_data")
    parquet_dir.mkdir(exist_ok=True)
    
    # 读取JSON数据
    print(f"📖 读取 {json_path}...")
    with open(json_path, 'r') as f:
        db_data = json.load(f)
    
    # 统计原始数据
    models_count = len(db_data.get('models', {}))
    total_tests = db_data.get('summary', {}).get('total_tests', 0)
    
    # 计算实际测试数
    actual_tests = 0
    for model_data in db_data.get('models', {}).values():
        actual_tests += model_data.get('total_tests', 0)
    
    print(f"  - 模型数量: {models_count}")
    print(f"  - 总测试数: {total_tests if total_tests > 0 else actual_tests}")
    
    # 展平数据
    print("\n🔄 转换数据结构...")
    records = flatten_hierarchical_data(db_data)
    print(f"  - 生成记录数: {len(records)}")
    
    if not records:
        print("⚠️  没有数据需要转换")
        return False
    
    # 创建DataFrame
    df = pd.DataFrame(records)
    
    # 优化数据类型
    print("\n📊 优化数据类型...")
    
    # 类别型数据
    categorical_cols = ['model', 'prompt_type', 'difficulty', 'task_type', 'source']
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')
    
    # 布尔型数据
    bool_cols = ['success', 'partial_success']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype(bool)
    
    # 浮点型数据
    float_cols = ['tool_success_rate', 'success_rate', 'partial_rate', 'failure_rate', 
                  'weighted_success_score', 'avg_execution_time', 'avg_turns', 
                  'tool_coverage_rate', 'avg_tool_calls']
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('float32')
    
    # 整型数据
    int_cols = ['total', 'successful', 'partial', 'failed']
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int32')
    
    # 保存主数据文件
    main_file = parquet_dir / "test_results.parquet"
    print(f"\n💾 保存到 {main_file}...")
    df.to_parquet(main_file, index=False, compression='snappy')
    
    # 创建汇总统计文件
    print("\n📈 生成汇总统计...")
    
    # 模型级别统计
    model_stats = df.groupby('model').agg({
        'success': ['count', 'sum', 'mean'],
        'partial_success': 'sum',
        'avg_execution_time': 'mean',
        'tool_coverage_rate': 'mean'
    }).round(4)
    
    stats_file = parquet_dir / "model_stats.parquet"
    model_stats.to_parquet(stats_file)
    
    # 创建元数据文件
    metadata = {
        'conversion_time': datetime.now().isoformat(),
        'source_file': str(json_path),
        'total_records': len(df),
        'models': df['model'].unique().tolist(),
        'prompt_types': df['prompt_type'].unique().tolist(),
        'difficulties': df['difficulty'].unique().tolist(),
        'task_types': df['task_type'].unique().tolist(),
        'data_schema': {
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
    }
    
    metadata_file = parquet_dir / "metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # 验证数据
    print("\n✅ 转换完成！验证结果：")
    print(f"  - 主数据文件: {main_file} ({main_file.stat().st_size / 1024:.1f} KB)")
    print(f"  - 统计文件: {stats_file} ({stats_file.stat().st_size / 1024:.1f} KB)")
    print(f"  - 元数据文件: {metadata_file}")
    
    # 显示数据摘要
    print("\n📋 数据摘要：")
    print(f"  - 总记录数: {len(df)}")
    print(f"  - 模型数: {df['model'].nunique()}")
    print(f"  - 成功测试: {df['success'].sum()}")
    print(f"  - 部分成功: {df['partial_success'].sum()}")
    print(f"  - 失败测试: {(~df['success'] & ~df['partial_success']).sum()}")
    
    # 显示前几个模型的统计
    print("\n🏆 模型性能（前5个）：")
    top_models = df.groupby('model')['success'].agg(['count', 'mean']).sort_values('mean', ascending=False).head()
    for model, stats in top_models.iterrows():
        print(f"  - {model}: {stats['count']:.0f} 测试, {stats['mean']*100:.1f}% 成功率")
    
    return True

if __name__ == "__main__":
    success = convert_json_to_parquet()
    
    if success:
        print("\n" + "="*60)
        print("🎉 转换成功！现在可以使用Parquet格式进行增量测试")
        print("="*60)
        print("\n下一步：")
        print("1. 设置环境变量: export STORAGE_FORMAT=parquet")
        print("2. 运行增量测试: python smart_batch_runner.py ...")
        print("3. 查看数据: python view_parquet_data.py")
    else:
        print("\n❌ 转换失败，请检查源文件")