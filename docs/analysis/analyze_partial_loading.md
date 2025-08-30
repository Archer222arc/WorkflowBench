# 只读取20个任务的实现方案分析

## 核心问题
当前`_load_task_library`一次性加载所有630个任务，但每次测试只需要20个任务实例。

## 实现挑战

### 1. 随机选择的问题
```python
# 当前实现
task = random.choice(tasks)  # 需要所有任务在内存中
```
- 需要从630个任务中随机选择
- 如果只加载20个，失去了真正的随机性

### 2. JSON文件结构限制
```json
{
  "tasks": [
    {...},  // task 1
    {...},  // task 2
    ...     // 630个任务
  ]
}
```
- JSON必须完整解析才能访问内部数组
- 无法直接读取第N个任务

## 解决方案

### 方案1：两阶段加载（推荐）
```python
def _load_task_library_lightweight(self, difficulty="easy", num_instances=20):
    """轻量级任务加载 - 只加载需要的任务数量"""
    
    # 第一阶段：只读取任务ID和类型（轻量级索引）
    task_index = self._build_task_index(difficulty)
    
    # 第二阶段：随机选择并加载具体任务
    selected_indices = {}
    for task_type in ["simple_task", "basic_task", ...]:
        # 随机选择num_instances个索引
        type_indices = task_index[task_type]
        selected = random.sample(type_indices, min(num_instances, len(type_indices)))
        selected_indices[task_type] = selected
    
    # 只加载选中的任务
    self.tasks_by_type = self._load_selected_tasks(selected_indices)
```

### 方案2：流式JSON解析
```python
import ijson  # 增量JSON解析库

def _stream_load_tasks(self, difficulty="easy", num_instances=20):
    """流式加载任务，不需要一次性加载整个文件"""
    
    filepath = f"task_library_{difficulty}_with_workflows.json"
    selected_tasks = {}
    
    with open(filepath, 'rb') as file:
        # 使用ijson流式解析
        parser = ijson.items(file, 'tasks.item')
        
        task_pool = defaultdict(list)
        for task in parser:
            task_type = task['task_type']
            
            # 使用水塘抽样算法保持随机性
            if len(task_pool[task_type]) < num_instances:
                task_pool[task_type].append(task)
            else:
                # 随机替换已选任务
                j = random.randint(0, task_counter[task_type])
                if j < num_instances:
                    task_pool[task_type][j] = task
            
            task_counter[task_type] += 1
    
    return task_pool
```

### 方案3：预处理任务库分片
```python
def preprocess_task_library():
    """预处理：将大任务库分成小文件"""
    
    # 读取原始任务库
    with open("task_library_with_workflows.json") as f:
        data = json.load(f)
    
    # 按类型分片保存
    for task_type in ["simple_task", "basic_task", ...]:
        type_tasks = [t for t in data['tasks'] if t['task_type'] == task_type]
        
        # 保存为独立文件
        with open(f"tasks/{task_type}_{difficulty}.json", 'w') as f:
            json.dump(type_tasks, f)
    
    # 创建索引文件
    index = {
        task_type: {
            "file": f"tasks/{task_type}_{difficulty}.json",
            "count": len(type_tasks)
        }
    }
```

### 方案4：任务采样缓存
```python
class TaskSamplingCache:
    """任务采样缓存 - 预生成随机任务集"""
    
    def __init__(self):
        self.cache_file = "task_samples_cache.json"
        self.sample_sets = []
        
    def generate_sample_sets(self, num_sets=100, tasks_per_set=20):
        """预生成100组随机任务集，每组20个任务"""
        all_tasks = self._load_all_tasks()
        
        for i in range(num_sets):
            sample = {}
            for task_type in task_types:
                sample[task_type] = random.sample(
                    all_tasks[task_type], 
                    min(tasks_per_set, len(all_tasks[task_type]))
                )
            self.sample_sets.append(sample)
        
        # 保存到缓存文件
        self._save_cache()
    
    def get_random_sample(self):
        """获取一个预生成的随机任务集"""
        return random.choice(self.sample_sets)
```

## 实现难度和效果对比

| 方案 | 实现难度 | 内存节省 | 随机性 | 性能影响 |
|-----|---------|---------|--------|----------|
| 两阶段加载 | 中等 | 95% | 保持 | 轻微增加I/O |
| 流式解析 | 较高 | 97% | 保持 | 解析较慢 |
| 预处理分片 | 简单 | 96% | 保持 | 需要预处理 |
| 采样缓存 | 简单 | 97% | 有限 | 最快 |

## 推荐实施方案

### 短期方案：任务采样缓存
1. 预生成100组任务集（每组20个任务）
2. 运行时随机选择一组
3. 内存使用：630个任务 → 20个任务（减少96.8%）

### 中期方案：两阶段加载
1. 先加载轻量级索引
2. 随机选择后只加载需要的任务
3. 保持完全的随机性

### 代码修改示例
```python
# batch_test_runner.py
def _load_task_library(self, difficulty="easy", num_instances=20):
    """修改为只加载需要的任务数量"""
    
    # 如果有缓存的任务集，直接使用
    if self.use_task_cache:
        cache_file = f"task_cache_{difficulty}_{num_instances}.json"
        if Path(cache_file).exists():
            with open(cache_file) as f:
                self.tasks_by_type = json.load(f)
                self.logger.info(f"Loaded {num_instances} cached tasks per type")
                return
    
    # 否则使用两阶段加载
    task_lib_path = Path(f"task_library_{difficulty}_with_workflows.json")
    
    # 第一阶段：构建索引（轻量级）
    task_index = {}
    with open(task_lib_path) as f:
        data = json.load(f)
        tasks = data.get('tasks', data)
        
        for i, task in enumerate(tasks):
            task_type = task.get('task_type')
            if task_type not in task_index:
                task_index[task_type] = []
            task_index[task_type].append(i)
    
    # 第二阶段：随机选择并加载
    self.tasks_by_type = {}
    for task_type, indices in task_index.items():
        # 随机选择num_instances个
        selected_indices = random.sample(
            indices, 
            min(num_instances, len(indices))
        )
        
        # 只加载选中的任务
        self.tasks_by_type[task_type] = [
            tasks[i] for i in selected_indices
        ]
    
    self.logger.info(f"Loaded {num_instances} tasks per type (total: {sum(len(v) for v in self.tasks_by_type.values())})")
```

## 内存影响评估

### 当前状态
- 加载630个任务（带workflow）：62MB/进程
- 25个进程：1.55GB

### 优化后（只加载20个任务）
- 加载20个任务：62MB × (20/630) = 2MB/进程
- 25个进程：50MB

### 节省效果
- 内存节省：1.5GB（96.8%）
- 加载时间：减少95%
- I/O操作：可能略有增加（需要索引）