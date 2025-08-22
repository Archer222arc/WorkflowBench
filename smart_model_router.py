#!/usr/bin/env python3
"""
智能模型路由器
==============
自动选择最优的API端点，优先使用用户的Azure端点
"""

from typing import Dict, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

# 用户Azure端点可用的模型
USER_AZURE_MODELS = {
    # 基础模型
    "DeepSeek-R1-0528",
    "DeepSeek-V3-0324",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-oss-120b",
    "Llama-3.3-70B-Instruct",
    "grok-3",         # Azure AI Foundry
    "grok-3-mini",    # Azure AI Foundry
    
    # 并行部署实例（保持原样传递，不做转换）
    "DeepSeek-V3-0324-2",      # DeepSeek V3 并行部署2
    "DeepSeek-V3-0324-3",      # DeepSeek V3 并行部署3
    "DeepSeek-R1-0528-2",      # DeepSeek R1 并行部署2
    "DeepSeek-R1-0528-3",      # DeepSeek R1 并行部署3
    "Llama-3.3-70B-Instruct-2", # Llama 并行部署2
    "Llama-3.3-70B-Instruct-3"  # Llama 并行部署3
}

# 模型别名映射（支持多种名称格式）
MODEL_ALIASES = {
    # DeepSeek系列 - 映射到正确的deployment name
    "deepseek-r1": "DeepSeek-R1-0528",
    "deepseek-r1-0528": "DeepSeek-R1-0528",
    "deepseek-r1-671b": "DeepSeek-R1-0528",
    "DeepSeek-R1": "DeepSeek-R1-0528",
    "DeepSeek-R1-671B": "DeepSeek-R1-0528",
    
    "deepseek-v3": "DeepSeek-V3-0324",
    "deepseek-v3-0324": "DeepSeek-V3-0324",
    "deepseek-v3-671b": "DeepSeek-V3-0324",
    "DeepSeek-V3": "DeepSeek-V3-0324",
    "DeepSeek-V3-671B": "DeepSeek-V3-0324",
    
    # GPT-5系列
    "gpt5-mini": "gpt-5-mini",
    "GPT-5-mini": "gpt-5-mini",
    "gpt5-nano": "gpt-5-nano",
    "GPT-5-nano": "gpt-5-nano",
    
    # GPT-OSS
    "gpt-oss": "gpt-oss-120b",
    "GPT-OSS": "gpt-oss-120b",
    "gpt-oss-120": "gpt-oss-120b",
    
    # Grok
    "grok3": "grok-3",
    "Grok-3": "grok-3",
    "GROK-3": "grok-3",
    "grok3-mini": "grok-3-mini",
    "Grok-3-mini": "grok-3-mini",
    
    # Llama
    "llama-3.3": "Llama-3.3-70B-Instruct",
    "llama-3.3-70b": "Llama-3.3-70B-Instruct",
    "llama-3.3-70b-instruct": "Llama-3.3-70B-Instruct",
    "Llama-3.3": "Llama-3.3-70B-Instruct",
    "llama-3.1-nemotron-70b-instruct": "Llama-3.3-70B-Instruct"  # 映射到正确的模型
}

# idealab可用的模型（作为备选）
IDEALAB_MODELS = {
    # GPT系列
    "gpt-41-0414-global", "o1-1217-global", "o3-0416-global", "o4-mini-0416-global",
    
    # Claude系列
    "claude37_sonnet", "claude_sonnet4", "claude_opus4",
    
    # Gemini系列
    "gemini-2.5-pro-06-17", "gemini-2.5-flash-06-17", "gemini-1.5-pro", "gemini-2.0-flash",
    
    # DeepSeek系列（旧版，但仍然可用）
    "deepseek-v3-671b", "deepseek-r1-671b", "DeepSeek-V3-671B", "DeepSeek-R1-671B",
    
    # Qwen系列
    "qwen2.5-max", "qwen2.5-72b-instruct", "qwen2.5-32b-instruct", 
    "qwen2.5-14b-instruct", "qwen2.5-7b-instruct", "qwen2.5-3b-instruct",
    
    # Kimi
    "kimi-k2"
}

# Azure可用的模型
AZURE_MODELS = {"gpt-4o-mini"}


class SmartModelRouter:
    """智能模型路由器，自动选择最优API端点"""
    
    def __init__(self):
        self.routing_cache = {}
        
    def resolve_model_name(self, model_name: str) -> str:
        """解析模型名称，处理别名"""
        # 如果是已知的别名，转换为标准名称
        if model_name in MODEL_ALIASES:
            resolved = MODEL_ALIASES[model_name]
            logger.info(f"Resolved alias: {model_name} -> {resolved}")
            return resolved
        return model_name
    
    def get_best_provider(self, model_name: str) -> Tuple[str, str]:
        """
        获取模型的最佳提供商
        
        Returns:
            (provider, resolved_model_name)
        """
        # 先解析模型名称
        resolved_name = self.resolve_model_name(model_name)
        
        # 检查缓存
        if resolved_name in self.routing_cache:
            return self.routing_cache[resolved_name]
        
        # 先检查是否有可替代的模型（优先级最高）
        if self._find_alternative(resolved_name):
            alt_provider, alt_model = self._find_alternative(resolved_name)
            provider = (alt_provider, alt_model)
            logger.info(f"✨ Routing {resolved_name} -> {alt_model} via {alt_provider}")
            
        # 优先级2：用户的Azure端点（最新最强的模型）
        elif resolved_name in USER_AZURE_MODELS:
            provider = ("user_azure", resolved_name)
            logger.info(f"✨ Using USER's Azure endpoint for {resolved_name}")
            
        # 优先级4：标准Azure端点
        elif resolved_name in AZURE_MODELS:
            provider = ("azure", resolved_name)
            logger.info(f"Using Azure for {resolved_name}")
            
        # 优先级5：idealab API
        elif resolved_name in IDEALAB_MODELS:
            provider = ("idealab", resolved_name)
            logger.info(f"Using idealab for {resolved_name}")
            
        else:
            # 默认尝试idealab
            provider = ("idealab", resolved_name)
            logger.warning(f"Model {resolved_name} not in known lists, defaulting to idealab")
        
        # 缓存结果
        self.routing_cache[resolved_name] = provider
        return provider
    
    def _find_alternative(self, model_name: str) -> Optional[Tuple[str, str]]:
        """寻找替代模型"""
        alternatives = {
            # DeepSeek旧版本 -> 新版本 (V3-0324可以替代所有V3变体)
            "deepseek-v3-671b": ("user_azure", "DeepSeek-V3-0324"),
            "DeepSeek-V3-671B": ("user_azure", "DeepSeek-V3-0324"),
            "deepseek-v3": ("user_azure", "DeepSeek-V3-0324"),
            
            # DeepSeek R1系列
            "deepseek-r1-671b": ("user_azure", "DeepSeek-R1-0528"),
            "DeepSeek-R1-671B": ("user_azure", "DeepSeek-R1-0528"),
            "deepseek-r1": ("user_azure", "DeepSeek-R1-0528"),
            
            # 其他GPT模型的备选
            "gpt-4o": ("idealab", "gpt-41-0414-global"),
            "gpt-o1": ("idealab", "o1-1217-global"),
            "gpt-o3": ("idealab", "o3-0416-global"),
            "gpt-o4-mini": ("idealab", "o4-mini-0416-global"),
        }
        
        if model_name in alternatives:
            return alternatives[model_name]
        return None
    
    def get_routing_summary(self) -> Dict[str, List[str]]:
        """获取路由摘要"""
        summary = {
            "user_azure": list(USER_AZURE_MODELS),
            "azure": list(AZURE_MODELS),
            "idealab": list(IDEALAB_MODELS)
        }
        return summary
    
    def batch_route(self, model_names: List[str]) -> Dict[str, Tuple[str, str]]:
        """批量路由多个模型"""
        results = {}
        for model in model_names:
            provider, resolved = self.get_best_provider(model)
            results[model] = (provider, resolved)
        return results


# 全局路由器实例
_router = None

def get_router() -> SmartModelRouter:
    """获取全局路由器实例"""
    global _router
    if _router is None:
        _router = SmartModelRouter()
    return _router


def route_model(model_name: str) -> Tuple[str, str]:
    """便捷函数：路由单个模型"""
    router = get_router()
    return router.get_best_provider(model_name)


def print_routing_report(models: List[str]):
    """打印路由报告"""
    router = get_router()
    results = router.batch_route(models)
    
    print("\n" + "="*60)
    print("模型路由报告")
    print("="*60)
    
    by_provider = {}
    for model, (provider, resolved) in results.items():
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append((model, resolved))
    
    for provider, models in by_provider.items():
        if provider == "user_azure":
            print(f"\n✨ 使用您的Azure端点 ({len(models)}个模型):")
        elif provider == "azure":
            print(f"\n☁️ 使用标准Azure ({len(models)}个模型):")
        else:
            print(f"\n🔧 使用{provider} ({len(models)}个模型):")
        
        for original, resolved in models:
            if original != resolved:
                print(f"  • {original} -> {resolved}")
            else:
                print(f"  • {original}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # 测试路由器
    test_models = [
        "gpt-5-mini",
        "deepseek-v3",
        "deepseek-v3-671b",  # 旧版本，应该路由到新版
        "gpt-4o-mini",
        "llama-3.3",
        "qwen2.5-72b-instruct",
        "grok-3"
    ]
    
    print_routing_report(test_models)