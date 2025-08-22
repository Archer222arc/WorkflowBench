#!/usr/bin/env python3
"""
模型API连接测试工具
快速验证所有模型的API连接是否正常
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any

def test_model_connections():
    """测试所有模型的API连接"""
    
    # 从配置中获取模型列表
    config_path = Path("config/config.json")
    if not config_path.exists():
        print("❌ 找不到配置文件: config/config.json")
        return
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    models = config.get("supported_models", [])
    if not models:
        print("❌ 配置文件中没有找到支持的模型列表")
        return
    
    print("🧪 开始测试模型API连接...")
    print(f"📋 共 {len(models)} 个模型需要测试")
    print("=" * 60)
    
    results = []
    
    for i, model in enumerate(models, 1):
        print(f"\n[{i}/{len(models)}] 测试模型: {model}")
        print("-" * 40)
        
        try:
            # 导入API客户端管理器
            from api_client_manager import get_client_for_model
            
            # 获取客户端
            start_time = time.time()
            client = get_client_for_model(model)
            
            if not client:
                results.append((model, "❌ 连接失败", "无法获取客户端", 0))
                print(f"❌ {model}: 无法获取客户端")
                continue
            
            # 测试简单的API调用
            test_prompt = "请简单回答：1+1等于几？"
            
            try:
                if hasattr(client, 'is_gpt5_nano') and client.is_gpt5_nano:
                    # GPT-5 Nano客户端
                    response = client.chat.completions.create(
                        messages=[{"role": "user", "content": test_prompt}],
                        model=model
                    )
                else:
                    # 标准OpenAI兼容客户端
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": test_prompt}],
                        max_tokens=50,
                        temperature=0.1
                    )
                
                response_time = time.time() - start_time
                
                if response and response.choices and len(response.choices) > 0:
                    answer = response.choices[0].message.content.strip()
                    results.append((model, "✅ 连接成功", answer[:50], response_time))
                    print(f"✅ {model}: 连接成功 ({response_time:.2f}s)")
                    print(f"   响应: {answer[:50]}...")
                else:
                    results.append((model, "⚠️  响应异常", "空响应", response_time))
                    print(f"⚠️  {model}: 响应异常 - 空响应")
                    
            except Exception as api_error:
                response_time = time.time() - start_time
                error_msg = str(api_error)
                results.append((model, "❌ API错误", error_msg[:50], response_time))
                print(f"❌ {model}: API调用失败")
                print(f"   错误: {error_msg}")
                
        except ImportError as e:
            results.append((model, "❌ 导入错误", str(e)[:50], 0))
            print(f"❌ {model}: 导入API客户端失败 - {e}")
            
        except Exception as e:
            results.append((model, "❌ 未知错误", str(e)[:50], 0))
            print(f"❌ {model}: 未知错误 - {e}")
    
    # 输出测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    successful = sum(1 for r in results if "成功" in r[1])
    failed = len(results) - successful
    
    print(f"✅ 成功: {successful}/{len(results)} 个模型")
    print(f"❌ 失败: {failed}/{len(results)} 个模型")
    print()
    
    # 详细结果表格
    print("模型测试详情:")
    print("-" * 60)
    print(f"{'模型名称':<25} {'状态':<12} {'响应时间':<10}")
    print("-" * 60)
    
    for model, status, response, time_taken in results:
        time_str = f"{time_taken:.2f}s" if time_taken > 0 else "N/A"
        print(f"{model:<25} {status:<12} {time_str:<10}")
    
    # 失败详情
    failed_models = [r for r in results if "成功" not in r[1]]
    if failed_models:
        print("\n" + "=" * 60)
        print("❌ 失败详情:")
        print("=" * 60)
        for model, status, error, _ in failed_models:
            print(f"• {model}: {status}")
            if error and error != "N/A":
                print(f"  └─ {error}")
    
    # 成功模型列表（用于后续测试）
    successful_models = [r[0] for r in results if "成功" in r[1]]
    if successful_models:
        print("\n" + "=" * 60)
        print("✅ 可用模型列表 (可以开始测试):")
        print("=" * 60)
        for model in successful_models:
            print(f"  • {model}")
        
        # 保存可用模型列表
        available_models_file = Path("available_models.json")
        with open(available_models_file, 'w') as f:
            json.dump({
                "tested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "available_models": successful_models,
                "total_tested": len(results),
                "success_rate": f"{successful}/{len(results)}"
            }, f, indent=2)
        
        print(f"\n📄 可用模型列表已保存到: {available_models_file}")
    
    return results


def test_specific_models(model_names: List[str]):
    """测试指定的模型列表"""
    print(f"🎯 测试指定模型: {', '.join(model_names)}")
    
    # 临时修改配置只测试指定模型
    config_path = Path("config/config.json")
    if config_path.exists():
        with open(config_path, 'r') as f:
            original_config = json.load(f)
        
        # 备份原配置
        backup_config = original_config.copy()
        backup_config["models"] = model_names
        
        # 临时写入新配置
        with open(config_path, 'w') as f:
            json.dump(backup_config, f, indent=2)
        
        try:
            # 运行测试
            results = test_model_connections()
        finally:
            # 恢复原配置
            with open(config_path, 'w') as f:
                json.dump(original_config, f, indent=2)
        
        return results
    else:
        print("❌ 找不到配置文件")
        return []


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="测试模型API连接")
    parser.add_argument("--models", nargs="+", help="指定要测试的模型名称")
    parser.add_argument("--baseline-only", action="store_true", help="只测试基线模型")
    
    args = parser.parse_args()
    
    if args.baseline_only:
        # 只测试几个主要模型
        baseline_models = [
            "gpt-4o-mini",
            "qwen2.5-7b-instruct", 
            "DeepSeek-V3-0324",
            "Llama-3.3-70B-Instruct"
        ]
        test_specific_models(baseline_models)
    elif args.models:
        test_specific_models(args.models)
    else:
        test_model_connections()


if __name__ == "__main__":
    main()