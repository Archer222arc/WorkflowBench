#!/usr/bin/env python3
"""
Phase 1/2/3 完整集成和验证脚本
===============================
集成所有Phase的改进并进行完整测试
"""

import sys
import json
import logging
import numpy as np
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PhaseIntegrationManager:
    """管理Phase 1/2/3的完整集成"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'phases': {},
            'integration_tests': {},
            'performance_metrics': {}
        }
    
    def run_complete_integration(self):
        """运行完整的集成流程"""
        logger.info("="*70)
        logger.info("Phase 1/2/3 完整集成测试")
        logger.info("="*70)
        
        # 1. 应用所有修复
        logger.info("\n步骤 1: 应用所有修复")
        if not self.apply_all_fixes():
            logger.error("修复应用失败，中止测试")
            return False
        
        # 2. 验证各Phase功能
        logger.info("\n步骤 2: 验证各Phase功能")
        self.verify_phase_features()
        
        # 3. 运行集成训练
        logger.info("\n步骤 3: 运行集成训练")
        self.run_integrated_training()
        
        # 4. 性能评估
        logger.info("\n步骤 4: 性能评估")
        self.evaluate_performance()
        
        # 5. 生成报告
        logger.info("\n步骤 5: 生成报告")
        self.generate_report()
        
        return True
    
    def apply_all_fixes(self):
        """应用所有必要的修复"""
        try:
            # 检查并应用Phase 2修复
            from apply_phase23_fixes import Phase23FixApplier
            
            applier = Phase23FixApplier()
            success = applier.apply_all_fixes()
            
            self.results['phases']['fixes_applied'] = {
                'status': 'SUCCESS' if success else 'FAILED',
                'fixes': applier.fixes_applied
            }
            
            return success
            
        except Exception as e:
            logger.error(f"应用修复时出错: {e}")
            self.results['phases']['fixes_applied'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            return False
    
    def verify_phase_features(self):
        """验证各Phase的功能"""
        
        # Phase 1: Workflow强化
        logger.info("\n验证Phase 1: Workflow强化机制")
        phase1_result = self.verify_phase1_workflow()
        self.results['phases']['phase1'] = phase1_result
        
        # Phase 2: 稳定评分
        logger.info("\n验证Phase 2: 稳定评分系统")
        phase2_result = self.verify_phase2_scoring()
        self.results['phases']['phase2'] = phase2_result
        
        # Phase 3: 任务感知状态
        logger.info("\n验证Phase 3: 任务感知状态")
        phase3_result = self.verify_phase3_features()
        self.results['phases']['phase3'] = phase3_result
    
    def verify_phase1_workflow(self):
        """验证Phase 1 Workflow强化功能"""
        try:
            from phase1_workflow_enforcement import WorkflowEnforcer, test_workflow_enforcement
            
            # 运行测试
            test_workflow_enforcement()
            
            # 创建实例测试
            enforcer = WorkflowEnforcer(strict_mode=True)
            test_workflow = {
                'task_type': 'test',
                'optimal_sequence': ['tool1', 'tool2', 'tool3']
            }
            enforcer.set_workflow(test_workflow)
            
            # 测试验证
            valid, reward, msg = enforcer.validate_action({'tool_name': 'tool1'}, {})
            
            return {
                'status': 'PASSED' if valid else 'FAILED',
                'enforcement_working': valid,
                'message': msg
            }
            
        except Exception as e:
            logger.error(f"Phase 1验证失败: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def verify_phase2_scoring(self):
        """验证Phase 2评分系统"""
        try:
            from diagnose_scoring_issue_improved import diagnose_scoring_issue_improved
            from workflow_quality_test_flawed import StableScorer
            
            # 运行改进的诊断
            logger.info("运行Phase 2诊断...")
            diagnose_scoring_issue_improved()
            
            # 直接测试评分
            scorer = StableScorer()
            
            # 测试案例
            execution_result = {
                'tool_calls': ['file_reader', 'data_transformer', 'file_writer'],
                'success': True
            }
            
            evaluation_context = {
                'task_type': 'data_pipeline',
                'required_tools': ['file_reader', 'data_transformer', 'file_writer']
            }
            
            score, breakdown = scorer.calculate_stable_score(
                execution_result, evaluation_context
            )
            
            # 验证得分合理性
            is_valid = (
                0 <= score <= 1 and
                breakdown['task_achievement'] > 0 and  # 不应该是0
                breakdown['execution_quality'] > 0
            )
            
            return {
                'status': 'PASSED' if is_valid else 'FAILED',
                'final_score': score,
                'task_achievement': breakdown['task_achievement'],
                'execution_quality': breakdown['execution_quality'],
                'scoring_fixed': breakdown['task_achievement'] > 0
            }
            
        except Exception as e:
            logger.error(f"Phase 2验证失败: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def verify_phase3_features(self):
        """验证Phase 3特征提取"""
        try:
            from generalized_mdp_framework import TaskFeatures, TaskAwareMDPState
            
            # 创建测试状态
            state = TaskAwareMDPState(
                task_id='test_123',
                task_type='complex_pipeline',
                task_objective='Read data, transform it, and save results'
            )
            
            # 检查特征提取
            features = state.task_features
            vector = features.to_vector()
            
            # 验证
            checks = {
                'vector_shape': vector.shape == (20,),
                'normalized': -3 < vector.mean() < 3,
                'features_extracted': features.has_input_requirement and features.has_output_requirement,
                'complexity_set': features.complexity is not None
            }
            
            return {
                'status': 'PASSED' if all(checks.values()) else 'FAILED',
                'checks': checks,
                'vector_stats': {
                    'mean': float(vector.mean()),
                    'std': float(vector.std()),
                    'shape': vector.shape
                }
            }
            
        except Exception as e:
            logger.error(f"Phase 3验证失败: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def run_integrated_training(self):
        """运行集成训练测试"""
        try:
            from unified_training_manager import UnifiedTrainingManager
            from phase1_workflow_enforcement import WorkflowEnforcer, WorkflowGuidedMDPEnvironment
            
            logger.info("创建集成训练环境...")
            
            # 创建管理器
            manager = UnifiedTrainingManager(
                use_task_aware_state=True,  # Phase 3
                enforce_workflow=False,      # 先用基础环境
                use_phase2_scoring=True      # Phase 2
            )
            
            if not manager.setup_environment():
                logger.error("环境设置失败")
                self.results['integration_tests']['training'] = {
                    'status': 'FAILED',
                    'error': 'Environment setup failed'
                }
                return
            
            # 添加Phase 1 workflow强化
            enforcer = WorkflowEnforcer(strict_mode=False)  # 使用非严格模式
            wrapped_env = WorkflowGuidedMDPEnvironment(manager.env, enforcer)
            
            # 设置workflow生成器
            if hasattr(manager, 'generator'):
                wrapped_env.set_workflow_generator(manager.generator)
            
            # 替换环境
            manager.env = wrapped_env
            
            # 运行短期训练
            logger.info("运行50个episode的集成训练...")
            start_time = time.time()
            
            success = manager.train_dqn(
                num_episodes=50,
                print_frequency=10,
                save_frequency=50
            )
            
            training_time = time.time() - start_time
            
            if success:
                # 评估结果
                eval_results = manager.evaluate(num_episodes=20)
                
                self.results['integration_tests']['training'] = {
                    'status': 'SUCCESS',
                    'episodes': 50,
                    'training_time': training_time,
                    'success_rate': eval_results['overall_success'],
                    'phase2_score': eval_results['overall_phase2_score'],
                    'task_results': eval_results['task_results']
                }
                
                logger.info(f"训练完成:")
                logger.info(f"  成功率: {eval_results['overall_success']:.2%}")
                logger.info(f"  Phase 2得分: {eval_results['overall_phase2_score']:.3f}")
            else:
                self.results['integration_tests']['training'] = {
                    'status': 'FAILED',
                    'error': 'Training failed'
                }
                
        except Exception as e:
            logger.error(f"集成训练失败: {e}")
            self.results['integration_tests']['training'] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    def evaluate_performance(self):
        """评估整体性能"""
        try:
            from workflow_quality_test_flawed import WorkflowQualityTester
            from mdp_workflow_generator import MDPWorkflowGenerator
            
            logger.info("运行性能评估...")
            
            # 创建测试器
            generator = MDPWorkflowGenerator(
                "checkpoints/best_model.pt",
                "mcp_generated_library/tool_registry.json"
            )
            
            tester = WorkflowQualityTester(
                generator,
                output_dir="phase123_performance",
                use_phase2_scoring=True
            )
            
            # 运行简化测试
            tester.test_config['num_tests_per_task'] = 5
            
            results = tester.run_comprehensive_test(
                task_types=['simple_task', 'data_pipeline'],
                test_flawed=False
            )
            
            # 提取关键指标
            self.results['performance_metrics'] = {
                'overall_improvement': results['summary'].get('avg_success_rate_improvement', 0),
                'score_improvement': results['summary'].get('avg_final_score_improvement', 0),
                'score_stability': results['summary'].get('overall_score_stability', 0),
                'task_types_tested': list(results['results'].keys())
            }
            
            logger.info(f"性能评估完成:")
            logger.info(f"  成功率提升: {self.results['performance_metrics']['overall_improvement']:+.2%}")
            logger.info(f"  得分提升: {self.results['performance_metrics']['score_improvement']:+.3f}")
            
        except Exception as e:
            logger.error(f"性能评估失败: {e}")
            self.results['performance_metrics'] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    def generate_report(self):
        """生成综合报告"""
        # 保存JSON结果
        output_file = Path("phase123_integration_results.json")
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # 生成文本报告
        report_file = Path("phase123_integration_report.txt")
        with open(report_file, 'w') as f:
            f.write("Phase 1/2/3 集成测试报告\n")
            f.write("="*70 + "\n")
            f.write(f"生成时间: {self.results['timestamp']}\n\n")
            
            # Phase验证结果
            f.write("## Phase功能验证\n\n")
            for phase, result in self.results['phases'].items():
                if isinstance(result, dict) and 'status' in result:
                    f.write(f"### {phase}\n")
                    f.write(f"状态: {result['status']}\n")
                    if result['status'] == 'PASSED':
                        f.write("✅ 功能正常\n")
                    else:
                        f.write("❌ 存在问题\n")
                    f.write("\n")
            
            # 集成训练结果
            if 'training' in self.results.get('integration_tests', {}):
                training = self.results['integration_tests']['training']
                f.write("## 集成训练结果\n\n")
                f.write(f"状态: {training.get('status', 'N/A')}\n")
                if training.get('status') == 'SUCCESS':
                    f.write(f"成功率: {training.get('success_rate', 0):.2%}\n")
                    f.write(f"Phase 2得分: {training.get('phase2_score', 0):.3f}\n")
                f.write("\n")
            
            # 性能指标
            if self.results.get('performance_metrics'):
                metrics = self.results['performance_metrics']
                f.write("## 性能指标\n\n")
                f.write(f"成功率提升: {metrics.get('overall_improvement', 0):+.2%}\n")
                f.write(f"得分提升: {metrics.get('score_improvement', 0):+.3f}\n")
                f.write(f"评分稳定性: {metrics.get('score_stability', 0):.3f}\n")
                f.write("\n")
            
            # 总结
            f.write("## 总结\n\n")
            all_passed = all(
                phase.get('status') == 'PASSED'
                for phase in self.results['phases'].values()
                if isinstance(phase, dict) and 'status' in phase
            )
            
            if all_passed:
                f.write("✅ 所有Phase功能验证通过\n")
                f.write("✅ Phase 2评分系统已修复（task_achievement不再为0）\n")
                f.write("✅ Phase 3特征提取正常工作\n")
                f.write("✅ 集成训练成功运行\n")
            else:
                f.write("⚠️  部分功能存在问题，请查看详细日志\n")
        
        logger.info(f"\n报告已生成:")
        logger.info(f"  JSON结果: {output_file}")
        logger.info(f"  文本报告: {report_file}")
        
        # 生成可视化
        self.generate_visualization()
    
    def generate_visualization(self):
        """生成结果可视化"""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle('Phase 1/2/3 集成测试结果', fontsize=16)
            
            # 1. Phase状态
            ax = axes[0, 0]
            phases = list(self.results['phases'].keys())
            statuses = [
                1 if p.get('status') == 'PASSED' else 0
                for p in self.results['phases'].values()
                if isinstance(p, dict) and 'status' in p
            ]
            
            ax.bar(phases, statuses, color=['green' if s else 'red' for s in statuses])
            ax.set_ylabel('状态 (1=通过, 0=失败)')
            ax.set_title('Phase功能验证状态')
            ax.set_ylim(0, 1.2)
            
            # 2. Phase 2评分分布
            ax = axes[0, 1]
            if 'phase2' in self.results['phases']:
                phase2 = self.results['phases']['phase2']
                if 'task_achievement' in phase2:
                    scores = [
                        phase2.get('task_achievement', 0),
                        phase2.get('execution_quality', 0),
                        phase2.get('final_score', 0)
                    ]
                    labels = ['任务完成度', '执行质量', '最终得分']
                    ax.bar(labels, scores, color=['blue', 'green', 'orange'])
                    ax.set_ylabel('得分')
                    ax.set_title('Phase 2评分组成')
                    ax.set_ylim(0, 1.1)
            
            # 3. 训练性能
            ax = axes[1, 0]
            if 'training' in self.results.get('integration_tests', {}):
                training = self.results['integration_tests']['training']
                if training.get('status') == 'SUCCESS':
                    metrics = ['成功率', 'Phase 2得分']
                    values = [
                        training.get('success_rate', 0),
                        training.get('phase2_score', 0)
                    ]
                    ax.bar(metrics, values, color=['skyblue', 'lightgreen'])
                    ax.set_ylabel('值')
                    ax.set_title('集成训练结果')
                    ax.set_ylim(0, 1.1)
            
            # 4. 改进幅度
            ax = axes[1, 1]
            if self.results.get('performance_metrics'):
                metrics = self.results['performance_metrics']
                improvements = [
                    metrics.get('overall_improvement', 0) * 100,  # 转换为百分比
                    metrics.get('score_improvement', 0) * 100
                ]
                labels = ['成功率提升(%)', '得分提升(%)']
                colors = ['green' if i > 0 else 'red' for i in improvements]
                ax.bar(labels, improvements, color=colors)
                ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
                ax.set_ylabel('提升百分比')
                ax.set_title('性能改进')
            
            plt.tight_layout()
            plt.savefig('phase123_integration_results.png', dpi=300, bbox_inches='tight')
            logger.info("  可视化图表: phase123_integration_results.png")
            
        except Exception as e:
            logger.warning(f"生成可视化失败: {e}")


def main():
    """主函数"""
    logger.info("Phase 1/2/3 完整集成测试")
    logger.info("="*70)
    
    manager = PhaseIntegrationManager()
    success = manager.run_complete_integration()
    
    if success:
        logger.info("\n✅ 集成测试完成！")
        logger.info("\n关键结果:")
        
        # 显示关键结果
        results = manager.results
        if 'phase2' in results['phases']:
            phase2 = results['phases']['phase2']
            if phase2.get('scoring_fixed'):
                logger.info("✅ Phase 2评分问题已修复 - task_achievement不再为0")
        
        if results.get('performance_metrics'):
            metrics = results['performance_metrics']
            logger.info(f"✅ 性能提升: 成功率 {metrics.get('overall_improvement', 0):+.2%}")
        
        logger.info("\n下一步建议:")
        logger.info("1. 运行长期训练: python main.py train --episodes 1000")
        logger.info("2. 执行完整的workflow质量测试")
        logger.info("3. 开始Phase 4的设计和实施")
        
        return 0
    else:
        logger.error("\n❌ 集成测试失败，请检查错误日志")
        return 1


if __name__ == "__main__":
    sys.exit(main())
