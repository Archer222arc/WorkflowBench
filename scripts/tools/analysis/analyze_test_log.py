#!/usr/bin/env python3
"""
测试日志分析工具 - 用于调试单个测试失败
使用方法：
    python analyze_test_log.py [日志文件路径]
    python analyze_test_log.py --latest DeepSeek  # 查看最新的DeepSeek测试
    python analyze_test_log.py --list  # 列出最新的10个测试日志
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

def analyze_log(log_file_path):
    """分析单个测试日志文件"""
    try:
        with open(log_file_path, 'r') as f:
            log_data = json.load(f)
    except Exception as e:
        print(f"❌ 无法读取日志文件: {e}")
        return
    
    print("\n" + "="*80)
    print("📊 测试日志分析报告")
    print("="*80)
    
    # 基本信息
    print(f"\n📍 基本信息:")
    print(f"  测试ID: {log_data.get('test_id', 'N/A')}")
    print(f"  任务类型: {log_data.get('task_type', 'N/A')}")
    print(f"  提示类型: {log_data.get('prompt_type', 'N/A')}")
    print(f"  时间戳: {log_data.get('timestamp', 'N/A')}")
    print(f"  是否有缺陷: {log_data.get('is_flawed', False)}")
    if log_data.get('flaw_type'):
        print(f"  缺陷类型: {log_data['flaw_type']}")
    
    # 任务实例
    task_instance = log_data.get('task_instance', {})
    if task_instance:
        print(f"\n📋 任务实例:")
        print(f"  任务描述: {task_instance.get('description', 'N/A')[:100]}...")
        required_tools = task_instance.get('required_tools', [])
        if required_tools:
            print(f"  需要的工具: {', '.join(required_tools)}")
    
    # 对话历史分析
    conversation = log_data.get('conversation_history', [])
    print(f"\n💬 对话历史: 共{len(conversation)}条消息")
    
    for i, msg in enumerate(conversation[:6]):  # 只显示前6条
        role = msg.get('role', '')
        content = msg.get('content', '')
        
        if role == 'user':
            print(f"\n  [{i+1}] 👤 用户:")
            # 提取关键信息
            if 'Tool Search Results:' in content:
                print(f"    [工具搜索结果]")
            elif 'Tool Execution Result:' in content:
                print(f"    [工具执行结果]")
            else:
                print(f"    {content[:150]}...")
                
        elif role == 'assistant':
            print(f"\n  [{i+1}] 🤖 助手:")
            # 分析工具调用
            if '<tool_call>' in content:
                import re
                tool_calls = re.findall(r'<tool_call>(.*?)</tool_call>', content)
                print(f"    ✅ 正确格式工具调用: {', '.join(tool_calls)}")
            elif '<tool_search>' in content:
                import re
                tool_searches = re.findall(r'<tool_search>(.*?)</tool_search>', content)
                print(f"    ⚠️ 错误格式(tool_search): {', '.join(tool_searches)}")
            elif '<tool_info>' in content:
                import re
                tool_infos = re.findall(r'<tool_info>(.*?)</tool_info>', content)
                print(f"    ℹ️ 工具信息查询: {', '.join(tool_infos)}")
            else:
                # 显示前200字符
                print(f"    {content[:200]}...")
    
    if len(conversation) > 6:
        print(f"\n  ... 还有 {len(conversation)-6} 条消息未显示")
    
    # 执行历史
    exec_history = log_data.get('execution_history', [])
    print(f"\n⚙️ 执行历史: 共{len(exec_history)}个工具调用")
    
    if exec_history:
        success_count = sum(1 for h in exec_history if h.get('success', False))
        print(f"  成功: {success_count}/{len(exec_history)}")
        
        for i, h in enumerate(exec_history[:5]):
            tool = h.get('tool', 'unknown')
            success = h.get('success', False)
            error = h.get('error')
            
            status = "✅" if success else "❌"
            print(f"  [{i+1}] {status} {tool}")
            if error:
                print(f"      错误: {error[:100]}...")
    
    # 提取的工具调用
    extracted_calls = log_data.get('extracted_tool_calls', [])
    if extracted_calls:
        print(f"\n🔧 提取的工具调用: {', '.join(extracted_calls)}")
    
    # API问题
    api_issues = log_data.get('api_issues', [])
    if api_issues:
        print(f"\n⚠️ API问题: {len(api_issues)}个")
        for issue in api_issues[:3]:
            print(f"  - {issue}")
    
    print("\n" + "="*80)

def list_latest_logs(pattern=None, limit=10):
    """列出最新的测试日志"""
    log_dir = Path('workflow_quality_results/test_logs')
    if not log_dir.exists():
        print("❌ 日志目录不存在")
        return
    
    # 获取所有JSON日志文件
    if pattern:
        log_files = list(log_dir.glob(f'*{pattern}*.json'))
    else:
        log_files = list(log_dir.glob('*.json'))
    
    # 按修改时间排序
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"\n📁 最新的{min(limit, len(log_files))}个测试日志:")
    print("-"*80)
    
    for i, log_file in enumerate(log_files[:limit]):
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        size = log_file.stat().st_size / 1024  # KB
        
        # 解析文件名获取信息
        name_parts = log_file.stem.split('_')
        model = name_parts[0] if name_parts else "unknown"
        
        print(f"{i+1:2}. {log_file.name}")
        print(f"    模型: {model}")
        print(f"    时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    大小: {size:.1f} KB")
        
        # 快速读取测试结果
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)
                task_type = data.get('task_type', 'N/A')
                prompt_type = data.get('prompt_type', 'N/A')
                exec_history = data.get('execution_history', [])
                success = any(h.get('success') for h in exec_history) if exec_history else False
                
                print(f"    任务: {task_type} | 提示: {prompt_type} | 结果: {'✅成功' if success else '❌失败'}")
        except:
            pass
        
        print()

def main():
    parser = argparse.ArgumentParser(description='分析测试日志文件')
    parser.add_argument('log_file', nargs='?', help='日志文件路径')
    parser.add_argument('--latest', help='查看包含指定模式的最新日志')
    parser.add_argument('--list', action='store_true', help='列出最新的日志文件')
    parser.add_argument('--limit', type=int, default=10, help='列出日志的数量限制')
    
    args = parser.parse_args()
    
    if args.list:
        list_latest_logs(limit=args.limit)
    elif args.latest:
        # 找到最新的匹配文件
        log_dir = Path('workflow_quality_results/test_logs')
        matching_files = list(log_dir.glob(f'*{args.latest}*.json'))
        if matching_files:
            matching_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest = matching_files[0]
            print(f"📂 分析最新的 {args.latest} 日志: {latest.name}")
            analyze_log(latest)
        else:
            print(f"❌ 没有找到包含 '{args.latest}' 的日志文件")
    elif args.log_file:
        log_path = Path(args.log_file)
        if log_path.exists():
            analyze_log(log_path)
        else:
            print(f"❌ 文件不存在: {args.log_file}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()