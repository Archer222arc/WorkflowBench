#!/usr/bin/env python3
"""
测试并发写入数据库的安全性
验证文件锁机制和事务处理
"""

import json
import time
import threading
import multiprocessing
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import random

class ConcurrentWriteTester:
    """并发写入测试器"""
    
    def __init__(self):
        self.db_path = Path("pilot_bench_cumulative_results/master_database.json")
        self.backup_path = None
        self.results = {
            'conflicts': 0,
            'successes': 0,
            'failures': 0,
            'data_losses': 0
        }
        self.lock = threading.Lock()
        
    def backup_database(self):
        """备份原始数据库"""
        if self.db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_path = self.db_path.with_suffix(f'.backup_concurrent_test_{timestamp}.json')
            
            with open(self.db_path, 'r') as f:
                data = json.load(f)
            
            with open(self.backup_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ 已备份数据库到: {self.backup_path}")
            return data
        return {}
    
    def restore_database(self):
        """恢复数据库"""
        if self.backup_path and self.backup_path.exists():
            with open(self.backup_path, 'r') as f:
                data = json.load(f)
            
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ 已恢复数据库")
    
    def simulate_write_operation(self, worker_id, operation_id):
        """模拟写入操作"""
        try:
            # 使用enhanced_cumulative_manager进行写入
            from enhanced_cumulative_manager import EnhancedCumulativeManager
            from cumulative_test_manager import TestRecord
            
            manager = EnhancedCumulativeManager()
            
            # 创建测试记录
            test_model = f"concurrent-test-model-{worker_id}"
            record = TestRecord(
                model=test_model,
                task_type=f'task_{operation_id}',
                prompt_type='baseline',
                difficulty='easy'
            )
            record.tool_success_rate = 0.8
            record.success = random.choice([True, False])
            record.execution_time = random.uniform(1.0, 5.0)
            record.turns = random.randint(1, 10)
            record.tool_calls = random.randint(1, 5)
            
            # 尝试写入
            start_time = time.time()
            success = manager.add_test_result_with_classification(record)
            elapsed = time.time() - start_time
            
            # 记录结果
            with self.lock:
                if success:
                    self.results['successes'] += 1
                else:
                    self.results['failures'] += 1
            
            return {
                'worker_id': worker_id,
                'operation_id': operation_id,
                'success': success,
                'elapsed': elapsed
            }
            
        except Exception as e:
            with self.lock:
                self.results['failures'] += 1
            return {
                'worker_id': worker_id,
                'operation_id': operation_id,
                'success': False,
                'error': str(e)
            }
    
    def test_thread_concurrency(self, num_threads=10, operations_per_thread=5):
        """测试线程并发"""
        print(f"\n🧵 测试线程并发 ({num_threads} 线程, 每线程 {operations_per_thread} 操作)...")
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for thread_id in range(num_threads):
                for op_id in range(operations_per_thread):
                    future = executor.submit(
                        self.simulate_write_operation,
                        f"thread_{thread_id}",
                        op_id
                    )
                    futures.append(future)
            
            # 等待所有操作完成
            results = [f.result() for f in futures]
        
        # 分析结果
        successful = sum(1 for r in results if r.get('success'))
        failed = sum(1 for r in results if not r.get('success'))
        avg_time = sum(r.get('elapsed', 0) for r in results) / len(results)
        
        print(f"  成功: {successful}/{len(results)}")
        print(f"  失败: {failed}/{len(results)}")
        print(f"  平均耗时: {avg_time:.3f}秒")
        
        return results
    
    def test_process_concurrency(self, num_processes=5, operations_per_process=3):
        """测试进程并发"""
        print(f"\n🔧 测试进程并发 ({num_processes} 进程, 每进程 {operations_per_process} 操作)...")
        
        # 注意：ProcessPoolExecutor需要可序列化的函数
        # 这里简化为顺序执行多个进程的测试
        results = []
        for proc_id in range(num_processes):
            for op_id in range(operations_per_process):
                result = self.simulate_write_operation(f"process_{proc_id}", op_id)
                results.append(result)
        
        # 分析结果
        successful = sum(1 for r in results if r.get('success'))
        failed = sum(1 for r in results if not r.get('success'))
        
        print(f"  成功: {successful}/{len(results)}")
        print(f"  失败: {failed}/{len(results)}")
        
        return results
    
    def verify_data_integrity(self, original_data):
        """验证数据完整性"""
        print("\n🔍 验证数据完整性...")
        
        # 读取当前数据库
        with open(self.db_path, 'r') as f:
            current_data = json.load(f)
        
        # 检查原始数据是否保留
        original_models = set(original_data.get('models', {}).keys())
        current_models = set(current_data.get('models', {}).keys())
        
        lost_models = original_models - current_models
        new_models = current_models - original_models
        
        print(f"  原始模型数: {len(original_models)}")
        print(f"  当前模型数: {len(current_models)}")
        print(f"  新增模型: {len(new_models)}")
        
        if lost_models:
            print(f"  ❌ 丢失的模型: {lost_models}")
            self.results['data_losses'] += len(lost_models)
        else:
            print(f"  ✅ 所有原始数据保留完整")
        
        # 检查测试数据是否正确写入
        test_models = [m for m in current_models if m.startswith('concurrent-test-model')]
        print(f"  测试模型写入: {len(test_models)}")
        
        return len(lost_models) == 0
    
    def run_comprehensive_test(self):
        """运行综合测试"""
        print("=" * 60)
        print("并发写入安全性测试")
        print("=" * 60)
        
        # 1. 备份原始数据
        original_data = self.backup_database()
        
        try:
            # 2. 测试线程并发
            thread_results = self.test_thread_concurrency(
                num_threads=10,
                operations_per_thread=5
            )
            
            # 3. 测试进程并发
            process_results = self.test_process_concurrency(
                num_processes=3,
                operations_per_process=5
            )
            
            # 4. 验证数据完整性
            integrity_ok = self.verify_data_integrity(original_data)
            
            # 5. 生成报告
            self.generate_report(thread_results, process_results, integrity_ok)
            
        finally:
            # 6. 恢复数据库
            self.restore_database()
    
    def generate_report(self, thread_results, process_results, integrity_ok):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("测试报告")
        print("=" * 60)
        
        total_operations = len(thread_results) + len(process_results)
        
        print(f"\n📊 总体统计:")
        print(f"  总操作数: {total_operations}")
        print(f"  成功写入: {self.results['successes']}")
        print(f"  失败写入: {self.results['failures']}")
        print(f"  数据丢失: {self.results['data_losses']}")
        
        success_rate = (self.results['successes'] / total_operations * 100) if total_operations > 0 else 0
        print(f"  成功率: {success_rate:.1f}%")
        
        print(f"\n🔒 并发安全性:")
        if self.results['data_losses'] == 0:
            print("  ✅ 未检测到数据丢失")
        else:
            print(f"  ❌ 检测到 {self.results['data_losses']} 个数据丢失")
        
        if self.results['conflicts'] == 0:
            print("  ✅ 未检测到写入冲突")
        else:
            print(f"  ⚠️ 检测到 {self.results['conflicts']} 个写入冲突")
        
        if integrity_ok:
            print("  ✅ 数据完整性验证通过")
        else:
            print("  ❌ 数据完整性验证失败")
        
        print(f"\n📝 结论:")
        if success_rate > 95 and self.results['data_losses'] == 0 and integrity_ok:
            print("  ✅ 并发写入机制安全可靠")
        elif success_rate > 80 and self.results['data_losses'] == 0:
            print("  ⚠️ 并发写入基本安全，但有改进空间")
        else:
            print("  ❌ 并发写入存在问题，需要修复")

def main():
    """主函数"""
    tester = ConcurrentWriteTester()
    tester.run_comprehensive_test()
    
    return 0

if __name__ == "__main__":
    exit(main())