#!/usr/bin/env python3
"""
验证Parquet和JSON数据一致性
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

class DataConsistencyVerifier:
    """数据一致性验证器"""
    
    def __init__(self):
        self.json_path = Path("pilot_bench_cumulative_results/master_database.json")
        self.parquet_path = Path("pilot_bench_parquet_data/test_results.parquet")
        self.results = {
            'json_exists': False,
            'parquet_exists': False,
            'models_match': False,
            'totals_match': False,
            'structure_match': False
        }
    
    def load_json_data(self):
        """加载JSON数据"""
        if not self.json_path.exists():
            print("❌ JSON数据库不存在")
            return None
        
        with open(self.json_path, 'r') as f:
            data = json.load(f)
        
        self.results['json_exists'] = True
        print(f"✅ JSON数据库已加载")
        return data
    
    def load_parquet_data(self):
        """加载Parquet数据"""
        if not self.parquet_path.exists():
            print("❌ Parquet文件不存在")
            # 检查增量目录
            inc_dir = Path("pilot_bench_parquet_data/incremental")
            if inc_dir.exists():
                inc_files = list(inc_dir.glob("*.parquet"))
                if inc_files:
                    print(f"  找到 {len(inc_files)} 个增量Parquet文件")
                    # 合并所有增量文件
                    dfs = []
                    for file in inc_files:
                        df = pd.read_parquet(file)
                        dfs.append(df)
                    if dfs:
                        combined_df = pd.concat(dfs, ignore_index=True)
                        self.results['parquet_exists'] = True
                        print(f"  合并了 {len(combined_df)} 条记录")
                        return combined_df
            return None
        
        df = pd.read_parquet(self.parquet_path)
        self.results['parquet_exists'] = True
        print(f"✅ Parquet文件已加载 ({len(df)} 条记录)")
        return df
    
    def extract_json_stats(self, json_data):
        """从JSON提取统计信息"""
        stats = {
            'total_tests': 0,
            'models': {},
            'prompt_types': set(),
            'difficulties': set(),
            'task_types': set()
        }
        
        # 从summary获取总数
        stats['total_tests'] = json_data.get('summary', {}).get('total_tests', 0)
        
        # 从models提取详细信息
        if 'models' in json_data:
            for model_name, model_data in json_data['models'].items():
                model_total = 0
                
                if 'by_prompt_type' in model_data:
                    for pt, pt_data in model_data['by_prompt_type'].items():
                        stats['prompt_types'].add(pt)
                        
                        if 'by_tool_success_rate' in pt_data:
                            for rate, rate_data in pt_data['by_tool_success_rate'].items():
                                
                                if 'by_difficulty' in rate_data:
                                    for diff, diff_data in rate_data['by_difficulty'].items():
                                        stats['difficulties'].add(diff)
                                        
                                        if 'by_task_type' in diff_data:
                                            for task, task_data in diff_data['by_task_type'].items():
                                                stats['task_types'].add(task)
                                                model_total += task_data.get('total', 0)
                
                stats['models'][model_name] = model_total
        
        return stats
    
    def extract_parquet_stats(self, df):
        """从Parquet提取统计信息"""
        stats = {
            'total_tests': len(df),
            'models': {},
            'prompt_types': set(),
            'difficulties': set(),
            'task_types': set()
        }
        
        # 按模型统计
        if 'model' in df.columns:
            model_counts = df['model'].value_counts().to_dict()
            stats['models'] = model_counts
        
        # 收集唯一值
        if 'prompt_type' in df.columns:
            stats['prompt_types'] = set(df['prompt_type'].unique())
        
        if 'difficulty' in df.columns:
            stats['difficulties'] = set(df['difficulty'].unique())
        
        if 'task_type' in df.columns:
            stats['task_types'] = set(df['task_type'].unique())
        
        return stats
    
    def compare_stats(self, json_stats, parquet_stats):
        """比较统计信息"""
        print("\n" + "=" * 60)
        print("数据对比")
        print("=" * 60)
        
        # 比较总数
        print(f"\n📊 总测试数:")
        print(f"  JSON: {json_stats['total_tests']}")
        print(f"  Parquet: {parquet_stats['total_tests']}")
        
        if json_stats['total_tests'] == parquet_stats['total_tests']:
            print("  ✅ 总数匹配")
            self.results['totals_match'] = True
        else:
            diff = abs(json_stats['total_tests'] - parquet_stats['total_tests'])
            print(f"  ❌ 差异: {diff}")
        
        # 比较模型
        print(f"\n🤖 模型数量:")
        print(f"  JSON: {len(json_stats['models'])}")
        print(f"  Parquet: {len(parquet_stats['models'])}")
        
        json_models = set(json_stats['models'].keys())
        parquet_models = set(parquet_stats['models'].keys())
        
        if json_models == parquet_models:
            print("  ✅ 模型列表匹配")
            self.results['models_match'] = True
        else:
            only_json = json_models - parquet_models
            only_parquet = parquet_models - json_models
            
            if only_json:
                print(f"  仅在JSON中: {only_json}")
            if only_parquet:
                print(f"  仅在Parquet中: {only_parquet}")
        
        # 比较维度
        print(f"\n📐 数据维度:")
        print(f"  Prompt类型 - JSON: {len(json_stats['prompt_types'])}, Parquet: {len(parquet_stats['prompt_types'])}")
        print(f"  难度级别 - JSON: {len(json_stats['difficulties'])}, Parquet: {len(parquet_stats['difficulties'])}")
        print(f"  任务类型 - JSON: {len(json_stats['task_types'])}, Parquet: {len(parquet_stats['task_types'])}")
        
        # 详细模型对比
        print(f"\n📈 模型测试数对比:")
        common_models = json_models & parquet_models
        
        for model in sorted(common_models):
            json_count = json_stats['models'].get(model, 0)
            parquet_count = parquet_stats['models'].get(model, 0)
            
            if json_count == parquet_count:
                print(f"  ✅ {model}: {json_count}")
            else:
                print(f"  ❌ {model}: JSON={json_count}, Parquet={parquet_count}")
    
    def run_verification(self):
        """运行验证"""
        print("=" * 60)
        print("Parquet和JSON数据一致性验证")
        print("=" * 60)
        
        # 1. 加载数据
        json_data = self.load_json_data()
        parquet_df = self.load_parquet_data()
        
        if not json_data or parquet_df is None:
            print("\n❌ 无法加载数据进行对比")
            return False
        
        # 2. 提取统计
        print("\n📊 提取统计信息...")
        json_stats = self.extract_json_stats(json_data)
        parquet_stats = self.extract_parquet_stats(parquet_df)
        
        # 3. 对比数据
        self.compare_stats(json_stats, parquet_stats)
        
        # 4. 生成报告
        self.generate_report()
        
        return self.results['totals_match'] and self.results['models_match']
    
    def generate_report(self):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("验证报告")
        print("=" * 60)
        
        # 检查各项结果
        all_pass = all(self.results.values())
        
        print("\n✅ 通过项:")
        for key, value in self.results.items():
            if value:
                print(f"  - {key}")
        
        print("\n❌ 失败项:")
        for key, value in self.results.items():
            if not value:
                print(f"  - {key}")
        
        print(f"\n📝 结论:")
        if all_pass:
            print("  ✅ JSON和Parquet数据完全一致")
        elif self.results['json_exists'] and not self.results['parquet_exists']:
            print("  ⚠️ Parquet存储未启用或数据未同步")
            print("  建议：设置STORAGE_FORMAT=parquet并重新运行测试")
        elif self.results['totals_match']:
            print("  ⚠️ 数据基本一致，但有细节差异")
        else:
            print("  ❌ 数据存在不一致，需要同步")
    
    def sync_recommendation(self):
        """同步建议"""
        if not self.results['totals_match']:
            print("\n💡 同步建议:")
            print("  1. 运行 update_summary_totals.py 更新JSON统计")
            print("  2. 设置 STORAGE_FORMAT=parquet 启用Parquet存储")
            print("  3. 运行一次完整测试以同步数据")

def main():
    """主函数"""
    verifier = DataConsistencyVerifier()
    success = verifier.run_verification()
    
    if not success:
        verifier.sync_recommendation()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())