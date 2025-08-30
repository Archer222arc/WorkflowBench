#!/usr/bin/env python3
"""
测试IdealLab API Keys的可用性
验证两个key是否都能正确调用API
"""

import os
import sys
import json
import time
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

class IdealLabKeyValidator:
    def __init__(self):
        """初始化IdealLab Key验证器"""
        self.api_base = "https://idealab.alibaba-inc.com/api/openai/v1"
        
        # 从不同来源获取API keys
        self.keys = self._get_api_keys()
        
        # 测试用的模型列表（优先测试轻量级模型）
        self.test_models = [
            "qwen2.5-3b-instruct",    # 轻量级，响应快
            "qwen2.5-7b-instruct",    # 中等规模
            "qwen2.5-14b-instruct",   # 稍大规模
        ]
        
        # 简单的测试提示
        self.test_prompt = "Hello, please respond with just the word 'OK' to confirm you are working."
        
        # 结果统计
        self.results = {}
        
    def _get_api_keys(self) -> Dict[int, str]:
        """从多个来源获取API keys"""
        keys = {}
        
        # 方式1：从环境变量获取
        for i in [0, 1]:
            env_key = f"IDEALLAB_API_KEY_{i}"
            if env_key in os.environ:
                keys[i] = os.environ[env_key]
                print(f"✅ 从环境变量获取 {env_key}")
        
        # 方式2：如果环境变量没有，从配置文件获取已知的keys
        if not keys:
            known_keys = [
                "956c41bd0f31beaf68b871d4987af4bb",  # Key 0
                "3d906058842b6cf4cee8aaa019f7e77b",  # Key 1
            ]
            for i, key in enumerate(known_keys):
                keys[i] = key
                print(f"⚠️ 使用硬编码key {i}: {key[:8]}...{key[-4:]}")
        
        print(f"\n🔍 找到 {len(keys)} 个IdealLab API keys")
        return keys
    
    async def test_single_key(self, key_index: int, api_key: str, model: str) -> Tuple[bool, str, dict]:
        """测试单个API key对特定模型的调用"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user", 
                    "content": self.test_prompt
                }
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    elapsed = time.time() - start_time
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                        
                        return True, f"成功 ({elapsed:.2f}s): {content.strip()}", {
                            'status_code': 200,
                            'response_time': elapsed,
                            'content': content.strip(),
                            'usage': result.get('usage', {})
                        }
                    else:
                        error_text = await response.text()
                        return False, f"HTTP {response.status}: {error_text[:100]}", {
                            'status_code': response.status,
                            'response_time': elapsed,
                            'error': error_text
                        }
        
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            return False, f"超时 ({elapsed:.2f}s)", {
                'status_code': 'timeout',
                'response_time': elapsed,
                'error': 'Request timeout'
            }
        except Exception as e:
            elapsed = time.time() - start_time
            return False, f"异常 ({elapsed:.2f}s): {str(e)}", {
                'status_code': 'error',
                'response_time': elapsed,
                'error': str(e)
            }
    
    async def validate_all_keys(self):
        """验证所有keys对所有测试模型的可用性"""
        print(f"\n🚀 开始验证 {len(self.keys)} 个API keys")
        print("=" * 80)
        
        for key_index, api_key in self.keys.items():
            print(f"\n🔑 测试 Key {key_index}: {api_key[:8]}...{api_key[-4:]}")
            print("-" * 60)
            
            key_results = {}
            
            for model in self.test_models:
                print(f"  📱 测试模型: {model}", end=" ... ", flush=True)
                
                success, message, details = await self.test_single_key(key_index, api_key, model)
                
                if success:
                    print(f"✅ {message}")
                else:
                    print(f"❌ {message}")
                
                key_results[model] = {
                    'success': success,
                    'message': message,
                    'details': details
                }
            
            self.results[f"key_{key_index}"] = key_results
    
    def generate_report(self):
        """生成详细的验证报告"""
        print(f"\n📊 IdealLab API Keys 验证报告")
        print("=" * 80)
        print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API Base: {self.api_base}")
        print(f"测试模型: {', '.join(self.test_models)}")
        
        # 按key统计
        print(f"\n🔑 Key级别统计:")
        for key_name, models_result in self.results.items():
            success_count = sum(1 for r in models_result.values() if r['success'])
            total_count = len(models_result)
            success_rate = success_count / total_count * 100 if total_count > 0 else 0
            
            status = "✅ 正常" if success_count == total_count else f"⚠️  {success_count}/{total_count}"
            print(f"  {key_name}: {status} ({success_rate:.1f}%)")
        
        # 按模型统计
        print(f"\n📱 模型级别统计:")
        for model in self.test_models:
            success_count = 0
            total_count = len(self.results)
            
            for key_results in self.results.values():
                if model in key_results and key_results[model]['success']:
                    success_count += 1
            
            success_rate = success_count / total_count * 100 if total_count > 0 else 0
            status = "✅ 全部key可用" if success_count == total_count else f"⚠️  {success_count}/{total_count}个key可用"
            print(f"  {model}: {status} ({success_rate:.1f}%)")
        
        # 详细错误信息
        print(f"\n❌ 错误详情:")
        has_errors = False
        for key_name, models_result in self.results.items():
            for model, result in models_result.items():
                if not result['success']:
                    has_errors = True
                    print(f"  {key_name} + {model}: {result['message']}")
        
        if not has_errors:
            print("  无错误 🎉")
        
        # 性能统计
        print(f"\n⚡ 性能统计:")
        all_response_times = []
        for models_result in self.results.values():
            for result in models_result.values():
                if result['success'] and 'response_time' in result['details']:
                    all_response_times.append(result['details']['response_time'])
        
        if all_response_times:
            avg_time = sum(all_response_times) / len(all_response_times)
            min_time = min(all_response_times)
            max_time = max(all_response_times)
            print(f"  平均响应时间: {avg_time:.2f}s")
            print(f"  最快响应: {min_time:.2f}s")
            print(f"  最慢响应: {max_time:.2f}s")
        
        # 推荐配置
        print(f"\n💡 配置建议:")
        working_keys = []
        for key_name, models_result in self.results.items():
            if all(r['success'] for r in models_result.values()):
                key_index = key_name.split('_')[1]
                working_keys.append(key_index)
        
        if len(working_keys) >= 2:
            print("  ✅ 两个key都工作正常，可以使用2-key并发配置")
            print("  export IDEALLAB_API_KEY_0=\"956c41bd0f31beaf68b871d4987af4bb\"")
            print("  export IDEALLAB_API_KEY_1=\"3d906058842b6cf4cee8aaa019f7e77b\"")
        elif len(working_keys) == 1:
            print(f"  ⚠️  只有key{working_keys[0]}工作正常，建议使用单key配置")
        else:
            print("  ❌ 没有key正常工作，请检查key的有效性")
    
    def save_report_json(self):
        """保存详细的JSON报告"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'api_base': self.api_base,
            'test_models': self.test_models,
            'keys_tested': len(self.keys),
            'results': self.results
        }
        
        report_file = Path("ideallab_keys_validation_report.json")
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 详细报告已保存到: {report_file}")

async def main():
    """主函数"""
    print("🔍 IdealLab API Keys 可用性验证")
    print("=" * 80)
    
    validator = IdealLabKeyValidator()
    
    if not validator.keys:
        print("❌ 未找到任何IdealLab API keys")
        print("请设置环境变量:")
        print("  export IDEALLAB_API_KEY_0=\"your_key_0\"")
        print("  export IDEALLAB_API_KEY_1=\"your_key_1\"")
        return False
    
    # 执行验证
    await validator.validate_all_keys()
    
    # 生成报告
    validator.generate_report()
    validator.save_report_json()
    
    # 返回是否所有key都可用
    all_success = all(
        all(model_result['success'] for model_result in key_results.values())
        for key_results in validator.results.values()
    )
    
    return all_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)