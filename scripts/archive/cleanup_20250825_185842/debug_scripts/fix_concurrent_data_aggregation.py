#!/usr/bin/env python3
"""
修复Ultra并发模式下的数据聚合问题
==============================

主要问题：
1. overall_stats没有被正确聚合
2. 字段名不一致（success vs successful）  
3. summary统计没有更新
4. 缺乏从底层数据重新聚合的机制
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

class ConcurrentDataAggregationFixer:
    """并发数据聚合修复器"""
    
    def __init__(self):
        self.db_path = Path("pilot_bench_cumulative_results/master_database.json")
        self.backup_path = Path(f"pilot_bench_cumulative_results/master_database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
    def load_database(self) -> Dict[str, Any]:
        """加载数据库"""
        if not self.db_path.exists():
            print("❌ 数据库文件不存在")
            return {}
        
        with open(self.db_path, 'r') as f:
            return json.load(f)
    
    def backup_database(self, db: Dict[str, Any]):
        """备份数据库"""
        with open(self.backup_path, 'w') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f"✅ 数据库已备份到: {self.backup_path}")
    
    def fix_field_naming_consistency(self, db: Dict[str, Any]) -> int:
        """修复字段命名不一致问题"""
        print("🔧 修复字段命名不一致...")
        fixed_count = 0
        
        models = db.get('models', {})
        for model_name, model_data in models.items():
            if not isinstance(model_data, dict):
                continue
                
            # 遍历所有层级的数据
            by_prompt = model_data.get('by_prompt_type', {})
            for prompt_type, prompt_data in by_prompt.items():
                by_rate = prompt_data.get('by_tool_success_rate', {})
                for rate, rate_data in by_rate.items():
                    by_diff = rate_data.get('by_difficulty', {})
                    for diff, diff_data in by_diff.items():
                        by_task = diff_data.get('by_task_type', {})
                        for task_type, task_data in by_task.items():
                            # 检查是否使用了success而不是successful
                            if 'success' in task_data and 'successful' not in task_data:
                                task_data['successful'] = task_data['success']
                                print(f"  修复 {model_name}/{prompt_type}/{rate}/{diff}/{task_type}: success -> successful")
                                fixed_count += 1
                            
                            # 检查是否使用了failure而不是failed
                            if 'failure' in task_data and 'failed' not in task_data:
                                task_data['failed'] = task_data['failure']
                                print(f"  修复 {model_name}/{prompt_type}/{rate}/{diff}/{task_type}: failure -> failed")
                                fixed_count += 1
        
        print(f"✅ 修复了 {fixed_count} 个字段命名问题")
        return fixed_count
    
    def rebuild_overall_stats(self, db: Dict[str, Any]) -> int:
        """重建overall_stats聚合统计"""
        print("🔧 重建overall_stats聚合统计...")
        rebuilt_count = 0
        
        models = db.get('models', {})
        for model_name, model_data in models.items():
            if not isinstance(model_data, dict):
                continue
            
            print(f"  重建 {model_name} 的overall_stats...")
            
            # 聚合所有统计
            total_tests = 0
            total_success = 0
            total_partial = 0
            total_failed = 0
            total_execution_time = 0.0
            total_turns = 0
            total_tool_calls = 0
            test_count_for_avg = 0
            
            # 聚合所有分数
            total_workflow_score = 0.0
            total_phase2_score = 0.0 
            total_quality_score = 0.0
            total_final_score = 0.0
            score_count = 0
            
            by_prompt = model_data.get('by_prompt_type', {})
            for prompt_type, prompt_data in by_prompt.items():
                by_rate = prompt_data.get('by_tool_success_rate', {})
                for rate, rate_data in by_rate.items():
                    by_diff = rate_data.get('by_difficulty', {})
                    for diff, diff_data in by_diff.items():
                        by_task = diff_data.get('by_task_type', {})
                        for task_type, task_data in by_task.items():
                            # 累加基础统计
                            total_tests += task_data.get('total', 0)
                            total_success += task_data.get('successful', 0)
                            total_partial += task_data.get('partial', 0)
                            total_failed += task_data.get('failed', 0)
                            
                            # 累加时间和轮次（如果有）
                            if 'avg_execution_time' in task_data and task_data['avg_execution_time'] > 0:
                                total_execution_time += task_data['avg_execution_time'] * task_data.get('total', 0)
                                test_count_for_avg += task_data.get('total', 0)
                            
                            if 'avg_turns' in task_data and task_data['avg_turns'] > 0:
                                total_turns += task_data['avg_turns'] * task_data.get('total', 0)
                            
                            # 累加分数（如果有）
                            for score_field in ['avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score']:
                                if score_field in task_data and task_data[score_field] > 0:
                                    score_value = task_data[score_field] * task_data.get('total', 0)
                                    if score_field == 'avg_workflow_score':
                                        total_workflow_score += score_value
                                    elif score_field == 'avg_phase2_score':
                                        total_phase2_score += score_value
                                    elif score_field == 'avg_quality_score':
                                        total_quality_score += score_value
                                    elif score_field == 'avg_final_score':
                                        total_final_score += score_value
                                    score_count = max(score_count, task_data.get('total', 0))
            
            # 计算聚合指标
            success_rate = total_success / total_tests if total_tests > 0 else 0.0
            partial_rate = total_partial / total_tests if total_tests > 0 else 0.0
            failure_rate = total_failed / total_tests if total_tests > 0 else 0.0
            
            avg_execution_time = total_execution_time / test_count_for_avg if test_count_for_avg > 0 else 0.0
            avg_turns = total_turns / test_count_for_avg if test_count_for_avg > 0 else 0.0
            
            # 计算平均分数
            avg_workflow_score = total_workflow_score / score_count if score_count > 0 else 0.0
            avg_phase2_score = total_phase2_score / score_count if score_count > 0 else 0.0
            avg_quality_score = total_quality_score / score_count if score_count > 0 else 0.0
            avg_final_score = total_final_score / score_count if score_count > 0 else 0.0
            
            # 更新overall_stats
            model_data['total_tests'] = total_tests
            model_data['overall_stats'] = {
                'total_tests': total_tests,
                'total_success': total_success,
                'total_partial': total_partial,
                'total_failed': total_failed,
                'success_rate': success_rate,
                'partial_rate': partial_rate,
                'failure_rate': failure_rate,
                'avg_execution_time': avg_execution_time,
                'avg_turns': avg_turns,
                'avg_workflow_score': avg_workflow_score,
                'avg_phase2_score': avg_phase2_score,
                'avg_quality_score': avg_quality_score,
                'avg_final_score': avg_final_score
            }
            
            print(f"    总测试: {total_tests}, 成功: {total_success}, 成功率: {success_rate:.1%}")
            rebuilt_count += 1
        
        print(f"✅ 重建了 {rebuilt_count} 个模型的overall_stats")
        return rebuilt_count
    
    def rebuild_summary_stats(self, db: Dict[str, Any]) -> bool:
        """重建summary全局统计"""
        print("🔧 重建summary全局统计...")
        
        total_tests = 0
        total_success = 0
        total_partial = 0
        total_failure = 0
        models_tested = []
        last_test_time = None
        
        models = db.get('models', {})
        for model_name, model_data in models.items():
            if not isinstance(model_data, dict):
                continue
            
            overall_stats = model_data.get('overall_stats', {})
            if overall_stats.get('total_tests', 0) > 0:
                total_tests += overall_stats.get('total_tests', 0)
                total_success += overall_stats.get('total_success', 0)
                total_partial += overall_stats.get('total_partial', 0)
                total_failure += overall_stats.get('total_failed', 0)
                models_tested.append(model_name)
            
            # 更新最后测试时间
            model_last_time = model_data.get('last_test_time', '')
            if model_last_time:
                if not last_test_time or model_last_time > last_test_time:
                    last_test_time = model_last_time
        
        # 更新summary
        if 'summary' not in db:
            db['summary'] = {}
        
        db['summary'].update({
            'total_tests': total_tests,
            'total_success': total_success,
            'total_partial': total_partial,
            'total_failure': total_failure,
            'models_tested': models_tested,
            'last_test_time': last_test_time
        })
        
        print(f"✅ Summary更新: {total_tests}个测试, {len(models_tested)}个模型")
        return True
    
    def add_missing_aggregation_fields(self, db: Dict[str, Any]) -> int:
        """添加缺失的聚合字段"""
        print("🔧 添加缺失的聚合字段...")
        added_count = 0
        
        models = db.get('models', {})
        for model_name, model_data in models.items():
            if not isinstance(model_data, dict):
                continue
            
            by_prompt = model_data.get('by_prompt_type', {})
            for prompt_type, prompt_data in by_prompt.items():
                by_rate = prompt_data.get('by_tool_success_rate', {})
                for rate, rate_data in by_rate.items():
                    by_diff = rate_data.get('by_difficulty', {})
                    for diff, diff_data in by_diff.items():
                        by_task = diff_data.get('by_task_type', {})
                        for task_type, task_data in by_task.items():
                            # 确保所有必需的字段都存在
                            required_fields = {
                                'total': 0,
                                'successful': 0,
                                'partial': 0, 
                                'failed': 0,
                                'success_rate': 0.0,
                                'partial_rate': 0.0,
                                'failure_rate': 0.0
                            }
                            
                            for field, default_value in required_fields.items():
                                if field not in task_data:
                                    task_data[field] = default_value
                                    added_count += 1
                            
                            # 重新计算比例字段
                            total = task_data.get('total', 0)
                            if total > 0:
                                task_data['success_rate'] = task_data.get('successful', 0) / total
                                task_data['partial_rate'] = task_data.get('partial', 0) / total  
                                task_data['failure_rate'] = task_data.get('failed', 0) / total
        
        print(f"✅ 添加了 {added_count} 个缺失字段")
        return added_count
    
    def validate_aggregation(self, db: Dict[str, Any]) -> Dict[str, Any]:
        """验证聚合结果"""
        print("🔍 验证聚合结果...")
        
        validation_results = {
            'models_with_data': 0,
            'models_without_data': [],
            'total_tests_sum': 0,
            'field_consistency': True,
            'issues': []
        }
        
        models = db.get('models', {})
        for model_name, model_data in models.items():
            if not isinstance(model_data, dict):
                continue
            
            overall_stats = model_data.get('overall_stats', {})
            total_tests = overall_stats.get('total_tests', 0)
            
            if total_tests > 0:
                validation_results['models_with_data'] += 1
                validation_results['total_tests_sum'] += total_tests
                print(f"  ✅ {model_name}: {total_tests} 测试")
            else:
                validation_results['models_without_data'].append(model_name)
                print(f"  ❌ {model_name}: 无数据")
        
        # 检查summary一致性
        summary = db.get('summary', {})
        summary_total = summary.get('total_tests', 0)
        
        if summary_total != validation_results['total_tests_sum']:
            validation_results['field_consistency'] = False
            validation_results['issues'].append(
                f"Summary总数不匹配: summary={summary_total}, 实际={validation_results['total_tests_sum']}"
            )
        
        print(f"✅ 验证完成: {validation_results['models_with_data']} 个模型有数据")
        return validation_results
    
    def save_database(self, db: Dict[str, Any]):
        """保存数据库"""
        with open(self.db_path, 'w') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        print(f"✅ 数据库已保存")
    
    def run_comprehensive_fix(self) -> Dict[str, Any]:
        """运行完整修复流程"""
        print("🚀 启动并发数据聚合修复")
        print("=" * 50)
        
        # 加载数据库
        db = self.load_database()
        if not db:
            return {'error': 'Cannot load database'}
        
        # 备份数据库
        self.backup_database(db)
        
        # 执行修复
        results = {}
        
        # 1. 修复字段命名不一致
        results['field_naming_fixes'] = self.fix_field_naming_consistency(db)
        
        # 2. 添加缺失的聚合字段
        results['added_fields'] = self.add_missing_aggregation_fields(db)
        
        # 3. 重建overall_stats
        results['rebuilt_overall_stats'] = self.rebuild_overall_stats(db)
        
        # 4. 重建summary统计
        results['rebuilt_summary'] = self.rebuild_summary_stats(db)
        
        # 5. 验证结果
        results['validation'] = self.validate_aggregation(db)
        
        # 保存修复后的数据库
        self.save_database(db)
        
        print("\n" + "=" * 50)
        print("📋 修复完成总结")
        print("=" * 50)
        print(f"字段命名修复: {results['field_naming_fixes']} 个")
        print(f"添加缺失字段: {results['added_fields']} 个")
        print(f"重建overall_stats: {results['rebuilt_overall_stats']} 个模型")
        print(f"有数据模型: {results['validation']['models_with_data']} 个")
        print(f"总测试数: {results['validation']['total_tests_sum']} 个")
        
        if results['validation']['issues']:
            print(f"❌ 发现问题:")
            for issue in results['validation']['issues']:
                print(f"  - {issue}")
        else:
            print(f"✅ 所有验证通过")
        
        return results

def main():
    """主函数"""
    fixer = ConcurrentDataAggregationFixer()
    results = fixer.run_comprehensive_fix()
    
    # 保存修复结果
    output_file = Path(f"fix_concurrent_aggregation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 修复结果已保存到: {output_file}")

if __name__ == "__main__":
    main()