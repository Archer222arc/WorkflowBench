#!/usr/bin/env python3
"""
Operation Embedding Index
========================
基于嵌入的语义操作索引系统，用于理解操作的语义含义，
避免硬编码的关键词匹配。
"""

import os
import json
import pickle
import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Set, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from collections import defaultdict

import hashlib

# 尝试导入可选依赖
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    print("[WARNING] FAISS not available, semantic search will use fallback")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("[WARNING] OpenAI not available, using local embeddings")

logger = logging.getLogger(__name__)


@dataclass
class OperationEmbedding:
    """操作的嵌入表示"""
    operation_name: str
    category: str
    description: str
    synonyms: List[str]
    embedding: np.ndarray
    related_tools: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'operation_name': self.operation_name,
            'category': self.category,
            'description': self.description,
            'synonyms': self.synonyms,
            'embedding': self.embedding.tolist(),
            'related_tools': self.related_tools or []
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationEmbedding':
        """从字典创建"""
        data['embedding'] = np.array(data['embedding'])
        return cls(**data)


class OperationEmbeddingIndex:
    """操作的语义索引管理器"""
    def __init__(self, embedding_dim: int = 1536, use_cache: bool = True):
        """
        初始化操作嵌入索引
        
        Args:
            embedding_dim: 嵌入维度（默认值，会被实际维度覆盖）
            use_cache: 是否使用缓存
        """
        self.embedding_dim = embedding_dim  # 初始值，将被实际维度覆盖
        self.use_cache = use_cache
        self.cache_dir = Path(".mcp_operation_cache")
        
        # 使用统一的 API 客户端管理器
        from api_client_manager import get_api_client, get_embedding_model, get_model_name
        
        print("[OperationEmbeddingIndex] Initializing with unified API client manager")
        
        # OpenAI client
        self.openai_client = None
        self.llm_model_name = None
        if HAS_OPENAI:
            self.openai_client = get_api_client()
            self.llm_model_name = get_model_name()
            print(f"[OperationEmbeddingIndex] OpenAI client initialized with model: {self.llm_model_name}")
            
            # 获取嵌入模型信息
            embedding_model = get_embedding_model()
            print(f"[OperationEmbeddingIndex] Using embedding model: {embedding_model}")
            
            # 动态检测实际的嵌入维度
            print(f"[OperationEmbeddingIndex] Detecting actual embedding dimension...")
            test_response = self.openai_client.embeddings.create(
                model=embedding_model,
                input="test"
            )
            actual_dim = len(test_response.data[0].embedding)
            self.embedding_dim = actual_dim
            print(f"[OperationEmbeddingIndex] Detected embedding dimension: {self.embedding_dim}")
            
        else:
            print("[OperationEmbeddingIndex] OpenAI not available, using local embeddings")
            # 保持提供的维度作为默认值
        
        # 初始化持久化缓存（在这里初始化，避免每次调用_create_embedding时重复加载）
        self.embedding_cache = self._load_embedding_cache()
        print(f"[OperationEmbeddingIndex] Initialized with {len(self.embedding_cache)} cached embeddings")
        
        # 操作定义 - 先尝试加载缓存的LLM增强版本，否则生成新的
        self.operation_definitions = self._load_or_generate_operation_definitions()
        
        # 存储
        self.operation_embeddings: Dict[str, OperationEmbedding] = {}
        self.index = None
        self.operation_names: List[str] = []
        
        # 初始化
        self._ensure_cache_dir()
        self._initialize_index()



    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        if self.use_cache:
            self.cache_dir.mkdir(exist_ok=True)
    
    def _get_cache_path(self) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / "operation_index.pkl"


    def _initialize_index(self):
        """初始化索引"""
        cache_path = self._get_cache_path()
        
        if self.use_cache and cache_path.exists():
            print(f"[INFO] Found cached operation index at {cache_path}")
            try:
                self.load_index(cache_path)
                print("[INFO] Successfully loaded cached index")
                return
            except Exception as e:
                print(f"[WARNING] Failed to load cached index: {e}")
                print("[INFO] Will rebuild index from scratch")
                
                # 删除损坏或不兼容的缓存文件
                if cache_path.exists():
                    cache_path.unlink()
                    print(f"[INFO] Removed incompatible cache file: {cache_path}")
                
                # 清空任何部分加载的数据
                self.operation_embeddings = {}
                self.operation_names = []
                self.index = None
        
        # 构建新索引
        print("[INFO] Building new operation index...")
        self.build_index()

    def _get_base_operation_definitions(self) -> Dict[str, Dict[str, Any]]:
        """获取基础操作定义（作为 fallback）"""
        return {
            'read': {
                'category': 'input',
                'description': 'Read or load data from a source',
                'synonyms': ['load', 'fetch', 'import', 'retrieve', 'get', 'acquire']
            },
            'validate': {
                'category': 'validation', 
                'description': 'Validate or verify data correctness',
                'synonyms': ['verify', 'check', 'ensure', 'confirm', 'test', 'assess']
            },
            'transform': {
                'category': 'transformation',
                'description': 'Transform or convert data format',
                'synonyms': ['convert', 'parse', 'process', 'modify', 'adapt', 'reshape']
            },
            'aggregate': {
                'category': 'aggregation',
                'description': 'Aggregate or combine multiple data items',
                'synonyms': ['combine', 'merge', 'collect', 'group', 'consolidate', 'unify']
            },
            'write': {
                'category': 'output',
                'description': 'Write or save data to a destination',
                'synonyms': ['save', 'export', 'store', 'persist', 'output', 'dump']
            },
            'calculate': {
                'category': 'computation',
                'description': 'Perform calculations or computations',
                'synonyms': ['compute', 'analyze', 'predict', 'estimate', 'derive', 'measure']
            },
            'connect': {
                'category': 'integration',
                'description': 'Connect to external services or APIs',
                'synonyms': ['authenticate', 'integrate', 'link', 'interface', 'communicate']
            },
            'log': {
                'category': 'utility',
                'description': 'Log information or track activities',
                'synonyms': ['track', 'record', 'monitor', 'audit', 'trace', 'report']
            }
        }

    def _load_or_generate_operation_definitions(self) -> Dict[str, Dict[str, Any]]:
        """加载或生成操作定义（使用 LLM 增强）"""
        # 尝试加载缓存的 LLM 增强定义
        llm_definitions_cache = self.cache_dir / "llm_operation_definitions.json"
        
        if self.use_cache and llm_definitions_cache.exists():
            try:
                with open(llm_definitions_cache, 'r') as f:
                    definitions = json.load(f)
                print(f"[INFO] Loaded {len(definitions)} LLM-enhanced operation definitions from cache")
                return definitions
            except Exception as e:
                print(f"[WARNING] Failed to load LLM definitions cache: {e}")
        
        # 获取基础定义
        base_definitions = self._get_base_operation_definitions()
        
        # 如果没有 LLM 客户端，返回基础定义
        if not self.openai_client:
            print("[INFO] No LLM client available, using base operation definitions")
            return base_definitions
        
        # 使用 LLM 增强定义
        print("[INFO] Generating LLM-enhanced operation definitions...")
        enhanced_definitions = self._enhance_definitions_with_llm(base_definitions)
        
        # 缓存增强后的定义
        if self.use_cache:
            try:
                with open(llm_definitions_cache, 'w') as f:
                    json.dump(enhanced_definitions, f, indent=2)
                print("[INFO] Cached LLM-enhanced operation definitions")
            except Exception as e:
                print(f"[WARNING] Failed to cache LLM definitions: {e}")
        
        return enhanced_definitions
    
    def _enhance_definitions_with_llm(self, base_definitions: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """使用 LLM 增强操作定义"""
        enhanced_definitions = base_definitions.copy()
        
        # 构建 prompt 来生成更多操作类型和同义词
        prompt = """You are helping to build a semantic index for tool operations. 
        
Given these base operation categories and their descriptions:

"""
        for op_name, op_def in base_definitions.items():
            prompt += f"- {op_name} ({op_def['category']}): {op_def['description']}\n"
            prompt += f"  Synonyms: {', '.join(op_def['synonyms'])}\n\n"
        
        prompt += """
Please:
1. Add 5-10 more relevant synonyms for each existing operation
2. Suggest 5-10 additional operation types that are commonly used in data processing, file operations, and API integrations
3. Format the response as JSON with this structure:
{
  "enhanced_operations": {
    "operation_name": {
      "category": "category_name",
      "description": "detailed description",
      "synonyms": ["list", "of", "synonyms"],
      "related_operations": ["list", "of", "related", "operations"]
    }
  },
  "new_operations": {
    "operation_name": {
      "category": "category_name", 
      "description": "detailed description",
      "synonyms": ["list", "of", "synonyms"]
    }
  }
}

Focus on operations commonly used in data pipelines, file processing, API interactions, and workflow automation."""

        response = self.openai_client.chat.completions.create(
            model=self.llm_model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates structured data for semantic search systems."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # 增强现有操作
        if "enhanced_operations" in result:
            for op_name, enhancements in result["enhanced_operations"].items():
                if op_name in enhanced_definitions:
                    # 添加新的同义词
                    existing_synonyms = set(enhanced_definitions[op_name]["synonyms"])
                    new_synonyms = set(enhancements.get("synonyms", []))
                    enhanced_definitions[op_name]["synonyms"] = list(existing_synonyms | new_synonyms)
                    
                    # 添加相关操作信息
                    if "related_operations" in enhancements:
                        enhanced_definitions[op_name]["related_operations"] = enhancements["related_operations"]
                    
                    # 更新描述（如果 LLM 提供了更详细的）
                    if len(enhancements.get("description", "")) > len(enhanced_definitions[op_name]["description"]):
                        enhanced_definitions[op_name]["description"] = enhancements["description"]
        
        # 添加新操作
        if "new_operations" in result:
            for op_name, op_def in result["new_operations"].items():
                if op_name not in enhanced_definitions:
                    enhanced_definitions[op_name] = {
                        "category": op_def.get("category", "general"),
                        "description": op_def.get("description", f"Operation: {op_name}"),
                        "synonyms": op_def.get("synonyms", [])
                    }
        
        print(f"[INFO] LLM enhanced definitions: {len(base_definitions)} -> {len(enhanced_definitions)} operations")

        return enhanced_definitions

    def _load_operation_definitions(self) -> Dict[str, Dict[str, Any]]:
        """加载操作定义（保持向后兼容）"""
        # 这个方法现在只是调用新的方法
        return self.operation_definitions

# 文件：operation_embedding_index.py
# 位置：第380-420行
    # 函数：_create_embedding

    def _create_embedding(self, text: str) -> np.ndarray:
        """创建文本的嵌入，使用本地磁盘缓存避免重复调用"""
        # 创建文本哈希用于缓存键
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        
        # 检查缓存
        if text_hash in self.embedding_cache:
            cached_embedding = self.embedding_cache[text_hash]
            # 验证缓存的嵌入维度
            if cached_embedding.shape[0] != self.embedding_dim:
                print(f"[WARNING] Cached embedding dimension mismatch for text hash {text_hash}")
                print(f"[WARNING] Expected: {self.embedding_dim}, Got: {cached_embedding.shape[0]}")
                print(f"[WARNING] Will regenerate embedding")
            else:
                return cached_embedding
        
        # 生成嵌入
        from api_client_manager import get_embedding_model
        embedding_model = get_embedding_model()
        
        response = self.openai_client.embeddings.create(
            model=embedding_model,
            input=text
        )
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        
        # 验证生成的嵌入维度
        if embedding.shape[0] != self.embedding_dim:
            print(f"[ERROR] Generated embedding dimension mismatch!")
            print(f"[ERROR] Expected: {self.embedding_dim}, Got: {embedding.shape[0]}")
            print(f"[ERROR] Model: {embedding_model}")
            # 更新维度以匹配实际情况
            print(f"[INFO] Updating embedding dimension to {embedding.shape[0]}")
            self.embedding_dim = embedding.shape[0]
        
        # 保存到缓存
        self.embedding_cache[text_hash] = embedding
        
        # 定期保存缓存到磁盘
        if len(self.embedding_cache) % 50 == 0:
            self._save_embedding_cache()
        
        return embedding


    def _load_embedding_cache(self) -> Dict[str, np.ndarray]:
        """加载持久化的嵌入缓存"""
        cache_file = self.cache_dir / "embedding_cache.pkl"
        with open(cache_file, 'rb') as f:
            cache = pickle.load(f)
        print(f"[INFO] Loaded {len(cache)} embeddings from persistent cache")
        return cache


    def _save_embedding_cache(self):
        """保存嵌入缓存到本地磁盘"""
        if not hasattr(self, 'embedding_cache'):
            return
        
        cache_file = self.cache_dir / "embedding_cache.pkl"
        
        # 确保缓存目录存在
        self.cache_dir.mkdir(exist_ok=True)
        
        with open(cache_file, 'wb') as f:
            pickle.dump(self.embedding_cache, f)
        
        logger.debug(f" Saved {len(self.embedding_cache)} embeddings to cache file")

    def _get_embedding_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        if not hasattr(self, 'embedding_cache'):
            return {'status': 'not_initialized'}
        
        cache_file = self.cache_dir / "embedding_cache.pkl"
        
        stats = {
            'cache_entries': len(self.embedding_cache),
            'cache_file_exists': cache_file.exists(),
            'cache_file_size_mb': 0.0
        }
        
        if cache_file.exists():
            stats['cache_file_size_mb'] = cache_file.stat().st_size / (1024 * 1024)
        
        return stats
    

    def build_index(self):
        """构建操作的语义索引"""
        logger.debug(f" Building index with operation_definitions: {list(self.operation_definitions.keys())}")
        
        if not self.operation_definitions:
            print("[ERROR] operation_definitions is empty! Cannot build index.")
            print("[ERROR] This will cause operations to always be empty and fallback to keyword matching")
            return
        
        embeddings = []
        successful_operations = 0
        failed_operations = 0
        
        for op_name, op_def in self.operation_definitions.items():
            logger.debug(f" Processing operation definition: {op_name}")
            
            # 验证操作定义的完整性
            if not isinstance(op_def, dict):
                print(f"[ERROR] Invalid operation definition for '{op_name}': {op_def}")
                failed_operations += 1
                continue
                
            if 'description' not in op_def or 'category' not in op_def or 'synonyms' not in op_def:
                print(f"[ERROR] Incomplete operation definition for '{op_name}': missing required fields")
                print(f"[ERROR] Required fields: description, category, synonyms")
                print(f"[ERROR] Available fields: {list(op_def.keys())}")
                failed_operations += 1
                continue
            
            # 创建操作的完整描述
            full_text = f"{op_name}: {op_def['description']}. "
            full_text += f"Synonyms: {', '.join(op_def['synonyms'])}"
            
            logger.debug(f" Creating embedding for operation '{op_name}' with text: {full_text[:100]}...")
            
            # 创建嵌入
            embedding = self._create_embedding(full_text)
            
            # 创建OperationEmbedding对象
            op_embedding = OperationEmbedding(
                operation_name=op_name,
                category=op_def['category'],
                description=op_def['description'],
                synonyms=op_def['synonyms'],
                embedding=embedding
            )
            
            self.operation_embeddings[op_name] = op_embedding
            embeddings.append(embedding)
            self.operation_names.append(op_name)
            successful_operations += 1
            
            logger.debug(f" Successfully processed operation '{op_name}' (category: {op_def['category']})")
        
        logger.debug(f" Index building completed: {successful_operations} successful, {failed_operations} failed")
        
        if successful_operations == 0:
            print("[ERROR] No operations were successfully processed! This will cause all category lookups to fail!")
            return
        
        # 构建FAISS索引
        if HAS_FAISS and embeddings:
            embeddings_matrix = np.vstack(embeddings).astype('float32')
            
            # 使用内积相似度
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            
            # 归一化以使用余弦相似度
            faiss.normalize_L2(embeddings_matrix)
            self.index.add(embeddings_matrix)
            
            print(f"[SUCCESS] Built FAISS index with {len(embeddings)} operations")
        else:
            print("[WARNING] FAISS not available, using direct similarity")
            self.index = None
        
        # 保存缓存
        if self.use_cache:
            self.save_index(self._get_cache_path())
        
        # 保存缓存
        if self.use_cache:
            self.save_index(self._get_cache_path())
    
# 文件：operation_embedding_index.py
# 位置：第470-510行
# 函数：search_operation

    def search_operation(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        """
        搜索语义相似的操作
        
        Args:
            query: 查询文本（可以是操作描述或名称）
            k: 返回结果数量
            
        Returns:
            [(operation_name, similarity_score)]列表
        """
        # 创建查询嵌入
        query_embedding = self._create_embedding(query)
        
        # 添加维度验证
        if query_embedding.shape[0] != self.embedding_dim:
            print(f"[ERROR] Query embedding dimension mismatch!")
            print(f"[ERROR] Expected: {self.embedding_dim}, Got: {query_embedding.shape[0]}")
            raise ValueError(f"Query embedding dimension ({query_embedding.shape[0]}) does not match expected dimension ({self.embedding_dim})")
        
        if self.index and HAS_FAISS:
            # 验证索引维度
            if hasattr(self.index, 'd') and self.index.d != self.embedding_dim:
                print(f"[ERROR] FAISS index dimension mismatch!")
                print(f"[ERROR] Index dimension: {self.index.d}")
                print(f"[ERROR] Expected dimension: {self.embedding_dim}")
                print(f"[ERROR] The cached index is incompatible with current embedding model")
                print(f"[ERROR] Please delete the cache at {self._get_cache_path()} and restart")
                raise ValueError(f"FAISS index dimension ({self.index.d}) does not match embedding dimension ({self.embedding_dim})")
            
            # 使用FAISS搜索
            query_embedding = query_embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(query_embedding)
            
            distances, indices = self.index.search(query_embedding, k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(self.operation_names):
                    op_name = self.operation_names[idx]
                    # 将距离转换为相似度分数（0-1）
                    similarity = float(dist)  # 内积相似度已经在0-1之间
                    results.append((op_name, similarity))
            
            return results
        else:
            # Fallback：使用直接相似度计算
            similarities = []
            
            for op_name, op_emb in self.operation_embeddings.items():
                # 计算余弦相似度
                similarity = np.dot(query_embedding, op_emb.embedding)
                similarity = similarity / (np.linalg.norm(query_embedding) * np.linalg.norm(op_emb.embedding))
                similarities.append((op_name, float(similarity)))
            
            # 排序并返回top-k
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:k]

    def get_category_for_operations(self, operations: List[str]) -> str:
        """
        基于语义理解获取操作列表的类别
        
        Args:
            operations: 操作名称列表
            
        Returns:
            最可能的类别
        """
        logger.debug(f" get_category_for_operations called with operations: {operations}")
        
        if not operations:
            logger.debug(f" Operations list is empty, returning 'general'")
            return 'general'
        
        # 检查是否有有效的operation_embeddings
        if not self.operation_embeddings:
            logger.debug(f" No operation embeddings available, building index...")
            self.build_index()
            
            if not self.operation_embeddings:
                print("[ERROR] Failed to build operation embeddings, operations definitions may be empty")
                print(f"[ERROR] operation_definitions keys: {list(self.operation_definitions.keys())}")
                return 'general'
        
        # 统计每个类别的得分
        category_scores = defaultdict(float)
        total_operations_processed = 0
        
        for operation in operations:
            logger.debug(f" Processing operation: '{operation}'")
            
            # 搜索最相似的标准操作
            results = self.search_operation(operation, k=3)
            logger.debug(f" Search results for '{operation}': {results}")
            
            operation_matched = False
            for op_name, score in results:
                if op_name in self.operation_embeddings:
                    category = self.operation_embeddings[op_name].category
                    category_scores[category] += score
                    operation_matched = True
                    logger.debug(f" Matched '{operation}' -> '{op_name}' (category: {category}, score: {score:.3f})")
            
            if operation_matched:
                total_operations_processed += 1
            else:
                logger.debug(f" No matches found for operation: '{operation}'")
        
        logger.debug(f" Category scores: {dict(category_scores)}")
        logger.debug(f" Total operations processed: {total_operations_processed}/{len(operations)}")
        
        # 返回得分最高的类别
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])
            logger.debug(f" Best category: {best_category[0]} (score: {best_category[1]:.3f})")
            return best_category[0]
        
        logger.debug(f" No category scores, falling back to 'general'")
        return 'general'
    
    def find_similar_operations(self, operation: str, k: int = 5) -> List[str]:
        """
        查找相似的操作（包括同义词）
        
        Args:
            operation: 操作名称
            k: 返回数量
            
        Returns:
            相似操作列表
        """
        results = self.search_operation(operation, k=k)
        similar_ops = []
        
        for op_name, score in results:
            if score > 0.7:  # 相似度阈值
                similar_ops.append(op_name)
                # 添加同义词
                if op_name in self.operation_embeddings:
                    synonyms = self.operation_embeddings[op_name].synonyms
                    similar_ops.extend(synonyms[:2])  # 最多添加2个同义词
        
        return list(set(similar_ops))[:k]
    
    def is_operation_in_category(self, operation: str, category: str, threshold: float = 0.7) -> bool:
        """
        判断操作是否属于某个类别
        
        Args:
            operation: 操作名称或描述
            category: 目标类别
            threshold: 相似度阈值
            
        Returns:
            是否属于该类别
        """
        results = self.search_operation(operation, k=3)
        
        for op_name, score in results:
            if score >= threshold and op_name in self.operation_embeddings:
                if self.operation_embeddings[op_name].category == category:
                    return True
        
        return False
    
    def save_index(self, path: Path):
        """保存索引到文件"""
        save_data = {
            'operation_embeddings': {
                name: emb.to_dict()
                for name, emb in self.operation_embeddings.items()
            },
            'operation_names': self.operation_names,
            'embedding_dim': self.embedding_dim
        }
        
        save_data['index'] = faiss.serialize_index(self.index)
        
        with open(path, 'wb') as f:
            pickle.dump(save_data, f)
        
        print(f"[INFO] Operation index saved to {path}")


    def load_index(self, path: Path):
        """从文件加载索引"""
        print(f"[INFO] Loading operation index from {path}")
        
        with open(path, 'rb') as f:
            save_data = pickle.load(f)
        
        # 恢复嵌入
        self.operation_embeddings = {
            name: OperationEmbedding.from_dict(emb_dict)
            for name, emb_dict in save_data['operation_embeddings'].items()
        }
        
        self.operation_names = save_data['operation_names']
        saved_embedding_dim = save_data['embedding_dim']
        
        # 验证维度一致性
        if saved_embedding_dim != self.embedding_dim:
            print(f"[ERROR] Dimension mismatch in cached index!")
            print(f"[ERROR] Cached index dimension: {saved_embedding_dim}")
            print(f"[ERROR] Current embedding dimension: {self.embedding_dim}")
            print(f"[ERROR] This typically happens when the embedding model has changed")
            print(f"[ERROR] For example: text-embedding-ada-002 (1536) vs text-embedding-3-large (3072)")
            
            # 清空已加载的数据
            self.operation_embeddings = {}
            self.operation_names = []
            self.index = None
            
            # 直接报错，不使用 fallback
            raise ValueError(f"Cached index dimension ({saved_embedding_dim}) does not match current embedding dimension ({self.embedding_dim}). Please delete {path} and restart.")
        
        # 恢复FAISS索引
        if HAS_FAISS and 'index' in save_data:
            self.index = faiss.deserialize_index(save_data['index'])
            
            # 验证索引维度
            if hasattr(self.index, 'd'):
                if self.index.d != self.embedding_dim:
                    print(f"[ERROR] FAISS index dimension mismatch!")
                    print(f"[ERROR] Index dimension: {self.index.d}")
                    print(f"[ERROR] Expected dimension: {self.embedding_dim}")
                    
                    self.operation_embeddings = {}
                    self.operation_names = []
                    self.index = None
                    
                    raise ValueError(f"FAISS index dimension ({self.index.d}) does not match embedding dimension ({self.embedding_dim})")
                
                print(f"[INFO] Successfully loaded FAISS index with dimension {self.index.d}")
        else:
            self.index = None
            print(f"[WARNING] No FAISS index found in cache")
        
        print(f"[INFO] Operation index loaded successfully from {path}")
        print(f"[INFO] Loaded {len(self.operation_embeddings)} operations with dimension {self.embedding_dim}")


    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计信息"""
        category_counts = defaultdict(int)
        for op_emb in self.operation_embeddings.values():
            category_counts[op_emb.category] += 1
        
        return {
            'total_operations': len(self.operation_embeddings),
            'categories': dict(category_counts),
            'has_faiss': HAS_FAISS and self.index is not None,
            'has_openai': self.openai_client is not None,
            'embedding_dim': self.embedding_dim
        }


# 文件：operation_embedding_index.py
# 位置：第580-605行
# 函数：get_operation_index

# 单例实例
_operation_index_instance = None

def get_operation_index() -> OperationEmbeddingIndex:
    """获取操作索引的单例实例"""
    global _operation_index_instance
    
    if _operation_index_instance is None:
        logger.debug(f" Creating new OperationEmbeddingIndex instance")
        _operation_index_instance = OperationEmbeddingIndex()
        logger.debug(f" OperationEmbeddingIndex created with {len(_operation_index_instance.embedding_cache)} cached embeddings")
    else:
        logger.debug(f" Reusing existing OperationEmbeddingIndex instance with {len(_operation_index_instance.embedding_cache)} cached embeddings")
    
    return _operation_index_instance

def reset_operation_index():
    """重置单例实例（用于测试或重新初始化）"""
    global _operation_index_instance
    logger.debug(f" Resetting OperationEmbeddingIndex singleton")
    _operation_index_instance = None

def get_embedding_cache_info() -> dict:
    """获取当前embedding缓存信息（调试用）"""
    global _operation_index_instance
    
    if _operation_index_instance is None:
        return {"status": "not_initialized"}
    
    cache_stats = _operation_index_instance._get_embedding_cache_stats()
    cache_stats["instance_id"] = id(_operation_index_instance)
    return cache_stats


if __name__ == "__main__":
    # 测试代码
    print("Testing Operation Embedding Index...")
    
    index = get_operation_index()
    
    # 测试搜索
    test_queries = [
        "load data from file",
        "check if data is valid",
        "save results to database",
        "combine multiple datasets",
        "calculate statistics"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = index.search_operation(query, k=3)
        for op_name, score in results:
            print(f"  - {op_name}: {score:.3f}")
    
    # 显示统计信息
    print("\nIndex Statistics:")
    stats = index.get_stats()
    print(json.dumps(stats, indent=2))
