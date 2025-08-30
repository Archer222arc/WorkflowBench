#!/usr/bin/env python3
"""
分析并发模式下的数据完整性问题
基于用户反馈：串行+Parquet正常，并发+JSON有问题
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def analyze_concurrent_execution_logs():
    """分析并发执行的日志模式"""
    print("=" * 60)
    print("🔍 并发执行日志模式分析")
    print("=" * 60)
    
    log_dir = Path("logs")
    if not log_dir.exists():
        print("❌ 日志目录不存在")
        return
    
    # 找到最新的批处理日志（用户提到的5.1测试）
    log_files = sorted(log_dir.glob("batch_test_*.log"), 
                      key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not log_files:
        print("❌ 没有找到日志文件")
        return
    
    # 分析最新的几个日志文件
    models_found = set()
    test_starts = []
    test_completions = []
    failures = []
    
    for log_file in log_files[:10]:  # 分析最新的10个文件
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            print(f"\n📁 分析文件: {log_file.name}")
            
            for line in lines:
                # 寻找模型执行的证据
                if "Starting single test:" in line and "model=" in line:
                    # 提取模型名
                    match = re.search(r'model=([^,]+)', line)
                    if match:
                        model = match.group(1)
                        models_found.add(model)
                        test_starts.append((model, log_file.name, line.strip()))
                
                # 寻找测试完成/失败的证据
                if "test completed" in line.lower() or "test failed" in line.lower():
                    test_completions.append((log_file.name, line.strip()))
                
                # 寻找API错误或超时
                if any(error_keyword in line.lower() for error_keyword in 
                      ["error", "timeout", "failed", "exception"]):
                    failures.append((log_file.name, line.strip()))
                    
        except Exception as e:
            print(f"❌ 读取日志失败: {e}")
    
    print(f"\n📊 发现的模型总数: {len(models_found)}")
    for model in sorted(models_found):
        count = sum(1 for start in test_starts if start[0] == model)
        print(f"   {model}: {count} 次测试启动")
    
    # 检查期望的模型是否都出现了
    expected_models = [
        "DeepSeek-V3-0324", "DeepSeek-R1-0528", 
        "qwen2.5-72b-instruct", "qwen2.5-32b-instruct", "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct", "qwen2.5-3b-instruct", "Llama-3.3-70B-Instruct"
    ]
    
    missing_models = set(expected_models) - models_found
    if missing_models:
        print(f"\n❌ 未在日志中发现的模型:")
        for model in missing_models:
            print(f"   - {model}")
    
    print(f"\n📈 测试启动总次数: {len(test_starts)}")
    print(f"📉 错误/失败总次数: {len(failures)}")

def analyze_json_data_integrity():
    """分析JSON数据完整性问题"""
    print("\n" + "=" * 60)
    print("🔍 JSON数据完整性分析")
    print("=" * 60)
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return
    
    with open(db_path, 'r', encoding='utf-8') as f:
        db = json.load(f)
    
    print(f"数据库版本: {db.get('version', 'Unknown')}")
    print(f"创建时间: {db.get('created_at', 'Unknown')}")
    print(f"最后更新: {db.get('last_updated', 'Unknown')}")
    
    # 分析测试时间分布
    models = db.get('models', {})
    time_analysis = []
    
    for model_name, model_data in models.items():
        first_test = model_data.get('first_test_time')
        last_test = model_data.get('last_test_time')
        total_tests = model_data.get('total_tests', 0)
        
        if first_test and last_test:
            try:
                first_dt = datetime.fromisoformat(first_test.replace('Z', '+00:00'))
                last_dt = datetime.fromisoformat(last_test.replace('Z', '+00:00'))
                duration = (last_dt - first_dt).total_seconds()
                time_analysis.append((model_name, total_tests, duration, first_dt, last_dt))
            except:
                print(f"❌ 解析时间失败: {model_name}")
    
    # 按时间排序
    time_analysis.sort(key=lambda x: x[3])  # 按first_dt排序
    
    print("\n⏰ 模型测试时间序列:")
    for model_name, total_tests, duration, first_dt, last_dt in time_analysis:
        print(f"   {model_name}:")
        print(f"     测试数量: {total_tests}")
        print(f"     开始时间: {first_dt.strftime('%H:%M:%S')}")
        print(f"     结束时间: {last_dt.strftime('%H:%M:%S')}")
        print(f"     持续时间: {duration:.1f}秒")
        print()
    
    # 检查是否有重叠的测试时间（可能表明并发问题）
    print("🔄 并发重叠分析:")
    for i in range(len(time_analysis)):
        for j in range(i + 1, len(time_analysis)):
            model1, _, _, start1, end1 = time_analysis[i]
            model2, _, _, start2, end2 = time_analysis[j]
            
            # 检查时间重叠
            if start1 <= end2 and start2 <= end1:
                overlap_start = max(start1, start2)
                overlap_end = min(end1, end2)
                overlap_duration = (overlap_end - overlap_start).total_seconds()
                
                if overlap_duration > 0:
                    print(f"   ⚠️  {model1} 与 {model2} 有 {overlap_duration:.1f}秒 重叠")

def analyze_ultra_parallel_logic():
    """分析ultra_parallel_runner的逻辑问题"""
    print("\n" + "=" * 60)
    print("🔍 Ultra Parallel Runner逻辑分析")
    print("=" * 60)
    
    # 检查ultra_parallel_runner.py是否存在问题
    runner_path = Path("ultra_parallel_runner.py")
    if not runner_path.exists():
        print("❌ ultra_parallel_runner.py文件不存在")
        return
    
    with open(runner_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键逻辑点
    issues = []
    
    # 1. 检查qwen模型的小写转换问题
    if 'model=model.lower()' in content:
        issues.append("❌ 发现model.lower()转换，可能导致qwen模型名称问题")
    
    # 2. 检查模型分片逻辑
    if '_create_qwen_smart_shards' in content:
        print("✅ 找到qwen智能分片逻辑")
        # 提取相关代码段
        pattern = r'def _create_qwen_smart_shards.*?(?=def|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            qwen_logic = match.group(0)
            if 'model.lower()' in qwen_logic:
                issues.append("❌ qwen分片中有model.lower()转换")
    
    # 3. 检查DeepSeek-R1的处理
    deepseek_r1_mentions = content.count('deepseek-r1')
    deepseek_R1_mentions = content.count('DeepSeek-R1')
    print(f"DeepSeek-R1在代码中提及次数: {deepseek_R1_mentions + deepseek_r1_mentions}")
    
    if deepseek_r1_mentions == 0 and deepseek_R1_mentions == 0:
        issues.append("❌ ultra_parallel_runner中没有DeepSeek-R1相关逻辑")
    
    # 4. 检查模型族映射逻辑
    if 'elif "deepseek-r1" in model.lower():' in content:
        print("✅ 找到DeepSeek-R1模型族映射逻辑")
    else:
        issues.append("❌ 缺少DeepSeek-R1模型族映射逻辑")
    
    if issues:
        print("\n⚠️  发现的潜在问题:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ ultra_parallel_runner逻辑看起来正常")

def suggest_fixes():
    """建议修复方案"""
    print("\n" + "=" * 60)
    print("🛠️  修复建议")
    print("=" * 60)
    
    print("基于分析，建议按以下优先级修复:")
    print()
    print("1. 🔧 修复ultra_parallel_runner.py中的model.lower()问题")
    print("   - 在qwen分片中保持原始大小写")
    print("   - 确保模型名称传递的一致性")
    print()
    print("2. 🔧 检查并发模式下的模型遍历逻辑")
    print("   - 确认所有预期模型都被包含在执行列表中")
    print("   - 验证DeepSeek-R1是否被正确触发")
    print()
    print("3. 🔧 加强JSON格式的并发写入保护")
    print("   - 检查数据保存时的锁机制")  
    print("   - 防止数据覆盖和重复写入")
    print()
    print("4. 🧪 创建并发测试验证脚本")
    print("   - 小规模复现问题")
    print("   - 验证修复效果")

def main():
    """主函数"""
    print("🔍 并发模式数据完整性问题分析")
    print(f"🕐 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    analyze_concurrent_execution_logs()
    analyze_json_data_integrity()
    analyze_ultra_parallel_logic()
    suggest_fixes()
    
    print("\n" + "=" * 60)
    print("📋 关键发现")
    print("=" * 60)
    print("✅ 串行+Parquet模式工作正常（用户确认）")
    print("❌ 并发+JSON模式存在数据丢失/重复问题")
    print("❌ DeepSeek-R1完全没有被执行")
    print("❌ 部分qwen模型缺失，部分重复")
    print("⚠️  问题可能出现在模型调度或并发数据写入阶段")

if __name__ == "__main__":
    main()