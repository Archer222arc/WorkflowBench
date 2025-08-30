#!/usr/bin/env python3
"""
智能数据收集器集成脚本
将SmartResultCollector集成到现有的BatchTestRunner和smart_batch_runner中

集成策略：
1. 向后兼容 - 保持现有接口不变
2. 渐进升级 - 可以选择性启用新功能
3. 智能检测 - 自动选择最佳配置
4. 无缝切换 - 无需修改调用代码
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class SmartCollectorIntegrator:
    """智能收集器集成器"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.backup_dir = self.workspace_root / "backups" / f"integration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 需要集成的文件
        self.target_files = [
            "smart_batch_runner.py",
            "batch_test_runner.py"
        ]
        
    def integrate_all(self) -> Dict[str, Any]:
        """执行完整集成"""
        logger.info("🚀 开始集成智能数据收集器...")
        
        results = {
            'backup_created': False,
            'files_modified': [],
            'files_failed': [],
            'new_files_created': [],
            'integration_success': False
        }
        
        try:
            # 1. 创建备份
            results['backup_created'] = self._create_backups()
            
            # 2. 集成到smart_batch_runner.py
            if self._integrate_smart_batch_runner():
                results['files_modified'].append('smart_batch_runner.py')
            else:
                results['files_failed'].append('smart_batch_runner.py')
            
            # 3. 集成到batch_test_runner.py
            if self._integrate_batch_test_runner():
                results['files_modified'].append('batch_test_runner.py')
            else:
                results['files_failed'].append('batch_test_runner.py')
            
            # 4. 创建配置文件
            if self._create_integration_config():
                results['new_files_created'].append('smart_collector_config.py')
            
            # 5. 创建使用指南
            if self._create_usage_guide():
                results['new_files_created'].append('SMART_COLLECTOR_GUIDE.md')
            
            results['integration_success'] = len(results['files_failed']) == 0
            
        except Exception as e:
            logger.error(f"集成过程出错: {e}")
            results['integration_success'] = False
        
        return results
    
    def _create_backups(self) -> bool:
        """创建文件备份"""
        logger.info("📦 创建文件备份...")
        
        try:
            for filename in self.target_files:
                source_file = self.workspace_root / filename
                if source_file.exists():
                    backup_file = self.backup_dir / filename
                    shutil.copy2(source_file, backup_file)
                    logger.info(f"  备份: {filename} -> {backup_file}")
            
            logger.info(f"✅ 备份完成: {self.backup_dir}")
            return True
            
        except Exception as e:
            logger.error(f"备份失败: {e}")
            return False
    
    def _integrate_smart_batch_runner(self) -> bool:
        """集成到smart_batch_runner.py"""
        logger.info("🔧 集成到 smart_batch_runner.py...")
        
        target_file = self.workspace_root / "smart_batch_runner.py"
        if not target_file.exists():
            logger.warning("smart_batch_runner.py 不存在")
            return False
        
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. 添加智能收集器导入
            import_section = '''# 可选支持ResultCollector
try:
    from result_collector import ResultCollector
    from result_collector_adapter import AdaptiveResultCollector
    RESULT_COLLECTOR_AVAILABLE = True
except ImportError:
    RESULT_COLLECTOR_AVAILABLE = False'''
            
            # 替换现有的import部分
            old_import_pattern = r'# 可选支持ResultCollector\ntry:\s*\n\s*from result_collector import ResultCollector\n\s*RESULT_COLLECTOR_AVAILABLE = True\nexcept ImportError:\s*\n\s*RESULT_COLLECTOR_AVAILABLE = False'
            
            if re.search(old_import_pattern, content, re.MULTILINE):
                content = re.sub(old_import_pattern, import_section, content, flags=re.MULTILINE)
            else:
                # 如果没有找到精确匹配，在导入部分后添加
                content = content.replace(
                    '# 可选支持ResultCollector',
                    import_section
                )
            
            # 2. 修改结果收集器创建逻辑
            new_collector_creation = '''    # 创建智能结果收集器
    result_collector = None
    if use_collector:
        try:
            # 尝试使用自适应收集器
            from result_collector_adapter import create_adaptive_collector
            
            # 获取数据库管理器
            database_manager = getattr(runner, 'manager', None) if hasattr(runner, 'manager') else None
            
            # 智能配置
            collector_config = {
                'temp_dir': 'temp_results',
                'max_memory_results': max(5, checkpoint_interval or 5),  # 自适应阈值
                'max_time_seconds': 300,  # 5分钟超时
                'auto_save_interval': 60,  # 1分钟自动保存
                'adaptive_threshold': True,
                'database_manager': database_manager
            }
            
            result_collector = create_adaptive_collector(**collector_config)
            
            if not silent:
                print("🧠 启用SmartResultCollector模式，智能数据管理")
        except ImportError:
            # 回退到原始ResultCollector
            try:
                result_collector = ResultCollector()
                if not silent:
                    print("🆕 启用ResultCollector模式，测试完成后统一写入")
            except:
                result_collector = None
                if not silent:
                    print("⚠️ ResultCollector不可用，使用传统模式")
        except Exception as e:
            logger.warning(f"智能收集器创建失败，使用传统模式: {e}")
            result_collector = None'''
            
            # 替换现有的收集器创建逻辑
            old_collector_pattern = r'# 创建ResultCollector（如果需要）[\s\S]*?print\("⚠️ ResultCollector不可用，使用传统模式"\)'
            
            if re.search(old_collector_pattern, content):
                content = re.sub(old_collector_pattern, new_collector_creation, content)
            else:
                # 如果找不到精确模式，寻找更简单的模式进行替换
                simple_pattern = r'result_collector = ResultCollector\(\)[\s\S]*?print\("⚠️ ResultCollector不可用，使用传统模式"\)'
                if re.search(simple_pattern, content):
                    content = re.sub(simple_pattern, new_collector_creation, content)
            
            # 3. 改进checkpoint_interval的默认处理
            checkpoint_improvement = '''    # 智能checkpoint_interval处理
    if checkpoint_interval is None:
        # 根据测试规模自动调整
        if num_instances <= 5:
            checkpoint_interval = max(1, num_instances)  # 小规模测试使用小阈值
        else:
            checkpoint_interval = min(10, num_instances // 2)  # 大规模测试使用适中阈值
        
        if not silent:
            print(f"📊 自适应checkpoint_interval: {checkpoint_interval}")'''
            
            # 在参数处理部分添加智能逻辑
            if 'if checkpoint_interval > 0:' in content:
                content = content.replace(
                    'if checkpoint_interval > 0:',
                    checkpoint_improvement + '\n    \n    if checkpoint_interval > 0:'
                )
            
            # 写入修改后的内容
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ smart_batch_runner.py 集成完成")
            return True
            
        except Exception as e:
            logger.error(f"smart_batch_runner.py 集成失败: {e}")
            # 恢复备份
            backup_file = self.backup_dir / "smart_batch_runner.py"
            if backup_file.exists():
                shutil.copy2(backup_file, target_file)
            return False
    
    def _integrate_batch_test_runner(self) -> bool:
        """集成到batch_test_runner.py"""
        logger.info("🔧 集成到 batch_test_runner.py...")
        
        target_file = self.workspace_root / "batch_test_runner.py"
        if not target_file.exists():
            logger.warning("batch_test_runner.py 不存在")
            return False
        
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. 添加智能checkpoint逻辑
            smart_checkpoint_method = '''
    def _smart_checkpoint_save(self, results, task_model=None, force=False):
        """智能checkpoint保存 - 支持多重触发条件"""
        if not self.checkpoint_interval or self.enable_database_updates:
            return
        
        # 将结果添加到pending缓存
        if results:
            if isinstance(results, list):
                self.pending_results.extend(results)
            else:
                self.pending_results.append(results)
        
        # 多重触发条件检查
        current_time = time.time()
        time_since_last_save = current_time - getattr(self, '_last_checkpoint_time', current_time)
        result_count = len(self.pending_results)
        
        # 自适应阈值
        effective_threshold = self.checkpoint_interval
        if hasattr(self, '_adaptive_checkpoint') and self._adaptive_checkpoint:
            if result_count > 0 and time_since_last_save > 300:  # 5分钟强制保存
                effective_threshold = 1
            elif time_since_last_save > 180:  # 3分钟降低阈值
                effective_threshold = max(1, self.checkpoint_interval // 2)
        
        # 触发条件
        should_save = (force or 
                      result_count >= effective_threshold or
                      (result_count > 0 and time_since_last_save > 600) or  # 10分钟强制保存
                      (result_count >= 3 and time_since_last_save > 120))   # 2分钟部分保存
        
        if should_save and self.pending_results:
            print(f"\\n💾 智能Checkpoint: 保存{len(self.pending_results)}个结果...")
            print(f"   触发原因: 数量={result_count}, 时间={time_since_last_save:.1f}s, 强制={force}")
            
            # 确保已初始化manager
            self._lazy_init()
            
            # 保存逻辑（保持原有逻辑）
            try:
                from cumulative_test_manager import TestRecord
                saved_count = 0
                
                for result in self.pending_results:
                    if result and not result.get('_saved', False):
                        record = TestRecord(
                            model=result.get('model', task_model or 'unknown'),
                            task_type=result.get('task_type', 'unknown'),
                            prompt_type=result.get('prompt_type', 'baseline'),
                            difficulty=result.get('difficulty', 'easy')
                        )
                        
                        # 设置其他字段（保持原有逻辑）
                        for field in ['timestamp', 'success', 'success_level', 'execution_time', 'turns',
                                    'tool_calls', 'workflow_score', 'phase2_score', 'quality_score',
                                    'final_score', 'error_type', 'tool_success_rate', 'is_flawed',
                                    'flaw_type', 'format_error_count', 'api_issues', 'executed_tools',
                                    'required_tools', 'tool_coverage_rate', 'task_instance', 'execution_history',
                                    'ai_error_category', '_ai_error_category']:
                            if field in result:
                                if field == '_ai_error_category':
                                    setattr(record, 'ai_error_category', result[field])
                                else:
                                    setattr(record, field, result[field])
                        
                        # 保存记录
                        try:
                            self.manager.append_test_result(record.__dict__)
                            result['_saved'] = True
                            saved_count += 1
                        except Exception as e:
                            print(f"保存记录失败: {e}")
                
                print(f"✅ Checkpoint完成: 成功保存 {saved_count}/{len(self.pending_results)} 个结果")
                
                # 清空已保存的结果
                self.pending_results = [r for r in self.pending_results if not r.get('_saved', False)]
                self._last_checkpoint_time = current_time
                
            except Exception as e:
                print(f"❌ Checkpoint失败: {e}")
                import traceback
                traceback.print_exc()
'''
            
            # 2. 添加退出处理器
            exit_handler_code = '''
    def _setup_exit_handlers(self):
        """设置进程退出处理器"""
        import atexit
        import signal
        
        def cleanup_handler():
            if hasattr(self, 'pending_results') and self.pending_results:
                print(f"\\n🚨 进程退出，强制保存 {len(self.pending_results)} 个未保存结果...")
                self._smart_checkpoint_save([], force=True)
        
        def signal_handler(signum, frame):
            print(f"\\n🚨 收到信号 {signum}，准备退出...")
            cleanup_handler()
        
        atexit.register(cleanup_handler)
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except:
            pass  # 某些环境下可能不支持信号处理
'''
            
            # 3. 修改初始化方法
            init_modification = '''        # 启用智能checkpoint和退出处理
        self._adaptive_checkpoint = True
        self._last_checkpoint_time = time.time()
        self._setup_exit_handlers()
        
        print(f"[DEBUG] BatchTestRunner initialized with save_logs={save_logs}, enable_database_updates={enable_database_updates}, use_ai_classification={use_ai_classification}, checkpoint_interval={checkpoint_interval}")
        print(f"[DEBUG] 智能checkpoint已启用: 自适应阈值={self._adaptive_checkpoint}")'''
            
            # 应用修改
            # 添加import time如果不存在
            if 'import time' not in content:
                content = 'import time\n' + content
            
            # 添加智能checkpoint方法
            if '_smart_checkpoint_save' not in content:
                # 在类定义中找个合适的位置插入
                class_pattern = r'(class BatchTestRunner:[\s\S]*?def __init__[\s\S]*?def _lazy_init\(self\):[\s\S]*?def )'
                if re.search(class_pattern, content):
                    content = re.sub(
                        r'(def _lazy_init\(self\):[\s\S]*?)(\n    def )',
                        r'\1' + smart_checkpoint_method + r'\2',
                        content
                    )
                else:
                    # 简单插入到类的末尾
                    content = content.replace(
                        'class BatchTestRunner:',
                        'class BatchTestRunner:' + smart_checkpoint_method
                    )
            
            # 添加退出处理器方法
            if '_setup_exit_handlers' not in content:
                content = content.replace(
                    smart_checkpoint_method,
                    smart_checkpoint_method + exit_handler_code
                )
            
            # 修改初始化部分
            old_debug_pattern = r'print\(f"\[DEBUG\] BatchTestRunner initialized.*?\)"'
            if re.search(old_debug_pattern, content):
                content = re.sub(old_debug_pattern, init_modification.strip().split('\n')[-2], content)
                # 在初始化的合适位置添加其他代码
                init_pattern = r'(self\.pending_results = \[\].*?\n)'
                content = re.sub(
                    init_pattern,
                    init_modification,
                    content,
                    flags=re.DOTALL
                )
            
            # 替换原有的_checkpoint_save为智能版本
            if '_checkpoint_save' in content and '_smart_checkpoint_save' in content:
                content = content.replace('self._checkpoint_save(', 'self._smart_checkpoint_save(')
            
            # 写入修改后的内容
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("✅ batch_test_runner.py 集成完成")
            return True
            
        except Exception as e:
            logger.error(f"batch_test_runner.py 集成失败: {e}")
            # 恢复备份
            backup_file = self.backup_dir / "batch_test_runner.py"
            if backup_file.exists():
                shutil.copy2(backup_file, target_file)
            return False
    
    def _create_integration_config(self) -> bool:
        """创建集成配置文件"""
        logger.info("📄 创建集成配置文件...")
        
        config_content = '''#!/usr/bin/env python3
"""
智能数据收集器配置文件
为不同的使用场景提供预设配置
"""

import os
from pathlib import Path

# 基础配置
BASE_CONFIG = {
    'temp_dir': 'temp_results',
    'adaptive_threshold': True,
    'auto_save_interval': 60,  # 1分钟
}

# 小规模测试配置（<10个测试）
SMALL_SCALE_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 3,
    'max_time_seconds': 120,  # 2分钟
    'checkpoint_interval': 1,  # 每个测试都保存
}

# 中等规模测试配置（10-50个测试）
MEDIUM_SCALE_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 10,
    'max_time_seconds': 300,  # 5分钟
    'checkpoint_interval': 5,
}

# 大规模测试配置（>50个测试）
LARGE_SCALE_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 25,
    'max_time_seconds': 600,  # 10分钟
    'checkpoint_interval': 20,
}

# 超并发配置（多进程环境）
ULTRA_PARALLEL_CONFIG = {
    **BASE_CONFIG,
    'max_memory_results': 5,   # 更小的内存阈值
    'max_time_seconds': 180,   # 3分钟
    'auto_save_interval': 30,  # 30秒更频繁检查
    'checkpoint_interval': 3,
}

# 环境变量配置映射
ENV_CONFIG_MAP = {
    'small': SMALL_SCALE_CONFIG,
    'medium': MEDIUM_SCALE_CONFIG,
    'large': LARGE_SCALE_CONFIG,
    'ultra': ULTRA_PARALLEL_CONFIG,
}

def get_smart_collector_config(scale: str = None, num_tests: int = None) -> dict:
    """
    获取智能收集器配置
    
    Args:
        scale: 规模类型 ('small', 'medium', 'large', 'ultra')
        num_tests: 预期测试数量
    
    Returns:
        配置字典
    """
    # 从环境变量获取
    if scale is None:
        scale = os.environ.get('COLLECTOR_SCALE', '').lower()
    
    # 根据测试数量自动判断规模
    if scale == '' and num_tests:
        if num_tests <= 10:
            scale = 'small'
        elif num_tests <= 50:
            scale = 'medium'
        elif num_tests <= 200:
            scale = 'large'
        else:
            scale = 'ultra'
    
    # 获取配置
    config = ENV_CONFIG_MAP.get(scale, MEDIUM_SCALE_CONFIG)
    
    # 如果有具体的测试数量，进一步优化
    if num_tests:
        config = config.copy()
        config['max_memory_results'] = min(config['max_memory_results'], max(1, num_tests // 5))
        config['checkpoint_interval'] = min(config['checkpoint_interval'], max(1, num_tests // 3))
    
    return config

def get_current_config() -> dict:
    """获取当前环境的推荐配置"""
    # 检查环境变量
    scale = os.environ.get('COLLECTOR_SCALE', '').lower()
    num_tests = os.environ.get('NUM_TESTS')
    
    if num_tests:
        try:
            num_tests = int(num_tests)
        except:
            num_tests = None
    
    return get_smart_collector_config(scale, num_tests)

# 导出配置检查功能
def validate_config(config: dict) -> list:
    """验证配置的合理性"""
    issues = []
    
    if config.get('max_memory_results', 0) <= 0:
        issues.append("max_memory_results 必须大于0")
    
    if config.get('checkpoint_interval', 0) > config.get('max_memory_results', 0) * 2:
        issues.append("checkpoint_interval 过大，可能导致数据不保存")
    
    if config.get('max_time_seconds', 0) <= 0:
        issues.append("max_time_seconds 必须大于0")
    
    return issues

if __name__ == "__main__":
    # 显示当前推荐配置
    config = get_current_config()
    print("当前推荐配置:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    # 验证配置
    issues = validate_config(config)
    if issues:
        print("\\n配置问题:")
        for issue in issues:
            print(f"  ⚠️ {issue}")
    else:
        print("\\n✅ 配置验证通过")
'''
        
        try:
            config_file = self.workspace_root / "smart_collector_config.py"
            with open(config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            logger.info(f"✅ 配置文件创建完成: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"配置文件创建失败: {e}")
            return False
    
    def _create_usage_guide(self) -> bool:
        """创建使用指南"""
        guide_content = '''# 智能数据收集器使用指南

## 概述

智能数据收集器已集成到现有的测试系统中，提供了更灵活、可靠的数据管理机制。

## 关键改进

### 1. 多重触发条件
不再依赖单一的数量阈值，支持：
- **数量触发**: 达到指定数量的结果
- **时间触发**: 超过指定时间间隔
- **智能触发**: 根据情况动态调整阈值
- **强制触发**: 进程退出时自动保存

### 2. 自适应配置
系统会根据实际测试规模自动调整参数：
- 小规模测试（<10个）：低阈值，快速保存
- 中等规模测试（10-50个）：平衡阈值
- 大规模测试（>50个）：高阈值，批量优化

### 3. 容错机制
- **进程退出保护**: 异常退出时自动保存未处理数据
- **多级回退**: 智能收集器 → 原始收集器 → 简单模式
- **数据恢复**: 从临时文件恢复丢失的数据

## 使用方法

### 基本使用（无需修改现有代码）
```bash
# 现有的测试命令将自动使用智能收集器
./run_systematic_test_final.sh --phase 5.1

# 或
python3 smart_batch_runner.py --model test_model --num-instances 10
```

### 环境变量配置
```bash
# 设置收集器规模
export COLLECTOR_SCALE=small    # 小规模测试
export COLLECTOR_SCALE=medium   # 中等规模测试  
export COLLECTOR_SCALE=large    # 大规模测试
export COLLECTOR_SCALE=ultra    # 超并发测试

# 设置预期测试数量（自动优化配置）
export NUM_TESTS=15

# 启用智能收集器
export USE_SMART_COLLECTOR=true
```

### 手动配置
如果需要精确控制，可以修改配置：

```python
# 在 smart_collector_config.py 中
CUSTOM_CONFIG = {
    'max_memory_results': 5,    # 5个结果触发保存
    'max_time_seconds': 180,    # 3分钟超时保存
    'auto_save_interval': 60,   # 1分钟自动检查
    'adaptive_threshold': True, # 启用自适应
    'checkpoint_interval': 3,   # 每3个测试保存
}
```

## 故障排除

### 1. 数据没有保存
检查以下几点：
- 确认 `temp_results` 目录存在
- 检查是否有权限写入文件
- 查看日志中的错误信息
- 运行 `python3 smart_collector_config.py` 检查配置

### 2. 性能问题
如果保存过于频繁：
- 增加 `max_memory_results`
- 增加 `max_time_seconds`
- 设置 `COLLECTOR_SCALE=large`

如果保存不够及时：
- 减少 `max_memory_results`
- 减少 `max_time_seconds`  
- 设置 `COLLECTOR_SCALE=small`

### 3. 恢复丢失的数据
```python
# 从临时文件恢复
from result_collector_adapter import create_adaptive_collector

collector = create_adaptive_collector()
recovered_data = collector.collect_all_results()
print(f"恢复了 {len(recovered_data)} 条记录")
```

### 4. 调试信息
增加详细日志：
```bash
export DEBUG_COLLECTOR=true
python3 smart_batch_runner.py --model test_model
```

## 配置参考

| 参数 | 小规模 | 中等规模 | 大规模 | 超并发 |
|------|--------|----------|--------|--------|
| max_memory_results | 3 | 10 | 25 | 5 |
| max_time_seconds | 120 | 300 | 600 | 180 |
| checkpoint_interval | 1 | 5 | 20 | 3 |
| auto_save_interval | 60 | 60 | 60 | 30 |

## 监控和统计

检查收集器状态：
```python
from result_collector_adapter import create_adaptive_collector

collector = create_adaptive_collector()
stats = collector.get_stats()
print(f"当前状态: {stats}")
```

## 注意事项

1. **向后兼容**: 现有代码无需修改即可使用新功能
2. **渐进升级**: 可以选择性启用新特性
3. **安全第一**: 所有修改都有备份，可以随时回滚
4. **监控重要**: 定期检查数据完整性和系统性能

## 获取帮助

如果遇到问题：
1. 检查备份目录中的原始文件
2. 查看 `data_collection_diagnosis_report.md`
3. 运行 `python3 fix_data_collection.py` 进行诊断
4. 查看系统日志获取详细错误信息
'''
        
        try:
            guide_file = self.workspace_root / "SMART_COLLECTOR_GUIDE.md"
            with open(guide_file, 'w', encoding='utf-8') as f:
                f.write(guide_content)
            
            logger.info(f"✅ 使用指南创建完成: {guide_file}")
            return True
            
        except Exception as e:
            logger.error(f"使用指南创建失败: {e}")
            return False


def main():
    """主函数"""
    print("🚀 智能数据收集器集成工具")
    print("=" * 60)
    
    integrator = SmartCollectorIntegrator()
    
    print("📋 集成计划:")
    print("  1. 备份现有文件")
    print("  2. 集成智能收集器到 smart_batch_runner.py")
    print("  3. 集成智能checkpoint到 batch_test_runner.py") 
    print("  4. 创建配置文件和使用指南")
    print()
    
    # 执行集成
    results = integrator.integrate_all()
    
    # 显示结果
    print("🎯 集成结果:")
    print(f"  备份创建: {'✅' if results['backup_created'] else '❌'}")
    print(f"  文件修改: {len(results['files_modified'])} 个")
    for file in results['files_modified']:
        print(f"    ✅ {file}")
    
    if results['files_failed']:
        print(f"  失败文件: {len(results['files_failed'])} 个")
        for file in results['files_failed']:
            print(f"    ❌ {file}")
    
    print(f"  新增文件: {len(results['new_files_created'])} 个")
    for file in results['new_files_created']:
        print(f"    📄 {file}")
    
    print(f"\n🎉 集成{'成功' if results['integration_success'] else '失败'}!")
    
    if results['integration_success']:
        print("\n✅ 下一步操作:")
        print("1. 查看 SMART_COLLECTOR_GUIDE.md 了解使用方法")
        print("2. 运行 python3 smart_collector_config.py 检查配置")
        print("3. 测试现有的批处理脚本确认功能正常")
        print("4. 根据需要调整环境变量 (COLLECTOR_SCALE, NUM_TESTS)")
    else:
        print("\n❌ 集成失败，可以从备份目录恢复:")
        print(f"   {integrator.backup_dir}")


if __name__ == "__main__":
    main()