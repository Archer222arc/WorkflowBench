#!/usr/bin/env python3
"""
PILOT-Bench 快速启动脚本
========================
一键运行所有实验并生成报告
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
import json

# 导入核心模块
from experiment_manager import ExperimentManager
from result_analyzer import ResultAnalyzer
from api_client_manager import SUPPORTED_MODELS

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pilot_bench.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class PILOTBenchRunner:
    """PILOT-Bench 运行器"""
    
    def __init__(self, config_file: str = None):
        """初始化运行器"""
        self.config = self._load_config(config_file)
        self.start_time = None
        self.end_time = None
        
    def _load_config(self, config_file: str) -> dict:
        """加载配置"""
        default_config = {
            "model_path": "../phase23_checkpoints/final_phase23_model.pt",
            "tools_path": "mcp_generated_library/tool_registry.json",
            "output_dir": "pilot_bench_results",
            "experiments": {
                "overall_performance": {
                    "enabled": True,
                    "models": "all",  # 或指定模型列表
                    "num_tests": 10
                },
                "qwen_scale_analysis": {
                    "enabled": True,
                    "num_tests": 15
                },
                "robustness_test": {
                    "enabled": True,
                    "num_tests": 20
                },
                "prompt_sensitivity": {
                    "enabled": True,
                    "num_tests": 10
                },
                "error_analysis": {
                    "enabled": True,
                    "num_tests": 25
                }
            },
            "parallel_models": 3,
            "save_individual_results": True
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                # 合并配置
                default_config.update(user_config)
        
        return default_config
    
    def check_prerequisites(self) -> bool:
        """检查前置条件"""
        logger.info("Checking prerequisites...")
        
        # 检查模型文件
        if not Path(self.config['model_path']).exists():
            logger.error(f"Model file not found: {self.config['model_path']}")
            return False
        
        # 检查工具目录
        if not Path(self.config['tools_path']).exists():
            logger.error(f"Tools directory not found: {self.config['tools_path']}")
            return False
        
        # 检查API配置
        logger.info(f"Available models: {len(SUPPORTED_MODELS)}")
        if len(SUPPORTED_MODELS) < 5:
            logger.warning("Less than 5 models available. Results may be limited.")
        
        # 创建输出目录
        output_dir = Path(self.config['output_dir'])
        output_dir.mkdir(exist_ok=True)
        
        logger.info("Prerequisites check passed ✓")
        return True
    
    def run_experiments(self) -> dict:
        """运行所有启用的实验"""
        self.start_time = datetime.now()
        logger.info(f"Starting PILOT-Bench experiments at {self.start_time}")
        
        # 创建实验管理器
        manager = ExperimentManager(
            model_path=self.config['model_path'],
            tools_path=self.config['tools_path'],
            output_base_dir=self.config['output_dir']
        )
        
        results = {}
        enabled_experiments = [name for name, cfg in self.config['experiments'].items() 
                             if cfg.get('enabled', True)]
        
        logger.info(f"Enabled experiments: {', '.join(enabled_experiments)}")
        
        # 逐个运行实验
        for exp_name in enabled_experiments:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running experiment: {exp_name}")
            logger.info(f"{'='*60}")
            
            try:
                # 自定义实验配置
                if exp_name in manager.experiments:
                    exp_config = manager.experiments[exp_name]
                    
                    # 应用用户配置
                    user_exp_config = self.config['experiments'][exp_name]
                    if 'models' in user_exp_config:
                        if user_exp_config['models'] == 'all':
                            exp_config.models = SUPPORTED_MODELS
                        else:
                            exp_config.models = user_exp_config['models']
                    
                    if 'num_tests' in user_exp_config:
                        exp_config.num_tests = user_exp_config['num_tests']
                
                # 运行实验
                result = manager.run_experiment(exp_name)
                results[exp_name] = {
                    'status': 'completed',
                    'summary': result
                }
                logger.info(f"✓ {exp_name} completed successfully")
                
            except Exception as e:
                logger.error(f"✗ {exp_name} failed: {str(e)}")
                results[exp_name] = {
                    'status': 'failed',
                    'error': str(e)
                }
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        logger.info(f"\nAll experiments completed in {duration:.1f} seconds")
        
        # 保存会话信息
        session_info = {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': duration,
            'config': self.config,
            'results_summary': results,
            'session_dir': manager.session_dir.name
        }
        
        session_file = manager.session_dir / 'session_info.json'
        with open(session_file, 'w') as f:
            json.dump(session_info, f, indent=2)
        
        return {
            'session_dir': str(manager.session_dir),
            'results': results,
            'duration': duration
        }
    
    def analyze_results(self, session_dir: str) -> str:
        """分析实验结果"""
        logger.info(f"\nAnalyzing results from {session_dir}...")
        
        # 创建结果分析器
        analyzer = ResultAnalyzer(session_dir)
        
        # 生成综合报告
        report_path = analyzer.generate_comprehensive_report()
        
        # 生成实验计划填充版本
        self._fill_experiment_plan(analyzer, Path(session_dir))
        
        logger.info(f"Analysis complete. Report saved to: {report_path}")
        return str(report_path)
    
    def _fill_experiment_plan(self, analyzer: ResultAnalyzer, session_dir: Path):
        """填充实验计划表格"""
        output_file = session_dir / "综合实验评估计划_填充版.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # 复制原始计划的头部
            f.write("# PILOT-Bench 详细实验计划（结果填充版）\n\n")
            f.write(f"**实验完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 写入各个表格
            sections = [
                ("## 4.1 整体性能评估实验\n\n### 4.1.1 主要性能指标对比表\n\n", 
                 analyzer.generate_performance_table()),
                ("### 4.1.2 任务类型分解性能表\n\n", 
                 analyzer.generate_task_performance_table()),
                ("## 4.2 模型规模效应分析实验\n\n### 4.2.1 Qwen系列规模效应表\n\n", 
                 analyzer.generate_scale_effect_table()),
                ("## 4.3 Robustness评估实验\n\n### 4.3.1 缺陷工作流适应性表\n\n", 
                 analyzer.generate_robustness_table()),
                ("## 4.4 提示类型敏感性实验\n\n### 4.4.1 不同提示类型性能表\n\n", 
                 analyzer.generate_prompt_sensitivity_table()),
                ("## 4.5 错误模式深度分析实验\n\n### 4.5.1 系统性错误分类表\n\n", 
                 analyzer.generate_error_analysis_table())
            ]
            
            for title, df in sections:
                f.write(title)
                if not df.empty:
                    f.write(df.to_markdown(index=False))
                else:
                    f.write("*实验数据不可用*")
                f.write("\n\n")
        
        logger.info(f"Filled experiment plan saved to: {output_file}")
    
    def quick_test(self):
        """快速测试模式"""
        logger.info("Running quick test mode...")
        
        # 修改配置为快速测试
        self.config['experiments'] = {
            "overall_performance": {
                "enabled": True,
                "models": ["gpt-4o-mini", "DeepSeek-V3-671B", "qwen2.5-7b-instruct"],
                "num_tests": 2
            }
        }
        
        # 运行测试
        results = self.run_experiments()
        
        # 分析结果
        if results['results']['overall_performance']['status'] == 'completed':
            report_path = self.analyze_results(results['session_dir'])
            logger.info(f"\nQuick test completed! Report: {report_path}")
        else:
            logger.error("Quick test failed!")
    
    def run_full_benchmark(self):
        """运行完整基准测试"""
        logger.info("Starting full PILOT-Bench benchmark...")
        
        # 检查前置条件
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed. Exiting.")
            return
        
        # 运行实验
        results = self.run_experiments()
        
        # 分析结果
        report_path = self.analyze_results(results['session_dir'])
        
        # 打印总结
        print("\n" + "="*60)
        print("PILOT-Bench Benchmark Complete!")
        print("="*60)
        print(f"Duration: {results['duration']:.1f} seconds")
        print(f"Session Directory: {results['session_dir']}")
        print(f"Analysis Report: {report_path}")
        print("\nExperiment Status:")
        for exp_name, result in results['results'].items():
            status_icon = "✓" if result['status'] == 'completed' else "✗"
            print(f"  {status_icon} {exp_name}: {result['status']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='PILOT-Bench: Comprehensive AI Model Workflow Testing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full benchmark
  python run_pilot_bench.py --full
  
  # Quick test with 3 models
  python run_pilot_bench.py --quick
  
  # Run specific experiments
  python run_pilot_bench.py --experiments overall_performance qwen_scale_analysis
  
  # Use custom config
  python run_pilot_bench.py --config my_config.json --full
        """
    )
    
    parser.add_argument('--full', action='store_true', 
                       help='Run full benchmark with all experiments')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick test with 3 models')
    parser.add_argument('--experiments', nargs='+',
                       help='Specific experiments to run')
    parser.add_argument('--config', type=str,
                       help='Custom configuration file')
    parser.add_argument('--analyze-only', type=str,
                       help='Only analyze existing results from session directory')
    
    args = parser.parse_args()
    
    # 创建运行器
    runner = PILOTBenchRunner(config_file=args.config)
    
    if args.analyze_only:
        # 仅分析模式
        report_path = runner.analyze_results(args.analyze_only)
        print(f"Analysis complete. Report: {report_path}")
        
    elif args.quick:
        # 快速测试
        runner.quick_test()
        
    elif args.full:
        # 完整基准测试
        runner.run_full_benchmark()
        
    elif args.experiments:
        # 运行特定实验
        runner.config['experiments'] = {
            exp: {"enabled": exp in args.experiments}
            for exp in runner.config['experiments']
        }
        results = runner.run_experiments()
        report_path = runner.analyze_results(results['session_dir'])
        print(f"Experiments complete. Report: {report_path}")
        
    else:
        # 显示帮助
        parser.print_help()
        print("\nAvailable experiments:")
        for exp in runner.config['experiments']:
            print(f"  - {exp}")


if __name__ == "__main__":
    main()