#!/usr/bin/env python3
"""
详细API测试脚本 - 显示完整的请求和响应信息并保存日志
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

def test_model_detailed(model_name: str, prompt_type: str = "baseline"):
    """详细测试单个模型"""
    print(f"\n{'='*60}")
    print(f"测试模型: {model_name}")
    print(f"Prompt类型: {prompt_type}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('-'*60)
    
    try:
        # 1. 获取客户端
        print(f"[1] 获取API客户端...")
        start = time.time()
        client = get_client_for_model(model_name, prompt_type)
        elapsed = time.time() - start
        print(f"    ✓ 客户端获取成功 ({elapsed:.3f}s)")
        print(f"    客户端类型: {type(client).__name__}")
        
        # 检查是否是Azure客户端
        if hasattr(client, '_base_url'):
            print(f"    Base URL: {client._base_url}")
        
        # 2. 获取API模型名
        print(f"[2] 获取API模型名...")
        api_model_name = get_api_model_name(model_name)
        print(f"    原始模型名: {model_name}")
        print(f"    API模型名: {api_model_name}")
        
        # 3. 构建请求
        print(f"[3] 构建API请求...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Reply with exactly: Hello World"}
        ]
        
        request_params = {
            "model": api_model_name,
            "messages": messages
        }
        
        print(f"    请求参数:")
        print(f"      model: {api_model_name}")
        print(f"      messages: {len(messages)} 条")
        print(f"      timeout: 60秒")
        
        # 4. 发送请求
        print(f"[4] 发送API请求...")
        start = time.time()
        response = client.chat.completions.create(**request_params, timeout=60)
        elapsed = time.time() - start
        print(f"    ✓ 请求成功 ({elapsed:.3f}s)")
        
        # 5. 解析响应
        print(f"[5] 解析响应...")
        content = response.choices[0].message.content
        print(f"    响应内容: '{content}'")
        
        # 响应元数据
        if hasattr(response, 'usage'):
            print(f"    Token使用:")
            if hasattr(response.usage, 'prompt_tokens'):
                print(f"      Prompt tokens: {response.usage.prompt_tokens}")
            if hasattr(response.usage, 'completion_tokens'):
                print(f"      Completion tokens: {response.usage.completion_tokens}")
            if hasattr(response.usage, 'total_tokens'):
                print(f"      Total tokens: {response.usage.total_tokens}")
        
        if hasattr(response, 'model'):
            print(f"    实际使用模型: {response.model}")
        
        print(f"\n✅ 测试成功！总耗时: {elapsed:.3f}秒")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败!")
        print(f"    错误类型: {type(e).__name__}")
        print(f"    错误消息: {str(e)}")
        print(f"\n    详细错误追踪:")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    # 创建日志文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"api_test_{timestamp}.log"
    
    # 设置双重输出
    logger = DualLogger(log_file)
    old_stdout = sys.stdout
    sys.stdout = logger
    
    try:
        print("="*80)
        print("详细API测试 - 完整日志")
        print(f"日志文件: {log_file}")
        print("="*80)
        
        # 测试bash脚本中定义的所有模型
        # 从run_systematic_test_final.sh中提取的模型列表
        
        # 开源模型（来自OPENSOURCE_MODELS数组）
        opensource_models = [
            "DeepSeek-V3-0324",       # Azure 85409
            "DeepSeek-R1-0528",       # Azure 85409
            "qwen2.5-72b-instruct",   # IdealLab
            "qwen2.5-32b-instruct",   # IdealLab
            "qwen2.5-14b-instruct",   # IdealLab
            "qwen2.5-7b-instruct",    # IdealLab
            "qwen2.5-3b-instruct",    # IdealLab
            "Llama-3.3-70B-Instruct", # Azure 85409
        ]
        
        # 闭源模型（来自CLOSED_SOURCE_MODELS数组）
        closed_source_models = [
            "gpt-4o-mini",             # Azure
            "gpt-5-mini",              # Azure 85409
            "o3-0416-global",          # IdealLab
            "gemini-2.5-flash-06-17",  # IdealLab
            "kimi-k2",                 # IdealLab
            "claude_sonnet4",          # IdealLab
        ]
        
        # 合并所有模型
        all_bash_models = opensource_models + closed_source_models
        
        print(f"从bash脚本中找到的模型:")
        print(f"  - 开源模型: {len(opensource_models)} 个")
        print(f"  - 闭源模型: {len(closed_source_models)} 个")
        print(f"  - 总计: {len(all_bash_models)} 个模型")
        print("-"*80)
        
        # 为每个模型创建测试条目
        test_models = [(model, "baseline") for model in all_bash_models]
        
        success_count = 0
        failed_models = []
        
        for model, prompt_type in test_models:
            if test_model_detailed(model, prompt_type):
                success_count += 1
            else:
                failed_models.append(model)
    
        # 总结
        print("\n" + "="*80)
        print("测试总结")
        print("-"*80)
        print(f"成功: {success_count}/{len(test_models)}")
        if failed_models:
            print(f"失败的模型: {', '.join(failed_models)}")
        else:
            print("✅ 所有模型测试通过！")
        
        print(f"\n日志已保存到: {log_file}")
        
    finally:
        # 恢复标准输出
        sys.stdout = old_stdout
        logger.close()
        print(f"\n📝 日志已保存到: {log_file}")

if __name__ == "__main__":
    main()