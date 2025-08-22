#!/usr/bin/env python3
"""
API Client Manager
==================
统一的多模型API客户端管理器，支持OpenAI、Azure OpenAI、idealab等多个提供商
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from openai import OpenAI, AzureOpenAI

logger = logging.getLogger(__name__)

# 支持的模型列表 (更新：包含所有可用模型)
SUPPORTED_MODELS = [
    # Azure OpenAI 模型
    "gpt-4o-mini",
    
    # GPT系列 (通过idealab)
    "gpt-41-0414-global", "o1-1217-global", "o3-0416-global", "o4-mini-0416-global",
    
    # Claude系列 (通过idealab)
    "claude37_sonnet", "claude_sonnet4", "claude_opus4",
    
    # Gemini系列 (通过idealab)
    "gemini-2.5-pro-06-17", "gemini-2.5-flash-06-17", "gemini-1.5-pro", "gemini-2.0-flash",
    
    # DeepSeek 模型 (通过idealab)
    "deepseek-v3-671b", "deepseek-r1-671b", "DeepSeek-V3-671B", "DeepSeek-R1-671B",
    
    # Qwen 模型 (通过idealab) 
    "qwen2.5-max", "qwen2.5-72b-instruct", "qwen2.5-32b-instruct", "qwen2.5-14b-instruct", 
    "qwen2.5-7b-instruct", "qwen2.5-3b-instruct",
    
    # Kimi 模型 (通过idealab)
    "kimi-k2",
    
    # 新增的用户模型 (通过专用Azure endpoint)
    "DeepSeek-R1-0528", "DeepSeek-V3-0324",
    # 并行部署实例 (Azure上的多个deployment)
    "DeepSeek-V3-0324-2", "DeepSeek-V3-0324-3",
    "DeepSeek-R1-0528-2", "DeepSeek-R1-0528-3",
    "Llama-3.3-70B-Instruct-2", "Llama-3.3-70B-Instruct-3",
    "gpt-5-mini", "gpt-5-nano", "gpt-oss-120b",
    "grok-3"
]

# 不可用的模型列表 (保留供参考)
UNAVAILABLE_MODELS = [
    # OpenAI 模型 (需要直接OpenAI API访问)
    "gpt-4o", "gpt-o1", "gpt-o3", "gpt-o4-mini",
    
    # Claude 模型 (idealab当前无权限)
    "claude-opus-4", "claude-sonnet-4", "claude-sonnet-3.7", "claude-haiku-3.5",
    
    # Gemini 模型 (idealab当前无权限)
    "gemini-2.5-pro", "gemini-2.5-flash",
    
    # Llama 模型 (idealab模型名称不匹配)
    "llama-3.3-70b-instruct", "llama-4-scout-17b",
    
    # Qwen 限流模型
    "qwen2.5-72b-instruct"
]

# 模型提供商映射 (更新：包含所有可用模型)
MODEL_PROVIDER_MAP = {
    # Azure OpenAI 模型
    "gpt-4o-mini": "azure",
    
    # 所有其他模型通过idealab
    "gpt-41-0414-global": "idealab",
    "o1-1217-global": "idealab",
    "o3-0416-global": "idealab",
    "o4-mini-0416-global": "idealab",
    "claude37_sonnet": "idealab",
    "claude_sonnet4": "idealab",
    "claude_opus4": "idealab",
    "gemini-2.5-pro-06-17": "idealab",
    "gemini-2.5-flash-06-17": "idealab",
    "gemini-1.5-pro": "idealab",
    "gemini-2.0-flash": "idealab",
    "deepseek-v3-671b": "idealab",
    "deepseek-r1-671b": "idealab",
    "DeepSeek-V3-671B": "idealab",
    "DeepSeek-R1-671B": "idealab",
    "qwen2.5-max": "idealab",
    "qwen2.5-72b-instruct": "idealab",
    "qwen2.5-32b-instruct": "idealab", 
    "qwen2.5-14b-instruct": "idealab",
    "qwen2.5-7b-instruct": "idealab",
    "qwen2.5-3b-instruct": "idealab",
    "kimi-k2": "idealab",
    
    # 用户提供的新模型 (通过专用Azure endpoint)
    "DeepSeek-R1-0528": "user_azure",      # 原始实例（无后缀）
    "DeepSeek-V3-0324": "user_azure",      # 原始实例（无后缀）
    # 新增的并行DeepSeek实例
    "deepseek-v3-0324-2": "user_azure",    # 并行实例2
    "deepseek-r1-0528-2": "user_azure",    # 并行实例2
    "deepseek-v3-0324-3": "user_azure",    # 并行实例3
    "deepseek-r1-0528-3": "user_azure",    # 并行实例3
    "gpt-5-mini": "user_azure",
    "gpt-5-nano": "user_azure",
    "gpt-oss-120b": "user_azure",
    "grok-3": "user_azure",
    "Llama-3.3-70B-Instruct": "user_azure",   # 原始实例（无后缀）
    # Llama-3.3并行实例
    "llama-3.3-70b-instruct-2": "user_azure", # 并行实例2
    "llama-3.3-70b-instruct-3": "user_azure"  # 并行实例3
}


class APIClientManager:
    """统一的 API 客户端管理器，支持多API Key池"""
    
    _instance = None
    _client = None
    _config = None
    _idealab_keys = None
    _key_usage_count = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APIClientManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化管理器"""
        if self._config is None:
            self._config = self._load_config_file()
            self._client = None
            self._initialize_key_pools()
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from config directory
        
        Returns:
            dict: Configuration dictionary or empty dict if not found
        """
        config_files = ['config/config.json', 'config/api_keys.json', 'config/api-keys.json']
        print(config_files)
        for config_file in config_files:
            config_path = Path(config_file)
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)
                        logger.info(f"Loaded configuration from {config_file}")
                        return config_data
                except Exception as e:
                    logger.warning(f"Failed to load {config_file}: {e}")
                    continue
        
        return {}
    
    def _initialize_key_pools(self):
        """初始化API Key池"""
        # IdealLab API Keys池
        self._idealab_keys = [
            self._config.get('idealab_api_key', '956c41bd0f31beaf68b871d4987af4bb'),
            '3d906058842b6cf4cee8aaa019f7e77b',
            '88a9a9010f2864bfb53996279dc6c3b9'
        ]
        
        # Key使用计数（用于轮询）
        self._key_usage_count = {
            'baseline': 0,
            'cot': 0,
            'optimal': 0,
            'flawed': 0,
            'general': 0
        }
        
        # Prompt类型到API Key的映射策略
        self._prompt_key_strategy = {
            'baseline': 0,  # 使用第1个key
            'cot': 1,       # 使用第2个key  
            'optimal': 2,   # 使用第3个key
            'flawed': -1    # 轮询使用
        }
    
    def get_client(self, model: Optional[str] = None, prompt_type: Optional[str] = None,
                   force_azure: Optional[bool] = None, deployment_name: Optional[str] = None,
                   key_index: Optional[int] = None) -> Union[OpenAI, AzureOpenAI]:
        """Get OpenAI client instance for specific model with intelligent key selection
        
        Args:
            model: Model name to get client for
            prompt_type: Prompt type for key selection
            force_azure: Force Azure client
            deployment_name: Deployment name
            key_index: Optional IdealLab key index (0-2)
            prompt_type: Prompt type for IdealLab key selection
            force_azure: Force use of Azure OpenAI (overrides config)
            deployment_name: Override deployment name for Azure
            
        Returns:
            OpenAI or AzureOpenAI client instance
        """
        # 如果指定了模型，根据模型确定提供商
        if model:
            provider = MODEL_PROVIDER_MAP.get(model, 'idealab')
            
            # 根据提供商返回相应的客户端
            if provider == 'azure':
                use_azure = True
                deployment_name = model
            elif provider == 'user_azure':
                # 使用用户提供的Azure端点
                return self._get_user_azure_client(model)
            elif provider == 'ideallab':
                # 使用IdealLab API with智能key选择
                return self._get_idealab_client(model, prompt_type, key_index)
            else:
                use_azure = force_azure if force_azure is not None else self._config.get('use_azure_openai', False)
        else:
            # 没有指定模型，使用默认逻辑
            use_azure = force_azure
            if use_azure is None:
                use_azure = os.getenv('USE_AZURE_OPENAI', '').lower() == 'true'
                if not use_azure and self._config.get('use_azure_openai', False):
                    use_azure = True
        
        if use_azure:
            # Azure OpenAI配置 - 优先使用配置文件，回退到环境变量
            api_key = (self._config.get('azure_openai_api_key') or 
                      self._config.get('AZURE_OPENAI_API_KEY') or 
                      os.getenv('AZURE_OPENAI_API_KEY'))

            api_base = (self._config.get('azure_openai_api_base') or 
                       self._config.get('AZURE_OPENAI_API_BASE') or 
                       os.getenv('AZURE_OPENAI_API_BASE'))
            
            api_version = (self._config.get('azure_openai_api_version') or 
                          self._config.get('AZURE_OPENAI_API_VERSION') or 
                          os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview'))
            
            # 使用传入的 deployment_name 或从配置获取
            if deployment_name is None:
                deployment_name = (self._config.get('azure_openai_deployment_name') or 
                                 self._config.get('AZURE_OPENAI_DEPLOYMENT_NAME') or 
                                 os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'))
            
            if not all([api_key, api_base, deployment_name]):
                print("[ERROR] Azure OpenAI configuration incomplete!")
                print("[ERROR] Required: azure_openai_api_key, azure_openai_api_base, azure_openai_deployment_name")
                print("[INFO] Check ./config/config.json or environment variables")
                raise ValueError("Azure OpenAI configuration incomplete")
            
            client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=api_base
            )
            # 存储 deployment name 供后续使用
            client.deployment_name = deployment_name
            return client
            
        else:
            # 标准OpenAI配置 - 优先使用配置文件，回退到环境变量
            api_key = (self._config.get('openai_api_key') or 
                      self._config.get('OPENAI_API_KEY') or 
                      self._config.get('api-key') or 
                      self._config.get('api_key') or 
                      os.getenv('OPENAI_API_KEY'))
            
            if not api_key:
                print("[ERROR] OpenAI API key not found!")
                print("[ERROR] Please set 'openai_api_key' in config/config.json or OPENAI_API_KEY environment variable")
                raise ValueError("OpenAI API key not configured")
            
            return OpenAI(api_key=api_key)
    
    def get_model_name(self, default: str = "gpt-4o-mini") -> str:
        """Get appropriate model name based on client type
        
        Args:
            default: Default model name if not configured
            APIClientManager
        Returns:
            Model name to use
        """
        if isinstance(self._client, AzureOpenAI):
            # For Azure, return deployment name
            print(getattr(self._client, 'deployment_name', default))
            return getattr(self._client, 'deployment_name', default)
        else:
            # For standard OpenAI, use configured model or default
            return self._config.get('openai_model', default)
    
    def _get_idealab_client(self, model: str, prompt_type: Optional[str] = None, key_index: Optional[int] = None) -> OpenAI:
        """Get IdealLab API client with intelligent key selection
        
        Args:
            model: Model name
            prompt_type: Prompt type for key selection strategy
            key_index: Optional explicit key index (0-2)
        """
        api_base = self._config.get('idealab_api_base')
        if not api_base:
            raise ValueError("IdealLab API base URL missing")
        
        # 智能选择API Key
        api_key = self._select_idealab_key(prompt_type, key_index)
        
        client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )
        client.model_name = model
        client.api_key_used = api_key  # 记录使用的key
        return client
    
    def _select_idealab_key(self, prompt_type: Optional[str] = None, key_index: Optional[int] = None) -> str:
        """智能选择IdealLab API Key
        
        策略：
        - 如果指定了key_index，直接使用
        - baseline使用key0
        - cot使用key1
        - optimal使用key2
        - flawed类型轮询使用
        - 其他情况轮询使用
        """
        # 检查环境变量覆盖
        override_key = os.getenv('IDEALAB_API_KEY_OVERRIDE')
        if override_key:
            return override_key
        
        # 如果指定了key索引，直接使用
        if key_index is not None:
            if 0 <= key_index < len(self._idealab_keys):
                return self._idealab_keys[key_index]
            else:
                logger.warning(f"Invalid key_index {key_index}, falling back to default selection")
        
        if not prompt_type:
            # 默认轮询
            self._key_usage_count['general'] += 1
            return self._idealab_keys[self._key_usage_count['general'] % len(self._idealab_keys)]
        
        # 清理prompt_type
        if prompt_type.startswith('flawed_'):
            base_type = 'flawed'
        else:
            base_type = prompt_type
        
        # 根据策略选择key
        if base_type in self._prompt_key_strategy:
            key_index = self._prompt_key_strategy[base_type]
            if key_index >= 0:
                # 固定分配
                return self._idealab_keys[key_index]
            else:
                # 轮询分配
                self._key_usage_count[base_type] += 1
                return self._idealab_keys[self._key_usage_count[base_type] % len(self._idealab_keys)]
        else:
            # 默认轮询
            self._key_usage_count['general'] += 1
            return self._idealab_keys[self._key_usage_count['general'] % len(self._idealab_keys)]
    
    def _get_user_azure_client(self, model: str) -> AzureOpenAI:
        """Get user-provided Azure client"""
        # 从配置中获取模型特定的配置
        model_config = self._config.get('model_configs', {}).get(model, {})
        
        if model_config.get('provider') == 'user_azure':
            azure_endpoint = model_config.get('azure_endpoint')
            api_version = model_config.get('api_version', '2024-12-01-preview')
            deployment_name = model_config.get('deployment_name', model)
            
            # 使用用户的Azure API key (假设存储在环境变量中)
            api_key = os.getenv('USER_AZURE_API_KEY') or self._config.get('user_azure_api_key')
            
            if not all([api_key, azure_endpoint]):
                raise ValueError(f"User Azure configuration incomplete for {model}")
            
            client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=azure_endpoint
            )
            client.deployment_name = deployment_name
            return client
        else:
            raise ValueError(f"Model {model} is not configured for user_azure")
    
    def get_embedding_model(self) -> str:
        """Get appropriate embedding model name"""
        if hasattr(self, '_client') and isinstance(self._client, AzureOpenAI):
            # Azure 可能有专门的 embedding deployment
            return (self._config.get('azure_openai_embedding_deployment') or 
                    "text-embedding-3-large")
        else:
            return self._config.get('embedding_model', "text-embedding-3-large")
    
    def reload_config(self):
        """Reload configuration from file"""
        self._config = self._load_config_file()
        self._client = None
        logger.info("Configuration reloaded")


# 便捷函数
def get_api_client(force_azure: Optional[bool] = None, 
                   deployment_name: Optional[str] = None) -> Union[OpenAI, AzureOpenAI]:
    """Get API client instance
    
    Args:
        force_azure: Force use of Azure OpenAI
        deployment_name: Override deployment name for Azure
        
    Returns:
        OpenAI or AzureOpenAI client
    """
    manager = APIClientManager()
    return manager.get_client(force_azure=force_azure, deployment_name=deployment_name)


def get_model_name(default: str = "gpt-4o-mini") -> str:
    """Get appropriate model name for current client"""
    manager = APIClientManager()
    return manager.get_model_name(default=default)


def get_embedding_model() -> str:
    """Get appropriate embedding model name"""
    manager = APIClientManager()
    return manager.get_embedding_model()


# 新增：多模型支持
class MultiModelAPIManager:
    """支持多个模型和提供商的API管理器"""
    
    def __init__(self):
        self.clients = {}  # 缓存不同提供商的客户端
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        config_path = Path('config/config.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
    
    def get_client_for_model(self, model_name: str, prompt_type: Optional[str] = None, key_index: Optional[int] = None) -> OpenAI:
        """根据模型名称获取对应的API客户端
        
        Args:
            model_name: 模型名称
            prompt_type: 提示类型（用于IdealLab的智能key 选择）
            key_index: 可选的IdealLab key索引（0-2）
        """
        # 使用智能路由器优化端点选择
        from smart_model_router import route_model
        provider, resolved_model = route_model(model_name)
        
        # 更新model_name为解析后的名称
        model_name = resolved_model
        
        if model_name not in SUPPORTED_MODELS:
            # 如果路由器给出的模型不在支持列表，记录警告但继续尝试
            logger.warning(f"Model {model_name} not in SUPPORTED_MODELS, attempting anyway")
        
        # provider已经由路由器决定，不再使用MODEL_PROVIDER_MAP
        
        if provider in self.clients:
            return self.clients[provider]
        
        if provider == "azure":
            # Azure OpenAI 客户端
            client = AzureOpenAI(
                api_key=self.config.get('azure_openai_api_key'),
                api_version=self.config.get('azure_openai_api_version', '2024-12-01-preview'),
                azure_endpoint=self.config.get('azure_openai_api_base')
            )
            client.deployment_name = self.config.get('azure_openai_deployment_name')
        
        elif provider == "openai":
            # 标准 OpenAI 客户端
            client = OpenAI(
                api_key=self.config.get('openai_api_key')
            )
        
        elif provider == "idealab":
            # idealab 客户端 (使用OpenAI兼容接口)
            # 使用APIClientManager的智能key选择
            manager = APIClientManager()
            client = manager._get_idealab_client(model_name, prompt_type)
        
            
        elif provider == "user_azure":
            # 用户提供的Azure endpoint
            # 注意：每个模型需要独立的客户端实例，因为deployment_name不同
            
            # 特殊处理DeepSeek和Grok模型 - 使用标准Azure端口
            if "deepseek" in model_name.lower() or "DeepSeek" in model_name or "grok" in model_name.lower():
                client = AzureOpenAI(
                    api_key="6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza",
                    api_version="2024-02-15-preview",
                    azure_endpoint="https://85409-me3ofvov-eastus2.services.ai.azure.com"
                )
            # 特殊处理gpt-5-nano - 使用专门的endpoint和API版本
            elif model_name == "gpt-5-nano":
                client = AzureOpenAI(
                    api_key="6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza",
                    api_version="2024-12-01-preview",
                    azure_endpoint="https://85409-me3ofvov-eastus2.cognitiveservices.azure.com/"
                )
                # 标记为gpt-5-nano，后续API调用时会过滤参数
                client.is_gpt5_nano = True
            else:
                # 其他user_azure模型使用标准配置
                client = AzureOpenAI(
                    api_key="6Qc2Oxuf0oVtGutYCTSHOGbm1Dmn4kESwrDYeytkJsHWv3xqrnEMJQQJ99BHACHYHv6XJ3w3AAAAACOGXWza",
                    api_version="2024-02-15-preview",
                    azure_endpoint="https://85409-me3ofvov-eastus2.services.ai.azure.com"
                )
                # 标记为非gpt-5-nano
                client.is_gpt5_nano = False
            
            # 对于用户的Azure模型，deployment_name就是模型名称本身
            client.deployment_name = model_name
            
            # 不缓存user_azure客户端，因为每个模型需要不同的deployment_name
            return client
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # 只缓存非user_azure的客户端
        if provider != "user_azure":
            self.clients[provider] = client
        logger.info(f"Created {provider} client for model {model_name}")
        return client
    
    def get_model_name_for_api(self, model_name: str) -> str:
        """获取API调用时使用的模型名称"""
        # 使用智能路由器解析模型名称
        from smart_model_router import route_model
        provider, resolved_model = route_model(model_name)
        
        if provider == "azure":
            # Azure使用deployment name
            return self.config.get('azure_openai_deployment_name', 'gpt-4o-mini')
        elif provider == "user_azure":
            # user_azure直接使用解析后的模型名作为deployment name
            return resolved_model
        elif provider == "idealab":
            # idealab保持原名
            return resolved_model
        else:
            # 其他直接使用模型名
            return resolved_model
    
    def test_model_connection(self, model_name: str) -> bool:
        """测试特定模型的连接"""
        try:
            client = self.get_client_for_model(model_name)
            api_model_name = self.get_model_name_for_api(model_name)
            
            # 发送测试请求（不带max_tokens和temperature）
            response = client.chat.completions.create(
                model=api_model_name,
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                timeout=30  # 设置30秒超时
            )
            
            logger.info(f"Model {model_name} connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Model {model_name} connection test failed: {e}")
            return False
    
    def list_available_models(self) -> List[str]:
        """列出所有可用的模型"""
        available = []
        for model in SUPPORTED_MODELS:
            if self.test_model_connection(model):
                available.append(model)
        return available


# 便捷函数用于多模型测试
def get_multi_model_manager() -> MultiModelAPIManager:
    """获取多模型API管理器实例"""
    return MultiModelAPIManager()


def get_client_for_model(model_name: str, prompt_type: Optional[str] = None, key_index: Optional[int] = None) -> OpenAI:
    """便捷函数：根据模型名称获取客户端
    
    Args:
        model_name: 模型名称
        prompt_type: 提示类型（用于IdealLab的智能 key 选择）
        key_index: 可选的IdealLab key索引（0-2）
    """
    manager = get_multi_model_manager()
    return manager.get_client_for_model(model_name, prompt_type, key_index)


def get_api_model_name(model_name: str) -> str:
    """便捷函数：获取API调用时的模型名称"""
    manager = get_multi_model_manager()
    return manager.get_model_name_for_api(model_name)


def test_all_models() -> Dict[str, bool]:
    """测试所有支持的模型连接"""
    manager = get_multi_model_manager()
    results = {}
    
    print("Testing model connections...")
    for model in SUPPORTED_MODELS:
        print(f"Testing {model}...", end=" ")
        success = manager.test_model_connection(model)
        results[model] = success
        print("✓" if success else "✗")
    
    return results