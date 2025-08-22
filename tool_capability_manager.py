#!/usr/bin/env python3
"""
Unified Tool Capability Manager
===============================
统一管理工具能力判断，使用语义操作索引消除硬编码
"""

from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
import logging

# 导入语义操作索引
from operation_embedding_index import get_operation_index, get_embedding_cache_info
HAS_OPERATION_INDEX = True

logger = logging.getLogger(__name__)


class ToolCapabilityManager:
    """统一的工具能力管理器（使用语义索引）"""
    
    def __init__(self):
        """初始化管理器"""
        # 初始化语义操作索引
        self.operation_index = get_operation_index()
        
        # 打印缓存信息以验证单例是否正常工作
        cache_info = get_embedding_cache_info()
        logger.debug(f" OperationIndex cache info: {cache_info}")
        print("[INFO] Operation semantic index initialized")

        # 保留原有的硬编码映射作为fallback
        self.operation_category_mapping = {
            'input': ['read', 'load', 'fetch', 'scan'],
            'validation': ['validate', 'verify', 'check'],
            'transformation': ['transform', 'convert', 'parse', 'process'],
            'aggregation': ['aggregate', 'combine', 'merge', 'collect'],
            'output': ['write', 'export', 'save', 'store'],
            'computation': ['calculate', 'compute', 'analyze', 'predict'],
            'integration': ['connect', 'authenticate', 'map', 'route'],
            'utility': ['log', 'cache', 'notify', 'track']
        }
        
        # 反向映射：操作关键词到类别（fallback用）
        self.operation_to_category = {}
        for category, operations in self.operation_category_mapping.items():
            for op in operations:
                self.operation_to_category[op] = category
        
        # 工具可靠性基准值
        self.reliability_baselines = {
            'validation': 0.95,
            'input': 0.85,
            'output': 0.85,
            'transformation': 0.80,
            'aggregation': 0.80,
            'computation': 0.75,
            'integration': 0.70,
            'utility': 0.90,
            'general': 0.80
        }
        
        # 相似工具组（暂时保留，后续可以用语义搜索替代）
        self.similar_tool_groups = {
            'readers': ['file_operations_reader', 'file_operations_scanner'],
            'processors': ['data_processing_parser', 'data_processing_transformer'],
            'validators': ['data_processing_filter', 'data_processing_validator'],
            'calculators': ['computation_calculator', 'computation_analyzer'],
            'networkers': ['network_fetcher', 'network_poster', 'network_monitor']
        }
    
    def get_category(self, capability) -> str:
        """获取工具类别（使用语义索引）"""
        if hasattr(capability, 'semantic_operations'):
            operations = capability.semantic_operations
        elif isinstance(capability, dict):
            operations = capability.get('semantic_operations', [])
        else:
            return 'general'
        
        logger.debug(f" get_category called with operations: {operations}")
        
        # 如果operations为空，尝试动态生成
        if not operations:
            logger.debug(f" Operations empty, attempting dynamic generation...")
            
            # 尝试从capability对象获取工具名称
            tool_name = None
            if hasattr(capability, 'tool_name'):
                tool_name = capability.tool_name
            elif isinstance(capability, dict):
                tool_name = capability.get('tool_name', capability.get('name'))
            
            if tool_name:
                logger.debug(f" Generating operations for tool: {tool_name}")
                operations = self._generate_operations_from_tool_name(tool_name)
                logger.debug(f" Generated operations: {operations}")
        
        # 优先使用语义索引
        if operations:
            logger.debug(f" Using semantic index for operations: {operations}")
            category = self.operation_index.get_category_for_operations(operations)
            if category != 'general':
                logger.debug(f" Semantic category determined: {category}")
                return category

        # Fallback: 基于硬编码的语义操作判断类别
        print("[DEBUG] Falling back to keyword matching")
        for operation in operations:
            for keyword, category in self.operation_to_category.items():
                if keyword in operation.lower():
                    return category
        
        return 'general'

    def _generate_operations_from_tool_name(self, tool_name: str) -> List[str]:
        """从工具名称动态生成语义操作"""
        operations = []
        name_lower = tool_name.lower()
        
        logger.debug(f" Generating operations from tool name: {tool_name}")
        
        # 基于工具名称的模式推断（与上面的逻辑一致）
        if 'reader' in name_lower or 'scanner' in name_lower or 'fetcher' in name_lower:
            operations.append('read')
        elif 'writer' in name_lower or 'exporter' in name_lower or 'poster' in name_lower:
            operations.append('write')
        elif 'validator' in name_lower or 'checker' in name_lower:
            operations.append('validate')
        elif 'transformer' in name_lower or 'converter' in name_lower or 'parser' in name_lower:
            operations.append('transform')
        elif 'filter' in name_lower:
            operations.append('filter')
        elif 'aggregator' in name_lower or 'combiner' in name_lower:
            operations.append('aggregate')
        elif 'calculator' in name_lower or 'analyzer' in name_lower or 'simulator' in name_lower:
            operations.append('compute')
        elif 'monitor' in name_lower or 'tracker' in name_lower:
            operations.append('monitor')
        elif 'cache' in name_lower:
            operations.append('cache')
        elif 'authenticator' in name_lower:
            operations.append('authenticate')
        elif 'compressor' in name_lower:
            operations.append('compress')
        elif 'network' in name_lower or 'http' in name_lower:
            operations.append('network')
        elif 'queue' in name_lower or 'scheduler' in name_lower:
            operations.append('queue')
        elif 'logger' in name_lower:
            operations.append('log')
        elif 'notifier' in name_lower:
            operations.append('notify')
        else:
            # 基于前缀推断
            if name_lower.startswith('data_'):
                operations.append('transform')
            elif name_lower.startswith('file_'):
                operations.append('read')
            elif name_lower.startswith('network_'):
                operations.append('network')
            elif name_lower.startswith('utility_'):
                operations.append('cache')
            elif name_lower.startswith('integration_'):
                operations.append('integrate')
            elif name_lower.startswith('computation_'):
                operations.append('compute')
            else:
                operations.append('transform')  # 默认操作
        
        logger.debug(f" Generated operations: {operations}")
        return operations
        
    def get_category_encoding(self, category: str) -> float:
        """获取类别的数值编码（用于特征工程）"""
        category_encodings = {
            'input': 0.0,
            'validation': 0.2,
            'transformation': 0.4,
            'aggregation': 0.6,
            'output': 0.8,
            'computation': 0.3,
            'integration': 0.5,
            'utility': 0.7,
            'general': 0.5
        }
        return category_encodings.get(category, 0.5)
    
    def get_base_reliability(self, tool_name: str, category: Optional[str] = None) -> float:
        """获取工具的基础可靠性"""
        if category is None:
            # 从工具名推断类别
            if '_validator' in tool_name:
                category = 'validation'
            elif '_reader' in tool_name or '_scanner' in tool_name:
                category = 'input'
            elif '_writer' in tool_name:
                category = 'output'
            else:
                category = 'general'
        
        return self.reliability_baselines.get(category, 0.80)
    
    def find_similar_tools(self, tool_name: str) -> List[str]:
        """找到可能混淆的相似工具"""
        similar_tools = []
        
        # 先尝试从预定义组中查找
        for group_name, tools in self.similar_tool_groups.items():
            if tool_name in tools:
                similar_tools.extend([t for t in tools if t != tool_name])
        
        # 如果有语义索引，可以基于操作相似性查找
        # （这需要工具的semantic_operations信息）
        
        return similar_tools
    
    def is_output_tool(self, tool_name: str, semantic_operations: List[str] = None) -> bool:
        """判断是否为输出工具（使用语义理解）"""
        # 如果提供了语义操作，优先使用语义判断
        if semantic_operations and self.operation_index:
            logger.debug(f" Checking if operations are output-related: {semantic_operations}")
            for operation in semantic_operations:
                if self.operation_index.is_operation_in_category(operation, 'output', threshold=0.7):
                    logger.debug(f" Operation '{operation}' is semantically output-related")
                    return True
        
        # Fallback: 基于工具名判断
        output_keywords = ['writer', 'exporter', 'saver', 'poster', 'notifier']
        if any(keyword in tool_name.lower() for keyword in output_keywords):
            return True
        
        # Fallback: 基于硬编码的语义操作判断
        if semantic_operations:
            output_operations = ['write', 'export', 'save', 'post', 'notify']
            return any(any(op in sem_op for op in output_operations) 
                      for sem_op in semantic_operations)
        
        return False
    
    def get_semantic_operations_for_category(self, category: str) -> List[str]:
        """获取类别对应的语义操作"""
        # 如果有语义索引，返回更丰富的同义词
        if self.operation_index:
            operations = []
            # 查找属于该类别的所有操作
            for op_name, op_emb in self.operation_index.operation_embeddings.items():
                if op_emb.category == category:
                    operations.append(op_name)
                    # 添加一些同义词
                    operations.extend(op_emb.synonyms[:2])
            return operations
        
        # Fallback: 返回硬编码的操作
        return self.operation_category_mapping.get(category, [])
    
    def find_operations_by_description(self, description: str, k: int = 3) -> List[Tuple[str, float]]:
        """
        根据描述查找相关操作（新功能）
        
        Args:
            description: 操作描述
            k: 返回数量
            
        Returns:
            [(operation_name, score)]列表
        """
        if self.operation_index:
            return self.operation_index.search_operation(description, k=k)
        
        # Fallback: 简单的关键词匹配
        results = []
        description_lower = description.lower()
        
        for op, category in self.operation_to_category.items():
            if op in description_lower:
                results.append((op, 0.8))  # 固定分数
        
        return results[:k]
    
    def enhance_semantic_operations(self, operations: List[str]) -> List[str]:
        """
        增强语义操作列表，添加同义词和相关操作
        
        Args:
            operations: 原始操作列表
            
        Returns:
            增强后的操作列表
        """
        enhanced = list(operations)  # 保留原始操作
        
        if self.operation_index:
            for op in operations:
                # 查找相似操作
                similar_ops = self.operation_index.find_similar_operations(op, k=3)
                enhanced.extend(similar_ops)
        
        # 去重并返回
        return list(set(enhanced))
    
    def get_operation_category_confidence(self, operation: str, category: str) -> float:
        """
        获取操作属于某个类别的置信度
        
        Args:
            operation: 操作名称或描述
            category: 目标类别
            
        Returns:
            置信度分数（0-1）
        """
        if self.operation_index:
            # 使用语义搜索
            results = self.operation_index.search_operation(operation, k=3)
            
            confidence = 0.0
            for op_name, score in results:
                if op_name in self.operation_index.operation_embeddings:
                    op_emb = self.operation_index.operation_embeddings[op_name]
                    if op_emb.category == category:
                        confidence = max(confidence, score)
            
            return confidence
        
        # Fallback: 简单匹配
        for keyword, cat in self.operation_to_category.items():
            if keyword in operation.lower() and cat == category:
                return 0.8
        
        return 0.0
    
    def suggest_operations_for_task(self, task_description: str, k: int = 5) -> List[str]:
        """
        根据任务描述建议相关操作
        
        Args:
            task_description: 任务描述
            k: 建议数量
            
        Returns:
            建议的操作列表
        """
        if self.operation_index:
            results = self.operation_index.search_operation(task_description, k=k)
            return [op_name for op_name, score in results if score > 0.5]
        
        # Fallback: 基于关键词提取
        suggested = []
        task_lower = task_description.lower()
        
        for keyword in self.operation_to_category.keys():
            if keyword in task_lower:
                suggested.append(keyword)
        
        return suggested[:k]


# 创建全局实例
_global_manager = None

def get_tool_capability_manager() -> ToolCapabilityManager:
    """获取全局工具能力管理器实例"""
    global _global_manager
    
    if _global_manager is None:
        print("[DEBUG] Creating new ToolCapabilityManager instance")
        _global_manager = ToolCapabilityManager()
    else:
        logger.debug(f" Reusing existing ToolCapabilityManager instance (id: {id(_global_manager)})")
        # 验证operation_index缓存状态
        cache_info = get_embedding_cache_info()
        logger.debug(f" Current embedding cache: {cache_info}")
    
    return _global_manager

def reset_tool_capability_manager():
    """重置全局管理器实例（用于测试）"""
    global _global_manager
    print("[DEBUG] Resetting ToolCapabilityManager singleton")
    _global_manager = None
    # 同时重置operation index
    reset_operation_index()


if __name__ == "__main__":
    # 测试代码
    print("Testing Tool Capability Manager with Semantic Index...")
    
    manager = get_tool_capability_manager()
    
    # 测试类别判断
    test_capability = type('TestCapability', (), {
        'semantic_operations': ['read data from file', 'validate json schema', 'export to database']
    })()
    
    category = manager.get_category(test_capability)
    print(f"\nCategory for operations: {category}")
    
    # 测试操作描述搜索
    test_descriptions = [
        "I need to load data from a CSV file",
        "Check if the data meets quality standards",
        "Save the processed results"
    ]
    
    print("\nOperation suggestions:")
    for desc in test_descriptions:
        operations = manager.find_operations_by_description(desc, k=3)
        print(f"\n'{desc}':")
        for op, score in operations:
            print(f"  - {op}: {score:.3f}")
    
    # 测试任务建议
    task = "Read customer data from API, validate addresses, and save to database"
    suggested_ops = manager.suggest_operations_for_task(task, k=5)
    print(f"\nSuggested operations for task: {suggested_ops}")