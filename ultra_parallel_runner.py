#!/usr/bin/env python3
"""
Ultra Parallel Runner - 最大化并行度的测试执行器
===============================================

核心设计：
1. 智能实例池管理：统一调度9个Azure实例
2. 任务智能分片：将大任务拆分到多实例
3. 动态负载均衡：根据实例性能自适应分配
4. 聚合结果管理：统一收集和存储结果

目标：将资源利用率从11%提升到90%+
"""

import asyncio
import concurrent.futures
import json
import os
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import subprocess
import threading
from queue import Queue, Empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= Qwen队列调度器 =============
class QwenQueueScheduler:
    """Qwen模型队列调度器 - 确保同key串行，不同key并行
    
    适用于所有phases，自动管理API key资源
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.num_keys = 3
            self.key_queues = {i: Queue() for i in range(self.num_keys)}
            self.key_workers = {}
            self.key_busy = {i: False for i in range(self.num_keys)}
            self.results = []
            
            # 启动worker线程
            for key_idx in range(self.num_keys):
                worker = threading.Thread(
                    target=self._process_queue,
                    args=(key_idx,),
                    daemon=True,
                    name=f"QwenKey{key_idx}Worker"
                )
                worker.start()
                self.key_workers[key_idx] = worker
    
    def _process_queue(self, key_idx: int):
        """处理单个key的任务队列"""
        while True:
            task = self.key_queues[key_idx].get()
            if task is None:  # 退出信号
                break
            
            self.key_busy[key_idx] = True
            try:
                logger.info(f"🔄 Key{key_idx}: 执行 {task['model']}-{task.get('difficulty', 'unknown')}")
                result = task['func'](**task['kwargs'])
                self.results.append((key_idx, task['model'], result))
                logger.info(f"✅ Key{key_idx}: 完成 {task['model']}-{task.get('difficulty', 'unknown')}")
            except Exception as e:
                logger.error(f"❌ Key{key_idx}: 失败 - {e}")
                self.results.append((key_idx, task['model'], False))
            finally:
                self.key_busy[key_idx] = False
                self.key_queues[key_idx].task_done()
    
    def submit_task(self, model: str, key_idx: int, func, **kwargs):
        """提交任务到指定key的队列"""
        # 将model参数包含在kwargs中，确保func调用时能接收到所有参数
        kwargs['model'] = model
        task = {
            'model': model,
            'func': func,
            'kwargs': kwargs,
            'difficulty': kwargs.get('difficulty', 'unknown')
        }
        self.key_queues[key_idx].put(task)
    
    def wait_all(self):
        """等待所有队列完成"""
        for key_idx in range(self.num_keys):
            self.key_queues[key_idx].join()
    
    def shutdown(self):
        """关闭调度器"""
        for key_idx in range(self.num_keys):
            self.key_queues[key_idx].put(None)
# =========================================

# 可选导入新的ResultCollector
try:
    from result_collector import ResultCollector, ResultAggregator
    RESULT_COLLECTOR_AVAILABLE = True
except ImportError:
    RESULT_COLLECTOR_AVAILABLE = False
    logger.info("ResultCollector不可用，将使用传统模式")

@dataclass
class InstanceConfig:
    """Azure实例配置"""
    name: str
    model_family: str  # "deepseek-v3", "deepseek-r1", "llama-3.3"
    max_workers: int = 100
    max_qps: float = 200.0
    is_busy: bool = False
    current_load: int = 0
    performance_score: float = 1.0  # 性能评分，动态调整

@dataclass
class TaskShard:
    """任务分片"""
    shard_id: str
    model: str
    prompt_types: str
    difficulty: str
    task_types: str
    num_instances: int
    instance_name: str
    tool_success_rate: float = 0.8

class UltraParallelRunner:
    """超高并行度测试执行器"""
    
    def __init__(self, use_result_collector: bool = None):
        """
        初始化UltraParallelRunner
        
        Args:
            use_result_collector: 是否使用新的ResultCollector模式
                                 None=自动检测, True=强制启用, False=禁用
        """
        self.instance_pool = self._initialize_instance_pool()
        self.active_tasks: Set[str] = set()
        self.task_queue = Queue()
        self.results_lock = threading.Lock()
        self.performance_stats = {}
        
        # 初始化Qwen调度器
        self.qwen_scheduler = QwenQueueScheduler()
        self._qwen_batch_mode = False  # 批量模式标记
        
        # 结果收集模式配置
        if use_result_collector is None:
            # 自动检测：从环境变量或配置决定
            use_collector = os.environ.get('USE_RESULT_COLLECTOR', 'false').lower() == 'true'
        else:
            use_collector = use_result_collector
            
        if use_collector and RESULT_COLLECTOR_AVAILABLE:
            self.result_collector = ResultCollector()
            self.result_aggregator = ResultAggregator()
            self.use_collector_mode = True
            logger.info("🆕 启用ResultCollector模式，支持零冲突并发")
        else:
            self.result_collector = None
            self.result_aggregator = None
            self.use_collector_mode = False
            if use_collector and not RESULT_COLLECTOR_AVAILABLE:
                logger.warning("⚠️ ResultCollector不可用，使用传统模式")
            else:
                logger.info("📜 使用传统数据库写入模式")
        
    def _initialize_instance_pool(self) -> Dict[str, InstanceConfig]:
        """初始化Azure实例池"""
        instances = {}
        
        # 6个DeepSeek实例（保持Azure API要求的大小写）
        deepseek_v3_instances = [
            "DeepSeek-V3-0324",
            "DeepSeek-V3-0324-2",  # 统一大小写
            "DeepSeek-V3-0324-3"   # 统一大小写
        ]
        
        deepseek_r1_instances = [
            "DeepSeek-R1-0528",
            "DeepSeek-R1-0528-2",  # 统一大小写
            "DeepSeek-R1-0528-3"   # 统一大小写
        ]
        
        # 3个Llama实例（保持Azure API要求的大小写）
        llama_instances = [
            "Llama-3.3-70B-Instruct",
            "Llama-3.3-70B-Instruct-2",  # 统一大小写
            "Llama-3.3-70B-Instruct-3"   # 统一大小写
        ]
        
        # 2个IdealLab API Key对应的虚拟实例
        # 为开源模型qwen创建2个虚拟实例，对应2个可用的API keys
        # 这样可以实现真正的并发（第3个key暂时不可用）
        ideallab_qwen_instances = [
            "qwen-key0",      # 对应API key 0 (baseline偏好)
            "qwen-key1"       # 对应API key 1 (cot+optimal偏好)
        ]
        
        # 注册所有实例
        for name in deepseek_v3_instances:
            instances[name] = InstanceConfig(
                name=name,
                model_family="deepseek-v3",
                max_workers=100,
                max_qps=200.0
            )
            
        for name in deepseek_r1_instances:
            instances[name] = InstanceConfig(
                name=name,
                model_family="deepseek-r1", 
                max_workers=100,
                max_qps=200.0
            )
            
        for name in llama_instances:
            instances[name] = InstanceConfig(
                name=name,
                model_family="llama-3.3",
                max_workers=100,
                max_qps=200.0
            )
            
        # 注册IdealLab实例 (API Key级别并行)
        for name in ideallab_qwen_instances:
            instances[name] = InstanceConfig(
                name=name,
                model_family="qwen",
                max_workers=1,   # 限制为1避免限流问题
                max_qps=5.0      # 更保守的QPS限制
            )
        
        # 添加闭源Azure模型实例 (只有一个deployment，但可以model level并发)
        azure_closed_models = [
            "gpt-4o-mini",
            "gpt-5-mini"
        ]
        
        for model in azure_closed_models:
            # 闭源模型只有单个deployment，但可以用更高并发
            instances[model] = InstanceConfig(
                name=model,
                model_family=f"azure-{model}",
                max_workers=200,  # 单实例更高并发
                max_qps=400.0
            )
        
        # 添加IdealLab闭源模型实例 (只有一个API Key可用，但可以model level并发)
        ideallab_closed_models = [
            "o3-0416-global",
            "gemini-2.5-flash-06-17", 
            "kimi-k2",
            "claude_sonnet4"
        ]
        
        for model in ideallab_closed_models:
            # 闭源模型只能用一个API Key，且有严格速率限制
            instances[model] = InstanceConfig(
                name=model,
                model_family=f"ideallab-{model}",
                max_workers=1,   # 限制为1避免限流问题
                max_qps=5.0      # 更保守的QPS限制
            )
            
        logger.info(f"初始化实例池: {len(instances)}个实例 ({len([i for i in instances.values() if 'azure' in i.model_family])}个Azure + {len([i for i in instances.values() if 'ideallab' in i.model_family or i.model_family == 'qwen'])}个IdealLab)")
        return instances
        
    def get_available_instances(self, model_family: str) -> List[InstanceConfig]:
        """获取指定模型族的可用实例"""
        available = []
        for instance in self.instance_pool.values():
            if (instance.model_family == model_family and 
                not instance.is_busy and 
                instance.current_load < instance.max_workers * 0.8):
                available.append(instance)
        
        # 按性能评分排序，优先使用高性能实例
        available.sort(key=lambda x: x.performance_score, reverse=True)
        return available
        
    def _create_qwen_smart_shards(self, model: str, prompt_types: str, difficulty: str,
                                  task_types: str, num_instances: int, tool_success_rate: float) -> List[TaskShard]:
        """为qwen模型创建智能分片，使用API Key轮换避免冲突
        
        重要更新：实施API Key轮换策略，每个模型只使用一个固定的key
        避免多个模型同时使用同一个key导致的限流问题
        """
        shards = []
        
        # API Key轮换映射表 - 使用3个可用的keys (key0, key1, key2)
        # 策略：根据模型大小固定分配key，确保负载均衡
        KEY_ROTATION_MAP = {
            "72b": 0,  # qwen2.5-72b → key0
            "32b": 1,  # qwen2.5-32b → key1
            "14b": 2,  # qwen2.5-14b → key2
            "7b": 0,   # qwen2.5-7b → key0（与72b错开时间）
            "3b": 1,   # qwen2.5-3b → key1（与32b错开时间）
        }
        
        # 从模型名称提取规模标识
        import re
        match = re.search(r'(\d+b)', model.lower())
        model_size = match.group(1) if match else None
        
        if model_size not in KEY_ROTATION_MAP:
            logger.warning(f"未知的qwen模型规模: {model_size}，默认使用key0")
            assigned_key = 0
        else:
            assigned_key = KEY_ROTATION_MAP[model_size]
        
        # 也可以从环境变量覆盖（用于测试或特殊情况）
        env_key = os.environ.get(f'QWEN_{model_size.upper()}_KEY')
        if env_key and env_key.isdigit():
            assigned_key = int(env_key) % 3  # 确保在0-2范围内（3个keys）
            logger.info(f"使用环境变量指定的key: QWEN_{model_size.upper()}_KEY={assigned_key}")
        
        # 检查是否是5.3的多prompt_types情况（仅处理flawed类型）
        if "," in prompt_types and "flawed" in prompt_types:
            # 5.3场景：保持原有逻辑，但使用assigned_key而非固定分配
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
                prompt_types=prompt_types,  # 保持原始的多个prompt_types
                difficulty=difficulty,
                task_types=task_types,
                num_instances=num_instances,
                instance_name=f"qwen-key{assigned_key}",  # 使用分配的key
                tool_success_rate=tool_success_rate
            )
            shards.append(shard)
            logger.info(f"🔄 API Key轮换(5.3): {model}({model_size}) → key{assigned_key} (缺陷组: {group_name})")
            return shards
        
        # 5.1/5.2/5.4/5.5场景：启用真正的多key并发！
        # 重要修复：创建3个分片，分别使用key0、key1、key2实现并发
        instances_per_key = max(1, num_instances // 3)  # 每个key分配的实例数
        remaining_instances = num_instances % 3  # 余数实例
        
        for key_idx in range(3):  # 使用所有3个keys
            # 分配实例数（余数分配给前几个key）
            key_instances = instances_per_key + (1 if key_idx < remaining_instances else 0)
            
            if key_instances > 0:  # 只创建有实例分配的分片
                shard = TaskShard(
                    shard_id=f"{model}_{difficulty}_{prompt_types}_key{key_idx}",
                    model=model,
                    prompt_types=prompt_types,
                    difficulty=difficulty,
                    task_types=task_types,
                    num_instances=key_instances,
                    instance_name=f"qwen-key{key_idx}",
                    tool_success_rate=tool_success_rate
                )
                shards.append(shard)
        
        logger.info(f"🔄 真正多Key并发策略:")
        logger.info(f"   模型: {model} (规模: {model_size})")
        logger.info(f"   使用Keys: key0, key1, key2")
        logger.info(f"   总实例数: {num_instances}")
        logger.info(f"   分片数: {len(shards)} (每个key独立分片)")
        logger.info(f"   实例分配: {[shard.num_instances for shard in shards]}")
        logger.info(f"   🚀 启用3倍API并发！")
        
        return shards
    
    def create_task_shards(self, model: str, prompt_types: str, difficulty: str, 
                          task_types: str, num_instances: int, tool_success_rate: float = 0.8) -> List[TaskShard]:
        """智能创建任务分片"""
        
        # 特殊处理：qwen模型使用智能分片策略
        if "qwen" in model.lower():
            logger.info(f"🎯 使用qwen智能分片策略: {model}")
            return self._create_qwen_smart_shards(model, prompt_types, difficulty,
                                                 task_types, num_instances, tool_success_rate)
        
        # 确定模型族
        if "deepseek-v3" in model.lower():
            model_family = "deepseek-v3"
            base_model = "DeepSeek-V3-0324"
        elif "deepseek-r1" in model.lower():
            model_family = "deepseek-r1"
            base_model = "DeepSeek-R1-0528"
        elif "llama" in model.lower():
            model_family = "llama-3.3"
            base_model = "Llama-3.3-70B-Instruct"
        # Azure闭源模型
        elif model == "gpt-4o-mini":
            model_family = "azure-gpt-4o-mini"
            base_model = "gpt-4o-mini"
        elif model == "gpt-5-mini":
            model_family = "azure-gpt-5-mini"
            base_model = "gpt-5-mini"
        # IdealLab闭源模型
        elif model == "o3-0416-global":
            model_family = "ideallab-o3-0416-global"
            base_model = "o3-0416-global"
        elif model == "gemini-2.5-flash-06-17":
            model_family = "ideallab-gemini-2.5-flash-06-17"
            base_model = "gemini-2.5-flash-06-17"
        elif model == "kimi-k2":
            model_family = "ideallab-kimi-k2"
            base_model = "kimi-k2"
        elif model == "claude_sonnet4":
            model_family = "ideallab-claude_sonnet4"
            base_model = "claude_sonnet4"
        else:
            logger.warning(f"未知模型族: {model}")
            return []
            
        # 获取可用实例
        available_instances = self.get_available_instances(model_family)
        
        if not available_instances:
            logger.warning(f"没有可用的{model_family}实例")
            return []
            
        # 计算分片策略
        shards = []
        
        # 对于闭源模型，使用特殊的分片策略
        if model_family.startswith("ideallab-"):
            instances_to_use = 1  # IdealLab闭源模型只能使用单分片避免API Key冲突
            logger.info(f"IdealLab闭源模型 {model} 使用单分片策略（避免API Key冲突）")
        elif model_family.startswith("azure-"):
            instances_to_use = 1  # Azure闭源模型使用单分片高并发策略
            logger.info(f"Azure闭源模型 {model} 使用单分片高并发策略（单deployment优化）")
        elif model_family.startswith("deepseek"):
            # DeepSeek模型暂时只使用第一个部署实例，避免多部署可能的并发问题
            instances_to_use = 1
            logger.info(f"DeepSeek模型 {model} 暂时使用单部署策略（避免多部署并发问题）")
        elif model_family.startswith("llama"):
            # Llama模型也暂时只使用第一个部署实例，避免多部署可能的并发问题
            instances_to_use = 1
            logger.info(f"Llama模型 {model} 暂时使用单部署策略（避免多部署并发问题）")
        else:
            instances_to_use = min(len(available_instances), 3)  # 其他开源模型最多用3个实例
            
        instances_per_shard = max(1, num_instances // instances_to_use)
        
        logger.info(f"创建任务分片: {instances_to_use}个实例并行")
        
        for i in range(instances_to_use):
            instance = available_instances[i]
            shard_instances = instances_per_shard
            
            # 最后一个分片处理余数
            if i == instances_to_use - 1:
                shard_instances += num_instances % instances_to_use
                
            shard = TaskShard(
                shard_id=f"{model}_{difficulty}_{i}",
                model=base_model,  # 保持原始大小写，normalize会在存储时处理
                prompt_types=prompt_types,
                difficulty=difficulty,
                task_types=task_types,
                num_instances=shard_instances,
                instance_name=instance.name,  # 保留原始大小写用于API调用
                tool_success_rate=tool_success_rate
            )
            shards.append(shard)
            
        return shards
        
    def execute_shard_async(self, shard: TaskShard, rate_mode: str = "adaptive", result_suffix: str = "", silent: bool = False, max_workers: int = None, shard_index: int = 0) -> subprocess.Popen:
        """异步执行任务分片
        
        Args:
            shard: 任务分片
            rate_mode: 速率模式 - "adaptive" 或 "fixed"
        """
        
        # 标记实例为忙碌
        if shard.instance_name in self.instance_pool:
            self.instance_pool[shard.instance_name].is_busy = True
            self.instance_pool[shard.instance_name].current_load += shard.num_instances
            
        # 计算prompt数量（用于动态调整workers）
        prompt_count = len(shard.prompt_types.split(",")) if "," in shard.prompt_types else 1
        use_prompt_parallel = "--prompt-parallel" if prompt_count > 1 else ""
        
        # 保持原始的instance_name作为deployment
        deployment_name = shard.instance_name
        # 注意：不要在这里修改deployment_name！
        # qwen-key0/1 虚拟实例名会在 batch_test_runner.py 中正确处理
        
        # 根据模型类型和rate_mode调整参数
        if shard.instance_name in self.instance_pool:
            instance = self.instance_pool[shard.instance_name]
            
            # IdealLab开源模型（qwen系列）
            if instance.model_family == "qwen" or shard.instance_name.startswith("qwen-key"):
                # IdealLab API严格限制，必须使用低并发
                # 无论用户设置什么（包括--max-workers），都强制限制为1个worker
                max_workers = 1  # 强制限制：每个key只能1个worker（严格限流）
                qps = 10  # QPS限制为10
                logger.info(f"  IdealLab qwen模型限制: {shard.instance_name} 强制使用 max_workers={max_workers}, qps={qps}")
                logger.info(f"    注意: IdealLab API并发限制严格，忽略--max-workers设置")
            # Azure开源模型（DeepSeek, Llama等）
            elif instance.model_family in ["deepseek-v3", "deepseek-r1", "llama-3.3"]:
                # 如果用户指定了max_workers，优先使用
                if max_workers is not None:
                    base_workers = max_workers
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None  # 移除QPS限制
                    logger.info(f"  Azure开源模型自定义: {prompt_count}个prompt × {base_workers} = {max_workers} workers")
                elif rate_mode == "fixed":
                    # 固定模式：每个prompt 50 workers
                    base_workers = 50
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None  # 移除QPS限制
                    logger.info(f"  Azure开源模型固定模式: {prompt_count}个prompt × {base_workers} = {max_workers} workers")
                else:
                    # 自适应模式：每个prompt 100 workers
                    base_workers = 100
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None  # adaptive不需要QPS
                    logger.info(f"  Azure开源模型自适应模式: {prompt_count}个prompt × {base_workers} = {max_workers} workers")
            # IdealLab闭源模型（单API Key限制）
            elif instance.model_family.startswith("ideallab-"):
                # IdealLab闭源模型严格限制为1个worker，不管有多少prompts
                max_workers = 1  # 强制1个worker，忽略用户设置和prompt数量
                qps = 10  # QPS限制为10
                logger.info(f"  IdealLab闭源模型: max_workers={max_workers}, qps={qps} (严格限流，忽略prompt数量)")
            # Azure闭源模型（单deployment但支持高并发）
            elif instance.model_family.startswith("azure-"):
                # 如果用户指定了max_workers，优先使用
                if max_workers is not None:
                    base_workers = max_workers
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None  # 移除QPS限制
                    logger.info(f"  Azure闭源模型自定义: {prompt_count}个prompt × {base_workers} = {max_workers} workers")
                elif rate_mode == "fixed":
                    # 闭源模型固定模式：单deployment高并发
                    base_workers = 100  # 更高的基础并发
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None  # 移除QPS限制
                    logger.info(f"  Azure闭源模型固定模式: {prompt_count}个prompt × {base_workers} = {max_workers} workers")
                else:
                    # 闭源模型自适应模式：单deployment超高并发
                    base_workers = 200  # 超高基础并发
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None
                    logger.info(f"  Azure闭源模型自适应模式: {prompt_count}个prompt × {base_workers} = {max_workers} workers")
            else:
                # 其他未分类模型 - 使用保守配置
                logger.warning(f"  未识别的模型族 {instance.model_family}，使用默认配置")
                if max_workers is not None:
                    base_workers = max_workers
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None  # 移除QPS限制
                elif rate_mode == "fixed":
                    base_workers = 30  # 保守的固定模式配置
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None  # 移除QPS限制
                else:
                    base_workers = 50  # 保守的自适应模式配置
                    max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                    qps = None
        else:
            # 默认配置
            # 如果用户指定了max_workers，优先使用
            if max_workers is not None:
                base_workers = max_workers
                max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                qps = None  # 移除QPS限制
            elif rate_mode == "fixed":
                base_workers = 30
                max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                qps = None  # 移除QPS限制
            else:
                base_workers = 50
                max_workers = base_workers * prompt_count if prompt_count > 1 else base_workers
                qps = None
        
        # 构建命令
        cmd = [
            "python", "smart_batch_runner.py",
            "--model", shard.model,  # 小写的基础模型名（用于统计）
            "--deployment", deployment_name,  # 使用映射后的部署名（对qwen是模型名，对Azure是实例名）
            "--prompt-types", shard.prompt_types,
            "--difficulty", shard.difficulty,
            "--task-types", shard.task_types,
            "--num-instances", str(shard.num_instances),
            "--max-workers", str(max_workers),
            "--tool-success-rate", str(shard.tool_success_rate),
            "--batch-commit",
            "--checkpoint-interval", "20",
            "--ai-classification",
            "--no-save-logs"  # 避免日志冲突
        ]
        
        # 对于qwen虚拟实例，添加API key索引参数
        if shard.instance_name.startswith("qwen-key"):
            key_index = int(shard.instance_name[-1])  # 从 "qwen-key0" 提取 0
            cmd.extend(["--idealab-key-index", str(key_index)])
            logger.info(f"  使用IdealLab API Key {key_index}")
        elif shard.instance_name == "qwen-serial":
            # 串行模式：不指定key，让smart_batch_runner自己轮询使用
            logger.info(f"  串行模式: 将在内部轮询使用多个API keys")
        
        # 添加静默模式参数（如果是调试进程则不静默）
        debug_process_num = int(os.environ.get('DEBUG_PROCESS_NUM', '1'))
        if os.environ.get('DEBUG_LOG', 'false').lower() == 'true' and shard_index == debug_process_num:
            # 这是要调试的进程，不使用静默模式
            logger.info(f"🔍 进程 {shard_index} 启用调试模式（详细日志）")
        elif silent:
            cmd.append("--silent")
        
        # 根据rate_mode添加参数
        if rate_mode == "fixed":
            if qps is not None:
                cmd.extend(["--no-adaptive", "--qps", str(qps)])
            else:
                cmd.append("--no-adaptive")  # 固定模式但无QPS限制
        else:
            cmd.append("--adaptive")
        
        # 有多个prompt时才添加prompt-parallel
        if use_prompt_parallel:
            cmd.append(use_prompt_parallel)
        
        # 添加结果文件后缀
        if result_suffix:
            cmd.extend(["--result-suffix", result_suffix])
        
        logger.info(f"🚀 启动分片 {shard.shard_id}: {shard.instance_name}")
        logger.info(f"   实例数: {shard.num_instances}, 模型: {shard.model}")
        
        # 启动进程（保留错误输出以便调试）
        # 确保传递环境变量
        env = os.environ.copy()
        
        # 确保所有关键内存优化环境变量被传递
        critical_env_vars = {
            'STORAGE_FORMAT': os.environ.get('STORAGE_FORMAT', 'json'),
            'USE_PARTIAL_LOADING': os.environ.get('USE_PARTIAL_LOADING', 'true'),
            'TASK_LOAD_COUNT': os.environ.get('TASK_LOAD_COUNT', '20'),
            'SKIP_MODEL_LOADING': os.environ.get('SKIP_MODEL_LOADING', 'true'),
            'USE_RESULT_COLLECTOR': os.environ.get('USE_RESULT_COLLECTOR', 'true'),
            'KMP_DUPLICATE_LIB_OK': 'TRUE',
            'PYTHONMALLOC': 'malloc'
        }
        
        # 更新环境变量
        for key, value in critical_env_vars.items():
            if key not in env or not env.get(key):
                env[key] = value
                logger.info(f"   设置{key}={value}给子进程")
            else:
                logger.info(f"   传递{key}={env[key]}给子进程")
        
        # 构建环境变量前缀命令（确保所有关键变量都传递）
        env_prefix = []
        for key, value in critical_env_vars.items():
            env_prefix.append(f'{key}={env[key]}')
        
        cmd_with_env = ['env'] + env_prefix + cmd
        
        process = subprocess.Popen(
            cmd_with_env,
            stdout=None,  # 允许输出到终端 (不重定向)
            stderr=subprocess.STDOUT,  # 将错误输出合并到标准输出
            text=True,
            env=env  # 显式传递环境变量
        )
        
        self.active_tasks.add(shard.shard_id)
        return process
        
    def run_ultra_parallel_test(self, model: str, prompt_types: str, difficulty: str,
                               task_types: str = "all", num_instances: int = 20,
                               rate_mode: str = "adaptive", result_suffix: str = "",
                               silent: bool = False, tool_success_rate: float = 0.8,
                               max_workers: int = None) -> bool:
        """运行超高并行度测试 - 自动检测qwen模型并使用队列调度
        
        Args:
            model: 模型名称
            prompt_types: 提示类型
            difficulty: 难度
            task_types: 任务类型
            num_instances: 实例数
            rate_mode: 速率模式 - "adaptive" 或 "fixed"
        """
        
        # 检测是否是qwen模型，如果是则使用队列调度
        if "qwen" in model.lower() and not self._qwen_batch_mode:
            logger.info(f"\n🎯 检测到Qwen模型，使用队列调度器")
            
            # 获取分配的key
            import re
            match = re.search(r'(\d+b)', model.lower())
            if match:
                model_size = match.group(1)
                KEY_MAP = {"72b": 0, "32b": 1, "14b": 2, "7b": 0, "3b": 1}
                key_idx = KEY_MAP.get(model_size, 0)
            else:
                key_idx = 0
            
            logger.info(f"   模型: {model} → Key{key_idx}")
            logger.info(f"   Prompt类型: {prompt_types}")
            logger.info(f"   难度: {difficulty}")
            
            # 提交到队列
            self.qwen_scheduler.submit_task(
                model=model,
                key_idx=key_idx,
                func=self._run_qwen_test_internal,
                prompt_types=prompt_types,
                difficulty=difficulty,
                task_types=task_types,
                num_instances=num_instances,
                rate_mode=rate_mode,
                result_suffix=result_suffix,
                silent=silent,
                tool_success_rate=tool_success_rate,
                max_workers=max_workers
            )
            
            # 如果不是批量模式，等待完成
            if not self._qwen_batch_mode:
                self.qwen_scheduler.wait_all()
            
            return True
        
        # 非qwen模型或批量模式中的qwen，使用原逻辑
        logger.info(f"\n🔥 启动超高并行测试")
        logger.info(f"   模型: {model}")
        logger.info(f"   Prompt类型: {prompt_types}") 
        logger.info(f"   难度: {difficulty}")
        logger.info(f"   实例数: {num_instances}")
        logger.info(f"   速率模式: {rate_mode}")
        
        # 创建任务分片
        shards = self.create_task_shards(model, prompt_types, difficulty, 
                                        task_types, num_instances, tool_success_rate)
        
        if not shards:
            logger.error("无法创建任务分片")
            return False
            
        logger.info(f"📊 创建了 {len(shards)} 个并行分片")
        
        # 并行启动所有分片（错开启动避免workflow生成冲突）
        processes = []
        start_time = time.time()
        
        # 智能分组启动，平衡并发性和稳定性
        # 策略：第一个分片立即启动，后续分片延迟启动
        # 这样第一个分片的workflow生成可以与后续分片的启动并行
        for i, shard in enumerate(shards):
            if i == 0:
                # 第一个分片立即启动
                process = self.execute_shard_async(shard, rate_mode=rate_mode, result_suffix=result_suffix, silent=silent, max_workers=max_workers, shard_index=i+1)
                processes.append((shard, process))
                logger.info(f"🚀 第一个分片 {shard.shard_id} 立即启动")
            elif i == 1:
                # 第二个分片延迟5秒（现在使用预加载workflow，无需长延迟）
                logger.info(f"⏱️  延迟5秒后启动第二个分片...")
                time.sleep(5)
                process = self.execute_shard_async(shard, rate_mode=rate_mode, result_suffix=result_suffix, silent=silent, max_workers=max_workers, shard_index=i+1)
                processes.append((shard, process))
            else:
                # 第三个及后续分片延迟5秒（预加载workflow，快速启动）
                logger.info(f"⏱️  延迟5秒后启动分片 {i+1}...")
                time.sleep(5)
                process = self.execute_shard_async(shard, rate_mode=rate_mode, result_suffix=result_suffix, silent=silent, max_workers=max_workers, shard_index=i+1)
                processes.append((shard, process))
            
        # 并发等待所有进程完成（真正的并发！）
        logger.info(f"⏳ 并发等待 {len(processes)} 个分片完成...")
        
        success_count = 0
        failed_shards = []
        completed_shards = set()
        
        # 使用轮询方式检查所有进程状态（非阻塞）
        while len(completed_shards) < len(processes):
            for shard, process in processes:
                if shard.shard_id in completed_shards:
                    continue
                    
                # 非阻塞检查进程状态
                poll_result = process.poll()
                if poll_result is not None:  # 进程已结束
                    completed_shards.add(shard.shard_id)
                    
                    if poll_result == 0:
                        logger.info(f"✅ 分片 {shard.shard_id} 完成")
                        success_count += 1
                        self._update_performance_score(shard.instance_name, True)
                    else:
                        # 读取错误输出
                        stderr_output = process.stderr.read() if process.stderr else ""
                        logger.error(f"❌ 分片 {shard.shard_id} 失败 (退出码: {poll_result})")
                        if stderr_output:
                            # 显示更多错误信息，特别是最后的部分
                            lines = stderr_output.strip().split('\n')
                            if len(lines) > 10:
                                logger.error(f"   错误信息（最后10行）:")
                                for line in lines[-10:]:
                                    logger.error(f"     {line}")
                            else:
                                logger.error(f"   错误信息: {stderr_output}")
                        failed_shards.append(shard.shard_id)
                        self._update_performance_score(shard.instance_name, False)
                    
                    # 释放实例
                    if shard.instance_name in self.instance_pool:
                        instance = self.instance_pool[shard.instance_name]
                        instance.is_busy = False
                        instance.current_load = max(0, instance.current_load - shard.num_instances)
                    
                    self.active_tasks.discard(shard.shard_id)
            
            # 短暂休眠避免CPU占用过高
            if len(completed_shards) < len(processes):
                time.sleep(1)
                
        end_time = time.time()
        duration = end_time - start_time
        
        # 报告结果
        logger.info(f"\n📊 并行测试完成")
        logger.info(f"   成功: {success_count}/{len(shards)} 个分片")
        logger.info(f"   总耗时: {duration:.1f}秒")
        logger.info(f"   理论加速比: {len(shards)}x")
        
        if failed_shards:
            logger.warning(f"   失败分片: {failed_shards}")
        
        # 新功能：收集和聚合所有结果（如果启用了collector模式）
        if self.use_collector_mode and success_count > 0:
            self._collect_and_aggregate_results(model)
            
        return len(failed_shards) == 0
    
    def _collect_and_aggregate_results(self, model: str):
        """收集并聚合所有分片的结果（新功能）"""
        logger.info("🔄 开始收集所有分片的测试结果...")
        
        try:
            # 收集所有待处理的结果
            all_results = self.result_collector.collect_all_results(cleanup=True)
            
            if not all_results:
                logger.warning("⚠️ 未发现任何待处理的结果")
                return
            
            # 聚合结果
            logger.info("📊 开始聚合结果...")
            aggregated_db = self.result_aggregator.aggregate_results(all_results)
            
            # 保存到数据库
            self._save_aggregated_results(aggregated_db)
            
            logger.info("✅ 结果收集和聚合完成，数据已安全保存")
            
        except Exception as e:
            logger.error(f"❌ 结果收集失败: {e}")
            # 不抛出异常，让测试继续完成
            
    def _save_aggregated_results(self, aggregated_db: Dict):
        """保存聚合后的结果到数据库"""
        # 使用传统的数据库保存机制，但现在是单线程安全的
        from pathlib import Path
        import json
        
        db_file = Path("pilot_bench_cumulative_results/master_database.json")
        db_file.parent.mkdir(exist_ok=True)
        
        # 如果已有数据库，需要合并
        if db_file.exists():
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    existing_db = json.load(f)
                    
                # 合并数据库（这里现在是安全的，因为只有一个写入者）
                merged_db = self._merge_databases(existing_db, aggregated_db)
            except Exception as e:
                logger.warning(f"读取现有数据库失败，将创建新数据库: {e}")
                merged_db = aggregated_db
        else:
            merged_db = aggregated_db
        
        # 原子写入
        temp_file = db_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(merged_db, f, indent=2, ensure_ascii=False)
        
        temp_file.replace(db_file)
        logger.info(f"💾 数据库已保存到: {db_file}")
        
    def _merge_databases(self, existing: Dict, new: Dict) -> Dict:
        """合并两个数据库（简化版本）"""
        # 这里可以实现更复杂的合并逻辑
        # 现在先做简单的模型级别合并
        merged = existing.copy()
        
        if 'models' in new:
            if 'models' not in merged:
                merged['models'] = {}
            merged['models'].update(new['models'])
        
        merged['last_updated'] = new.get('last_updated', existing.get('last_updated'))
        return merged
        
    def _update_performance_score(self, instance_name: str, success: bool):
        """更新实例性能评分"""
        if instance_name not in self.performance_stats:
            self.performance_stats[instance_name] = {'success': 0, 'total': 0}
            
        stats = self.performance_stats[instance_name]
        stats['total'] += 1
        if success:
            stats['success'] += 1
            
        # 计算成功率作为性能评分
        success_rate = stats['success'] / stats['total']
        self.instance_pool[instance_name].performance_score = success_rate
        
    def _run_qwen_test_internal(self, model: str, prompt_types: str, difficulty: str,
                               task_types: str, num_instances: int, rate_mode: str,
                               result_suffix: str, silent: bool, tool_success_rate: float,
                               max_workers: int) -> bool:
        """内部方法：实际执行qwen测试（在队列中运行）
        
        现在支持多分片并发执行！
        """
        
        # 创建任务分片（现在支持多个分片！）
        shards = self.create_task_shards(model, prompt_types, difficulty,
                                        task_types, num_instances, tool_success_rate)
        
        if not shards:
            logger.error(f"无法创建任务分片: {model}")
            return False
        
        logger.info(f"🚀 启动{len(shards)}个分片并发执行")
        
        # 并发执行所有分片
        processes = []
        for i, shard in enumerate(shards):
            process = self.execute_shard_async(shard, rate_mode=rate_mode,
                                              result_suffix=result_suffix,
                                              silent=silent, max_workers=max_workers,
                                              shard_index=i+1)
            processes.append(process)
            logger.info(f"   分片{i+1}: {shard.instance_name} ({shard.num_instances}个实例)")
        
        # 等待所有分片完成 - 添加超时保护防止无限等待
        success_count = 0
        
        for i, process in enumerate(processes):
            try:
                # 🔧 修复：使用更可靠的超时机制（基于poll而不是signal）
                import time
                
                # 🎯 动态计算超时时间，基于测试规模
                base_timeout = 30  # 基础30分钟
                
                # 获取测试规模参数
                num_instances = int(os.environ.get('NUM_INSTANCES', '20'))
                max_workers = int(os.environ.get('CUSTOM_WORKERS', '50'))
                
                # 根据实例数量调整：每个实例平均1分钟
                instance_timeout = num_instances * 1  
                # 根据worker数量调整：worker少则需要更多时间
                worker_factor = max(1.0, 50.0 / max_workers)  
                
                timeout_minutes = int(base_timeout + instance_timeout * worker_factor)
                timeout_minutes = max(30, min(timeout_minutes, 120))  # 限制在30-120分钟之间
                timeout_seconds = timeout_minutes * 60
                start_time = time.time()
                
                logger.info(f"等待分片{i+1}完成（{num_instances}实例×{max_workers}workers，最多等待{timeout_minutes}分钟）...")
                
                # 轮询等待，避免无限阻塞
                while True:
                    # 检查进程是否结束
                    return_code = process.poll()
                    if return_code is not None:
                        # 进程已结束
                        if return_code == 0:
                            success_count += 1
                            logger.info(f"✅ 分片{i+1}完成")
                        else:
                            logger.error(f"❌ 分片{i+1}失败 (退出码: {return_code})")
                        break
                    
                    # 检查是否超时
                    elapsed = time.time() - start_time
                    if elapsed > timeout_seconds:
                        logger.warning(f"⏰ 分片{i+1}执行超时{timeout_minutes}分钟，强制终止")
                        # 先尝试优雅终止
                        process.terminate()
                        # 等待3秒让进程有机会清理
                        for _ in range(30):  # 3秒
                            if process.poll() is not None:
                                break
                            time.sleep(0.1)
                        
                        # 如果还没结束就强制杀死
                        if process.poll() is None:
                            logger.warning(f"分片{i+1}未响应SIGTERM，使用SIGKILL强制结束")
                            process.kill()
                            process.wait()  # 确保进程完全结束
                        
                        logger.error(f"❌ 分片{i+1}超时终止")
                        break
                    
                    # 短暂休眠避免CPU占用过高
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ 分片{i+1}等待过程中出现异常: {e}")
                # 确保异常情况下也尝试清理进程
                try:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                except:
                    pass
        
        logger.info(f"📊 并发执行结果: {success_count}/{len(processes)} 分片成功")
        
        return success_count == len(processes)
    
    def run_batch_qwen_tests(self, models: List[str], prompt_types: str,
                            difficulties: List[str], task_types: str = "all",
                            num_instances: int = 20, rate_mode: str = "fixed",
                            result_suffix: str = "", silent: bool = False,
                            tool_success_rate: float = 0.8, max_workers: int = None) -> bool:
        """批量运行qwen测试 - 专为Phase 5.2等场景设计
        
        使用队列调度器确保：
        1. 同一key的任务串行执行
        2. 不同key之间并行执行
        3. 没有API key冲突
        """
        
        logger.info(f"\n🚀 批量Qwen测试（队列调度模式）")
        logger.info(f"   模型数: {len(models)}")
        logger.info(f"   难度: {difficulties}")
        logger.info(f"   总任务数: {len(models) * len(difficulties)}")
        
        # 设置批量模式
        self._qwen_batch_mode = True
        
        # 提交所有任务
        task_count = 0
        for difficulty in difficulties:
            for model in models:
                if "qwen" in model.lower():
                    task_count += 1
                    self.run_ultra_parallel_test(
                        model=model,
                        prompt_types=prompt_types,
                        difficulty=difficulty,
                        task_types=task_types,
                        num_instances=num_instances,
                        rate_mode=rate_mode,
                        result_suffix=result_suffix,
                        silent=silent,
                        tool_success_rate=tool_success_rate,
                        max_workers=max_workers
                    )
        
        logger.info(f"📋 已提交 {task_count} 个任务到队列")
        
        # 等待所有任务完成
        logger.info(f"⏳ 等待所有队列任务完成...")
        self.qwen_scheduler.wait_all()
        
        # 清除批量模式
        self._qwen_batch_mode = False
        
        logger.info(f"✅ 批量Qwen测试完成")
        return True
    
    def get_resource_utilization(self) -> Dict:
        """获取资源利用率统计"""
        total_capacity = sum(inst.max_workers for inst in self.instance_pool.values())
        current_load = sum(inst.current_load for inst in self.instance_pool.values())
        busy_instances = sum(1 for inst in self.instance_pool.values() if inst.is_busy)
        
        return {
            "total_instances": len(self.instance_pool),
            "busy_instances": busy_instances,
            "total_capacity": total_capacity,
            "current_load": current_load,
            "utilization_rate": current_load / total_capacity if total_capacity > 0 else 0,
            "active_tasks": len(self.active_tasks)
        }

def main():
    """命令行接口"""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description="Ultra Parallel Test Runner")
    parser.add_argument("--model", required=True, help="模型名称")
    parser.add_argument("--prompt-types", required=True, help="Prompt类型")
    parser.add_argument("--difficulty", default="easy", help="难度")
    parser.add_argument("--task-types", default="all", help="任务类型")
    parser.add_argument("--num-instances", type=int, default=20, help="实例数量")
    parser.add_argument("--rate-mode", default="adaptive", 
                       choices=["adaptive", "fixed"],
                       help="速率模式: adaptive(动态调整) 或 fixed(固定速率)")
    parser.add_argument("--result-suffix", default="", 
                       help="结果文件后缀(用于区分闭源/开源模型)")
    parser.add_argument("--silent", action="store_true",
                       help="静默模式，减少输出")
    parser.add_argument("--tool-success-rate", type=float, default=0.8,
                       help="工具成功率(0.0-1.0)")
    parser.add_argument("--max-workers", type=int, default=None,
                       help="每个分片的最大并发workers数")
    
    args = parser.parse_args()
    
    # 也可以从环境变量读取rate_mode
    rate_mode = args.rate_mode
    if os.environ.get("RATE_MODE"):
        rate_mode = os.environ.get("RATE_MODE")
        logger.info(f"使用环境变量 RATE_MODE: {rate_mode}")
    
    # 注意：保留logger的INFO级别以显示高层级进度信息
    # silent参数只控制详细的执行输出，不影响主要进度显示
    
    runner = UltraParallelRunner()
    
    # 显示资源状态
    util = runner.get_resource_utilization()
    logger.info(f"资源池状态: {util['total_instances']}个实例, 容量{util['total_capacity']}")
    
    # 执行测试
    success = runner.run_ultra_parallel_test(
        model=args.model,
        prompt_types=args.prompt_types,
        difficulty=args.difficulty,
        task_types=args.task_types,
        num_instances=args.num_instances,
        rate_mode=rate_mode,
        result_suffix=args.result_suffix,
        silent=args.silent,
        tool_success_rate=args.tool_success_rate,
        max_workers=args.max_workers
    )
    
    # 最终统计
    final_util = runner.get_resource_utilization()
    logger.info(f"最终利用率: {final_util['utilization_rate']:.1%}")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())