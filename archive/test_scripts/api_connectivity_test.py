#!/usr/bin/env python3
"""
API连通性测试脚本
测试所有模型的API端点是否正常，检查404、400等错误
"""

import json
import asyncio
import aiohttp
import time
from pathlib import Path
import sys

# 模型配置
MODELS_CONFIG = {
    "azure_models": {
        # 开源模型
        "DeepSeek-V3-0324": "DeepSeek-V3-0324",
        "DeepSeek-R1-0528": "DeepSeek-R1-0528", 
        "Llama-3.3-70B-Instruct": "Llama-3.3-70B-Instruct",
        # 闭源模型
        "gpt-4o-mini": "gpt-4o-mini",
        "gpt-5-mini": "gpt-5-mini"
    },
    "idealab_models": {
        # 开源模型
        "qwen2.5-72b-instruct": "qwen2.5-72b-instruct",
        "qwen2.5-32b-instruct": "qwen2.5-32b-instruct", 
        "qwen2.5-14b-instruct": "qwen2.5-14b-instruct",
        "qwen2.5-7b-instruct": "qwen2.5-7b-instruct",
        "qwen2.5-3b-instruct": "qwen2.5-3b-instruct",
        # 闭源模型
        "o3-0416-global": "o3-0416-global",
        "gemini-2.5-flash-06-17": "gemini-2.5-flash-06-17",
        "kimi-k2": "kimi-k2"
    }
}

class APITester:
    def __init__(self):
        self.config = self.load_config()
        self.results = {}
        
    def load_config(self):
        """加载配置文件"""
        config_path = Path("config/config.json")
        if not config_path.exists():
            raise FileNotFoundError("config/config.json not found")
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    async def test_azure_model(self, session, model_name, deployment_name):
        """测试Azure模型"""
        try:
            # 检查是否使用新的Azure配置
            azure_config_path = Path("config/azure_models_config.json")
            if azure_config_path.exists():
                with open(azure_config_path, 'r') as f:
                    azure_config = json.load(f)
                
                # 查找模型在新配置中的endpoint
                for endpoint_name, endpoint_config in azure_config["azure_endpoints"].items():
                    if model_name in endpoint_config["models"]:
                        base_url = endpoint_config["endpoint"]
                        api_key = endpoint_config["api_key"]
                        api_version = endpoint_config.get("api_version", "2024-02-15-preview")
                        break
                else:
                    # 回退到默认配置
                    base_url = self.config["azure_openai_api_base"]
                    api_key = self.config["azure_openai_api_key"]
                    api_version = "2024-12-01-preview"
            else:
                base_url = self.config["azure_openai_api_base"]
                api_key = self.config["azure_openai_api_key"]
                api_version = "2024-12-01-preview"
            
            url = f"{base_url}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
            
            headers = {
                "Content-Type": "application/json",
                "api-key": api_key
            }
            
            # 简单测试请求
            # gpt-5系列模型需要使用max_completion_tokens和temperature=1
            if "gpt-5" in model_name.lower():
                payload = {
                    "messages": [{"role": "user", "content": "Hello, test connection"}],
                    "max_completion_tokens": 10,
                    "temperature": 1  # gpt-5只支持默认值1
                }
            else:
                payload = {
                    "messages": [{"role": "user", "content": "Hello, test connection"}],
                    "max_tokens": 10,
                    "temperature": 0
                }
            
            # Llama模型响应较慢，给更长超时
            timeout_seconds = 60 if "llama" in model_name.lower() else 30
            start_time = time.time()
            async with session.post(url, headers=headers, json=payload, timeout=timeout_seconds) as response:
                response_time = time.time() - start_time
                
                status = response.status
                if status == 200:
                    data = await response.json()
                    return {
                        "status": "✅ SUCCESS",
                        "http_code": status,
                        "response_time": f"{response_time:.2f}s",
                        "has_choices": len(data.get("choices", [])) > 0,
                        "error": None
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "❌ FAILED",
                        "http_code": status,
                        "response_time": f"{response_time:.2f}s",
                        "error": error_text[:200] + "..." if len(error_text) > 200 else error_text
                    }
                    
        except asyncio.TimeoutError:
            return {
                "status": "⏰ TIMEOUT",
                "http_code": "N/A",
                "response_time": ">30s",
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "status": "💥 ERROR",
                "http_code": "N/A", 
                "response_time": "N/A",
                "error": str(e)
            }
    
    async def test_idealab_model(self, session, model_name):
        """测试IdealLab模型"""
        try:
            # 构建IdealLab URL
            base_url = self.config["idealab_api_base"]
            url = f"{base_url}/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['idealab_api_key']}"
            }
            
            # 简单测试请求
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "Hello, test connection"}],
                "max_tokens": 10,
                "temperature": 0
            }
            
            start_time = time.time()
            async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                response_time = time.time() - start_time
                
                status = response.status
                if status == 200:
                    data = await response.json()
                    return {
                        "status": "✅ SUCCESS", 
                        "http_code": status,
                        "response_time": f"{response_time:.2f}s",
                        "has_choices": len(data.get("choices", [])) > 0,
                        "error": None
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "❌ FAILED",
                        "http_code": status,
                        "response_time": f"{response_time:.2f}s", 
                        "error": error_text[:200] + "..." if len(error_text) > 200 else error_text
                    }
                    
        except asyncio.TimeoutError:
            return {
                "status": "⏰ TIMEOUT",
                "http_code": "N/A",
                "response_time": ">30s",
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "status": "💥 ERROR",
                "http_code": "N/A",
                "response_time": "N/A", 
                "error": str(e)
            }
    
    async def run_tests(self):
        """运行所有测试"""
        print("🚀 开始API连通性测试...")
        print("=" * 80)
        
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            
            # 测试Azure模型
            print("📋 Azure OpenAI 模型测试:")
            for model_name, deployment_name in MODELS_CONFIG["azure_models"].items():
                task = self.test_azure_model(session, model_name, deployment_name)
                tasks.append(("azure", model_name, task))
            
            # 测试IdealLab模型  
            print("📋 IdealLab 模型测试:")
            for model_name in MODELS_CONFIG["idealab_models"].keys():
                task = self.test_idealab_model(session, model_name)
                tasks.append(("ideallab", model_name, task))
            
            # 并发执行所有测试
            results = []
            for provider, model_name, task in tasks:
                try:
                    result = await task
                    results.append((provider, model_name, result))
                    
                    # 实时显示结果
                    status_icon = result["status"].split()[0]
                    print(f"  {status_icon} {model_name:25} | HTTP:{result['http_code']:3} | {result['response_time']:>6} | {provider}")
                    if result["error"]:
                        print(f"      ⚠️  Error: {result['error']}")
                        
                except Exception as e:
                    results.append((provider, model_name, {
                        "status": "💥 ERROR",
                        "http_code": "N/A",
                        "response_time": "N/A",
                        "error": str(e)
                    }))
                    print(f"  💥 {model_name:25} | FAILED | {provider} | Error: {str(e)}")
        
        # 生成测试报告
        self.generate_report(results)
        return results
    
    def generate_report(self, results):
        """生成测试报告"""
        print("\n" + "=" * 80)
        print("📊 API连通性测试报告")
        print("=" * 80)
        
        # 统计结果
        total_tests = len(results)
        success_tests = len([r for _, _, r in results if "SUCCESS" in r["status"]])
        failed_tests = len([r for _, _, r in results if "FAILED" in r["status"]])
        timeout_tests = len([r for _, _, r in results if "TIMEOUT" in r["status"]])
        error_tests = len([r for _, _, r in results if "ERROR" in r["status"]])
        
        print(f"✅ 成功: {success_tests}/{total_tests}")
        print(f"❌ 失败: {failed_tests}/{total_tests}")
        print(f"⏰ 超时: {timeout_tests}/{total_tests}")
        print(f"💥 错误: {error_tests}/{total_tests}")
        print(f"📈 成功率: {success_tests/total_tests*100:.1f}%")
        
        # 按提供商分组显示
        azure_results = [(m, r) for p, m, r in results if p == "azure"]
        ideallab_results = [(m, r) for p, m, r in results if p == "ideallab"]
        
        print(f"\n🔵 Azure OpenAI ({len(azure_results)}个模型):")
        for model_name, result in azure_results:
            status_icon = result["status"].split()[0]
            print(f"  {status_icon} {model_name:25} | HTTP:{result['http_code']:3} | {result['response_time']:>6}")
            if result.get("error"):
                print(f"      ⚠️  {result['error']}")
        
        print(f"\n🟡 IdealLab ({len(ideallab_results)}个模型):")
        for model_name, result in ideallab_results:
            status_icon = result["status"].split()[0]
            print(f"  {status_icon} {model_name:25} | HTTP:{result['http_code']:3} | {result['response_time']:>6}")
            if result.get("error"):
                print(f"      ⚠️  {result['error']}")
        
        # 保存详细报告
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total": total_tests,
                "success": success_tests, 
                "failed": failed_tests,
                "timeout": timeout_tests,
                "error": error_tests,
                "success_rate": success_tests/total_tests*100
            },
            "details": results
        }
        
        report_file = f"api_connectivity_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 详细报告已保存: {report_file}")

async def main():
    """主函数"""
    tester = APITester()
    
    try:
        await tester.run_tests()
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"💥 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 检查依赖
    try:
        import aiohttp
    except ImportError:
        print("❌ 缺少依赖: pip install aiohttp")
        sys.exit(1)
    
    # 运行测试
    asyncio.run(main())