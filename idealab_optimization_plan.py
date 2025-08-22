#!/usr/bin/env python3
"""
IdealLab开源模型并发优化方案 - 结合动态重映射和模型级并发
"""

from typing import List, Dict, Tuple
import random
from dataclasses import dataclass

@dataclass
class OptimizationPlan:
    """优化方案数据结构"""
    model: str
    prompt_type: str
    api_key_index: int
    shard_id: str
    
class IdealLabOptimizer:
    """IdealLab开源模型并发优化器"""
    
    def __init__(self):
        # 3个API keys
        self.api_keys = [0, 1, 2]
        
        # 原始的prompt type到key的映射
        self.default_mapping = {
            'baseline': 0,
            'cot': 1,
            'optimal': 2,
            # flawed类型轮询
        }
        
        # 轮询计数器
        self.rotate_counter = 0
        
    def optimize_task_distribution(self, models: List[str], prompt_types: List[str], 
                                  num_instances: int) -> List[OptimizationPlan]:
        """
        优化任务分配策略
        
        Args:
            models: 要测试的模型列表，如 ['qwen2.5-72b', 'qwen2.5-7b']
            prompt_types: 要测试的prompt类型，如 ['optimal'] 或 ['flawed_sequence_disorder', ...]
            num_instances: 每个组合的实例数
            
        Returns:
            优化后的任务分配计划
        """
        
        plans = []
        
        # 判断是否为单一prompt type场景（如5.1/5.2只测optimal）
        is_single_prompt = len(prompt_types) == 1
        
        if is_single_prompt:
            # 场景：5.1/5.2测试（只有optimal）
            return self._optimize_single_prompt(models, prompt_types[0], num_instances)
        else:
            # 场景：5.3（多个flawed）或5.5（baseline/cot/optimal）
            return self._optimize_multi_prompt(models, prompt_types, num_instances)
    
    def _optimize_single_prompt(self, models: List[str], prompt_type: str, 
                               num_instances: int) -> List[OptimizationPlan]:
        """
        优化单一prompt type的分配（如5.1/5.2只测optimal）
        
        策略：
        1. 如果有多个模型，每个模型分配给不同的key（模型级并发）
        2. 如果模型数>3，循环分配
        3. 同一模型的多个实例也轮询分配到3个key
        """
        plans = []
        
        # 策略1：不同模型分配到不同key（利用模型间独立限速）
        model_to_keys = {}
        for i, model in enumerate(models):
            # 每个模型优先分配到不同的key
            preferred_key = i % 3
            model_to_keys[model] = preferred_key
            
        # 策略2：同一模型的多个实例也分散到不同key
        for model in models:
            base_key = model_to_keys[model]
            
            for instance_id in range(num_instances):
                # 实例轮询分配到3个key，从模型的base_key开始
                key_index = (base_key + instance_id) % 3
                
                plan = OptimizationPlan(
                    model=model,
                    prompt_type=prompt_type,
                    api_key_index=key_index,
                    shard_id=f"{model}_{prompt_type}_{instance_id}_key{key_index}"
                )
                plans.append(plan)
                
        return plans
    
    def _optimize_multi_prompt(self, models: List[str], prompt_types: List[str], 
                              num_instances: int) -> List[OptimizationPlan]:
        """
        优化多prompt type的分配（如5.3的flawed或5.5的baseline/cot/optimal）
        
        策略：
        1. 非flawed类型按默认映射（baseline→0, cot→1, optimal→2）
        2. flawed类型轮询分配
        3. 同时考虑模型级并发
        """
        plans = []
        
        for model in models:
            for prompt_type in prompt_types:
                # 确定该prompt_type应该用哪个key
                if prompt_type in self.default_mapping:
                    base_key = self.default_mapping[prompt_type]
                elif prompt_type.startswith('flawed_'):
                    # flawed类型轮询
                    base_key = self.rotate_counter % 3
                    self.rotate_counter += 1
                else:
                    # 未知类型，轮询
                    base_key = self.rotate_counter % 3
                    self.rotate_counter += 1
                
                # 为该组合创建多个实例
                for instance_id in range(num_instances):
                    # 如果是flawed，实例也要分散
                    if prompt_type.startswith('flawed_'):
                        key_index = (base_key + instance_id) % 3
                    else:
                        # 非flawed保持固定映射，但实例可以轮询
                        if num_instances > 3:
                            # 实例太多时也要分散
                            key_index = (base_key + instance_id) % 3
                        else:
                            # 实例少时保持原映射
                            key_index = base_key
                    
                    plan = OptimizationPlan(
                        model=model,
                        prompt_type=prompt_type,
                        api_key_index=key_index,
                        shard_id=f"{model}_{prompt_type}_{instance_id}_key{key_index}"
                    )
                    plans.append(plan)
                    
        return plans
    
    def calculate_concurrency(self, plans: List[OptimizationPlan]) -> Dict:
        """计算并发度统计"""
        key_usage = {0: [], 1: [], 2: []}
        
        for plan in plans:
            key_usage[plan.api_key_index].append(f"{plan.model}_{plan.prompt_type}")
        
        # 统计每个key的负载
        stats = {
            'key0_tasks': len(key_usage[0]),
            'key1_tasks': len(key_usage[1]),
            'key2_tasks': len(key_usage[2]),
            'max_concurrency': max(len(key_usage[0]), len(key_usage[1]), len(key_usage[2])),
            'min_concurrency': min(len(key_usage[0]), len(key_usage[1]), len(key_usage[2])),
            'balance_ratio': min(len(key_usage[0]), len(key_usage[1]), len(key_usage[2])) / 
                           max(len(key_usage[0]), len(key_usage[1]), len(key_usage[2])) 
                           if max(len(key_usage[0]), len(key_usage[1]), len(key_usage[2])) > 0 else 1
        }
        
        return stats

def demonstrate_optimization():
    """演示优化效果"""
    optimizer = IdealLabOptimizer()
    
    print("=" * 70)
    print("IdealLab开源模型并发优化方案演示")
    print("=" * 70)
    
    # 场景1：5.1/5.2测试（只测optimal）
    print("\n📊 场景1：5.1/5.2测试 - 只测optimal")
    print("-" * 50)
    
    models_5_1 = ['qwen2.5-72b-instruct', 'qwen2.5-32b-instruct', 'qwen2.5-14b-instruct']
    prompt_types_5_1 = ['optimal']
    
    plans_5_1 = optimizer.optimize_task_distribution(models_5_1, prompt_types_5_1, num_instances=3)
    
    print("\n优化前：所有任务都用Key2（optimal的默认key）")
    print("- Key0: 空闲 ❌")
    print("- Key1: 空闲 ❌")
    print("- Key2: 所有9个任务串行 ❌")
    
    print("\n优化后：任务分散到3个key")
    key_distribution = {0: 0, 1: 0, 2: 0}
    for plan in plans_5_1:
        key_distribution[plan.api_key_index] += 1
    
    for key_idx in range(3):
        tasks = [p for p in plans_5_1 if p.api_key_index == key_idx]
        print(f"- Key{key_idx}: {len(tasks)}个任务")
        for task in tasks[:2]:  # 只显示前2个
            print(f"    • {task.model} ({task.prompt_type})")
        if len(tasks) > 2:
            print(f"    • ... 共{len(tasks)}个任务")
    
    stats = optimizer.calculate_concurrency(plans_5_1)
    print(f"\n并发度提升：1 → 3 (提升3倍)")
    print(f"负载均衡度：{stats['balance_ratio']:.2%}")
    
    # 场景2：5.3测试（多个flawed）
    print("\n\n📊 场景2：5.3测试 - 多个flawed类型")
    print("-" * 50)
    
    models_5_3 = ['qwen2.5-72b-instruct', 'qwen2.5-7b-instruct']
    prompt_types_5_3 = ['flawed_sequence_disorder', 'flawed_tool_misuse', 'flawed_parameter_error']
    
    plans_5_3 = optimizer.optimize_task_distribution(models_5_3, prompt_types_5_3, num_instances=2)
    
    print("\nflawed类型轮询分配到3个key：")
    for key_idx in range(3):
        tasks = [p for p in plans_5_3 if p.api_key_index == key_idx]
        print(f"- Key{key_idx}: {len(tasks)}个任务")
        for task in tasks[:3]:
            print(f"    • {task.model} ({task.prompt_type})")
        if len(tasks) > 3:
            print(f"    • ... 共{len(tasks)}个任务")
    
    stats = optimizer.calculate_concurrency(plans_5_3)
    print(f"\n负载均衡度：{stats['balance_ratio']:.2%}")
    
    # 场景3：5.5测试（baseline/cot/optimal）
    print("\n\n📊 场景3：5.5测试 - baseline/cot/optimal")
    print("-" * 50)
    
    models_5_5 = ['qwen2.5-72b-instruct']
    prompt_types_5_5 = ['baseline', 'cot', 'optimal']
    
    plans_5_5 = optimizer.optimize_task_distribution(models_5_5, prompt_types_5_5, num_instances=5)
    
    print("\n固定映射但实例分散：")
    for key_idx in range(3):
        tasks = [p for p in plans_5_5 if p.api_key_index == key_idx]
        print(f"- Key{key_idx}: {len(tasks)}个任务")
        prompt_counts = {}
        for task in tasks:
            prompt_counts[task.prompt_type] = prompt_counts.get(task.prompt_type, 0) + 1
        for prompt_type, count in prompt_counts.items():
            print(f"    • {prompt_type}: {count}个实例")
    
    stats = optimizer.calculate_concurrency(plans_5_5)
    print(f"\n负载均衡度：{stats['balance_ratio']:.2%}")
    
    print("\n" + "=" * 70)
    print("总结：")
    print("✅ 5.1/5.2场景：从1个并发提升到3个并发（3倍提升）")
    print("✅ 5.3场景：保持3个并发，负载均衡")
    print("✅ 5.5场景：保持3个并发，按prompt type分组")
    print("✅ 所有场景都充分利用3个API keys")
    print("=" * 70)

if __name__ == "__main__":
    demonstrate_optimization()