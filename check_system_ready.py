#!/usr/bin/env python3
"""
检查系统是否准备好运行5.3超并发测试
"""

import psutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

def check_system_resources():
    """检查系统资源"""
    print("=" * 60)
    print("系统资源检查")
    print("=" * 60)
    
    # CPU检查
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    print(f"\n🖥️ CPU状态:")
    print(f"  核心数: {cpu_count}")
    print(f"  当前使用率: {cpu_percent}%")
    
    if cpu_percent > 80:
        print("  ⚠️ CPU使用率较高，可能影响性能")
    else:
        print("  ✅ CPU使用率正常")
    
    # 内存检查
    memory = psutil.virtual_memory()
    available_gb = memory.available / (1024**3)
    total_gb = memory.total / (1024**3)
    used_percent = memory.percent
    
    print(f"\n💾 内存状态:")
    print(f"  总内存: {total_gb:.1f} GB")
    print(f"  可用内存: {available_gb:.1f} GB")
    print(f"  使用率: {used_percent}%")
    
    if available_gb < 8:
        print("  ❌ 可用内存不足8GB，建议释放内存")
        return False
    else:
        print("  ✅ 内存充足")
    
    return True

def check_python_processes():
    """检查Python进程"""
    print(f"\n🐍 Python进程检查:")
    
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info.get('cmdline', []))
                if any(x in cmdline for x in ['ultra_parallel', 'smart_batch', 'batch_test']):
                    python_processes.append({
                        'pid': proc.info['pid'],
                        'cmd': cmdline[:100]
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if python_processes:
        print(f"  ⚠️ 发现 {len(python_processes)} 个相关Python进程:")
        for proc in python_processes[:5]:
            print(f"    PID {proc['pid']}: {proc['cmd']}")
        
        print("\n  建议清理命令:")
        print("    pkill -f 'ultra_parallel'")
        print("    pkill -f 'smart_batch'")
        return False
    else:
        print("  ✅ 没有残留的测试进程")
        return True

def check_database_status():
    """检查数据库状态"""
    print(f"\n📊 数据库状态检查:")
    
    db_path = Path("pilot_bench_cumulative_results/master_database.json")
    if db_path.exists():
        import json
        with open(db_path, 'r') as f:
            db = json.load(f)
        
        total_tests = db.get('summary', {}).get('total_tests', 0)
        models_count = len(db.get('models', {}))
        
        print(f"  总测试数: {total_tests}")
        print(f"  模型数: {models_count}")
        
        # 检查5.3相关数据
        flawed_count = 0
        if 'models' in db:
            for model_data in db['models'].values():
                if 'by_prompt_type' in model_data:
                    for pt in model_data['by_prompt_type']:
                        if 'flawed' in pt:
                            flawed_count += 1
        
        if flawed_count > 0:
            print(f"  已有缺陷工作流数据: {flawed_count} 个配置")
        
        print("  ✅ 数据库状态正常")
        return True
    else:
        print("  ❌ 数据库不存在")
        return False

def check_scripts_exist():
    """检查必要脚本是否存在"""
    print(f"\n📝 脚本文件检查:")
    
    required_scripts = [
        "ultra_parallel_runner.py",
        "smart_batch_runner.py",
        "batch_test_runner.py",
        "enhanced_cumulative_manager.py",
        "run_systematic_test_final.sh"
    ]
    
    all_exist = True
    for script in required_scripts:
        if Path(script).exists():
            print(f"  ✅ {script}")
        else:
            print(f"  ❌ {script} 缺失")
            all_exist = False
    
    return all_exist

def generate_run_command():
    """生成推荐的运行命令"""
    print("\n" + "=" * 60)
    print("推荐的运行命令")
    print("=" * 60)
    
    print("\n🔧 安全模式（单模型，降低并发）:")
    print("""
python ultra_parallel_runner.py \\
    --model DeepSeek-V3-0324 \\
    --prompt-types flawed_sequence_disorder \\
    --difficulty easy \\
    --task-types simple_task \\
    --num-instances 5 \\
    --tool-success-rate 0.8 \\
    --max-workers 10 \\
    --batch-commit \\
    --checkpoint-interval 5 \\
    --no-silent
""")
    
    print("\n🚀 标准模式（3个模型，中等并发）:")
    print("""
./run_systematic_test_final.sh \\
    --phase 5.3 \\
    --ultra-parallel \\
    --max-workers 20 \\
    --stagger 30
""")
    
    print("\n⚡ 激进模式（全速，需要充足资源）:")
    print("""
python ultra_parallel_runner.py \\
    --model DeepSeek-V3-0324,DeepSeek-R1-0528,Llama-3.3-70B-Instruct \\
    --prompt-types flawed_sequence_disorder,flawed_redundant_steps \\
    --difficulty easy \\
    --task-types simple_task,basic_task \\
    --num-instances 10 \\
    --tool-success-rate 0.8 \\
    --max-workers 50 \\
    --batch-commit \\
    --checkpoint-interval 10
""")

def main():
    """主函数"""
    print("🔍 5.3超并发测试准备状态检查")
    print(f"时间: {datetime.now()}")
    print()
    
    # 执行各项检查
    checks = {
        'resources': check_system_resources(),
        'processes': check_python_processes(),
        'database': check_database_status(),
        'scripts': check_scripts_exist()
    }
    
    # 总体评估
    print("\n" + "=" * 60)
    print("总体评估")
    print("=" * 60)
    
    all_ready = all(checks.values())
    
    if all_ready:
        print("\n✅ 系统已准备好运行5.3超并发测试")
        generate_run_command()
    else:
        print("\n❌ 系统尚未准备好，请解决以下问题:")
        if not checks['resources']:
            print("  - 释放内存或降低并发度")
        if not checks['processes']:
            print("  - 清理残留进程")
        if not checks['database']:
            print("  - 检查数据库文件")
        if not checks['scripts']:
            print("  - 确保所有脚本文件存在")
    
    return 0 if all_ready else 1

if __name__ == "__main__":
    exit(main())