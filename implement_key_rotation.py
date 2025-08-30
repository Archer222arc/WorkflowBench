#!/usr/bin/env python3
"""
API Key轮换策略实现方案
========================

问题分析：
- 当前：5个qwen模型各自使用3个API keys，导致每个key被5个模型同时使用
- 结果：每个key实际承载5×QPS的请求量，远超服务器限制

解决方案：
- API Key轮换：确保每个key同一时间只被一个模型使用
- 分配策略：根据模型索引分配固定的API key

实现方式：
1. 修改ultra_parallel_runner.py的_create_qwen_smart_shards方法
2. 根据环境变量或模型名称确定使用哪个API key
3. 每个模型只创建一个分片，使用指定的API key
"""

import os
import sys

def show_rotation_strategy():
    """展示API Key轮换策略"""
    print("=" * 80)
    print("API Key轮换策略设计")
    print("=" * 80)
    
    print("\n当前问题（并发共享）：")
    print("  qwen2.5-72b: 使用 key0, key1, key2（3个分片）")
    print("  qwen2.5-32b: 使用 key0, key1, key2（3个分片）")
    print("  qwen2.5-14b: 使用 key0, key1, key2（3个分片）")
    print("  结果：每个key被3个模型同时使用 → 限流")
    
    print("\n新方案A（固定分配，推荐）：")
    print("  qwen2.5-72b: 只使用 key0")
    print("  qwen2.5-32b: 只使用 key1")
    print("  qwen2.5-14b: 只使用 key0（轮换）")
    print("  qwen2.5-7b:  只使用 key1（轮换）")
    print("  qwen2.5-3b:  只使用 key0（轮换）")
    print("  优点：简单、可预测、易调试")
    print("  缺点：key负载可能不均衡")
    
    print("\n新方案B（动态轮换）：")
    print("  使用全局锁文件记录每个key的使用状态")
    print("  模型启动时选择空闲的key")
    print("  优点：负载均衡")
    print("  缺点：复杂、可能有竞态条件")
    
    print("\n推荐实现：方案A（固定分配）")
    print("原因：")
    print("  1. 实现简单，不需要复杂的同步机制")
    print("  2. 可预测性强，便于调试")
    print("  3. 避免竞态条件")
    print("  4. 每个key最多被2个模型使用（可接受）")

def generate_fix_code():
    """生成修复代码"""
    print("\n" + "=" * 80)
    print("修复代码（ultra_parallel_runner.py）")
    print("=" * 80)
    
    fix_code = '''
def _create_qwen_smart_shards(self, model: str, prompt_types: str, difficulty: str,
                              task_types: str, num_instances: int, tool_success_rate: float) -> List[TaskShard]:
    """为qwen模型创建智能分片，使用API Key轮换避免冲突
    
    重要更新：实施API Key轮换策略，每个模型只使用一个固定的key
    """
    shards = []
    
    # API Key轮换映射表
    # 策略：根据模型大小固定分配key，确保负载相对均衡
    KEY_ROTATION_MAP = {
        "72b": 0,  # qwen2.5-72b → key0
        "32b": 1,  # qwen2.5-32b → key1
        "14b": 0,  # qwen2.5-14b → key0（与72b轮换）
        "7b": 1,   # qwen2.5-7b → key1（与32b轮换）
        "3b": 0,   # qwen2.5-3b → key0（与72b/14b轮换）
    }
    
    # 从模型名称提取规模标识
    import re
    match = re.search(r'(\\d+b)', model.lower())
    model_size = match.group(1) if match else None
    
    if model_size not in KEY_ROTATION_MAP:
        logger.warning(f"未知的qwen模型规模: {model_size}，默认使用key0")
        assigned_key = 0
    else:
        assigned_key = KEY_ROTATION_MAP[model_size]
    
    # 也可以从环境变量覆盖（用于测试或特殊情况）
    env_key = os.environ.get(f'QWEN_{model_size.upper()}_KEY')
    if env_key and env_key.isdigit():
        assigned_key = int(env_key) % 2  # 确保在0-1范围内（只有2个keys）
        logger.info(f"使用环境变量指定的key: QWEN_{model_size.upper()}_KEY={assigned_key}")
    
    # 检查是否是5.3的多prompt_types情况（仅处理flawed类型）
    if "," in prompt_types and "flawed" in prompt_types:
        # 5.3场景：保持原有逻辑，但使用assigned_key
        # 判断是哪一组缺陷，但使用模型的assigned_key
        if "sequence_disorder" in prompt_types:
            group_name = "struct_defects"
        elif "missing_step" in prompt_types:
            group_name = "operation_defects"
        elif "logical_inconsistency" in prompt_types:
            group_name = "logic_defects"
        else:
            group_name = "unknown_defects"
        
        shard = TaskShard(
            shard_id=f"{model}_{difficulty}_{group_name}_key{assigned_key}",
            model=model,
            prompt_types=prompt_types,
            difficulty=difficulty,
            task_types=task_types,
            num_instances=num_instances,
            instance_name=f"qwen-key{assigned_key}",  # 使用分配的key
            tool_success_rate=tool_success_rate
        )
        shards.append(shard)
        logger.info(f"🔄 API Key轮换: {model}(5.3模式) → key{assigned_key}")
        return shards
    
    # 5.1/5.2/5.4/5.5场景：使用单个分配的key，不再创建多个分片
    # 这是关键改变：从3个分片改为1个分片
    shard = TaskShard(
        shard_id=f"{model}_{difficulty}_{prompt_types}_key{assigned_key}",
        model=model,
        prompt_types=prompt_types,
        difficulty=difficulty,
        task_types=task_types,
        num_instances=num_instances,  # 全部实例使用同一个key
        instance_name=f"qwen-key{assigned_key}",
        tool_success_rate=tool_success_rate
    )
    shards.append(shard)
    
    logger.info(f"🔄 API Key轮换策略:")
    logger.info(f"   模型: {model} (规模: {model_size})")
    logger.info(f"   分配Key: key{assigned_key}")
    logger.info(f"   实例数: {num_instances}")
    logger.info(f"   注意: 使用单分片模式避免key冲突")
    
    return shards
'''
    print(fix_code)

def show_testing_plan():
    """展示测试计划"""
    print("\n" + "=" * 80)
    print("测试计划")
    print("=" * 80)
    
    print("\n1. 单元测试：")
    print("   python3 -c \"from ultra_parallel_runner import UltraParallelRunner; r = UltraParallelRunner(); print(r._create_qwen_smart_shards('qwen2.5-72b-instruct', 'optimal', 'easy', 'all', 20, 0.8))\"")
    
    print("\n2. 小规模集成测试：")
    print("   NUM_INSTANCES=2 python ultra_parallel_runner.py --model qwen2.5-72b-instruct --prompt-types optimal --difficulty easy --task-types simple_task --num-instances 2")
    
    print("\n3. 并发测试（模拟5.2场景）：")
    print("   # 同时启动两个qwen模型，验证使用不同的keys")
    print("   python ultra_parallel_runner.py --model qwen2.5-72b-instruct ... &")
    print("   python ultra_parallel_runner.py --model qwen2.5-32b-instruct ... &")
    
    print("\n4. 监控验证：")
    print("   # 检查state文件，确认没有key冲突")
    print("   ls -la /tmp/qps_limiter/*.json")
    print("   # 查看每个文件的PID，确认不同模型使用不同的key")

if __name__ == "__main__":
    show_rotation_strategy()
    generate_fix_code()
    show_testing_plan()
    
    print("\n" + "=" * 80)
    print("实施步骤")
    print("=" * 80)
    print("1. 备份当前的ultra_parallel_runner.py")
    print("2. 修改_create_qwen_smart_shards方法")
    print("3. 运行小规模测试验证")
    print("4. 监控QPS限流情况")
    print("5. 根据结果微调key分配策略")