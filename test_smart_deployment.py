#!/usr/bin/env python3
"""
测试智能部署管理器功能
===================
验证多部署负载均衡和429错误处理
"""

import sys
import time
import logging
from smart_deployment_manager import SmartDeploymentManager, get_deployment_manager
from api_client_manager import APIClientManager

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_deployment_manager():
    """测试智能部署管理器基本功能"""
    print("🚀 测试智能部署管理器")
    print("=" * 50)
    
    # 创建管理器实例
    manager = SmartDeploymentManager()
    
    # 显示当前状态
    manager.print_status()
    
    # 测试获取最佳部署
    print(f"\n🎯 测试部署选择:")
    for i in range(5):
        llama_deployment = manager.get_best_deployment("Llama-3.3-70B-Instruct")
        deepseek_deployment = manager.get_best_deployment("DeepSeek-V3-0324")
        print(f"  轮次{i+1}: Llama -> {llama_deployment}, DeepSeek -> {deepseek_deployment}")
        time.sleep(0.1)
    
    # 测试故障标记
    print(f"\n⚠️  测试故障标记:")
    manager.mark_deployment_failed("Llama-3.3-70B-Instruct", "429")
    manager.mark_deployment_failed("Llama-3.3-70B-Instruct-2", "timeout")
    
    print(f"标记失败后的选择:")
    for i in range(3):
        deployment = manager.get_best_deployment("Llama-3.3-70B-Instruct")
        print(f"  轮次{i+1}: {deployment}")
        time.sleep(0.1)
    
    # 显示更新后的状态
    print(f"\n📊 更新后的状态:")
    manager.print_status()

def test_api_integration():
    """测试API客户端管理器集成"""
    print(f"\n🔌 测试API客户端管理器集成")
    print("=" * 50)
    
    try:
        # 创建API客户端管理器
        api_manager = APIClientManager()
        
        # 测试获取Llama客户端
        print("📡 测试获取Llama-3.3-70B-Instruct客户端...")
        client = api_manager._get_user_azure_client("Llama-3.3-70B-Instruct")
        
        if hasattr(client, 'deployment_name'):
            print(f"✅ 成功创建客户端，部署名: {client.deployment_name}")
            if hasattr(client, 'current_deployment'):
                print(f"✅ 当前部署: {client.current_deployment}")
        else:
            print("❌ 客户端缺少部署信息")
            
    except Exception as e:
        print(f"❌ API集成测试失败: {e}")

def test_mock_429_scenario():
    """模拟429错误场景"""
    print(f"\n🚨 模拟429错误处理场景")
    print("=" * 50)
    
    manager = get_deployment_manager()
    
    # 模拟多个429错误
    print("📡 模拟Llama-3.3-70B-Instruct的3个部署都遇到429错误...")
    
    deployments = ["Llama-3.3-70B-Instruct", "Llama-3.3-70B-Instruct-2", "Llama-3.3-70B-Instruct-3"]
    
    for i, deployment in enumerate(deployments):
        print(f"  {i+1}. 标记 {deployment} 为429错误")
        manager.mark_deployment_failed(deployment, "429")
        
        # 尝试获取最佳部署
        best = manager.get_best_deployment("Llama-3.3-70B-Instruct")
        print(f"     -> 当前最佳选择: {best}")
    
    # 显示最终状态
    print(f"\n📊 所有部署标记失败后的状态:")
    manager.print_status()
    
    # 测试恢复机制
    print(f"\n🔄 测试恢复机制 - 标记一个部署恢复成功:")
    manager.mark_deployment_success("Llama-3.3-70B-Instruct-2")
    best = manager.get_best_deployment("Llama-3.3-70B-Instruct")
    print(f"恢复后的最佳选择: {best}")

def test_configuration_validation():
    """验证配置正确性"""
    print(f"\n⚙️  验证配置正确性")
    print("=" * 50)
    
    try:
        manager = SmartDeploymentManager()
        
        # 检查配置中的并行部署
        parallel_deployments = manager.parallel_deployments
        
        print("📋 配置的并行部署:")
        for model, deployments in parallel_deployments.items():
            print(f"  {model}:")
            for deployment in deployments:
                print(f"    • {deployment}")
        
        # 验证每个部署是否有对应的配置
        print(f"\n🔍 验证部署配置:")
        config = manager.config
        model_configs = config.get('model_configs', {})
        
        for model, deployments in parallel_deployments.items():
            print(f"  {model}:")
            for deployment in deployments:
                if deployment in model_configs:
                    provider = model_configs[deployment].get('provider', 'unknown')
                    endpoint = model_configs[deployment].get('azure_endpoint', 'N/A')
                    print(f"    ✅ {deployment}: {provider} - {endpoint}")
                else:
                    print(f"    ❌ {deployment}: 配置缺失")
                    
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")

def main():
    """主测试函数"""
    print("🧪 智能部署管理器测试套件")
    print("=" * 60)
    
    try:
        # 测试1: 基本功能
        test_deployment_manager()
        
        # 测试2: API集成
        test_api_integration()
        
        # 测试3: 429错误场景
        test_mock_429_scenario()
        
        # 测试4: 配置验证
        test_configuration_validation()
        
        print(f"\n🎉 所有测试完成！")
        print("💡 建议: 在实际使用中监控日志以观察故障转移行为")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()