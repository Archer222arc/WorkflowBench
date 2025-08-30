# Embedding Manager 共享机制分析

## 1. 当前问题

### 内存占用分析
```
当前情况（25个并发进程）：
- 每个进程独立创建 embedding_manager
- 每个 embedding_manager ≈ 50MB
- 总内存占用：25 × 50MB = 1.25GB（仅embedding manager）
```

### 重复初始化问题
```python
# 每个MockGenerator都会执行：
from mcp_embedding_manager import get_embedding_manager
self.embedding_manager = get_embedding_manager()  # 每次都创建新实例
```

## 2. 共享方案设计

### 方案A：使用multiprocessing.Manager（推荐）

```python
import multiprocessing
from multiprocessing import Manager

class SharedEmbeddingManager:
    """共享的Embedding Manager包装器"""
    
    _shared_instance = None
    _manager = None
    
    @classmethod
    def get_shared_instance(cls):
        if cls._shared_instance is None:
            # 创建进程间共享的manager
            cls._manager = Manager()
            
            # 在主进程中创建embedding manager
            from mcp_embedding_manager import get_embedding_manager
            real_manager = get_embedding_manager()
            
            # 创建共享代理
            cls._shared_instance = cls._manager.Namespace()
            cls._shared_instance.embeddings = cls._manager.dict()
            cls._shared_instance.ready = True
            
        return cls._shared_instance
```

### 方案B：预加载到主进程，传递引用

```python
# 在 smart_batch_runner.py 或 ultra_parallel_runner.py 中
class OptimizedBatchRunner:
    def __init__(self):
        # 主进程创建一次
        self.shared_embedding_manager = self._create_shared_embedding_manager()
    
    def _create_shared_embedding_manager(self):
        """创建共享的embedding manager"""
        from mcp_embedding_manager import get_embedding_manager
        manager = get_embedding_manager()
        
        # 预加载常用embeddings到缓存
        manager.preload_common_tools()
        
        return manager
    
    def create_worker_args(self, task):
        """为worker创建参数，包含共享manager引用"""
        return {
            'task': task,
            'embedding_manager_ref': self.shared_embedding_manager,
            # ... 其他参数
        }
```

### 方案C：使用单例模式（当前已部分实现）

```python
# mcp_embedding_manager.py 已经有单例模式
class MCPEmbeddingManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**问题**：在多进程环境下，每个进程有独立的Python解释器，单例模式失效。

## 3. 最优实现方案

### 混合方案：进程池 + 共享缓存

```python
# 新文件：shared_resource_manager.py
import multiprocessing as mp
from multiprocessing import Queue, Manager
import pickle

class SharedResourceManager:
    """管理进程间共享的资源"""
    
    def __init__(self):
        self.manager = Manager()
        self.shared_cache = self.manager.dict()
        self.embedding_queue = Queue()
        
        # 在主进程中初始化embedding manager
        self._init_embedding_manager()
    
    def _init_embedding_manager(self):
        """主进程中初始化一次"""
        from mcp_embedding_manager import get_embedding_manager
        self.embedding_manager = get_embedding_manager()
        
        # 预计算常用embeddings
        common_tools = [
            'file_operations_reader',
            'file_operations_writer',
            'data_processing_parser',
            # ... 更多常用工具
        ]
        
        for tool in common_tools:
            embedding = self.embedding_manager.get_embedding(tool)
            self.shared_cache[tool] = embedding
        
        print(f"✅ 预加载 {len(self.shared_cache)} 个工具的embeddings")
    
    def get_embedding(self, text):
        """获取embedding（优先使用缓存）"""
        if text in self.shared_cache:
            return self.shared_cache[text]
        
        # 如果不在缓存中，请求主进程计算
        # （这里简化实现，实际需要更复杂的通信机制）
        return None
```

### 修改MockGenerator使用共享资源

```python
class MockGenerator:
    def __init__(self, shared_resources=None):
        # ... 其他初始化代码 ...
        
        if shared_resources and hasattr(shared_resources, 'embedding_manager'):
            # 使用共享的embedding manager
            self.embedding_manager = shared_resources.embedding_manager
            print("✅ 使用共享的embedding manager")
        else:
            # 降级到独立创建
            from mcp_embedding_manager import get_embedding_manager
            self.embedding_manager = get_embedding_manager()
            print("⚠️ 创建独立的embedding manager")
```

## 4. 实施步骤

### Step 1：创建共享资源管理器
```python
# 在 batch_test_runner.py 顶部
_shared_resources = None

def get_shared_resources():
    global _shared_resources
    if _shared_resources is None:
        _shared_resources = SharedResourceManager()
    return _shared_resources
```

### Step 2：修改BatchTestRunner初始化
```python
def _lazy_init(self):
    # ... 其他代码 ...
    
    # 获取共享资源
    shared_res = get_shared_resources()
    
    # 创建MockGenerator时传入共享资源
    self.generator = MockGenerator(shared_resources=shared_res)
```

### Step 3：在并行执行时使用
```python
# ultra_parallel_runner.py
def run_parallel_tests(self, tasks):
    # 主进程创建共享资源
    shared_resources = SharedResourceManager()
    
    # 创建进程池
    with ProcessPoolExecutor(max_workers=25) as executor:
        futures = []
        for task in tasks:
            # 每个任务使用相同的共享资源
            future = executor.submit(
                run_single_test_with_shared,
                task,
                shared_resources
            )
            futures.append(future)
```

## 5. 预期效果

### 内存优化
| 组件 | 当前（25进程） | 优化后 | 节省 |
|-----|---------------|--------|------|
| Embedding Manager | 1.25GB | 50MB | 1.2GB |
| 任务库 | 320MB | 320MB | 0 |
| 其他 | 100MB | 100MB | 0 |
| **总计** | **1.67GB** | **470MB** | **1.2GB** |

### 性能影响
- ✅ **内存大幅减少**：节省1.2GB
- ✅ **初始化更快**：只需初始化一次
- ⚠️ **可能的延迟**：进程间通信开销
- ⚠️ **复杂度增加**：需要处理进程间同步

## 6. 快速实现方案（最小改动）

如果要快速实现，可以采用最简单的方案：

```python
# 修改 batch_test_runner.py
class MockGenerator:
    # 类级别的共享实例
    _shared_embedding_manager = None
    
    def __init__(self):
        # ... 其他代码 ...
        
        # 尝试重用已有的embedding manager
        if MockGenerator._shared_embedding_manager is None:
            from mcp_embedding_manager import get_embedding_manager
            MockGenerator._shared_embedding_manager = get_embedding_manager()
            print("📦 创建新的embedding manager")
        
        self.embedding_manager = MockGenerator._shared_embedding_manager
        print("♻️ 重用existing embedding manager")
```

**注意**：这在多线程中有效，但多进程中每个进程仍会创建一个实例。

## 7. 建议

### 短期方案（立即可做）
1. 先保持当前实现（每进程50MB）
2. 确保5.3测试能运行
3. 总内存仍然可接受（<500MB）

### 中期方案（值得实施）
1. 实现进程池级别的共享
2. 使用multiprocessing.Manager
3. 预加载常用embeddings

### 长期方案（如果需要）
1. 实现完整的资源池管理
2. 支持动态扩缩容
3. 添加监控和调试工具

## 8. 结论

**是的，可以共享embedding manager！** 这将带来显著的内存优化：
- 当前：25进程 × 50MB = 1.25GB
- 优化后：1 × 50MB = 50MB
- **节省：1.2GB**

但考虑到实现复杂度和当前紧急性，建议：
1. **先运行5.3测试**（当前方案已可用）
2. **之后实施共享优化**（作为性能改进）