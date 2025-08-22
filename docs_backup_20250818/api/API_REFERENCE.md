# API 参考文档

## 📚 概述

本文档提供了 WorkflowBench Scale-Up 系统的完整 API 参考，包括所有核心类、方法和配置选项。

## 🎯 核心API

### 1. MDP框架 API

#### 1.1 GeneralizedMDPFramework

**主要类定义:**

```python
class GeneralizedMDPFramework:
    """
    广义马尔可夫决策过程框架
    """
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化MDP框架
        
        Args:
            config: 配置字典，包含状态维度、动作维度等参数
        """
```

**核心方法:**

```python
def create_state(self, task_description: str, context: Dict[str, Any]) -> TaskState:
    """
    创建任务状态
    
    Args:
        task_description: 任务描述文本
        context: 任务上下文信息
        
    Returns:
        TaskState: 初始化的任务状态对象
    """

def select_action(self, state: TaskState, policy: PolicyNetwork) -> MDPAction:
    """
    基于当前状态选择动作
    
    Args:
        state: 当前任务状态
        policy: 策略网络
        
    Returns:
        MDPAction: 选择的动作对象
    """

def calculate_reward(self, state: TaskState, action: MDPAction, 
                    next_state: TaskState, execution_result: Any) -> float:
    """
    计算奖励值
    
    Args:
        state: 当前状态
        action: 执行的动作
        next_state: 下一个状态
        execution_result: 执行结果
        
    Returns:
        float: 奖励值 (-1.0 到 1.0)
    """
```

#### 1.2 TaskState

```python
@dataclass
class TaskState:
    """任务状态数据类"""
    task_id: str                                    # 任务唯一标识
    current_step: int                              # 当前执行步骤
    tool_states: Dict[str, ToolExecutionStatus]    # 工具状态映射
    workflow_context: Dict[str, Any]               # 工作流上下文
    error_history: List[str]                       # 错误历史记录
    execution_trace: List[Dict]                    # 执行轨迹
    phase: int = 1                                 # 执行阶段
    step_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_feature_vector(self) -> np.ndarray:
        """
        转换为特征向量
        
        Returns:
            np.ndarray: 512维特征向量
        """
```

#### 1.3 ActionType枚举

```python
class ActionType(Enum):
    """MDP动作类型枚举"""
    INVOKE_TOOL = "invoke_tool"              # 调用工具
    VALIDATE_OUTPUT = "validate_output"      # 验证输出
    RETRY_TOOL = "retry_tool"               # 重试工具
    RECOVER_ERROR = "recover_error"         # 错误恢复
    CHECK_DEPENDENCIES = "check_dependencies" # 检查依赖
    CREATE_CHECKPOINT = "create_checkpoint"  # 创建检查点
    RESTORE_CHECKPOINT = "restore_checkpoint" # 恢复检查点
    NO_OP = "no_op"                         # 无操作
    PARALLEL_EXECUTE = "parallel_execute"    # 并行执行
    CONDITIONAL_BRANCH = "conditional_branch" # 条件分支
```

### 2. 训练管理器 API

#### 2.1 UnifiedTrainingManager

```python
class UnifiedTrainingManager:
    """统一训练管理器"""
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        初始化训练管理器
        
        Args:
            config_path: 配置文件路径
        """

    def train_agent(self, episodes: int = 1000, 
                   algorithm: str = "ppo") -> TrainingResults:
        """
        训练智能体
        
        Args:
            episodes: 训练回合数
            algorithm: 训练算法 ("ppo", "dqn", "a2c")
            
        Returns:
            TrainingResults: 训练结果对象
        """

    def evaluate_model(self, model_path: str, 
                      test_episodes: int = 100) -> EvaluationResults:
        """
        评估模型性能
        
        Args:
            model_path: 模型文件路径
            test_episodes: 测试回合数
            
        Returns:
            EvaluationResults: 评估结果
        """

    def save_checkpoint(self, episode: int, 
                       metrics: Dict[str, float]) -> str:
        """
        保存训练检查点
        
        Args:
            episode: 当前回合数
            metrics: 当前指标
            
        Returns:
            str: 检查点文件路径
        """
```

#### 2.2 PolicyNetwork

```python
class PolicyNetwork(nn.Module):
    """策略网络"""
    
    def __init__(self, state_dim: int = 512, 
                 action_dim: int = 64, 
                 hidden_dim: int = 256):
        """
        初始化策略网络
        
        Args:
            state_dim: 状态维度
            action_dim: 动作维度  
            hidden_dim: 隐藏层维度
        """

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        前向传播
        
        Args:
            state: 状态张量 [batch_size, state_dim]
            
        Returns:
            torch.Tensor: 动作概率分布 [batch_size, action_dim]
        """

    def get_action(self, state: torch.Tensor, 
                   deterministic: bool = False) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取动作和对数概率
        
        Args:
            state: 状态张量
            deterministic: 是否确定性采样
            
        Returns:
            Tuple[torch.Tensor, torch.Tensor]: (动作, 对数概率)
        """
```

### 3. 工作流生成器 API

#### 3.1 MDPWorkflowGenerator

```python
class MDPWorkflowGenerator:
    """MDP工作流生成器"""
    
    def __init__(self, mdp_framework: GeneralizedMDPFramework):
        """
        初始化工作流生成器
        
        Args:
            mdp_framework: MDP框架实例
        """

    def generate_workflow(self, task_type: str, 
                         difficulty: str = "medium",
                         context: Optional[Dict] = None) -> Workflow:
        """
        生成工作流
        
        Args:
            task_type: 任务类型 ("basic_task", "simple_task", "data_pipeline", 
                              "api_integration", "multi_stage_pipeline")
            difficulty: 难度级别 ("easy", "medium", "hard")
            context: 额外上下文信息
            
        Returns:
            Workflow: 生成的工作流对象
        """

    def optimize_workflow(self, workflow: Workflow) -> Workflow:
        """
        优化工作流结构
        
        Args:
            workflow: 原始工作流
            
        Returns:
            Workflow: 优化后的工作流
        """
```

#### 3.2 FlawedWorkflowGenerator

```python
class FlawedWorkflowGenerator:
    """缺陷工作流生成器"""
    
    def inject_flaw(self, workflow: Workflow, 
                   flaw_type: str, 
                   severity: str) -> FlawedWorkflow:
        """
        注入缺陷到工作流
        
        Args:
            workflow: 原始工作流
            flaw_type: 缺陷类型 ("missing_middle", "order_flaw_swap", 
                              "semantic_mismatch")
            severity: 严重程度 ("light", "medium", "severe")
            
        Returns:
            FlawedWorkflow: 包含缺陷的工作流
        """

    def analyze_flaw_impact(self, flawed_workflow: FlawedWorkflow) -> FlawAnalysis:
        """
        分析缺陷影响
        
        Args:
            flawed_workflow: 有缺陷的工作流
            
        Returns:
            FlawAnalysis: 缺陷分析结果
        """
```

### 4. 质量测试器 API

#### 4.1 FlawedWorkflowTester

```python
class FlawedWorkflowTester:
    """工作流质量测试器"""
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        初始化测试器
        
        Args:
            config_path: 配置文件路径
        """

    def run_comprehensive_test(self, 
                              test_config: Optional[Dict] = None) -> TestResults:
        """
        运行综合测试
        
        Args:
            test_config: 测试配置
            
        Returns:
            TestResults: 测试结果对象
        """

    def test_single_workflow(self, workflow: Workflow, 
                           strategy: str = "baseline") -> SingleTestResult:
        """
        测试单个工作流
        
        Args:
            workflow: 待测试工作流
            strategy: 测试策略 ("baseline", "optimal", "cot")
            
        Returns:
            SingleTestResult: 单次测试结果
        """

    def generate_quality_report(self, results: TestResults) -> str:
        """
        生成质量报告
        
        Args:
            results: 测试结果
            
        Returns:
            str: Markdown格式的报告内容
        """
```

### 5. 执行器 API

#### 5.1 InteractiveExecutor

```python
class InteractiveExecutor:
    """交互式工作流执行器"""
    
    async def execute_workflow(self, workflow: Workflow, 
                              context: Optional[Dict] = None) -> ExecutionResult:
        """
        异步执行工作流
        
        Args:
            workflow: 待执行的工作流
            context: 执行上下文
            
        Returns:
            ExecutionResult: 执行结果
        """

    async def execute_step(self, step: WorkflowStep, 
                          context: Dict) -> StepResult:
        """
        执行单个步骤
        
        Args:
            step: 工作流步骤
            context: 执行上下文
            
        Returns:
            StepResult: 步骤执行结果
        """

    def validate_execution(self, result: ExecutionResult) -> ValidationResult:
        """
        验证执行结果
        
        Args:
            result: 执行结果
            
        Returns:
            ValidationResult: 验证结果
        """
```

### 6. 嵌入管理 API

#### 6.1 MCPEmbeddingManager

```python
class MCPEmbeddingManager:
    """MCP嵌入管理器"""
    
    def __init__(self, embedding_dim: int = 384):
        """
        初始化嵌入管理器
        
        Args:
            embedding_dim: 嵌入维度
        """

    def embed_text(self, text: str) -> np.ndarray:
        """
        文本嵌入
        
        Args:
            text: 输入文本
            
        Returns:
            np.ndarray: 嵌入向量
        """

    def search_similar(self, query: str, 
                      top_k: int = 10) -> List[SearchResult]:
        """
        相似性搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            List[SearchResult]: 搜索结果列表
        """

    def build_index(self, documents: List[str]) -> None:
        """
        构建索引
        
        Args:
            documents: 文档列表
        """
```

### 7. API客户端管理 API

#### 7.1 APIClientManager

```python
class APIClientManager:
    """API客户端管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化API客户端管理器
        
        Args:
            config: API配置信息
        """

    async def make_request(self, prompt: str, 
                          max_tokens: int = 2048,
                          temperature: float = 0.7) -> str:
        """
        发起API请求
        
        Args:
            prompt: 提示文本
            max_tokens: 最大token数
            temperature: 温度参数
            
        Returns:
            str: API响应内容
        """

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        获取使用统计
        
        Returns:
            Dict[str, Any]: 使用统计信息
        """
```

## 📊 数据结构

### 1. 核心数据类型

#### 1.1 Workflow

```python
@dataclass
class Workflow:
    """工作流定义"""
    id: str                              # 工作流ID
    name: str                           # 工作流名称
    task_type: str                      # 任务类型
    difficulty: str                     # 难度级别
    steps: List[WorkflowStep]           # 工作流步骤
    dependencies: Dict[str, List[str]]   # 步骤依赖关系
    metadata: Dict[str, Any]            # 元数据
    created_at: datetime                # 创建时间
```

#### 1.2 WorkflowStep

```python
@dataclass
class WorkflowStep:
    """工作流步骤"""
    id: str                             # 步骤ID
    name: str                          # 步骤名称
    tool_name: str                     # 使用的工具名称
    parameters: Dict[str, Any]         # 工具参数
    expected_output: Optional[str]     # 期望输出
    retry_count: int = 0               # 重试次数
    timeout: int = 30                  # 超时时间(秒)
```

#### 1.3 ExecutionResult

```python
@dataclass
class ExecutionResult:
    """执行结果"""
    workflow_id: str                   # 工作流ID
    success: bool                      # 是否成功
    completion_rate: float             # 完成率 (0.0-1.0)
    execution_time: float              # 执行时间(秒)
    step_results: List[StepResult]     # 步骤结果列表
    error_message: Optional[str]       # 错误信息
    quality_score: float               # 质量分数
    metrics: Dict[str, float]          # 其他指标
```

#### 1.4 TestResults

```python
@dataclass
class TestResults:
    """测试结果集合"""
    total_tests: int                   # 总测试数
    successful_tests: int              # 成功测试数
    failed_tests: int                  # 失败测试数
    success_rate: float                # 成功率
    average_score: float               # 平均分数
    results_by_strategy: Dict[str, List[SingleTestResult]]  # 按策略分组的结果
    results_by_task_type: Dict[str, List[SingleTestResult]] # 按任务类型分组的结果
    flaw_sensitivity_analysis: Dict[str, float]             # 缺陷敏感性分析
    execution_time_stats: Dict[str, float]                  # 执行时间统计
```

## ⚙️ 配置参数

### 1. 主配置 (config.json)

```json
{
  "api_config": {
    "use_azure_openai": true,
    "azure_openai_api_key": "your_api_key",
    "azure_openai_api_base": "https://your-resource.openai.azure.com/",
    "azure_openai_api_version": "2024-12-01-preview",
    "azure_openai_deployment_name": "gpt-4o-mini",
    "azure_openai_model": "gpt-4o-mini",
    "openai_api_key": "your_openai_key",
    "model": "gpt-4o-mini",
    "max_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
  },
  "mdp_config": {
    "state_dim": 512,
    "action_dim": 64,
    "max_steps": 50,
    "reward_scale": 1.0,
    "discount_factor": 0.99,
    "exploration_rate": 0.1
  },
  "training_config": {
    "algorithm": "ppo",
    "learning_rate": 0.0003,
    "batch_size": 64,
    "episodes": 1000,
    "gamma": 0.99,
    "tau": 0.95,
    "clip_epsilon": 0.2,
    "value_loss_coef": 0.5,
    "entropy_coef": 0.01,
    "max_grad_norm": 0.5
  },
  "testing_config": {
    "strategies": ["baseline", "optimal", "cot"],
    "task_types": ["basic_task", "simple_task", "data_pipeline", 
                  "api_integration", "multi_stage_pipeline"],
    "difficulties": ["easy", "medium", "hard"],
    "flaw_types": ["missing_middle", "order_flaw_swap", "semantic_mismatch"],
    "severities": ["light", "medium", "severe"],
    "test_count_per_combination": 10
  }
}
```

### 2. PPO训练配置 (ppo_m1_config.json)

```json
{
  "training": {
    "algorithm": "ppo",
    "episodes": 2000,
    "batch_size": 32,
    "learning_rate": 0.0001,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_epsilon": 0.2,
    "value_loss_coef": 0.5,
    "entropy_coef": 0.01,
    "max_grad_norm": 0.5,
    "update_epochs": 4,
    "num_minibatches": 4
  },
  "device_config": {
    "device": "mps",
    "use_mixed_precision": false,
    "compile_model": true
  },
  "optimization": {
    "gradient_accumulation_steps": 2,
    "memory_efficient": true,
    "use_checkpoint": true
  }
}
```

## 🚨 错误处理

### 错误类型

```python
class WorkflowError(Exception):
    """工作流相关错误基类"""
    pass

class ExecutionError(WorkflowError):
    """执行错误"""
    def __init__(self, step_id: str, message: str):
        self.step_id = step_id
        self.message = message
        super().__init__(f"Step {step_id}: {message}")

class ValidationError(WorkflowError):
    """验证错误"""
    pass

class ConfigurationError(WorkflowError):
    """配置错误"""
    pass

class APIError(WorkflowError):
    """API调用错误"""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")
```

### 错误处理策略

```python
class ErrorHandler:
    """错误处理器"""
    
    def handle_execution_error(self, error: ExecutionError, 
                              context: Dict) -> RecoveryAction:
        """
        处理执行错误
        
        Args:
            error: 执行错误
            context: 错误上下文
            
        Returns:
            RecoveryAction: 恢复动作
        """

    def handle_api_error(self, error: APIError) -> RetryAction:
        """
        处理API错误
        
        Args:
            error: API错误
            
        Returns:
            RetryAction: 重试动作
        """
```

## 📝 使用示例

### 1. 基础训练示例

```python
from unified_training_manager import UnifiedTrainingManager

# 初始化训练管理器
trainer = UnifiedTrainingManager("config/ppo_m1_config.json")

# 开始训练
results = trainer.train_agent(
    episodes=1000,
    algorithm="ppo"
)

# 保存模型
trainer.save_model("checkpoints/trained_model.pt")

print(f"训练完成，平均奖励: {results.average_reward}")
```

### 2. 工作流生成和测试示例

```python
from mdp_workflow_generator import MDPWorkflowGenerator
from workflow_quality_test_flawed import FlawedWorkflowTester

# 生成工作流
generator = MDPWorkflowGenerator()
workflow = generator.generate_workflow(
    task_type="data_pipeline",
    difficulty="medium"
)

# 测试工作流质量
tester = FlawedWorkflowTester()
results = tester.test_single_workflow(
    workflow=workflow,
    strategy="optimal"
)

print(f"工作流质量分数: {results.quality_score}")
```

### 3. 缺陷注入和分析示例

```python
from flawed_workflow_generator import FlawedWorkflowGenerator

# 初始化缺陷生成器
flaw_generator = FlawedWorkflowGenerator()

# 注入缺陷
flawed_workflow = flaw_generator.inject_flaw(
    workflow=original_workflow,
    flaw_type="missing_middle",
    severity="medium"
)

# 分析缺陷影响
analysis = flaw_generator.analyze_flaw_impact(flawed_workflow)
print(f"缺陷影响评分: {analysis.impact_score}")
```

---

*API文档版本: v2.0*  
*最后更新: 2025-08-02*