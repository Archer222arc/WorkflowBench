#!/usr/bin/env python3
"""
Main entry point for the MDP Workflow System with Phase 3 Task-Aware Support
Provides CLI interface for all system functionalities
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import json
import argparse
import torch
import numpy as np
from typing import Optional, Dict, List, Any

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 创建文件处理器
log_filename = f"logs/debug_main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

# 创建格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(file_handler)


class MDPWorkflowSystem:
    """Main system controller with Phase 3 enhancements"""
    
    def __init__(self):
        self.base_dir = Path(".")
        self.setup_directories()
    
    def setup_directories(self):
        """Create necessary directories"""
        directories = [
            "mcp_generated_library",
            "checkpoints",
            "logs",
            "analysis"
        ]
        for dir_name in directories:
            (self.base_dir / dir_name).mkdir(exist_ok=True)
    
    def check_environment(self) -> bool:
        """Check if environment is properly set up"""
        required_files = [
            "mcp_generated_library/tool_registry.json",
            "mcp_generated_library/task_library.json"
        ]
        
        required_modules = [
            "generalized_mdp_framework.py",
            "unified_training_manager.py", 
            "mdp_workflow_generator.py",
            "tool_and_task_generator.py"
        ]
        
        all_present = True
        
        # Check data files
        for file_path in required_files:
            if not (self.base_dir / file_path).exists():
                logger.warning(f"Missing data file: {file_path}")
                all_present = False
        
        # Check Python modules
        for module in required_modules:
            if not (self.base_dir / module).exists():
                logger.warning(f"Missing module: {module}")
                all_present = False
        
        return all_present
    
    def setup_data(self):
        """Generate tools and tasks if not present"""
        logger.info("Setting up training data...")
        
        tool_registry_path = self.base_dir / "mcp_generated_library/tool_registry.json"
        task_library_path = self.base_dir / "mcp_generated_library/task_library.json"
        
        # Check if data already exists
        if tool_registry_path.exists() and task_library_path.exists():
            logger.info("Data files already exist.")
            response = input("Regenerate data? (y/n): ").lower()
            if response != 'y':
                logger.info("Using existing data.")
                return
        
        try:
            # Import generator
            from tool_and_task_generator import create_diverse_tool_library, generate_multi_tool_tasks
            
            # Generate tools
            logger.info("Generating diverse tool library...")
            tools = create_diverse_tool_library(num_tools=50)
            
            # Generate tasks
            logger.info("Generating multi-tool tasks...")
            tasks = generate_multi_tool_tasks(tools, num_tasks=200)
            
            # Save to files
            logger.info("Saving generated data...")
            
            # Save tools - using correct method name
            tool_registry = {}
            for tool in tools:
                tool_registry[tool.name] = tool.to_mcp_json()
            
            with open(tool_registry_path, 'w') as f:
                json.dump(tool_registry, f, indent=2)
            
            # Save tasks
            task_data = []
            for task in tasks:
                task_dict = {
                    "id": task.instance_id,
                    "task_type": task.task_type,
                    "complexity": task.complexity,
                    "description": task.description,
                    "test_input": task.inputs,
                    "expected_output": task.expected_outputs,
                    "required_tools": task.required_tools,
                    "metadata": task.metadata
                }
                task_data.append(task_dict)
            
            task_library_data = {
                "tasks": task_data,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "num_tasks": len(tasks)
                }
            }
            with open(task_library_path, 'w') as f:
                json.dump(task_library_data, f, indent=2)
            
            # Generate summary
            summary = self._generate_data_summary(tools, tasks)
            summary_path = self.base_dir / "mcp_generated_library/generation_summary.json"
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"✅ Data generation complete!")
            logger.info(f"   Tools: {len(tools)}")
            logger.info(f"   Tasks: {len(tasks)}")
            
        except Exception as e:
            logger.error(f"Data generation failed: {e}")
            raise

    def analyze_task_library(self, library_path: Optional[str] = None):
        """分析任务库中的任务类型分布"""
        task_path = Path(library_path or "mcp_generated_library/task_library_enhanced.json")
        
        if not task_path.exists():
            logger.error(f"Task library not found: {task_path}")
            return {}
        
        logger.info(f"Analyzing task library: {task_path}")
        
        with open(task_path, 'r') as f:
            data = json.load(f)
        
        # 统计任务类型
        type_counts = {}
        complexity_counts = {}
        tasks = data if isinstance(data, list) else data.get('tasks', list(data.values()))
        
        for task in tasks:
            if isinstance(task, dict):
                # 统计任务类型
                task_type = task.get('task_type', 'unknown')
                type_counts[task_type] = type_counts.get(task_type, 0) + 1
                
                # 统计复杂度
                complexity = task.get('complexity', 'unknown')
                complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        
        # 显示结果
        logger.info("\n任务库分析结果:")
        logger.info(f"总任务数: {len(tasks)}")
        
        logger.info("\n按任务类型:")
        for task_type, count in sorted(type_counts.items()):
            logger.info(f"  {task_type}: {count} 个任务")
        
        logger.info("\n按复杂度:")
        for complexity, count in sorted(complexity_counts.items()):
            logger.info(f"  {complexity}: {count} 个任务")
        
        return {'type_counts': type_counts, 'complexity_counts': complexity_counts, 'total': len(tasks)}

    def train_specific_tasks(self, task_types: List[str], episodes: int = 1000, 
                            algorithm: str = 'dqn', use_task_aware: bool = True,
                            resume: bool = False):
        """训练特定任务类型"""
        logger.info("="*70)
        logger.info(f"训练特定任务类型: {task_types}")
        logger.info("="*70)
        
        # 首先分析任务库
        analysis = self.analyze_task_library()
        
        # 检查请求的任务类型是否存在
        missing_types = []
        for task_type in task_types:
            if task_type not in analysis['type_counts']:
                missing_types.append(task_type)
        
        if missing_types:
            logger.error(f"任务库中不存在以下任务类型: {missing_types}")
            logger.info(f"可用的任务类型: {list(analysis['type_counts'].keys())}")
            return False
        
        # 显示即将训练的任务数量
        logger.info("\n即将训练的任务:")
        total_tasks = 0
        for task_type in task_types:
            count = analysis['type_counts'][task_type]
            logger.info(f"  {task_type}: {count} 个任务")
            total_tasks += count
        logger.info(f"总计: {total_tasks} 个任务")
        
        # 调用train方法，传入task_types参数
        logger.info(f"\n开始训练 ({episodes} episodes)...")
        self.train(
            mode='dqn',  # 保持兼容性
            episodes=episodes,
            resume=resume,
            use_task_aware=use_task_aware,
            algorithm=algorithm,
            task_types=task_types  # 传递任务类型
        )
        
        return True


    def train(self, mode: str = 'dqn', episodes: int = 1000, resume: bool = False, 
            budget: float = 50.0, use_task_aware: bool = True,
            algorithm: str = 'dqn', task_types: Optional[List[str]] = None):  # <- 修改了这一行：添加task_types参数
        """Train the model with specified algorithm"""
        logger.info(f"Starting {algorithm.upper()} training...")
        logger.info(f"Task-aware state: {'ENABLED' if use_task_aware else 'DISABLED'}")
        if task_types:  # <- 新增了这部分
            logger.info(f"Training on specific task types: {task_types}")  # <- 新增了这一行
        
        try:
            from unified_training_manager import UnifiedTrainingManager
            
            # Create manager with selected algorithm
            manager = UnifiedTrainingManager(
                use_task_aware_state=use_task_aware,
                algorithm=algorithm,
                task_types=task_types  # <- 修改了这一行：传递task_types
            )
            
            # Setup environment
            if not manager.setup_environment():
                logger.error("Failed to setup training environment!")
                return
            
            # Train
            success = manager.train(num_episodes=episodes, resume=resume)
            
            if success:
                logger.info("✅ Training completed successfully!")
                manager.analyze_model()
            else:
                logger.error("❌ Training failed!")
                
        except Exception as e:
            logger.error(f"Training error: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_workflows(self, task_type: Optional[str] = None, use_task_aware: bool = True):
        """Generate workflows using trained model with Phase 3 support"""
        logger.info("Generating workflows...")
        logger.info(f"Task-aware features: {'ENABLED' if use_task_aware else 'DISABLED'}")
        
        try:
            from mdp_workflow_generator import MDPWorkflowGenerator
            
            # Find best model
            checkpoint_dir = self.base_dir / "checkpoints"
            model_path = checkpoint_dir / "final_model.pt"
            
            if not model_path.exists():
                # Try to find latest checkpoint
                checkpoints = list(checkpoint_dir.glob("checkpoint_*.pt"))
                if checkpoints:
                    model_path = max(checkpoints, key=lambda p: p.stat().st_mtime)
                else:
                    logger.error("No trained model found!")
                    return
            
            logger.info(f"Using model: {model_path}")
            
            # Create generator
            generator = MDPWorkflowGenerator(
                model_path=str(model_path),
                tools_path="mcp_generated_library/tool_registry.json",
                use_task_aware_state=use_task_aware
            )
            
            # Generate workflows
            if task_type:
                workflows = generator.generate_workflows_for_task_type(task_type)
                logger.info(f"Generated workflow for {task_type}")
            else:
                # Generate for all task types
                task_types = generator.get_available_task_types()
                workflows = {}
                for t_type in task_types:
                    workflows[t_type] = generator.generate_workflows_for_task_type(t_type)
                logger.info(f"Generated workflows for {len(workflows)} task types")
            
            # Save workflows
            output_path = self.base_dir / "generated_workflows.json"
            with open(output_path, 'w') as f:
                json.dump(workflows, f, indent=2)
            
            logger.info(f"✅ Workflows saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Workflow generation failed: {e}")
            import traceback
            traceback.print_exc()
    
    def analyze_training(self):
        """Analyze training results with Phase 3 metrics"""
        logger.info("Analyzing training results...")
        
        try:
            from unified_training_manager import UnifiedTrainingManager
            
            manager = UnifiedTrainingManager()
            
            # Load latest model
            checkpoint_dir = self.base_dir / "checkpoints"
            model_path = checkpoint_dir / "final_model.pt"
            
            if not model_path.exists():
                checkpoints = list(checkpoint_dir.glob("checkpoint_*.pt"))
                if checkpoints:
                    model_path = max(checkpoints, key=lambda p: p.stat().st_mtime)
                else:
                    logger.error("No model found to analyze!")
                    return
            
            # Load checkpoint
            checkpoint = torch.load(model_path, map_location='cpu')
            metrics = checkpoint.get('metrics', {})
            
            logger.info("\n" + "="*60)
            logger.info("Training Analysis Report")
            logger.info("="*60)
            
            # Basic metrics
            logger.info(f"\nModel: {model_path.name}")
            logger.info(f"Episodes trained: {checkpoint.get('episode', 'unknown')}")
            
            # Performance metrics
            if 'best_success_rate' in metrics:
                logger.info(f"\nPerformance:")
                logger.info(f"  Best success rate: {metrics['best_success_rate']:.2%}")
                logger.info(f"  Best avg reward: {metrics.get('best_avg_reward', 0):.2f}")
            
            # Task breakdown
            task_success = metrics.get('task_success_counts', {})
            task_attempts = metrics.get('task_attempt_counts', {})
            
            if task_attempts:
                logger.info(f"\nTask Performance:")
                for task_type in sorted(task_attempts.keys()):
                    attempts = task_attempts[task_type]
                    successes = task_success.get(task_type, 0)
                    rate = successes / attempts if attempts > 0 else 0
                    logger.info(f"  {task_type}: {rate:.2%} ({successes}/{attempts})")
            
            # Phase 3: Complexity analysis
            complexity_rates = metrics.get('complexity_success_rates', {})
            if complexity_rates:
                logger.info("\nSuccess Rate by Complexity:")
                for complexity in ['simple', 'moderate', 'complex', 'very_complex']:
                    if complexity in complexity_rates and complexity_rates[complexity]:
                        rate = np.mean(complexity_rates[complexity])
                        logger.info(f"  {complexity}: {rate:.2%}")
            
            # Phase 3: Semantic milestones
            milestone_counts = metrics.get('semantic_milestone_counts', [])
            if milestone_counts:
                avg_milestones = np.mean(milestone_counts)
                max_milestones = max(milestone_counts) if milestone_counts else 0
                logger.info(f"\nSemantic Progress:")
                logger.info(f"  Avg milestones per episode: {avg_milestones:.1f}")
                logger.info(f"  Max milestones achieved: {max_milestones}")
            
            # Training efficiency
            if 'training_time' in metrics:
                time_hours = metrics['training_time'] / 3600
                episodes = checkpoint.get('episode', 1)
                logger.info(f"\nTraining Efficiency:")
                logger.info(f"  Total time: {time_hours:.2f} hours")
                logger.info(f"  Time per episode: {metrics['training_time']/episodes:.1f} seconds")
            
            # Generate plots if possible
            try:
                self._generate_analysis_plots(metrics)
                logger.info("\n✅ Analysis plots saved to analysis/")
            except Exception as e:
                logger.warning(f"Could not generate plots: {e}")
            
            logger.info("\n" + "="*60)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            import traceback
            traceback.print_exc()
    
    def demo(self):
        """Run interactive demo with Phase 3 features"""
        logger.info("Starting interactive demo...")
        
        print("[DEBUG] Importing required modules for demo...")
        from unified_training_manager import UnifiedTrainingManager
        from mdp_workflow_generator import MDPWorkflowGenerator
        
        # Setup manager
        print("[DEBUG] Creating UnifiedTrainingManager...")
        manager = UnifiedTrainingManager(use_task_aware_state=True)
        if not manager.setup_environment():
            logger.error("Failed to setup environment!")
            return
        
        # Find model
        checkpoint_dir = self.base_dir / "checkpoints"
        model_path = checkpoint_dir / "final_model.pt"
        
        if not model_path.exists():
            logger.error("No trained model found! Train a model first.")
            return
        
        # Load model
        logger.debug(f" Loading model from {model_path}")
        manager.trainer.load_checkpoint(str(model_path))
        
        logger.info("\n" + "="*50)
        logger.info("MDP Workflow System Demo")
        logger.info("="*50)
        
        while True:
            # Get available task types
            task_types = list(set(t.task_type for t in manager.env.task_manager.tasks))
            
            logger.info("\nAvailable task types:")
            for i, t_type in enumerate(task_types):
                logger.info(f"  {i+1}. {t_type}")
            logger.info("  0. Exit")
            
            # Get user choice
            choice_str = input("\nSelect task type (number): ")
            
            if not choice_str.strip():
                continue
                
            choice = int(choice_str)
            
            if choice == 0:
                break
            
            if 1 <= choice <= len(task_types):
                selected_type = task_types[choice - 1]
                logger.info(f"\nGenerating workflow for: {selected_type}")
                
                # Get a task of this type
                task = manager.env.task_manager.get_task(task_type=selected_type)
                if not task:
                    logger.error(f"No task found for type: {selected_type}")
                    continue
                
                # Reset environment with this task
                state = manager.env.reset(task=task)
                
                logger.info(f"\nTask: {task.description}")
                logger.info(f"Required tools: {task.required_tools}")
                logger.info(f"\nExecuting workflow...")
                
                # Execute workflow
                done = False
                step = 0
                
                while not done:
                    # Get action
                    state_vector = manager.env.get_state_vector()
                    action = manager.trainer.select_action(state_vector, deterministic=True)
                    
                    # Show action
                    action_type, tool_name = manager.env._decode_action(action)
                    if action_type == ActionType.INVOKE_TOOL and tool_name:
                        logger.info(f"\nStep {step + 1}: Execute {tool_name}")
                    else:
                        logger.info(f"\nStep {step + 1}: {action_type.value}")
                    
                    next_state, reward, done, info = manager.env.step(action)
                    
                    # Show progress
                    logger.info(f"  Progress: {info['progress']:.1%}")
                    logger.info(f"  Reward: {reward:.2f}")
                    
                    # Show semantic milestones if available
                    if 'semantic_milestones' in info and info['semantic_milestones'] > 0:
                        logger.info(f"  Milestones achieved: {info['semantic_milestones']}")
                    
                    state = next_state
                    step += 1
                    
                    if done:
                        break
                    
                    if step > 30:
                        logger.info("\nWorkflow too long, stopping...")
                        break
                
                # Show results
                logger.info(f"\n{'='*50}")
                logger.info(f"Workflow completed!")
                logger.info(f"Success: {info['success']}")
                logger.info(f"Final progress: {info['progress']:.1%}")
                logger.info(f"Total steps: {step}")
                
                # Show achieved milestones
                if hasattr(manager.env.current_state, 'semantic_milestones'):
                    milestones = manager.env.current_state.semantic_milestones
                    if milestones:
                        logger.info(f"\nAchieved milestones:")
                        for milestone in milestones:
                            logger.info(f"  - {milestone}")
            else:
                logger.warning("Invalid choice!")
        
        logger.info("\nDemo completed!")
        def clean_checkpoints(self):
            """Clean up old checkpoints"""
            logger.info("Cleaning checkpoints...")
            
            checkpoint_dir = self.base_dir / "checkpoints"
            checkpoints = list(checkpoint_dir.glob("checkpoint_*.pt"))
            
            if not checkpoints:
                logger.info("No checkpoints to clean.")
                return
            
            # Sort by modification time
            checkpoints.sort(key=lambda p: p.stat().st_mtime)
            
            logger.info(f"Found {len(checkpoints)} checkpoints")
            keep = 5  # Keep last 5
            
            if len(checkpoints) > keep:
                to_remove = checkpoints[:-keep]
                
                for checkpoint in to_remove:
                    logger.info(f"Removing {checkpoint.name}...")
                    checkpoint.unlink()
                
                logger.info(f"✅ Removed {len(to_remove)} old checkpoints")
            else:
                logger.info("Not enough checkpoints to clean.")
        
        def diagnose(self):
            """Run diagnostics on the system"""
            logger.info("Running system diagnostics...")
            
            try:
                # Import and run diagnostics
                from diagnose_training import main as diagnose_main
                diagnose_main()
            except ImportError:
                logger.error("Diagnostics module not found!")
            except Exception as e:
                logger.error(f"Diagnostics failed: {e}")
        
        def _generate_data_summary(self, tools: List[Any], tasks: List[Any]) -> Dict[str, Any]:
            """Generate summary of generated data"""
            # Tool analysis
            tool_categories = {}
            for tool in tools:
                category = tool.category if hasattr(tool, 'category') else 'general'
                if category not in tool_categories:
                    tool_categories[category] = []
                tool_categories[category].append(tool.name)
            
            # Task analysis
            task_types = {}
            task_complexities = {"easy": 0, "medium": 0, "hard": 0}
            tool_usage = {}
            
            for task in tasks:
                # Task types
                if task.task_type not in task_types:
                    task_types[task.task_type] = 0
                task_types[task.task_type] += 1
                
                # Complexity
                task_complexities[task.complexity] += 1
                
                # Tool usage
                for tool in task.required_tools:
                    if tool not in tool_usage:
                        tool_usage[tool] = 0
                    tool_usage[tool] += 1
            
            return {
                "generated_at": datetime.now().isoformat(),
                "tools": {
                    "total": len(tools),
                    "by_category": {k: len(v) for k, v in tool_categories.items()},
                    "categories": tool_categories
                },
                "tasks": {
                    "total": len(tasks),
                    "by_type": task_types,
                    "by_complexity": task_complexities,
                    "tool_usage": dict(sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:10])
                }
            }
        
        def _generate_analysis_plots(self, metrics: Dict[str, Any]):
            """Generate analysis plots"""
            try:
                import matplotlib.pyplot as plt
                import seaborn as sns
                
                # Set style
                plt.style.use('seaborn-v0_8-darkgrid')
                analysis_dir = self.base_dir / "analysis"
                
                # Plot 1: Success rate over episodes
                if 'episode_success' in metrics:
                    plt.figure(figsize=(10, 6))
                    success_rates = metrics['episode_success']
                    window = min(50, len(success_rates) // 10)
                    
                    # Calculate moving average
                    moving_avg = []
                    for i in range(len(success_rates)):
                        start = max(0, i - window)
                        moving_avg.append(np.mean(success_rates[start:i+1]))
                    
                    plt.plot(success_rates, alpha=0.3, label='Episode success')
                    plt.plot(moving_avg, label=f'Moving avg ({window} ep)')
                    plt.xlabel('Episode')
                    plt.ylabel('Success Rate')
                    plt.title('Training Progress: Success Rate')
                    plt.legend()
                    plt.savefig(analysis_dir / 'success_rate.png')
                    plt.close()
                
                # Plot 2: Task performance breakdown
                task_success = metrics.get('task_success_counts', {})
                task_attempts = metrics.get('task_attempt_counts', {})
                
                if task_attempts:
                    plt.figure(figsize=(12, 6))
                    task_types = sorted(task_attempts.keys())
                    success_rates = []
                    
                    for task_type in task_types:
                        attempts = task_attempts[task_type]
                        successes = task_success.get(task_type, 0)
                        rate = successes / attempts if attempts > 0 else 0
                        success_rates.append(rate)
                    
                    plt.bar(task_types, success_rates)
                    plt.xlabel('Task Type')
                    plt.ylabel('Success Rate')
                    plt.title('Performance by Task Type')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    plt.savefig(analysis_dir / 'task_performance.png')
                    plt.close()
                
                # Plot 3: Complexity analysis (Phase 3)
                complexity_rates = metrics.get('complexity_success_rates', {})
                if complexity_rates:
                    plt.figure(figsize=(10, 6))
                    complexities = ['simple', 'moderate', 'complex', 'very_complex']
                    rates = []
                    errors = []
                    
                    for complexity in complexities:
                        if complexity in complexity_rates and complexity_rates[complexity]:
                            rate_list = complexity_rates[complexity]
                            rates.append(np.mean(rate_list))
                            errors.append(np.std(rate_list))
                        else:
                            rates.append(0)
                            errors.append(0)
                    
                    plt.bar(complexities, rates, yerr=errors, capsize=5)
                    plt.xlabel('Task Complexity')
                    plt.ylabel('Success Rate')
                    plt.title('Performance by Task Complexity')
                    plt.savefig(analysis_dir / 'complexity_performance.png')
                    plt.close()
                
                # Plot 4: Semantic milestones (Phase 3)
                milestone_counts = metrics.get('semantic_milestone_counts', [])
                if milestone_counts:
                    plt.figure(figsize=(10, 6))
                    plt.plot(milestone_counts, alpha=0.5)
                    
                    # Moving average
                    window = min(20, len(milestone_counts) // 10)
                    moving_avg = []
                    for i in range(len(milestone_counts)):
                        start = max(0, i - window)
                        moving_avg.append(np.mean(milestone_counts[start:i+1]))
                    
                    plt.plot(moving_avg, label=f'Moving avg ({window} ep)')
                    plt.xlabel('Episode')
                    plt.ylabel('Semantic Milestones Achieved')
                    plt.title('Semantic Progress Over Training')
                    plt.legend()
                    plt.savefig(analysis_dir / 'semantic_progress.png')
                    plt.close()
                
            except ImportError:
                logger.warning("Matplotlib not available for plotting")
            except Exception as e:
                logger.warning(f"Plot generation failed: {e}")



    def generate_tasks_parallel(self, 
                            num_tasks: int = 500,
                            task_distribution: Dict[str, float] = None,
                            use_llm: bool = True,
                            max_workers: int = None):
        """使用现有工具库并行生成任务"""
        logger.info("Starting parallel task generation...")
        
        tool_registry_path = self.base_dir / "mcp_generated_library/tool_registry_consolidated.json"
        
        # 检查工具库是否存在
        if not tool_registry_path.exists():
            logger.error(f"Tool registry not found at {tool_registry_path}")
            logger.info("Please ensure tool_registry_consolidated.json exists")
            return
        
        from tool_and_task_generator import parallel_generate_tasks_from_existing_tools
        
        logger.info(f"Generating {num_tasks} tasks in parallel...")
        
        # 执行并行生成
        results = parallel_generate_tasks_from_existing_tools(
            tool_registry_path=str(tool_registry_path),
            num_tasks=num_tasks,
            task_distribution=task_distribution,
            max_workers=max_workers,
            use_llm=use_llm,
            output_dir="mcp_generated_library",
            show_progress=True
        )
        
        logger.info(f"✅ Successfully generated {len(results['tasks'])} tasks")
        logger.info(f"📁 Task library saved to: {results['task_file']}")
        logger.info(f"📊 Report saved to: {results['report_file']}")
        
        # 打印摘要
        summary = results['summary']
        logger.info(f"\n📈 Generation Summary:")
        logger.info(f"  Total time: {summary['total_time']:.2f} seconds")
        logger.info(f"  Speed: {summary['tasks_per_second']:.2f} tasks/second")
        logger.info(f"  Parallel speedup: {summary['parallel_speedup']:.2f}x")
            


def main():
    """Main entry point with Phase 3 support"""
    parser = argparse.ArgumentParser(
        description="MDP Workflow System with Task-Aware Features",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup training data')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Train the model')
    train_parser.add_argument('--mode', choices=['dqn', 'llm', 'integrated'], 
                             default='dqn', help='Training mode')
    train_parser.add_argument('--algorithm', choices=['dqn', 'ppo'],  # <- 新增了这一行
                         default='dqn', help='Training algorithm')  # <- 新增了这一行
    train_parser.add_argument('--episodes', type=int, default=1000, 
                             help='Number of training episodes')
    train_parser.add_argument('--resume', action='store_true', 
                             help='Resume from checkpoint')
    train_parser.add_argument('--budget', type=float, default=50.0, 
                             help='LLM budget in dollars')
    train_parser.add_argument('--use-task-aware', action='store_true', default=True,
                             help='Use task-aware state representation (Phase 3)')
    train_parser.add_argument('--no-task-aware', dest='use_task_aware', action='store_false',
                             help='Disable task-aware state representation')
    train_parser.add_argument('--task-library', type=str,  # <- 新增这一行
                         default='mcp_generated_library/task_library_enhanced.json',  # <- 新增这一行
                         help='Path to task library file')  # <- 新增这一行
    train_parser.add_argument('--task-types', nargs='+',  # <- 新增了这一行
                         help='Specific task types to train on')  # <- 新增了这一行
    # 添加新的子命令
    train_specific_parser = subparsers.add_parser('train-specific',  # <- 新增了整个子命令
                                                help='Train on specific task types')  # <- 新增了这一行
    train_specific_parser.add_argument('task_types', nargs='+',  # <- 新增了这一行
                                    help='Task types to train on')  # <- 新增了这一行
    train_specific_parser.add_argument('--episodes', type=int, default=1000,  # <- 新增了这一行
                                    help='Number of training episodes')  # <- 新增了这一行
    train_specific_parser.add_argument('--algorithm', choices=['dqn', 'ppo'],  # <- 新增了这一行
                                    default='dqn', help='Training algorithm')  # <- 新增了这一行
    train_specific_parser.add_argument('--resume', action='store_true',  # <- 新增了这一行
                                    help='Resume from checkpoint')  # <- 新增了这一行

    # 添加analyze-tasks命令
    analyze_tasks_parser = subparsers.add_parser('analyze-tasks',  # <- 新增了整个子命令
                                            help='Analyze task library')  # <- 新增了这一行
    analyze_tasks_parser.add_argument('--library', type=str,  # <- 新增了这一行
                                    default='mcp_generated_library/task_library_enhanced.json',  # <- 新增了这一行
                                    help='Path to task library')  # <- 新增了这一行
                                    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate workflows')
    gen_parser.add_argument('--task-type', type=str, help='Specific task type')
    gen_parser.add_argument('--use-task-aware', action='store_true', default=True,
                           help='Use task-aware features for generation')
    gen_parser.add_argument('--no-task-aware', dest='use_task_aware', action='store_false',
                           help='Disable task-aware features')
    
    generate_tasks_parser = subparsers.add_parser(
    'generate-tasks', 
    help='Generate tasks using existing tool registry'
    )
    generate_tasks_parser.add_argument(
        '--num-tasks', 
        type=int, 
        default=500,
        help='Number of tasks to generate (default: 500)'
    )
    generate_tasks_parser.add_argument(
        '--max-workers',
        type=int,
        default=None,
        help='Maximum parallel workers (default: CPU count)'
    )
    generate_tasks_parser.add_argument(
        '--no-llm',
        action='store_true',
        help='Disable LLM-enhanced generation'
    )
    generate_tasks_parser.add_argument(
        '--distribution',
        type=str,
        help='Task distribution as JSON string, e.g., \'{"basic_task": 0.3, "simple_task": 0.3, ...}\''
    )

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze training results')
    
    # Demo command
    demo_parser = subparsers.add_parser('demo', help='Run interactive demo')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean old checkpoints')
    
    # Diagnose command
    diagnose_parser = subparsers.add_parser('diagnose', help='Run system diagnostics')
    
    args = parser.parse_args()
    
    # Create system
    system = MDPWorkflowSystem()
    
    # Check environment first
    if args.command != 'setup' and not system.check_environment():
        logger.error("Environment not properly set up! Run 'python main.py setup' first.")
        return
    
    # Execute command
    if args.command == 'setup':
        system.setup_data()
    elif args.command == 'train':
        system.train(
            mode=args.mode,  # 保留兼容性
            episodes=args.episodes,
            resume=args.resume,
            budget=args.budget,
            use_task_aware=args.use_task_aware,
            algorithm=args.algorithm,
            task_types=getattr(args, 'task_types', None)  # <- 修改了这一行：传递task_types
        )
    elif args.command == 'train-specific':  # <- 新增了这个条件分支
        system.train_specific_tasks(  # <- 新增了这一行
            task_types=args.task_types,  # <- 新增了这一行
            episodes=args.episodes,  # <- 新增了这一行
            algorithm=args.algorithm,  # <- 新增了这一行
            resume=args.resume  # <- 新增了这一行
        )  # <- 新增了这一行
    elif args.command == 'analyze-tasks':  # <- 新增了这个条件分支
        system.analyze_task_library(args.library)  # <- 新增了这一行
    elif args.command == 'generate':
        system.generate_workflows(
            task_type=args.task_type,
            use_task_aware=args.use_task_aware
        )
    elif args.command == 'analyze':
        system.analyze_training()
    elif args.command == 'demo':
        system.demo()
    elif args.command == 'clean':
        system.clean_checkpoints()
    elif args.command == 'diagnose':
        system.diagnose()
    elif args.command == 'generate-tasks':
    # 解析任务分布
        task_distribution = None
        if args.distribution:
            try:
                task_distribution = json.loads(args.distribution)
            except json.JSONDecodeError:
                logger.error("Invalid JSON for task distribution")
                return
        
        system.generate_tasks_parallel(
            num_tasks=args.num_tasks,
            task_distribution=task_distribution,
            use_llm=not args.no_llm,
            max_workers=args.max_workers
        )
    else:
        parser.print_help()





if __name__ == "__main__":
    main()