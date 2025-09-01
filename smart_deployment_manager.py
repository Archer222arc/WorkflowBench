#!/usr/bin/env python3
"""
智能部署管理器 - 处理429错误和多部署负载均衡
=============================================
当遇到429 Too Many Requests错误时，自动切换到其他可用的部署实例
"""

import json
import time
import random
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from openai import OpenAI, AzureOpenAI
import httpx

logger = logging.getLogger(__name__)

class SmartDeploymentManager:
    """智能部署管理器"""
    
    def __init__(self, config_path: str = "config/config.json"):
        self.config = self._load_config(config_path)
        self.deployment_health = {}  # 记录部署健康状态
        self.last_used = {}  # 记录上次使用时间，用于负载均衡
        self.failure_count = {}  # 记录失败次数
        
        # 从配置中获取并行部署映射
        self.parallel_deployments = self.config.get("azure_parallel_deployments", {})
        
        # 初始化部署健康状态
        for model, deployments in self.parallel_deployments.items():
            for deployment in deployments:
                self.deployment_health[deployment] = True
                self.last_used[deployment] = 0
                self.failure_count[deployment] = 0
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return {}
    
    def get_best_deployment(self, model_name: str) -> Optional[str]:
        """获取最佳可用部署
        
        Args:
            model_name: 基础模型名称（如 Llama-3.3-70B-Instruct）
            
        Returns:
            最佳可用部署名称，如果没有可用部署则返回None
        """
        # 获取该模型的所有部署
        deployments = self.parallel_deployments.get(model_name, [model_name])
        
        # 过滤健康的部署
        healthy_deployments = [
            d for d in deployments 
            if self.deployment_health.get(d, True) and self.failure_count.get(d, 0) < 5
        ]
        
        if not healthy_deployments:
            logger.warning(f"No healthy deployments available for {model_name}")
            # 重置失败计数，给所有部署一个机会
            for d in deployments:
                self.failure_count[d] = 0
                self.deployment_health[d] = True
            healthy_deployments = deployments
        
        # 负载均衡：选择最少使用的部署
        current_time = time.time()
        best_deployment = min(healthy_deployments, key=lambda d: self.last_used.get(d, 0))
        
        # 更新使用时间
        self.last_used[best_deployment] = current_time
        
        logger.info(f"Selected deployment for {model_name}: {best_deployment}")
        return best_deployment
    
    def mark_deployment_failed(self, deployment_name: str, error_type: str = "429"):
        """标记部署失败
        
        Args:
            deployment_name: 部署名称
            error_type: 错误类型（429, timeout等）
        """
        self.failure_count[deployment_name] = self.failure_count.get(deployment_name, 0) + 1
        
        if error_type == "429":
            # 429错误：暂时标记为不健康，10分钟后恢复
            self.deployment_health[deployment_name] = False
            logger.warning(f"Deployment {deployment_name} marked as unhealthy due to 429 error")
            
            # 设置恢复时间（10分钟后）
            recovery_time = time.time() + 600  # 10分钟
            # 这里可以添加定时器来恢复健康状态
            
        elif self.failure_count[deployment_name] >= 5:
            # 失败次数过多，标记为不健康
            self.deployment_health[deployment_name] = False
            logger.warning(f"Deployment {deployment_name} marked as unhealthy due to repeated failures")
    
    def mark_deployment_success(self, deployment_name: str):
        """标记部署成功，重置失败计数"""
        if deployment_name in self.failure_count:
            self.failure_count[deployment_name] = 0
        self.deployment_health[deployment_name] = True
    
    def get_client_with_fallback(self, model_name: str, max_retries: int = 3) -> Optional[OpenAI]:
        """获取带有故障转移的客户端
        
        Args:
            model_name: 模型名称
            max_retries: 最大重试次数
            
        Returns:
            OpenAI客户端实例
        """
        for attempt in range(max_retries):
            deployment = self.get_best_deployment(model_name)
            if not deployment:
                logger.error(f"No available deployments for {model_name}")
                return None
            
            try:
                client = self._create_client_for_deployment(deployment)
                logger.info(f"Successfully created client for deployment: {deployment}")
                return client
                
            except Exception as e:
                logger.warning(f"Failed to create client for deployment {deployment}: {e}")
                self.mark_deployment_failed(deployment, "connection")
                continue
        
        logger.error(f"Failed to create client for {model_name} after {max_retries} attempts")
        return None
    
    def _create_client_for_deployment(self, deployment_name: str) -> OpenAI:
        """为特定部署创建客户端"""
        # 从配置中获取部署信息
        model_config = self.config.get("model_configs", {}).get(deployment_name, {})
        
        if not model_config:
            raise ValueError(f"No configuration found for deployment: {deployment_name}")
        
        provider = model_config.get("provider", "user_azure")
        
        if provider == "user_azure":
            return AzureOpenAI(
                api_key=self.config.get("user_azure_api_key"),
                api_version=model_config.get("api_version", "2024-02-15-preview"),
                azure_endpoint=model_config.get("azure_endpoint"),
                timeout=httpx.Timeout(150.0, read=150.0, write=30.0, connect=30.0)
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def execute_with_retry_and_fallback(self, model_name: str, api_call_func, *args, **kwargs):
        """执行API调用，包含重试和故障转移逻辑
        
        Args:
            model_name: 模型名称
            api_call_func: API调用函数
            *args, **kwargs: 传递给API调用函数的参数
            
        Returns:
            API调用结果
        """
        deployments = self.parallel_deployments.get(model_name, [model_name])
        
        for deployment in deployments:
            if not self.deployment_health.get(deployment, True):
                continue
                
            try:
                client = self._create_client_for_deployment(deployment)
                result = api_call_func(client, *args, **kwargs)
                
                # 成功，标记部署为健康
                self.mark_deployment_success(deployment)
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "too many requests" in error_str:
                    logger.warning(f"429 error with deployment {deployment}, trying next...")
                    self.mark_deployment_failed(deployment, "429")
                    continue
                elif "timeout" in error_str:
                    logger.warning(f"Timeout with deployment {deployment}, trying next...")
                    self.mark_deployment_failed(deployment, "timeout")
                    continue
                else:
                    # 其他错误，也尝试下一个部署
                    logger.warning(f"Error with deployment {deployment}: {e}")
                    self.mark_deployment_failed(deployment, "other")
                    continue
        
        raise Exception(f"All deployments failed for model {model_name}")
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """获取所有部署的状态信息"""
        status = {}
        for model, deployments in self.parallel_deployments.items():
            status[model] = {}
            for deployment in deployments:
                status[model][deployment] = {
                    "healthy": self.deployment_health.get(deployment, True),
                    "failure_count": self.failure_count.get(deployment, 0),
                    "last_used": self.last_used.get(deployment, 0)
                }
        return status
    
    def print_status(self):
        """打印部署状态"""
        print("🚀 智能部署管理器状态:")
        print("=" * 50)
        
        for model, deployments in self.parallel_deployments.items():
            print(f"\n📊 {model}:")
            for deployment in deployments:
                health = "✅ 健康" if self.deployment_health.get(deployment, True) else "❌ 不健康"
                failures = self.failure_count.get(deployment, 0)
                last_used = self.last_used.get(deployment, 0)
                last_used_str = time.strftime("%H:%M:%S", time.localtime(last_used)) if last_used > 0 else "从未使用"
                
                print(f"  • {deployment}: {health} (失败次数: {failures}, 上次使用: {last_used_str})")


# 全局实例
_deployment_manager = None

def get_deployment_manager() -> SmartDeploymentManager:
    """获取全局部署管理器实例"""
    global _deployment_manager
    if _deployment_manager is None:
        _deployment_manager = SmartDeploymentManager()
    return _deployment_manager


def create_smart_client(model_name: str) -> Optional[OpenAI]:
    """创建智能客户端，包含故障转移功能"""
    manager = get_deployment_manager()
    return manager.get_client_with_fallback(model_name)


def execute_with_smart_retry(model_name: str, api_call_func, *args, **kwargs):
    """执行带有智能重试的API调用"""
    manager = get_deployment_manager()
    return manager.execute_with_retry_and_fallback(model_name, api_call_func, *args, **kwargs)


if __name__ == "__main__":
    # 测试代码
    manager = SmartDeploymentManager()
    manager.print_status()
    
    # 测试获取最佳部署
    print(f"\n🎯 Llama-3.3-70B-Instruct最佳部署: {manager.get_best_deployment('Llama-3.3-70B-Instruct')}")
    print(f"🎯 DeepSeek-V3-0324最佳部署: {manager.get_best_deployment('DeepSeek-V3-0324')}")