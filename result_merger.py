#!/usr/bin/env python3
"""
结果合并器 - ResultCollector的核心组件
负责从临时文件收集结果并统一写入数据库
"""

import os
import json
import time
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict
from merger_lock import get_merger_lock

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入必要的模块
from cumulative_test_manager import TestRecord
from enhanced_cumulative_manager import EnhancedCumulativeManager

# 避免循环导入，本地实现manager获取
def _get_or_create_manager(use_ai_classification=True):
    """获取或创建manager实例"""
    return EnhancedCumulativeManager(use_ai_classification=use_ai_classification)


class ResultMerger:
    """
    结果合并器 - 负责收集和合并所有临时结果文件
    单例模式，确保只有一个进程写入数据库
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.temp_dir = Path("temp_results")
            self.temp_dir.mkdir(exist_ok=True)
            self.processed_files = set()  # 已处理的文件
            self.merge_interval = 10  # 合并间隔（秒）
            self.is_running = False
            self.merge_thread = None
            self._initialized = True
            logger.info("ResultMerger初始化完成")
    
    def start(self, interval: int = 10):
        """
        启动后台合并线程
        
        Args:
            interval: 合并间隔（秒）
        """
        if self.is_running:
            logger.warning("合并线程已在运行")
            return
        
        # 尝试获取合并器锁
        lock = get_merger_lock()
        if not lock.acquire():
            logger.warning(f"另一个合并器已在运行 (PID: {lock.get_lock_owner()})")
            return
        
        logger.info(f"🚀 启动ResultMerger，合并间隔: {interval}秒")
        self.merge_interval = interval
        self.is_running = True
        self.merge_thread = threading.Thread(target=self._merge_loop, daemon=True)
        self.merge_thread.start()
        logger.info(f"✅ ResultMerger后台线程已启动，支持智能停止机制")
    
    def stop(self):
        """停止合并线程"""
        if not self.is_running:
            logger.info("合并线程已经停止，无需重复操作")
            return
        
        logger.info("🛑 手动停止ResultMerger...")
        self.is_running = False
        
        if self.merge_thread:
            logger.info("等待合并线程结束...")
            # 🔧 修复：缩短join超时时间，避免长时间等待
            self.merge_thread.join(timeout=2)
            if self.merge_thread.is_alive():
                logger.info("⚠️ 合并线程仍在运行，但由于使用daemon线程，主程序退出时会自动清理")
            else:
                logger.info("✅ 合并线程已正常结束")
        
        # 释放合并器锁
        try:
            lock = get_merger_lock()
            lock.release()
            logger.info("🔓 合并器锁已释放")
        except Exception as e:
            logger.warning(f"⚠️ 释放合并器锁时出现问题: {e}")
        
        logger.info("🏁 ResultMerger已完全停止")
    
    def _merge_loop(self):
        """合并循环 - 增强版：支持智能停止防止hang住"""
        consecutive_empty_rounds = 0
        max_empty_rounds = 3  # 连续3轮没有文件就自动停止
        
        logger.info(f"ResultMerger开始运行，智能停止阈值: {max_empty_rounds}轮")
        
        while self.is_running:
            try:
                processed_files = self.merge_once()
                
                if processed_files == 0:
                    consecutive_empty_rounds += 1
                    logger.debug(f"本轮无文件处理，连续空轮次: {consecutive_empty_rounds}/{max_empty_rounds}")
                    
                    if consecutive_empty_rounds >= max_empty_rounds:
                        logger.info(f"🛑 连续{max_empty_rounds}轮无新文件，自动停止合并器防止hang住")
                        self.is_running = False
                        break
                else:
                    if consecutive_empty_rounds > 0:
                        logger.info(f"✅ 处理了{processed_files}个文件，重置空轮次计数器")
                    consecutive_empty_rounds = 0  # 重置计数器
                    
            except Exception as e:
                logger.error(f"合并出错: {e}")
                # 异常时不增加空轮次计数，避免意外退出
            
            # 等待下一次合并
            if self.is_running:  # 只有在还需要运行时才等待
                for _ in range(self.merge_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
        
        logger.info("🏁 ResultMerger合并循环已结束")
    
    def merge_once(self) -> int:
        """
        执行一次合并操作
        
        Returns:
            合并的文件数量
        """
        # 查找所有临时结果文件
        temp_files = list(self.temp_dir.glob("*.json"))
        new_files = [f for f in temp_files if f not in self.processed_files]
        
        if not new_files:
            return 0
        
        logger.info(f"发现{len(new_files)}个新的结果文件")
        
        # 按模型分组
        results_by_model = defaultdict(list)
        
        for file_path in new_files:
            # 检查文件是否仍然存在（可能被其他进程删除）
            if not file_path.exists():
                logger.debug(f"文件已被其他进程处理: {file_path}")
                self.processed_files.add(file_path)
                continue
            
            try:
                # 尝试读取文件内容
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except FileNotFoundError:
                    # 文件在打开时被删除了
                    logger.debug(f"文件在读取时被删除: {file_path}")
                    self.processed_files.add(file_path)
                    continue
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败 {file_path}: {e}")
                    # 仍然标记为已处理，避免重复尝试
                    self.processed_files.add(file_path)
                    continue
                
                model = data.get('model', 'unknown')
                results = data.get('results', [])
                
                # 转换为TestRecord对象
                for result in results:
                    if result and not result.get('_merged', False):
                        record = self._create_test_record(model, result)
                        if record:
                            results_by_model[model].append(record)
                
                # 标记为已处理
                self.processed_files.add(file_path)
                
                # 处理后删除文件（避免占用空间）
                try:
                    if file_path.exists():  # 再次检查文件是否存在
                        file_path.unlink()
                        logger.debug(f"删除已处理文件: {file_path}")
                except FileNotFoundError:
                    pass  # 文件已被其他进程删除，这是正常的
                except Exception as e:
                    logger.warning(f"无法删除文件{file_path}: {e}")
                
            except Exception as e:
                logger.error(f"处理文件{file_path}失败: {e}")
                continue
        
        # 批量保存到数据库
        total_saved = 0
        for model, records in results_by_model.items():
            saved = self._save_to_database(model, records)
            total_saved += saved
        
        logger.info(f"合并完成，共处理{len(new_files)}个文件，保存{total_saved}条记录")
        return len(new_files)
    
    def _create_test_record(self, model: str, result: Dict) -> Optional[TestRecord]:
        """
        从结果字典创建TestRecord对象
        
        Args:
            model: 模型名称
            result: 结果字典
            
        Returns:
            TestRecord对象或None
        """
        try:
            record = TestRecord(
                model=model,
                task_type=result.get("task_type", "unknown"),
                prompt_type=result.get("prompt_type", "baseline"),
                difficulty=result.get("difficulty", "easy")
            )
            
            # 设置其他字段
            for field in ['timestamp', 'success', 'success_level', 'execution_time', 
                         'turns', 'tool_calls', 'workflow_score', 'phase2_score', 
                         'quality_score', 'final_score', 'error_type', 'error_message',
                         'tool_success_rate', 'is_flawed', 'flaw_type', 'execution_status',
                         'ai_error_category', 'tool_coverage_rate', 'format_turns',
                         'assisted_turns', 'assisted_success']:
                if field in result:
                    setattr(record, field, result[field])
            
            return record
            
        except Exception as e:
            logger.error(f"创建TestRecord失败: {e}")
            return None
    
    def _save_to_database(self, model: str, records: List[TestRecord]) -> int:
        """
        保存记录到数据库
        
        Args:
            model: 模型名称
            records: 记录列表
            
        Returns:
            成功保存的数量
        """
        if not records:
            return 0
        
        try:
            # 获取或创建manager（单例） - 增强数据保护
            manager = _get_or_create_manager(use_ai_classification=True)
            
            # 🔧 数据保护修复：使用智能合并而不是强制重新加载
            # 移除强制重新加载，让manager使用其内置的文件锁和合并机制
            logger.info(f"[MERGER_PROTECTION] 使用manager内置的安全合并机制")
            
            success_count = 0
            for record in records:
                try:
                    if manager.append_test_result(record):
                        success_count += 1
                except Exception as e:
                    logger.error(f"保存记录失败: {e}")
                    continue
            
            logger.info(f"模型{model}保存{success_count}/{len(records)}条记录")
            return success_count
            
        except Exception as e:
            logger.error(f"数据库保存失败: {e}")
            return 0
    
    def force_merge_all(self) -> int:
        """
        强制合并所有未处理的文件
        
        Returns:
            合并的文件数量
        """
        # 重置已处理文件列表，强制处理所有文件
        self.processed_files.clear()
        return self.merge_once()
    
    def cleanup_old_files(self, days: int = 7):
        """
        清理旧的临时文件
        
        Args:
            days: 保留天数
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        cleaned = 0
        
        for file_path in self.temp_dir.glob("*.json"):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    cleaned += 1
                    if file_path in self.processed_files:
                        self.processed_files.remove(file_path)
                except Exception as e:
                    logger.error(f"删除文件{file_path}失败: {e}")
        
        if cleaned > 0:
            logger.info(f"清理了{cleaned}个旧文件")
        
        return cleaned


# 全局合并器实例
_global_merger = None

def get_merger() -> ResultMerger:
    """获取全局合并器实例"""
    global _global_merger
    if _global_merger is None:
        _global_merger = ResultMerger()
    return _global_merger


def start_auto_merge(interval: int = 10):
    """
    启动自动合并
    
    Args:
        interval: 合并间隔（秒）
    """
    merger = get_merger()
    merger.start(interval)
    return merger


def stop_auto_merge():
    """停止自动合并"""
    merger = get_merger()
    merger.stop()


def force_merge():
    """强制执行一次合并"""
    merger = get_merger()
    return merger.force_merge_all()


if __name__ == "__main__":
    # 测试代码
    print("启动ResultMerger测试...")
    
    # 启动自动合并
    merger = start_auto_merge(interval=5)
    
    print("合并器已启动，每5秒检查一次")
    print("按Ctrl+C停止...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止合并器...")
        stop_auto_merge()
        
        # 最后强制合并一次
        print("执行最终合并...")
        count = force_merge()
        print(f"最终合并了{count}个文件")