#!/usr/bin/env python3
"""
API测试汇总脚本 - 生成测试报告
"""

import time
import json
from datetime import datetime
from pathlib import Path
from api_client_manager import get_client_for_model, get_api_model_name

# 创建日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 从bash脚本中的模型列表
OPENSOURCE_MODELS = [
    "DeepSeek-V3-0324",
    "DeepSeek-R1-0528",
    "qwen2.5-72b-instruct",
    "qwen2.5-32b-instruct",
    "qwen2.5-14b-instruct",
    "qwen2.5-7b-instruct",
    "qwen2.5-3b-instruct",
    "Llama-3.3-70B-Instruct"
]

CLOSED_SOURCE_MODELS = [
    "gpt-4o-mini",
    "gpt-5-mini",
    "o3-0416-global",
    "gemini-2.5-flash-06-17",
    "kimi-k2",
    "claude_sonnet4"
]

def test_model_quick(model_name: str, prompt_type: str = "baseline") -> dict:
    """快速测试单个模型"""
    result = {
        "model": model_name,
        "status": "unknown",
        "response_time": None,
        "error": None,
        "provider": None
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
            elif 'idealab' in base_url:
                result["provider"] = "IdealLab"
            else:
                result["provider"] = "Unknown"
        else:
            result["provider"] = "Unknown"
        
        # 发送测试请求
        response = client.chat.completions.create(
            model=api_model_name,
            messages=[{"role": "user", "content": "Hi"}],
            timeout=30
        )
        
        elapsed = time.time() - start
        result["status"] = "✅ Success"
        result["response_time"] = round(elapsed, 2)
        
    except Exception as e:
        elapsed = time.time() - start
        result["status"] = "❌ Failed"
        result["response_time"] = round(elapsed, 2)
        result["error"] = str(e)[:50]  # 截断错误信息
    
    return result

def main():
    """主函数"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = LOG_DIR / f"api_test_report_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        # 写入标题
        f.write("# API测试报告\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 测试开源模型
        f.write("## 开源模型测试结果\n\n")
        f.write("| 模型 | 状态 | 响应时间(秒) | Provider | 错误信息 |\n")
        f.write("|------|------|-------------|----------|----------|\n")
        
        print("测试开源模型...")
        for model in OPENSOURCE_MODELS:
            print(f"  测试 {model}...")
            result = test_model_quick(model)
            error_msg = result['error'] if result['error'] else "-"
            f.write(f"| {model} | {result['status']} | {result['response_time']} | {result['provider']} | {error_msg} |\n")
        
        # 测试闭源模型
        f.write("\n## 闭源模型测试结果\n\n")
        f.write("| 模型 | 状态 | 响应时间(秒) | Provider | 错误信息 |\n")
        f.write("|------|------|-------------|----------|----------|\n")
        
        print("测试闭源模型...")
        for model in CLOSED_SOURCE_MODELS:
            print(f"  测试 {model}...")
            result = test_model_quick(model)
            error_msg = result['error'] if result['error'] else "-"
            f.write(f"| {model} | {result['status']} | {result['response_time']} | {result['provider']} | {error_msg} |\n")
        
        # 写入统计
        f.write("\n## 统计汇总\n\n")
        f.write(f"- 总模型数: {len(OPENSOURCE_MODELS) + len(CLOSED_SOURCE_MODELS)}\n")
        f.write(f"- 开源模型: {len(OPENSOURCE_MODELS)}个\n")
        f.write(f"- 闭源模型: {len(CLOSED_SOURCE_MODELS)}个\n")
        
        # 写入配置说明
        f.write("\n## 配置说明\n\n")
        f.write("### Azure (85409) 端点模型\n")
        f.write("- DeepSeek系列 (含3个并发实例)\n")
        f.write("- Llama-3.3 (含3个并发实例)\n")
        f.write("- GPT系列 (gpt-4o-mini, gpt-5-mini等)\n\n")
        
        f.write("### IdealLab 端点模型\n")
        f.write("- Qwen2.5全系列\n")
        f.write("- Claude系列\n")
        f.write("- Gemini系列\n")
        f.write("- Kimi-k2\n")
    
    print(f"\n✅ 测试报告已生成: {report_file}")
    
    # 同时在控制台显示报告
    with open(report_file, 'r', encoding='utf-8') as f:
        print("\n" + f.read())

if __name__ == "__main__":
    main()