#!/usr/bin/env python3
"""
全面API连接测试脚本
完全模拟bash脚本的调用链
"""

import time
import json
from api_client_manager import get_client_for_model, get_api_model_name

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

def test_model_api(model_name: str, prompt_type: str = "baseline") -> dict:
    """测试单个模型的API连接 - 完全模拟InteractiveExecutor的调用方式"""
    result = {
        "model": model_name,
        "prompt_type": prompt_type,
        "status": "unknown",
        "response_time": None,
        "error": None,
        "warning": None
    }
    
    start = time.time()
    try:
        # 完全模拟InteractiveExecutor的调用方式
        # 1. 获取客户端（传递prompt_type用于IdealLab key选择）
        client = get_client_for_model(model_name, prompt_type)
        
        # 2. 获取API模型名
        api_model_name = get_api_model_name(model_name)
        
        # 3. 构建请求参数 - 完全模拟InteractiveExecutor第1189行的调用
        # InteractiveExecutor不设置max_tokens和temperature
        request_params = {
            "model": api_model_name,
            "messages": [{"role": "user", "content": "Reply with OK"}]
        }
        
        # 4. 发送测试请求（带60秒超时，与InteractiveExecutor一致）
        response = client.chat.completions.create(**request_params, timeout=60)
        
        elapsed = time.time() - start
        result["status"] = "success"
        result["response_time"] = round(elapsed, 2)
        
        # 检查响应内容
        content = response.choices[0].message.content
        if not content or content.strip() == "":
            result["warning"] = "Empty response content"
            
    except Exception as e:
        elapsed = time.time() - start
        result["status"] = "failed"
        result["response_time"] = round(elapsed, 2)
        result["error"] = str(e)
        
        # 特殊错误检查
        if "max_tokens" in str(e):
            result["warning"] = "Model doesn't support max_tokens parameter"
        elif "temperature" in str(e):
            result["warning"] = "Model doesn't support temperature parameter"
    
    return result

def main():
    """主测试函数"""
    print("=" * 60)
    print("全面API连接测试（模拟实际批测试调用）")
    print("=" * 60)
    
    # 测试开源模型
    print("\n📊 开源模型测试")
    print("-" * 40)
    opensource_results = []
    for model in OPENSOURCE_MODELS:
        print(f"测试 {model}...", end=" ")
        # 使用baseline prompt_type测试（模拟批测试的默认行为）
        result = test_model_api(model, prompt_type="baseline")
        opensource_results.append(result)
        
        if result["status"] == "success":
            print(f"✅ 成功 ({result['response_time']}s)")
            if result["warning"]:
                print(f"  ⚠️  {result['warning']}")
        else:
            print(f"❌ 失败")
            print(f"  错误: {result['error']}")
    
    # 测试闭源模型
    print("\n📊 闭源模型测试")
    print("-" * 40)
    closed_results = []
    for model in CLOSED_SOURCE_MODELS:
        print(f"测试 {model}...", end=" ")
        # 闭源模型也使用baseline
        result = test_model_api(model, prompt_type="baseline")
        closed_results.append(result)
        
        if result["status"] == "success":
            print(f"✅ 成功 ({result['response_time']}s)")
            if result["warning"]:
                print(f"  ⚠️  {result['warning']}")
        else:
            print(f"❌ 失败")
            print(f"  错误: {result['error']}")
    
    # 统计结果
    print("\n" + "=" * 60)
    print("📈 测试统计")
    print("-" * 40)
    
    # 开源模型统计
    opensource_success = sum(1 for r in opensource_results if r["status"] == "success")
    print(f"开源模型: {opensource_success}/{len(OPENSOURCE_MODELS)} 成功")
    if opensource_success < len(OPENSOURCE_MODELS):
        failed = [r["model"] for r in opensource_results if r["status"] == "failed"]
        print(f"  失败: {', '.join(failed)}")
    
    # 闭源模型统计
    closed_success = sum(1 for r in closed_results if r["status"] == "success")
    print(f"闭源模型: {closed_success}/{len(CLOSED_SOURCE_MODELS)} 成功")
    if closed_success < len(CLOSED_SOURCE_MODELS):
        failed = [r["model"] for r in closed_results if r["status"] == "failed"]
        print(f"  失败: {', '.join(failed)}")
    
    # 性能统计
    all_results = opensource_results + closed_results
    success_results = [r for r in all_results if r["status"] == "success"]
    if success_results:
        avg_time = sum(r["response_time"] for r in success_results) / len(success_results)
        max_time = max(r["response_time"] for r in success_results)
        min_time = min(r["response_time"] for r in success_results)
        
        print(f"\n响应时间统计:")
        print(f"  平均: {avg_time:.2f}s")
        print(f"  最快: {min_time:.2f}s")
        print(f"  最慢: {max_time:.2f}s")
        
        # 找出最慢的模型
        slowest = max(success_results, key=lambda x: x["response_time"])
        if slowest["response_time"] > 5:
            print(f"  ⚠️  {slowest['model']} 响应较慢 ({slowest['response_time']}s)")
    
    # 警告汇总
    warnings = [r for r in all_results if r.get("warning")]
    if warnings:
        print(f"\n⚠️  警告汇总:")
        for r in warnings:
            print(f"  {r['model']}: {r['warning']}")
    
    print("\n" + "=" * 60)
    
    # 返回是否所有测试都成功
    total_success = opensource_success + closed_success
    total_models = len(OPENSOURCE_MODELS) + len(CLOSED_SOURCE_MODELS)
    
    if total_success == total_models:
        print("✅ 所有API测试通过！")
        return 0
    else:
        print(f"⚠️  {total_models - total_success} 个模型API测试失败")
        return 1

if __name__ == "__main__":
    exit(main())