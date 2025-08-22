#!/usr/bin/env python3
"""
计算实际内存影响 - 基于真实文件大小
"""

def calculate_real_impact():
    """计算基于实际文件大小的内存影响"""
    print("="*60)
    print("基于实际文件大小的内存影响分析")
    print("="*60)
    
    # 实际测量值
    file_size_mb = 59  # task_library_enhanced_v3_easy_with_workflows.json实际大小
    total_tasks = 630
    task_size_kb = (file_size_mb * 1024) / total_tasks  # 每个任务的平均大小
    
    print(f"实际文件大小: {file_size_mb}MB")
    print(f"总任务数: {total_tasks}")
    print(f"每个任务平均: {task_size_kb:.2f}KB")
    
    scenarios = [
        ("原始（全部630个任务）", 630, 25),
        ("部分加载（20个/类型，共140个）", 140, 25),
        ("部分加载（10个/类型，共70个）", 70, 25),
        ("部分加载（5个/类型，共35个）", 35, 25),
        ("极限优化（3个/类型，共21个）", 21, 25),
    ]
    
    print("\n" + "="*60)
    print("内存使用对比")
    print("="*60)
    
    for name, tasks_per_process, num_processes in scenarios:
        # 计算每个进程的内存使用
        memory_per_process_mb = (tasks_per_process * task_size_kb) / 1024
        
        # 计算总内存使用
        total_memory_mb = memory_per_process_mb * num_processes
        total_memory_gb = total_memory_mb / 1024
        
        print(f"\n{name}:")
        print(f"  每进程加载: {tasks_per_process} 个任务")
        print(f"  每进程内存: {memory_per_process_mb:.2f}MB")
        print(f"  {num_processes}进程总内存: {total_memory_mb:.2f}MB ({total_memory_gb:.2f}GB)")
        
        if "原始" not in name:
            # 计算节省
            original_memory = (630 * task_size_kb / 1024) * num_processes
            saved_mb = original_memory - total_memory_mb
            saved_percent = (saved_mb / original_memory) * 100
            print(f"  💚 内存节省: {saved_mb:.2f}MB ({saved_percent:.1f}%)")
    
    print("\n" + "="*60)
    print("结合workflow预生成的总体优化效果")
    print("="*60)
    
    # MDPWorkflowGenerator的内存占用（已通过预生成避免）
    mdp_memory_per_process = 350  # MB
    
    print(f"\nMDPWorkflowGenerator内存: {mdp_memory_per_process}MB/进程")
    print(f"任务库内存: {file_size_mb}MB/进程")
    
    print("\n25个并发进程的总内存使用:")
    
    # 原始（无任何优化）
    original_total = (mdp_memory_per_process + file_size_mb) * 25
    print(f"\n1. 原始方案（无优化）:")
    print(f"   MDPWorkflowGenerator: {mdp_memory_per_process * 25}MB")
    print(f"   任务库（全部加载）: {file_size_mb * 25}MB")
    print(f"   总计: {original_total}MB ({original_total/1024:.2f}GB)")
    
    # 当前（只有workflow预生成）
    current_total = file_size_mb * 25
    print(f"\n2. 当前方案（workflow预生成）:")
    print(f"   MDPWorkflowGenerator: 0MB（已优化）")
    print(f"   任务库（全部加载）: {file_size_mb * 25}MB")
    print(f"   总计: {current_total}MB ({current_total/1024:.2f}GB)")
    print(f"   相比原始节省: {original_total - current_total}MB ({(original_total - current_total)/original_total*100:.1f}%)")
    
    # 最优（workflow预生成 + 部分加载20个/类型）
    optimal_task_memory = (140 * task_size_kb / 1024) * 25
    optimal_total = optimal_task_memory
    print(f"\n3. 优化方案（workflow预生成 + 部分加载20个/类型）:")
    print(f"   MDPWorkflowGenerator: 0MB（已优化）")
    print(f"   任务库（部分加载）: {optimal_task_memory:.2f}MB")
    print(f"   总计: {optimal_total:.2f}MB ({optimal_total/1024:.2f}GB)")
    print(f"   相比原始节省: {original_total - optimal_total:.2f}MB ({(original_total - optimal_total)/original_total*100:.1f}%)")
    print(f"   相比当前节省: {current_total - optimal_total:.2f}MB ({(current_total - optimal_total)/current_total*100:.1f}%)")
    
    # 极限优化（workflow预生成 + 部分加载5个/类型）
    extreme_task_memory = (35 * task_size_kb / 1024) * 25
    extreme_total = extreme_task_memory
    print(f"\n4. 极限方案（workflow预生成 + 部分加载5个/类型）:")
    print(f"   MDPWorkflowGenerator: 0MB（已优化）")
    print(f"   任务库（部分加载）: {extreme_task_memory:.2f}MB")
    print(f"   总计: {extreme_total:.2f}MB ({extreme_total/1024:.2f}GB)")
    print(f"   相比原始节省: {original_total - extreme_total:.2f}MB ({(original_total - extreme_total)/original_total*100:.1f}%)")
    print(f"   相比当前节省: {current_total - extreme_total:.2f}MB ({(current_total - extreme_total)/current_total*100:.1f}%)")
    
    print("\n" + "="*60)
    print("建议")
    print("="*60)
    print("\n✅ 推荐方案：workflow预生成 + 部分加载20个/类型")
    print(f"  - 内存从 {original_total/1024:.1f}GB → {optimal_total/1024:.2f}GB")
    print(f"  - 节省 {(original_total - optimal_total)/1024:.2f}GB ({(original_total - optimal_total)/original_total*100:.1f}%)")
    print("  - 保持足够的任务多样性")
    print("  - 实施简单，风险低")

if __name__ == "__main__":
    calculate_real_impact()