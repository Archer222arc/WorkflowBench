#!/usr/bin/env python3
"""调试parameter_error缺陷测试的超时问题"""

import sys
import json
import time
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from batch_test_runner import BatchTestRunner, TestTask

def test_parameter_error():
    """测试单个parameter_error缺陷案例"""
    print("\n" + "="*50)
    print("测试 Parameter Error 缺陷")
    print("="*50)
    
    # 创建测试运行器
    runner = BatchTestRunner(debug=True, silent=False)
    
    # 创建测试任务
    task = TestTask(
        model='gpt-4o-mini',  # 使用快速的模型
        task_type='simple_task',
        prompt_type='flawed',
        difficulty='easy',
        is_flawed=True,
        flaw_type='parameter_error',
        tool_success_rate=0.8,
        timeout=30  # 使用较短的超时时间便于调试
    )
    
    print(f"\n测试任务: {task}")
    print("\n开始测试...")
    
    start_time = time.time()
    
    try:
        # 运行测试
        result = runner.run_single_test(
            model=task.model,
            task_type=task.task_type,
            prompt_type=task.prompt_type,
            is_flawed=task.is_flawed,
            flaw_type=task.flaw_type,
            timeout=task.timeout,
            tool_success_rate=task.tool_success_rate,
            difficulty=task.difficulty
        )
        
        elapsed = time.time() - start_time
        
        # 显示结果
        print(f"\n测试完成，耗时: {elapsed:.2f}秒")
        print(f"成功: {result.get('success', False)}")
        
        if result.get('error'):
            print(f"错误: {result['error']}")
            
        if result.get('execution_history'):
            print(f"\n执行历史 ({len(result['execution_history'])} 轮):")
            for i, turn in enumerate(result['execution_history'][:3], 1):
                print(f"  第{i}轮: {turn.get('action', 'N/A')}")
                
        # 保存详细结果
        output_file = Path('debug_parameter_error_result.json')
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n详细结果已保存到: {output_file}")
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n测试失败，耗时: {elapsed:.2f}秒")
        print(f"异常: {str(e)}")
        import traceback
        traceback.print_exc()
        
    return result

def check_flawed_generator():
    """检查FlawedWorkflowGenerator是否正常工作"""
    print("\n" + "="*50)
    print("检查 Flawed Workflow Generator")
    print("="*50)
    
    from batch_test_runner import BatchTestRunner
    
    runner = BatchTestRunner(debug=True, silent=False)
    runner._lazy_init()
    
    # 生成一个正常的工作流
    print("\n1. 生成正常工作流...")
    task_dict = {
        'id': 'test_001',
        'description': 'Test task for debugging',
        'task_type': 'simple_task',
        'required_tools': ['tool1', 'tool2'],
        'expected_outputs': {}
    }
    
    normal_workflow = runner.generator.generate_workflow(
        'simple_task',
        task_instance=task_dict
    )
    
    if normal_workflow:
        print(f"   ✓ 正常工作流生成成功")
        print(f"   步骤数: {len(normal_workflow.get('optimal_sequence', []))}")
    else:
        print(f"   ✗ 正常工作流生成失败")
        return
    
    # 注入parameter_error缺陷
    print("\n2. 注入parameter_error缺陷...")
    try:
        flawed_workflow = runner.flawed_generator.inject_specific_flaw(
            normal_workflow, 
            'parameter_error'
        )
        
        if flawed_workflow:
            print(f"   ✓ 缺陷注入成功")
            print(f"   步骤数: {len(flawed_workflow.get('optimal_sequence', []))}")
            
            # 比较前后差异
            normal_seq = normal_workflow.get('optimal_sequence', [])
            flawed_seq = flawed_workflow.get('optimal_sequence', [])
            
            if normal_seq != flawed_seq:
                print(f"   ✓ 工作流已被修改")
                # 找出差异
                for i, (n, f) in enumerate(zip(normal_seq[:3], flawed_seq[:3])):
                    if n != f:
                        print(f"   第{i+1}步差异:")
                        print(f"     正常: {n.get('tool', 'N/A')}")
                        print(f"     缺陷: {f.get('tool', 'N/A')}")
            else:
                print(f"   ✗ 工作流未被修改（可能是问题所在）")
        else:
            print(f"   ✗ 缺陷注入失败")
            
    except Exception as e:
        print(f"   ✗ 缺陷注入异常: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 先检查生成器
    check_flawed_generator()
    
    # 然后运行测试
    print("\n" + "="*50)
    result = test_parameter_error()
    
    # 显示总结
    print("\n" + "="*50)
    print("测试总结")
    print("="*50)
    if result.get('success'):
        print("✅ 测试成功")
    else:
        print("❌ 测试失败")
        if result.get('error'):
            print(f"   原因: {result['error']}")