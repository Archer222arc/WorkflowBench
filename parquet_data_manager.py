#!/usr/bin/env python3
"""
基于Parquet的数据管理系统
解决并发写入和数据丢失问题
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import hashlib
from typing import Dict, List, Optional, Any
import threading
import time
import pyarrow as pa
import pyarrow.parquet as pq
from contextlib import contextmanager
import fcntl
import os

class ParquetDataManager:
    """
    使用Parquet格式管理测试数据
    优势：
    1. 支持增量写入（append模式）
    2. 列式存储，查询效率高
    3. 支持schema evolution
    4. 自带数据压缩
    5. 支持并发读取
    """
    
    def __init__(self, data_dir: Path = None):
        """初始化Parquet数据管理器"""
        self.data_dir = Path(data_dir or "pilot_bench_parquet_data")
        self.data_dir.mkdir(exist_ok=True)
        
        # 不同类型数据的存储路径
        self.test_results_path = self.data_dir / "test_results.parquet"
        self.model_stats_path = self.data_dir / "model_stats.parquet"
        self.incremental_dir = self.data_dir / "incremental"  # 增量数据目录
        self.incremental_dir.mkdir(exist_ok=True)
        
        # 写入锁（每个进程一个唯一的增量文件，避免冲突）
        self.process_id = f"{os.getpid()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def append_summary_record(self, summary_data: Dict) -> bool:
        """
        直接追加汇总记录到主文件
        不存储单个测试记录
        """
        try:
            # 确保包含所有必要的汇总字段
            required_fields = {
                # 基本信息
                'model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type',
                # 核心统计
                'total', 'success', 'full_success', 'partial_success',
                # 兼容性字段（successful/partial/failed是success/partial_success/failed的别名）
                'successful', 'partial', 'failed',
                # 成功率字段
                'success_rate', 'full_success_rate', 'partial_success_rate', 'partial_rate',
                'failure_rate', 'weighted_success_score',
                # 执行指标
                'avg_execution_time', 'avg_turns', 'avg_tool_calls', 'tool_coverage_rate',
                # 质量分数
                'avg_workflow_score', 'avg_phase2_score', 'avg_quality_score', 'avg_final_score',
                # 错误统计
                'total_errors', 'tool_call_format_errors', 'timeout_errors', 'dependency_errors',
                'parameter_config_errors', 'tool_selection_errors', 'sequence_order_errors',
                'max_turns_errors', 'other_errors',
                # 错误率
                'tool_selection_error_rate', 'parameter_error_rate', 'sequence_error_rate',
                'dependency_error_rate', 'timeout_error_rate', 'format_error_rate',
                'max_turns_error_rate', 'other_error_rate',
                # 辅助统计
                'assisted_failure', 'assisted_success', 'total_assisted_turns',
                'tests_with_assistance', 'avg_assisted_turns', 'assisted_success_rate',
                'assistance_rate'
            }
            
            # 添加默认值
            for field in required_fields:
                if field not in summary_data:
                    if 'rate' in field or 'avg' in field or 'score' in field:
                        summary_data[field] = 0.0
                    elif field in ['model', 'prompt_type', 'difficulty', 'task_type']:
                        summary_data[field] = summary_data.get(field, 'unknown')
                    else:
                        summary_data[field] = 0
            
            # 添加时间戳
            summary_data['last_updated'] = datetime.now().isoformat()
            
            # Debug: 检查接收到的数据
            if summary_data.get('total_errors', 0) > 0:
                print(f"[PARQUET_WRITE_DEBUG] Received data for {summary_data.get('model')}-{summary_data.get('task_type')}:")
                print(f"  sequence_order_errors={summary_data.get('sequence_order_errors', 0)}")
                print(f"  dependency_errors={summary_data.get('dependency_errors', 0)}")
                print(f"  other_errors={summary_data.get('other_errors', 0)}")
            
            # 创建DataFrame
            df = pd.DataFrame([summary_data])
            
            # 使用文件锁保护读写操作
            lock_file = str(self.test_results_path) + '.lock'
            max_retries = 10
            retry_delay = 0.5
            
            for attempt in range(max_retries):
                try:
                    with open(lock_file, 'w') as lock_fd:
                        # 获取独占锁
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                        
                        try:
                            # 读取现有主文件（如果存在）
                            if self.test_results_path.exists():
                                try:
                                    existing_df = pd.read_parquet(self.test_results_path)
                                except Exception as read_error:
                                    # 文件可能损坏，尝试从备份恢复
                                    print(f"[WARNING] 主文件损坏: {read_error}")
                                    backup_files = sorted(self.base_dir.glob("test_results_backup_*.parquet"))
                                    if backup_files:
                                        print(f"[INFO] 尝试从备份恢复: {backup_files[-1]}")
                                        existing_df = pd.read_parquet(backup_files[-1])
                                    else:
                                        print("[INFO] 没有可用备份，创建新文件")
                                        existing_df = pd.DataFrame()
                                
                                if not existing_df.empty:
                                    # 创建唯一键
                                    key_cols = ['model', 'prompt_type', 'tool_success_rate', 'difficulty', 'task_type']
                                    df['_key'] = df[key_cols].apply(lambda x: '|'.join(map(str, x)), axis=1)
                                    existing_df['_key'] = existing_df[key_cols].apply(lambda x: '|'.join(map(str, x)), axis=1)
                                    
                                    # 更新或添加记录
                                    key = df['_key'].iloc[0]
                                    if key in existing_df['_key'].values:
                                        # 更新现有记录 - 需要累加某些字段而不是覆盖
                                        idx = existing_df[existing_df['_key'] == key].index[0]
                                        
                                        # 需要累加的计数字段
                                        accumulate_fields = {
                                            'total', 'success', 'full_success', 'partial_success', 'partial',
                                            'failed', 'successful',
                                            'total_errors', 'tool_call_format_errors', 'timeout_errors',
                                            'dependency_errors', 'parameter_config_errors', 'tool_selection_errors',
                                            'sequence_order_errors', 'max_turns_errors', 'other_errors',
                                            'assisted_failure', 'assisted_success', 'total_assisted_turns',
                                            'tests_with_assistance',
                                            # 内部累加器字段（以_开头的）也需要累加
                                            '_total_execution_time', '_total_turns', '_total_tool_calls',
                                            '_total_tool_coverage', '_total_workflow_score', '_total_phase2_score',
                                            '_total_quality_score', '_total_final_score'
                                        }
                                        
                                        for col in df.columns:
                                            if col == '_key':
                                                continue
                                            elif col in accumulate_fields:
                                                # 累加计数字段
                                                old_val = existing_df.loc[idx, col] if col in existing_df.columns else 0
                                                new_val = df[col].iloc[0]
                                                existing_df.loc[idx, col] = old_val + new_val
                                                if col.endswith('_errors'):
                                                    print(f"[PARQUET_DEBUG] 累加 {col}: {old_val} + {new_val} = {old_val + new_val}")
                                            elif col in ['avg_execution_time', 'avg_turns', 'avg_tool_calls', 
                                                        'tool_coverage_rate', 'avg_workflow_score', 'avg_phase2_score',
                                                        'avg_quality_score', 'avg_final_score']:
                                                # 平均值字段需要重新计算（使用新的总数）
                                                # 这里简单地使用新值，因为flush时已经计算好了平均值
                                                existing_df.loc[idx, col] = df[col].iloc[0]
                                            elif col.endswith('_rate'):
                                                # 率字段也使用新值（flush时已经重新计算）
                                                existing_df.loc[idx, col] = df[col].iloc[0]
                                            else:
                                                # 其他字段（如last_updated）使用新值
                                                existing_df.loc[idx, col] = df[col].iloc[0]
                                        final_df = existing_df
                                    else:
                                        # 添加新记录
                                        final_df = pd.concat([existing_df, df], ignore_index=True)
                                    
                                    # 删除临时键
                                    final_df = final_df.drop(columns=['_key'])
                                else:
                                    final_df = df
                            else:
                                final_df = df
                            
                            # 保存前创建备份
                            if self.test_results_path.exists():
                                backup_path = self.data_dir / f"test_results_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
                                import shutil
                                shutil.copy2(self.test_results_path, backup_path)
                            
                            # 保存
                            final_df.to_parquet(self.test_results_path, index=False)
                            
                        finally:
                            # 释放锁
                            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    
                    # 成功则退出循环
                    break
                    
                except IOError as e:
                    if attempt < max_retries - 1:
                        print(f"[WARNING] 获取文件锁失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"无法获取文件锁: {e}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 追加汇总记录失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def append_test_result(self, test_data: Dict) -> bool:
        """
        兼容旧接口，但实际不存储单个测试记录
        """
        # 不做任何操作，因为我们只存储汇总
        return True
    
    def batch_append_results(self, test_results: List[Dict]) -> bool:
        """批量追加测试结果"""
        try:
            # 添加元数据
            for result in test_results:
                result['timestamp'] = datetime.now().isoformat()
                result['process_id'] = self.process_id
            
            # 创建DataFrame
            df = pd.DataFrame(test_results)
            
            # 写入增量文件
            incremental_file = self.incremental_dir / f"increment_{self.process_id}.parquet"
            
            if incremental_file.exists():
                existing_df = pd.read_parquet(incremental_file)
                df = pd.concat([existing_df, df], ignore_index=True)
            
            df.to_parquet(incremental_file, index=False)
            return True
            
        except Exception as e:
            print(f"[ERROR] 批量追加失败: {e}")
            return False
    
    def consolidate_incremental_data(self) -> bool:
        """
        兼容旧接口，但不再需要合并（因为不存储单个记录）
        """
        # 清理任何遗留的增量文件
        incremental_files = list(self.incremental_dir.glob("increment_*.parquet"))
        for file in incremental_files:
            try:
                file.unlink()
            except:
                pass
        
        return True
    
    def query_model_stats(self, model_name: str = None, 
                          prompt_type: str = None,
                          tool_success_rate: float = None) -> pd.DataFrame:
        """
        查询模型统计数据
        先合并增量数据，再查询
        """
        # 先合并增量数据
        self.consolidate_incremental_data()
        
        if not self.test_results_path.exists():
            return pd.DataFrame()
        
        # 读取数据
        df = pd.read_parquet(self.test_results_path)
        
        # 应用过滤条件
        if model_name:
            df = df[df['model'] == model_name]
        if prompt_type:
            df = df[df['prompt_type'] == prompt_type]
        if tool_success_rate is not None:
            df = df[df['tool_success_rate'] == tool_success_rate]
        
        return df
    
    def compute_statistics(self, df: pd.DataFrame) -> Dict:
        """计算统计数据"""
        if df.empty:
            return {}
        
        # 检查是否是汇总数据（包含total字段）
        is_summary_data = 'total' in df.columns
        
        if is_summary_data:
            # 处理汇总数据：累加各个汇总的总数
            total_tests = df['total'].sum() if 'total' in df else 0
            success_count = df['success'].sum() if 'success' in df else 0
            # 加权平均成功率
            if total_tests > 0:
                success_rate = success_count / total_tests
            else:
                success_rate = 0
            # 加权平均执行时间
            if 'avg_execution_time' in df and total_tests > 0:
                avg_execution_time = (df['avg_execution_time'] * df['total']).sum() / total_tests
            else:
                avg_execution_time = 0
        else:
            # 处理原始数据（兼容旧代码）
            total_tests = len(df)
            success_count = df['success'].sum() if 'success' in df else 0
            success_rate = df['success'].mean() if 'success' in df else 0
            avg_execution_time = df['execution_time'].mean() if 'execution_time' in df else 0
        
        stats = {
            'total_tests': int(total_tests),
            'success_count': int(success_count),
            'success_rate': float(success_rate),
            'avg_execution_time': float(avg_execution_time),
            'models': df['model'].unique().tolist() if 'model' in df else [],
            'prompt_types': df['prompt_type'].unique().tolist() if 'prompt_type' in df else []
        }
        
        # 按模型分组统计
        if 'model' in df and is_summary_data:
            model_stats = {}
            for model in df['model'].unique():
                model_df = df[df['model'] == model]
                model_total = model_df['total'].sum()
                model_success = model_df['success'].sum() if 'success' in model_df else 0
                model_stats[model] = {
                    'total': int(model_total),
                    'success': int(model_success),
                    'success_rate': float(model_success / model_total) if model_total > 0 else 0
                }
            stats['by_model'] = model_stats
        elif 'model' in df:
            # 原始数据的分组统计（兼容）
            model_stats = df.groupby('model').agg({
                'success': ['count', 'sum', 'mean'],
                'execution_time': 'mean'
            }).to_dict()
            stats['by_model'] = model_stats
        
        return stats
    
    def export_to_json(self, output_path: Path = None) -> bool:
        """
        导出数据为JSON格式（用于兼容性）
        """
        try:
            # 合并增量数据
            self.consolidate_incremental_data()
            
            if not self.test_results_path.exists():
                print("没有数据可导出")
                return False
            
            # 读取所有数据
            df = pd.read_parquet(self.test_results_path)
            
            # 转换为层次化JSON结构
            json_data = self._build_hierarchical_json(df)
            
            # 保存
            output_path = output_path or self.data_dir / "export.json"
            with open(output_path, 'w') as f:
                json.dump(json_data, f, indent=2, default=str)
            
            print(f"✅ 导出到: {output_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] 导出失败: {e}")
            return False
    
    def _build_hierarchical_json(self, df: pd.DataFrame) -> Dict:
        """构建层次化的JSON结构"""
        result = {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "models": {},
            "summary": self.compute_statistics(df)
        }
        
        # 按模型分组
        for model in df['model'].unique():
            model_df = df[df['model'] == model]
            result['models'][model] = {
                'overall_stats': self.compute_statistics(model_df),
                'by_prompt_type': {}
            }
            
            # 按prompt_type分组
            for prompt_type in model_df['prompt_type'].unique():
                prompt_df = model_df[model_df['prompt_type'] == prompt_type]
                result['models'][model]['by_prompt_type'][prompt_type] = {
                    'stats': self.compute_statistics(prompt_df),
                    'by_tool_success_rate': {}
                }
                
                # 继续嵌套...（按需要的层次结构）
        
        return result
    
    def migrate_from_json(self, json_path: Path) -> bool:
        """
        从JSON格式迁移数据到Parquet
        """
        try:
            print(f"从JSON迁移数据: {json_path}")
            
            with open(json_path, 'r') as f:
                json_data = json.load(f)
            
            # 展平JSON数据为表格格式
            records = []
            
            for model_name, model_data in json_data.get('models', {}).items():
                if 'by_prompt_type' in model_data:
                    for prompt_type, prompt_data in model_data['by_prompt_type'].items():
                        if 'by_tool_success_rate' in prompt_data:
                            for rate, rate_data in prompt_data['by_tool_success_rate'].items():
                                if 'by_difficulty' in rate_data:
                                    for diff, diff_data in rate_data['by_difficulty'].items():
                                        if 'by_task_type' in diff_data:
                                            for task, task_data in diff_data['by_task_type'].items():
                                                # 创建完整的汇总记录，包含所有JSON字段
                                                record = {
                                                    # 基本信息
                                                    'model': model_name,
                                                    'prompt_type': prompt_type,
                                                    'tool_success_rate': float(rate),
                                                    'difficulty': diff,
                                                    'task_type': task,
                                                    # 核心统计
                                                    'total': task_data.get('total', 0),
                                                    'success': task_data.get('success', 0),
                                                    'full_success': task_data.get('full_success', 0),
                                                    'partial_success': task_data.get('partial_success', 0),
                                                    'success_rate': task_data.get('success_rate', 0),
                                                    'full_success_rate': task_data.get('full_success_rate', 0),
                                                    'partial_success_rate': task_data.get('partial_success_rate', 0),
                                                    'failure_rate': task_data.get('failure_rate', 0),
                                                    'weighted_success_score': task_data.get('weighted_success_score', 0),
                                                    # 执行指标
                                                    'avg_execution_time': task_data.get('avg_execution_time', 0),
                                                    'avg_turns': task_data.get('avg_turns', 0),
                                                    'avg_tool_calls': task_data.get('avg_tool_calls', 0),
                                                    'tool_coverage_rate': task_data.get('tool_coverage_rate', 0),
                                                    # 质量分数
                                                    'avg_workflow_score': task_data.get('avg_workflow_score', 0),
                                                    'avg_phase2_score': task_data.get('avg_phase2_score', 0),
                                                    'avg_quality_score': task_data.get('avg_quality_score', 0),
                                                    'avg_final_score': task_data.get('avg_final_score', 0),
                                                    # 错误统计
                                                    'total_errors': task_data.get('total_errors', 0),
                                                    'tool_call_format_errors': task_data.get('tool_call_format_errors', 0),
                                                    'timeout_errors': task_data.get('timeout_errors', 0),
                                                    'dependency_errors': task_data.get('dependency_errors', 0),
                                                    'parameter_config_errors': task_data.get('parameter_config_errors', 0),
                                                    'tool_selection_errors': task_data.get('tool_selection_errors', 0),
                                                    'sequence_order_errors': task_data.get('sequence_order_errors', 0),
                                                    'max_turns_errors': task_data.get('max_turns_errors', 0),
                                                    'other_errors': task_data.get('other_errors', 0),
                                                    # 错误率
                                                    'tool_selection_error_rate': task_data.get('tool_selection_error_rate', 0),
                                                    'parameter_error_rate': task_data.get('parameter_error_rate', 0),
                                                    'sequence_error_rate': task_data.get('sequence_error_rate', 0),
                                                    'dependency_error_rate': task_data.get('dependency_error_rate', 0),
                                                    'timeout_error_rate': task_data.get('timeout_error_rate', 0),
                                                    'format_error_rate': task_data.get('format_error_rate', 0),
                                                    'max_turns_error_rate': task_data.get('max_turns_error_rate', 0),
                                                    'other_error_rate': task_data.get('other_error_rate', 0),
                                                    # 辅助统计
                                                    'assisted_failure': task_data.get('assisted_failure', 0),
                                                    'assisted_success': task_data.get('assisted_success', 0),
                                                    'total_assisted_turns': task_data.get('total_assisted_turns', 0),
                                                    'tests_with_assistance': task_data.get('tests_with_assistance', 0),
                                                    'avg_assisted_turns': task_data.get('avg_assisted_turns', 0),
                                                    'assisted_success_rate': task_data.get('assisted_success_rate', 0),
                                                    'assistance_rate': task_data.get('assistance_rate', 0),
                                                    # 元数据
                                                    'imported_from_json': True,
                                                    'import_time': datetime.now().isoformat()
                                                }
                                                records.append(record)
            
            if records:
                # 创建DataFrame并保存
                df = pd.DataFrame(records)
                df.to_parquet(self.test_results_path, index=False)
                print(f"✅ 成功迁移 {len(records)} 条记录")
                return True
            else:
                print("没有找到可迁移的数据")
                return False
                
        except Exception as e:
            print(f"[ERROR] 迁移失败: {e}")
            return False
    
    def create_backup(self) -> Path:
        """创建数据备份"""
        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"backup_{timestamp}"
        backup_path.mkdir()
        
        # 复制所有parquet文件
        import shutil
        for file in self.data_dir.glob("*.parquet"):
            shutil.copy2(file, backup_path / file.name)
        
        # 复制增量文件
        incremental_backup = backup_path / "incremental"
        incremental_backup.mkdir()
        for file in self.incremental_dir.glob("*.parquet"):
            shutil.copy2(file, incremental_backup / file.name)
        
        print(f"✅ 备份创建: {backup_path}")
        return backup_path


class SafeWriteManager:
    """
    安全写入管理器
    确保即使进程被中断，数据也不会丢失
    """
    
    def __init__(self, manager: ParquetDataManager):
        self.manager = manager
        self.pending_writes = []
        self.write_lock = threading.Lock()
        
    @contextmanager
    def safe_write_context(self):
        """
        安全写入上下文
        确保数据写入完成或回滚
        """
        transaction_id = hashlib.md5(
            f"{os.getpid()}_{time.time()}".encode()
        ).hexdigest()[:8]
        
        transaction_file = self.manager.data_dir / f"transaction_{transaction_id}.tmp"
        
        try:
            yield self
            
            # 写入成功，删除事务文件
            if transaction_file.exists():
                transaction_file.unlink()
                
        except Exception as e:
            print(f"[ERROR] 事务失败: {e}")
            # 保存未完成的数据到事务文件
            if self.pending_writes:
                pd.DataFrame(self.pending_writes).to_parquet(transaction_file)
                print(f"[INFO] 未完成数据已保存到: {transaction_file}")
            raise
        
        finally:
            self.pending_writes.clear()
    
    def add_pending_write(self, data: Dict):
        """添加待写入数据"""
        with self.write_lock:
            self.pending_writes.append(data)
    
    def flush_pending_writes(self) -> bool:
        """刷新所有待写入数据"""
        if not self.pending_writes:
            return True
        
        with self.write_lock:
            success = self.manager.batch_append_results(self.pending_writes)
            if success:
                self.pending_writes.clear()
            return success
    
    def recover_transactions(self) -> int:
        """
        恢复未完成的事务
        返回恢复的记录数
        """
        recovered = 0
        transaction_files = list(self.manager.data_dir.glob("transaction_*.tmp"))
        
        for trans_file in transaction_files:
            try:
                df = pd.read_parquet(trans_file)
                records = df.to_dict('records')
                
                if self.manager.batch_append_results(records):
                    recovered += len(records)
                    trans_file.unlink()
                    print(f"✅ 恢复事务: {trans_file.name} ({len(records)}条记录)")
                    
            except Exception as e:
                print(f"[WARNING] 恢复事务失败 {trans_file}: {e}")
        
        return recovered


if __name__ == "__main__":
    # 测试代码
    print("Parquet数据管理系统测试")
    print("="*60)
    
    manager = ParquetDataManager()
    
    # 测试追加数据
    test_data = {
        'model': 'gpt-4o-mini',
        'task_type': 'simple_task',
        'prompt_type': 'baseline',
        'success': True,
        'execution_time': 2.5,
        'tool_success_rate': 0.8
    }
    
    print("\n1. 测试数据追加...")
    if manager.append_test_result(test_data):
        print("✅ 追加成功")
    
    # 测试查询
    print("\n2. 测试数据查询...")
    df = manager.query_model_stats(model_name='gpt-4o-mini')
    print(f"查询结果: {len(df)} 条记录")
    
    # 测试统计
    print("\n3. 测试统计计算...")
    stats = manager.compute_statistics(df)
    print(f"统计结果: {stats}")
    
    # 测试安全写入
    print("\n4. 测试安全写入...")
    safe_manager = SafeWriteManager(manager)
    
    with safe_manager.safe_write_context():
        safe_manager.add_pending_write(test_data)
        safe_manager.flush_pending_writes()
    
    print("\n✅ 所有测试完成！")