#!/usr/bin/env python3
"""
Result Collector - 消息队列式结果收集器
支持超并发模式下的无冲突数据聚合

设计理念：
- 测试进程：只负责生成结果，发送到收集器
- 收集器：负责聚合所有结果，统一写入数据库
- 零并发冲突：只有一个写入者
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ResultCollector:
    """基于文件的结果收集器"""
    
    def __init__(self, temp_dir: str = "temp_results"):
        """
        初始化结果收集器
        
        Args:
            temp_dir: 临时结果文件存储目录
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        logger.info(f"ResultCollector初始化，临时目录: {self.temp_dir}")
    
    def add_batch_result(self, model: str, results: List[Dict], 
                        process_info: Optional[Dict] = None) -> str:
        """
        添加一个批次的测试结果
        
        Args:
            model: 模型名称
            results: 测试结果列表
            process_info: 进程信息（可选）
            
        Returns:
            结果文件路径
        """
        # 创建唯一的结果文件名
        timestamp = int(time.time() * 1000000)  # 微秒精度
        pid = os.getpid()
        filename = f"{model}_{pid}_{timestamp}.json"
        result_file = self.temp_dir / filename
        
        # 准备结果数据
        result_data = {
            'model': model,
            'results': results,
            'timestamp': datetime.now().isoformat(),
            'pid': pid,
            'process_info': process_info or {},
            'result_count': len(results)
        }
        
        # 写入结果文件
        try:
            # 确保所有数据都是JSON可序列化的
            json_str = json.dumps(result_data, indent=2, ensure_ascii=False, default=str)
            
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            logger.info(f"📤 已提交 {model} 的 {len(results)} 个结果到收集器: {filename}")
            return str(result_file)
            
        except Exception as e:
            logger.error(f"❌ 提交结果失败: {e}")
            # 尝试诊断问题
            try:
                for i, result in enumerate(results):
                    json.dumps(result, default=str)
            except Exception as inner_e:
                logger.error(f"❌ 第 {i} 个结果无法序列化: {inner_e}")
                logger.error(f"问题数据类型: {type(result)}")
            raise
    
    def collect_all_results(self, cleanup: bool = True) -> List[Dict]:
        """
        收集所有待处理的结果
        
        Args:
            cleanup: 是否删除已处理的临时文件
            
        Returns:
            所有结果的列表
        """
        all_results = []
        result_files = list(self.temp_dir.glob("*.json"))
        
        logger.info(f"🔄 开始收集结果，发现 {len(result_files)} 个结果文件")
        
        for result_file in result_files:
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    result_data = json.load(f)
                
                all_results.append(result_data)
                
                # 日志显示收集进度
                model = result_data.get('model', 'unknown')
                count = result_data.get('result_count', 0)
                pid = result_data.get('pid', 'unknown')
                logger.info(f"📥 收集到 {model} 的 {count} 个结果 (PID: {pid})")
                
                # 清理已处理的文件
                if cleanup:
                    result_file.unlink()
                    
            except Exception as e:
                logger.warning(f"⚠️ 读取结果文件失败: {result_file}, 错误: {e}")
                # 不删除失败的文件，便于后续排查
                continue
        
        # 按模型分组统计
        model_stats = {}
        for result in all_results:
            model = result.get('model', 'unknown')
            count = result.get('result_count', 0)
            model_stats[model] = model_stats.get(model, 0) + count
        
        logger.info("📊 收集统计:")
        total_results = 0
        for model, count in model_stats.items():
            logger.info(f"  {model}: {count} 个结果")
            total_results += count
        
        logger.info(f"✅ 总计收集 {total_results} 个测试结果，来自 {len(model_stats)} 个模型")
        
        return all_results
    
    def get_pending_count(self) -> int:
        """获取待处理的结果文件数量"""
        return len(list(self.temp_dir.glob("*.json")))
    
    def clear_temp_files(self):
        """清理所有临时结果文件（慎用！）"""
        result_files = list(self.temp_dir.glob("*.json"))
        for result_file in result_files:
            result_file.unlink()
        logger.info(f"🧹 已清理 {len(result_files)} 个临时结果文件")


class ResultAggregator:
    """结果聚合器 - 将收集到的结果聚合为数据库格式"""
    
    def __init__(self):
        logger.info("ResultAggregator初始化")
    
    def aggregate_results(self, collected_results: List[Dict]) -> Dict:
        """
        聚合所有收集到的结果
        
        Args:
            collected_results: ResultCollector.collect_all_results()的返回值
            
        Returns:
            聚合后的数据库格式
        """
        aggregated_db = {
            "version": "3.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "models": {},
            "summary": {
                "total_tests": 0,
                "total_success": 0,
                "total_failure": 0,
                "models_tested": []
            }
        }
        
        logger.info(f"🔄 开始聚合 {len(collected_results)} 个结果批次")
        
        for batch in collected_results:
            model = batch.get('model')
            results = batch.get('results', [])
            
            if not model or not results:
                logger.warning(f"⚠️ 跳过无效批次: model={model}, results_count={len(results)}")
                continue
            
            # 为模型创建条目（如果不存在）
            if model not in aggregated_db["models"]:
                aggregated_db["models"][model] = self._create_empty_model_entry(model)
                aggregated_db["summary"]["models_tested"].append(model)
            
            # 聚合结果到模型条目
            self._aggregate_model_results(aggregated_db["models"][model], results)
            
            logger.info(f"📊 已聚合 {model} 的 {len(results)} 个结果")
        
        # 更新总体统计
        self._update_summary_stats(aggregated_db)
        
        logger.info("✅ 结果聚合完成")
        return aggregated_db
    
    def _create_empty_model_entry(self, model: str) -> Dict:
        """创建空的模型条目"""
        return {
            "model_name": model,
            "first_test_time": datetime.now().isoformat(),
            "last_test_time": datetime.now().isoformat(),
            "total_tests": 0,
            "overall_stats": {},
            "by_prompt_type": {}
        }
    
    def _aggregate_model_results(self, model_entry: Dict, results: List[Dict]):
        """将结果聚合到模型条目中"""
        # 这里需要根据你的数据结构来实现具体的聚合逻辑
        # 现在先做简单的计数
        model_entry["total_tests"] += len(results)
        model_entry["last_test_time"] = datetime.now().isoformat()
        
        # TODO: 实现详细的按task_type、prompt_type等维度的聚合
        # 这部分逻辑可以从现有的CumulativeTestManager中提取
        
    def _update_summary_stats(self, aggregated_db: Dict):
        """更新总体统计信息"""
        total_tests = 0
        for model_data in aggregated_db["models"].values():
            total_tests += model_data.get("total_tests", 0)
        
        aggregated_db["summary"]["total_tests"] = total_tests


# 兼容性接口：可以作为现有系统的插件
class CumulativeTestManagerAdapter:
    """适配器：让ResultCollector兼容现有的CumulativeTestManager接口"""
    
    def __init__(self, use_collector: bool = False):
        """
        Args:
            use_collector: 是否启用新的collector模式
        """
        self.use_collector = use_collector
        
        if use_collector:
            self.collector = ResultCollector()
            self.aggregator = ResultAggregator()
            logger.info("🆕 启用ResultCollector模式")
        else:
            # 使用原有的CumulativeTestManager
            from cumulative_test_manager import CumulativeTestManager
            self.legacy_manager = CumulativeTestManager()
            logger.info("📜 使用传统CumulativeTestManager模式")
    
    def append_test_result(self, result: Dict) -> bool:
        """兼容现有接口：添加单个测试结果"""
        if self.use_collector:
            # 新模式：缓存结果，稍后批量提交
            if not hasattr(self, '_batch_cache'):
                self._batch_cache = []
            self._batch_cache.append(result)
            return True
        else:
            # 传统模式：直接使用原有管理器
            return self.legacy_manager.append_test_result(result)
    
    def save_database(self):
        """兼容现有接口：保存数据库"""
        if self.use_collector:
            # 新模式：提交缓存的结果到collector
            if hasattr(self, '_batch_cache') and self._batch_cache:
                model = self._batch_cache[0].get('model', 'unknown')
                self.collector.add_batch_result(model, self._batch_cache)
                self._batch_cache = []
                logger.info("📤 已提交批次结果到collector")
        else:
            # 传统模式
            self.legacy_manager.save_database()