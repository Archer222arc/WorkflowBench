# 闭源模型测试实现总结

## 🎯 实现目标

为 `run_systematic_test_final.sh` 添加闭源模型测试支持，包括：
- 闭源模型的API连接性验证
- 开源/闭源模型类型选择接口
- 不同的并发策略配置
- 独立的结果保存路径
- 排除5.2阶段（Qwen专用）

## ✅ 已完成的修改 (2025-08-15更新)

### 1. 闭源模型列表定义
```bash
# 可用的闭源模型
CLOSED_SOURCE_MODELS=(
    "gpt-4o-mini"                # Azure - 工作正常
    "o3-0416-global"             # IdealLab - 工作正常
    "gemini-2.5-flash-06-17"     # IdealLab - 工作正常（注意空content问题）
    # 以下模型需要额外配置：
    # "grok-3-mini"              # 需要X.AI API配置
    # "deepseek-v3-671b"         # Azure 8540端口
    # "Llama-3.3-70B-Instruct"   # Azure标准配置
)

# 已移除的模型（不可用）
# "gpt-5-mini"                 # API参数不兼容
# "claude_sonnet4"             # IdealLab权限问题
```

### 2. 模型类型选择系统
- **新增变量**：
  - `MODEL_TYPE`: "opensource" 或 "closed_source"
  - `CURRENT_MODELS[]`: 当前选择的模型列表
  - `RESULT_SUFFIX`: 结果文件后缀（闭源为 "_closed_source"）

- **新增菜单函数**：
  - `show_model_type_menu()`: 显示模型类型选择
  - `set_model_type_config()`: 配置模型类型设置

### 3. 并发策略配置（已优化+动态计算）
针对不同API提供商的特点优化：

#### 闭源模型并发
**Azure模型（高token限制）**
```bash
"gpt-4o-mini"|"gpt-5-mini"|"grok-3-mini"
# 单prompt测试：--max-workers 100
# 多prompt并发：--max-workers (100 * prompt数量)
# 例如：3个prompt并发时 = 300 workers
# 无QPS限制，充分利用Azure高token能力
```

**IdealLab闭源模型（单key限制）**
```bash
"claude_sonnet4"|"o3-0416-global"|"gemini-2.5-flash-06-17"
--max-workers 5 --max-prompt-workers 1  # 保守策略，QPS=10
```

#### 开源模型并发（同步优化）
**Azure开源模型（DeepSeek, Llama）**
```bash
# 单prompt测试：--max-workers 100
# 多prompt并发：--max-workers (100 * prompt数量)
# 动态计算workers，充分利用Azure多实例
```

**IdealLab开源模型（Qwen系列）**
```bash
--max-workers 10  # 3个API keys轮询，QPS=20
```

#### 动态Worker计算逻辑
```bash
# 自动检测prompt数量
if [[ "$prompt_types" == *","* ]]; then
    prompt_count=$(echo "$prompt_types" | tr ',' '\n' | wc -l)
elif [[ "$prompt_types" == "all" ]]; then
    prompt_count=3  # baseline, cot, optimal
fi

# Azure模型动态调整
if [ $prompt_count -gt 1 ] && [ -n "$use_prompt_parallel" ]; then
    max_workers=$((100 * prompt_count))  # 每个prompt 100 workers
fi
```

### 4. 阶段选择修改
- **动态菜单**：根据模型类型显示不同的阶段描述
- **5.2阶段排除**：闭源模型自动跳过Qwen规模效应测试
- **错误处理**：防止用户误选不适用的阶段

### 5. 结果文件分离
- 闭源模型结果保存为独立JSON文件
- 通过 `--result-suffix _closed_source` 参数实现
- 避免与开源模型结果混淆

### 6. 执行流程更新
- **统一模型引用**：所有执行部分使用 `CURRENT_MODELS` 代替 `OPENSOURCE_MODELS`
- **自适应并发**：根据模型类型自动调整并发参数
- **进度管理**：保持与现有进度系统兼容

## 🔧 技术细节

### 菜单集成
```bash
# 新增：模型类型选择菜单（插入在测试模式选择之前）
while true; do
    show_model_type_menu
    read -r model_type_choice
    
    if set_model_type_config "$model_type_choice"; then
        break
    fi
done
```

### 结果参数传递
```bash
# 添加结果文件后缀（用于闭源模型独立保存）
local result_suffix_param=""
if [ -n "$RESULT_SUFFIX" ]; then
    result_suffix_param="--result-suffix $RESULT_SUFFIX"
fi
```

### 5.2阶段跳过逻辑
```bash
if [ "$STEP" -eq 2 ]; then
    if [ "$MODEL_TYPE" = "closed_source" ]; then
        echo "⚠️  Qwen系列规模效应测试不适用于闭源模型"
        update_progress 3 0 ""  # 直接跳到5.3
        confirm_continue "跳过5.2阶段，准备进行5.3 缺陷工作流测试..."
    else
        # 正常执行开源模型的5.2测试
    fi
fi
```

## 🎮 用户体验

### 交互流程（优化版）
1. **模型类型选择**（第一层）：
   - 🔓 开源模型 (DeepSeek, Qwen, Llama)
   - 🔒 闭源模型 (GPT, Claude, Gemini)
   - 📊 查看两种模型的进度
   - 🔧 维护模式
   
2. **初始菜单**（第二层）：选择继续/重新开始/自定义阶段
3. **测试模式选择**：自动/调试/全自动
4. **并发策略选择**：自适应/固定/超高并行/自定义
5. **Checkpoint设置**：保存频率配置

### 进度和维护管理分离
- **开源模型文件**：
  - 进度：`test_progress_opensource.txt`
  - 完成记录：`completed_tests_opensource.txt`
  - 失败测试：`failed_tests_config_opensource.json`
  
- **闭源模型文件**：
  - 进度：`test_progress_closed_source.txt`
  - 完成记录：`completed_tests_closed_source.txt`
  - 失败测试：`failed_tests_config_closed_source.json`

### 用户友好提示
- **Azure模型**：显示"高token限制，支持模型+prompt并发"
- **IdealLab闭源**：显示"单key限制，仅模型并发"
- **5.2跳过**：明确说明"不适用于闭源模型"
- **进度显示**：保持一致的测试进度跟踪

## 🚀 实际测试场景示例

### 场景1：5.5 提示类型敏感性测试
```bash
# 测试baseline和cot两种prompt类型
run_smart_test "gpt-4o-mini" "baseline,cot" "easy" "all" "20"
# 结果：Azure模型自动使用200 workers（100*2）
```

### 场景2：5.3 缺陷工作流测试
```bash
# 测试3种结构缺陷
run_smart_test "gpt-5-mini" "flawed_sequence_disorder,flawed_tool_misuse,flawed_parameter_error" "easy" "all" "20"
# 结果：Azure模型自动使用300 workers（100*3）
```

### 场景3：5.1 基准测试
```bash
# 单个optimal prompt
run_smart_test "grok-3-mini" "optimal" "easy" "all" "20"
# 结果：Azure模型使用100 workers（单prompt）
```

### 场景4：IdealLab模型测试
```bash
# IdealLab闭源模型不受prompt数量影响
run_smart_test "claude_sonnet4" "baseline,cot,optimal" "easy" "all" "20"
# 结果：始终使用5 workers（API key限制）
```

## 🚀 下一步测试建议

1. **API连接验证**：运行修改后的脚本，选择闭源模型，验证API调用
2. **动态Worker验证**：观察Azure模型在多prompt并发时是否正确使用200/300 workers
3. **结果文件检查**：确认闭源模型结果保存在独立文件中（_closed_source后缀）
4. **阶段跳过验证**：确认5.2阶段对闭源模型正确跳过
5. **系统资源监控**：在使用300 workers时监控系统资源使用情况

## 📋 关键文件修改

- **主脚本**：`run_systematic_test_final.sh` - 添加了完整的闭源模型支持
- **测试脚本**：`test_script_modifications.sh` - 验证基本功能
- **文档**：当前文档记录实现细节

## 📊 数据存储分离

### 数据库文件结构
- **开源模型数据库**：`pilot_bench_cumulative_results/master_database.json`
- **闭源模型数据库**：`pilot_bench_cumulative_results/master_database_closed_source.json`

### 实现细节
1. **参数传递链**：
   - Shell脚本：`--result-suffix $RESULT_SUFFIX`
   - Python脚本：`smart_batch_runner.py --result-suffix _closed_source`
   - 管理器类：`EnhancedCumulativeManager(db_suffix=result_suffix)`
   - 数据库文件：`master_database{suffix}.json`

2. **自动创建**：首次运行闭源模型测试时自动创建独立数据库文件

3. **数据隔离**：开源和闭源模型的测试结果完全隔离，便于独立分析

## ⚠️ 注意事项

1. **API Key管理**：确保 IdealLab 的第一个API key支持闭源模型
2. **Azure配置**：确认Azure endpoint支持新增的grok-3-mini等模型
3. **Python脚本兼容**：✅ 已实现 `--result-suffix` 参数支持
4. **进度文件**：闭源和开源模型使用相同的进度管理系统
5. **数据库备份**：定期备份两个数据库文件，避免数据丢失

## ✨ 特色功能

- **智能跳过**：自动识别不适用的测试阶段
- **动态并发**：根据API提供商特点优化并发策略
- **独立结果**：闭源模型结果独立存储，便于分析对比
- **用户友好**：清晰的提示和错误处理机制