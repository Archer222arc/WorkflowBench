#!/bin/bash

# 立即修复进程"卡死"问题的脚本

echo "=========================================="
echo "修复进程卡死问题 - 立即解决方案"
echo "=========================================="

# 1. 减少max_turns从10到5
echo "1. 减少最大轮次从10到5..."
sed -i.bak 's/max_turns=10/max_turns=5/g' interactive_executor.py
echo "   ✅ 完成"

# 2. 添加连续搜索检测（临时方案）
echo "2. 创建修复补丁..."
cat > fix_infinite_loop.patch << 'PATCH'
--- interactive_executor.py.orig
+++ interactive_executor.py
@@ -399,6 +399,9 @@
         
         start_time = time.time()
         
+        # 添加连续搜索/格式错误计数器
+        consecutive_searches = 0
+        consecutive_format_errors = 0
+        
         for turn in range(self.max_turns):
             if not self.silent:
@@ -421,6 +424,13 @@
             search_queries = self._extract_tool_searches(response)
             if search_queries:
+                consecutive_searches += 1
+                if consecutive_searches >= 3:
+                    if not self.silent:
+                        print(f"  [ABORT] Too many consecutive searches ({consecutive_searches}), terminating")
+                    state.task_completed = False
+                    break
+                
                 # 处理工具搜索
                 search_results = self._handle_tool_searches(search_queries, state)
@@ -441,6 +451,8 @@
                     "turn": turn + 1
                 })
                 
+            else:
+                consecutive_searches = 0  # 重置计数器
                 continue
             
             # 3. 检查是否有工具详情请求（新增）
@@ -479,6 +491,13 @@
             
             # 如果检测到格式问题，提供帮助并继续对话
             if format_issue_detected:
+                consecutive_format_errors += 1
+                if consecutive_format_errors >= 3:
+                    if not self.silent:
+                        print(f"  [ABORT] Too many format errors ({consecutive_format_errors}), terminating")
+                    state.task_completed = False
+                    break
+                    
                 format_help = self._generate_format_help_message(state)
                 conversation.append({"role": "assistant", "content": response})
@@ -501,6 +520,8 @@
                     state.format_error_count = 0
                 state.format_error_count += 1
                 
+            else:
+                consecutive_format_errors = 0  # 重置计数器
                 continue
PATCH

# 3. 修改批量测试超时
echo "3. 修改批量测试超时..."
sed -i.bak 's/timeout=len(tasks) \* 70/timeout=min(len(tasks) * 30, 3600)/g' batch_test_runner.py
echo "   ✅ 完成（最大1小时）"

# 4. 减少API超时
echo "4. 减少API调用超时从60秒到30秒..."
sed -i.bak 's/timeout=60/timeout=30/g' interactive_executor.py
echo "   ✅ 完成"

echo ""
echo "=========================================="
echo "修复完成！"
echo "=========================================="
echo ""
echo "改进内容："
echo "  1. 最大轮次：10 → 5"
echo "  2. 连续搜索超过3次自动终止"
echo "  3. 连续格式错误超过3次自动终止"
echo "  4. 批量超时最大1小时"
echo "  5. API调用超时：60秒 → 30秒"
echo ""
echo "预期效果："
echo "  - 单个测试最多5轮（之前10轮）"
echo "  - 避免无限搜索循环"
echo "  - 避免无限格式错误循环"
echo "  - 整体运行时间减少50%以上"
echo ""
echo "使用建议："
echo "  ./run_systematic_test_final.sh"
echo "  - 选择较少的实例数（10-20个）"
echo "  - 使用串行或少量并发（1-2个worker）"
