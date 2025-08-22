#!/usr/bin/env python3
"""
智能批测试运行器 - 缓存版本
使用本地缓存避免实时数据库更新的并发竞争条件
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from local_cache_batch_manager import LocalCacheBatchManager

def main():
    parser = argparse.ArgumentParser(description='智能批测试运行器 - 缓存版本')
    parser.add_argument('--model', required=True, help='模型名称')
    parser.add_argument('--prompt-types', required=True, help='Prompt类型')
    parser.add_argument('--difficulty', default='easy', help='难度')
    parser.add_argument('--task-types', default='all', help='任务类型')
    parser.add_argument('--num-instances', type=int, default=20, help='每种任务的实例数')
    parser.add_argument('--tool-success-rate', type=float, help='工具成功率')
    parser.add_argument('--max-workers', type=int, default=10, help='最大并发数')
    parser.add_argument('--adaptive', action='store_true', default=True, help='使用adaptive模式（默认开启）')
    parser.add_argument('--no-adaptive', dest='adaptive', action='store_false', help='禁用adaptive模式')
    parser.add_argument('--save-logs', action='store_true', default=True, help='保存详细日志（默认开启）')
    parser.add_argument('--no-save-logs', dest='save_logs', action='store_false', help='禁用日志保存')
    parser.add_argument('--silent', action='store_true', help='静默模式')
    parser.add_argument('--qps', type=float, default=20.0, help='QPS限制')
    parser.add_argument('--auto-commit', action='store_true', help='自动提交到数据库（不询问）')
    
    args = parser.parse_args()
    
    # 创建本地缓存管理器
    manager = LocalCacheBatchManager()
    
    try:
        print("=" * 60)
        print("智能批测试运行器 - 本地缓存版本")
        print("=" * 60)
        
        # 规划测试任务
        tasks = manager.plan_model_tests(
            model=args.model,
            prompt_types=args.prompt_types,
            difficulty=args.difficulty,
            task_types=args.task_types,
            num_instances=args.num_instances,
            tool_success_rate=args.tool_success_rate if args.tool_success_rate else 0.8,
            adaptive=args.adaptive
        )
        
        if not tasks:
            print("✅ 所有测试已完成，无需运行新测试")
            sys.exit(0)
        
        print(f"\n📋 已规划 {len(tasks)} 个测试任务")
        
        # 运行缓存的批量测试
        success = manager.run_cached_batch_test(
            tasks=tasks,
            max_workers=args.max_workers,
            adaptive=args.adaptive,
            save_logs=args.save_logs,
            silent=args.silent,
            qps=args.qps
        )
        
        if not success:
            print("❌ 测试运行失败")
            sys.exit(1)
        
        # 决定是否自动提交
        if args.auto_commit:
            print("\n🤖 自动提交模式...")
            commit = True
        else:
            while True:
                response = input("\n💾 测试完成！是否将结果提交到主数据库？(y/n/s): ").strip().lower()
                if response in ['y', 'yes']:
                    commit = True
                    break
                elif response in ['n', 'no']:
                    commit = False
                    break
                elif response in ['s', 'show']:
                    print(f"\n📄 缓存文件位置: {manager.session_cache_path}")
                    print("   包含的测试结果数量:", len(manager.session_cache.get('results', [])))
                    continue
                else:
                    print("请输入 y(yes)/n(no)/s(show)")
        
        if commit:
            print("\n📤 正在提交结果到数据库...")
            if manager.commit_to_database():
                print("✅ 结果已成功提交到数据库")
                
                # 询问是否清理缓存
                if not args.auto_commit:
                    cleanup = input("🧹 是否清理临时缓存文件？(y/n): ").strip().lower()
                else:
                    cleanup = 'y'
                
                if cleanup in ['y', 'yes']:
                    manager.cleanup_session()
                    print("✅ 缓存文件已清理")
                else:
                    print(f"📄 缓存文件保留在: {manager.session_cache_path}")
            else:
                print("❌ 提交数据库失败")
                print(f"📄 测试结果保存在: {manager.session_cache_path}")
                print("   稍后可以手动提交或检查")
                sys.exit(1)
        else:
            print(f"\n📄 测试结果已保存到缓存文件: {manager.session_cache_path}")
            print("   稍后可以手动提交到数据库")
        
        print("\n🎉 任务完成!")
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  测试被用户中断")
        print(f"📄 部分结果可能已保存到: {manager.session_cache_path}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()