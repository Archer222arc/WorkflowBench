# 更新后的要测试的模型列表（基于实验计划中的表格）
MODELS_TO_TEST = [
    ## 闭源模型
    "gpt-4o",                    # GPT-4o
    "gpt-o1",                    # GPT-o1
    "gpt-o3",                    # GPT-o3
    "gpt-o4-mini",               # GPT-o4-mini
    "claude-opus-4",             # Claude-Opus-4
    "claude-sonnet-4",           # Claude-Sonnet-4
    "claude-sonnet-3.7",         # Claude-Sonnet-3.7
    "claude-haiku-3.5",          # Claude-Haiku-3.5
    "gemini-2.5-pro",            # Gemini-2.5-Pro
    "gemini-2.5-flash",          # Gemini-2.5-Flash
    
    ## 开源模型
    "deepseek-v3-671b",          # DeepSeek-V3-671B
    "deepseek-r1-671b",          # DeepSeek-R1-671B
    "qwen2.5-72b-instruct",      # Qwen2.5-72B-Instruct
    "qwen2.5-32b-instruct",      # Qwen2.5-32B-Instruct
    "qwen2.5-14b-instruct",      # Qwen2.5-14B-Instruct
    "qwen2.5-7b-instruct",       # Qwen2.5-7B-Instruct
    "qwen2.5-3b-instruct",       # Qwen2.5-3B-Instruct
    "llama-3.3-70b-instruct",    # Llama-3.3-70B-Instruct
    "llama-4-scout-17b",         # Llama-4-Scout-17B
]

# 从原列表中删除的模型（不在实验计划表格中）：
REMOVED_MODELS = [
    # 原列表中但不在表格中的模型
    "qwen2.5-max",               # 不在表格中
    "kimi-k2",                   # 不在表格中
    "gpt-41-0414-global",        # 不在表格中
    "o1-1217-global",            # 不在表格中
    "o3-0416-global",            # 不在表格中
    "o4-mini-0416-global",       # 不在表格中
    "claude37_sonnet",           # 不在表格中（可能是claude-sonnet-3.7的别名）
    "claude_sonnet4",            # 不在表格中（可能是claude-sonnet-4的别名）
    "claude_opus4",              # 不在表格中（可能是claude-opus-4的别名）
    "gemini-2.5-pro-06-17",      # 不在表格中（可能是gemini-2.5-pro的别名）
    "gemini-2.5-flash-06-17",    # 不在表格中（可能是gemini-2.5-flash的别名）
]

print(f"保留的模型数量: {len(MODELS_TO_TEST)}")
print(f"删除的模型数量: {len(REMOVED_MODELS)}")