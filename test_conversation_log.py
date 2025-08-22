#!/usr/bin/env python3
"""
测试对话历史记录的修复
"""

from batch_test_runner import BatchTestRunner, TestTask
from pathlib import Path

def test_conversation_logging():
    """测试对话历史是否正确记录"""
    print("=" * 60)
    print("测试对话历史记录修复")
    print("=" * 60)
    
    # 创建runner
    runner = BatchTestRunner(debug=True, silent=False, save_logs=True)
    
    # 运行测试
    print("\n运行测试...")
    result = runner.run_single_test(
        model='gpt-4o-mini',
        task_type='simple_task',
        prompt_type='baseline',
        difficulty='easy',
        tool_success_rate=0.8
    )
    
    # 检查日志文件
    log_dir = Path("workflow_quality_results/test_logs")
    if log_dir.exists():
        # 找到最新的日志文件
        txt_files = list(log_dir.glob("gpt_4o_mini_*.txt"))
        if txt_files:
            latest = max(txt_files, key=lambda f: f.stat().st_mtime)
            print(f"\n最新日志文件: {latest.name}")
            
            # 读取文件内容，检查Conversation History部分
            with open(latest, 'r') as f:
                content = f.read()
                
            # 查找Conversation History部分
            if "Conversation History:" in content:
                lines = content.split('\n')
                start_idx = None
                for i, line in enumerate(lines):
                    if "Conversation History:" in line:
                        start_idx = i
                        break
                
                if start_idx:
                    # 显示对话历史的前30行
                    print("\n对话历史部分:")
                    print("-" * 40)
                    for i in range(start_idx, min(start_idx + 30, len(lines))):
                        print(lines[i])
                    
                    # 检查是否还有N/A
                    conversation_section = '\n'.join(lines[start_idx:start_idx+50])
                    if "Human: N/A" in conversation_section and "Assistant: N/A" in conversation_section:
                        print("\n⚠️ 仍然存在N/A的对话记录")
                        # 可能是conversation_history确实为空
                        print("这可能意味着conversation_history列表为空或格式不匹配")
                    elif "(No conversation history recorded)" in conversation_section:
                        print("\n⚠️ 没有记录到对话历史")
                    else:
                        print("\n✅ 对话历史记录正常！")
            else:
                print("\n❌ 日志中没有找到Conversation History部分")
        else:
            print("\n❌ 没有找到日志文件")
    else:
        print(f"\n❌ 日志目录不存在: {log_dir}")

if __name__ == "__main__":
    test_conversation_logging()