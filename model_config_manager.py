#!/usr/bin/env python3
"""
模型配置管理器
==============
管理不同模型的API参数配置
"""

from typing import Dict, Any

# 模型特定配置
MODEL_CONFIGS = {
    # 使用 max_completion_tokens 的模型（新API格式）
    "DeepSeek-R1-0528": {
        "use_max_completion_tokens": True,
        "min_temperature": 0.1,  # 不能为0
        "default_temperature": 0.7,
        "timeout": 30
    },
    "DeepSeek-V3-0324": {
        "use_max_completion_tokens": True,
        "min_temperature": 0.1,
        "default_temperature": 0.7,
        "timeout": 30
    },
    "gpt-oss-120b": {
        "use_max_completion_tokens": True,
        "min_temperature": 0.1,
        "default_temperature": 0.7,
        "timeout": 10
    },
    "grok-3": {
        "use_max_completion_tokens": True,
        "min_temperature": 0.1,
        "default_temperature": 0.7,
        "timeout": 10
    },
    "Llama-3.3-70B-Instruct": {
        "use_max_completion_tokens": True,
        "min_temperature": 0.1,
        "default_temperature": 0.7,
        "timeout": 10
    },
    
    # GPT-5系列 - 使用最简单的接口
    "gpt-5-mini": {
        "use_simple_api": True,  # 不设置任何额外参数
        "skip_params": ["max_tokens", "max_completion_tokens", "temperature"],
        "timeout": 30
    },
    "gpt-5-nano": {
        "use_simple_api": True,
        "skip_params": ["max_tokens", "max_completion_tokens", "temperature"],
        "timeout": 30
    }
}

# 默认配置（用于未明确配置的模型）
DEFAULT_CONFIG = {
    "use_max_completion_tokens": False,  # 默认使用max_tokens
    "min_temperature": 0.0,
    "default_temperature": 0.7,
    "timeout": 30
}


class ModelConfigManager:
    """管理模型特定的配置"""
    
    @staticmethod
    def get_config(model_name: str) -> Dict[str, Any]:
        """获取模型配置"""
        return MODEL_CONFIGS.get(model_name, DEFAULT_CONFIG)
    
    @staticmethod
    def prepare_api_params(model_name: str, **kwargs) -> Dict[str, Any]:
        """准备API调用参数"""
        config = ModelConfigManager.get_config(model_name)
        
        # 检查是否禁用
        if config.get("disabled", False):
            raise ValueError(f"Model {model_name} is disabled: {config.get('reason', 'Unknown')}")
        
        # 检查是否使用简单API（GPT-5系列）
        if config.get("use_simple_api", False):
            # 对于简单API，只传递messages和少数必要参数
            params = {}
            skip_params = config.get("skip_params", [])
            
            for key, value in kwargs.items():
                if key not in skip_params:
                    params[key] = value
            
            # 确保有timeout
            if "timeout" not in params:
                params["timeout"] = config.get("timeout", 30)
            
            return params
        
        # 准备参数（其他模型）
        params = {}
        
        # 处理max_tokens/max_completion_tokens
        if "max_tokens" in kwargs or "max_completion_tokens" in kwargs:
            if config.get("use_max_completion_tokens", False):
                # 使用新参数名
                if "max_tokens" in kwargs:
                    params["max_completion_tokens"] = kwargs["max_tokens"]
                elif "max_completion_tokens" in kwargs:
                    params["max_completion_tokens"] = kwargs["max_completion_tokens"]
            else:
                # 使用旧参数名
                if "max_completion_tokens" in kwargs:
                    params["max_tokens"] = kwargs["max_completion_tokens"]
                elif "max_tokens" in kwargs:
                    params["max_tokens"] = kwargs["max_tokens"]
        
        # 处理temperature
        if "temperature" in kwargs:
            temp = kwargs["temperature"]
            min_temp = config.get("min_temperature", 0.0)
            
            # 确保temperature不低于最小值
            if temp < min_temp:
                params["temperature"] = min_temp
            else:
                params["temperature"] = temp
        else:
            # 使用默认temperature
            params["temperature"] = config.get("default_temperature", 0.7)
        
        # 添加其他参数
        for key, value in kwargs.items():
            if key not in ["max_tokens", "max_completion_tokens", "temperature"]:
                params[key] = value
        
        # 添加超时
        if "timeout" not in params:
            params["timeout"] = config.get("timeout", 30)
        
        return params
    
    @staticmethod
    def is_model_available(model_name: str) -> bool:
        """检查模型是否可用"""
        config = ModelConfigManager.get_config(model_name)
        return not config.get("disabled", False)
    
    @staticmethod
    def get_available_models() -> list:
        """获取所有可用的模型"""
        available = []
        for model, config in MODEL_CONFIGS.items():
            if not config.get("disabled", False):
                available.append(model)
        return available


# 便捷函数
def prepare_model_params(model_name: str, **kwargs) -> Dict[str, Any]:
    """准备模型API参数的便捷函数"""
    return ModelConfigManager.prepare_api_params(model_name, **kwargs)


def is_model_working(model_name: str) -> bool:
    """检查模型是否可用的便捷函数"""
    return ModelConfigManager.is_model_available(model_name)