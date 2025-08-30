#!/usr/bin/env python3
"""
MCP Tool Embedding Manager
==========================
独立的工具嵌入管理系统，用于动态检索MCP工具规范

Features:
- 多维度工具嵌入（描述、参数、功能）
- FAISS向量索引
- 智能相似度搜索
- 批量处理和缓存
- 命令行接口
"""

import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, field, asdict
from collections import OrderedDict
import pickle
import logging
from datetime import datetime
import argparse
import os
from tqdm import tqdm
import hashlib
import threading
from api_client_manager import get_api_client, get_embedding_model


# Optional imports with fallback
import openai
HAS_OPENAI = True


try:
    import faiss
    HAS_FAISS = True
except ImportError:
    faiss = None
    HAS_FAISS = False


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



# 文件：mcp_embedding_manager.py
# 位置：第48-150行
# 类：PermanentSmartCache（改进版）

class PermanentSmartCache:
    """永久智能缓存管理器 - 无过期机制，修复了迭代错误"""
    
    def __init__(self, max_size: int = 1000, similarity_threshold: float = 0.95):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.cache = OrderedDict()
        self.embeddings = {}  # 存储查询的embedding用于相似度比较
        self.access_counts = {}  # 记录访问频率
        self._lock = threading.RLock()  # 添加线程锁以防并发问题
        
    def get(self, key: str, query_embedding: np.ndarray = None) -> Any:
        """智能获取缓存，支持相似度匹配"""
        with self._lock:
            # 1. 精确匹配
            if key in self.cache:
                # 更新访问计数和LRU顺序
                self.access_counts[key] = self.access_counts.get(key, 0) + 1
                self.cache.move_to_end(key)
                return self.cache[key]
            
            # 2. 相似度匹配（如果提供了embedding）
            if query_embedding is not None:
                similar_key = self._find_similar_key(query_embedding)
                if similar_key:
                    logger.debug(f"[Cache] Similar match: '{key}' → '{similar_key}'")
                    self.access_counts[similar_key] = self.access_counts.get(similar_key, 0) + 1
                    self.cache.move_to_end(similar_key)
                    return self.cache[similar_key]
            
            return None
    
    def put(self, key: str, value: Any, query_embedding: np.ndarray = None):
        """智能存储缓存"""
        with self._lock:
            # 检查相似条目
            if query_embedding is not None:
                similar_key = self._find_similar_key(query_embedding)
                if similar_key:
                    logger.debug(f"[Cache] Merging similar: '{key}' → '{similar_key}'")
                    # 更新现有条目
                    self.cache[similar_key] = value
                    self.access_counts[similar_key] = self.access_counts.get(similar_key, 0) + 1
                    return
            
            # 缓存大小管理
            while len(self.cache) >= self.max_size:
                self._evict_lfu()  # 使用LFU（最少频率使用）策略
            
            # 存储新条目
            self.cache[key] = value
            if query_embedding is not None:
                self.embeddings[key] = query_embedding
            self.access_counts[key] = 1
    
    def _find_similar_key(self, query_embedding: np.ndarray) -> Optional[str]:
        """查找相似的缓存键"""
        max_similarity = 0
        similar_key = None
        
        # 使用列表副本避免迭代时修改的问题
        for key in list(self.embeddings.keys()):
            if key not in self.cache:
                # 清理过期的embedding
                self.embeddings.pop(key, None)
                continue
                
            embedding = self.embeddings[key]
            # 计算余弦相似度
            try:
                similarity = np.dot(query_embedding, embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
                )
                
                if similarity > self.similarity_threshold and similarity > max_similarity:
                    max_similarity = similarity
                    similar_key = key
            except Exception as e:
                logger.debug(f"Error calculating similarity for key {key}: {e}")
                continue
        
        return similar_key
    
    def _evict_lfu(self):
        """LFU淘汰策略 - 移除访问频率最低的条目"""
        if not self.cache:
            return
            
        # 找出访问频率最低的键
        min_count = min(self.access_counts.values())
        
        # 找到所有最低频率的键
        lfu_candidates = [(k, self.access_counts[k]) for k in self.cache.keys() 
                          if self.access_counts.get(k, 0) == min_count]
        
        if lfu_candidates:
            # 选择最旧的（第一个）
            key_to_remove = lfu_candidates[0][0]
            
            # 删除条目
            self.cache.pop(key_to_remove, None)
            self.embeddings.pop(key_to_remove, None)
            self.access_counts.pop(key_to_remove, None)
            logger.debug(f"[Cache] Evicted LFU entry: {key_to_remove} (count: {min_count})")
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
            self.embeddings.clear()
            self.access_counts.clear()
            logger.info("[Cache] Cleared all entries")
    
    def save_to_file(self, filepath: str):
        """保存缓存到文件"""
        with self._lock:
            save_data = {
                'cache': dict(self.cache),
                'embeddings': self.embeddings,
                'access_counts': self.access_counts
            }
            try:
                with open(filepath, 'wb') as f:
                    pickle.dump(save_data, f)
                logger.info(f"[Cache] Saved {len(self.cache)} entries to {filepath}")
            except Exception as e:
                logger.error(f"Failed to save cache: {e}")
    
    def load_from_file(self, filepath: str):
        """从文件加载缓存"""
        with self._lock:
            try:
                with open(filepath, 'rb') as f:
                    save_data = pickle.load(f)
                
                self.cache = OrderedDict(save_data.get('cache', {}))
                self.embeddings = save_data.get('embeddings', {})
                self.access_counts = save_data.get('access_counts', {})
                
                logger.info(f"[Cache] Loaded {len(self.cache)} entries from file")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'embeddings_count': len(self.embeddings),
                'total_accesses': sum(self.access_counts.values()),
                'average_access_count': sum(self.access_counts.values()) / len(self.access_counts) if self.access_counts else 0
            }
    
    def __len__(self):
        """返回缓存大小"""
        return len(self.cache)


# ===========================
# Data Classes
# ===========================

@dataclass
class ToolEmbedding:
    """工具的向量表示"""
    tool_name: str
    category: str
    description: str
    description_embedding: np.ndarray
    parameter_embedding: np.ndarray
    functionality_embedding: np.ndarray
    combined_embedding: np.ndarray
    mcp_protocol: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            'tool_name': self.tool_name,
            'category': self.category,
            'description': self.description,
            'description_embedding': self.description_embedding.tolist(),
            'parameter_embedding': self.parameter_embedding.tolist(),
            'functionality_embedding': self.functionality_embedding.tolist(),
            'combined_embedding': self.combined_embedding.tolist(),
            'mcp_protocol': self.mcp_protocol,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolEmbedding':
        """从字典创建实例"""
        return cls(
            tool_name=data['tool_name'],
            category=data['category'],
            description=data['description'],
            description_embedding=np.array(data['description_embedding']),
            parameter_embedding=np.array(data['parameter_embedding']),
            functionality_embedding=np.array(data['functionality_embedding']),
            combined_embedding=np.array(data['combined_embedding']),
            mcp_protocol=data['mcp_protocol'],
            metadata=data.get('metadata', {})
        )


@dataclass
class EmbeddingConfig:
    """嵌入配置"""
    model: str = "text-embedding-3-large"  # <- 修改为便宜的模型
    dimension: int = 3072  # <- text-embedding-3-large 也是 1536 维
    description_weight: float = 0.4
    parameter_weight: float = 0.3
    functionality_weight: float = 0.3
    batch_size: int = 100
    cache_dir: str = ".mcp_embedding_cache"

@dataclass
class SearchResult:
    """搜索结果"""
    tool_name: str
    score: float
    mcp_protocol: Dict[str, Any]
    category: str
    reason: str = ""


# ===========================
# Main Embedding Manager
# ===========================

class MCPEmbeddingManager:
    _instance = None
    _initialized = False
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Optional[EmbeddingConfig] = None, api_key: Optional[str] = None):
        """初始化嵌入管理器"""

        if MCPEmbeddingManager._initialized:
            return
            
        with MCPEmbeddingManager._lock:
            if MCPEmbeddingManager._initialized:
                return
            
            self.config = config or EmbeddingConfig()
            
            # 使用统一的 API 客户端管理器
            from api_client_manager import get_api_client, get_embedding_model
            
            print("[MCPEmbeddingManager] Initializing with unified API client manager")
            
            # 获取 OpenAI/Azure OpenAI 客户端
            self.client = get_api_client()
            
            # 获取并更新嵌入模型名称
            embedding_model = get_embedding_model()
            self.config.model = embedding_model
            print(f"[MCPEmbeddingManager] Using embedding model: {embedding_model}")
            
            # Azure OpenAI 的嵌入模型通常是 1536 维
            if embedding_model == "text-embedding-3-large":
                self.config.dimension = 3072
            else:
                self.config.dimension = 1536
            
            print(f"[MCPEmbeddingManager] Client initialized successfully")
            
            self.tool_embeddings: Dict[str, ToolEmbedding] = {}
            self.tool_names: List[str] = []
            self.index = None
            
            # Caches - 修正初始化顺序
            if self.config.cache_dir is None:
                self.cache_dir = Path(".mcp_embedding_cache")
            else:
                self.cache_dir = Path(self.config.cache_dir)
            self.cache_dir.mkdir(exist_ok=True)
            
            # 先定义缓存文件路径
            self.embedding_cache_file = self.cache_dir / "embedding_cache.pkl"  # <- 添加这行
            self.search_cache_file = self.cache_dir / "search_cache.pkl"
            
            # 然后加载缓存
            self.embedding_cache = self._load_embedding_cache()
            self.search_cache = {}
            self._load_search_cache()
            
            # 初始化操作映射（用于查询规范化）
            self.synonym_to_canonical = {}
            self._initialize_operation_mappings()

            self.search_cache = PermanentSmartCache(
                max_size=10000,  # 搜索缓存
                similarity_threshold=0.95
            )
            
            # Embedding缓存 - 完全基于文件的永久存储
            self.embedding_cache_file = self.cache_dir / "embedding_cache.pkl"
            self.embedding_cache = self._load_embedding_cache()
            
            # 加载搜索缓存
            self.search_cache_file = self.cache_dir / "search_cache.pkl"
            if self.search_cache_file.exists():
                self.search_cache.load_from_file(str(self.search_cache_file))
            
            # 批量预计算管理
            self.batch_queue = []
            self.batch_size = 20  # Azure OpenAI批量大小限制
            self.last_batch_time = 0
            self.batch_interval = 1.0  # 批量请求间隔

            MCPEmbeddingManager._initialized = True

    
    def _load_config_file(self) -> Dict[str, Any]:
        """不再需要这个方法，由 APIClientManager 统一处理"""
        # 保留方法以保持向后兼容，但实际上不使用
        return {}
    
    def _build_faiss_index(self):
        """构建FAISS索引从当前的tool_embeddings"""
        if not HAS_FAISS:
            logger.warning("FAISS not available, skipping index build")
            return
            
        if not self.tool_embeddings:
            logger.warning("No tool embeddings to index")
            return
            
        # 提取所有嵌入向量
        embeddings = []
        tool_names = []
        
        for tool_name, tool_emb in self.tool_embeddings.items():
            embeddings.append(tool_emb.combined_embedding)
            tool_names.append(tool_name)
        
        # 创建FAISS索引
        embeddings_matrix = np.vstack(embeddings).astype('float32')
        self.index = faiss.IndexFlatIP(self.config.dimension)
        
        # 归一化向量（用于余弦相似度）
        faiss.normalize_L2(embeddings_matrix)
        self.index.add(embeddings_matrix)
        
        self.tool_names = tool_names
        logger.info(f"Built FAISS index with {len(tool_names)} tools")
    

    def _load_embedding_cache(self) -> Dict[str, np.ndarray]:
        """加载embedding缓存，增强错误处理"""
        cache_file = Path(self.config.cache_dir) / "embedding_cache.pkl"
        
        if not cache_file.exists():
            logger.info("No embedding cache found, starting fresh")
            return {}
        
        # 检查文件大小
        file_size = cache_file.stat().st_size
        if file_size == 0:
            logger.warning(f"Cache file {cache_file} is empty, removing and starting fresh")
            cache_file.unlink()  # 删除空文件
            return {}
        
        logger.info(f"Loading embedding cache from {cache_file} (size: {file_size} bytes)")
        
        try:
            with open(cache_file, 'rb') as f:
                cache = pickle.load(f)
                
            # 验证缓存内容
            if not isinstance(cache, dict):
                logger.warning(f"Invalid cache format (expected dict, got {type(cache)}), starting fresh")
                cache_file.unlink()
                return {}
                
            # 验证缓存条目
            valid_entries = 0
            for key, value in cache.items():
                if isinstance(value, np.ndarray):
                    valid_entries += 1
            
            logger.info(f"Loaded {valid_entries} cached embeddings")
            return cache
            
        except EOFError:
            logger.error(f"Cache file {cache_file} is corrupted (EOFError), removing and starting fresh")
            # 备份损坏的文件以供调试
            backup_path = cache_file.with_suffix('.pkl.corrupted')
            cache_file.rename(backup_path)
            logger.info(f"Corrupted cache backed up to {backup_path}")
            return {}
            
        except (pickle.UnpicklingError, ValueError) as e:
            logger.error(f"Failed to load cache: {e}, removing and starting fresh")
            cache_file.unlink()
            return {}
            
        except Exception as e:
            logger.error(f"Unexpected error loading cache: {e}")
            # 不删除文件，但返回空缓存
            return {}
    
    def _save_embedding_cache(self) -> None:
        """保存embedding缓存，增加原子写入保护"""
        if not self.embedding_cache:
            return
            
        cache_dir = Path(self.config.cache_dir)
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / "embedding_cache.pkl"
        temp_file = cache_dir / "embedding_cache.pkl.tmp"
        
        try:
            # 原子写入：先写到临时文件，然后重命名
            logger.info(f"Saving {len(self.embedding_cache)} embeddings to cache")
            
            with open(temp_file, 'wb') as f:
                pickle.dump(self.embedding_cache, f)
            
            # 验证临时文件
            if temp_file.stat().st_size == 0:
                logger.error("Failed to write cache (file is empty)")
                temp_file.unlink()
                return
                
            # 原子重命名（在POSIX系统上是原子操作）
            temp_file.replace(cache_file)
            logger.info("Embedding cache saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save embedding cache: {e}")
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取embedding - 永久缓存"""
        # 检查永久缓存
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        # API调用获取新的embedding
        response = self.client.embeddings.create(
            model=self.config.model,
            input=text
        )
        embedding = np.array(response.data[0].embedding)
        
        # 永久保存到缓存
        self.embedding_cache[text_hash] = embedding
        
        # 每50个新embedding保存一次
        if len(self.embedding_cache) % 50 == 0:
            self._save_embedding_cache()
        
        return embedding
    
    def _process_batch_embeddings(self) -> np.ndarray:
        """批量处理embedding请求"""
        if not self.batch_queue:
            return None
            
        texts = [item[0] for item in self.batch_queue]
        hashes = [item[1] for item in self.batch_queue]
        
        print(f"[Batch] Processing {len(texts)} embeddings in batch")
        
        # 批量API调用
        response = self.client.embeddings.create(
            model=self.config.model,
            input=texts
        )
        
        # 处理结果
        result_embedding = None
        for i, embedding_data in enumerate(response.data):
            embedding = np.array(embedding_data.embedding)
            
            # 存储到智能缓存
            self.smart_embedding_cache.put(
                hashes[i], 
                embedding,
                query_embedding=embedding
            )
            
            # 返回第一个（当前请求的）
            if i == 0:
                result_embedding = embedding
        
        # 清空队列
        self.batch_queue.clear()
        self.last_batch_time = time.time()
        
        return result_embedding
    
    def _get_single_embedding(self, text: str, text_hash: str) -> np.ndarray:
        """获取单个embedding（fallback）"""
        # 限速
        time.sleep(0.1)  # 100ms延迟，避免429错误
        
        response = self.client.embeddings.create(
            model=self.config.model,
            input=text
        )
        embedding = np.array(response.data[0].embedding)
        
        # 存储到智能缓存
        self.smart_embedding_cache.put(
            text_hash,
            embedding,
            query_embedding=embedding
        )
        
        return embedding
    
    def create_tool_embedding(self, tool_name: str, tool_spec: Dict[str, Any]) -> ToolEmbedding:
        """为单个工具创建嵌入，包含区分度信息"""
        # 1. 提取描述（使用增强的描述）
        description = tool_spec.get('description', '')
        desc_text = f"{tool_name}: {description}"
        desc_emb = self._get_embedding(desc_text)
        
        # 2. 提取参数信息
        param_text = self._format_parameters(tool_spec.get('parameters', []))
        param_emb = self._get_embedding(param_text)
        
        # 3. 提取功能信息（包含区分度）
        func_text = self._format_functionality(tool_name, tool_spec)
        func_emb = self._get_embedding(func_text)
        
        # 4. ============ 新增：区分度嵌入 ============
        differentiation = tool_spec.get('differentiation', {})
        if differentiation:
            # 创建区分度文本
            diff_parts = []
            
            if 'unique_purpose' in differentiation:
                diff_parts.append(differentiation['unique_purpose'])
            
            if 'usage_keywords' in differentiation:
                diff_parts.append(f"Use for: {', '.join(differentiation['usage_keywords'])}")
            
            if 'key_differentiators' in differentiation:
                diff_parts.append(f"Features: {'; '.join(differentiation['key_differentiators'])}")
            
            if 'example_scenario' in differentiation:
                diff_parts.append(f"Example: {differentiation['example_scenario']}")
            
            if diff_parts:
                diff_text = f"{tool_name} differentiation: {'; '.join(diff_parts)}"
                diff_emb = self._get_embedding(diff_text)
                
                # 调整权重，给区分度信息更高权重
                combined = (
                    0.25 * desc_emb +      # 降低描述权重
                    0.20 * param_emb +     # 降低参数权重
                    0.25 * func_emb +      # 降低功能权重
                    0.30 * diff_emb        # 新增区分度权重
                )
            else:
                # 没有区分度信息时使用原权重
                combined = (
                    self.config.description_weight * desc_emb + 
                    self.config.parameter_weight * param_emb + 
                    self.config.functionality_weight * func_emb
                )
        else:
            # 原有逻辑
            combined = (
                self.config.description_weight * desc_emb + 
                self.config.parameter_weight * param_emb + 
                self.config.functionality_weight * func_emb
            )
        # ============ 结束新增 ============
        
        # 归一化
        combined = combined / np.linalg.norm(combined)
        
        return ToolEmbedding(
            tool_name=tool_name,
            category=tool_spec.get('metadata', {}).get('category', 'general'),
            description=description,
            description_embedding=desc_emb,
            parameter_embedding=param_emb,
            functionality_embedding=func_emb,
            combined_embedding=combined,
            mcp_protocol=tool_spec,
            metadata={
                'created_at': datetime.now().isoformat(),
                'embedding_model': self.config.model,
                'has_differentiation': bool(differentiation)  # 标记是否有区分度信息
            }
        )
    
    def _format_parameters(self, parameters: List[Dict]) -> str:
        """格式化参数信息"""
        if not parameters:
            return "No parameters required"
        
        parts = []
        for param in parameters:
            param_desc = f"{param.get('name', 'unnamed')} ({param.get('type', 'any')})"
            if param.get('description'):
                param_desc += f": {param['description']}"
            if param.get('required', True):
                param_desc += " [required]"
            parts.append(param_desc)
        
        return "Parameters: " + "; ".join(parts)
    
    def _format_functionality(self, tool_name: str, tool_spec: Dict) -> str:
        """格式化功能信息"""
        metadata = tool_spec.get('metadata', {})
        parts = []
        
        # 基本信息
        parts.append(f"Tool: {tool_name}")
        parts.append(f"Category: {metadata.get('category', 'general')}")
        parts.append(f"Operation: {metadata.get('operation', 'process')}")
        
        # 依赖关系
        dependencies = tool_spec.get('dependencies', [])
        if dependencies:
            parts.append(f"Dependencies: {', '.join(dependencies)}")
        
        # 返回类型
        returns = tool_spec.get('returns', [])
        if returns:
            return_types = [r.get('type', 'any') for r in returns]
            parts.append(f"Returns: {', '.join(return_types)}")
        
        # 错误处理
        errors = tool_spec.get('errors', [])
        if errors:
            error_codes = [e.get('code', 'ERROR') for e in errors]
            parts.append(f"Possible errors: {', '.join(error_codes)}")
        
        return "; ".join(parts)
    
    def build_index(self, 
                tool_registry_path: Union[str, Path],
                force_rebuild: bool = False) -> Dict[str, Any]:
        """
        构建工具的向量索引
        
        Args:
            tool_registry_path: 工具注册表路径
            force_rebuild: 是否强制重建索引
            
        Returns:
            构建统计信息
        """
        logger.info("Building tool embedding index...")
        
        # 检查是否需要重建
        index_file = self.cache_dir / "tool_index.pkl"
        if index_file.exists() and not force_rebuild:
            logger.info("Loading existing index...")
            self.load_index(index_file)
            return {'status': 'loaded', 'tools': len(self.tool_embeddings)}
        
        # 加载工具注册表
        with open(tool_registry_path, 'r') as f:
            tool_registry = json.load(f)
        
        # 批量创建嵌入
        embeddings = []
        tool_names = []
        
        logger.info(f"Creating embeddings for {len(tool_registry)} tools...")
        for tool_name, tool_spec in tqdm(tool_registry.items()):
            tool_emb = self.create_tool_embedding(tool_name, tool_spec)
            self.tool_embeddings[tool_name] = tool_emb
            embeddings.append(tool_emb.combined_embedding)
            tool_names.append(tool_name)

        # 构建FAISS索引
        if embeddings:  # 确保有嵌入向量
            embeddings_matrix = np.vstack(embeddings).astype('float32')
            
            # 动态获取实际的嵌入维度
            actual_dimension = embeddings_matrix.shape[1]
            
            # 打印调试信息
            print(f"[MCPEmbeddingManager] Expected dimension: {self.config.dimension}")
            print(f"[MCPEmbeddingManager] Actual embedding dimension: {actual_dimension}")
            
            # 如果维度不匹配，更新配置
            if actual_dimension != self.config.dimension:
                logger.warning(f"Dimension mismatch: expected {self.config.dimension}, got {actual_dimension}")
                self.config.dimension = actual_dimension
                print(f"[MCPEmbeddingManager] Updated config dimension to: {self.config.dimension}")
            
            # 使用实际维度创建FAISS索引
            self.index = faiss.IndexFlatIP(actual_dimension)
            faiss.normalize_L2(embeddings_matrix)
            self.index.add(embeddings_matrix)
        else:
            logger.error("No embeddings created, cannot build index")
            raise ValueError("No embeddings were created from the tool registry")
        
        self.tool_names = tool_names
        
        # 保存缓存
        self._save_embedding_cache()
        self.save_index(index_file)
        
        stats = {
            'status': 'built',
            'tools': len(tool_names),
            'categories': len(set(e.category for e in self.tool_embeddings.values())),
            'index_type': 'faiss' if self.index else 'none',
            'embedding_dimension': self.config.dimension  # 现在这是实际维度
        }
        
        logger.info(f"Index built: {stats}")
        return stats
    def _initialize_operation_mappings(self):
        """从operation_embedding_index初始化操作映射"""
        try:
            from operation_embedding_index import get_operation_index
            
            # 获取操作索引实例
            operation_index = get_operation_index()
            
            # 构建同义词映射
            self.synonym_to_canonical = {}
            
            # 使用operation_definitions中的数据
            for canonical, op_def in operation_index.operation_definitions.items():
                # 规范词映射到自己
                self.synonym_to_canonical[canonical] = canonical
                
                # 同义词映射到规范词
                if 'synonyms' in op_def:
                    for synonym in op_def['synonyms']:
                        self.synonym_to_canonical[synonym] = canonical
            
            logger.info(f"Initialized operation mappings with {len(self.synonym_to_canonical)} terms")
            
        except ImportError:
            logger.warning("operation_embedding_index not available, using basic normalization")
            # 基本的备用映射
            self.synonym_to_canonical = {}

    def _normalize_query(self, query: str) -> str:
        """
        规范化查询字符串以提高缓存命中率
        
        Args:
            query: 原始查询字符串
            
        Returns:
            规范化后的查询字符串
        """
        # 转换为小写
        normalized = query.lower()
        
        # 替换同义词为规范形式
        words = normalized.split()
        normalized_words = []
        
        for word in words:
            # 检查是否是已知的操作同义词
            if hasattr(self, 'synonym_to_canonical') and word in self.synonym_to_canonical:
                normalized_words.append(self.synonym_to_canonical[word])
            else:
                normalized_words.append(word)
        
        # 重新组合
        normalized = ' '.join(normalized_words)
        
        # 移除常见的变化模式
        # 例如："for task_type_X" -> "for task_type"
        import re
        # 替换具体的任务类型为通用标记
        normalized = re.sub(r'for \w+_integration', 'for TASK_TYPE', normalized)
        normalized = re.sub(r'for \w+_processing', 'for TASK_TYPE', normalized)
        normalized = re.sub(r'for \w+_validation', 'for TASK_TYPE', normalized)
        normalized = re.sub(r'after \w+_\w+', 'after TOOL_NAME', normalized)
        
        # 移除多余的空格
        normalized = ' '.join(normalized.split())
        
        return normalized


    def _get_search_cache_key(self, query: str, k: int, filter_category: Optional[str], 
                            filter_tools: Optional[List[str]]) -> str:
        """生成搜索缓存键"""
        # 规范化查询
        normalized_query = self._normalize_query(query)
        
        # 构建缓存键
        key_parts = [
            normalized_query,
            str(k),
            filter_category or 'none',
            ','.join(sorted(filter_tools)) if filter_tools else 'none'
        ]
        
        return '|'.join(key_parts)


    def _load_search_cache(self):
        """加载搜索结果缓存"""
        if self.search_cache_file.exists():
            try:
                with open(self.search_cache_file, 'rb') as f:
                    self.search_cache = pickle.load(f)
                logger.info(f"Loaded search cache with {len(self.search_cache)} entries")
            except Exception as e:
                logger.warning(f"Failed to load search cache: {e}")
                self.search_cache = {}
        else:
            self.search_cache = {}


    def _load_search_cache(self):
        """加载搜索结果缓存"""
        if self.search_cache_file.exists():
            try:
                with open(self.search_cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                
                # 兼容性处理：判断加载的是字典还是对象
                if isinstance(cache_data, dict):
                    # 如果是字典，直接使用
                    self.search_cache = cache_data
                    logger.info(f"Loaded search cache with {len(self.search_cache)} entries")
                else:
                    # 如果是其他格式，创建新的字典缓存
                    self.search_cache = {}
                    logger.warning("Incompatible cache format, starting fresh")
                    
            except Exception as e:
                logger.warning(f"Failed to load search cache: {e}")
                self.search_cache = {}
        else:
            self.search_cache = {}

    # 文件：mcp_embedding_manager.py
    # 位置：第850-950行
    # 函数：search（修复版本）

    def search(self, 
            query: str, 
            k: int = 5,
            category_filter: Optional[str] = None,
            return_scores: bool = True,
            similarity_threshold: float = 0.0) -> List[SearchResult]:
        """
        搜索相关工具
        
        Args:
            query: 搜索查询
            k: 返回数量
            category_filter: 类别过滤
            return_scores: 是否返回分数
            similarity_threshold: 相似度阈值
            
        Returns:
            搜索结果列表
        """
        # 检查缓存
        cache_key = f"{query}_{k}_{category_filter}_{similarity_threshold}"
        if hasattr(self.search_cache, 'get'):
            cached = self.search_cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Search cache hit for: {query}")
                return cached
        
        if not self.index or not self.tool_embeddings:
            logger.warning("No index or embeddings available")
            return []
        
        # 确保 tool_names 和 tool_embeddings 同步
        if not hasattr(self, 'tool_names') or len(self.tool_names) == 0:
            logger.warning("tool_names not initialized, rebuilding from embeddings")
            self.tool_names = list(self.tool_embeddings.keys())
        
        # 获取查询的嵌入
        query_embedding = self._get_embedding(query)
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        # 归一化
        if HAS_FAISS:
            faiss.normalize_L2(query_embedding)
        
        # 搜索
        k_search = min(k * 3, len(self.tool_names))  # 搜索更多以便过滤
        distances, indices = self.index.search(query_embedding, k_search)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if dist < similarity_threshold:
                continue
            
            # 边界检查
            if idx < 0 or idx >= len(self.tool_names):
                logger.warning(f"Invalid index {idx} (tool_names length: {len(self.tool_names)})")
                continue
                
            tool_name = self.tool_names[idx]
            
            # 关键修复：检查工具是否在 embeddings 中
            if tool_name not in self.tool_embeddings:
                logger.warning(f"Tool '{tool_name}' at index {idx} not found in tool_embeddings")
                # 尝试从 embeddings 重建 tool_names
                if len(self.tool_names) != len(self.tool_embeddings):
                    logger.info("Detected mismatch, rebuilding tool_names from embeddings")
                    self.tool_names = list(self.tool_embeddings.keys())
                    # 重建 FAISS 索引
                    self._rebuild_faiss_index()
                    # 重新搜索
                    return self.search(query, k, category_filter, return_scores, similarity_threshold)
                continue
                
            tool_emb = self.tool_embeddings[tool_name]
            
            # 类别过滤
            if category_filter and tool_emb.category != category_filter:
                continue
            
            # 分析相关性原因
            try:
                desc_sim = self._calculate_similarity(
                    query_embedding[0], 
                    tool_emb.description_embedding
                )
                param_sim = self._calculate_similarity(
                    query_embedding[0], 
                    tool_emb.parameter_embedding
                )
                func_sim = self._calculate_similarity(
                    query_embedding[0], 
                    tool_emb.functionality_embedding
                )
                
                # 生成原因
                reason_parts = []
                if desc_sim > 0.7:
                    reason_parts.append("description match")
                if param_sim > 0.7:
                    reason_parts.append("parameter match")
                if func_sim > 0.7:
                    reason_parts.append("functionality match")
                
                reason = " + ".join(reason_parts) if reason_parts else "general similarity"
            except Exception as e:
                logger.debug(f"Failed to calculate similarity reasons: {e}")
                reason = "general similarity"
            
            result = SearchResult(
                tool_name=tool_name,
                score=float(dist) if return_scores else 1.0,
                mcp_protocol=tool_emb.mcp_protocol,
                category=tool_emb.category,
                reason=reason
            )
            
            results.append(result)
            
            if len(results) >= k:
                break
        
        # 缓存结果
        if hasattr(self.search_cache, 'put'):
            self.search_cache.put(cache_key, results)
        elif isinstance(self.search_cache, dict):
            self.search_cache[cache_key] = results
        
        return results

    def _rebuild_faiss_index(self):
        """重建 FAISS 索引以确保同步"""
        if not HAS_FAISS or not self.tool_embeddings:
            return
        
        logger.info("Rebuilding FAISS index for synchronization")
        
        # 从 tool_embeddings 重建
        embeddings = []
        tool_names = []
        
        for tool_name, tool_emb in self.tool_embeddings.items():
            embeddings.append(tool_emb.combined_embedding)
            tool_names.append(tool_name)
        
        if embeddings:
            embeddings_matrix = np.vstack(embeddings).astype('float32')
            
            # 获取实际维度
            actual_dimension = embeddings_matrix.shape[1]
            
            # 创建新索引
            self.index = faiss.IndexFlatIP(actual_dimension)
            faiss.normalize_L2(embeddings_matrix)
            self.index.add(embeddings_matrix)
            
            # 更新 tool_names
            self.tool_names = tool_names
            
            logger.info(f"Rebuilt FAISS index with {len(tool_names)} tools")

    def clear_cache(self, keep_embeddings: bool = True):
        """清理缓存"""
        print(f"🗑️ Clearing cache (keep_embeddings={keep_embeddings})...")
        
        # 清理搜索缓存
        self.search_cache = PermanentSmartCache(
            max_size=10000,
            similarity_threshold=0.95
        )
        if self.search_cache_file.exists():
            self.search_cache_file.unlink()
            print("  - Cleared search cache")
        
        # 清理embedding缓存（可选）
        if not keep_embeddings:
            self.embedding_cache = {}
            if self.embedding_cache_file.exists():
                self.embedding_cache_file.unlink()
                print("  - Cleared embedding cache")
        else:
            print(f"  - Kept {len(self.embedding_cache)} embeddings")


    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        embedding_size_mb = 0
        if self.embedding_cache_file.exists():
            embedding_size_mb = self.embedding_cache_file.stat().st_size / (1024 * 1024)
        
        search_size_mb = 0
        if self.search_cache_file.exists():
            search_size_mb = self.search_cache_file.stat().st_size / (1024 * 1024)
        
        # 计算最常访问的查询
        top_queries = []
        if hasattr(self.search_cache, 'access_counts'):
            sorted_queries = sorted(
                self.search_cache.access_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            top_queries = [
                {'query': k.split('|')[0], 'count': v}
                for k, v in sorted_queries
            ]
        
        return {
            'embedding_cache': {
                'entries': len(self.embedding_cache),
                'size_mb': embedding_size_mb,
                'type': 'permanent'
            },
            'search_cache': {
                'entries': len(self.search_cache.cache),
                'max_size': self.search_cache.max_size,
                'size_mb': search_size_mb,
                'type': 'permanent_lfu',
                'top_queries': top_queries
            },
            'total_size_mb': embedding_size_mb + search_size_mb
        }
    
    def _calculate_hit_rate(self, cache_manager: PermanentSmartCache) -> float:
        """计算缓存命中率"""
        total_accesses = sum(cache_manager.access_counts.values())
        if total_accesses == 0:
            return 0.0
        
        # 估算命中率（访问次数>1的条目）
        hits = sum(count - 1 for count in cache_manager.access_counts.values() if count > 1)
        return hits / total_accesses if total_accesses > 0 else 0.0
       
    def get_tool_protocols(self, 
                          tool_names: List[str],
                          include_embeddings: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        批量获取工具协议
        
        Args:
            tool_names: 工具名称列表
            include_embeddings: 是否包含嵌入向量
            
        Returns:
            工具协议字典
        """
        protocols = {}
        for tool_name in tool_names:
            if tool_name in self.tool_embeddings:
                tool_emb = self.tool_embeddings[tool_name]
                protocol_data = {
                    'mcp_protocol': tool_emb.mcp_protocol,
                    'category': tool_emb.category,
                    'description': tool_emb.description
                }
                
                if include_embeddings:
                    protocol_data['embedding'] = tool_emb.combined_embedding.tolist()
                
                protocols[tool_name] = protocol_data
        
        return protocols
    
    def find_similar_tools(self, 
                        tool_name: str, 
                        k: int = 5,
                        same_category_only: bool = False) -> List[Tuple[str, float]]:
        """
        查找相似工具
        
        Args:
            tool_name: 基准工具名称
            k: 返回数量
            same_category_only: 是否只返回同类别工具
            
        Returns:
            相似工具列表
        """
        # 使用线程锁保护整个搜索过程
        with MCPEmbeddingManager._lock:
            if tool_name not in self.tool_embeddings:
                logger.warning(f"Tool {tool_name} not found")
                return []
            
            tool_emb = self.tool_embeddings[tool_name]
            query_embedding = tool_emb.combined_embedding.reshape(1, -1).astype('float32')
            
            if not self.index or not HAS_FAISS:
                return []
            
            # 在锁保护下创建本地副本，避免搜索过程中数据变化
            local_tool_names = list(self.tool_names)
            local_tool_embeddings_keys = set(self.tool_embeddings.keys())
            
            # 搜索相似工具
            distances, indices = self.index.search(query_embedding, k + 1)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                # 添加边界检查
                if idx < 0 or idx >= len(local_tool_names):
                    print(f"[ERROR] Invalid index {idx} for tool_names length {len(local_tool_names)}")
                    continue
                    
                similar_tool = local_tool_names[idx]
                
                # 跳过自身
                if similar_tool == tool_name:
                    continue
                
                # 关键修复：检查工具是否在 embeddings 中
                if similar_tool not in local_tool_embeddings_keys:
                    print(f"[ERROR] Tool '{similar_tool}' at index {idx} not found in tool_embeddings")
                    print(f"[DEBUG] tool_names length: {len(local_tool_names)}, tool_embeddings keys: {len(local_tool_embeddings_keys)}")
                    print(f"[DEBUG] Thread ID: {threading.current_thread().ident}")
                    # 直接跳过这个工具，继续处理下一个
                    continue
                
                # 再次验证（双重检查）
                if similar_tool not in self.tool_embeddings:
                    print(f"[ERROR] Tool '{similar_tool}' disappeared during search")
                    continue
                    
                similar_emb = self.tool_embeddings[similar_tool]
                if same_category_only and similar_emb.category != tool_emb.category:
                    continue
                    
                results.append((similar_tool, float(dist)))
                
                if len(results) >= k:
                    break
            
            return results
    
    def _save_search_cache(self):
        """保存搜索缓存到文件"""
        # 直接调用 PermanentSmartCache 的 save_to_file 方法
        # 使用已定义的 search_cache_file 路径
        logger.debug(f" Saving search cache to {self.search_cache_file}")
        
        # 确保缓存目录存在
        self.search_cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 调用 PermanentSmartCache 的 save_to_file 方法
        self.search_cache.save_to_file(str(self.search_cache_file))
        
        # 记录保存的条目数量
        cache_entries = len(self.search_cache.cache)
        print(f"[INFO] Saved {cache_entries} search cache entries")
        logger.info(f"Search cache saved with {cache_entries} entries")

    def save_index(self, path: Union[str, Path]):
        """保存索引到文件"""
        # 保存搜索缓存
        self._save_search_cache()
        
        save_data = {
            'config': asdict(self.config),
            'tool_names': self.tool_names,
            'tool_embeddings': {
                name: emb.to_dict() 
                for name, emb in self.tool_embeddings.items()
            }
        }
        
        if HAS_FAISS and self.index:
            save_data['index'] = faiss.serialize_index(self.index)
        
        with open(path, 'wb') as f:
            pickle.dump(save_data, f)
        
        logger.info(f"Index saved to {path}")
    


    def load_index(self, index_file: str = None) -> None:
        """从文件加载索引，增强错误处理"""
        if index_file is None:
            index_file = Path(self.config.cache_dir) / "tool_index.pkl"
        else:
            index_file = Path(index_file)
        
        if not index_file.exists():
            logger.warning(f"Index file not found: {index_file}")
            return
        
        # 检查文件大小
        file_size = index_file.stat().st_size
        if file_size == 0:
            logger.error(f"Index file {index_file} is empty, cannot load")
            index_file.unlink()
            raise ValueError(f"Index file is empty: {index_file}")
        
        logger.info(f"Loading index from {index_file} (size: {file_size} bytes)")
        
        try:
            with open(index_file, 'rb') as f:
                data = pickle.load(f)
            
            # 验证数据结构
            if not isinstance(data, dict):
                raise ValueError(f"Invalid index format (expected dict, got {type(data)})")
            
            # 修复：检查新旧两种可能的键名
            if 'tool_embeddings' in data:
                # 新格式：直接使用 tool_embeddings
                embeddings_data = data['tool_embeddings']
            elif 'embeddings' in data:
                # 旧格式：使用 embeddings
                embeddings_data = data['embeddings']
            else:
                # 都没有，报错
                available_keys = list(data.keys())
                raise ValueError(f"Neither 'tool_embeddings' nor 'embeddings' found in index. Available keys: {available_keys}")
            
            # 检查其他必需的键
            required_keys = ['tool_names', 'index', 'config']
            missing_keys = set(required_keys) - set(data.keys())
            if missing_keys:
                raise ValueError(f"Missing required keys in index: {missing_keys}")
            
            # 恢复工具名称
            self.tool_names = data['tool_names']
            
            # 恢复嵌入数据
            self.tool_embeddings = {}
            for name, emb_data in embeddings_data.items():
                if isinstance(emb_data, dict):
                    # 从字典恢复 ToolEmbedding 对象
                    self.tool_embeddings[name] = ToolEmbedding.from_dict(emb_data)
                else:
                    # 兼容旧格式
                    logger.warning(f"Old format detected for {name}, skipping")
            
            # 恢复 FAISS 索引
            if 'index' in data and data['index'] is not None:
                self.index = faiss.deserialize_index(data['index'])
                logger.info(f"FAISS index loaded")
            else:
                self.index = None
                logger.warning("No FAISS index found in saved data")
            
            # 恢复配置
            if 'config' in data:
                saved_config = data['config']
                # 更新配置中的维度信息
                if 'dimension' in saved_config:
                    self.config.dimension = saved_config['dimension']
                    logger.info(f"Updated dimension to {self.config.dimension}")
            
            logger.info(f"Index loaded successfully: {len(self.tool_embeddings)} tools")
            
        except EOFError:
            logger.error(f"Index file {index_file} is corrupted (EOFError)")
            # 备份损坏的文件
            backup_path = index_file.with_suffix('.pkl.corrupted')
            index_file.rename(backup_path)
            logger.info(f"Corrupted index backed up to {backup_path}")
            raise ValueError(f"Index file is corrupted: {index_file}")
            
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            raise
    def export_stats(self) -> Dict[str, Any]:
        """导出统计信息"""
        if not self.tool_embeddings:
            return {'status': 'empty'}
        
        categories = {}
        for tool_emb in self.tool_embeddings.values():
            cat = tool_emb.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1
        
        return {
            'total_tools': len(self.tool_embeddings),
            'categories': categories,
            'index_type': 'faiss' if self.index else 'none',
            'embedding_model': self.config.model,
            'embedding_dimension': self.config.dimension,
            'cache_size': len(self.embedding_cache)
        }


# ===========================
# Convenience Functions
# ===========================

def create_manager(api_key: Optional[str] = None) -> MCPEmbeddingManager:
    """创建嵌入管理器的便捷函数"""
    return MCPEmbeddingManager(api_key=api_key)


def quick_search(query: str, 
                tool_registry_path: str = "mcp_generated_library/tool_registry_consolidated.json",
                k: int = 5) -> List[Dict[str, Any]]:
    """快速搜索工具的便捷函数"""
    manager = create_manager()
    
    # 构建或加载索引
    index_path = Path(".mcp_embedding_cache/tool_index.pkl")
    if index_path.exists():
        manager.load_index(index_path)
    else:
        manager.build_index(tool_registry_path)
    
    # 搜索
    results = manager.search(query, k=k)
    
    return [
        {
            'tool_name': r.tool_name,
            'score': r.score,
            'category': r.category,
            'description': r.mcp_protocol.get('description', '')
        }
        for r in results
    ]


# ===========================
# Command Line Interface
# ===========================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="MCP Tool Embedding Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 构建索引
  python mcp_embedding_manager.py build --registry tool_registry.json
  
  # 搜索工具
  python mcp_embedding_manager.py search "validate json data" -k 5
  
  # 查找相似工具
  python mcp_embedding_manager.py similar file_operations_reader -k 3
  
  # 导出统计信息
  python mcp_embedding_manager.py stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build embedding index')
    build_parser.add_argument('--registry', '-r', required=True, help='Tool registry JSON file')
    build_parser.add_argument('--force', '-f', action='store_true', help='Force rebuild')
    build_parser.add_argument('--api-key', help='OpenAI API key')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for tools')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-k', type=int, default=5, help='Number of results')
    search_parser.add_argument('--category', help='Filter by category')
    search_parser.add_argument('--api-key', help='OpenAI API key')
    
    # Similar command
    similar_parser = subparsers.add_parser('similar', help='Find similar tools')
    similar_parser.add_argument('tool', help='Tool name')
    similar_parser.add_argument('-k', type=int, default=5, help='Number of results')
    similar_parser.add_argument('--same-category', action='store_true', help='Same category only')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export tool protocols')
    export_parser.add_argument('tools', nargs='+', help='Tool names to export')
    export_parser.add_argument('--output', '-o', help='Output file')
    export_parser.add_argument('--embeddings', action='store_true', help='Include embeddings')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 设置API密钥
    api_key = getattr(args, 'api_key', None) or os.getenv('OPENAI_API_KEY')
    
    # 创建管理器
    manager = MCPEmbeddingManager(api_key=api_key)
    
    # 执行命令
    if args.command == 'build':
        stats = manager.build_index(args.registry, force_rebuild=args.force)
        print(json.dumps(stats, indent=2))
        
    elif args.command == 'search':
        # 加载索引
        index_path = Path(".mcp_embedding_cache/tool_index.pkl")
        if not index_path.exists():
            print("Error: Index not found. Run 'build' first.")
            return
        
        manager.load_index(index_path)
        
        # 搜索
        results = manager.search(
            args.query, 
            k=args.k, 
            filter_category=args.category
        )
        
        # 显示结果
        print(f"\nSearch results for: '{args.query}'\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.tool_name} (score: {result.score:.3f})")
            print(f"   Category: {result.category}")
            print(f"   Description: {result.mcp_protocol.get('description', 'N/A')}")
            print()
    
    elif args.command == 'similar':
        # 加载索引
        index_path = Path(".mcp_embedding_cache/tool_index.pkl")
        if not index_path.exists():
            print("Error: Index not found. Run 'build' first.")
            return
        
        manager.load_index(index_path)
        
        # 查找相似工具
        results = manager.find_similar_tools(
            args.tool,
            k=args.k,
            same_category_only=args.same_category
        )
        
        if not results:
            print(f"Tool '{args.tool}' not found.")
            return
        
        print(f"\nTools similar to: '{args.tool}'\n")
        for i, (tool_name, score) in enumerate(results, 1):
            tool_emb = manager.tool_embeddings[tool_name]
            print(f"{i}. {tool_name} (similarity: {score:.3f})")
            print(f"   Category: {tool_emb.category}")
            print(f"   Description: {tool_emb.description}")
            print()
    
    elif args.command == 'stats':
        # 加载索引
        index_path = Path(".mcp_embedding_cache/tool_index.pkl")
        if index_path.exists():
            manager.load_index(index_path)
        
        stats = manager.export_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.command == 'export':
        # 加载索引
        index_path = Path(".mcp_embedding_cache/tool_index.pkl")
        if not index_path.exists():
            print("Error: Index not found. Run 'build' first.")
            return
        
        manager.load_index(index_path)
        
        # 获取协议
        protocols = manager.get_tool_protocols(
            args.tools,
            include_embeddings=args.embeddings
        )
        
        # 输出
        output_data = json.dumps(protocols, indent=2)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_data)
            print(f"Exported to {args.output}")
        else:
            print(output_data)

_global_embedding_manager = None

def get_embedding_manager(config: Optional[EmbeddingConfig] = None) -> MCPEmbeddingManager:
    """获取MCPEmbeddingManager的单例实例
    
    Args:
        config: 可选的配置对象，仅在首次创建时使用
        
    Returns:
        MCPEmbeddingManager的全局单例实例
    """
    global _global_embedding_manager
    
    if _global_embedding_manager is None:
        print("[MCPEmbeddingManager] Creating new singleton instance")
        _global_embedding_manager = MCPEmbeddingManager(config=config)
        print(f"[MCPEmbeddingManager] Singleton created with {len(_global_embedding_manager.tool_embeddings)} cached embeddings")
    else:
        if config is not None:
            print("[MCPEmbeddingManager] Warning: Config ignored, using existing singleton instance")
        print(f"[MCPEmbeddingManager] Reusing existing singleton instance (id: {id(_global_embedding_manager)})")
        print(f"[MCPEmbeddingManager] Current cache size: {len(_global_embedding_manager.tool_embeddings)} embeddings")
    
    return _global_embedding_manager

def reset_embedding_manager():
    """重置单例实例（用于测试）"""
    global _global_embedding_manager
    print("[MCPEmbeddingManager] Resetting singleton instance")
    _global_embedding_manager = None

def get_embedding_manager_info() -> dict:
    """获取当前embedding管理器信息（调试用）"""
    global _global_embedding_manager
    
    if _global_embedding_manager is None:
        return {"status": "not_initialized"}
    
    return {
        "status": "initialized",
        "instance_id": id(_global_embedding_manager),
        "cached_embeddings": len(_global_embedding_manager.tool_embeddings),
        "index_loaded": _global_embedding_manager.index is not None,
        "model": _global_embedding_manager.config.model,
        "dimension": _global_embedding_manager.config.dimension
    }

if __name__ == "__main__":
    main()
