#!/usr/bin/env python3
"""
Workflow预生成脚本 - 为所有任务库添加workflow字段
============================================
功能：
1. 读取所有难度级别的任务库文件
2. 为每个任务生成workflow（使用MDPWorkflowGenerator）
3. 将workflow保存到task_instance['workflow']字段
4. 输出增强版任务库文件

这样可以避免在并发测试时重复加载大型模型（250-350MB每个进程）
"""

import json
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
from enum import Enum

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from mdp_workflow_generator import MDPWorkflowGenerator


def make_json_serializable(obj: Any) -> Any:
    """
    递归转换对象为JSON可序列化格式
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, '__dict__'):
        # 自定义对象转换为字典
        return make_json_serializable(obj.__dict__)
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # 其他类型转换为字符串
        return str(obj)


class WorkflowAugmenter:
    """任务库workflow增强器"""
    
    def __init__(self, force_regenerate: bool = False, verbose: bool = True):
        """
        初始化augmenter
        
        Args:
            force_regenerate: 是否强制重新生成已有workflow的任务
            verbose: 是否显示详细输出
        """
        self.force_regenerate = force_regenerate
        self.verbose = verbose
        self.generator = None
        self.stats = {
            'total_tasks': 0,
            'workflows_generated': 0,
            'workflows_skipped': 0,
            'errors': 0
        }
        
    def initialize_generator(self):
        """初始化MDPWorkflowGenerator（只需一次）"""
        if self.verbose:
            print("\n" + "="*60)
            print("初始化MDPWorkflowGenerator...")
            print("="*60)
            
        start_time = time.time()
        
        # 设置日志级别以减少输出
        import logging
        logging.getLogger('mdp_workflow_generator').setLevel(logging.ERROR)
        logging.getLogger('mcp_embedding_manager').setLevel(logging.ERROR)
        logging.getLogger('unified_training_manager').setLevel(logging.ERROR)
        logging.getLogger('tool_capability_manager').setLevel(logging.ERROR)
        
        # 初始化generator - 这会加载大型模型
        self.generator = MDPWorkflowGenerator(
            model_path="checkpoints/best_model.pt",
            use_embeddings=True  # 使用FAISS嵌入搜索
        )
        
        elapsed = time.time() - start_time
        if self.verbose:
            print(f"✅ Generator初始化完成，耗时: {elapsed:.2f}秒")
            print(f"   - 加载了神经网络模型")
            print(f"   - 加载了FAISS索引")
            print(f"   - 准备就绪")
            
    def augment_task(self, task: Dict) -> Dict:
        """
        为单个任务添加workflow
        
        Args:
            task: 任务实例
            
        Returns:
            增强后的任务（包含workflow字段）
        """
        task_id = task.get('instance_id') or task.get('id', 'unknown')
        
        # 检查是否已有workflow
        if 'workflow' in task and not self.force_regenerate:
            if self.verbose:
                print(f"   ⏭️  跳过 {task_id} (已有workflow)")
            self.stats['workflows_skipped'] += 1
            return task
            
        try:
            # 生成workflow
            if self.verbose:
                print(f"   🔧 生成 {task_id}...", end='')
                
            workflow = self.generator.generate_workflow_for_instance(
                task_instance=task,
                max_depth=20
            )
            
            # 确保workflow是JSON可序列化的
            workflow = make_json_serializable(workflow)
            
            # 将workflow添加到任务
            task['workflow'] = workflow
            
            if self.verbose:
                sequence_len = len(workflow.get('optimal_sequence', []))
                print(f" ✅ (序列长度: {sequence_len})")
                
            self.stats['workflows_generated'] += 1
            
        except Exception as e:
            if self.verbose:
                print(f" ❌ 错误: {str(e)}")
            self.stats['errors'] += 1
            # 即使出错也返回原任务，避免数据丢失
            
        return task
        
    def augment_task_library(self, input_path: Path, output_path: Optional[Path] = None) -> bool:
        """
        增强整个任务库文件
        
        Args:
            input_path: 输入任务库路径
            output_path: 输出路径（默认为同目录下的_with_workflows版本）
            
        Returns:
            是否成功
        """
        if not input_path.exists():
            print(f"❌ 文件不存在: {input_path}")
            return False
            
        # 确定输出路径
        if output_path is None:
            # 在文件名中插入_with_workflows
            stem = input_path.stem  # 不含扩展名的文件名
            output_path = input_path.parent / f"{stem}_with_workflows.json"
            
        print(f"\n处理: {input_path.name}")
        print(f"输出到: {output_path.name}")
        
        # 读取任务库
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 处理不同的数据格式
        if isinstance(data, dict) and 'tasks' in data:
            tasks = data['tasks']
            is_wrapped = True
        elif isinstance(data, list):
            tasks = data
            is_wrapped = False
        else:
            print(f"❌ 未知的数据格式")
            return False
            
        print(f"   发现 {len(tasks)} 个任务")
        
        # 为每个任务生成workflow
        augmented_tasks = []
        for i, task in enumerate(tasks):
            if self.verbose and i % 10 == 0 and i > 0:
                print(f"   进度: {i}/{len(tasks)}")
                
            self.stats['total_tasks'] += 1
            augmented_task = self.augment_task(task)
            augmented_tasks.append(augmented_task)
            
        # 构建输出数据
        if is_wrapped:
            output_data = {
                'tasks': augmented_tasks,
                'metadata': {
                    'original_file': input_path.name,
                    'augmented_at': datetime.now().isoformat(),
                    'workflows_generated': self.stats['workflows_generated'],
                    'generator_version': '1.0'
                }
            }
        else:
            output_data = augmented_tasks
            
        # 保存增强后的任务库
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
            
        print(f"   ✅ 保存到: {output_path}")
        return True
        
    def process_all_libraries(self, directory: Path):
        """
        处理目录下的所有任务库文件
        
        Args:
            directory: 包含任务库的目录
        """
        # 查找所有任务库文件（不包含已经有workflow的版本）
        task_files = sorted([
            f for f in directory.glob("task_library_enhanced_v3_*.json")
            if "_with_workflows" not in f.name
        ])
        
        if not task_files:
            print(f"❌ 在 {directory} 中未找到任务库文件")
            return
            
        print(f"\n找到 {len(task_files)} 个任务库文件:")
        for f in task_files:
            print(f"  - {f.name}")
            
        # 初始化generator（只需一次）
        self.initialize_generator()
        
        # 处理每个文件
        print("\n" + "="*60)
        print("开始处理任务库")
        print("="*60)
        
        for task_file in task_files:
            success = self.augment_task_library(task_file)
            if not success:
                print(f"⚠️  处理 {task_file.name} 时出错")
                
        # 显示统计
        self.print_statistics()
        
    def print_statistics(self):
        """打印处理统计"""
        print("\n" + "="*60)
        print("处理完成 - 统计信息")
        print("="*60)
        print(f"总任务数: {self.stats['total_tasks']}")
        print(f"生成workflow: {self.stats['workflows_generated']}")
        print(f"跳过（已存在）: {self.stats['workflows_skipped']}")
        print(f"错误: {self.stats['errors']}")
        
        if self.stats['workflows_generated'] > 0:
            print(f"\n✅ 成功为 {self.stats['workflows_generated']} 个任务生成了workflow!")
            print("   这将显著减少并发测试时的内存使用（从8.75GB降到<2GB）")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='为任务库生成workflow，避免并发测试时重复加载大型模型'
    )
    
    parser.add_argument(
        '--directory', '-d',
        type=str,
        default='mcp_generated_library/difficulty_versions',
        help='任务库目录路径'
    )
    
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='处理单个文件（可选）'
    )
    
    parser.add_argument(
        '--force-regenerate',
        action='store_true',
        help='强制重新生成已有workflow的任务'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='减少输出信息'
    )
    
    args = parser.parse_args()
    
    # 创建augmenter
    augmenter = WorkflowAugmenter(
        force_regenerate=args.force_regenerate,
        verbose=not args.quiet
    )
    
    # 处理单个文件或整个目录
    if args.file:
        file_path = Path(args.file)
        if not augmenter.initialize_generator():
            augmenter.initialize_generator()
        success = augmenter.augment_task_library(file_path)
        if success:
            augmenter.print_statistics()
    else:
        directory = Path(args.directory)
        augmenter.process_all_libraries(directory)
        
    print("\n🎉 Workflow预生成完成！")
    print("   下次运行测试时将直接使用这些workflow，无需加载大型模型")


if __name__ == "__main__":
    main()