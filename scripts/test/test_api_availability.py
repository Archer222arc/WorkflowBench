#!/usr/bin/env python3
"""
完整的API可用性测试脚本
测试所有闭源和开源模型的API连接状态
"""

import time
import sys
from datetime import datetime
from api_client_manager import get_client_for_model, get_api_model_name

# 闭源模型列表
CLOSED_SOURCE_MODELS = [
    "gpt-4o-mini",                # Azure
    "gpt-5-mini",                 # Azure (可能不存在)
    "grok-3-mini",                # Azure (可能不存在)
    "claude_sonnet4",             # IdealLab
    "o3-0416-global",             # IdealLab
    "gemini-2.5-flash-06-17",     # IdealLab
]

# 开源模型列表（部分）
OPENSOURCE_MODELS = [
    "qwen2.5-72b-instruct",
    "qwen2.5-32b-instruct",
    "deepseek-v3-671b",
    "llama-3.1-nemotron-70b-instruct",
]

def test_model_api(model_name, timeout=10):
    """测试单个模型的API连接"""
    result = {
        'model': model_name,
        'status': 'unknown',
        'response_time': None,
        'error': None,
        'api_name': None,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # 获取客户端和API模型名
        print(f"\n测试模型: {model_name}")
        print("-" * 50)
        
        client = get_client_for_model(model_name)
        api_model = get_api_model_name(model_name)
        result['api_name'] = api_model
        
        print(f"  API模型名: {api_model}")
        print(f"  开始测试连接...")
        
        # 测试API调用
        start = time.time()
        response = client.chat.completions.create(
            model=api_model,
            messages=[{'role': 'user', 'content': 'Say "test" in one word'}],
            timeout=timeout
        )
        elapsed = time.time() - start
        
        result['response_time'] = elapsed
        result['status'] = 'success'
        
        print(f"  ✓ 成功！响应时间: {elapsed:.2f}秒")
        
        # 显示响应内容
        if response and response.choices:
            content = response.choices[0].message.content
            print(f"  响应内容: {content[:50]}")
            
    except Exception as e:
        error_msg = str(e)
        result['status'] = 'failed'
        result['error'] = error_msg
        
        # 分析错误类型
        if 'Error code: 400' in error_msg:
            if '模型不存在' in error_msg:
                print(f"  ✗ 错误: 模型不存在")
                result['error_type'] = 'model_not_found'
            elif '资源限制' in error_msg or 'IRC-001' in error_msg:
                print(f"  ✗ 错误: 无权限访问此模型")
                result['error_type'] = 'permission_denied'
            else:
                print(f"  ✗ 错误: 请求格式错误")
                result['error_type'] = 'bad_request'
                
        elif 'Error code: 401' in error_msg:
            print(f"  ✗ 错误: API密钥无效")
            result['error_type'] = 'invalid_api_key'
            
        elif 'Error code: 429' in error_msg:
            print(f"  ✗ 错误: 请求频率过高")
            result['error_type'] = 'rate_limit'
            
        elif 'timeout' in error_msg.lower():
            print(f"  ✗ 错误: 请求超时 ({timeout}秒)")
            result['error_type'] = 'timeout'
            
        elif 'connection' in error_msg.lower():
            print(f"  ✗ 错误: 网络连接失败")
            result['error_type'] = 'connection_error'
            
        else:
            print(f"  ✗ 错误: {error_msg[:100]}")
            result['error_type'] = 'unknown'
            
        # 显示详细错误信息
        if len(error_msg) > 100:
            print(f"  详细信息: {error_msg[:200]}...")
    
    return result

def main():
    """主测试函数"""
    print("=" * 60)
    print("API可用性完整测试")
    print("=" * 60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 测试闭源模型
    print("\n" + "=" * 60)
    print("闭源模型测试")
    print("=" * 60)
    
    closed_results = []
    for model in CLOSED_SOURCE_MODELS:
        result = test_model_api(model, timeout=10)
        closed_results.append(result)
        time.sleep(0.5)  # 避免请求过快
    
    # 测试开源模型
    print("\n" + "=" * 60)
    print("开源模型测试（示例）")
    print("=" * 60)
    
    open_results = []
    for model in OPENSOURCE_MODELS:
        result = test_model_api(model, timeout=10)
        open_results.append(result)
        time.sleep(0.5)
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    print("\n闭源模型:")
    success_count = 0
    for result in closed_results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        time_str = f"{result['response_time']:.2f}s" if result['response_time'] else "N/A"
        print(f"  {status_icon} {result['model']:30} - {result['status']:10} - {time_str}")
        if result['status'] == 'success':
            success_count += 1
    
    print(f"\n  成功率: {success_count}/{len(closed_results)} ({success_count*100/len(closed_results):.1f}%)")
    
    print("\n开源模型:")
    success_count = 0
    for result in open_results:
        status_icon = "✓" if result['status'] == 'success' else "✗"
        time_str = f"{result['response_time']:.2f}s" if result['response_time'] else "N/A"
        print(f"  {status_icon} {result['model']:30} - {result['status']:10} - {time_str}")
        if result['status'] == 'success':
            success_count += 1
    
    print(f"\n  成功率: {success_count}/{len(open_results)} ({success_count*100/len(open_results) if open_results else 0:.1f}%)")
    
    # 保存详细结果到文件
    import json
    with open('api_test_results.json', 'w') as f:
        json.dump({
            'test_time': datetime.now().isoformat(),
            'closed_source': closed_results,
            'open_source': open_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n详细结果已保存到: api_test_results.json")
    
    # 返回是否有失败
    all_results = closed_results + open_results
    failed_count = sum(1 for r in all_results if r['status'] != 'success')
    return failed_count

if __name__ == "__main__":
    failed = main()
    sys.exit(failed)