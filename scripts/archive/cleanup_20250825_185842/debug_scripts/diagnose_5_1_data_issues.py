#!/usr/bin/env python3
"""
诊断5.1基准测试数据问题
- DeepSeek-R1缺失问题
- Qwen模型数据混乱问题  
- 测试数量异常问题
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def analyze_database():
    """分析数据库状态"""
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
        
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    print("=" * 60)
    print("📊 5.1基准测试数据完整性分析")
    print("=" * 60)
    
    # 预期的模型列表（来自脚本）
    expected_models = [
        "DeepSeek-V3-0324",
        "DeepSeek-R1-0528", 
        "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct",
        "qwen2.5-14b-instruct", 
        "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct",
        "Llama-3.3-70B-Instruct"
    ]
    
    # 实际数据库中的模型
    actual_models = list(db.get('models', {}).keys())
    
    print(f"预期模型数量: {len(expected_models)}")
    print(f"实际模型数量: {len(actual_models)}")
    print()
    
    # 检查缺失的模型
    missing_models = set(expected_models) - set(actual_models)
    extra_models = set(actual_models) - set(expected_models)
    
    if missing_models:
        print("❌ 缺失的模型:")
        for model in missing_models:
            print(f"   - {model}")
    
    if extra_models:
        print("⚠️  额外的模型:")
        for model in extra_models:
            print(f"   - {model}")
    
    if not missing_models and not extra_models:
        print("✅ 模型列表完整")
    
    print()
    
    # 分析每个模型的测试详情
    print("=" * 60)
    print("📈 各模型测试详情分析")
    print("=" * 60)
    
    expected_tests_per_model = 10  # 5种任务类型 × 2个实例
    task_types = ["simple_task", "basic_task", "data_pipeline", "api_integration", "multi_stage_pipeline"]
    
    for model in actual_models:
        model_data = db['models'][model]
        total_tests = model_data.get('total_tests', 0)
        
        print(f"\n🎯 {model}")
        print(f"   总测试数: {total_tests} (预期: {expected_tests_per_model})")
        
        if total_tests != expected_tests_per_model:
            print(f"   ❌ 测试数量异常! 差异: {total_tests - expected_tests_per_model}")
        
        # 分析任务类型分布
        if 'by_prompt_type' in model_data:
            optimal_data = model_data['by_prompt_type'].get('optimal', {})
            if 'by_tool_success_rate' in optimal_data:
                rate_08_data = optimal_data['by_tool_success_rate'].get('0.8', {})
                if 'by_difficulty' in rate_08_data:
                    easy_data = rate_08_data['by_difficulty'].get('easy', {})
                    if 'by_task_type' in easy_data:
                        task_data = easy_data['by_task_type']
                        
                        print("   任务类型分布:")
                        for task_type in task_types:
                            if task_type in task_data:
                                count = task_data[task_type].get('total', 0)
                                expected = 2
                                status = "✅" if count == expected else "❌"
                                print(f"     {status} {task_type}: {count} (预期: {expected})")
                            else:
                                print(f"     ❌ {task_type}: 0 (预期: 2) - 完全缺失")
        
        # 分析时间信息
        first_test = model_data.get('first_test_time', 'Unknown')
        last_test = model_data.get('last_test_time', 'Unknown')
        print(f"   测试时间: {first_test} - {last_test}")

def check_normalize_logic():
    """检查模型名称规范化逻辑"""
    print("\n" + "=" * 60)
    print("🔧 模型名称规范化逻辑检查")
    print("=" * 60)
    
    try:
        from cumulative_test_manager import normalize_model_name
        
        test_cases = [
            # DeepSeek系列
            ("DeepSeek-V3-0324", "DeepSeek-V3-0324"),
            ("DeepSeek-V3-0324-2", "DeepSeek-V3-0324"),
            ("DeepSeek-R1-0528", "DeepSeek-R1-0528"), 
            ("DeepSeek-R1-0528-2", "DeepSeek-R1-0528"),
            
            # Qwen系列（应该保持不变）
            ("qwen2.5-72b-instruct", "qwen2.5-72b-instruct"),
            ("qwen2.5-32b-instruct", "qwen2.5-32b-instruct"),
            ("qwen2.5-14b-instruct", "qwen2.5-14b-instruct"),
            ("qwen2.5-7b-instruct", "qwen2.5-7b-instruct"),
            ("qwen2.5-3b-instruct", "qwen2.5-3b-instruct"),
            
            # Llama系列
            ("Llama-3.3-70B-Instruct", "Llama-3.3-70B-Instruct"),
            ("Llama-3.3-70B-Instruct-2", "Llama-3.3-70B-Instruct"),
        ]
        
        all_correct = True
        for input_name, expected in test_cases:
            actual = normalize_model_name(input_name)
            status = "✅" if actual == expected else "❌"
            if actual != expected:
                all_correct = False
            print(f"   {status} {input_name} -> {actual} (预期: {expected})")
        
        if all_correct:
            print("\n✅ 模型名称规范化逻辑正确")
        else:
            print("\n❌ 模型名称规范化存在问题")
            
    except ImportError as e:
        print(f"❌ 无法导入normalize_model_name函数: {e}")

def analyze_log_files():
    """分析最近的日志文件"""
    print("\n" + "=" * 60)
    print("📝 最近测试日志分析")
    print("=" * 60)
    
    log_dir = Path("logs")
    if not log_dir.exists():
        print("❌ 日志目录不存在")
        return
    
    # 找到最新的批处理日志
    log_files = list(log_dir.glob("batch_test_*.log"))
    if not log_files:
        print("❌ 没有找到批处理日志文件")
        return
    
    # 按时间排序，取最新的5个
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    recent_logs = log_files[:5]
    
    print(f"分析最新的 {len(recent_logs)} 个日志文件:")
    
    model_mentions = defaultdict(int)
    
    for log_file in recent_logs:
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 统计每个模型的提及次数
                for model in ["DeepSeek-V3-0324", "DeepSeek-R1-0528", "qwen2.5-72b-instruct", 
                             "qwen2.5-32b-instruct", "qwen2.5-14b-instruct", "qwen2.5-7b-instruct",
                             "qwen2.5-3b-instruct", "Llama-3.3-70B-Instruct"]:
                    count = content.count(model)
                    if count > 0:
                        model_mentions[model] += count
                        
        except Exception as e:
            print(f"   ❌ 读取日志失败 {log_file}: {e}")
    
    print("\n模型在日志中的提及次数:")
    for model, count in sorted(model_mentions.items(), key=lambda x: x[1], reverse=True):
        print(f"   {model}: {count} 次")
    
    if "DeepSeek-R1-0528" not in model_mentions:
        print("\n❌ DeepSeek-R1-0528 在日志中完全没有被提及！")
        print("   这证实了DeepSeek-R1确实没有被测试")

def main():
    """主函数"""
    print("🔍 启动5.1基准测试数据问题诊断")
    print(f"🕐 诊断时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    analyze_database()
    check_normalize_logic()
    analyze_log_files()
    
    print("\n" + "=" * 60)
    print("📋 诊断总结与建议")
    print("=" * 60)
    print("1. 检查ultra_parallel_runner.py中的模型分片逻辑")
    print("2. 检查5.1测试实际执行的模型列表") 
    print("3. 检查API配置是否正确（特别是DeepSeek-R1）")
    print("4. 检查并发模式下的数据保存机制")
    print("5. 验证qwen模型名称在传递过程中是否被篡改")

if __name__ == "__main__":
    main()