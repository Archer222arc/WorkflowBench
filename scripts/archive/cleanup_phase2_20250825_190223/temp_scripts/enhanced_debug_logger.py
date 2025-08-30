#!/usr/bin/env python3
"""
增强的调试日志记录器
支持多层次的详细日志捕获
"""

import os
import sys
import logging
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
import signal
import json

class EnhancedDebugLogger:
    """增强的调试日志器，支持多层次日志捕获"""
    
    def __init__(self, log_dir="logs/debug_detailed"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.processes = {}
        self.stop_monitoring = False
        
    def setup_logging(self, name, level=logging.DEBUG):
        """设置日志记录器"""
        log_file = self.log_dir / f"{name}_{self.timestamp}.log"
        
        # 创建logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # 文件handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(level)
        
        # 控制台handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # 格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def monitor_process(self, process, name, logger):
        """监控进程输出"""
        def read_output(pipe, prefix):
            """读取管道输出"""
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        logger.debug(f"{prefix}: {line.strip()}")
                    if self.stop_monitoring:
                        break
            except Exception as e:
                logger.error(f"Error reading {prefix}: {e}")
        
        # 创建线程读取stdout和stderr
        if process.stdout:
            stdout_thread = threading.Thread(
                target=read_output, 
                args=(process.stdout, "STDOUT")
            )
            stdout_thread.daemon = True
            stdout_thread.start()
            
        if process.stderr:
            stderr_thread = threading.Thread(
                target=read_output, 
                args=(process.stderr, "STDERR")
            )
            stderr_thread.daemon = True
            stderr_thread.start()
    
    def run_with_detailed_logging(self, cmd, env=None):
        """运行命令并捕获详细日志"""
        
        # 主日志器
        main_logger = self.setup_logging("main")
        main_logger.info("="*60)
        main_logger.info(f"启动增强调试模式")
        main_logger.info(f"命令: {' '.join(cmd)}")
        main_logger.info(f"环境变量:")
        
        # 记录关键环境变量
        important_vars = [
            'STORAGE_FORMAT', 'DEBUG_LOG', 'DEBUG_PROCESS_NUM',
            'RATE_MODE', 'PYTHONFAULTHANDLER', 'PYTHONUNBUFFERED'
        ]
        
        for var in important_vars:
            value = os.environ.get(var, 'NOT SET')
            main_logger.info(f"  {var}={value}")
        
        main_logger.info("="*60)
        
        # 准备环境变量
        process_env = os.environ.copy()
        if env:
            process_env.update(env)
            
        # 强制启用Python调试
        process_env['PYTHONFAULTHANDLER'] = '1'
        process_env['PYTHONUNBUFFERED'] = '1'
        process_env['PYTHONVERBOSE'] = '1'  # 显示导入信息
        
        # 启动主进程
        main_logger.info("启动主进程...")
        main_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=process_env
        )
        
        self.processes['main'] = main_process
        
        # 监控主进程
        self.monitor_process(main_process, 'main', main_logger)
        
        # 定期检查子进程
        def monitor_children():
            """监控子进程"""
            child_logger = self.setup_logging("children")
            seen_pids = set()
            
            while not self.stop_monitoring:
                try:
                    # 查找所有相关进程
                    result = subprocess.run(
                        ['pgrep', '-f', 'smart_batch_runner'],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.stdout:
                        pids = result.stdout.strip().split('\n')
                        for pid in pids:
                            if pid and pid not in seen_pids:
                                seen_pids.add(pid)
                                # 获取进程信息
                                try:
                                    ps_result = subprocess.run(
                                        ['ps', '-p', pid, '-o', 'command='],
                                        capture_output=True,
                                        text=True
                                    )
                                    if ps_result.stdout:
                                        child_logger.info(f"发现子进程 PID={pid}: {ps_result.stdout.strip()[:100]}")
                                except:
                                    pass
                    
                    # 检查网络连接
                    netstat_result = subprocess.run(
                        ['netstat', '-an'],
                        capture_output=True,
                        text=True
                    )
                    
                    close_wait_count = netstat_result.stdout.count('CLOSE_WAIT')
                    if close_wait_count > 10:
                        child_logger.warning(f"⚠️ 发现 {close_wait_count} 个CLOSE_WAIT连接")
                    
                except Exception as e:
                    child_logger.error(f"监控错误: {e}")
                
                time.sleep(5)  # 每5秒检查一次
        
        # 启动子进程监控线程
        monitor_thread = threading.Thread(target=monitor_children)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # 等待主进程完成
        try:
            returncode = main_process.wait()
            main_logger.info(f"主进程完成，退出码: {returncode}")
        except KeyboardInterrupt:
            main_logger.warning("收到中断信号")
            main_process.terminate()
            returncode = -1
        finally:
            self.stop_monitoring = True
            
        # 收集统计信息
        stats_logger = self.setup_logging("statistics")
        stats_logger.info("="*60)
        stats_logger.info("执行统计")
        
        # 检查数据保存
        self.check_data_saved(stats_logger)
        
        return returncode
    
    def check_data_saved(self, logger):
        """检查数据是否保存"""
        try:
            # 检查JSON数据库
            json_path = Path('pilot_bench_cumulative_results/master_database.json')
            if json_path.exists():
                with open(json_path, 'r') as f:
                    db = json.load(f)
                logger.info(f"JSON数据库: {db['summary']['total_tests']} 个测试")
                logger.info(f"最后更新: {db.get('last_updated', 'Unknown')}")
            
            # 检查Parquet文件
            parquet_path = Path('pilot_bench_parquet_data/test_results.parquet')
            if parquet_path.exists():
                import pandas as pd
                df = pd.read_parquet(parquet_path)
                logger.info(f"Parquet文件: {len(df)} 条记录")
                if 'last_updated' in df.columns:
                    logger.info(f"最新更新: {df['last_updated'].max()}")
                    
            # 检查增量文件
            inc_dir = Path('pilot_bench_parquet_data/incremental')
            if inc_dir.exists():
                inc_files = list(inc_dir.glob('*.parquet'))
                logger.info(f"增量文件: {len(inc_files)} 个")
                
        except Exception as e:
            logger.error(f"检查数据保存失败: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Debug Logger')
    parser.add_argument('--command', nargs='+', required=True, help='要执行的命令')
    parser.add_argument('--log-dir', default='logs/debug_detailed', help='日志目录')
    
    args = parser.parse_args()
    
    logger = EnhancedDebugLogger(log_dir=args.log_dir)
    returncode = logger.run_with_detailed_logging(args.command)
    
    sys.exit(returncode)

if __name__ == '__main__':
    main()