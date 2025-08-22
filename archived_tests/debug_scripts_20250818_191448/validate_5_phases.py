#!/usr/bin/env python3
"""
验证5.1-5.5所有测试阶段的数据保存机制
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

class TestPhaseValidator:
    """测试阶段验证器"""
    
    def __init__(self):
        self.db_path = Path("pilot_bench_cumulative_results/master_database.json")
        self.results = {}
        
    def get_test_count(self, phase_name):
        """获取特定阶段的测试数量"""
        if not self.db_path.exists():
            return 0
            
        with open(self.db_path, 'r') as f:
            db = json.load(f)
            
        # Use the summary total_tests field
        return db.get('summary', {}).get('total_tests', 0)
    
    def run_mini_test(self, phase_config):
        """运行单个最小测试"""
        print(f"\n运行{phase_config['name']}的最小测试...")
        
        # 记录测试前的数量
        before_count = self.get_test_count(phase_config['name'])
        print(f"测试前总数: {before_count}")
        
        # 构建命令
        cmd = [
            'python', 'smart_batch_runner.py',
            '--model', phase_config['model'],
            '--prompt-types', phase_config['prompt_type'],
            '--difficulty', phase_config['difficulty'],
            '--task-types', 'simple_task',
            '--num-instances', '1',
            '--tool-success-rate', str(phase_config['tool_rate']),
            '--batch-commit',  # 使用batch commit
            '--checkpoint-interval', '1',  # 每个测试后保存
            '--max-workers', '1',
            '--no-adaptive',
            '--qps', '10',
            '--no-save-logs'
        ]
        
        print(f"命令: {' '.join(cmd)}")
        
        # 运行测试
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # 等待数据写入
        time.sleep(2)
        
        # 记录测试后的数量
        after_count = self.get_test_count(phase_config['name'])
        print(f"测试后总数: {after_count}")
        
        # 分析结果
        saved = after_count > before_count
        
        # 检查输出中的保存信息
        save_mentioned = False
        if "保存" in result.stdout or "Saving" in result.stdout or "saved" in result.stdout.lower():
            save_mentioned = True
        
        return {
            'phase': phase_config['name'],
            'before': before_count,
            'after': after_count,
            'saved': saved,
            'save_mentioned': save_mentioned,
            'exit_code': result.returncode,
            'success': saved and result.returncode == 0
        }
    
    def validate_all_phases(self):
        """验证所有测试阶段"""
        print("=" * 60)
        print("验证5.1-5.5所有测试阶段的数据保存")
        print("=" * 60)
        
        # 定义每个阶段的配置
        phases = [
            {
                'name': '5.1 基准测试',
                'model': 'gpt-4o-mini',
                'prompt_type': 'optimal',
                'difficulty': 'easy',
                'tool_rate': 0.8
            },
            {
                'name': '5.2 规模效应测试',
                'model': 'qwen2.5-7b-instruct',
                'prompt_type': 'optimal',
                'difficulty': 'medium',
                'tool_rate': 0.8
            },
            {
                'name': '5.3 缺陷工作流测试',
                'model': 'gpt-4o-mini',
                'prompt_type': 'flawed_sequence_disorder',
                'difficulty': 'easy',
                'tool_rate': 0.8
            },
            {
                'name': '5.4 工具可靠性测试',
                'model': 'gpt-4o-mini',
                'prompt_type': 'optimal',
                'difficulty': 'easy',
                'tool_rate': 0.6  # 使用低可靠性
            },
            {
                'name': '5.5 提示敏感性测试',
                'model': 'gpt-4o-mini',
                'prompt_type': 'cot',  # 使用CoT prompt
                'difficulty': 'easy',
                'tool_rate': 0.8
            }
        ]
        
        # 运行每个阶段的测试
        for phase in phases:
            result = self.run_mini_test(phase)
            self.results[phase['name']] = result
            
            # 打印即时结果
            if result['success']:
                print(f"✅ {phase['name']}: 数据保存成功")
            else:
                print(f"❌ {phase['name']}: 数据保存失败")
            
            print("-" * 40)
        
        # 生成总结报告
        self.generate_report()
    
    def generate_report(self):
        """生成验证报告"""
        print("\n" + "=" * 60)
        print("验证报告")
        print("=" * 60)
        
        success_count = 0
        failed_phases = []
        
        print("\n详细结果:")
        print("-" * 40)
        
        for phase_name, result in self.results.items():
            print(f"\n{phase_name}:")
            print(f"  测试前数量: {result['before']}")
            print(f"  测试后数量: {result['after']}")
            print(f"  数据已保存: {'✅' if result['saved'] else '❌'}")
            print(f"  输出提到保存: {'✅' if result['save_mentioned'] else '❌'}")
            print(f"  退出码: {result['exit_code']}")
            print(f"  整体成功: {'✅' if result['success'] else '❌'}")
            
            if result['success']:
                success_count += 1
            else:
                failed_phases.append(phase_name)
        
        print("\n" + "=" * 60)
        print("总结")
        print("=" * 60)
        
        total_phases = len(self.results)
        print(f"\n测试阶段总数: {total_phases}")
        print(f"成功: {success_count}")
        print(f"失败: {total_phases - success_count}")
        print(f"成功率: {success_count/total_phases*100:.1f}%")
        
        if failed_phases:
            print(f"\n❌ 失败的阶段:")
            for phase in failed_phases:
                print(f"  - {phase}")
        else:
            print("\n✅ 所有阶段验证通过！")
        
        # 保存报告
        report_path = Path(f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到: {report_path}")
        
        return success_count == total_phases

def main():
    """主函数"""
    validator = TestPhaseValidator()
    success = validator.validate_all_phases()
    
    if success:
        print("\n🎉 所有测试阶段的数据保存机制验证通过！")
        return 0
    else:
        print("\n⚠️ 部分测试阶段存在问题，请检查")
        return 1

if __name__ == "__main__":
    exit(main())