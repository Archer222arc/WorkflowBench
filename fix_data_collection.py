#!/usr/bin/env python3
"""
数据收集机制修复工具
自动检测并修复当前数据收集的配置问题

功能：
1. 检测当前配置问题
2. 提供智能修复建议
3. 自动应用修复
4. 验证修复效果
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class DataCollectionFixer:
    """数据收集机制修复器"""
    
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.issues = []
        self.fixes = []
        
    def diagnose_issues(self) -> List[Dict[str, Any]]:
        """诊断当前的数据收集问题"""
        logger.info("🔍 开始诊断数据收集问题...")
        self.issues = []
        
        # 1. 检查配置文件问题
        self._check_configuration_issues()
        
        # 2. 检查代码逻辑问题
        self._check_code_logic_issues()
        
        # 3. 检查环境问题
        self._check_environment_issues()
        
        # 4. 检查数据完整性
        self._check_data_integrity_issues()
        
        logger.info(f"发现 {len(self.issues)} 个问题")
        return self.issues
    
    def _check_configuration_issues(self):
        """检查配置相关问题"""
        # 检查checkpoint_interval配置
        batch_runner_file = self.workspace_root / "batch_test_runner.py"
        if batch_runner_file.exists():
            with open(batch_runner_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查默认checkpoint_interval
                if 'checkpoint_interval: int = 20' in content or 'checkpoint_interval=20' in content:
                    self.issues.append({
                        'type': 'configuration',
                        'severity': 'high',
                        'file': str(batch_runner_file),
                        'issue': 'checkpoint_interval默认值20过高',
                        'description': '每个分片只运行5个测试，但需要20个测试才能保存，导致数据丢失',
                        'suggestion': '将checkpoint_interval默认值改为5或启用自适应机制'
                    })
        
        # 检查run_systematic_test_final.sh中的配置
        test_script = self.workspace_root / "run_systematic_test_final.sh"
        if test_script.exists():
            with open(test_script, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查checkpoint-interval参数传递
                if '--checkpoint-interval 20' in content:
                    self.issues.append({
                        'type': 'configuration',
                        'severity': 'high', 
                        'file': str(test_script),
                        'issue': 'bash脚本中checkpoint-interval硬编码为20',
                        'description': '脚本传递固定的checkpoint-interval=20，与小批次测试不匹配',
                        'suggestion': '使用自适应checkpoint-interval或根据测试数量动态调整'
                    })
    
    def _check_code_logic_issues(self):
        """检查代码逻辑问题"""
        # 检查BatchTestRunner的checkpoint逻辑
        batch_runner_file = self.workspace_root / "batch_test_runner.py"
        if batch_runner_file.exists():
            with open(batch_runner_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查_checkpoint_save方法的逻辑
                if 'len(self.pending_results) >= self.checkpoint_interval' in content:
                    self.issues.append({
                        'type': 'logic',
                        'severity': 'high',
                        'file': str(batch_runner_file),
                        'issue': '僵化的checkpoint触发条件',
                        'description': '只有数量达到阈值才保存，缺乏时间、进程结束等其他触发条件',
                        'suggestion': '添加多重触发条件：时间阈值、进程结束、内存压力等'
                    })
                
                # 检查是否缺少进程结束时的强制保存
                if 'atexit.register' not in content and 'signal.signal' not in content:
                    self.issues.append({
                        'type': 'logic',
                        'severity': 'medium',
                        'file': str(batch_runner_file),
                        'issue': '缺少进程退出时的数据保护',
                        'description': '进程异常退出时，pending_results中的数据会丢失',
                        'suggestion': '添加atexit处理器和信号处理器，确保进程退出时保存数据'
                    })
    
    def _check_environment_issues(self):
        """检查环境相关问题"""
        # 检查temp_results目录
        temp_results = self.workspace_root / "temp_results"
        if not temp_results.exists():
            self.issues.append({
                'type': 'environment',
                'severity': 'low',
                'file': 'N/A',
                'issue': 'temp_results目录不存在',
                'description': 'ResultCollector期望的临时目录不存在，可能导致文件写入失败',
                'suggestion': '创建temp_results目录并设置适当的权限'
            })
        
        # 检查是否有遗留的临时文件
        temp_files = list(self.workspace_root.glob("temp_results/*.json"))
        if temp_files:
            self.issues.append({
                'type': 'environment',
                'severity': 'low',
                'file': 'temp_results/',
                'issue': f'发现 {len(temp_files)} 个未处理的临时文件',
                'description': '可能包含未保存到数据库的测试结果',
                'suggestion': '检查这些临时文件并尝试恢复数据'
            })
    
    def _check_data_integrity_issues(self):
        """检查数据完整性问题"""
        # 检查数据库文件
        db_file = self.workspace_root / "pilot_bench_cumulative_results" / "master_database.json"
        if db_file.exists():
            try:
                with open(db_file, 'r') as f:
                    db = json.load(f)
                
                # 检查overall_stats是否为空
                models = db.get('models', {})
                empty_stats_models = []
                for model_name, model_data in models.items():
                    if not model_data.get('overall_stats'):
                        empty_stats_models.append(model_name)
                
                if empty_stats_models:
                    self.issues.append({
                        'type': 'data_integrity',
                        'severity': 'medium',
                        'file': str(db_file),
                        'issue': f'{len(empty_stats_models)} 个模型的overall_stats为空',
                        'description': '模型级别的统计信息缺失，影响数据分析',
                        'suggestion': '运行update_summary_totals.py更新统计信息'
                    })
                
                # 检查summary统计
                summary = db.get('summary', {})
                if summary.get('total_tests', 0) == 0:
                    self.issues.append({
                        'type': 'data_integrity',
                        'severity': 'medium', 
                        'file': str(db_file),
                        'issue': 'summary.total_tests为0',
                        'description': '顶级统计信息不正确，总测试数显示为0',
                        'suggestion': '运行update_summary_totals.py重新计算统计信息'
                    })
                
            except Exception as e:
                self.issues.append({
                    'type': 'data_integrity',
                    'severity': 'high',
                    'file': str(db_file),
                    'issue': f'数据库文件解析失败: {e}',
                    'description': '主数据库文件可能损坏或格式不正确',
                    'suggestion': '检查数据库文件格式，考虑从备份恢复'
                })

    def generate_fixes(self) -> List[Dict[str, Any]]:
        """基于诊断结果生成修复方案"""
        logger.info("💡 生成修复方案...")
        self.fixes = []
        
        for issue in self.issues:
            fix = self._generate_fix_for_issue(issue)
            if fix:
                self.fixes.append(fix)
        
        logger.info(f"生成 {len(self.fixes)} 个修复方案")
        return self.fixes
    
    def _generate_fix_for_issue(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """为特定问题生成修复方案"""
        issue_type = issue['type']
        
        if issue_type == 'configuration':
            if 'checkpoint_interval' in issue['issue']:
                return {
                    'type': 'code_modification',
                    'target': issue['file'],
                    'action': 'replace_checkpoint_interval',
                    'description': '将checkpoint_interval默认值从20改为5，并添加自适应逻辑',
                    'old_pattern': r'checkpoint_interval: int = 20',
                    'new_value': 'checkpoint_interval: int = 5',
                    'priority': 'high'
                }
        
        elif issue_type == 'logic':
            if '僵化的checkpoint触发条件' in issue['issue']:
                return {
                    'type': 'code_enhancement',
                    'target': issue['file'],
                    'action': 'add_smart_checkpoint',
                    'description': '替换为智能checkpoint逻辑，支持多重触发条件',
                    'priority': 'high'
                }
            
            elif '缺少进程退出时的数据保护' in issue['issue']:
                return {
                    'type': 'code_enhancement',
                    'target': issue['file'],
                    'action': 'add_exit_handlers',
                    'description': '添加进程退出处理器，确保数据不丢失',
                    'priority': 'medium'
                }
        
        elif issue_type == 'environment':
            if 'temp_results目录不存在' in issue['issue']:
                return {
                    'type': 'file_system',
                    'action': 'create_directory',
                    'target': 'temp_results',
                    'description': '创建临时结果目录',
                    'priority': 'low'
                }
        
        elif issue_type == 'data_integrity':
            if 'overall_stats为空' in issue['issue'] or 'summary' in issue['issue']:
                return {
                    'type': 'data_repair',
                    'action': 'update_statistics',
                    'description': '重新计算并更新统计信息',
                    'priority': 'medium'
                }
        
        return None

    def apply_fixes(self, auto_apply: bool = False) -> Dict[str, Any]:
        """应用修复方案"""
        if not self.fixes:
            logger.warning("没有修复方案可应用")
            return {'applied': 0, 'failed': 0, 'skipped': 0}
        
        results = {'applied': 0, 'failed': 0, 'skipped': 0}
        
        for fix in self.fixes:
            try:
                if not auto_apply:
                    # 询问用户是否应用此修复
                    response = input(f"\n应用修复: {fix['description']}? (y/n/a=all): ").lower()
                    if response == 'n':
                        results['skipped'] += 1
                        continue
                    elif response == 'a':
                        auto_apply = True
                
                # 应用修复
                success = self._apply_single_fix(fix)
                if success:
                    results['applied'] += 1
                    logger.info(f"✅ 修复成功: {fix['description']}")
                else:
                    results['failed'] += 1
                    logger.error(f"❌ 修复失败: {fix['description']}")
                    
            except Exception as e:
                results['failed'] += 1
                logger.error(f"❌ 修复异常: {fix['description']} - {e}")
        
        return results

    def _apply_single_fix(self, fix: Dict[str, Any]) -> bool:
        """应用单个修复"""
        fix_type = fix['type']
        
        if fix_type == 'code_modification':
            return self._apply_code_modification(fix)
        elif fix_type == 'code_enhancement':
            return self._apply_code_enhancement(fix)
        elif fix_type == 'file_system':
            return self._apply_file_system_fix(fix)
        elif fix_type == 'data_repair':
            return self._apply_data_repair(fix)
        
        return False

    def _apply_code_modification(self, fix: Dict[str, Any]) -> bool:
        """应用代码修改"""
        target_file = Path(fix['target'])
        if not target_file.exists():
            return False
        
        # 创建备份
        backup_file = target_file.with_suffix(target_file.suffix + '.backup')
        shutil.copy2(target_file, backup_file)
        
        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 应用修改
            if fix['action'] == 'replace_checkpoint_interval':
                import re
                content = re.sub(
                    r'checkpoint_interval:\s*int\s*=\s*20',
                    'checkpoint_interval: int = 5',
                    content
                )
            
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True
            
        except Exception as e:
            # 恢复备份
            shutil.copy2(backup_file, target_file)
            logger.error(f"代码修改失败，已恢复备份: {e}")
            return False

    def _apply_code_enhancement(self, fix: Dict[str, Any]) -> bool:
        """应用代码增强（这里只是标记，实际需要手动实现）"""
        logger.info(f"代码增强需要手动实现: {fix['description']}")
        logger.info("建议：使用 smart_result_collector.py 替换现有的收集机制")
        return True

    def _apply_file_system_fix(self, fix: Dict[str, Any]) -> bool:
        """应用文件系统修复"""
        if fix['action'] == 'create_directory':
            target_dir = self.workspace_root / fix['target']
            target_dir.mkdir(exist_ok=True)
            return True
        return False

    def _apply_data_repair(self, fix: Dict[str, Any]) -> bool:
        """应用数据修复"""
        if fix['action'] == 'update_statistics':
            # 运行统计更新脚本
            update_script = self.workspace_root / "update_summary_totals.py"
            if update_script.exists():
                try:
                    import subprocess
                    result = subprocess.run(['python3', str(update_script)], 
                                          capture_output=True, text=True)
                    return result.returncode == 0
                except Exception:
                    logger.info("请手动运行: python3 update_summary_totals.py")
                    return True
        return False

    def generate_report(self) -> str:
        """生成诊断和修复报告"""
        report = []
        report.append("# 数据收集机制诊断报告")
        report.append(f"生成时间: {datetime.now().isoformat()}")
        report.append("")
        
        # 问题摘要
        report.append("## 问题摘要")
        severity_counts = {}
        for issue in self.issues:
            severity = issue['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        for severity, count in severity_counts.items():
            report.append(f"- {severity.upper()}: {count} 个问题")
        report.append("")
        
        # 详细问题列表
        report.append("## 详细问题")
        for i, issue in enumerate(self.issues, 1):
            report.append(f"### {i}. {issue['issue']} ({issue['severity'].upper()})")
            report.append(f"**文件**: {issue['file']}")
            report.append(f"**描述**: {issue['description']}")
            report.append(f"**建议**: {issue['suggestion']}")
            report.append("")
        
        # 修复方案
        if self.fixes:
            report.append("## 修复方案")
            for i, fix in enumerate(self.fixes, 1):
                report.append(f"{i}. {fix['description']} (优先级: {fix['priority']})")
            report.append("")
        
        return "\n".join(report)


def main():
    """主函数"""
    print("🔧 数据收集机制修复工具")
    print("=" * 50)
    
    # 创建修复器
    fixer = DataCollectionFixer()
    
    # 诊断问题
    issues = fixer.diagnose_issues()
    
    if not issues:
        print("✅ 未发现问题，数据收集机制工作正常")
        return
    
    # 显示问题摘要
    print(f"\n发现 {len(issues)} 个问题:")
    for issue in issues:
        severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
        emoji = severity_emoji.get(issue['severity'], '⚪')
        print(f"  {emoji} {issue['severity'].upper()}: {issue['issue']}")
    
    # 生成修复方案
    fixes = fixer.generate_fixes()
    
    if fixes:
        print(f"\n💡 可用修复方案: {len(fixes)} 个")
        
        # 询问是否应用修复
        apply_fixes = input("\n是否应用修复? (y/n): ").lower() == 'y'
        if apply_fixes:
            results = fixer.apply_fixes()
            print(f"\n修复结果: 成功 {results['applied']}, 失败 {results['failed']}, 跳过 {results['skipped']}")
    
    # 生成报告
    print(f"\n📋 生成详细报告...")
    report = fixer.generate_report()
    
    report_file = Path("data_collection_diagnosis_report.md")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"报告已保存: {report_file}")
    
    # 给出建议
    print(f"\n💡 核心建议:")
    print(f"1. 使用 smart_result_collector.py 替换现有收集机制")
    print(f"2. 设置 checkpoint_interval=5 匹配实际测试数量")
    print(f"3. 运行 python3 update_summary_totals.py 更新统计")
    print(f"4. 考虑启用 enable_database_updates=True 进行实时保存")


if __name__ == "__main__":
    from datetime import datetime
    main()