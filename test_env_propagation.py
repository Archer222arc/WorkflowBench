#!/usr/bin/env python3
"""测试环境变量传递"""
import os
import sys

def check_env_vars():
    """检查关键环境变量"""
    critical_vars = [
        'SKIP_MODEL_LOADING',
        'USE_PARTIAL_LOADING',
        'TASK_LOAD_COUNT',
        'USE_RESULT_COLLECTOR',
        'STORAGE_FORMAT'
    ]
    
    print("="*50)
    print("环境变量检查")
    print("="*50)
    
    for var in critical_vars:
        value = os.environ.get(var, 'NOT_SET')
        status = "✅" if value != 'NOT_SET' else "❌"
        print(f"{status} {var}: {value}")
    
    print("="*50)
    
    # 检查是否会触发模型加载
    skip_loading = os.environ.get('SKIP_MODEL_LOADING', 'false').lower() == 'true'
    if skip_loading:
        print("✅ 应该跳过模型加载")
    else:
        print("⚠️  将会加载模型（消耗350MB内存）")
    
    print("="*50)

if __name__ == "__main__":
    check_env_vars()
    
    # 如果参数包含test_import，测试导入
    if len(sys.argv) > 1 and sys.argv[1] == "test_import":
        print("\n测试导入mdp_workflow_generator...")
        try:
            from mdp_workflow_generator import MDPWorkflowGenerator
            print("✅ 导入成功")
            
            # 检查是否真的跳过了模型加载
            gen = MDPWorkflowGenerator(
                model_path="checkpoints/best_model.pt",
                use_embeddings=True
            )
            
            if gen.q_network is None and gen.network is None:
                print("✅ 确认跳过了模型加载")
            else:
                print("❌ 模型被加载了！")
                
        except Exception as e:
            print(f"❌ 导入失败: {e}")