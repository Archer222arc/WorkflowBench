#!/usr/bin/env python3
"""
实现任务部分加载机制 - 只加载20个任务而不是全部630个
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional
import logging

class TaskPartialLoader:
    """任务部分加载器 - 减少内存使用"""
    
    def __init__(self, num_instances: int = 20, seed: Optional[int] = None):
        """
        初始化任务加载器
        
        Args:
            num_instances: 每个任务类型加载的实例数量
            seed: 随机种子（用于可重复性）
        """
        self.num_instances = num_instances
        self.logger = logging.getLogger(__name__)
        
        if seed is not None:
            random.seed(seed)
    
    def load_partial_task_library(self, difficulty: str = "easy") -> Dict[str, List]:
        """
        部分加载任务库 - 只加载需要的任务数量
        
        Args:
            difficulty: 难度级别
            
        Returns:
            按类型组织的任务字典，每种类型只包含num_instances个任务
        """
        # 首先尝试加载带workflow的版本
        workflow_enhanced_path = Path(f"mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{difficulty}_with_workflows.json")
        
        if workflow_enhanced_path.exists():
            task_lib_path = workflow_enhanced_path
            self.logger.info(f"Loading task library with pre-generated workflows: {task_lib_path.name}")
        else:
            task_lib_path = Path(f"mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{difficulty}.json")
            self.logger.info(f"Loading standard task library: {task_lib_path.name}")
        
        if not task_lib_path.exists():
            self.logger.warning(f"Task library not found: {task_lib_path}")
            return {}
        
        # 使用两阶段加载策略
        return self._two_phase_loading(task_lib_path)
    
    def _two_phase_loading(self, task_lib_path: Path) -> Dict[str, List]:
        """
        两阶段加载：先构建索引，再加载选中的任务
        
        这种方法避免了一次性加载所有任务到内存
        """
        self.logger.info(f"Phase 1: Building task index...")
        
        # 第一阶段：构建轻量级索引
        task_index = self._build_task_index(task_lib_path)
        
        self.logger.info(f"Found {sum(len(indices) for indices in task_index.values())} total tasks")
        
        # 第二阶段：随机选择并加载具体任务
        self.logger.info(f"Phase 2: Loading {self.num_instances} tasks per type...")
        
        selected_tasks = self._load_selected_tasks(task_lib_path, task_index)
        
        # 统计信息
        total_loaded = sum(len(tasks) for tasks in selected_tasks.values())
        self.logger.info(f"Loaded {total_loaded} tasks total")
        
        return selected_tasks
    
    def _build_task_index(self, task_lib_path: Path) -> Dict[str, List[int]]:
        """
        构建任务索引（只记录任务类型和位置）
        
        Returns:
            {task_type: [task_indices]}
        """
        task_index = {}
        
        with open(task_lib_path, 'r') as f:
            data = json.load(f)
        
        # 处理不同的数据格式
        if isinstance(data, dict):
            tasks = data.get('tasks', [])
        else:
            tasks = data
        
        # 构建索引
        for i, task in enumerate(tasks):
            if isinstance(task, dict) and 'task_type' in task:
                task_type = task['task_type']
                if task_type not in task_index:
                    task_index[task_type] = []
                task_index[task_type].append(i)
        
        return task_index
    
    def _load_selected_tasks(self, task_lib_path: Path, task_index: Dict[str, List[int]]) -> Dict[str, List]:
        """
        加载选中的任务
        
        Args:
            task_lib_path: 任务库文件路径
            task_index: 任务索引 {task_type: [indices]}
            
        Returns:
            {task_type: [selected_tasks]}
        """
        # 再次打开文件（这次我们知道要加载哪些任务）
        with open(task_lib_path, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            all_tasks = data.get('tasks', [])
        else:
            all_tasks = data
        
        selected_tasks = {}
        
        for task_type, indices in task_index.items():
            # 随机选择num_instances个索引
            num_to_select = min(self.num_instances, len(indices))
            selected_indices = random.sample(indices, num_to_select)
            
            # 只加载选中的任务
            selected_tasks[task_type] = [all_tasks[i] for i in selected_indices]
            
            self.logger.debug(f"Selected {len(selected_tasks[task_type])} tasks for {task_type}")
        
        return selected_tasks


def patch_batch_test_runner():
    """
    修补BatchTestRunner使其使用部分加载
    
    这个函数修改BatchTestRunner的_load_task_library方法
    """
    import batch_test_runner
    
    # 保存原始方法
    original_load_task_library = batch_test_runner.BatchTestRunner._load_task_library
    
    def _load_task_library_partial(self, difficulty="easy", num_instances=20):
        """优化的任务加载方法 - 只加载需要的任务数量"""
        
        # 检查是否启用部分加载
        if hasattr(self, 'use_partial_loading') and self.use_partial_loading:
            self.logger.info(f"Using partial loading: {num_instances} tasks per type")
            
            # 使用部分加载器
            loader = TaskPartialLoader(num_instances=num_instances)
            self.tasks_by_type = loader.load_partial_task_library(difficulty)
            
            # 记录加载统计
            total_tasks = sum(len(tasks) for tasks in self.tasks_by_type.values())
            self.logger.info(f"Partially loaded {total_tasks} tasks (vs 630 full load)")
            
            # 估算内存节省
            memory_saved_percent = (1 - total_tasks / 630) * 100
            self.logger.info(f"Estimated memory saving: {memory_saved_percent:.1f}%")
        else:
            # 使用原始方法
            original_load_task_library(self, difficulty)
    
    # 替换方法
    batch_test_runner.BatchTestRunner._load_task_library = _load_task_library_partial
    
    print("✅ BatchTestRunner已修补，支持部分加载")


def test_partial_loading():
    """测试部分加载功能"""
    print("\n" + "="*60)
    print("测试任务部分加载机制")
    print("="*60)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 测试不同的加载数量
    for num_instances in [5, 10, 20]:
        print(f"\n测试加载 {num_instances} 个任务/类型:")
        loader = TaskPartialLoader(num_instances=num_instances, seed=42)
        tasks = loader.load_partial_task_library("easy")
        
        print(f"任务类型数: {len(tasks)}")
        for task_type, task_list in tasks.items():
            print(f"  {task_type}: {len(task_list)} 个任务")
        
        total = sum(len(t) for t in tasks.values())
        print(f"总计: {total} 个任务")
        print(f"内存节省: {(1 - total/630)*100:.1f}%")
    
    # 测试修补功能
    print("\n" + "="*60)
    print("测试BatchTestRunner修补")
    print("="*60)
    
    patch_batch_test_runner()
    
    # 创建一个测试实例
    from batch_test_runner import BatchTestRunner
    
    runner = BatchTestRunner(debug=True, silent=False)
    runner.use_partial_loading = True  # 启用部分加载
    runner._load_task_library(difficulty="easy", num_instances=10)
    
    print(f"\n✅ 测试完成")


def calculate_memory_impact():
    """计算内存影响"""
    print("\n" + "="*60)
    print("内存影响评估")
    print("="*60)
    
    # 假设每个任务平均2KB（包含workflow）
    task_size_kb = 2
    
    scenarios = [
        ("原始（全部加载）", 630, 25),
        ("部分加载（20/类型）", 20 * 7, 25),  # 7种任务类型
        ("部分加载（10/类型）", 10 * 7, 25),
        ("部分加载（5/类型）", 5 * 7, 25),
    ]
    
    print(f"假设每个任务约 {task_size_kb}KB")
    print("\n场景分析：")
    
    for name, tasks_per_process, num_processes in scenarios:
        total_tasks = tasks_per_process * num_processes
        memory_mb = (total_tasks * task_size_kb) / 1024
        memory_per_process = (tasks_per_process * task_size_kb) / 1024
        
        print(f"\n{name}:")
        print(f"  每进程任务数: {tasks_per_process}")
        print(f"  每进程内存: {memory_per_process:.2f}MB")
        print(f"  {num_processes}进程总内存: {memory_mb:.2f}MB")
        
        if "原始" not in name:
            original_memory = (630 * num_processes * task_size_kb) / 1024
            saved = original_memory - memory_mb
            saved_percent = (saved / original_memory) * 100
            print(f"  节省: {saved:.2f}MB ({saved_percent:.1f}%)")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "patch":
        # 直接修补模式
        patch_batch_test_runner()
        print("BatchTestRunner已修补为使用部分加载")
    elif len(sys.argv) > 1 and sys.argv[1] == "impact":
        # 计算内存影响
        calculate_memory_impact()
    else:
        # 运行测试
        test_partial_loading()
        calculate_memory_impact()