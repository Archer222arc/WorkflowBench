#!/usr/bin/env python3
"""
PILOT-Bench Batch Test Runner with Concurrent Execution Support
支持并发执行、累积测试、智能选择的批量测试运行器
"""

import argparse
import json
import logging
import random
import time
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Semaphore
import traceback

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入核心组件
from mdp_workflow_generator import MDPWorkflowGenerator
from interactive_executor import InteractiveExecutor
from flawed_workflow_generator import FlawedWorkflowGenerator

# 支持存储格式选择
storage_format = os.environ.get('STORAGE_FORMAT', 'json').lower()
if storage_format == 'parquet':
    try:
        from parquet_cumulative_manager import ParquetCumulativeManager as CumulativeTestManager
        from parquet_cumulative_manager import ParquetCumulativeManager as EnhancedCumulativeManager
        from cumulative_test_manager import TestRecord  # TestRecord仍从原模块导入
        print(f"[INFO] 使用Parquet存储格式")
    except ImportError:
        from cumulative_test_manager import CumulativeTestManager, TestRecord
        from enhanced_cumulative_manager import EnhancedCumulativeManager
        print(f"[INFO] Parquet不可用，使用JSON存储格式")
else:
    from cumulative_test_manager import CumulativeTestManager, TestRecord
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    print(f"[INFO] 使用JSON存储格式")
from workflow_quality_test_flawed import WorkflowQualityTester
from adaptive_rate_limiter import AdaptiveRateLimiter
from storage_adapter import create_storage_adapter

# 设置默认日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@dataclass
class TestTask:
    """测试任务"""
    model: str  # 统计用的基础模型名（小写）
    task_type: str
    prompt_type: str
    difficulty: str = "easy"
    deployment: Optional[str] = None  # API调用用的部署实例名（保持原始大小写）
    is_flawed: bool = False
    flaw_type: Optional[str] = None
    task_instance: Optional[Dict] = None
    timeout: int = 600  # 默认超时时间（10分钟，确保任务能按时结束）
    tool_success_rate: float = 0.8  # 工具成功率
    required_tools: Optional[List[str]] = None  # 必需工具列表
    
    def __post_init__(self):
        """根据模型动态调整超时时间（统一限制在10分钟内）"""
        # 所有模型统一使用10分钟超时，确保任务能按时结束
        # 不再根据模型类型区分，避免某些模型占用过长时间
        self.timeout = 600  # 统一10分钟超时


class BatchTestRunner:
    """批量测试运行器 - 支持并发和累积测试"""
    
    def __init__(self, debug: bool = False, silent: bool = False, use_adaptive: bool = False, 
                 save_logs: bool = False, enable_database_updates: bool = True, 
                 use_ai_classification: bool = True, checkpoint_interval: int = 0,
                 idealab_key_index: Optional[int] = None):
        """初始化测试运行器"""
        self.debug = debug
        self.silent = silent
        self.use_adaptive = use_adaptive
        self.save_logs = save_logs  # 是否保存详细交互日志
        self.enable_database_updates = enable_database_updates  # 是否启用实时数据库更新
        self.use_ai_classification = use_ai_classification  # 是否启用AI错误分类
        self.checkpoint_interval = checkpoint_interval  # 中间保存间隔（每N个测试保存一次）
        self.pending_results = []  # 待保存的结果缓存
        self.idealab_key_index = idealab_key_index  # IdealLab API key索引
        
        # 初始化存储适配器（稍后创建，需要manager）
        self.storage_adapter = None
        
        # 创建logs目录 (必须先初始化日志系统)
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 创建日志文件名
        self.log_filename = log_dir / f"batch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # 获取logger (必须在使用logger之前初始化)
        self.logger = logging.getLogger(__name__)
        
        # 初始化AI分类器
        self.ai_classifier = None
        if use_ai_classification:
            try:
                from txt_based_ai_classifier import TxtBasedAIClassifier
                self.ai_classifier = TxtBasedAIClassifier(model_name="gpt-5-nano")
                print(f"[AI_DEBUG] AI分类器初始化成功: {self.ai_classifier}")
                self.logger.info("基于TXT文件的AI错误分类系统已启用 (使用gpt-5-nano)")
            except Exception as e:
                self.logger.error(f"Failed to initialize TXT-based AI classifier: {e}")
                self.use_ai_classification = False
        
        print(f"[DEBUG] BatchTestRunner initialized with save_logs={save_logs}, enable_database_updates={enable_database_updates}, use_ai_classification={use_ai_classification}, checkpoint_interval={checkpoint_interval}")
        
        # 清除现有的handlers（避免重复）
        self.logger.handlers.clear()
        
        # 添加控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        if silent:
            console_handler.setLevel(logging.WARNING)  # silent模式下控制台只显示警告
        else:
            console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        self.logger.addHandler(console_handler)
        
        # 添加文件handler（始终记录所有级别）
        file_handler = logging.FileHandler(self.log_filename, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        file_handler.setLevel(logging.DEBUG)  # 文件始终记录DEBUG级别
        self.logger.addHandler(file_handler)
        
        # 设置logger级别
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # 避免日志传播到父logger
        
        # 记录运行配置
        self.logger.info("="*60)
        self.logger.info(f"Batch test runner initialized")
        self.logger.info(f"Configuration: debug={debug}, silent={silent}, adaptive={use_adaptive}")
        self.logger.info(f"Log file: {self.log_filename}")
        self.logger.info("="*60)
        
        # 延迟初始化（使用lazy loading避免启动时加载）
        self.generator = None
        self.flawed_generator = None
        self.manager = None
        self.quality_tester = None  # WorkflowQualityTester 实例（用于继承prompt方法）
        
        # 线程安全
        self._init_lock = Lock()
        self._initialized = False
        
        # 统计
        self._test_counter = 0
        self._success_counter = 0
        self._lock = Lock()
        
        # QPS控制
        self._last_request_time = 0
        self._request_lock = Lock()
    
    def _generate_txt_log_content(self, task: TestTask, result: Dict, log_data: Dict = None) -> str:
        """生成TXT格式的日志内容（不限制token数）
        
        Returns:
            str: TXT格式的日志内容字符串
        """
        # 准备完整的日志数据
        if not log_data:
            # 如果没有传入log_data，创建基本结构，包含模型信息
            model_safe = task.model.replace('-', '_').replace('.', '_')  # 安全的模型名
            # 生成test_id，模型名放在前面更显眼
            if task.is_flawed and task.flaw_type:
                test_id = f"{model_safe}_{task.task_type}_inst0_test{random.randint(0, 999)}_flawed_{task.flaw_type}_{task.prompt_type}"
            else:
                test_id = f"{model_safe}_{task.task_type}_inst0_test{random.randint(0, 999)}_{task.prompt_type}"
            
            log_data = {
                'test_id': test_id,
                'task_type': task.task_type,
                'prompt_type': task.prompt_type,
                'timestamp': datetime.now().isoformat(),
                'task_instance': {
                    'required_tools': task.required_tools or [],
                    'description': 'Task description not available',
                    'task_type': task.task_type
                },
                'prompt': 'Prompt not captured',
                'llm_response': json.dumps(result, indent=2),
                'extracted_tool_calls': result.get('tool_calls', []),
                'conversation_history': result.get('conversation_history', []),
                'execution_history': result.get('execution_history', []),
                'is_flawed': task.is_flawed,
                'flaw_type': task.flaw_type
            }
        
        # 添加结果信息
        if result:
            log_data['result'] = {
                'success': result.get('success', False),
                'final_score': result.get('final_score', 0),
                'execution_time': result.get('execution_time', 0),
                'workflow_score': result.get('workflow_score', 0),
                'phase2_score': result.get('phase2_score', 0),
                'quality_score': result.get('quality_score', 0),
                'tool_calls': result.get('tool_calls', []),
                'error': result.get('error'),
                'error_type': result.get('error_type')
            }
        
        test_id = log_data.get('test_id', 'unknown')
        
        # 生成TXT格式内容（不限制长度）
        txt_lines = []
        txt_lines.append(f"Test Log: {test_id}")
        txt_lines.append("=" * 80 + "\n")
        
        txt_lines.append(f"Task Type: {log_data.get('task_type', 'unknown')}")
        txt_lines.append(f"Prompt Type: {log_data.get('prompt_type', 'unknown')}")
        txt_lines.append(f"Timestamp: {log_data.get('timestamp', datetime.now().isoformat())}\n")
        
        txt_lines.append("Task Instance:")
        txt_lines.append("-" * 40)
        if log_data.get('task_instance'):
            txt_lines.append(f"Required Tools: {log_data['task_instance'].get('required_tools', [])}")
            txt_lines.append(f"Description: {log_data['task_instance'].get('description', 'N/A')}")
        txt_lines.append("")
        
        txt_lines.append("Prompt:")
        txt_lines.append("-" * 40)
        txt_lines.append(str(log_data.get('prompt', 'Not captured')))
        txt_lines.append("")
        
        txt_lines.append("LLM Response:")
        txt_lines.append("-" * 40)
        txt_lines.append(str(log_data.get('llm_response', 'Not captured')))
        txt_lines.append("")
        
        # 添加完整的对话历史（按turn分组）
        txt_lines.append("Conversation History:")
        txt_lines.append("-" * 40)
        conversation = log_data.get('conversation_history', [])
        
        if conversation:
            # 按turn号分组对话
            turns_dict = {}
            
            for msg in conversation:
                if isinstance(msg, dict):
                    # 获取turn号，如果没有则使用索引
                    turn_num = msg.get('turn', len(turns_dict) + 1)
                    
                    if turn_num not in turns_dict:
                        turns_dict[turn_num] = {'assistant': [], 'user': []}
                    
                    role = msg.get('role', '')
                    content = msg.get('content', 'N/A')
                    
                    if role == 'assistant':
                        turns_dict[turn_num]['assistant'].append(content)
                    elif role == 'user':
                        turns_dict[turn_num]['user'].append(content)
                    elif 'human' in msg and 'assistant' in msg:
                        # 旧格式
                        turns_dict[turn_num]['user'].append(msg.get('human', 'N/A'))
                        turns_dict[turn_num]['assistant'].append(msg.get('assistant', 'N/A'))
            
            # 按turn号排序输出
            for turn_num in sorted(turns_dict.keys()):
                txt_lines.append(f"\nTurn {turn_num}:")
                
                # 输出assistant消息
                if turns_dict[turn_num]['assistant']:
                    for i, content in enumerate(turns_dict[turn_num]['assistant']):
                        if i == 0:
                            txt_lines.append(f"  Assistant: {content}")
                        else:
                            # 如果同一turn有多个assistant消息，缩进显示
                            txt_lines.append(f"            {content}")
                
                # 输出user消息
                if turns_dict[turn_num]['user']:
                    for i, content in enumerate(turns_dict[turn_num]['user']):
                        if i == 0:
                            txt_lines.append(f"  User: {content}")
                        else:
                            # 如果同一turn有多个user消息，缩进显示
                            txt_lines.append(f"        {content}")
                
                # 如果某个角色没有消息，显示N/A
                if not turns_dict[turn_num]['assistant']:
                    txt_lines.append(f"  Assistant: N/A")
                if not turns_dict[turn_num]['user']:
                    txt_lines.append(f"  User: N/A")
        else:
            # 没有对话历史
            txt_lines.append("\n(No conversation history recorded)")
        txt_lines.append("")
        
        txt_lines.append("Extracted Tool Calls:")
        txt_lines.append("-" * 40)
        txt_lines.append(str(log_data.get('extracted_tool_calls', [])))
        txt_lines.append("")
        
        # 添加API问题信息（如果有）
        if log_data.get('api_issues'):
            txt_lines.append("API Issues:")
            txt_lines.append("-" * 40)
            for issue in log_data.get('api_issues', []):
                txt_lines.append(f"Turn {issue.get('turn', 'N/A')}: {issue.get('issue', 'Unknown issue')}")
                if issue.get('timestamp'):
                    txt_lines.append(f"  Timestamp: {issue['timestamp']}")
            txt_lines.append("")
        
        # 添加执行历史
        txt_lines.append("Execution History:")
        txt_lines.append("-" * 40)
        execution = log_data.get('execution_history', [])
        for i, step in enumerate(execution):
            txt_lines.append(f"Step {i+1}: {step}")
        txt_lines.append("")
        
        if log_data.get('result'):
            txt_lines.append("Execution Results:")
            txt_lines.append("-" * 40)
            txt_lines.append(f"Success: {log_data['result'].get('success', False)}")
            txt_lines.append(f"Final Score: {log_data['result'].get('final_score', 0):.3f}")
            txt_lines.append(f"Execution Time: {log_data['result'].get('execution_time', 0):.2f}s")
            txt_lines.append(f"Workflow Score: {log_data['result'].get('workflow_score', 0):.3f}")
            txt_lines.append(f"Phase2 Score: {log_data['result'].get('phase2_score', 0):.3f}")
            if log_data['result'].get('error'):
                txt_lines.append(f"Error: {log_data['result']['error']}")
                txt_lines.append(f"Error Type: {log_data['result'].get('error_type', 'Unknown')}")
        
        return "\n".join(txt_lines)
    
    def _ai_classify_with_txt_content(self, task: TestTask, result: Dict, txt_content: str = None) -> Tuple[str, str, float]:
        """基于TXT内容字符串进行AI错误分类（不需要文件）"""
        # AI分类调试信息
        print(f"[AI_DEBUG] _ai_classify_with_txt_content called:")
        print(f"  - use_ai_classification={self.use_ai_classification}")
        print(f"  - ai_classifier={self.ai_classifier is not None}")
        print(f"  - txt_content_len={len(txt_content) if txt_content else 0}")
        print(f"  - task_model={task.model}")
        
        if not (self.use_ai_classification and self.ai_classifier and txt_content):
            return None, None, 0.0
        
        try:
            # 使用基于TXT内容的分类器
            category, reason, confidence = self.ai_classifier.classify_from_txt_content(txt_content)
            
            # Check if category is not None before accessing .value
            if category is None:
                self.logger.warning("AI classifier returned None category")
                return None, None, 0.0
            
            if self.debug:
                self.logger.info(f"AI基于TXT内容分类结果: {category.value} (置信度: {confidence:.2f}) - {reason[:100] if reason else 'No reason'}")
            
            return category.value, reason, confidence
            
        except Exception as e:
            self.logger.error(f"AI基于TXT内容错误分类失败: {e}")
            return None, None, 0.0
    
    def _save_interaction_log(self, task: TestTask, result: Dict, log_data: Dict = None) -> Optional[Path]:
        """保存交互日志到文件（使用WorkflowQualityTester的格式）
        
        Returns:
            Path: 保存的TXT文件路径，如果保存失败则返回None
        """
        try:
            # 创建日志目录
            log_dir = Path("workflow_quality_results/test_logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成TXT内容
            txt_content = self._generate_txt_log_content(task, result, log_data)
            
            # 获取test_id（用于文件名）
            # test_id现在已经在生成时包含了模型名在最前面
            if log_data and 'test_id' in log_data:
                test_id = log_data['test_id']
            else:
                # 备用：如果没有test_id，生成一个新的（模型名在前）
                model_safe = task.model.replace('-', '_').replace('.', '_')
                if task.is_flawed and task.flaw_type:
                    test_id = f"{model_safe}_{task.task_type}_inst0_test{random.randint(0, 999)}_flawed_{task.flaw_type}_{task.prompt_type}"
                else:
                    test_id = f"{model_safe}_{task.task_type}_inst0_test{random.randint(0, 999)}_{task.prompt_type}"
            
            # 保存TXT文件
            txt_file = log_dir / f"{test_id}_log.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            
            # 也保存JSON格式（如果有log_data）
            if log_data:
                json_file = log_dir / f"{test_id}_log.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(log_data, f, indent=2, ensure_ascii=False)
                self.logger.debug(f"Saved detailed logs: {json_file} and {txt_file}")
            else:
                self.logger.debug(f"Saved log: {txt_file}")
            
            return txt_file  # 返回TXT文件路径供AI分类使用
            
        except Exception as e:
            self.logger.error(f"Failed to save interaction log: {e}")
            return None
    
    def _lazy_init(self):
        """延迟初始化（线程安全）"""
        if self._initialized:
            return
        
        with self._init_lock:
            # Double-check locking pattern
            if self._initialized:
                return
            
            self.logger.info("Initializing test components...")
            
            # 检查是否有预生成的workflow文件
            # 通过检查任务库是否包含workflow字段来判断
            self.use_pregenerated_workflows = False
            try:
                # 尝试加载一个任务库文件检查
                sample_path = Path("mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy_with_workflows.json")
                if sample_path.exists():
                    with open(sample_path, 'r') as f:
                        sample_data = json.load(f)
                        tasks = sample_data.get('tasks', sample_data if isinstance(sample_data, list) else [])
                        if tasks and len(tasks) > 0 and 'workflow' in tasks[0]:
                            self.use_pregenerated_workflows = True
                            self.logger.info("Found pre-generated workflows, will use them to save memory")
            except Exception as e:
                self.logger.debug(f"Could not check for pre-generated workflows: {e}")
            
            # 只在没有预生成workflow时初始化生成器
            if not self.use_pregenerated_workflows:
                self.logger.info("No pre-generated workflows found, initializing MDPWorkflowGenerator")
                self.generator = MDPWorkflowGenerator(
                    model_path="checkpoints/best_model.pt",
                    use_embeddings=True
                )
            else:
                # ⚡ 优化方案：使用真正的MDPWorkflowGenerator，但跳过模型加载
                self.logger.info("⚡ [OPTIMIZATION] Using MDPWorkflowGenerator with SKIP_MODEL_LOADING=true")
                self.logger.info("⚡ This saves ~350MB memory while keeping all functionality intact")
                
                # 设置环境变量以跳过神经网络模型加载
                import os
                os.environ['SKIP_MODEL_LOADING'] = 'true'
                
                # 使用真正的MDPWorkflowGenerator
                # 它会检测SKIP_MODEL_LOADING环境变量并跳过模型加载
                from mdp_workflow_generator import MDPWorkflowGenerator
                self.generator = MDPWorkflowGenerator(
                    model_path="checkpoints/best_model.pt",  # 路径会被忽略因为SKIP_MODEL_LOADING=true
                    use_embeddings=True  # 保留所有其他功能
                )
                
                self.logger.info("✅ MDPWorkflowGenerator initialized successfully:")
                self.logger.info(f"  - task_manager: {'✓' if hasattr(self.generator, 'task_manager') else '✗'}")
                self.logger.info(f"  - output_verifier: {'✓' if hasattr(self.generator, 'output_verifier') else '✗'}")
                self.logger.info(f"  - embedding_manager: {'✓' if hasattr(self.generator, 'embedding_manager') else '✗'}")
                self.logger.info(f"  - tool_capabilities: {len(self.generator.tool_capabilities)} tools")
                self.logger.info(f"  - neural network: {'loaded' if self.generator.q_network or self.generator.network else 'skipped (saving 350MB)'}")
                
                # 不再需要MockGenerator！所有功能都完整保留
            
            # 初始化缺陷生成器（始终需要）
            self.flawed_generator = FlawedWorkflowGenerator(
                self.generator.full_tool_registry
            )
            
            # 初始化增强版累积测试管理器（实时错误分类）
            self.manager = EnhancedCumulativeManager(use_ai_classification=self.use_ai_classification)
            
            # 创建存储适配器
            self.storage_adapter = create_storage_adapter(self.manager)
            
            # 初始化 WorkflowQualityTester（用于继承prompt创建方法和评分）
            # 注意：传递generator作为第一个参数
            self.quality_tester = WorkflowQualityTester(
                generator=self.generator,  # 必需的第一个参数
                model='gpt-4o-mini',
                use_phase2_scoring=True,  # 启用Phase2评分以初始化stable_scorer
                save_logs=self.save_logs  # 使用传入的save_logs参数
            )
            
            # 加载任务库（默认easy，后续可以根据需要重新加载）
            self._load_task_library(difficulty="easy")
            self._current_difficulty = "easy"
            
            self._initialized = True
            self.logger.info("Initialization complete")
    
    def _smart_checkpoint_save(self, results, task_model=None, force=False):
        """智能checkpoint保存 - 支持多重触发条件"""
        if not self.checkpoint_interval or self.enable_database_updates:
            return
        
        # 将结果添加到pending缓存
        if results:
            if isinstance(results, list):
                self.pending_results.extend(results)
            else:
                self.pending_results.append(results)
        
        # 多重触发条件检查
        current_time = time.time()
        time_since_last_save = current_time - getattr(self, '_last_checkpoint_time', current_time)
        result_count = len(self.pending_results)
        
        # 自适应阈值
        effective_threshold = self.checkpoint_interval
        if hasattr(self, '_adaptive_checkpoint') and self._adaptive_checkpoint:
            if result_count > 0 and time_since_last_save > 300:  # 5分钟强制保存
                effective_threshold = 1
            elif time_since_last_save > 180:  # 3分钟降低阈值
                effective_threshold = max(1, self.checkpoint_interval // 2)
        
        # 触发条件
        should_save = (force or 
                      result_count >= effective_threshold or
                      (result_count > 0 and time_since_last_save > 600) or  # 10分钟强制保存
                      (result_count >= 3 and time_since_last_save > 120))   # 2分钟部分保存
        
        if should_save and self.pending_results:
            print(f"💾 智能Checkpoint: 保存{len(self.pending_results)}个结果...")
            print(f"   触发原因: 数量={result_count}, 时间={time_since_last_save:.1f}s, 强制={force}")
            
            # 确保已初始化manager
            self._lazy_init()
            
            # 保存逻辑（保持原有逻辑）
            try:
                from cumulative_test_manager import TestRecord
                saved_count = 0
                
                for result in self.pending_results:
                    if result and not result.get('_saved', False):
                        record = TestRecord(
                            model=result.get('model', task_model or 'unknown'),
                            task_type=result.get('task_type', 'unknown'),
                            prompt_type=result.get('prompt_type', 'baseline'),
                            difficulty=result.get('difficulty', 'easy')
                        )
                        
                        # 设置其他字段（保持原有逻辑）
                        for field in ['timestamp', 'success', 'success_level', 'execution_time', 'turns',
                                    'tool_calls', 'workflow_score', 'phase2_score', 'quality_score',
                                    'final_score', 'error_type', 'tool_success_rate', 'is_flawed',
                                    'flaw_type', 'format_error_count', 'api_issues', 'executed_tools',
                                    'required_tools', 'tool_coverage_rate', 'task_instance', 'execution_history',
                                    'ai_error_category', '_ai_error_category']:
                            if field in result:
                                if field == '_ai_error_category':
                                    setattr(record, 'ai_error_category', result[field])
                                else:
                                    setattr(record, field, result[field])
                        
                        # 保存记录（使用统一的存储适配器）
                        try:
                            if self.storage_adapter and self.storage_adapter.write_result(record):
                                result['_saved'] = True
                                saved_count += 1
                        except Exception as e:
                            print(f"保存记录失败: {e}")
                
                print(f"✅ Checkpoint完成: 成功保存 {saved_count}/{len(self.pending_results)} 个结果")
                
                # 清空已保存的结果
                self.pending_results = [r for r in self.pending_results if not r.get('_saved', False)]
                self._last_checkpoint_time = current_time
                
            except Exception as e:
                print(f"❌ Checkpoint失败: {e}")
                import traceback
                traceback.print_exc()

    def _load_task_library(self, difficulty="easy", num_instances=20):
        """加载任务库
        
        Args:
            difficulty: 难度级别 (very_easy, easy, medium, hard, very_hard)
            num_instances: 每个任务类型加载的实例数量（用于部分加载）
        """
        # 检查是否启用部分加载（通过环境变量或属性）
        use_partial_loading = os.environ.get('USE_PARTIAL_LOADING', 'false').lower() == 'true'
        if hasattr(self, 'use_partial_loading'):
            use_partial_loading = self.use_partial_loading
        
        # 从环境变量获取加载数量
        if os.environ.get('TASK_LOAD_COUNT'):
            try:
                num_instances = int(os.environ.get('TASK_LOAD_COUNT'))
            except ValueError:
                pass
        
        # 首先尝试加载带workflow的版本
        workflow_enhanced_path = Path(f"mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{difficulty}_with_workflows.json")
        
        if workflow_enhanced_path.exists():
            # 使用预生成workflow的版本
            task_lib_path = workflow_enhanced_path
            self.logger.info(f"Loading task library with pre-generated workflows: {task_lib_path.name}")
        else:
            # 没有workflow版本，使用普通版本
            # 根据难度选择对应的任务库文件
            task_lib_path = Path(f"mcp_generated_library/difficulty_versions/task_library_enhanced_v3_{difficulty}.json")
            if not task_lib_path.exists():
                # 如果没有对应难度的文件，尝试默认的easy文件
                self.logger.warning(f"Task library for difficulty '{difficulty}' not found, trying 'easy'")
                task_lib_path = Path("mcp_generated_library/difficulty_versions/task_library_enhanced_v3_easy.json")
                if not task_lib_path.exists():
                    # 最后尝试默认文件
                    task_lib_path = Path("mcp_generated_library/task_library_enhanced_v3.json")
            self.logger.info(f"Loading standard task library (workflows will be generated): {task_lib_path.name}")
        
        if task_lib_path.exists():
            if use_partial_loading:
                # 使用部分加载策略
                self._load_task_library_partial(task_lib_path, difficulty, num_instances)
            else:
                # 使用传统全量加载
                with open(task_lib_path, 'r') as f:
                    data = json.load(f)
                
                # 处理任务数据
                if isinstance(data, dict):
                    tasks = data.get('tasks', [])
                else:
                    tasks = data
                
                # 按类型组织任务
                self.tasks_by_type = {}
                for task in tasks:
                    if isinstance(task, dict) and 'task_type' in task:
                        task_type = task['task_type']
                        if task_type not in self.tasks_by_type:
                            self.tasks_by_type[task_type] = []
                        self.tasks_by_type[task_type].append(task)
                
                self.logger.info(f"Loaded {len(tasks)} tasks from {task_lib_path.name}")
        else:
            self.logger.warning("Task library not found")
            self.tasks_by_type = {}
    
    def _load_task_library_partial(self, task_lib_path: Path, difficulty: str, num_instances: int):
        """部分加载任务库 - 只加载需要的任务数量
        
        Args:
            task_lib_path: 任务库文件路径
            difficulty: 难度级别
            num_instances: 每个任务类型加载的实例数量
        """
        self.logger.info(f"Using partial loading: {num_instances} tasks per type")
        
        # 第一阶段：构建轻量级索引
        self.logger.debug("Phase 1: Building task index...")
        task_index = {}
        
        with open(task_lib_path, 'r') as f:
            data = json.load(f)
        
        # 处理不同的数据格式
        if isinstance(data, dict):
            all_tasks = data.get('tasks', [])
        else:
            all_tasks = data
        
        # 构建索引
        for i, task in enumerate(all_tasks):
            if isinstance(task, dict) and 'task_type' in task:
                task_type = task['task_type']
                if task_type not in task_index:
                    task_index[task_type] = []
                task_index[task_type].append(i)
        
        self.logger.debug(f"Found {sum(len(indices) for indices in task_index.values())} total tasks")
        
        # 第二阶段：随机选择并加载具体任务
        self.logger.debug(f"Phase 2: Loading {num_instances} tasks per type...")
        self.tasks_by_type = {}
        
        for task_type, indices in task_index.items():
            # 随机选择num_instances个索引
            num_to_select = min(num_instances, len(indices))
            selected_indices = random.sample(indices, num_to_select)
            
            # 只加载选中的任务
            self.tasks_by_type[task_type] = [all_tasks[i] for i in selected_indices]
            self.logger.debug(f"Selected {len(self.tasks_by_type[task_type])} tasks for {task_type}")
        
        # 统计信息
        total_loaded = sum(len(tasks) for tasks in self.tasks_by_type.values())
        self.logger.info(f"Partially loaded {total_loaded} tasks (vs {len(all_tasks)} total)")
        
        # 估算内存节省
        memory_saved_percent = (1 - total_loaded / len(all_tasks)) * 100
        self.logger.info(f"Estimated memory saving: {memory_saved_percent:.1f}%")
    
    def run_single_test(self, model: str, task_type: str, prompt_type: str,
                       deployment: Optional[str] = None, is_flawed: bool = False, 
                       flaw_type: Optional[str] = None, timeout: int = 30, 
                       tool_success_rate: float = 0.8, difficulty: str = "easy") -> Dict:
        """运行单个测试并返回结果
        
        Args:
            difficulty: 任务难度级别 (very_easy, easy, medium, hard, very_hard)
        """
        self._lazy_init()
        
        # 检查是否需要重新加载不同难度的任务库
        if not hasattr(self, '_current_difficulty') or self._current_difficulty != difficulty:
            self.logger.info(f"Loading task library for difficulty: {difficulty}")
            self._load_task_library(difficulty=difficulty)
            self._current_difficulty = difficulty
        
        self.logger.debug(f"Starting single test: model={model}, task_type={task_type}, "
                         f"prompt_type={prompt_type}, is_flawed={is_flawed}, flaw_type={flaw_type}")
        
        try:
            # 获取任务
            tasks = self.tasks_by_type.get(task_type, [])
            self.logger.debug(f"Found {len(tasks)} tasks for type {task_type}")
            if not tasks:
                error_msg = f'No tasks found for {task_type}'
                self.logger.error(error_msg)
                # 创建基本的log_data用于AI分类
                basic_log_data = {
                    'test_id': f"{model.replace('-', '_').replace('.', '_')}_{task_type}_notask_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'task_type': task_type,
                    'prompt_type': prompt_type,
                    'timestamp': datetime.now().isoformat(),
                    'task_instance': {'required_tools': []},
                    'prompt': '',
                    'llm_response': 'No response - no tasks found',
                    'extracted_tool_calls': [],
                    'conversation_history': [],
                    'execution_history': [],
                    'is_flawed': is_flawed,
                    'flaw_type': flaw_type,
                    'result': {'success': False, 'error': error_msg}
                }
                return {
                    'success': False,
                    'error': error_msg,
                    'success_level': 'failure',
                    'tool_calls': [],
                    'turns': 0,
                    'workflow_score': 0.0,
                    'phase2_score': 0.0,
                    'quality_score': 0.0,
                    'final_score': 0.0,
                    '_log_data': basic_log_data
                }
            
            task = random.choice(tasks)
            # 兼容性处理：支持instance_id和id两种字段
            task_id = task.get('instance_id') or task.get('id', 'unknown')
            self.logger.debug(f"Selected task: {task_id}")
            
            # 获取或生成工作流
            # 首先检查任务是否已有预生成的workflow
            if 'workflow' in task and task['workflow'] is not None:
                # 使用预生成的workflow
                self.logger.debug(f"Using pre-generated workflow for task")
                workflow = task['workflow']
                
                # 如果是flawed测试，在预生成的workflow上注入缺陷
                if is_flawed and flaw_type:
                    self.logger.debug(f"Injecting flaw type: {flaw_type} on pre-generated workflow")
                    # 复制workflow以避免修改原始数据
                    import copy
                    normal_workflow = copy.deepcopy(workflow)
                    workflow = self.flawed_generator.inject_specific_flaw(normal_workflow, flaw_type)
            else:
                # 没有预生成的workflow，需要动态生成
                self.logger.debug(f"No pre-generated workflow found, generating dynamically")
                
                if is_flawed and flaw_type:
                    # 先生成正常工作流
                    # 兼容性处理：支持instance_id和id两种字段
                    task_id = task.get('instance_id') or task.get('id', 'unknown')
                    task_dict = {
                        'id': task_id,
                        'description': task.get('description', ''),
                        'task_type': task_type,
                        'required_tools': task.get('required_tools', []),
                        'expected_outputs': task.get('expected_outputs', {})
                    }
                    self.logger.debug(f"Generating normal workflow for flawed test")
                    normal_workflow = self.generator.generate_workflow(
                        task_type,
                        task_instance=task_dict
                    )
                    if not normal_workflow:
                        # 创建基本的log_data用于AI分类
                        basic_log_data = {
                            'test_id': f"{model.replace('-', '_').replace('.', '_')}_{task_type}_noworkflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                            'task_type': task_type,
                            'prompt_type': f'flawed_{flaw_type}',
                            'timestamp': datetime.now().isoformat(),
                            'task_instance': task_dict,
                            'prompt': '',
                            'llm_response': 'No response - workflow generation failed',
                            'extracted_tool_calls': [],
                            'conversation_history': [],
                            'execution_history': [],
                            'is_flawed': True,
                            'flaw_type': flaw_type,
                            'result': {'success': False, 'error': 'Failed to generate base workflow'}
                        }
                        return {
                            'success': False,
                            'error': 'Failed to generate base workflow',
                            'success_level': 'failure',
                            'tool_calls': [],
                            'turns': 0,
                            'workflow_score': 0.0,
                            'phase2_score': 0.0,
                            'quality_score': 0.0,
                            'final_score': 0.0,
                            '_log_data': basic_log_data
                        }
                    
                    # 注入缺陷
                    self.logger.debug(f"Injecting flaw type: {flaw_type}")
                    workflow = self.flawed_generator.inject_specific_flaw(normal_workflow, flaw_type)
                else:
                    # 兼容性处理：支持instance_id和id两种字段
                    task_id = task.get('instance_id') or task.get('id', 'unknown')
                    task_dict = {
                        'id': task_id,
                        'description': task.get('description', ''),
                        'task_type': task_type,
                        'required_tools': task.get('required_tools', []),
                        'expected_outputs': task.get('expected_outputs', {})
                    }
                    self.logger.debug(f"Generating workflow")
                    workflow = self.generator.generate_workflow(
                        task_type,
                        task_instance=task_dict
                    )
            
            if not workflow:
                # 创建基本的log_data用于AI分类
                task_id = task.get('instance_id') or task.get('id', 'unknown')
                basic_log_data = {
                    'test_id': f"{model.replace('-', '_').replace('.', '_')}_{task_type}_noworkflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'task_type': task_type,
                    'prompt_type': prompt_type,
                    'timestamp': datetime.now().isoformat(),
                    'task_instance': {
                        'id': task_id,
                        'description': task.get('description', ''),
                        'task_type': task_type,
                        'required_tools': task.get('required_tools', []),
                        'expected_outputs': task.get('expected_outputs', {})
                    },
                    'prompt': '',
                    'llm_response': 'No response - workflow generation failed',
                    'extracted_tool_calls': [],
                    'conversation_history': [],
                    'execution_history': [],
                    'is_flawed': is_flawed,
                    'flaw_type': flaw_type,
                    'result': {'success': False, 'error': 'Failed to generate workflow'}
                }
                return {
                    'success': False,
                    'error': 'Failed to generate workflow',
                    'success_level': 'failure',
                    'tool_calls': [],
                    'turns': 0,
                    'workflow_score': 0.0,
                    'phase2_score': 0.0,
                    'quality_score': 0.0,
                    'final_score': 0.0,
                    '_log_data': basic_log_data
                }
            
            # 创建执行器（与workflow_quality_test_flawed保持一致）
            # 传递prompt_type以便IdealLab API选择正确的key
            actual_prompt_type = prompt_type
            if is_flawed and flaw_type:
                actual_prompt_type = f"flawed_{flaw_type}"
            
            # 使用deployment进行API调用，如果没有指定则使用model
            # 特殊处理qwen-key虚拟实例
            if deployment and deployment.startswith("qwen-key"):
                # qwen-key0/1 是虚拟实例，需要使用实际的模型名
                # 同时提取key索引用于API key选择
                api_model = model  # 使用实际的模型名
                # key索引已经通过self.idealab_key_index传递
                self.logger.debug(f"Using qwen virtual instance {deployment}, actual model: {api_model}")
            else:
                api_model = deployment if deployment else model
            
            executor = InteractiveExecutor(
                tool_registry=self.generator.full_tool_registry,
                llm_client=None,  # 让InteractiveExecutor自动获取
                max_turns=10,     # 与workflow_quality_test_flawed一致
                success_rate=tool_success_rate, # 可配置的工具成功率
                model=api_model,  # 使用deployment名称进行API调用
                idealab_key_index=self.idealab_key_index,  # 传递API key索引
                prompt_type=actual_prompt_type,  # 传递prompt_type用于API key选择
                silent=self.silent  # 传递静默模式标志
            )
            
            # 执行测试
            self.logger.debug(f"Executing workflow with {len(workflow.get('optimal_sequence', []))} steps")
            start_time = time.time()
            
            # 准备task_instance（兼容性处理）
            task_id = task.get('instance_id') or task.get('id', 'unknown')
            task_instance = {
                'id': task_id,
                'description': task.get('description', ''),
                'task_type': task_type,
                'required_tools': task.get('required_tools', []),
                'expected_outputs': task.get('expected_outputs', {})
            }
            
            # 根据不同的prompt类型创建相应的提示
            if is_flawed and flaw_type:
                # 缺陷测试：使用继承的_create_flawed_prompt方法
                initial_prompt = self.quality_tester._create_flawed_prompt(
                    task_type=task_type,
                    workflow=workflow,
                    flaw_type=flaw_type,
                    fixed_task_instance=task_instance
                )
                execution_prompt_type = 'flawed'
            elif prompt_type == 'baseline':
                # 基础提示：使用继承的_create_baseline_prompt方法
                initial_prompt = self.quality_tester._create_baseline_prompt(
                    task_type=task_type,
                    fixed_task_instance=task_instance
                )
                execution_prompt_type = 'baseline'
            elif prompt_type == 'optimal':
                # 最优提示：使用继承的_create_optimal_prompt方法
                initial_prompt = self.quality_tester._create_optimal_prompt(
                    task_type=task_type,
                    workflow=workflow,
                    fixed_task_instance=task_instance
                )
                execution_prompt_type = 'optimal'
            elif prompt_type == 'cot':
                # 思维链提示：使用继承的_create_cot_prompt方法
                initial_prompt = self.quality_tester._create_cot_prompt(
                    task_type=task_type,
                    workflow=workflow,
                    fixed_task_instance=task_instance
                )
                execution_prompt_type = 'cot'
            else:
                # 默认使用任务描述
                initial_prompt = task.get('description', '')
                execution_prompt_type = prompt_type
            
            # 准备日志数据（与workflow_quality_test_flawed一致）
            # 在test_id中包含模型名，放在最前面以便识别
            model_safe = model.replace('-', '_').replace('.', '_')
            log_data = {
                'test_id': f"{model_safe}_{task_type}_inst{task_id}_test{random.randint(0, 999)}_{prompt_type}",
                'task_type': task_type,
                'prompt_type': prompt_type,
                'timestamp': datetime.now().isoformat(),
                'task_instance': task_instance,
                'prompt': initial_prompt,
                'is_flawed': is_flawed,
                'flaw_type': flaw_type
            }
            
            # QPS控制已经移到interactive_executor._get_llm_response中
            # 在每次实际API调用前进行限流，而不是在任务开始时
            
            result = executor.execute_interactive(
                initial_prompt=initial_prompt,
                task_instance=task_instance,
                workflow=workflow,
                prompt_type=execution_prompt_type
            )
            execution_time = time.time() - start_time
            
            # 保存完整的交互历史到日志
            log_data['conversation_history'] = result.get('conversation_history', [])
            log_data['execution_history'] = [
                {
                    'tool': getattr(h, 'tool_name', None) if hasattr(h, 'tool_name') else h.get('tool', ''),
                    'success': getattr(h, 'success', False) if hasattr(h, 'success') else h.get('success', False),
                    'output': str(getattr(h, 'output', '')) if hasattr(h, 'output') else h.get('output'),
                    'error': getattr(h, 'error', None) if hasattr(h, 'error') else h.get('error'),
                    'execution_time': getattr(h, 'execution_time', 0) if hasattr(h, 'execution_time') else h.get('execution_time', 0)
                }
                for h in result.get('execution_history', [])
            ]
            log_data['llm_response'] = json.dumps({
                'conversation': result.get('conversation_history', []),
                'final_state': {
                    'task_completed': result.get('success', False),
                    'tools_executed': result.get('tool_calls', []),
                    'total_turns': result.get('turns', 0)
                }
            }, indent=2)
            log_data['extracted_tool_calls'] = result.get('tool_calls', [])
            # 添加API问题信息到日志
            log_data['api_issues'] = result.get('api_issues', [])
            
            # 添加required_tools和交互历史到结果中
            result['required_tools'] = task.get('required_tools', [])
            result['conversation_history'] = result.get('conversation_history', [])
            # 使用清理过的execution_history，确保可序列化
            result['execution_history'] = log_data['execution_history']
            self.logger.debug(f"Execution completed in {execution_time:.2f}s")
            
            # 计算workflow adherence（继承workflow_quality_test_flawed的逻辑）
            tool_calls = result.get('tool_calls', [])
            expected_sequence = workflow.get('optimal_sequence', [])
            expected_tools = expected_sequence  # optimal_sequence直接就是工具列表
            execution_history = result.get('execution_history', [])
            
            # 调用继承的方法计算adherence
            if hasattr(self.quality_tester, '_calculate_workflow_adherence'):
                adherence_scores = self.quality_tester._calculate_workflow_adherence(
                    expected_tools, tool_calls, execution_history
                )
            else:
                # 备用简单计算
                adherence_scores = {'overall_adherence': 0.0}
                if expected_tools and tool_calls:
                    expected_set = set(expected_tools)
                    actual_set = set(tool_calls)
                    coverage = len(expected_set & actual_set) / len(expected_set) if expected_set else 0
                    adherence_scores['overall_adherence'] = coverage
            
            # 将adherence_scores添加到result中
            result['adherence_scores'] = adherence_scores
            
            # 判断成功
            execution_status = result.get('execution_status', 'failure')
            success = execution_status in ['full_success', 'partial_success']
            
            # 获取错误信息（优先使用InteractiveExecutor生成的智能错误消息）
            error_message = None
            if not success:
                # 使用智能错误消息（如果有）
                error_message = result.get('error_message', None)
                if not error_message:
                    # 退回到旧逻辑
                    if result.get('turns', 0) >= 10:
                        error_message = f"Max turns reached ({result.get('turns', 0)})"
                    else:
                        error_message = result.get('error', 'Unknown error')
            
            # 计算score (使用继承的评分器)
            workflow_score = 0.0
            phase2_score = 0.0
            quality_score = 0.0
            final_score = 0.0
            
            # 使用已计算的adherence_scores
            workflow_score = adherence_scores.get('overall_adherence', 0.0) if adherence_scores else 0.0
            
            # 使用stable_scorer计算phase2和quality分数
            if hasattr(self.quality_tester, 'stable_scorer') and self.quality_tester.stable_scorer:
                try:
                    # 准备评分所需的数据
                    execution_data = {
                        'tool_calls': result.get('tool_calls', []),
                        'execution_time': result.get('execution_time', 0.0),
                        'success_level': execution_status,
                        'output_generated': len(result.get('tool_calls', [])) > 0,
                        'turns': result.get('turns', 0)
                    }
                    
                    evaluation_context = {
                        'task': task,
                        'workflow': workflow,
                        'required_tools': workflow.get('required_tools', []),
                        'expected_time': 10.0,
                        'adherence_scores': adherence_scores
                    }
                    
                    # 调用calculate_stable_score方法
                    phase2_score, score_breakdown = self.quality_tester.stable_scorer.calculate_stable_score(
                        execution_data, evaluation_context
                    )
                    quality_score = score_breakdown.get('execution_quality', 0.0)
                    
                    # 确保返回的score不是None
                    phase2_score = phase2_score if phase2_score is not None else 0.0
                    quality_score = quality_score if quality_score is not None else 0.0
                    
                except Exception as e:
                    self.logger.warning(f"Error in calculate_stable_score: {e}")
                    phase2_score = 0.0
                    quality_score = 0.0
                    # 确保workflow_score也不为None
                    workflow_score = workflow_score if workflow_score is not None else 0.0
            else:
                # stable_scorer不可用，直接报错
                raise RuntimeError(
                    "stable_scorer is not available but required for quality scoring. "
                    "Check WorkflowQualityTester initialization and ensure use_phase2_scoring=True"
                )
            
            # 根据use_phase2_scoring决定final_score
            use_phase2_scoring = getattr(self.quality_tester, 'use_phase2_scoring', True)
            final_score = phase2_score if use_phase2_scoring else workflow_score
            
            # 计算tool_coverage_rate
            required_tools = result.get('required_tools', [])
            executed_tools = result.get('executed_tools', result.get('tool_calls', []))
            tool_coverage_rate = 0.0
            if required_tools:
                required_set = set(required_tools)
                executed_set = set(executed_tools) if executed_tools else set()
                covered_tools = required_set.intersection(executed_set)
                tool_coverage_rate = len(covered_tools) / len(required_tools)
            
            # 正确判定success_level基于分数（处理None值）
            workflow_score = workflow_score or 0.0
            phase2_score = phase2_score or 0.0
            if workflow_score >= 0.8 and phase2_score >= 0.8:
                success_level = 'full_success'
                success = True
            elif workflow_score >= 0.5 or phase2_score >= 0.5:
                success_level = 'partial_success'
                success = True
            else:
                success_level = 'failure'
                success = False
            
            # 调试输出
            if self.debug:
                print(f"[DEBUG] Scores - workflow: {workflow_score:.3f}, phase2: {phase2_score:.3f}, quality: {quality_score:.3f}, final: {final_score:.3f}")
                print(f"[DEBUG] Tool coverage: {tool_coverage_rate:.2%} (required: {required_tools}, executed: {executed_tools})")
                print(f"[DEBUG] Success level: {success_level} (workflow>=0.8: {workflow_score>=0.8}, phase2>=0.8: {phase2_score>=0.8})")
            
            # AI错误分类（如果启用且测试失败）
            ai_error_category = None
            ai_error_reason = None
            ai_confidence = 0.0
            
            # 注意：AI错误分类现在在批处理过程中基于完整的交互日志数据进行
            # 这样可以获得更多的上下文信息，包括完整的对话历史和执行详情
            
            # 返回结果 - 包含所有必要的统计信息和分数
            return_result = {
                'success': success,
                'success_level': success_level,  # 使用基于分数的判定
                'execution_time': execution_time,
                'error': error_message,
                'tool_calls': result.get('tool_calls', []),
                'turns': result.get('turns', 0),
                # 分数指标
                'workflow_score': workflow_score,
                'phase2_score': phase2_score,
                'quality_score': quality_score,
                'final_score': final_score,
                # 添加更多信息以便统计
                'task_type': task_type,
                'prompt_type': prompt_type,
                'difficulty': difficulty,  # 添加difficulty字段
                'is_flawed': is_flawed,
                'flaw_type': flaw_type,
                'tool_success_rate': tool_success_rate,
                # 添加assisted统计相关字段
                'format_error_count': result.get('format_error_count', 0),
                'format_issues': result.get('format_issues', []),
                'api_issues': result.get('api_issues', []),
                # 添加完整的交互历史
                'conversation_history': result.get('conversation_history', []),
                'execution_history': result.get('execution_history', []),
                # 添加required_tools和executed_tools用于tool_coverage计算
                'required_tools': required_tools,
                'executed_tools': executed_tools,
                'tool_coverage_rate': tool_coverage_rate,  # 添加计算好的tool_coverage_rate
                # 添加task_instance
                'task_instance': task_instance,
                # 添加log_data以便保存
                '_log_data': log_data,
                # AI分类结果
                'ai_error_category': ai_error_category,
                'ai_error_reason': ai_error_reason,
                'ai_confidence': ai_confidence
            }
            
            # 保存日志文件（如果启用）- 添加模型名到文件名
            if self.save_logs:
                # 创建一个包含模型信息的TestTask对象，用于_save_interaction_log
                task_obj = TestTask(
                    model=model,
                    task_type=task_type,
                    prompt_type=prompt_type,
                    difficulty=difficulty,
                    tool_success_rate=tool_success_rate,
                    is_flawed=is_flawed,
                    flaw_type=flaw_type
                )
                txt_file_path = self._save_interaction_log(task_obj, return_result, log_data)
                if self.debug and txt_file_path:
                    print(f"[DEBUG] Saved interaction log to {txt_file_path.name}")
            
            return return_result
            
        except Exception as e:
            self.logger.error(f"Test failed with exception: {str(e)}")
            if self.debug:
                self.logger.error(traceback.format_exc())
            
            # 创建错误结果
            error_result = {
                'success': False,
                'error': str(e),
                'execution_time': 0,
                'format_error_count': 0,
                'format_issues': [],
                'api_issues': [],
                'execution_history': [],
                'conversation_history': []
            }
            
            # 即使出现异常也保存日志文件，便于调试
            if self.save_logs:
                try:
                    # 创建包含错误信息的log_data
                    error_log_data = {
                        'test_id': f"{model}_{task_type}_{prompt_type}_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        'task_type': task_type,
                        'prompt_type': prompt_type,
                        'model': model,
                        'error': str(e),
                        'error_type': 'exception',
                        'test_metadata': {
                            'model': model,
                            'task_type': task_type,
                            'prompt_type': prompt_type,
                            'timestamp': datetime.now().isoformat(),
                            'success': False,
                            'failure_reason': f"Exception: {str(e)}"
                        },
                        'conversation_history': [],
                        'test_result': error_result
                    }
                    
                    # 创建TestTask对象用于保存日志
                    task_obj = TestTask(
                        model=model,
                        task_type=task_type,
                        prompt_type=prompt_type,
                        difficulty=difficulty,
                        tool_success_rate=tool_success_rate,
                        is_flawed=is_flawed,
                        flaw_type=flaw_type
                    )
                    
                    # 保存错误日志
                    txt_file_path = self._save_interaction_log(task_obj, error_result, error_log_data)
                    if self.debug and txt_file_path:
                        self.logger.debug(f"Saved exception log to {txt_file_path.name}")
                except Exception as log_error:
                    self.logger.error(f"Failed to save exception log: {log_error}")
            
            return error_result
    
    def run_concurrent_batch(self, tasks: List[TestTask], workers: int = 20, 
                           qps: float = 20.0) -> List[Dict]:
        """并发运行批量测试"""
        self.logger.info(f"Running {len(tasks)} tests with {workers} workers, QPS limit: {qps}")
        
        # 保存QPS值供后续使用
        self.qps = qps
        
        # 预初始化（在主线程中完成初始化）
        self._lazy_init()
        
        # 检测是否是Azure API
        api_provider = None
        if tasks and any(x in tasks[0].model.lower() for x in ['gpt-4o-mini', 'gpt-5', 'deepseek', 'llama-3.3']):
            api_provider = 'azure'
            self.logger.info("Detected Azure API, disabling QPS sleep for better performance")
        
        results = []
        self._test_counter = 0
        self._success_counter = 0
        
        # 本地记录缓存 - 避免并发写入数据库
        local_records = []
        
        # QPS控制（Azure API不需要严格限制）
        # 确保qps不为None
        qps = qps if qps is not None else 0
        min_interval = 0 if api_provider == 'azure' else (1.0 / qps if qps > 0 else 0)
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # 提交所有任务
            self.logger.info(f"Starting batch test with {len(tasks)} tasks, {workers} workers")
            self.logger.info(f"Each task timeout: 10 minutes, Total batch timeout: 20 minutes")
            future_to_task = {}
            for task in tasks:
                # QPS限制（只在需要时应用）
                if min_interval > 0:
                    with self._request_lock:
                        now = time.time()
                        time_since_last = now - self._last_request_time
                        if time_since_last < min_interval:
                            time.sleep(min_interval - time_since_last)
                        self._last_request_time = time.time()
                
                future = executor.submit(
                    self._run_single_test_safe,
                    task
                )
                future_to_task[future] = task
            
            # 收集结果
            try:
                # 合理的超时策略：每个任务60秒，但至少1小时，最多4小时
                total_timeout = max(3600, min(14400, len(tasks) * 60))  # 至少1小时，最多4小时
                self.logger.info(f"Batch timeout set to {total_timeout}s ({total_timeout/60:.1f} minutes) for {len(tasks)} tasks")
                
                for future in as_completed(future_to_task, timeout=total_timeout):
                    task = future_to_task[future]
                    try:
                        result = future.result(timeout=1)  # 快速获取已完成的结果
                        results.append(result)
                        print(f"[DEBUG] Got result for task: has_result={result is not None}, save_logs={self.save_logs}")
                        
                        # 始终获取log_data用于AI分类（无论是否启用save_logs）
                        log_data = None
                        if result:
                            # 从result中获取log_data（总是存在）
                            log_data = result.pop('_log_data', None)
                            if self.debug and log_data:
                                print(f"[DEBUG] Got log_data for {task.task_type}_{task.prompt_type}")
                                print(f"[DEBUG] Log data has conversation_history: {'conversation_history' in log_data}")
                        
                        # 生成TXT内容用于AI分类（不写文件）
                        ai_error_category = None
                        ai_error_reason = None
                        ai_confidence = 0.0
                        
                        if result and log_data:
                            # 检查是否需要AI分类（非full_success都需要分类）
                            success_level = result.get('success_level', '')
                            if not success_level:
                                # 如果没有success_level，需要更细致的判断
                                if result.get('success', False):
                                    # 检查是否是partial_success
                                    # 通过分数判断：workflow_score < 1.0 或 phase2_score < 1.0
                                    workflow_score = result.get('workflow_score', 1.0)
                                    phase2_score = result.get('phase2_score', 1.0)
                                    # 确保不是None值再进行比较
                                    workflow_score = workflow_score if workflow_score is not None else 1.0
                                    phase2_score = phase2_score if phase2_score is not None else 1.0
                                    if workflow_score < 0.8 or phase2_score < 0.8:
                                        success_level = 'partial_success'
                                        print(f"[AI_DEBUG] 检测到partial_success (workflow={workflow_score:.2f}, phase2={phase2_score:.2f})")
                                    else:
                                        success_level = 'full_success'
                                else:
                                    success_level = 'failure'
                            
                            # partial_success和failure都需要AI分类
                            if success_level != 'full_success':
                                print(f"[AI_DEBUG] 测试非完全成功({success_level})，准备调用AI分类")
                                # 生成TXT格式内容（在内存中）
                                txt_content = self._generate_txt_log_content(task, result, log_data)
                                print(f"[AI_DEBUG] 生成的txt_content长度: {len(txt_content) if txt_content else 0}")
                                
                                # 使用TXT内容进行AI分类
                                ai_error_category, ai_error_reason, ai_confidence = self._ai_classify_with_txt_content(task, result, txt_content)
                                print(f"[AI_DEBUG] AI分类结果: category={ai_error_category}, confidence={ai_confidence}")
                                if self.debug and ai_error_category:
                                    print(f"[DEBUG] AI classification: {ai_error_category} (confidence: {ai_confidence:.2f})")
                            
                            # 保存日志文件（所有测试都保存，不仅仅是失败的）
                            if self.save_logs:
                                txt_file_path = self._save_interaction_log(task, result, log_data)
                                if self.debug and txt_file_path:
                                    print(f"[DEBUG] Saved interaction log to {txt_file_path.name}")
                        
                        # 保存到累积数据库
                        if result:
                            record = TestRecord(
                                model=task.model,
                                task_type=task.task_type,
                                prompt_type=task.prompt_type,
                                difficulty=task.difficulty,
                                success=result.get('success', False),
                                execution_time=result.get('execution_time', 0),
                                error_message=result.get('error'),
                                is_flawed=task.is_flawed,
                                flaw_type=task.flaw_type,
                                timestamp=datetime.now().isoformat()
                            )
                            # 添加额外的度量（如果可用）
                            record.turns = result.get('turns', 0)
                            record.tool_calls = result.get('tool_calls', [])
                            record.tool_reliability = task.tool_success_rate  # 记录工具成功率
                            record.required_tools = result.get('required_tools', [])
                            record.executed_tools = result.get('executed_tools', [])
                            # 设置部分成功标志
                            if result.get('success_level') == 'partial_success':
                                record.partial_success = True
                            # 设置成功级别 - 使用execution_status以与cumulative_test_manager保持一致
                            record.execution_status = result.get('success_level', 'failure')
                            record.success_level = result.get('success_level', 'failure')  # 保留以便向后兼容
                            # 添加分数指标
                            record.workflow_score = result.get('workflow_score')
                            record.phase2_score = result.get('phase2_score')
                            record.quality_score = result.get('quality_score')
                            record.final_score = result.get('final_score')
                            
                            # 添加重要的缺失字段
                            record.format_error_count = result.get('format_error_count', 0)
                            record.api_issues = result.get('api_issues', [])
                            record.executed_tools = result.get('executed_tools', [])
                            record.required_tools = result.get('required_tools', task.required_tools if hasattr(task, 'required_tools') else [])
                            
                            # 添加AI分类结果（基于完整交互日志）
                            if ai_error_category:
                                record.ai_error_category = ai_error_category
                                record.ai_error_reason = ai_error_reason
                                record.ai_confidence = ai_confidence
                                if self.debug:
                                    print(f"[DEBUG] Added enhanced AI classification: {ai_error_category} (confidence: {ai_confidence:.2f})")
                            
                            # 添加关键的缺失字段 - tool_coverage_rate和task_instance
                            record.tool_coverage_rate = result.get('tool_coverage_rate', 0.0)
                            record.tool_success_rate = task.tool_success_rate
                            record.task_instance = task.task_instance if hasattr(task, 'task_instance') else {}
                            
                            # 调试输出
                            if self.debug and record.workflow_score is not None:
                                phase2_str = f"{record.phase2_score:.3f}" if record.phase2_score is not None else "0.000"
                                final_str = f"{record.final_score:.3f}" if record.final_score is not None else "0.000"
                                print(f"[DEBUG] Caching record - workflow: {record.workflow_score:.3f}, phase2: {phase2_str}, final: {final_str}")
                            
                            # 添加到本地缓存而不是直接写数据库
                            with self._lock:
                                local_records.append(record)
                            
                            # 检查是否需要checkpoint
                            if not self.enable_database_updates and self.checkpoint_interval > 0:
                                # 添加到结果中以便checkpoint
                                result['model'] = task.model
                                result['difficulty'] = task.difficulty
                                self._smart_checkpoint_save([result], task.model)
                        
                        # 更新进度
                        if not self.silent:
                            with self._lock:
                                self._test_counter += 1
                                if result.get('success', False):
                                    self._success_counter += 1
                                if self._test_counter % 10 == 0:
                                    print(f"Progress: {self._test_counter}/{len(tasks)} "
                                         f"(Success: {self._success_counter})")
                    
                    except Exception as e:
                        self.logger.error(f"Task failed: {e}")
                        if self.debug:
                            import traceback
                            traceback.print_exc()
                        results.append({'success': False, 'error': str(e)})
                        # 记录失败的测试
                        try:
                                record = TestRecord(
                                    model=task.model,
                                    task_type=task.task_type,
                                    prompt_type=task.prompt_type,
                                    difficulty=task.difficulty,
                                    success=False,
                                    execution_time=0,
                                    error_message=str(e),
                                    timestamp=datetime.now().isoformat()
                                )
                                # 添加缺失的字段以避免AttributeError
                                record.format_error_count = 0
                                record.api_issues = []
                                record.executed_tools = []
                                record.required_tools = task.required_tools if hasattr(task, 'required_tools') else []
                                # 添加到本地缓存
                                with self._lock:
                                    local_records.append(record)
                        except Exception as record_error:
                            self.logger.error(f"Failed to create error record: {record_error}")
            
            except TimeoutError:
                # 整体超时，取消剩余的任务
                self.logger.warning(f"Batch execution timeout, cancelling remaining tasks")
                for future in future_to_task:
                    if not future.done():
                        future.cancel()
                # 等待正在执行的任务完成后关闭executor
                # 注意：这里应该等待，否则可能丢失最后的任务结果
                executor.shutdown(wait=True, cancel_futures=True)
        
        # 如果使用checkpoint，最后保存剩余的
        if not self.enable_database_updates and self.checkpoint_interval > 0:
            self._smart_checkpoint_save([], force=True)
            
        # 确保所有待保存的数据都已写入
        # 这很重要，特别是对于最后一批不足checkpoint_interval的数据
        if self.pending_results:
            self.logger.info(f"Final flush: Saving remaining {len(self.pending_results)} results")
            self._smart_checkpoint_save([], force=True)
        
        # 批量写入所有记录到数据库
        # 统计模型分布
        model_counts = {}
        for record in local_records:
            model = getattr(record, 'model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        
        model_distribution = ", ".join([f"{model}:{count}" for model, count in model_counts.items()])
        write_start_msg = f"Batch writing {len(local_records)} records to database ({model_distribution})"
        print(f"\n[INFO] {write_start_msg}")
        self.logger.info(write_start_msg)
        
        # 使用存储适配器批量写入
        successful_writes = 0
        if self.storage_adapter:
            successful_writes = self.storage_adapter.write_batch(local_records)
        else:
            self.logger.error("No storage adapter available for writing records")
        
        write_complete_msg = f"Successfully wrote {successful_writes}/{len(local_records)} records ({model_distribution})"
        print(f"[INFO] {write_complete_msg}")
        self.logger.info(write_complete_msg)
        
        # 最终保存和错误统计
        if isinstance(self.manager, EnhancedCumulativeManager):
            # 完成所有统计并生成报告
            self.manager.finalize()
            
            # 显示运行时错误统计摘要
            summary = self.manager.get_runtime_summary()
            for model_name, model_summary in summary.items():
                self.logger.info(f"Error summary for {model_name}: {model_summary['total_errors']} total errors")
        else:
            self.manager.save_database()
        self.logger.info("Database saved successfully")
        
        # 显示保存位置（并发模式）
        if not self.silent:
            db_path = Path("pilot_bench_cumulative_results/master_database.json")
            if db_path.exists():
                save_msg = f"Statistics saved to: {db_path.absolute()}"
                print(f"\n📊 {save_msg}")
                self.logger.info(save_msg)
        
        # 记录最终统计
        self.logger.info("="*60)
        self.logger.info(f"Batch test completed at {datetime.now().isoformat()}")
        self.logger.info(f"Summary:")
        self.logger.info(f"  - Total tests: {len(results)}")
        self.logger.info(f"  - Successful: {self._success_counter}")
        self.logger.info(f"  - Failed: {len(results) - self._success_counter}")
        if results:
            self.logger.info(f"  - Success rate: {self._success_counter/len(results)*100:.1f}%")
        self.logger.info(f"  - Log file: {self.log_filename}")
        self.logger.info("="*60)
        
        return results
    
    def _checkpoint_save(self, results, task_model=None, force=False):
        """中间保存检查点"""
        if not self.checkpoint_interval or self.enable_database_updates:
            return  # 如果没有设置checkpoint或已经实时写入，则不需要
        
        # 将结果添加到pending缓存
        if results:
            if isinstance(results, list):
                self.pending_results.extend(results)
            else:
                self.pending_results.append(results)
        
        # 检查是否需要保存
        # 修改保存条件：force时强制保存，或者达到checkpoint_interval，或者interval为0时立即保存
        should_save = force or (self.checkpoint_interval == 0 and len(self.pending_results) > 0) or                      (self.checkpoint_interval > 0 and len(self.pending_results) >= self.checkpoint_interval)
        
        if should_save and self.pending_results:
            print(f"\n💾 Checkpoint: 保存{len(self.pending_results)}个中间结果...")
            
            # 确保已初始化manager
            self._lazy_init()
            
            # 使用现有的manager实例（不创建新的！）
            try:
                from cumulative_test_manager import TestRecord
                
                saved_count = 0
                
                for result in self.pending_results:
                    if result and not result.get('_saved', False):
                        # 从结果中提取信息创建TestRecord
                        record = TestRecord(
                            model=result.get('model', task_model or 'unknown'),
                            task_type=result.get('task_type', 'unknown'),
                            prompt_type=result.get('prompt_type', 'baseline'),
                            difficulty=result.get('difficulty', 'easy')
                        )
                        
                        # 设置其他字段
                        for field in ['timestamp', 'success', 'success_level', 'execution_time', 'turns',
                                    'tool_calls', 'workflow_score', 'phase2_score', 'quality_score',
                                    'final_score', 'error_type', 'tool_success_rate', 'is_flawed',
                                    'flaw_type', 'format_error_count', 'api_issues', 'executed_tools',
                                    'required_tools', 'tool_coverage_rate', 'task_instance', 'execution_history',
                                    'ai_error_category', '_ai_error_category']:  # Added AI classification fields
                            if field in result:
                                # Handle _ai_error_category -> ai_error_category conversion
                                if field == '_ai_error_category':
                                    setattr(record, 'ai_error_category', result[field])
                                else:
                                    setattr(record, field, result[field])
                        
                        # 使用存储适配器保存
                        if self.storage_adapter and self.storage_adapter.write_result(record):
                            result['_saved'] = True
                            saved_count += 1
                
                # 刷新缓冲区（特别重要对于Parquet格式）
                if hasattr(self.manager, '_flush_buffer'):
                    self.logger.debug(f"[Checkpoint] Flushing buffer after {saved_count} records")
                    self.manager._flush_buffer()
                
                print(f"✅ Checkpoint完成: 已保存{saved_count}个结果")
                
                # 清空已保存的结果
                self.pending_results = [r for r in self.pending_results if not r.get('_saved', False)]
                
            except Exception as e:
                self.logger.error(f"Checkpoint save failed: {e}")
                print(f"⚠️  Checkpoint保存失败: {e}")
    
    def run_adaptive_concurrent_batch(self, tasks: List[TestTask], 
                                    initial_workers: int = 20,  # 激进的初始并发数
                                    initial_qps: float = 50.0) -> List[Dict]:  # 高初始QPS
        """使用自适应限流的并发批量测试"""
        self.logger.info(f"Running {len(tasks)} tests with adaptive rate limiting")
        self.logger.info(f"Initial settings: workers={initial_workers}, QPS={initial_qps}")
        
        # 预初始化
        self._lazy_init()
        
        # 检测API提供商并自动调整参数
        api_provider = None
        if tasks:
            model = tasks[0].model
            if any(x in model.lower() for x in ['qwen', 'llama-4-scout', 'o1']):
                api_provider = 'idealab'
                self.logger.info(f"Detected idealab API for model {model}, using conservative settings")
            elif any(x in model.lower() for x in ['deepseek', 'llama-3.3', 'gpt-4o-mini', 'gpt-5']):
                # Azure API模型，使用极高并发
                api_provider = 'azure'
                initial_workers = max(80, initial_workers)  # 至少80并发
                initial_qps = max(150, initial_qps)  # 至少150 QPS
                self.logger.info(f"Detected Azure API for model {model}, using very high concurrency settings (100+ workers max)")
        
        # 创建自适应限流器（Azure API使用更高的上限）
        max_workers_limit = 100 if api_provider == 'azure' else 50  # Azure允许100并发
        max_qps_limit = 200 if api_provider == 'azure' else 100  # Azure允许200 QPS
        
        rate_limiter = AdaptiveRateLimiter(
            initial_workers=initial_workers,
            initial_qps=initial_qps,
            min_workers=2,  # 最小也保持2个并发
            max_workers=max_workers_limit,  # Azure: 100, 其他: 50
            min_qps=5,  # 最小也保持5 QPS
            max_qps=max_qps_limit,  # Azure: 200, 其他: 100
            backoff_factor=0.7,  # 降速不那么激进（原来0.5）
            recovery_factor=1.8,  # 提速更激进（原来1.5）
            stable_threshold=3,  # 更快触发提速（原来5）
            logger=self.logger,
            api_provider=api_provider  # 传递API提供商信息
        )
        
        results = []
        self._test_counter = 0
        self._success_counter = 0
        completed_tasks = 0
        failed_tasks = 0
        retry_queue = []
        
        # 主执行循环
        task_index = 0
        while task_index < len(tasks) or retry_queue:
            # 获取当前限制
            workers, qps = rate_limiter.get_current_limits()
            
            # 决定本批次执行的任务
            if retry_queue and len(retry_queue) >= workers:
                # 优先处理重试队列
                batch_tasks = retry_queue[:workers]
                retry_queue = retry_queue[workers:]
                is_retry = True
            else:
                # 混合新任务和重试任务
                batch_size = min(workers, len(tasks) - task_index + len(retry_queue))
                batch_tasks = []
                
                # 先加入重试任务
                while retry_queue and len(batch_tasks) < batch_size:
                    batch_tasks.append((retry_queue.pop(0), True))
                
                # 再加入新任务
                while task_index < len(tasks) and len(batch_tasks) < batch_size:
                    batch_tasks.append((tasks[task_index], False))
                    task_index += 1
                
                if not batch_tasks:
                    break
            
            self.logger.info(
                f"Executing batch: {len(batch_tasks)} tasks "
                f"(workers={workers}, QPS={qps}, completed={completed_tasks}/{len(tasks)})"
            )
            
            # QPS控制
            # 确保qps不为None
            qps = qps if qps is not None else 0
            min_interval = 1.0 / qps if qps > 0 else 0
            
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_task = {}
                
                for item in batch_tasks:
                    if isinstance(item, tuple):
                        task, is_retry = item
                    else:
                        task = item
                        is_retry = False
                    
                    # QPS限制
                    if min_interval > 0:
                        rate_limiter.wait_if_needed()
                    
                    future = executor.submit(self._run_single_test_safe, task)
                    future_to_task[future] = (task, is_retry)
                
                # 收集结果
                for future in as_completed(future_to_task):
                    task, is_retry = future_to_task[future]
                    try:
                        result = future.result()
                        
                        # 检查是否是限流错误
                        if result and not result.get('success', False):
                            error_msg = result.get('error', '')
                            if 'TPM/RPM限流' in error_msg or 'rate limit' in error_msg.lower():
                                # 记录限流
                                rate_limiter.record_rate_limit(error_msg)
                                # 加入重试队列
                                if not is_retry or task not in [t for t, _ in retry_queue if isinstance(t, tuple)]:
                                    retry_queue.append(task)
                                    self.logger.info(f"Task added to retry queue due to rate limit")
                                continue
                            else:
                                # 其他错误
                                rate_limiter.record_error(error_msg)
                        elif result and result.get('success', False):
                            # 成功
                            rate_limiter.record_success()
                            completed_tasks += 1
                            self._success_counter += 1
                        
                        # 添加到结果
                        results.append(result)
                        
                        # 检查是否需要checkpoint保存
                        if not self.enable_database_updates and self.checkpoint_interval > 0:
                            # 添加必要的字段
                            if result:
                                result['model'] = task.model
                                result['difficulty'] = task.difficulty
                            self._smart_checkpoint_save([result], task.model)
                        
                        # 保存到数据库（修复：run_adaptive_concurrent_batch缺少的数据保存）
                        if result:
                            record = TestRecord(
                                model=task.model,
                                task_type=task.task_type,
                                prompt_type=task.prompt_type,
                                difficulty=task.difficulty,
                                success=result.get('success', False),
                                execution_time=result.get('execution_time', 0),
                                error_message=result.get('error'),
                                is_flawed=task.is_flawed,
                                flaw_type=task.flaw_type,
                                timestamp=datetime.now().isoformat()
                            )
                            # 添加额外信息
                            record.turns = result.get('turns', 0)
                            record.tool_calls = result.get('tool_calls', [])
                            record.tool_reliability = task.tool_success_rate
                            record.required_tools = result.get('required_tools', [])
                            record.executed_tools = result.get('executed_tools', [])
                            if result.get('success_level') == 'partial_success':
                                record.partial_success = True
                            record.execution_status = result.get('success_level', 'failure')
                            record.success_level = result.get('success_level', 'failure')
                            record.workflow_score = result.get('workflow_score')
                            record.phase2_score = result.get('phase2_score')
                            record.quality_score = result.get('quality_score')
                            record.final_score = result.get('final_score')
                            record.format_error_count = result.get('format_error_count', 0)
                            record.api_issues = result.get('api_issues', [])
                            record.executed_tools = result.get('executed_tools', [])  # Fixed: should be executed_tools not tool_calls
                            record.required_tools = result.get('required_tools', task.required_tools if hasattr(task, 'required_tools') else [])
                            
                            # 添加关键的缺失字段
                            record.tool_coverage_rate = result.get('tool_coverage_rate', 0.0)
                            record.tool_success_rate = task.tool_success_rate
                            record.task_instance = task.task_instance if hasattr(task, 'task_instance') else {}
                            
                            # 使用存储适配器保存
                            if self.storage_adapter:
                                try:
                                    self.storage_adapter.write_result(record)
                                except Exception as e:
                                    self.logger.error(f"Failed to save record: {e}")
                        
                        # 获取或创建log_data用于AI分类
                        log_data = None
                        if result:
                            # 对于超时的情况，创建基本的log_data
                            if result.get('error_type') == 'timeout':
                                log_data = {
                                    'test_id': f"{task.task_type}_timeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                    'task_type': task.task_type,
                                    'prompt_type': task.prompt_type,
                                    'timestamp': datetime.now().isoformat(),
                                    'task_instance': {'required_tools': task.required_tools or []},
                                    'prompt': 'Timeout before prompt execution',
                                    'llm_response': 'Timeout - no response received',
                                    'extracted_tool_calls': [],
                                    'conversation_history': [],
                                    'execution_history': [],
                                    'is_flawed': task.is_flawed,
                                    'flaw_type': task.flaw_type,
                                    'result': {
                                        'success': False,
                                        'error': result.get('error', 'Timeout'),
                                        'error_type': 'timeout',
                                        'execution_time': result.get('execution_time', 60)
                                    }
                                }
                            else:
                                # 从result中获取log_data（总是存在）
                                log_data = result.pop('_log_data', None)
                        
                        # 生成TXT内容用于AI分类（不写文件）
                        if result and log_data:
                            # 如果有错误，生成TXT内容并进行AI分类
                            if not result.get('success', False):
                                try:
                                    # 生成TXT格式内容（在内存中）
                                    txt_content = self._generate_txt_log_content(task, result, log_data)
                                    
                                    # 使用TXT内容进行AI分类
                                    ai_cat, ai_reason, ai_conf = self._ai_classify_with_txt_content(task, result, txt_content)
                                    if ai_cat:
                                        # 将AI分类结果添加到result中，后续创建record时会使用
                                        result['_ai_error_category'] = ai_cat
                                        result['_ai_error_reason'] = ai_reason
                                        result['_ai_confidence'] = ai_conf
                                        if self.debug:
                                            print(f"[DEBUG] AI classification for timeout: {ai_cat} (confidence: {ai_conf:.2f})")
                                except Exception as e:
                                    if self.debug:
                                        print(f"[DEBUG] AI classification failed: {e}")
                            
                            # 如果需要保存日志文件
                            if self.save_logs:
                                txt_file_path = self._save_interaction_log(task, result, log_data)
                                if self.debug and txt_file_path:
                                    print(f"[DEBUG] Saved interaction log to {txt_file_path.name}")
                        
                        # 保存到数据库
                        if result:
                            record = TestRecord(
                                model=task.model,
                                task_type=task.task_type,
                                prompt_type=task.prompt_type,
                                difficulty=task.difficulty,
                                success=result.get('success', False),
                                execution_time=result.get('execution_time', 0),
                                error_message=result.get('error'),
                                is_flawed=task.is_flawed,
                                flaw_type=task.flaw_type,
                                timestamp=datetime.now().isoformat()
                            )
                            # 添加额外信息
                            record.turns = result.get('turns', 0)
                            record.tool_calls = result.get('tool_calls', [])
                            record.tool_reliability = task.tool_success_rate
                            record.required_tools = result.get('required_tools', [])
                            record.executed_tools = result.get('executed_tools', [])
                            if result.get('success_level') == 'partial_success':
                                record.partial_success = True
                            record.execution_status = result.get('success_level', 'failure')
                            record.success_level = result.get('success_level', 'failure')
                            record.workflow_score = result.get('workflow_score')
                            record.phase2_score = result.get('phase2_score')
                            record.quality_score = result.get('quality_score')
                            record.final_score = result.get('final_score')
                            record.tool_coverage_rate = result.get('tool_coverage_rate', 0.0)
                            record.required_tools = result.get('required_tools', task.required_tools if hasattr(task, 'required_tools') else [])
                            record.format_error_count = result.get('format_error_count', 0)
                            
                            # 添加其他关键字段
                            record.tool_success_rate = task.tool_success_rate
                            record.task_instance = task.task_instance if hasattr(task, 'task_instance') else {}
                            
                            # 添加AI分类结果（如果存在）
                            if result.get('_ai_error_category'):
                                record.ai_error_category = result['_ai_error_category']
                                record.ai_error_reason = result.get('_ai_error_reason', '')
                                record.ai_confidence = result.get('_ai_confidence', 0.0)
                                if self.debug:
                                    print(f"[DEBUG] Added AI classification to record: {record.ai_error_category}")
                            
                            # 使用存储适配器保存
                            if self.storage_adapter:
                                self.storage_adapter.write_result(record)
                        
                        # 更新计数器
                        with self._lock:
                            self._test_counter += 1
                            if self._test_counter % 10 == 0:
                                self.logger.info(f"Progress: {self._test_counter} tests completed")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to process result: {e}")
                        failed_tasks += 1
            
            # 打印当前统计
            stats = rate_limiter.get_stats_summary()
            self.logger.info(f"Adaptive stats: {stats}")
            
            # 如果连续限流太多次，增加等待（但更智能）
            if rate_limiter.consecutive_rate_limits > 10:  # 提高阈值
                # Azure API几乎不需要等待
                if api_provider == 'azure':
                    wait_time = 0.5  # Azure最多等0.5秒
                else:
                    wait_time = min(2.0, rate_limiter.get_retry_delay())  # 其他API最多等2秒
                if wait_time > 0:
                    self.logger.warning(f"Too many consecutive rate limits ({rate_limiter.consecutive_rate_limits}), waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
        
        # 最后一次checkpoint保存（强制）
        if not self.enable_database_updates and self.checkpoint_interval > 0:
            self._smart_checkpoint_save([], force=True)
        
        # 确保所有pending_results都被保存（即使不满checkpoint_interval）
        if self.pending_results and not self.enable_database_updates:
            print(f"\n💾 Final save: 保存剩余的{len(self.pending_results)}个结果...")
            self._smart_checkpoint_save([], force=True)
        
        # 最终统计
        self.logger.info("="*60)
        self.logger.info(f"Adaptive batch test completed")
        self.logger.info(f"Final statistics:")
        self.logger.info(f"  - Total tests: {len(results)}")
        self.logger.info(f"  - Successful: {self._success_counter}")
        self.logger.info(f"  - Failed: {len(results) - self._success_counter}")
        self.logger.info(f"  - Retries: {len(retry_queue)} remaining")
        if results:
            self.logger.info(f"  - Success rate: {self._success_counter/len(results)*100:.1f}%")
        
        final_stats = rate_limiter.get_stats_summary()
        self.logger.info(f"  - Rate limit hits: {final_stats['rate_limit_count']}")
        self.logger.info(f"  - Final workers: {final_stats['current_workers']}")
        self.logger.info(f"  - Final QPS: {final_stats['current_qps']}")
        self.logger.info("="*60)
        
        # 确保所有数据都保存到数据库（修复：刷新缓冲区）
        if isinstance(self.manager, EnhancedCumulativeManager):
            self.manager.finalize()
            self.logger.info("Database updates finalized")
        
        return results
    
    def _run_single_test_safe(self, task: TestTask) -> Dict:
        """线程安全的单个测试执行（使用嵌套线程池实现超时）"""
        import sys
        import threading
        from datetime import datetime
        from concurrent.futures import ThreadPoolExecutor, TimeoutError
        import signal
        
        # 记录开始时间
        start_time = time.time()
        
        # 无论是否在主线程，都使用ThreadPoolExecutor实现超时
        # 这样可以确保在worker线程中也能正确超时
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                self.run_single_test,
                model=task.model,
                deployment=getattr(task, 'deployment', None),  # 传递部署实例名（如果存在）
                task_type=task.task_type,
                prompt_type=task.prompt_type,
                is_flawed=task.is_flawed,
                flaw_type=task.flaw_type,
                timeout=task.timeout,
                tool_success_rate=task.tool_success_rate,
                difficulty=task.difficulty
            )
            
            # 使用合理的超时策略
            timeout_seconds = 900  # 15分钟超时（平衡稳定性和效率）
            
            try:
                # 等待结果，但使用更短的超时
                result = future.result(timeout=timeout_seconds)
                return result
            except TimeoutError:
                # 记录实际运行时间
                actual_runtime = time.time() - start_time
                self.logger.error(f"Test timeout after {actual_runtime:.1f} seconds (limit: {timeout_seconds}s)")
                
                # 尝试取消（虽然可能无效）
                cancelled = future.cancel()
                if not cancelled:
                    self.logger.warning("Failed to cancel the running task (already executing)")
                    # 强制关闭executor，不等待任务完成
                    executor.shutdown(wait=False, cancel_futures=True)
                
                self.logger.error(f"Test forcibly terminated after {timeout_seconds} seconds")
                # 为超时创建基本的log_data，用于AI分类
                timeout_log_data = {
                    'test_id': f"{task.task_type}_timeout_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'task_type': task.task_type,
                    'prompt_type': task.prompt_type,
                    'timestamp': datetime.now().isoformat(),
                    'task_instance': {'required_tools': task.required_tools or []},
                    'prompt': 'Task timeout after 10 minutes',
                    'llm_response': 'No response - timeout after 10 minutes',
                    'extracted_tool_calls': [],
                    'conversation_history': [],
                    'execution_history': [],
                    'is_flawed': task.is_flawed,
                    'flaw_type': task.flaw_type,
                    'result': {
                        'success': False,
                        'error': 'Test timeout after 10 minutes',
                        'error_type': 'timeout',
                        'execution_time': 600
                    }
                }
                
                return {
                    'success': False,
                    'error': 'Test timeout after 10 minutes',
                    'error_type': 'timeout',
                    'execution_time': 600,
                    'success_level': 'failure',
                    'tool_calls': [],
                    'turns': 0,
                    'workflow_score': 0.0,
                    'phase2_score': 0.0,
                    'quality_score': 0.0,
                    'final_score': 0.0,
                    'task_type': task.task_type,
                    'prompt_type': task.prompt_type,
                    'difficulty': task.difficulty,
                    'is_flawed': task.is_flawed,
                    'flaw_type': task.flaw_type,
                    'tool_success_rate': task.tool_success_rate,
                    'required_tools': task.required_tools or [],
                    'executed_tools': [],
                    'tool_coverage_rate': 0.0,
                    '_log_data': timeout_log_data  # 添加log_data以支持AI分类
                }
            except Exception as e:
                self.logger.error(f"Test execution failed: {e}")
                # 为异常创建基本的log_data，用于AI分类
                exception_log_data = {
                    'test_id': f"{task.task_type}_exception_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    'task_type': task.task_type,
                    'prompt_type': task.prompt_type,
                    'timestamp': datetime.now().isoformat(),
                    'task_instance': {'required_tools': task.required_tools or []},
                    'prompt': f'Task failed with exception: {str(e)}',
                    'llm_response': 'No response - execution exception',
                    'extracted_tool_calls': [],
                    'conversation_history': [],
                    'execution_history': [],
                    'is_flawed': task.is_flawed,
                    'flaw_type': task.flaw_type,
                    'result': {
                        'success': False,
                        'error': str(e),
                        'error_type': 'execution_error',
                        'execution_time': 0
                    }
                }
                
                return {
                    'success': False,
                    'error': str(e),
                    'error_type': 'execution_error',
                    'execution_time': 0,
                    'success_level': 'failure',
                    'tool_calls': [],
                    'turns': 0,
                    'workflow_score': 0.0,
                    'phase2_score': 0.0,
                    'quality_score': 0.0,
                    'final_score': 0.0,
                    'task_type': task.task_type,
                    'prompt_type': task.prompt_type,
                    'difficulty': task.difficulty,
                    'is_flawed': task.is_flawed,
                    'flaw_type': task.flaw_type,
                    'tool_success_rate': task.tool_success_rate,
                    'required_tools': task.required_tools or [],
                    'executed_tools': [],
                    'tool_coverage_rate': 0.0,
                    '_log_data': exception_log_data  # 添加log_data以支持AI分类
                }
    
    def get_smart_tasks(self, model: str, count: int, difficulty: str = "easy", 
                        tool_success_rate: float = 0.8,
                        selected_prompt_types: List[str] = None,
                        selected_task_types: List[str] = None) -> List[TestTask]:
        """智能选择需要测试的任务
        
        Args:
            count: 每种组合的测试数量 (prompt × task × difficulty)
            selected_prompt_types: 要测试的prompt类型，None或["all"]表示全部
            selected_task_types: 要测试的任务类型，None或["all"]表示全部
        
        实验计划：10种prompt策略 × 5种task_type = 50种组合
        - 3种基本prompt: baseline, optimal, cot
        - 7种缺陷prompt: 每种flaw_type对应一个
        - 5种任务类型: simple_task, basic_task, data_pipeline, api_integration, multi_stage_pipeline
        """
        self._lazy_init()
        
        # 默认的任务类型
        all_task_types = ["simple_task", "basic_task", "data_pipeline", "api_integration", "multi_stage_pipeline"]
        
        # 决定要测试的任务类型
        if selected_task_types is None or (len(selected_task_types) == 1 and selected_task_types[0] == "all"):
            task_types = all_task_types
        else:
            # 验证选择的任务类型
            task_types = [t for t in selected_task_types if t in all_task_types]
            if not task_types:
                self.logger.warning(f"No valid task types found in {selected_task_types}, using all")
                task_types = all_task_types
        
        # 定义所有可能的prompt策略
        all_prompt_strategies = [
            # 3种基本prompt
            {"prompt_type": "baseline", "is_flawed": False, "flaw_type": None},
            {"prompt_type": "optimal", "is_flawed": False, "flaw_type": None},
            {"prompt_type": "cot", "is_flawed": False, "flaw_type": None},
            # 7种缺陷prompt（使用具体的prompt_type名称）
            {"prompt_type": "flawed_sequence_disorder", "is_flawed": True, "flaw_type": "sequence_disorder"},
            {"prompt_type": "flawed_tool_misuse", "is_flawed": True, "flaw_type": "tool_misuse"},
            {"prompt_type": "flawed_parameter_error", "is_flawed": True, "flaw_type": "parameter_error"},
            {"prompt_type": "flawed_missing_step", "is_flawed": True, "flaw_type": "missing_step"},
            {"prompt_type": "flawed_redundant_operations", "is_flawed": True, "flaw_type": "redundant_operations"},
            {"prompt_type": "flawed_logical_inconsistency", "is_flawed": True, "flaw_type": "logical_inconsistency"},
            {"prompt_type": "flawed_semantic_drift", "is_flawed": True, "flaw_type": "semantic_drift"},
        ]
        
        # 决定要测试的prompt策略
        if selected_prompt_types is None or (len(selected_prompt_types) == 1 and selected_prompt_types[0] == "all"):
            prompt_strategies = all_prompt_strategies
        else:
            prompt_strategies = []
            for pt in selected_prompt_types:
                if pt == "baseline":
                    prompt_strategies.append({"prompt_type": "baseline", "is_flawed": False, "flaw_type": None})
                elif pt == "optimal":
                    prompt_strategies.append({"prompt_type": "optimal", "is_flawed": False, "flaw_type": None})
                elif pt == "cot":
                    prompt_strategies.append({"prompt_type": "cot", "is_flawed": False, "flaw_type": None})
                elif pt == "flawed":
                    # 添加所有缺陷类型
                    for s in all_prompt_strategies:
                        if s["is_flawed"]:
                            prompt_strategies.append(s)
                elif pt.startswith("flawed_"):
                    # 特定的缺陷类型
                    flaw_type = pt.replace("flawed_", "")
                    for s in all_prompt_strategies:
                        if s["is_flawed"] and s["flaw_type"] == flaw_type:
                            prompt_strategies.append(s)
                            break
            
            if not prompt_strategies:
                self.logger.warning(f"No valid prompt types found in {selected_prompt_types}, using all")
                prompt_strategies = all_prompt_strategies
        
        # 生成所有组合
        all_combinations = []
        for strategy in prompt_strategies:
            for task_type in task_types:
                combination = {
                    'task_type': task_type,
                    'strategy': strategy
                }
                all_combinations.append(combination)
        
        # count现在表示每种组合的测试数量
        self.logger.info(f"Creating {count} tests for each of {len(all_combinations)} combinations")
        self.logger.info(f"Total tests: {count * len(all_combinations)}")
        
        tasks = []
        
        # 为每种组合创建指定数量的测试
        for combo in all_combinations:
            for _ in range(count):
                strategy = combo['strategy']
                task = TestTask(
                    model=model,
                    task_type=combo['task_type'],
                    prompt_type=strategy["prompt_type"],
                    difficulty=difficulty,
                    is_flawed=strategy["is_flawed"],
                    flaw_type=strategy["flaw_type"],
                    tool_success_rate=tool_success_rate
                )
                tasks.append(task)
        
        # 打乱顺序以避免批次效应
        random.shuffle(tasks)
        
        # 记录分配统计
        if not self.silent:
            self._log_task_distribution(tasks)
            self._log_detailed_distribution(tasks)
        
        return tasks
    
    def _log_task_distribution(self, tasks: List[TestTask]):
        """记录任务分配统计"""
        distribution = {}
        for task in tasks:
            if task.is_flawed:
                key = f"flawed_{task.flaw_type}"
            else:
                key = task.prompt_type
            distribution[key] = distribution.get(key, 0) + 1
        
        self.logger.info("Task distribution by prompt strategy:")
        for strategy, count in sorted(distribution.items()):
            self.logger.info(f"  {strategy}: {count}")
    
    def _log_detailed_distribution(self, tasks: List[TestTask]):
        """记录详细的任务分配统计"""
        # 按task_type统计
        task_type_dist = {}
        for task in tasks:
            task_type_dist[task.task_type] = task_type_dist.get(task.task_type, 0) + 1
        
        self.logger.info("Task distribution by task type:")
        for task_type, count in sorted(task_type_dist.items()):
            self.logger.info(f"  {task_type}: {count}")
        
        # 检查分配均衡性
        combo_stats = {}
        for task in tasks:
            if task.is_flawed:
                combo_key = f"{task.task_type}_{task.flaw_type}"
            else:
                combo_key = f"{task.task_type}_{task.prompt_type}"
            combo_stats[combo_key] = combo_stats.get(combo_key, 0) + 1
        
        counts = list(combo_stats.values())
        min_count = min(counts) if counts else 0
        max_count = max(counts) if counts else 0
        
        self.logger.info(f"Combination balance: min={min_count}, max={max_count}, diff={max_count-min_count}")
    
    # 注意：prompt创建方法现在通过 self.quality_tester 继承
    # 不再需要本地实现 _create_flawed_workflow_prompt 和 _format_workflow_sequence
    
    def show_progress(self, model: str, detailed: bool = False):
        """显示测试进度"""
        self._lazy_init()
        
        progress = self.manager.get_progress_report(model)
        
        print(f"\n{'='*60}")
        print(f"Progress Report for {model}")
        print(f"{'='*60}")
        
        if model in progress.get('models', {}):
            model_data = progress['models'][model]
            print(f"Total tests: {model_data['total_tests']}")
            print(f"Total success: {model_data['total_success']}")
            
            if detailed:
                print("\nBy task type:")
                for task_type, stats in model_data.get('by_task_type', {}).items():
                    print(f"  {task_type}: {stats['total']} tests, {stats['success']} success")
                
                print("\nBy prompt type:")
                for prompt_type, stats in model_data.get('by_prompt_type', {}).items():
                    print(f"  {prompt_type}: {stats['total']} tests, {stats['success']} success")
                
                print("\nBy flaw type:")
                for flaw_type, stats in model_data.get('by_flaw_type', {}).items():
                    print(f"  {flaw_type}: {stats['total']} tests, {stats['success']} success")
        else:
            print("No test data found for this model")
        
        print(f"{'='*60}\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='PILOT-Bench Batch Test Runner')
    
    # 基本参数
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                       help='Model to test')
    parser.add_argument('--count', type=int, default=2,
                       help='Number of tests per combination (prompt × task × difficulty)')
    parser.add_argument('--difficulty', type=str, default='easy',
                       choices=['very_easy', 'easy', 'medium', 'hard', 'very_hard'],
                       help='Task difficulty level')
    
    # 测试模式
    parser.add_argument('--smart', action='store_true',
                       help='Smart mode - prioritize needed tests')
    parser.add_argument('--progress', action='store_true',
                       help='Show progress only')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed progress')
    
    # 并发参数
    parser.add_argument('--concurrent', action='store_true',
                       help='Enable concurrent execution')
    parser.add_argument('--adaptive', action='store_true',
                       help='Enable adaptive rate limiting (recommended)')
    parser.add_argument('--workers', type=int, default=20,
                       help='Number of concurrent workers (or initial workers for adaptive mode)')
    parser.add_argument('--qps', type=float, default=20.0,
                       help='Queries per second limit (or initial QPS for adaptive mode)')
    
    # 输出控制
    parser.add_argument('--silent', action='store_true',
                       help='Silent mode - minimal output')
    parser.add_argument('--debug', action='store_true',
                       help='Debug mode - verbose output')
    
    # 其他参数
    parser.add_argument('--timeout', type=int, default=30,
                       help='Timeout per test in seconds')
    parser.add_argument('--tool-success-rate', type=float, default=0.8,
                       help='Tool success rate (0.0-1.0), default 0.8')
    parser.add_argument('--task-types', nargs='+', default=['all'],
                       help='Task types to test (default: all). Use "all" for all types')
    parser.add_argument('--prompt-types', nargs='+', default=['all'],
                       help='Prompt types to test (default: all). Options: baseline, optimal, cot, flawed, flawed_<type>, all')
    parser.add_argument('--clear', action='store_true',
                       help='Clear previous cumulative records before running')
    parser.add_argument('--save-logs', action='store_true',
                       help='Save detailed interaction logs for each test')
    parser.add_argument('--ai-classification', action='store_true',
                       help='Enable AI-powered error classification using gpt-5-nano')
    
    args = parser.parse_args()
    
    # 创建运行器
    runner = BatchTestRunner(
        debug=args.debug, 
        silent=args.silent, 
        save_logs=args.save_logs,
        use_ai_classification=args.ai_classification
    )
    
    # 如果需要清除之前的记录
    if args.clear:
        # 确保manager被初始化
        runner._lazy_init()
        if runner.manager:
            runner.manager.clear_database()
    
    # 如果只是查看进度
    if args.progress:
        runner.show_progress(args.model, detailed=args.detailed)
        return
    
    # 准备测试任务 - 统一使用get_smart_tasks
    tasks = runner.get_smart_tasks(
        model=args.model, 
        count=args.count, 
        difficulty=args.difficulty, 
        tool_success_rate=args.tool_success_rate,
        selected_prompt_types=args.prompt_types,
        selected_task_types=args.task_types
    )
    
    # 运行测试
    print(f"Starting batch test: {len(tasks)} tests")
    print(f"Model: {args.model}")
    print(f"Difficulty: {args.difficulty}")
    
    if args.adaptive:
        # 使用自适应限流
        results = runner.run_adaptive_concurrent_batch(
            tasks,
            initial_workers=min(3, args.workers),  # 保守的初始值
            initial_qps=min(5.0, args.qps)
        )
    elif args.concurrent:
        # 使用固定并发
        results = runner.run_concurrent_batch(tasks, workers=args.workers, qps=args.qps)
    else:
        # 串行执行
        results = []
        for i, task in enumerate(tasks):
            if not args.silent:
                print(f"Running test {i+1}/{len(tasks)}...")
            result = runner.run_single_test(
                model=task.model,
                task_type=task.task_type,
                difficulty=task.difficulty,
                prompt_type=task.prompt_type,
                is_flawed=task.is_flawed,
                flaw_type=task.flaw_type,
                timeout=task.timeout,
                tool_success_rate=task.tool_success_rate
            )
            results.append(result)
            
            # 始终获取log_data用于AI分类（无论是否启用save_logs）
            log_data = None
            if result:
                # 从result中获取log_data（总是存在）
                log_data = result.pop('_log_data', None)
                if args.debug and log_data:
                    print(f"[DEBUG] Got log_data for {task.task_type}_{task.prompt_type}")
            
            # 生成TXT内容用于AI分类（不写文件）
            ai_error_category = None
            ai_error_reason = None
            ai_confidence = 0.0
            
            if result and log_data:
                # 如果有错误，生成TXT内容并进行AI分类
                if not result.get('success', False):
                    # 生成TXT格式内容（在内存中）
                    txt_content = runner._generate_txt_log_content(task, result, log_data)
                    
                    # 使用TXT内容进行AI分类
                    ai_error_category, ai_error_reason, ai_confidence = runner._ai_classify_with_txt_content(task, result, txt_content)
                    if ai_error_category and args.debug:
                        print(f"[DEBUG] AI classification: {ai_error_category} (confidence: {ai_confidence:.2f})")
                
                # 如果需要保存日志文件
                if runner.save_logs:
                    txt_file_path = runner._save_interaction_log(task, result, log_data)
                    if args.debug and txt_file_path:
                        print(f"[DEBUG] Saved interaction log to {txt_file_path.name}")
            
            # 保存到累积数据库
            record = TestRecord(
                model=task.model,
                task_type=task.task_type,
                prompt_type=task.prompt_type,
                difficulty=task.difficulty,
                success=result.get('success', False),
                execution_time=result.get('execution_time', 0),
                error_message=result.get('error'),
                is_flawed=task.is_flawed,
                flaw_type=task.flaw_type,
                timestamp=datetime.now().isoformat()
            )
            # 添加额外的度量（如果可用）
            record.turns = result.get('turns', 0)
            record.tool_calls = result.get('tool_calls', [])
            record.tool_reliability = task.tool_success_rate  # 记录工具成功率
            record.required_tools = result.get('required_tools', [])
            record.executed_tools = result.get('executed_tools', [])
            # 设置部分成功标志
            if result.get('success_level') == 'partial_success':
                record.partial_success = True
            # 设置成功级别 - 使用execution_status以与cumulative_test_manager保持一致
            record.execution_status = result.get('success_level', 'failure')
            record.success_level = result.get('success_level', 'failure')  # 保留以便向后兼容
            # 添加分数指标
            record.workflow_score = result.get('workflow_score')
            record.phase2_score = result.get('phase2_score')
            record.quality_score = result.get('quality_score')
            record.final_score = result.get('final_score')
            
            # 添加重要的缺失字段
            record.format_error_count = result.get('format_error_count', 0)
            record.api_issues = result.get('api_issues', [])
            record.executed_tools = result.get('executed_tools', [])
            record.required_tools = task.required_tools if hasattr(task, 'required_tools') else []
            
            # 在单独测试中，AI分类会在这里处理（如果启用了save_logs和AI分类）
            # 注意：这是同步测试路径，需要从log_data中获取AI分类结果
            
            runner.manager.add_test_result_with_classification(record)
    
    # 完成错误统计
    if isinstance(runner.manager, EnhancedCumulativeManager):
        runner.manager.finalize()
    
    # 显示结果
    success_count = sum(1 for r in results if r.get('success', False))
    print(f"\n{'='*60}")
    print(f"Test Complete!")
    print(f"Total: {len(results)}")
    print(f"Success: {success_count} ({success_count/len(results)*100:.1f}%)")
    print(f"Failed: {len(results) - success_count}")
    print(f"{'='*60}")
    
    # 显示统计结果保存位置
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if db_path.exists():
        print(f"\n📊 统计结果已保存到:")
        print(f"   {db_path.absolute()}")
        print(f"   文件大小: {db_path.stat().st_size / 1024:.1f} KB")
        print(f"\n💡 查看统计报告:")
        print(f"   python view_test_statistics.py --model {args.model}")
    
    # 显示最终进度
    if not args.silent:
        runner.show_progress(args.model, detailed=False)


if __name__ == "__main__":
    main()