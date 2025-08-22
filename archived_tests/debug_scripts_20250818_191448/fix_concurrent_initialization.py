#!/usr/bin/env python3
"""修复并发初始化问题的补丁"""

import threading
from pathlib import Path

# 全局单例和锁
_generator_instance = None
_generator_lock = threading.Lock()

def get_mdp_workflow_generator():
    """获取MDPWorkflowGenerator的线程安全单例实例"""
    global _generator_instance
    
    if _generator_instance is None:
        with _generator_lock:
            # 双重检查锁定
            if _generator_instance is None:
                print("[INFO] 初始化MDPWorkflowGenerator单例...")
                from mdp_workflow_generator import MDPWorkflowGenerator
                _generator_instance = MDPWorkflowGenerator()
                print("[INFO] MDPWorkflowGenerator单例初始化完成")
    
    return _generator_instance

def patch_batch_test_runner():
    """修补BatchTestRunner以使用单例generator"""
    import batch_test_runner
    
    # 保存原始的_lazy_init方法
    original_lazy_init = batch_test_runner.BatchTestRunner._lazy_init
    
    def patched_lazy_init(self):
        """修补后的_lazy_init方法，使用单例generator"""
        with self._init_lock:
            if self._initialized:
                return
            
            print(f"[INFO] 线程 {threading.current_thread().name}: 开始lazy_init")
            
            # 使用单例generator
            self.generator = get_mdp_workflow_generator()
            print(f"[INFO] 线程 {threading.current_thread().name}: 获取到generator单例")
            
            # 初始化其他组件
            from flawed_workflow_generator import FlawedWorkflowGenerator
            from workflow_quality_test import WorkflowQualityTester
            
            # 创建FlawedWorkflowGenerator（使用同一个generator）
            self.flawed_generator = FlawedWorkflowGenerator(base_generator=self.generator)
            
            # 创建manager
            from enhanced_cumulative_manager import EnhancedCumulativeManager
            self.manager = EnhancedCumulativeManager(
                enable_database_updates=self.enable_database_updates,
                use_ai_classification=self.use_ai_classification,
                save_logs=self.save_logs
            )
            
            # 创建quality tester
            self.quality_tester = WorkflowQualityTester(
                generator=self.generator,
                manager=self.manager,
                debug=self.debug,
                save_logs=self.save_logs
            )
            
            # 加载任务库
            self._load_task_library(difficulty="easy")
            self._current_difficulty = "easy"
            
            self._initialized = True
            print(f"[INFO] 线程 {threading.current_thread().name}: lazy_init完成")
    
    # 替换方法
    batch_test_runner.BatchTestRunner._lazy_init = patched_lazy_init
    print("[INFO] BatchTestRunner已修补为使用单例generator")

def ensure_data_flush():
    """确保数据被定期刷新到磁盘"""
    import atexit
    from enhanced_cumulative_manager import EnhancedCumulativeManager
    
    def flush_all_data():
        """刷新所有待保存的数据"""
        print("[INFO] 正在刷新所有数据到磁盘...")
        try:
            manager = EnhancedCumulativeManager()
            if hasattr(manager, '_flush_buffer'):
                manager._flush_buffer()
            if hasattr(manager, 'finalize'):
                manager.finalize()
            print("[INFO] 数据刷新完成")
        except Exception as e:
            print(f"[ERROR] 数据刷新失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 注册退出时的清理函数
    atexit.register(flush_all_data)
    print("[INFO] 已注册数据刷新钩子")

def apply_all_fixes():
    """应用所有修复"""
    print("=" * 60)
    print("应用并发初始化修复")
    print("=" * 60)
    
    # 1. 修补BatchTestRunner
    patch_batch_test_runner()
    
    # 2. 确保数据刷新
    ensure_data_flush()
    
    # 3. 设置合理的worker数量限制
    import os
    if not os.environ.get('MAX_WORKERS_OVERRIDE'):
        os.environ['MAX_WORKERS_LIMIT'] = '30'
        print("[INFO] 设置MAX_WORKERS_LIMIT=30")
    
    print("=" * 60)
    print("修复应用完成")
    print("=" * 60)

if __name__ == "__main__":
    apply_all_fixes()
    
    # 测试修复
    print("\n测试修复效果...")
    import threading
    from batch_test_runner import BatchTestRunner
    
    runners = []
    def create_runner(idx):
        print(f"创建Runner {idx}...")
        runner = BatchTestRunner(debug=False, silent=True)
        runner._lazy_init()  # 触发初始化
        runners.append(runner)
        print(f"Runner {idx} generator id: {id(runner.generator)}")
    
    threads = []
    for i in range(3):
        t = threading.Thread(target=create_runner, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # 验证是否使用同一个generator
    if len(runners) >= 2:
        same_generator = all(runners[0].generator is r.generator for r in runners[1:])
        if same_generator:
            print("✅ 所有Runner使用同一个generator单例")
        else:
            print("❌ Runner使用了不同的generator实例")