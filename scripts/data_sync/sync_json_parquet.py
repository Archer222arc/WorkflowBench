#!/usr/bin/env python3
"""
JSON和Parquet数据双向同步工具
支持数据清理、验证和同步
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import argparse
import shutil

class DataSyncManager:
    """管理JSON和Parquet数据的同步"""
    
    def __init__(self):
        self.json_path = Path('pilot_bench_cumulative_results/master_database.json')
        self.parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
        self.backup_dir = Path('pilot_bench_cumulative_results/backups')
        self.backup_dir.mkdir(exist_ok=True)
        
    def backup_files(self):
        """备份当前文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 备份JSON
        if self.json_path.exists():
            json_backup = self.backup_dir / f'master_database_{timestamp}.json'
            shutil.copy2(self.json_path, json_backup)
            print(f"✅ 已备份JSON: {json_backup.name}")
            
        # 备份Parquet
        if self.parquet_path.exists():
            parquet_backup = self.backup_dir / f'test_results_{timestamp}.parquet'
            shutil.copy2(self.parquet_path, parquet_backup)
            print(f"✅ 已备份Parquet: {parquet_backup.name}")
    
    def clean_invalid_flawed_records(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理无效的flawed记录（只有flawed而没有具体类型的）"""
        # 找出需要删除的记录
        invalid_mask = df['prompt_type'] == 'flawed'
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            print(f"\n🧹 发现 {invalid_count} 条无效的flawed记录（缺少具体类型）")
            
            # 显示要删除的记录详情
            invalid_records = df[invalid_mask]
            for model in invalid_records['model'].unique():
                model_count = len(invalid_records[invalid_records['model'] == model])
                print(f"  - {model}: {model_count} 条")
            
            # 删除这些记录
            df = df[~invalid_mask].copy()
            print(f"✅ 已删除 {invalid_count} 条无效记录")
        else:
            print("✅ 没有发现无效的flawed记录")
            
        return df
    
    def validate_flawed_types(self, df: pd.DataFrame) -> bool:
        """验证所有flawed记录都有具体类型"""
        valid_flawed_types = [
            'flawed_sequence_disorder',
            'flawed_tool_misuse', 
            'flawed_parameter_error',
            'flawed_missing_step',
            'flawed_redundant_operations',
            'flawed_logical_inconsistency',
            'flawed_semantic_drift'
        ]
        
        # 检查所有包含flawed的记录
        flawed_records = df[df['prompt_type'].str.contains('flawed', na=False)]
        
        # 验证每条记录
        invalid_types = []
        for prompt_type in flawed_records['prompt_type'].unique():
            if prompt_type == 'flawed' or prompt_type not in valid_flawed_types:
                if prompt_type != 'flawed':  # 已经处理过的情况
                    invalid_types.append(prompt_type)
        
        if invalid_types:
            print(f"⚠️ 发现未知的flawed类型: {invalid_types}")
            return False
        
        print(f"✅ 所有 {len(flawed_records)} 条flawed记录类型验证通过")
        return True
    
    def parquet_to_json(self, clean_data: bool = True) -> Dict:
        """从Parquet转换到JSON格式"""
        if not self.parquet_path.exists():
            print("❌ Parquet文件不存在")
            return None
            
        print("\n📖 读取Parquet数据...")
        df = pd.read_parquet(self.parquet_path)
        print(f"  读取 {len(df)} 条记录")
        
        # 清理无效数据
        if clean_data:
            df = self.clean_invalid_flawed_records(df)
            self.validate_flawed_types(df)
        
        # 构建JSON结构
        print("\n🔄 转换为JSON格式...")
        json_data = {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "models": {},
            "test_groups": {},
            "summary": {
                "total_tests": 0,
                "total_success": 0,
                "total_partial": 0,
                "total_failure": 0,
                "models_tested": [],
                "last_test_time": None
            }
        }
        
        # 处理每条记录
        for _, row in df.iterrows():
            model = row['model']
            prompt_type = row['prompt_type']
            tool_rate = str(row['tool_success_rate'])
            difficulty = row['difficulty']
            task_type = row['task_type']
            
            # 初始化模型结构
            if model not in json_data['models']:
                json_data['models'][model] = {
                    'overall_stats': {},
                    'experiment_metrics': {},
                    'by_prompt_type': {}
                }
            
            # 初始化层次结构
            model_data = json_data['models'][model]
            if prompt_type not in model_data['by_prompt_type']:
                model_data['by_prompt_type'][prompt_type] = {
                    'by_tool_success_rate': {}
                }
            
            prompt_data = model_data['by_prompt_type'][prompt_type]
            if tool_rate not in prompt_data['by_tool_success_rate']:
                prompt_data['by_tool_success_rate'][tool_rate] = {
                    'by_difficulty': {}
                }
            
            rate_data = prompt_data['by_tool_success_rate'][tool_rate]
            if difficulty not in rate_data['by_difficulty']:
                rate_data['by_difficulty'][difficulty] = {
                    'by_task_type': {}
                }
            
            diff_data = rate_data['by_difficulty'][difficulty]
            
            # 存储任务数据
            task_data = {
                'total': int(row.get('total', 0)),
                'successful': int(row.get('success', 0)),
                'partial': int(row.get('partial_success', 0)),
                'failed': int(row.get('total', 0) - row.get('success', 0) - row.get('partial_success', 0)),
                'success_rate': float(row.get('success_rate', 0)),
                'partial_rate': float(row.get('partial_rate', 0)),
                'failure_rate': float(row.get('failure_rate', 0)),
                'weighted_success_score': float(row.get('weighted_success_score', 0)),
                'avg_execution_time': float(row.get('avg_execution_time', 0)),
                'avg_turns': float(row.get('avg_turns', 0)),
                'avg_tool_calls': float(row.get('avg_tool_calls', 0)),
                'tool_coverage_rate': float(row.get('tool_coverage_rate', 0))
            }
            
            diff_data['by_task_type'][task_type] = task_data
            
            # 更新汇总
            json_data['summary']['total_tests'] += task_data['total']
            json_data['summary']['total_success'] += task_data['successful']
            json_data['summary']['total_partial'] += task_data['partial']
            json_data['summary']['total_failure'] += task_data['failed']
        
        json_data['summary']['models_tested'] = list(json_data['models'].keys())
        json_data['summary']['last_test_time'] = datetime.now().isoformat()
        
        print(f"✅ 转换完成: {len(json_data['models'])} 个模型")
        return json_data
    
    def json_to_parquet(self, clean_data: bool = True) -> pd.DataFrame:
        """从JSON转换到Parquet格式"""
        if not self.json_path.exists():
            print("❌ JSON文件不存在")
            return None
            
        print("\n📖 读取JSON数据...")
        with open(self.json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        records = []
        
        # 遍历JSON结构提取记录
        for model_name, model_data in json_data.get('models', {}).items():
            for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
                for tool_rate, rate_data in prompt_data.get('by_tool_success_rate', {}).items():
                    for difficulty, diff_data in rate_data.get('by_difficulty', {}).items():
                        for task_type, task_data in diff_data.get('by_task_type', {}).items():
                            
                            # 跳过无效的flawed记录
                            if clean_data and prompt_type == 'flawed':
                                print(f"  跳过无效记录: {model_name}/{prompt_type}")
                                continue
                            
                            record = {
                                'model': model_name,
                                'prompt_type': prompt_type,
                                'tool_success_rate': float(tool_rate),
                                'difficulty': difficulty,
                                'task_type': task_type,
                                'total': task_data.get('total', 0),
                                'success': task_data.get('successful', 0),
                                'full_success': task_data.get('successful', 0) - task_data.get('partial', 0),
                                'partial_success': task_data.get('partial', 0),
                                'success_rate': task_data.get('success_rate', 0),
                                'partial_rate': task_data.get('partial_rate', 0),
                                'failure_rate': task_data.get('failure_rate', 0),
                                'weighted_success_score': task_data.get('weighted_success_score', 0),
                                'avg_execution_time': task_data.get('avg_execution_time', 0),
                                'avg_turns': task_data.get('avg_turns', 0),
                                'avg_tool_calls': task_data.get('avg_tool_calls', 0),
                                'tool_coverage_rate': task_data.get('tool_coverage_rate', 0),
                                'last_updated': datetime.now().isoformat()
                            }
                            records.append(record)
        
        df = pd.DataFrame(records)
        print(f"✅ 转换完成: {len(df)} 条记录")
        
        if clean_data:
            df = self.clean_invalid_flawed_records(df)
            self.validate_flawed_types(df)
        
        return df
    
    def sync_parquet_to_json(self, clean: bool = True):
        """同步Parquet数据到JSON"""
        print("\n=== 同步Parquet → JSON ===")
        
        # 备份
        self.backup_files()
        
        # 转换
        json_data = self.parquet_to_json(clean_data=clean)
        if json_data:
            # 保存JSON
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"✅ 已保存到: {self.json_path}")
    
    def sync_json_to_parquet(self, clean: bool = True):
        """同步JSON数据到Parquet"""
        print("\n=== 同步JSON → Parquet ===")
        
        # 备份
        self.backup_files()
        
        # 转换
        df = self.json_to_parquet(clean_data=clean)
        if df is not None and len(df) > 0:
            # 保存Parquet
            df.to_parquet(self.parquet_path, index=False)
            print(f"✅ 已保存到: {self.parquet_path}")
    
    def bidirectional_sync(self, primary: str = 'parquet', clean: bool = True):
        """双向同步，指定主数据源"""
        print(f"\n{'='*60}")
        print(f"双向同步: 主数据源={primary.upper()}")
        print(f"{'='*60}")
        
        if primary == 'parquet':
            self.sync_parquet_to_json(clean=clean)
        elif primary == 'json':
            self.sync_json_to_parquet(clean=clean)
        else:
            print("❌ 无效的主数据源，请选择 'parquet' 或 'json'")
    
    def show_statistics(self):
        """显示数据统计"""
        print(f"\n{'='*60}")
        print("数据统计")
        print(f"{'='*60}")
        
        # Parquet统计
        if self.parquet_path.exists():
            df = pd.read_parquet(self.parquet_path)
            print(f"\n📊 Parquet数据:")
            print(f"  总记录数: {len(df)}")
            print(f"  模型数: {df['model'].nunique()}")
            print(f"  Prompt类型数: {df['prompt_type'].nunique()}")
            
            # 检查无效记录
            invalid_flawed = df[df['prompt_type'] == 'flawed']
            if len(invalid_flawed) > 0:
                print(f"  ⚠️ 无效flawed记录: {len(invalid_flawed)}")
        
        # JSON统计
        if self.json_path.exists():
            with open(self.json_path, 'r') as f:
                json_data = json.load(f)
            
            total_records = 0
            invalid_count = 0
            
            for model_data in json_data.get('models', {}).values():
                for prompt_type, prompt_data in model_data.get('by_prompt_type', {}).items():
                    if prompt_type == 'flawed':
                        invalid_count += 1
                    for rate_data in prompt_data.get('by_tool_success_rate', {}).values():
                        for diff_data in rate_data.get('by_difficulty', {}).values():
                            total_records += len(diff_data.get('by_task_type', {}))
            
            print(f"\n📊 JSON数据:")
            print(f"  总记录数: {total_records}")
            print(f"  模型数: {len(json_data.get('models', {}))}")
            if invalid_count > 0:
                print(f"  ⚠️ 无效flawed记录: {invalid_count}")

def main():
    parser = argparse.ArgumentParser(description='JSON和Parquet数据同步工具')
    parser.add_argument('action', choices=['sync', 'clean', 'stats', 'p2j', 'j2p'],
                       help='操作: sync(双向同步), clean(清理并同步), stats(统计), p2j(Parquet转JSON), j2p(JSON转Parquet)')
    parser.add_argument('--primary', choices=['parquet', 'json'], default='parquet',
                       help='主数据源 (默认: parquet)')
    parser.add_argument('--no-clean', action='store_true',
                       help='不清理无效数据')
    
    args = parser.parse_args()
    
    manager = DataSyncManager()
    clean = not args.no_clean
    
    if args.action == 'sync':
        manager.bidirectional_sync(primary=args.primary, clean=clean)
    elif args.action == 'clean':
        # 强制清理并同步
        manager.bidirectional_sync(primary=args.primary, clean=True)
    elif args.action == 'stats':
        manager.show_statistics()
    elif args.action == 'p2j':
        manager.sync_parquet_to_json(clean=clean)
    elif args.action == 'j2p':
        manager.sync_json_to_parquet(clean=clean)
    
    print("\n✅ 操作完成！")

if __name__ == "__main__":
    main()