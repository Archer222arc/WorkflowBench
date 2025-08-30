# Ultra并发架构修正分析

## 🔍 **真实的Ultra并发层次结构**

基于代码深入分析，不同API provider有完全不同的分片策略：

```
Ultra并发层次结构 (修正版)：
├── 1️⃣ ultra_parallel_runner.py (智能分片调度)
│   │
│   ├── 🔵 **Qwen模型 (IdealLab开源)** - 3-key分片策略
│   │   ├── 创建3个分片 (qwen-key0/1/2)
│   │   ├── 均匀分配任务到3个API keys
│   │   ├── 每key独立并发执行
│   │   └── 虚拟实例映射: qwen-key0→实际qwen模型
│   │
│   ├── 🟠 **Azure开源模型** - 3-instance分片策略  
│   │   ├── DeepSeek-V3-0324: 3个实例 (-1/-2/-3)
│   │   ├── DeepSeek-R1-0528: 3个实例 (-1/-2/-3)  
│   │   ├── Llama-3.3-70B-Instruct: 3个实例 (-1/-2/-3)
│   │   ├── 创建3个分片，分布到3个部署实例
│   │   └── 高并发策略 (50-100 workers/实例)
│   │
│   ├── 🔴 **IdealLab闭源模型** - 单分片策略
│   │   ├── o3-0416-global: 1个分片
│   │   ├── gemini-2.5-flash-06-17: 1个分片
│   │   ├── kimi-k2: 1个分片
│   │   ├── 避免API Key冲突，使用单分片
│   │   └── 保守并发 (5 workers max)
│   │
│   └── 🟢 **Azure闭源模型** - 单分片高并发策略
│       ├── gpt-4o-mini: 1个分片
│       ├── gpt-5-mini: 1个分片  
│       ├── 单deployment优化
│       └── 高并发策略 (50-100 workers)
│
├── 2️⃣ smart_batch_runner.py (分片执行) 
│   │
│   ├── **Qwen分片执行**:
│   │   ├── 接收虚拟实例名 (qwen-key0)
│   │   ├── 提取API key索引 (--ideallab-key-index 0)
│   │   ├── 路由到对应的IdealLab API key
│   │   ├── 保守并发 (workers=2, 避免过载)
│   │   └── 使用原始模型名存储统计
│   │
│   ├── **Azure实例分片执行**:
│   │   ├── 接收实例名 (DeepSeek-V3-0324-2)  
│   │   ├── 直接调用Azure API部署
│   │   ├── 极高并发 (workers=50-100)
│   │   ├── normalize模型名统一存储
│   │   └── 实例数据合并到基础模型名
│   │
│   └── **闭源模型分片执行**:
│       ├── 单分片处理所有任务
│       ├── API rate限制保护
│       ├── 错误重试机制
│       └── 统一模型名存储
│
├── 3️⃣ enhanced_cumulative_manager.py (数据聚合)
│   ├── **模型名标准化**: normalize_model_name()
│   │   ├── DeepSeek-V3-0324-2 → DeepSeek-V3-0324
│   │   ├── qwen2.5-72b-instruct → qwen2.5-72b-instruct
│   │   └── 保持IdealLab和闭源模型原名
│   │
│   ├── **多进程写入协调**:
│   │   ├── 接收所有分片的写入请求
│   │   ├── 按标准化模型名聚合
│   │   ├── 批量缓冲机制 (buffer_size=3)
│   │   └── 定期flush到数据库
│   │
│   └── **数据完整性保护**:
│       ├── 字段命名一致性 (success↔successful)
│       ├── overall_stats实时重建
│       ├── 层次化数据结构维护
│       └── 错误分类聚合
│
└── 4️⃣ master_database.json (最终存储)
    ├── **统一模型命名空间**:
    │   ├── DeepSeek-V3-0324 (合并3个Azure实例)
    │   ├── qwen2.5-72b-instruct (合并3个API keys)
    │   └── o3-0416-global (单一IdealLab API)
    │
    ├── **层次化数据结构**:
    │   ├── models/[model]/by_prompt_type/[prompt]/by_tool_success_rate/[rate]/by_difficulty/[diff]/by_task_type/[task]
    │   ├── 支持复杂查询和统计分析
    │   └── 自动聚合overall_stats
    │
    └── **并发安全保护**:
        ├── file_lock_manager保护 (建议启用)
        ├── 原子写入操作
        ├── 数据完整性验证
        └── 自动修复机制
```

## 🎯 **关键差异总结**

### **分片策略差异**:

| API Provider | 分片数量 | 并发策略 | 实例类型 | 数据合并 |
|-------------|----------|----------|----------|----------|
| **Qwen (IdealLab开源)** | 3个分片 | 3个API keys | 虚拟实例 (qwen-key0/1/2) | 按模型名合并 |
| **Azure开源** | 3个分片 | 3个部署实例 | 物理实例 (-1/-2/-3后缀) | normalize后合并 |
| **IdealLab闭源** | 1个分片 | 单API key | 原始模型名 | 无需合并 |
| **Azure闭源** | 1个分片 | 单部署高并发 | 原始模型名 | 无需合并 |

### **并发参数差异**:

```python
# Qwen模型 (IdealLab)
workers = 2          # 保守设置，避免过载
qps = 10             # 适中QPS
keys = 3             # 3个API keys分担负载

# Azure开源模型  
workers = 50-100     # 极高并发
qps = 100-200        # 极高QPS
instances = 3        # 3个Azure部署

# IdealLab闭源模型
workers = 5          # 严格限制
qps = 10             # 保守QPS
instances = 1        # 单一API key

# Azure闭源模型
workers = 50-100     # 高并发  
qps = 100-200        # 高QPS
instances = 1        # 单一deployment
```

### **数据流差异**:

```
🔵 Qwen流程:
ultra_parallel_runner → [qwen-key0, qwen-key1, qwen-key2] → 
smart_batch_runner (--ideallab-key-index) → 
IdealLab API (3个keys) → 
enhanced_cumulative_manager (qwen2.5-72b-instruct) → 
master_database.json

🟠 Azure开源流程:
ultra_parallel_runner → [DeepSeek-V3-0324, DeepSeek-V3-0324-2, DeepSeek-V3-0324-3] →
smart_batch_runner → 
Azure API (3个deployments) → 
enhanced_cumulative_manager (normalize: DeepSeek-V3-0324) →
master_database.json

🔴 IdealLab闭源流程:
ultra_parallel_runner → [o3-0416-global] →
smart_batch_runner → 
IdealLab API (单一key) →
enhanced_cumulative_manager (o3-0416-global) →
master_database.json
```

这个修正版本准确反映了不同API provider的不同并发策略和数据流！