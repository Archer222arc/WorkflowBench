#!/usr/bin/env python3
"""
Result Collector Adapter - 结果收集器适配器
提供智能收集器与现有代码的无缝集成

功能：
1. 兼容现有ResultCollector接口
2. 集成SmartResultCollector的先进功能
3. 自动数据库保存集成
4. 错误处理和回退机制
"""

import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from smart_result_collector import SmartResultCollector
    SMART_COLLECTOR_AVAILABLE = True
except ImportError:
    SMART_COLLECTOR_AVAILABLE = False
    
try:
    from result_collector import ResultCollector as OriginalResultCollector
    ORIGINAL_COLLECTOR_AVAILABLE = True
except ImportError:
    ORIGINAL_COLLECTOR_AVAILABLE = False

logger = logging.getLogger(__name__)

class AdaptiveResultCollector:
    """
    自适应结果收集器 - 智能选择最佳收集策略
    
    特性：
    1. 自动选择最佳收集器实现
    2. 数据库集成
    3. 错误恢复
    4. 性能优化
    """
    
    def __init__(self, 
                 temp_dir: str = "temp_results",
                 use_smart_collector: bool = None,
                 database_manager = None,
                 **kwargs):
        """
        初始化自适应收集器
        
        Args:
            temp_dir: 临时目录
            use_smart_collector: 是否使用智能收集器（None=自动选择）
            database_manager: 数据库管理器实例
            **kwargs: 其他参数传递给具体收集器
        """
        self.temp_dir = Path(temp_dir)
        self.database_manager = database_manager
        self.collector = None
        self.collector_type = None
        
        # 自动选择最佳收集器
        if use_smart_collector is None:
            use_smart_collector = SMART_COLLECTOR_AVAILABLE
            
        # 尝试创建智能收集器
        if use_smart_collector and SMART_COLLECTOR_AVAILABLE:
            try:
                self.collector = SmartResultCollector(
                    temp_dir=str(temp_dir),
                    **self._filter_smart_kwargs(kwargs)
                )
                self.collector_type = "smart"
                
                # 添加数据库保存回调
                if self.database_manager:
                    self.collector.add_save_callback(self._save_to_database)
                    
                logger.info("✅ 使用SmartResultCollector")
                
            except Exception as e:
                logger.error(f"SmartResultCollector初始化失败: {e}")
                self.collector = None
        
        # 回退到原始收集器
        if not self.collector and ORIGINAL_COLLECTOR_AVAILABLE:
            try:
                self.collector = OriginalResultCollector(temp_dir=str(temp_dir))
                self.collector_type = "original"
                logger.info("✅ 使用OriginalResultCollector")
                
            except Exception as e:
                logger.error(f"OriginalResultCollector初始化失败: {e}")
                self.collector = None
        
        # 最后的回退选项
        if not self.collector:
            self.collector = SimpleResultCollector(temp_dir=str(temp_dir))
            self.collector_type = "simple"
            logger.info("⚠️ 使用SimpleResultCollector (最小功能)")
        
        logger.info(f"AdaptiveResultCollector初始化完成，使用: {self.collector_type}")

    def _filter_smart_kwargs(self, kwargs: Dict) -> Dict:
        """过滤传递给SmartResultCollector的参数"""
        smart_params = {
            'max_memory_results', 'max_time_seconds', 'auto_save_interval', 
            'adaptive_threshold'
        }
        return {k: v for k, v in kwargs.items() if k in smart_params}

    def _save_to_database(self, results: List[Dict[str, Any]]):
        """保存结果到数据库的回调函数"""
        if not self.database_manager or not results:
            return
            
        try:
            logger.info(f"💾 保存 {len(results)} 个结果到数据库...")
            
            # 按模型分组保存
            model_groups = {}
            for result in results:
                model = result.get('model', 'unknown')
                if model not in model_groups:
                    model_groups[model] = []
                model_groups[model].append(result)
            
            # 分组保存到数据库
            total_saved = 0
            for model, model_results in model_groups.items():
                try:
                    # 这里集成具体的数据库保存逻辑
                    saved = self._save_model_results(model, model_results)
                    total_saved += saved
                    
                except Exception as e:
                    logger.error(f"保存模型 {model} 结果失败: {e}")
            
            logger.info(f"✅ 成功保存 {total_saved}/{len(results)} 个结果到数据库")
            
        except Exception as e:
            logger.error(f"❌ 数据库保存失败: {e}")

    def _save_model_results(self, model: str, results: List[Dict[str, Any]]) -> int:
        """保存特定模型的结果到数据库"""
        if not hasattr(self.database_manager, 'append_test_result'):
            logger.warning("数据库管理器不支持append_test_result方法")
            return 0
        
        saved_count = 0
        for result in results:
            try:
                # 调用数据库管理器的保存方法
                success = self.database_manager.append_test_result(result)
                if success:
                    saved_count += 1
                    
            except Exception as e:
                logger.error(f"保存单个结果失败: {e}")
                
        return saved_count

    # 兼容接口方法

    def add_batch_result(self, model: str, results: List[Dict], 
                        process_info: Optional[Dict] = None) -> str:
        """兼容原始ResultCollector的add_batch_result接口"""
        if self.collector_type == "smart":
            # 使用智能收集器的批量添加
            self.collector.add_batch(results, model, process_info)
            return f"smart_batch_{len(results)}"
            
        elif self.collector_type == "original":
            # 调用原始收集器
            return self.collector.add_batch_result(model, results, process_info)
            
        else:
            # 简单收集器
            return self.collector.add_batch_result(model, results, process_info)

    def add_result(self, result: Dict[str, Any]) -> bool:
        """添加单个结果"""
        if self.collector_type == "smart":
            return self.collector.add_result(result)
        else:
            # 对于非智能收集器，模拟单个结果添加
            return self.add_batch_result(
                result.get('model', 'unknown'), 
                [result]
            ) is not None

    def collect_all_results(self, cleanup: bool = True) -> List[Dict]:
        """收集所有结果（兼容接口）"""
        if hasattr(self.collector, 'collect_all_results'):
            return self.collector.collect_all_results(cleanup)
        elif hasattr(self.collector, 'recover_from_temp_files'):
            return self.collector.recover_from_temp_files()
        else:
            logger.warning("收集器不支持collect_all_results方法")
            return []

    def force_save(self, reason: str = "manual") -> bool:
        """强制保存"""
        if self.collector_type == "smart":
            return self.collector.force_save(reason)
        else:
            # 对于非智能收集器，触发数据收集
            results = self.collect_all_results(cleanup=False)
            if results:
                self._save_to_database(results)
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if hasattr(self.collector, 'get_stats'):
            return self.collector.get_stats()
        else:
            return {
                'collector_type': self.collector_type,
                'temp_dir': str(self.temp_dir)
            }

    def shutdown(self):
        """关闭收集器"""
        if hasattr(self.collector, 'shutdown'):
            self.collector.shutdown()
        elif hasattr(self.collector, '__exit__'):
            self.collector.__exit__(None, None, None)


class SimpleResultCollector:
    """最简单的结果收集器实现（回退选项）"""
    
    def __init__(self, temp_dir: str = "temp_results"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.results = []
        
    def add_batch_result(self, model: str, results: List[Dict], 
                        process_info: Optional[Dict] = None) -> str:
        """添加批次结果"""
        batch_id = f"simple_{int(time.time())}"
        
        for result in results:
            if 'model' not in result:
                result['model'] = model
            if process_info:
                result['_process_info'] = process_info
                
        self.results.extend(results)
        
        logger.info(f"简单收集器添加 {len(results)} 个结果，总数: {len(self.results)}")
        return batch_id
        
    def collect_all_results(self, cleanup: bool = True) -> List[Dict]:
        """收集所有结果"""
        results = self.results.copy()
        if cleanup:
            self.results.clear()
        return results


# 便利函数
def create_adaptive_collector(database_manager=None, **kwargs) -> AdaptiveResultCollector:
    """创建自适应收集器的便利函数"""
    return AdaptiveResultCollector(database_manager=database_manager, **kwargs)


# 检查环境和推荐配置
def get_recommended_config() -> Dict[str, Any]:
    """获取推荐的收集器配置"""
    config = {
        'temp_dir': 'temp_results',
        'use_smart_collector': SMART_COLLECTOR_AVAILABLE,
    }
    
    # 智能收集器特定配置
    if SMART_COLLECTOR_AVAILABLE:
        config.update({
            'max_memory_results': 10,     # 适中的内存阈值
            'max_time_seconds': 180,      # 3分钟时间阈值
            'auto_save_interval': 60,     # 1分钟自动检查
            'adaptive_threshold': True    # 启用自适应
        })
    
    return config


if __name__ == "__main__":
    # 测试适配器
    print("🧪 测试AdaptiveResultCollector")
    
    # 显示推荐配置
    config = get_recommended_config()
    print(f"推荐配置: {config}")
    
    # 创建收集器
    collector = create_adaptive_collector(**config)
    
    # 模拟一些结果
    import time
    results = [
        {'model': 'test_model', 'success': True, 'score': 0.85},
        {'model': 'test_model', 'success': False, 'score': 0.45},
        {'model': 'another_model', 'success': True, 'score': 0.92}
    ]
    
    # 测试批量添加
    batch_id = collector.add_batch_result('test_model', results)
    print(f"批次ID: {batch_id}")
    
    # 测试单个添加
    single_result = {'model': 'single_test', 'success': True, 'score': 0.78}
    collector.add_result(single_result)
    
    # 显示统计
    stats = collector.get_stats()
    print(f"统计信息: {stats}")
    
    # 强制保存
    collector.force_save("test")
    
    # 关闭
    collector.shutdown()
    print("✅ 测试完成")