#!/usr/bin/env python3
"""测试API超时机制"""

import sys
import time
import threading
from openai import OpenAI, AzureOpenAI

def test_timeout_settings():
    """检查OpenAI客户端的超时设置"""
    print("=" * 60)
    print("API客户端超时设置分析")
    print("=" * 60)
    
    # 1. 默认客户端
    print("\n1. 默认OpenAI客户端:")
    client = OpenAI(api_key="test_key")
    print(f"   默认timeout: {client.timeout}")
    print(f"   类型: {type(client.timeout)}")
    
    # 检查httpx timeout对象的属性
    if hasattr(client.timeout, '__dict__'):
        for attr, value in client.timeout.__dict__.items():
            print(f"   {attr}: {value}")
    
    # 2. 自定义超时设置
    print("\n2. 自定义超时设置:")
    import httpx
    custom_client = OpenAI(
        api_key="test_key",
        timeout=httpx.Timeout(
            connect=5.0,
            read=150.0,
            write=10.0,
            pool=None
        )
    )
    print(f"   Connect timeout: {custom_client.timeout.connect}")
    print(f"   Read timeout: {custom_client.timeout.read}")
    print(f"   Write timeout: {custom_client.timeout.write}")
    print(f"   Pool timeout: {custom_client.timeout.pool}")
    
    # 3. 简单超时设置
    print("\n3. 简单超时设置 (单个数值):")
    simple_client = OpenAI(api_key="test_key", timeout=30.0)
    print(f"   Timeout: {simple_client.timeout}")
    
    print("\n" + "=" * 60)
    print("分析结果:")
    print("-" * 60)
    print("1. OpenAI客户端使用httpx作为HTTP客户端")
    print("2. 默认超时是600秒（10分钟）")
    print("3. chat.completions.create()的timeout参数会覆盖客户端默认值")
    print("4. 超时包含多个阶段：connect, read, write, pool")
    print("=" * 60)

def simulate_api_call_timeout():
    """模拟API调用超时场景"""
    print("\n模拟API调用超时场景:")
    print("-" * 60)
    
    # 模拟网络层面的问题
    print("\n可能导致永久阻塞的场景:")
    print("1. TCP连接建立后，服务器不发送任何数据")
    print("2. 服务器发送部分响应后停止")
    print("3. 网络中断但TCP连接未正确关闭")
    print("4. 防火墙静默丢弃包")
    print("5. SSL/TLS握手卡住")
    
    print("\n当前超时链:")
    print("├── interactive_executor.py: timeout=150秒")
    print("│   └── llm_client.chat.completions.create(timeout=150)")
    print("│       └── httpx请求: timeout=150秒")
    print("│           ├── connect: 150秒")
    print("│           ├── read: 150秒")
    print("│           └── write: 150秒")
    print("└── 问题: 如果read阶段卡住，需要等待完整的150秒")

def analyze_blocking_issue():
    """分析为什么会出现8小时阻塞"""
    print("\n" + "=" * 60)
    print("8小时阻塞原因分析")
    print("=" * 60)
    
    print("\n1. Python GIL的影响:")
    print("   - 线程中的阻塞I/O不会释放GIL")
    print("   - 其他线程无法强制中断")
    
    print("\n2. httpx/requests的底层实现:")
    print("   - 使用socket的recv()操作")
    print("   - 如果服务器保持连接但不发送数据，recv()会永久等待")
    
    print("\n3. TCP Keep-Alive机制:")
    print("   - macOS默认: tcp_keepalive_time = 7200秒（2小时）")
    print("   - tcp_keepalive_intvl = 75秒")
    print("   - tcp_keepalive_probes = 8")
    print("   - 总计: 2小时 + 75*8 = 2小时10分钟才检测到连接死亡")
    print("   - 加上重试和其他延迟，可能累积到8小时")
    
    print("\n4. OpenAI API特殊情况:")
    print("   - 流式响应（SSE）可能导致部分读取后卡住")
    print("   - 某些错误状态下服务器不正确关闭连接")

if __name__ == "__main__":
    test_timeout_settings()
    simulate_api_call_timeout()
    analyze_blocking_issue()