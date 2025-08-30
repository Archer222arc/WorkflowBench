#!/usr/bin/env python3
"""
为ultra_parallel_runner.py添加Qwen队列调度功能的补丁
===================================================

这个补丁可以直接集成到ultra_parallel_runner.py中
主要修改run_ultra_parallel_test方法，添加对多个qwen模型的智能调度
"""

def run_ultra_parallel_test_with_qwen_queue(self, models: List[str], prompt_types: str, 
                                            difficulties: List[str], task_types: str = "all", 
                                            num_instances: int = 20, rate_mode: str = "fixed",
                                            result_suffix: str = "", silent: bool = False,
                                            tool_success_rate: float = 0.8, max_workers: int = None) -> bool:
    """运行多个qwen模型的超并发测试（使用队列调度）
    
    专门为Phase 5.2设计：
    - 输入多个qwen模型和多个难度
    - 自动分配到3个API key队列
    - 同一key串行，不同key并行
    """
    
    logger.info(f"\n🎯 启动Qwen批量超并发测试（队列调度模式）")
    logger.info(f"   模型数: {len(models)}")
    logger.info(f"   难度: {difficulties}")
    logger.info(f"   实例数: {num_instances}")
    
    # Key分配映射
    KEY_ASSIGNMENT = {
        "72b": 0,
        "32b": 1,
        "14b": 2,
        "7b": 0,
        "3b": 1,
    }
    
    # 构建任务队列
    key_queues = {0: [], 1: [], 2: []}
    
    for difficulty in difficulties:
        for model in models:
            # 提取模型规模
            import re
            match = re.search(r'(\d+b)', model.lower())
            if match:
                model_size = match.group(1)
                key_idx = KEY_ASSIGNMENT.get(model_size, 0)
            else:
                key_idx = 0
            
            # 添加到对应key的队列
            key_queues[key_idx].append({
                'model': model,
                'difficulty': difficulty,
                'prompt_types': prompt_types,
                'task_types': task_types,
                'num_instances': num_instances,
                'tool_success_rate': tool_success_rate
            })
    
    # 显示队列分配
    logger.info(f"📋 任务队列分配:")
    for key_idx, queue in key_queues.items():
        if queue:
            logger.info(f"   Key{key_idx}: {len(queue)}个任务")
            for task in queue:
                logger.info(f"      - {task['model']}-{task['difficulty']}")
    
    # 创建处理线程
    threads = []
    results = {}
    
    def process_queue(key_idx, tasks):
        """处理单个key的任务队列"""
        queue_results = []
        for i, task in enumerate(tasks, 1):
            logger.info(f"🔄 Key{key_idx} [{i}/{len(tasks)}]: 开始 {task['model']}-{task['difficulty']}")
            
            # 调用原有的单模型执行方法
            success = self.run_ultra_parallel_test(
                model=task['model'],
                prompt_types=task['prompt_types'],
                difficulty=task['difficulty'],
                task_types=task['task_types'],
                num_instances=task['num_instances'],
                rate_mode=rate_mode,
                result_suffix=result_suffix,
                silent=silent,
                tool_success_rate=task['tool_success_rate'],
                max_workers=max_workers
            )
            
            queue_results.append({
                'model': task['model'],
                'difficulty': task['difficulty'],
                'success': success
            })
            
            if success:
                logger.info(f"✅ Key{key_idx} [{i}/{len(tasks)}]: 完成 {task['model']}-{task['difficulty']}")
            else:
                logger.error(f"❌ Key{key_idx} [{i}/{len(tasks)}]: 失败 {task['model']}-{task['difficulty']}")
        
        results[key_idx] = queue_results
    
    # 启动线程处理每个key的队列
    for key_idx, tasks in key_queues.items():
        if tasks:
            thread = threading.Thread(
                target=process_queue,
                args=(key_idx, tasks),
                name=f"Key{key_idx}Worker"
            )
            threads.append(thread)
            thread.start()
            logger.info(f"🚀 启动Key{key_idx}处理线程")
    
    # 等待所有线程完成
    logger.info(f"⏳ 等待所有队列完成...")
    for thread in threads:
        thread.join()
    
    # 统计结果
    total_tasks = sum(len(queue) for queue in key_queues.values())
    successful_tasks = sum(
        sum(1 for r in queue_results if r['success']) 
        for queue_results in results.values()
    )
    
    logger.info(f"✅ 批量测试完成: {successful_tasks}/{total_tasks} 成功")
    
    return successful_tasks == total_tasks


# 使用示例（在run_systematic_test_final.sh中调用）
"""
# Phase 5.2调用示例
python ultra_parallel_runner.py \
    --models "qwen2.5-72b-instruct,qwen2.5-32b-instruct,qwen2.5-14b-instruct,qwen2.5-7b-instruct,qwen2.5-3b-instruct" \
    --prompt-types "optimal" \
    --difficulties "very_easy,medium" \
    --task-types "all" \
    --num-instances 20 \
    --rate-mode fixed \
    --use-queue-scheduler  # 新增参数，启用队列调度
"""

print("""
集成步骤：
=========

1. 将run_ultra_parallel_test_with_qwen_queue方法添加到UltraParallelRunner类

2. 在main函数中添加对多模型的支持：
   - 解析--models参数（逗号分隔的模型列表）
   - 解析--difficulties参数（逗号分隔的难度列表）
   - 添加--use-queue-scheduler开关

3. 修改run_systematic_test_final.sh的Phase 5.2部分：
   - 不再使用&后台并发
   - 直接调用带队列调度的ultra_parallel_runner

优势：
====
✅ 最小化代码改动
✅ 向后兼容（不影响现有功能）
✅ 彻底解决并发冲突
✅ 最大化资源利用率
""")