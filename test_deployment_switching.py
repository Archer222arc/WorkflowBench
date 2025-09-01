#!/usr/bin/env python3
"""
测试部署切换功能
==================
验证智能部署管理器是否能在429错误时正确切换部署
"""

import sys
import time
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_client_creation_with_deployment_switching():
    """测试客户端创建时的智能部署选择"""
    print("🧪 测试1: 客户端创建时的智能部署选择")
    print("=" * 50)
    
    from api_client_manager import get_client_for_model
    
    # 测试Llama-3.3-70B-Instruct（有多部署配置）
    print("📡 测试Llama-3.3-70B-Instruct部署选择...")
    client = get_client_for_model("Llama-3.3-70B-Instruct")
    
    if hasattr(client, 'current_deployment'):
        print(f"✅ 当前部署: {client.current_deployment}")
        print(f"✅ 部署名称: {client.deployment_name}")
    else:
        print("❌ 客户端缺少current_deployment属性")
    
    # 测试DeepSeek-V3-0324（也有多部署配置）
    print("\n📡 测试DeepSeek-V3-0324部署选择...")
    client2 = get_client_for_model("DeepSeek-V3-0324")
    
    if hasattr(client2, 'current_deployment'):
        print(f"✅ 当前部署: {client2.current_deployment}")
        print(f"✅ 部署名称: {client2.deployment_name}")
    else:
        print("❌ 客户端缺少current_deployment属性")

def test_deployment_manager():
    """测试智能部署管理器基本功能"""
    print("\n🧪 测试2: 智能部署管理器基本功能")
    print("=" * 50)
    
    from smart_deployment_manager import get_deployment_manager
    
    manager = get_deployment_manager()
    
    # 显示当前状态
    manager.print_status()
    
    # 测试获取最佳部署
    print(f"\n🎯 测试部署选择:")
    for i in range(3):
        llama_deployment = manager.get_best_deployment("Llama-3.3-70B-Instruct")
        deepseek_deployment = manager.get_best_deployment("DeepSeek-V3-0324")
        print(f"  轮次{i+1}: Llama -> {llama_deployment}, DeepSeek -> {deepseek_deployment}")
        time.sleep(0.1)

def test_429_error_simulation():
    """模拟429错误和部署切换"""
    print("\n🧪 测试3: 模拟429错误和部署切换")
    print("=" * 50)
    
    from smart_deployment_manager import get_deployment_manager
    
    manager = get_deployment_manager()
    
    # 模拟429错误
    print("🚨 模拟Llama-3.3-70B-Instruct遇到429错误...")
    
    # 获取当前最佳部署
    current_deployment = manager.get_best_deployment("Llama-3.3-70B-Instruct")
    print(f"当前使用部署: {current_deployment}")
    
    # 标记为429失败
    manager.mark_deployment_failed(current_deployment, "429")
    print(f"标记 {current_deployment} 为429失败")
    
    # 获取新的最佳部署
    new_deployment = manager.get_best_deployment("Llama-3.3-70B-Instruct")
    print(f"切换后部署: {new_deployment}")
    
    if new_deployment != current_deployment:
        print(f"✅ 成功切换部署: {current_deployment} -> {new_deployment}")
    else:
        print(f"⚠️  没有切换部署（可能没有可用的替代部署）")
    
    # 显示更新后状态
    print(f"\n📊 更新后的状态:")
    manager.print_status()

def test_interactive_executor_integration():
    """测试InteractiveExecutor与部署切换的集成"""
    print("\n🧪 测试4: InteractiveExecutor集成测试")
    print("=" * 50)
    
    try:
        from interactive_executor import InteractiveExecutor
        from api_client_manager import get_client_for_model
        
        print("📡 创建InteractiveExecutor...")
        
        # 创建一个简单的工具注册表
        tool_registry = {
            "test_tool": {
                "description": "A test tool",
                "parameters": [],
                "category": "test"
            }
        }
        
        # 使用Llama模型创建executor
        executor = InteractiveExecutor(
            tool_registry=tool_registry,
            model="Llama-3.3-70B-Instruct",
            prompt_type="optimal",
            max_turns=1,
            success_rate=0.8,
            silent=True
        )
        
        print(f"✅ InteractiveExecutor创建成功")
        print(f"   模型: {executor.model}")
        print(f"   Prompt类型: {getattr(executor, 'prompt_type', 'N/A')}")
        print(f"   IdealLab Key索引: {getattr(executor, 'ideallab_key_index', 'N/A')}")
        
        # 检查客户端是否有部署信息
        if hasattr(executor.llm_client, 'current_deployment'):
            print(f"   当前部署: {executor.llm_client.current_deployment}")
            print(f"   部署名称: {executor.llm_client.deployment_name}")
        else:
            print("   ⚠️  客户端缺少部署信息")
            
    except Exception as e:
        print(f"❌ InteractiveExecutor测试失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主测试函数"""
    print("🚀 部署切换功能测试套件")
    print("=" * 60)
    
    try:
        # 测试1: 客户端创建
        test_client_creation_with_deployment_switching()
        
        # 测试2: 部署管理器
        test_deployment_manager()
        
        # 测试3: 429错误模拟
        test_429_error_simulation()
        
        # 测试4: InteractiveExecutor集成
        test_interactive_executor_integration()
        
        print(f"\n🎉 所有测试完成！")
        print("💡 建议: 运行实际的5.5测试来验证429错误时的自动切换")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()