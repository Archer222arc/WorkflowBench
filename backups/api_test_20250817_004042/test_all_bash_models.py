#!/usr/bin/env python3
"""
测试run_systematic_test_final.sh中定义的所有模型
完整测试所有开源和闭源模型的API连接
"""

import time
import json
import traceback
import sys
from datetime import datetime
from pathlib import Path
from api_client_manager import get_client_for_model, get_api_model_name

# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 从bash脚本中提取的完整模型列表
OPENSOURCE_MODELS = [
    "DeepSeek-V3-0324",       # Azure 85409
    "DeepSeek-R1-0528",       # Azure 85409
    "qwen2.5-72b-instruct",   # IdealLab
    "qwen2.5-32b-instruct",   # IdealLab
    "qwen2.5-14b-instruct",   # IdealLab
    "qwen2.5-7b-instruct",    # IdealLab
    "qwen2.5-3b-instruct",    # IdealLab
    "Llama-3.3-70B-Instruct", # Azure 85409
]

CLOSED_SOURCE_MODELS = [
    "gpt-4o-mini",             # Azure
    "gpt-5-mini",              # Azure 85409
    "o3-0416-global",          # IdealLab
    "gemini-2.5-flash-06-17",  # IdealLab
    "kimi-k2",                 # IdealLab
    "claude_sonnet4",          # IdealLab
]

# Azure 85409端点的额外模型（从config.json中发现但未在bash脚本主列表中）
ADDITIONAL_AZURE_MODELS = [
    "gpt-4o",                  # Azure 85409
    "gpt-5-nano",              # Azure 85409
    "gpt-oss-120b",            # Azure 85409
    "grok-3",                  # Azure 85409
    "grok-3-mini",             # Azure 85409 (在bash中被注释但配置存在)
    "o3-mini",                 # Azure 85409
    "DeepSeek-R1",             # Azure 85409
    # 并发实例
    "DeepSeek-V3-0324-2",      # Azure 85409
    "DeepSeek-V3-0324-3",      # Azure 85409
    "DeepSeek-R1-0528-2",      # Azure 85409
    "DeepSeek-R1-0528-3",      # Azure 85409
    "Llama-3.3-70B-Instruct-2", # Azure 85409
    "Llama-3.3-70B-Instruct-3", # Azure 85409
]

# IdealLab的额外模型
ADDITIONAL_IDEALAB_MODELS = [
    "gpt-41-0414-global",      # IdealLab
    "o1-1217-global",          # IdealLab
    "o4-mini-0416-global",     # IdealLab
    "claude37_sonnet",         # IdealLab
    "claude_opus4",            # IdealLab
    "gemini-2.5-pro-06-17",    # IdealLab
    "gemini-1.5-pro",          # IdealLab
    "gemini-2.0-flash",        # IdealLab
    "deepseek-v3-671b",        # IdealLab
    "deepseek-r1-671b",        # IdealLab
    "DeepSeek-V3-671B",        # IdealLab
    "DeepSeek-R1-671B",        # IdealLab
    "qwen2.5-max",             # IdealLab
]

class DualLogger:
    """同时输出到控制台和文件的日志器"""
    def __init__(self, log_file):
        self.terminal = sys.stdout
        self.log = open(log_file, 'w', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()
    
    def flush(self):
        self.terminal.flush()
        self.log.flush()
    
    def close(self):
        self.log.close()

def test_model_api(model_name: str, prompt_type: str = "baseline", timeout: int = 30):
    """测试单个模型的API连接"""
    result = {
        "model": model_name,
        "status": "unknown",
        "response_time": None,
        "error": None,
        "provider": None,
        "response": None
    }
    
    start = time.time()
    try:
        # 获取客户端
        client = get_client_for_model(model_name, prompt_type)
        api_model_name = get_api_model_name(model_name)
        
        # 判断provider
        if hasattr(client, '_base_url'):
            base_url = str(client._base_url)
            if '85409' in base_url:
                result["provider"] = "Azure (85409)"
            elif 'aixplore' in base_url:
                result["provider"] = "Azure (France)"
            elif 'archer222' in base_url:
                result["provider"] = "Azure (Archer)"
            elif 'idealab' in base_url:
                result["provider"] = "IdealLab"
            else:
                result["provider"] = f"Unknown ({base_url[:30]}...)"
        
        # 构建请求参数
        request_params = {
            "model": api_model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: Hello World"}
            ],
            "timeout": timeout
        }
        
        # 特殊处理：gpt-5系列不支持某些参数
        if 'gpt-5' not in model_name.lower():
            request_params["temperature"] = 0.1
            request_params["max_tokens"] = 100
        
        # 发送请求
        response = client.chat.completions.create(**request_params)
        
        elapsed = time.time() - start
        result["status"] = "✅ Success"
        result["response_time"] = round(elapsed, 2)
        
        # 获取响应内容
        if response.choices and len(response.choices) > 0:
            result["response"] = response.choices[0].message.content[:50]
        
    except Exception as e:
        elapsed = time.time() - start
        result["status"] = "❌ Failed"
        result["response_time"] = round(elapsed, 2)
        result["error"] = str(e)[:100]  # 截断错误信息
    
    return result

def main():
    """主函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"all_models_test_{timestamp}.log"
    report_file = LOG_DIR / f"all_models_report_{timestamp}.md"
    
    # 设置双重输出
    logger = DualLogger(log_file)
    old_stdout = sys.stdout
    sys.stdout = logger
    
    try:
        print("="*80)
        print("完整模型API测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"日志文件: {log_file}")
        print("="*80)
        
        all_results = []
        
        # 1. 测试bash脚本中的开源模型
        print("\n## 1. Bash脚本开源模型测试")
        print("-"*60)
        for model in OPENSOURCE_MODELS:
            print(f"测试 {model}...", end=" ")
            result = test_model_api(model)
            print(f"{result['status']} ({result['response_time']}s)")
            all_results.append(("Bash开源", model, result))
        
        # 2. 测试bash脚本中的闭源模型
        print("\n## 2. Bash脚本闭源模型测试")
        print("-"*60)
        for model in CLOSED_SOURCE_MODELS:
            print(f"测试 {model}...", end=" ")
            result = test_model_api(model)
            print(f"{result['status']} ({result['response_time']}s)")
            all_results.append(("Bash闭源", model, result))
        
        # 3. 测试额外的Azure模型
        print("\n## 3. 额外Azure模型测试")
        print("-"*60)
        for model in ADDITIONAL_AZURE_MODELS:
            print(f"测试 {model}...", end=" ")
            result = test_model_api(model)
            print(f"{result['status']} ({result['response_time']}s)")
            all_results.append(("额外Azure", model, result))
        
        # 4. 测试额外的IdealLab模型
        print("\n## 4. 额外IdealLab模型测试")
        print("-"*60)
        for model in ADDITIONAL_IDEALAB_MODELS:
            print(f"测试 {model}...", end=" ")
            result = test_model_api(model)
            print(f"{result['status']} ({result['response_time']}s)")
            all_results.append(("额外IdealLab", model, result))
        
        # 生成Markdown报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 完整模型API测试报告\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 按类别整理结果
            categories = {}
            for category, model, result in all_results:
                if category not in categories:
                    categories[category] = []
                categories[category].append((model, result))
            
            # 统计
            total_models = len(all_results)
            success_count = sum(1 for _, _, r in all_results if "Success" in r["status"])
            
            f.write("## 测试统计\n\n")
            f.write(f"- 总模型数: {total_models}\n")
            f.write(f"- 成功: {success_count}\n")
            f.write(f"- 失败: {total_models - success_count}\n")
            f.write(f"- 成功率: {success_count/total_models*100:.1f}%\n\n")
            
            # 详细结果
            for category, models in categories.items():
                f.write(f"## {category}\n\n")
                f.write("| 模型 | 状态 | 响应时间(秒) | Provider | 错误信息 |\n")
                f.write("|------|------|-------------|----------|----------|\n")
                
                for model, result in models:
                    error_msg = result['error'] if result['error'] else "-"
                    provider = result['provider'] if result['provider'] else "Unknown"
                    f.write(f"| {model} | {result['status']} | {result['response_time']} | {provider} | {error_msg} |\n")
                f.write("\n")
        
        # 总结
        print("\n" + "="*80)
        print("测试总结")
        print("-"*80)
        print(f"总计测试: {total_models} 个模型")
        print(f"成功: {success_count} 个")
        print(f"失败: {total_models - success_count} 个")
        print(f"成功率: {success_count/total_models*100:.1f}%")
        
        # 失败的模型列表
        failed_models = [model for _, model, r in all_results if "Failed" in r["status"]]
        if failed_models:
            print(f"\n失败的模型:")
            for model in failed_models:
                print(f"  - {model}")
        
        print(f"\n📊 测试报告已保存到: {report_file}")
        
    finally:
        # 恢复标准输出
        sys.stdout = old_stdout
        logger.close()
        print(f"📝 完整日志已保存到: {log_file}")
        print(f"📊 测试报告已保存到: {report_file}")

if __name__ == "__main__":
    main()