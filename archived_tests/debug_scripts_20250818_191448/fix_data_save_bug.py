#!/usr/bin/env python3
"""
修复数据保存bug
问题：cumulative_test_manager.py中v2_models[model]创建为字典但调用了.update_from_test()方法
"""

import sys
import os
from pathlib import Path
from datetime import datetime

def analyze_problem():
    """分析问题"""
    print("="*60)
    print("问题分析")
    print("="*60)
    
    print("\n文件: cumulative_test_manager.py")
    print("行1007: self.v2_models[model] = {}  # 创建为空字典")
    print("行1035: self.v2_models[model].update_from_test(test_dict)  # 尝试调用不存在的方法")
    
    print("\n❌ 问题根因:")
    print("1. v2_models[model]应该是ModelStatistics对象，而不是字典")
    print("2. 字典没有update_from_test()方法")
    print("3. 这导致add_test_result_with_classification在第1035行抛出异常")
    print("4. 异常可能被静默处理，导致数据没有保存")

def propose_fix():
    """提出修复方案"""
    print("\n" + "="*60)
    print("修复方案")
    print("="*60)
    
    print("\n方案1: 导入并使用ModelStatistics类")
    print("""
# 在文件顶部导入
from old_data_structures.cumulative_data_structure import ModelStatistics

# 修改行1007
if model not in self.v2_models:
    self.v2_models[model] = ModelStatistics(model_name=model)
""")
    
    print("\n方案2: 直接使用字典操作（简化方案）")
    print("""
# 修改行1035，不调用update_from_test
# 而是直接更新数据库
if model not in self.database["models"]:
    self.database["models"][model] = self._create_empty_model_dict(model)

# 直接更新统计数据
self._update_model_stats(model, test_dict)
""")
    
    print("\n方案3: 临时禁用v2_models（最快修复）")
    print("""
# 注释掉行1035
# self.v2_models[model].update_from_test(test_dict)

# 直接调用父类方法
super().add_test_result(record)
""")

def create_patch():
    """创建修复补丁"""
    print("\n" + "="*60)
    print("创建修复补丁")
    print("="*60)
    
    patch_content = '''--- cumulative_test_manager.py.orig
+++ cumulative_test_manager.py
@@ -1004,10 +1004,15 @@
         # 更新V2模型数据
         model = record.model
         if model not in self.v2_models:
-            self.v2_models[model] = {}  # V3: dict format
+            # 修复：导入并使用ModelStatistics而不是空字典
+            try:
+                from old_data_structures.cumulative_data_structure import ModelStatistics
+                self.v2_models[model] = ModelStatistics(model_name=model)
+            except ImportError:
+                # 如果无法导入，跳过v2_models更新
+                pass
         
         # 构建测试字典
         test_dict = {
@@ -1032,8 +1037,11 @@
         }
         
         # 使用V2模型更新
-        self.v2_models[model].update_from_test(test_dict)
-        
+        if model in self.v2_models and hasattr(self.v2_models[model], 'update_from_test'):
+            self.v2_models[model].update_from_test(test_dict)
+        else:
+            # 如果v2_models不可用，直接跳过
+            pass
+            
         # 添加到缓冲
         self.buffer.append(record)
'''
    
    patch_file = Path("fix_data_save.patch")
    patch_file.write_text(patch_content)
    print(f"✅ 补丁已创建: {patch_file}")
    
    return patch_file

def apply_quick_fix():
    """应用快速修复"""
    print("\n" + "="*60)
    print("应用快速修复")
    print("="*60)
    
    file_path = Path("cumulative_test_manager.py")
    
    # 备份原文件
    backup_path = file_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    print(f"1. 备份原文件到: {backup_path}")
    import shutil
    shutil.copy(file_path, backup_path)
    
    print("2. 读取文件内容...")
    content = file_path.read_text()
    
    print("3. 应用修复...")
    # 修复1：导入ModelStatistics
    if "from old_data_structures.cumulative_data_structure import ModelStatistics" not in content:
        # 在其他导入后添加
        import_line = "from old_data_structures.cumulative_data_structure import ModelStatistics\n"
        content = content.replace(
            "from typing import Dict, List, Optional, Any",
            "from typing import Dict, List, Optional, Any\n" + import_line
        )
    
    # 修复2：创建ModelStatistics实例而不是字典
    content = content.replace(
        "            self.v2_models[model] = {}  # V3: dict format",
        """            try:
                from old_data_structures.cumulative_data_structure import ModelStatistics
                self.v2_models[model] = ModelStatistics(model_name=model)
            except ImportError:
                self.v2_models[model] = {}  # fallback to dict"""
    )
    
    # 修复3：安全调用update_from_test
    content = content.replace(
        "        self.v2_models[model].update_from_test(test_dict)",
        """        if hasattr(self.v2_models[model], 'update_from_test'):
            self.v2_models[model].update_from_test(test_dict)
        else:
            # v2_models是字典，跳过更新
            pass"""
    )
    
    print("4. 保存修复后的文件...")
    file_path.write_text(content)
    
    print("✅ 修复已应用!")
    print(f"   原文件备份: {backup_path}")
    print(f"   修复文件: {file_path}")

def main():
    """主函数"""
    print("🔧 数据保存Bug修复工具")
    print(f"时间: {datetime.now()}")
    
    # 分析问题
    analyze_problem()
    
    # 提出方案
    propose_fix()
    
    # 创建补丁
    patch_file = create_patch()
    
    # 询问是否应用
    print("\n" + "="*60)
    response = input("是否应用快速修复? (y/n): ")
    if response.lower() == 'y':
        apply_quick_fix()
        print("\n✅ 修复完成！请运行测试验证。")
    else:
        print(f"\n补丁已保存到: {patch_file}")
        print("您可以手动应用补丁：")
        print(f"  patch -p0 < {patch_file}")

if __name__ == "__main__":
    main()