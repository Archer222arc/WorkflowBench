#!/usr/bin/env python3
"""
简单的Embedding Manager共享方案
通过线程安全的单例模式减少内存占用
"""

import threading
from typing import Optional

# 全局锁和实例
_embedding_manager_lock = threading.Lock()
_global_embedding_manager = None

def get_or_create_shared_embedding_manager():
    """
    获取或创建共享的embedding manager
    线程安全，但在多进程中每个进程仍会有一个实例
    """
    global _global_embedding_manager
    
    if _global_embedding_manager is None:
        with _embedding_manager_lock:
            # 双重检查锁定
            if _global_embedding_manager is None:
                print("🔧 创建共享的Embedding Manager（整个进程只创建一次）")
                from mcp_embedding_manager import get_embedding_manager
                _global_embedding_manager = get_embedding_manager()
                print("✅ Embedding Manager创建完成，将被所有线程共享")
    else:
        print("♻️  重用已有的Embedding Manager")
    
    return _global_embedding_manager


class OptimizedMockGenerator:
    """优化的MockGenerator，使用共享的embedding manager"""
    
    def __init__(self):
        # 加载工具注册表（从JSON文件而不是导入模块）
        from pathlib import Path
        import json
        
        tool_registry_path = Path("mcp_generated_library/tool_registry_consolidated.json")
        if tool_registry_path.exists():
            with open(tool_registry_path, 'r') as f:
                tool_data = json.load(f)
                self.full_tool_registry = tool_data
                
                # tool_data本身就是一个扁平的字典，键是工具名，值是工具信息
                if isinstance(tool_data, dict):
                    self.tool_names = list(tool_data.keys())
                    # tool_capabilities就是tool_data本身
                    self.tool_capabilities = tool_data
                else:
                    self.tool_names = []
                    self.tool_capabilities = {}
        else:
            # 如果文件不存在，创建一个空的registry
            self.full_tool_registry = {}
            self.tool_names = []
            self.tool_capabilities = {}
        
        # 使用共享的embedding manager（关键优化）
        self.embedding_manager = get_or_create_shared_embedding_manager()
        
        # 使用真正的ToolCallVerifier获得准确的工具验证
        try:
            from workflow_quality_test_flawed import ToolCallVerifier
            self.output_verifier = ToolCallVerifier(
                tool_capabilities=self.tool_capabilities,
                embedding_manager=self.embedding_manager
            )
            print(f"✅ Using real ToolCallVerifier with {len(self.output_verifier.output_tools)} output tools")
        except ImportError:
            # Fallback到简单版本
            class SimpleOutputVerifier:
                def __init__(self):
                    self.output_tools = {
                        'file_operations_writer',
                        'data_output_saver', 
                        'file_operations_creator',
                        'data_processing_exporter',
                        'api_integration_responder'
                    }
                def verify(self, *args, **kwargs):
                    return True
            
            self.output_verifier = SimpleOutputVerifier()
            print("⚠️ Using SimpleOutputVerifier fallback")
        
        # 创建空的tool_success_history
        self.tool_success_history = {}
        
        # 其他属性设为None（不会导致崩溃）
        self.tool_capability_manager = None
        self.task_manager = None
        self.workflow_validator = None
        self.operation_embedding_index = None
    
    def get_tool_success_history(self):
        """返回工具成功历史"""
        return self.tool_success_history
    
    def generate_workflow(self, task_type, task_instance):
        # 如果意外调用到这个方法，返回None
        return None


def test_sharing():
    """测试共享机制"""
    print("="*60)
    print("测试Embedding Manager共享机制")
    print("="*60)
    
    # 创建多个MockGenerator
    generators = []
    for i in range(5):
        print(f"\n创建第{i+1}个MockGenerator:")
        gen = OptimizedMockGenerator()
        generators.append(gen)
    
    # 验证是否使用相同的embedding manager
    print("\n验证共享:")
    first_em = id(generators[0].embedding_manager)
    all_same = all(id(g.embedding_manager) == first_em for g in generators)
    
    if all_same:
        print("✅ 所有MockGenerator共享同一个Embedding Manager!")
        print(f"   内存节省: {(5-1)*50}MB (假设每个50MB)")
    else:
        print("❌ 未能共享Embedding Manager")
    
    return all_same


if __name__ == "__main__":
    # 运行测试
    success = test_sharing()
    
    if success:
        print("\n" + "="*60)
        print("💡 优化建议")
        print("="*60)
        print("将batch_test_runner.py中的MockGenerator")
        print("替换为OptimizedMockGenerator即可实现共享")
        print("\n预期效果（25个并发）:")
        print("  原始: 25 × 50MB = 1.25GB")
        print("  优化: 1 × 50MB = 50MB (每个进程)")
        print("  节省: 1.2GB (在多线程中)")
        print("\n注意: 多进程中每个进程仍会创建一个实例，")
        print("但比每个MockGenerator都创建要好得多。")