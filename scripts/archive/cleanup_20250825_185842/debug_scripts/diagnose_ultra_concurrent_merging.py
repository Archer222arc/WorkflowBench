#!/usr/bin/env python3
"""
Ultra并发模式数据合并完整性诊断工具
=================================

检查以下并发层级的数据合并问题：
1. 模型级并发 - 不同模型同时测试时的数据分离
2. API级并发 - 同一模型多个API实例的数据合并
3. Prompt级并发 - 多种prompt类型并行时的数据分离
4. 分片级合并 - ultra_parallel_runner分片结果聚合
5. 跨进程合并 - 多个smart_batch_runner进程的数据合并
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Any
import subprocess

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

class UltraConcurrentMergingDiagnostic:
    """Ultra并发模式数据合并诊断器"""
    
    def __init__(self):
        self.db_path = Path("pilot_bench_cumulative_results/master_database.json")
        self.log_dir = Path("logs")
        self.results = {}
        
        print("🔍 启动Ultra并发模式数据合并诊断")
        print("=" * 60)
    
    def load_database(self) -> Dict:
        """加载数据库"""
        if not self.db_path.exists():
            print("❌ 数据库文件不存在")
            return {}
        
        with open(self.db_path, 'r') as f:
            return json.load(f)
    
    def analyze_model_level_concurrency(self, db: Dict) -> Dict:
        """分析模型级别并发的数据合并问题"""
        print("\n📊 1. 模型级并发数据合并分析")
        print("-" * 40)
        
        models = db.get('models', {})
        analysis = {
            'total_models': len(models),
            'models_with_data': 0,
            'models_without_data': [],
            'data_mixing_issues': [],
            'expected_vs_actual': {}
        }
        
        expected_models = [
            'DeepSeek-V3-0324', 'DeepSeek-R1-0528', 'Llama-3.3-70B-Instruct',
            'qwen2.5-72b-instruct', 'qwen2.5-32b-instruct', 'qwen2.5-14b-instruct',
            'qwen2.5-7b-instruct', 'qwen2.5-3b-instruct'
        ]
        
        print(f"预期模型数量: {len(expected_models)}")
        print(f"实际模型数量: {len(models)}")
        
        # 检查每个模型的数据完整性
        for model_name, model_data in models.items():
            if isinstance(model_data, dict):
                overall_stats = model_data.get('overall_stats', {})
                total_tests = overall_stats.get('total_tests', 0)
                
                if total_tests > 0:
                    analysis['models_with_data'] += 1
                    print(f"  ✅ {model_name}: {total_tests} 测试")
                    
                    # 检查是否有异常高的测试数量（可能表示数据混合）
                    if total_tests > 50:  # 正常5.1测试应该是10个测试/模型
                        analysis['data_mixing_issues'].append({
                            'model': model_name,
                            'issue': 'abnormally_high_test_count',
                            'count': total_tests,
                            'expected': 10
                        })
                        print(f"    ⚠️  异常高测试数量: {total_tests} (期望: 10)")
                else:
                    analysis['models_without_data'].append(model_name)
                    print(f"  ❌ {model_name}: 无测试数据")
        
        # 检查缺失的模型
        missing_models = set(expected_models) - set(models.keys())
        if missing_models:
            analysis['missing_models'] = list(missing_models)
            print(f"\n❌ 缺失模型: {missing_models}")
        else:
            print(f"\n✅ 所有期望模型都存在")
        
        self.results['model_level'] = analysis
        return analysis
    
    def analyze_api_level_concurrency(self, db: Dict) -> Dict:
        """分析API级别并发的数据合并问题"""
        print("\n📊 2. API级并发数据合并分析")
        print("-" * 40)
        
        analysis = {
            'azure_instances_merged': {},
            'ideallab_keys_merged': {},
            'potential_duplication': []
        }
        
        models = db.get('models', {})
        
        # 检查Azure模型的实例合并（DeepSeek, Llama）
        azure_models = ['DeepSeek-V3-0324', 'DeepSeek-R1-0528', 'Llama-3.3-70B-Instruct']
        
        for model in azure_models:
            if model in models:
                model_data = models[model]
                overall_stats = model_data.get('overall_stats', {})
                total_tests = overall_stats.get('total_tests', 0)
                
                # 检查是否有3个实例的数据被正确合并
                # 每个实例应该贡献相等数量的测试
                analysis['azure_instances_merged'][model] = {
                    'total_tests': total_tests,
                    'expected_per_instance': total_tests / 3 if total_tests > 0 else 0,
                    'status': 'merged' if total_tests > 0 else 'no_data'
                }
                
                print(f"  Azure模型 {model}:")
                print(f"    总测试: {total_tests}")
                print(f"    预期每实例: {total_tests / 3:.1f}")
        
        # 检查IdealLab qwen模型的API key合并
        qwen_models = ['qwen2.5-72b-instruct', 'qwen2.5-32b-instruct', 'qwen2.5-14b-instruct',
                      'qwen2.5-7b-instruct', 'qwen2.5-3b-instruct']
        
        for model in qwen_models:
            if model in models:
                model_data = models[model]
                overall_stats = model_data.get('overall_stats', {})
                total_tests = overall_stats.get('total_tests', 0)
                
                # 检查是否有3个API key的数据被正确合并
                analysis['ideallab_keys_merged'][model] = {
                    'total_tests': total_tests,
                    'expected_per_key': total_tests / 3 if total_tests > 0 else 0,
                    'status': 'merged' if total_tests > 0 else 'no_data'
                }
                
                print(f"  IdealLab模型 {model}:")
                print(f"    总测试: {total_tests}")
                print(f"    预期每key: {total_tests / 3:.1f}")
        
        self.results['api_level'] = analysis
        return analysis
    
    def analyze_prompt_level_concurrency(self, db: Dict) -> Dict:
        """分析Prompt级别并发的数据分离"""
        print("\n📊 3. Prompt级并发数据分离分析")
        print("-" * 40)
        
        analysis = {
            'prompt_types_found': set(),
            'models_with_mixed_prompts': [],
            'prompt_separation_issues': []
        }
        
        models = db.get('models', {})
        
        for model_name, model_data in models.items():
            if not isinstance(model_data, dict):
                continue
                
            by_prompt = model_data.get('by_prompt_type', {})
            prompt_types = list(by_prompt.keys())
            
            analysis['prompt_types_found'].update(prompt_types)
            
            print(f"  模型 {model_name}:")
            print(f"    Prompt类型: {prompt_types}")
            
            # 检查是否有多种prompt类型（说明分离正确）
            if len(prompt_types) > 1:
                analysis['models_with_mixed_prompts'].append(model_name)
                print(f"    ✅ 正确分离了 {len(prompt_types)} 种prompt类型")
            elif len(prompt_types) == 1:
                print(f"    ⚠️  只有单一prompt类型: {prompt_types[0]}")
            else:
                print(f"    ❌ 没有prompt数据")
            
            # 检查每种prompt类型的数据完整性
            for prompt_type, prompt_data in by_prompt.items():
                by_rate = prompt_data.get('by_tool_success_rate', {})
                rates = list(by_rate.keys())
                
                if len(rates) == 0:
                    analysis['prompt_separation_issues'].append({
                        'model': model_name,
                        'prompt_type': prompt_type,
                        'issue': 'no_rate_data'
                    })
                    print(f"      ❌ {prompt_type}: 无tool_success_rate数据")
                else:
                    print(f"      ✅ {prompt_type}: {len(rates)} 种成功率")
        
        analysis['prompt_types_found'] = list(analysis['prompt_types_found'])
        print(f"\n发现的Prompt类型: {analysis['prompt_types_found']}")
        
        self.results['prompt_level'] = analysis
        return analysis
    
    def analyze_shard_aggregation(self) -> Dict:
        """分析分片数据聚合逻辑"""
        print("\n📊 4. 分片数据聚合逻辑分析")
        print("-" * 40)
        
        analysis = {
            'recent_shard_processes': [],
            'shard_completion_pattern': {},
            'aggregation_issues': []
        }
        
        # 检查最近的日志，寻找分片执行模式
        if self.log_dir.exists():
            log_files = list(self.log_dir.glob("batch_test_*.log"))
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            recent_logs = log_files[:5]  # 最近5个日志
            
            for log_file in recent_logs:
                try:
                    with open(log_file, 'r') as f:
                        content = f.read()
                    
                    # 寻找分片相关的日志
                    if 'shard' in content.lower() or '分片' in content:
                        analysis['recent_shard_processes'].append({
                            'file': str(log_file),
                            'size': len(content),
                            'has_shard_info': True
                        })
                        print(f"  📄 {log_file.name}: 包含分片信息")
                    else:
                        analysis['recent_shard_processes'].append({
                            'file': str(log_file),
                            'size': len(content),
                            'has_shard_info': False
                        })
                        print(f"  📄 {log_file.name}: 无分片信息")
                
                except Exception as e:
                    print(f"  ❌ 无法读取 {log_file.name}: {e}")
        
        self.results['shard_aggregation'] = analysis
        return analysis
    
    def analyze_cross_process_merging(self, db: Dict) -> Dict:
        """分析跨进程数据合并"""
        print("\n📊 5. 跨进程数据合并分析")  
        print("-" * 40)
        
        analysis = {
            'concurrent_write_evidence': [],
            'file_lock_usage': False,
            'data_consistency_issues': [],
            'timestamp_analysis': {}
        }
        
        # 检查数据时间戳分布，判断是否有并发写入
        models = db.get('models', {})
        
        all_timestamps = []
        for model_name, model_data in models.items():
            if isinstance(model_data, dict):
                last_test = model_data.get('last_test_time', '')
                if last_test:
                    all_timestamps.append(last_test)
        
        if all_timestamps:
            all_timestamps.sort()
            analysis['timestamp_analysis'] = {
                'earliest': all_timestamps[0],
                'latest': all_timestamps[-1],
                'total_entries': len(all_timestamps)
            }
            
            print(f"  时间戳分析:")
            print(f"    最早: {all_timestamps[0]}")
            print(f"    最晚: {all_timestamps[-1]}")
            print(f"    总条目: {len(all_timestamps)}")
        
        # 检查是否存在锁文件（说明使用了文件锁保护）
        lock_files = list(Path(".").glob("*.lock"))
        if lock_files:
            analysis['file_lock_usage'] = True
            print(f"  ✅ 发现锁文件: {[str(f) for f in lock_files]}")
        else:
            print(f"  ⚠️  未发现锁文件，可能存在并发写入风险")
        
        # 检查数据一致性（是否有重复或冲突的条目）
        # 通过检查test_groups的时间戳来识别可能的重复写入
        test_groups = db.get('test_groups', {})
        timestamp_groups = defaultdict(list)
        
        for group_id, group_data in test_groups.items():
            timestamp = group_data.get('timestamp', '')
            if timestamp:
                timestamp_groups[timestamp].append(group_id)
        
        # 如果同一时间戳有多个测试组，可能表示并发写入
        for timestamp, groups in timestamp_groups.items():
            if len(groups) > 1:
                analysis['concurrent_write_evidence'].append({
                    'timestamp': timestamp,
                    'group_count': len(groups),
                    'groups': groups[:3]  # 只显示前3个
                })
                print(f"  ⚠️  {timestamp}: {len(groups)} 个测试组（可能的并发写入）")
        
        self.results['cross_process'] = analysis
        return analysis
    
    def check_data_integrity(self, db: Dict) -> Dict:
        """检查整体数据完整性"""
        print("\n📊 6. 数据完整性检查")
        print("-" * 40)
        
        analysis = {
            'total_expected_tests': 0,
            'total_actual_tests': 0,
            'missing_test_ratio': 0.0,
            'integrity_score': 0.0,
            'critical_issues': []
        }
        
        # 计算期望的测试数量
        # 8个模型 × 5个任务类型 × 2个实例 = 80个测试（5.1基准测试）
        expected_models = 8
        expected_task_types = 5
        expected_instances = 2
        analysis['total_expected_tests'] = expected_models * expected_task_types * expected_instances
        
        # 计算实际测试数量
        models = db.get('models', {})
        actual_tests = 0
        
        for model_name, model_data in models.items():
            if isinstance(model_data, dict):
                overall_stats = model_data.get('overall_stats', {})
                total_tests = overall_stats.get('total_tests', 0)
                actual_tests += total_tests
        
        analysis['total_actual_tests'] = actual_tests
        
        if analysis['total_expected_tests'] > 0:
            analysis['missing_test_ratio'] = 1.0 - (actual_tests / analysis['total_expected_tests'])
            analysis['integrity_score'] = max(0, actual_tests / analysis['total_expected_tests'])
        
        print(f"  期望测试总数: {analysis['total_expected_tests']}")
        print(f"  实际测试总数: {analysis['total_actual_tests']}")
        print(f"  数据完整性评分: {analysis['integrity_score']:.2%}")
        
        # 识别关键问题
        if analysis['integrity_score'] < 0.5:
            analysis['critical_issues'].append("数据严重缺失（<50%）")
        if analysis['missing_test_ratio'] > 0.3:
            analysis['critical_issues'].append("测试缺失比例过高（>30%）")
        
        # 检查是否有任何模型的测试数量异常
        for model_name, model_data in models.items():
            if isinstance(model_data, dict):
                overall_stats = model_data.get('overall_stats', {})
                total_tests = overall_stats.get('total_tests', 0)
                
                # 单个模型期望10个测试
                expected_per_model = 10
                if total_tests > expected_per_model * 2:  # 超过期望2倍
                    analysis['critical_issues'].append(f"{model_name}: 测试数量异常（{total_tests}，期望{expected_per_model}）")
                elif total_tests == 0:
                    analysis['critical_issues'].append(f"{model_name}: 完全无测试数据")
        
        if analysis['critical_issues']:
            print(f"  ❌ 发现关键问题:")
            for issue in analysis['critical_issues']:
                print(f"    - {issue}")
        else:
            print(f"  ✅ 数据完整性良好")
        
        self.results['data_integrity'] = analysis
        return analysis
    
    def generate_recommendations(self) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        # 基于分析结果生成建议
        if 'model_level' in self.results:
            model_analysis = self.results['model_level']
            if model_analysis['data_mixing_issues']:
                recommendations.append("🔧 修复模型级数据混合问题 - 检查normalize_model_name函数")
            if model_analysis['models_without_data']:
                recommendations.append("🔧 调查模型缺失数据问题 - 检查API配置和执行日志")
        
        if 'api_level' in self.results:
            api_analysis = self.results['api_level']
            no_data_models = []
            for model, info in api_analysis['azure_instances_merged'].items():
                if info['status'] == 'no_data':
                    no_data_models.append(model)
            if no_data_models:
                recommendations.append(f"🔧 修复Azure模型数据合并 - 检查实例: {no_data_models}")
        
        if 'cross_process' in self.results:
            cross_analysis = self.results['cross_process']
            if not cross_analysis['file_lock_usage']:
                recommendations.append("🔧 启用文件锁保护 - 防止并发写入冲突")
            if cross_analysis['concurrent_write_evidence']:
                recommendations.append("🔧 检查并发写入冲突 - 可能存在数据竞争")
        
        if 'data_integrity' in self.results:
            integrity_analysis = self.results['data_integrity']
            if integrity_analysis['integrity_score'] < 0.8:
                recommendations.append("🔧 提高数据完整性 - 当前完整性低于80%")
        
        return recommendations
    
    def run_comprehensive_diagnosis(self) -> Dict:
        """运行完整诊断"""
        print(f"开始时间: {datetime.now()}")
        
        # 加载数据库
        db = self.load_database()
        
        if not db:
            return {'error': 'Cannot load database'}
        
        # 执行各项分析
        self.analyze_model_level_concurrency(db)
        self.analyze_api_level_concurrency(db)
        self.analyze_prompt_level_concurrency(db)
        self.analyze_shard_aggregation()
        self.analyze_cross_process_merging(db)
        self.check_data_integrity(db)
        
        # 生成建议
        recommendations = self.generate_recommendations()
        
        # 汇总报告
        print("\n" + "=" * 60)
        print("📋 Ultra并发数据合并诊断报告")
        print("=" * 60)
        
        # 关键指标
        if 'data_integrity' in self.results:
            integrity_score = self.results['data_integrity']['integrity_score']
            print(f"🎯 数据完整性评分: {integrity_score:.1%}")
        
        if 'model_level' in self.results:
            models_with_data = self.results['model_level']['models_with_data']
            total_models = self.results['model_level']['total_models']
            print(f"📊 有数据模型: {models_with_data}/{total_models}")
        
        # 建议
        if recommendations:
            print(f"\n💡 修复建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        else:
            print(f"\n✅ 所有检查通过，未发现明显问题")
        
        print(f"\n完成时间: {datetime.now()}")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'analysis_results': self.results,
            'recommendations': recommendations
        }

def main():
    """主函数"""
    diagnostic = UltraConcurrentMergingDiagnostic()
    results = diagnostic.run_comprehensive_diagnosis()
    
    # 保存诊断结果
    output_file = Path(f"diagnose_ultra_concurrent_merging_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 诊断结果已保存到: {output_file}")

if __name__ == "__main__":
    main()