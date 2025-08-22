# 相同位置的修复代码
# 修改的行用注释标注：# <- 修改了这一行

#!/usr/bin/env python3
"""
Unified Training Manager - Refactored for Better Structure
==========================================================
重构后的版本，解决了类职责不清和方法缺失的问题
"""

import os
import sys
import json
import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical  # <- 新增这一行：导入Categorical
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, deque, OrderedDict
from datetime import datetime
import random
import uuid
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import concurrent.futures
import faiss
import time
import threading
import math

from torch.distributed.fsdp import FullyShardedDataParallel as FSDP


from workflow_reasoning_generator import WorkflowReasoningGenerator
from tool_capability_manager import ToolCapabilityManager  # <- 修改了这一行：添加导入
from interactive_executor import ToolExecutionResult
from mcp_embedding_manager import MCPEmbeddingManager, SearchResult


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建文件处理器
log_filename = f"logs/debug__unified_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.INFO)

# Device configuration
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Using device: {device}")

# Import ScoringThresholds for type annotation  # <- 修改了这一行
from workflow_quality_test_flawed import ScoringThresholds  # <- 修改了这一行


# 文件：unified_training_manager.py
# 位置：EmbeddingDistillationCache类

class EmbeddingDistillationCache:
    """基于语义embedding的teacher蒸馏缓存系统"""
    
    def __init__(self, cache_dir: str = ".distillation_cache", 
                 max_size: int = 100000,
                 similarity_threshold: float = 0.95):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        
        # 初始化MCPEmbeddingManager来获取embeddings
        from mcp_embedding_manager import get_embedding_manager
        self.embedding_manager = get_embedding_manager()
            
        # 缓存文件路径
        self.cache_file = self.cache_dir / "teacher_cache_v2.pkl"
        self.index_file = self.cache_dir / "teacher_index.faiss"
        
        # 缓存数据结构
        self.cache_entries = OrderedDict()  # key -> distribution
        self.cache_keys = []  # 保存原始key用于查找
        self.embeddings = []  # 对应的embedding向量
        
        # FAISS索引
        self.index = None
        self.embedding_dim = None  # 动态确定维度
        
        # 加载已有缓存
        self._load_cache()
        
    def _load_cache(self):
        """从磁盘加载缓存和索引"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.cache_entries = saved_data.get('entries', OrderedDict())
                    self.cache_keys = saved_data.get('keys', [])
                    self.embeddings = saved_data.get('embeddings', [])
                    self.embedding_dim = saved_data.get('embedding_dim', None)
                print(f"[EmbeddingDistillationCache] Loaded {len(self.cache_entries)} cached entries")
                print(f"[EmbeddingDistillationCache] Embedding dimension: {self.embedding_dim}")
            except Exception as e:
                print(f"[EmbeddingDistillationCache] Failed to load cache: {e}")
                self.cache_entries = OrderedDict()
                self.cache_keys = []
                self.embeddings = []
                self.embedding_dim = None
        
        # 重建FAISS索引
        if self.embeddings and self.embedding_dim:
            self._rebuild_index()
    
    def _rebuild_index(self):
        """重建FAISS索引"""
        if not self.embeddings or not self.embedding_dim:
            return
            
        try:
            # 创建FAISS索引
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # 使用内积相似度
            
            # 检查所有embeddings的维度
            valid_embeddings = []
            valid_indices = []
            
            for i, emb in enumerate(self.embeddings):
                emb_array = np.array(emb) if not isinstance(emb, np.ndarray) else emb
                if emb_array.shape[0] == self.embedding_dim:
                    valid_embeddings.append(emb_array)
                    valid_indices.append(i)
                else:
                    print(f"[EmbeddingDistillationCache] WARNING: Embedding {i} has wrong dimension {emb_array.shape[0]}, expected {self.embedding_dim}")
            
            if valid_embeddings:
                # 只添加有效的embeddings
                embeddings_matrix = np.vstack(valid_embeddings).astype('float32')
                faiss.normalize_L2(embeddings_matrix)  # 归一化以使用余弦相似度
                self.index.add(embeddings_matrix)
                
                # 如果有无效的embeddings，清理它们
                if len(valid_indices) < len(self.embeddings):
                    print(f"[EmbeddingDistillationCache] Cleaning up {len(self.embeddings) - len(valid_indices)} invalid embeddings")
                    # 重建数据结构，只保留有效的
                    new_embeddings = []
                    new_keys = []
                    new_entries = OrderedDict()
                    
                    for idx in valid_indices:
                        new_embeddings.append(self.embeddings[idx])
                        key = self.cache_keys[idx]
                        new_keys.append(key)
                        new_entries[key] = self.cache_entries[key]
                    
                    self.embeddings = new_embeddings
                    self.cache_keys = new_keys
                    self.cache_entries = new_entries
                
                print(f"[EmbeddingDistillationCache] Rebuilt index with {len(valid_embeddings)} entries")
            else:
                print(f"[EmbeddingDistillationCache] ERROR: No valid embeddings found!")
                self.index = None
                
        except Exception as e:
            print(f"[EmbeddingDistillationCache] ERROR rebuilding index: {e}")
            self.index = None
    
    def _save_cache(self):
        """保存缓存到磁盘"""
        try:
            save_data = {
                'entries': self.cache_entries,
                'keys': self.cache_keys,
                'embeddings': self.embeddings,
                'embedding_dim': self.embedding_dim  # 保存维度信息
            }
            with open(self.cache_file, 'wb') as f:
                pickle.dump(save_data, f)
            print(f"[EmbeddingDistillationCache] Saved {len(self.cache_entries)} entries to disk")
        except Exception as e:
            print(f"[EmbeddingDistillationCache] Failed to save cache: {e}")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """获取文本的embedding（使用MCPEmbeddingManager的缓存）"""
        # 直接使用embedding manager的缓存机制
        embedding = self.embedding_manager._get_embedding(text)
        
        # 第一次获取embedding时设置维度
        if self.embedding_dim is None:
            self.embedding_dim = embedding.shape[0]
            print(f"[EmbeddingDistillationCache] Set embedding dimension to {self.embedding_dim}")
        
        return embedding
    
    def get(self, state_desc: str, tool_list: List[str], 
            rag_context: Optional[Dict] = None) -> Optional[Dict[str, float]]:
        """获取缓存的分布（基于语义相似度）"""
        if not self.index or len(self.cache_entries) == 0:
            return None
        
        # 创建查询key
        query_key = self._create_cache_key(state_desc, tool_list, rag_context)
        
        # 获取查询embedding
        query_embedding = self._get_embedding(query_key)
        
        # 检查维度
        if query_embedding.shape[0] != self.embedding_dim:
            print(f"[EmbeddingDistillationCache] WARNING: Query embedding dimension {query_embedding.shape[0]} != expected {self.embedding_dim}")
            return None
        
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_embedding)
        
        # 搜索最相似的缓存项
        distances, indices = self.index.search(query_embedding, 1)
        
        if distances[0][0] >= self.similarity_threshold:
            # 找到足够相似的缓存项
            cache_idx = indices[0][0]
            original_key = self.cache_keys[cache_idx]
            
            # 更新LRU顺序
            self.cache_entries.move_to_end(original_key)
            
            print(f"[EmbeddingDistillationCache] Cache hit with similarity {distances[0][0]:.3f}")
            return self.cache_entries[original_key]
        
        return None
    
    def put(self, state_desc: str, tool_list: List[str], 
            distribution: Dict[str, float], rag_context: Optional[Dict] = None):
        """存储分布到缓存"""
        # 创建key
        cache_key = self._create_cache_key(state_desc, tool_list, rag_context)
        
        # 获取embedding
        embedding = self._get_embedding(cache_key)
        
        # 检查维度
        if self.embedding_dim and embedding.shape[0] != self.embedding_dim:
            print(f"[EmbeddingDistillationCache] ERROR: Embedding dimension mismatch: {embedding.shape[0]} != {self.embedding_dim}")
            return
        
        # 检查是否需要删除旧条目
        if len(self.cache_entries) >= self.max_size:
            # 删除最旧的条目
            oldest_key = next(iter(self.cache_entries))
            self.cache_entries.pop(oldest_key)
            
            # 找到并删除对应的索引
            old_idx = self.cache_keys.index(oldest_key)
            self.cache_keys.pop(old_idx)
            self.embeddings.pop(old_idx)
            
            # 需要重建索引
            self._rebuild_index()
        
        # 添加新条目
        self.cache_entries[cache_key] = distribution
        self.cache_keys.append(cache_key)
        self.embeddings.append(embedding)
        
        # 更新FAISS索引
        if self.index is None:
            self._rebuild_index()
        else:
            # 添加单个向量到索引
            embedding_matrix = embedding.reshape(1, -1).astype('float32')
            faiss.normalize_L2(embedding_matrix)
            self.index.add(embedding_matrix)
        
        # 定期保存
        if len(self.cache_entries) % 100 == 0:
            self._save_cache()
            
    def clear(self):
        """清空缓存"""
        self.cache_entries = OrderedDict()
        self.cache_keys = []
        self.embeddings = []
        self.index = None
        self.embedding_dim = None
        print("[EmbeddingDistillationCache] Cache cleared")
    
    def _create_cache_key(self, state_desc: str, tool_list: List[str], 
                         rag_context: Optional[Dict] = None) -> str:
        """创建用于生成embedding的文本描述"""
        # 过滤None值和特殊动作
        valid_tools = []
        for tool in tool_list:
            if tool is not None and not tool.startswith('action_'):
                valid_tools.append(tool)
        
        # 构建描述文本
        key_parts = [
            f"Task: {state_desc}",
            f"Available tools: {', '.join(sorted(valid_tools)) if valid_tools else 'none'}"
        ]
        
        # 添加RAG上下文信息
        if rag_context:
            rag_info = []
            for operation, results in rag_context.items():
                if results and len(results) > 0:
                    top_result = results[0]
                    if hasattr(top_result, 'tool_name'):
                        rag_info.append(f"{operation}:{top_result.tool_name}")
            if rag_info:
                key_parts.append(f"RAG context: {', '.join(rag_info)}")
        
        return " | ".join(key_parts)


class ActorCriticNetwork(nn.Module):
    """超级增强的Actor-Critic网络，包含最新的深度学习技术、RAG支持和required_tools输入"""
    
    def __init__(self, state_dim: int, action_dim: int, config: Dict[str, Any] = None):
        super().__init__()
        
        print(f"[ActorCriticNetwork.__init__] Debug - state_dim={state_dim}, action_dim={action_dim}, config type={type(config)}")
        
        # 检查action_dim是否为None
        if action_dim is None:
            print("[ActorCriticNetwork] ERROR: action_dim is None!")
            raise ValueError("action_dim cannot be None. Please check model loading logic.")
        
        # 兼容性处理：检查第三个参数是否为配置字典
        if config is None:
            print("[ActorCriticNetwork] Warning: config is None, using default configuration")
            config = {}
        elif isinstance(config, int):
            # 向后兼容：如果传入的是整数，将其作为hidden_dim
            print(f"[ActorCriticNetwork] Warning: received int {config} instead of dict, treating as hidden_dim")
            config = {'hidden_dim': config}
        elif not isinstance(config, dict):
            print(f"[ActorCriticNetwork] Error: config is neither dict nor int, type={type(config)}")
            print(f"[ActorCriticNetwork] config value: {config}")
            # 使用默认配置
            config = {}
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.expected_state_dim = state_dim

        # 从配置中获取参数，确保类型正确
        self.hidden_dim = int(config.get('hidden_dim', 1024))
        self.num_layers = int(config.get('num_layers', 6))
        self.num_heads = int(config.get('num_heads', 16))
        self.dropout = float(config.get('dropout', 0.1))
        self.use_pre_norm = bool(config.get('use_pre_norm', True))
        self.use_rag_enhancement = bool(config.get('use_rag_enhancement', True))
        self.rag_dim = int(config.get('rag_dim', 64))
        # 移除对use_tools_input的依赖，始终创建tools_projection
        self.num_tools = int(config.get('num_tools', action_dim))
        self.tools_dim = int(config.get('tools_dim', 64))

        print(self.num_tools, "number of tools \n\n\n")
        
        # 验证hidden_dim的值
        if self.hidden_dim <= 0:
            print(f"[ActorCriticNetwork] Error: invalid hidden_dim={self.hidden_dim}, using default 1024")
            self.hidden_dim = 1024
        
        print(f"[ActorCriticNetwork] Initialized with hidden_dim={self.hidden_dim}, num_layers={self.num_layers}")
        
        # 输入投影
        self.input_projection = nn.Sequential(
            nn.Linear(state_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.GELU(),
            nn.Dropout(self.dropout)
        )

        self.dynamic_adapter = None

        
        # RAG投影层（条件创建）
        self.rag_projection = nn.Sequential(
            nn.Linear(self.rag_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.GELU(),
            nn.Dropout(self.dropout)
        )
        print(f"[ActorCriticNetwork] RAG projection layer created with dim={self.rag_dim}")
        
        # Tools投影层 - 始终创建（关键修改：移除条件判断）
        self.tools_projection = nn.Sequential(
            nn.Linear(self.tools_dim, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
            nn.GELU(),
            nn.Dropout(self.dropout)
        )
        print(f"[ActorCriticNetwork] Tools projection layer ALWAYS created with dim={self.tools_dim}")
        
        # Transformer编码器层
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=self.hidden_dim,
            nhead=self.num_heads,
            dim_feedforward=self.hidden_dim * 4,
            dropout=self.dropout,
            activation='gelu',
            norm_first=self.use_pre_norm,
            batch_first=True
        )
        
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=self.num_layers,
            norm=nn.LayerNorm(self.hidden_dim) if self.use_pre_norm else None
        )
        
        # 位置编码（可学习）
        self.pos_encoding = nn.Parameter(torch.randn(1, 128, self.hidden_dim))
        
        # Actor和Critic头部（使用更深的网络）
        self.actor_head = nn.Sequential(
            nn.Linear(self.hidden_dim, self.hidden_dim // 2),
            nn.LayerNorm(self.hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.hidden_dim // 2, self.hidden_dim // 4),
            nn.LayerNorm(self.hidden_dim // 4),
            nn.GELU(),
            nn.Linear(self.hidden_dim // 4, action_dim)
        )
        
        self.critic_head = nn.Sequential(
            nn.Linear(self.hidden_dim, self.hidden_dim // 2),
            nn.LayerNorm(self.hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(self.dropout),
            nn.Linear(self.hidden_dim // 2, self.hidden_dim // 4),
            nn.LayerNorm(self.hidden_dim // 4),
            nn.GELU(),
            nn.Linear(self.hidden_dim // 4, 1)
        )
        
        # 辅助任务头部（如果启用）
        if config.get('use_auxiliary_tasks', False):
            # 下一步工具预测
            self.next_tool_predictor = nn.Linear(self.hidden_dim, action_dim)
            
            # 进度预测
            self.progress_predictor = nn.Linear(self.hidden_dim, 1)
            
            # 错误预测
            self.error_predictor = nn.Linear(self.hidden_dim, 2)  # 二分类：是否会出错
        
        # 好奇心模块（如果启用）
        if config.get('use_curiosity', False):
            # 前向模型：预测下一个状态
            self.forward_model = nn.Sequential(
                nn.Linear(state_dim + action_dim, self.hidden_dim),
                nn.ReLU(),
                nn.Linear(self.hidden_dim, state_dim)
            )
            
            # 逆向模型：从状态预测动作
            self.inverse_model = nn.Sequential(
                nn.Linear(state_dim * 2, self.hidden_dim),
                nn.ReLU(),
                nn.Linear(self.hidden_dim, action_dim)
            )
        
        # 多任务适配器（如果启用）
        if config.get('use_task_adapters', False):
            self.task_adapters = nn.ModuleDict()
            for task_type in ['data_pipeline', 'api_integration', 'basic_task', 'multi_stage']:
                self.task_adapters[task_type] = nn.Sequential(
                    nn.Linear(self.hidden_dim, self.hidden_dim // 2),
                    nn.ReLU(),
                    nn.Linear(self.hidden_dim // 2, self.hidden_dim // 4)
                )
        
        # 初始化权重
        self._init_weights()
        
        # 谱归一化（如果启用）
        if config.get('spectral_norm', False):
            self._apply_spectral_norm()
        
        print("[ActorCriticNetwork] Initialization complete with tools_projection always created")
    def _init_weights(self):
        """改进的权重初始化"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.LayerNorm):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.TransformerEncoderLayer):
                # Transformer层的特殊初始化
                for p in m.parameters():
                    if p.dim() > 1:
                        nn.init.xavier_uniform_(p)
    
    def _apply_spectral_norm(self):
        """应用谱归一化"""
        for m in self.modules():
            if isinstance(m, nn.Linear) and m.out_features > 1:
                nn.utils.spectral_norm(m)


    def forward(self, state, rag_context=None, required_tools=None, return_features=False):
        """增强的前向传播，支持RAG上下文和required_tools输入 - 修复FSDP兼容性"""
        
        # 维度检查和自动修复 - 处理1D输入的情况
        if state.dim() == 1:
            logger.debug(f"[PPORAGNetwork.forward] WARNING: Received 1D state tensor with shape {state.shape}, adding batch dimension")
            state = state.unsqueeze(0)  # 添加 batch 维度
        elif state.dim() > 3:
            logger.debug(f"[PPORAGNetwork.forward] ERROR: State tensor has too many dimensions: {state.shape}")
            raise ValueError(f"State tensor must be 1D, 2D or 3D, got {state.dim()}D tensor")
        
        logger.debug(f"[PPORAGNetwork.forward] Input state shape: {state.shape}, expected state_dim: {self.expected_state_dim}")
        
        # 获取输入的数据类型和设备，用于保持一致性
        target_dtype = state.dtype
        target_device = state.device
        logger.debug(f"[PPORAGNetwork.forward] Target dtype: {target_dtype}, device: {target_device}")
        
        # 🔧 关键修复：检查是否在FSDP环境下
        # 方法1：检查模型是否被FSDP包装
        if isinstance(self, FSDP):
            logger.debug(f"[PPORAGNetwork.forward] Model is wrapped with FSDP")
            # 在FSDP环境下，确保使用正确的设备
            if hasattr(self, 'compute_device'):
                target_device = self.compute_device
                logger.debug(f"[PPORAGNetwork.forward] Using FSDP compute_device: {target_device}")
                state = state.to(target_device)
        
        # 方法2：检查第一个参数的设备，确保一致性
        # 获取模型参数的设备（通过第一个参数）
        try:
            first_param = next(self.parameters())
            param_device = first_param.device
            if state.device != param_device:
                logger.debug(f"[PPORAGNetwork.forward] Moving state from {state.device} to model device {param_device}")
                state = state.to(param_device)
                target_device = param_device
        except StopIteration:
            # 没有参数的情况（不太可能）
            logger.debug(f"[PPORAGNetwork.forward] Warning: Model has no parameters")
        
        # 检查输入维度
        actual_state_dim = state.shape[-1]
        if actual_state_dim != self.expected_state_dim:
            logger.debug(f"[PPORAGNetwork.forward] WARNING: State dimension mismatch! Expected {self.expected_state_dim}, got {actual_state_dim}")
            
            # 动态创建适配层
            if self.dynamic_adapter is None or self.dynamic_adapter.in_features != actual_state_dim:
                logger.debug(f"[PPORAGNetwork.forward] Creating dynamic adapter: {actual_state_dim} -> {self.expected_state_dim}")
                self.dynamic_adapter = nn.Linear(actual_state_dim, self.expected_state_dim).to(target_device, dtype=target_dtype)
                # 初始化为近似恒等映射
                with torch.no_grad():
                    if actual_state_dim <= self.expected_state_dim:
                        # 如果实际维度更小，填充零
                        self.dynamic_adapter.weight.zero_()
                        self.dynamic_adapter.weight[:actual_state_dim, :actual_state_dim] = torch.eye(actual_state_dim).to(target_device, dtype=target_dtype)
                    else:
                        # 如果实际维度更大，截断
                        self.dynamic_adapter.weight.zero_()
                        self.dynamic_adapter.weight[:, :self.expected_state_dim] = torch.eye(self.expected_state_dim, actual_state_dim).T.to(target_device, dtype=target_dtype)
                    self.dynamic_adapter.bias.zero_()
            
            # 确保adapter在正确的设备上
            if self.dynamic_adapter.weight.device != target_device:
                self.dynamic_adapter = self.dynamic_adapter.to(target_device)
            
            # 使用适配层转换输入
            state = self.dynamic_adapter(state)
            logger.debug(f"[PPORAGNetwork.forward] After adaptation: {state.shape}")
            
            # 重要：确保经过adapter后仍然保持正确的维度
            if state.dim() == 1:
                logger.debug(f"[PPORAGNetwork.forward] ERROR: State became 1D after adapter, this should not happen!")
                logger.debug(f"[PPORAGNetwork.forward] dynamic_adapter info: in_features={self.dynamic_adapter.in_features}, out_features={self.dynamic_adapter.out_features}")
                logger.debug(f"[PPORAGNetwork.forward] Fixing by adding batch dimension...")
                state = state.unsqueeze(0)
            elif state.dim() != 2 and state.dim() != 3:
                logger.debug(f"[PPORAGNetwork.forward] ERROR: Unexpected state dimension after adapter: {state.dim()}")
                raise ValueError(f"State tensor after adapter must be 2D or 3D, got {state.dim()}D tensor with shape {state.shape}")
        
        # 最终维度检查 - 在调用input_projection之前
        if state.dim() == 1:
            logger.debug(f"[PPORAGNetwork.forward] CRITICAL: State is still 1D before input_projection!")
            state = state.unsqueeze(0)
        
        logger.debug(f"[PPORAGNetwork.forward] Final state shape before projection: {state.shape}")
        logger.debug(f"[PPORAGNetwork.forward] State device: {state.device}, dtype: {state.dtype}")
        
        # 🔧 关键修复：确保数据类型兼容性
        # 在多GPU环境下，保持float32以避免精度问题
        if state.dtype not in [torch.float32, torch.float16]:
            logger.debug(f"[PPORAGNetwork.forward] Converting state from {state.dtype} to float32")
            state = state.to(torch.float32)
            target_dtype = torch.float32
        
        # 输入投影 - 这里是出错的地方
        logger.debug(f"[PPORAGNetwork.forward] Calling input_projection with state shape: {state.shape}, device: {state.device}, dtype: {state.dtype}")
        
        # 确保state在正确的设备上（最后一次检查）
        state = state.to(target_device)
        
        x = self.input_projection(state)
        logger.debug(f"[PPORAGNetwork.forward] After input_projection: shape={x.shape}, device={x.device}, dtype={x.dtype}")
        
        # 准备序列元素列表
        sequence_elements = [x.unsqueeze(1) if x.dim() == 2 else x]
        
        # RAG上下文融合（如果提供）
        if rag_context is not None and hasattr(self, 'rag_projection'):
            # 确保rag_context具有正确的维度
            if rag_context.dim() == 1:
                logger.debug(f"[PPORAGNetwork.forward] RAG context is 1D, adding batch dimension")
                rag_context = rag_context.unsqueeze(0)
            
            # 确保rag_context具有正确的数据类型和设备
            rag_context = rag_context.to(dtype=target_dtype, device=target_device)
            rag_features = self.rag_projection(rag_context)
            if rag_features.dim() == 2:
                rag_features = rag_features.unsqueeze(1)
            sequence_elements.append(rag_features)
            logger.debug(f"Added RAG features to sequence")
        
        # 新增：Required tools融合（如果提供）
        if required_tools is not None and hasattr(self, 'tools_projection'):
            # 确保required_tools具有正确的维度
            if required_tools.dim() == 1:
                logger.debug(f"[PPORAGNetwork.forward] Required tools is 1D, adding batch dimension")
                required_tools = required_tools.unsqueeze(0)
            
            # 确保required_tools具有正确的数据类型和设备
            required_tools = required_tools.to(dtype=target_dtype, device=target_device)
            tools_features = self.tools_projection(required_tools)
            if tools_features.dim() == 2:
                tools_features = tools_features.unsqueeze(1)
            sequence_elements.append(tools_features)
            logger.debug(f"Added tools features to sequence")
        
        # 合并所有序列元素
        x = torch.cat(sequence_elements, dim=1)
        
        # 添加位置编码 - 确保数据类型匹配
        seq_len = x.size(1)
        if seq_len > self.pos_encoding.size(1):
            # 动态扩展位置编码，使用正确的dtype和device
            additional_pos = torch.randn(1, seq_len - self.pos_encoding.size(1), self.hidden_dim, 
                                    dtype=target_dtype, device=target_device)
            # 确保原始位置编码也具有正确的数据类型
            self.pos_encoding.data = self.pos_encoding.data.to(dtype=target_dtype, device=target_device)
            self.pos_encoding = nn.Parameter(torch.cat([self.pos_encoding, additional_pos], dim=1))
            logger.debug(f"[PPORAGNetwork.forward] Expanded pos_encoding to seq_len={seq_len}")
        
        # 确保位置编码具有正确的数据类型和设备
        pos_encoding_slice = self.pos_encoding[:, :seq_len, :].to(dtype=target_dtype, device=target_device)
        x = x + pos_encoding_slice
        
        # Transformer编码
        logger.debug(f"[PPORAGNetwork.forward] Before transformer: x shape={x.shape}, dtype={x.dtype}, device={x.device}")
        features = self.transformer_encoder(x)
        logger.debug(f"[PPORAGNetwork.forward] After transformer: features shape={features.shape}, dtype={features.dtype}, device={features.device}")
        
        # 全局池化（取平均）
        global_features = features.mean(dim=1)
        
        # 计算输出
        policy_logits = self.actor_head(global_features)
        value = self.critic_head(global_features)
        
        logger.debug(f"[PPORAGNetwork.forward] Final output - policy_logits shape: {policy_logits.shape}, value shape: {value.shape}")
        logger.debug(f"[PPORAGNetwork.forward] Output device: {policy_logits.device}, dtype: {policy_logits.dtype}")
        
        if return_features:
            return policy_logits, value, global_features
        else:
            return policy_logits, value

            
    def get_action_and_value(self, state, action=None, rag_context=None, required_tools=None):
        """获取动作分布、采样动作、对数概率和价值"""
        logits, value = self(state, rag_context, required_tools)
        
        # 创建分类分布
        probs = F.softmax(logits, dim=-1)
        dist = torch.distributions.Categorical(probs)
        
        if action is None:
            action = dist.sample()
        
        return action, dist.log_prob(action), dist.entropy(), value
    
    def load_from_old_version(self, old_state_dict):
        """从旧版本模型加载权重的兼容性方法"""
        new_state_dict = self.state_dict()
        
        # 复制匹配的键
        for key in old_state_dict:
            if key in new_state_dict and old_state_dict[key].shape == new_state_dict[key].shape:
                new_state_dict[key] = old_state_dict[key]
                print(f"[INFO] Loaded weights for {key}")
            else:
                print(f"[WARNING] Skipping {key} (not found or shape mismatch)")
        
        # 加载更新后的状态字典
        self.load_state_dict(new_state_dict, strict=False)
        print("[INFO] Loaded weights from old version with compatibility mapping")



def encode_required_tools_embedding(required_tools: List[str], embedding_manager=None, target_dim: int = None) -> np.ndarray:
    """
    将required_tools列表编码为固定大小的embedding向量
    使用与RAG相同的编码方式保持一致性
    
    Args:
        required_tools: 需要的工具名称列表
        embedding_manager: embedding管理器实例
        target_dim: 目标维度，如果为None则从embedding_manager推断
        
    Returns:
        固定大小的embedding向量
    """
    # 确定目标维度
    if target_dim is not None:
        embedding_dim = target_dim
    else:
        # 默认使用64维以保持向后兼容
        embedding_dim = 64
        print(f"[WARNING] encode_required_tools_embedding: target_dim not specified, using default {embedding_dim}")
    
    print(f"[DEBUG] encode_required_tools_embedding using target dim={embedding_dim}")
    
    tools_embedding = np.zeros(embedding_dim)
    
    if not required_tools:
        return tools_embedding
    
    # 如果有embedding_manager，使用真实的工具embeddings
    if embedding_manager and hasattr(embedding_manager, 'tool_embeddings'):
        all_embeddings = []
        all_scores = []
        
        for tool_name in required_tools:
            if tool_name in embedding_manager.tool_embeddings:
                tool_emb = embedding_manager.tool_embeddings[tool_name]
                # 使用combined_embedding（综合了描述、参数、功能）
                if hasattr(tool_emb, 'combined_embedding'):
                    all_embeddings.append(tool_emb.combined_embedding)
                    all_scores.append(1.0)  # required tools权重最高
        
        if all_embeddings:
            # 加权平均
            all_embeddings = np.array(all_embeddings)
            all_scores = np.array(all_scores)
            all_scores = all_scores / all_scores.sum()
            
            # 计算加权embedding
            high_dim_embedding = np.zeros(all_embeddings.shape[1])
            for i, (emb, score) in enumerate(zip(all_embeddings, all_scores)):
                high_dim_embedding += emb * score
            
            # 降维到目标维度
            if high_dim_embedding.shape[0] > embedding_dim:
                # 使用PCA或简单的投影来降维
                # 这里使用简单的分段平均方法
                chunk_size = high_dim_embedding.shape[0] // embedding_dim
                for i in range(embedding_dim):
                    start_idx = i * chunk_size
                    end_idx = start_idx + chunk_size if i < embedding_dim - 1 else high_dim_embedding.shape[0]
                    tools_embedding[i] = high_dim_embedding[start_idx:end_idx].mean()
            else:
                # 如果原始维度小于目标维度，直接复制并填充零
                tools_embedding[:high_dim_embedding.shape[0]] = high_dim_embedding
        else:
            # 如果没有找到embedding，使用简单编码
            for i, tool in enumerate(required_tools[:10]):  # 最多10个工具
                # 在embedding空间中分散编码
                index = hash(tool) % embedding_dim
                tools_embedding[index] = 1.0
                # 添加一些相邻位置的激活
                for offset in [-1, 1]:
                    neighbor_idx = (index + offset) % embedding_dim
                    tools_embedding[neighbor_idx] = 0.5
    else:
        # Fallback：简单的one-hot风格编码
        for i, tool in enumerate(required_tools[:10]):
            # 使用哈希函数将工具名映射到embedding空间
            index = hash(tool) % embedding_dim
            tools_embedding[index] = 1.0
    
    # 归一化
    norm = np.linalg.norm(tools_embedding)
    if norm > 0:
        tools_embedding = tools_embedding / norm
    
    return tools_embedding

# ===========================
# Base Trainer Interface
# ===========================

# 文件：unified_training_manager.py
# 类：BaseTrainer（进一步增强版本）
# 位置：约310-500行

from abc import ABC, abstractmethod

# 文件：unified_training_manager.py
# 位置：BaseTrainer类的__init__方法（约310-400行）
# 注意：完整的修复版本，添加了eval_mode初始化

class BaseTrainer(ABC):
    """Enhanced abstract base class for all training algorithms"""
    
    def __init__(self, env: 'MDPEnvironment', config: Dict[str, Any]):
        self.env = env
        self.config = config
        
        # 增强的设备选择逻辑
        print(f"[BaseTrainer.__init__] Initializing device selection")
        print(f"[BaseTrainer.__init__] Config device: {config.get('device', 'not specified')}")
        print(f"[BaseTrainer.__init__] CUDA available: {torch.cuda.is_available()}")
        
        # 优先使用配置中的设备设置
        if 'device' in config and config['device']:
            if config['device'] == 'cuda' and not torch.cuda.is_available():
                print(f"[BaseTrainer.__init__] ERROR: CUDA requested but not available!")
                raise RuntimeError("CUDA device requested but not available on this system")
            self.device = torch.device(config['device'])
        else:
            # 自动选择设备
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
        print(f"[BaseTrainer.__init__] Selected device: {self.device}")
        
        # 如果使用GPU，打印详细信息
        if self.device.type == 'cuda':
            print(f"[BaseTrainer.__init__] GPU Device: {torch.cuda.get_device_name()}")
            print(f"[BaseTrainer.__init__] GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
            
        # Training parameters
        self.gamma = config.get('gamma', 0.99)
        self.learning_rate = config.get('learning_rate', 3e-4)
        
        # Training state
        self.training_steps = 0
        self.total_timesteps = 0
        
        # 关键修复：添加eval_mode初始化
        self.eval_mode = False
        print(f"[BaseTrainer.__init__] Initialized eval_mode = {self.eval_mode}")
        
    @abstractmethod
    def select_action(self, state: np.ndarray, valid_actions: Optional[List[int]] = None) -> int:
        """Select an action given the current state"""
        pass
    
    @abstractmethod
    def train_step(self) -> float:
        """Perform one training step and return loss"""
        pass
    
    @abstractmethod
    def update_exploration(self):
        """Update exploration parameters (e.g., epsilon for DQN)"""
        pass
    
    @abstractmethod  # <- 新增：统一的经验存储接口
    def store_experience(self, state: np.ndarray, action: int, reward: float, 
                        next_state: np.ndarray, done: bool, **kwargs) -> None:
        """Store experience/transition - unified interface for all algorithms"""
        pass
    
    @abstractmethod  # <- 新增：判断是否应该训练
    def should_train(self) -> bool:
        """Check if training should be performed"""
        pass
    
    @abstractmethod  # <- 新增：episode结束时的清理
    def on_episode_end(self) -> None:
        """Called when an episode ends - for algorithm-specific cleanup"""
        pass
    
    def step_completed(self) -> None:  # <- 新增：每步完成后调用
        """Called after each environment step"""
        self.total_timesteps += 1
    
    def set_eval_mode(self, eval_mode: bool):
        """Set evaluation mode for the trainer"""
        self.eval_mode = eval_mode
        
    def apply_action_mask(self, action_values: torch.Tensor, 
                         valid_actions: Optional[List[int]]) -> torch.Tensor:
        """Apply action masking to action values/probabilities"""
        if valid_actions is not None:
            mask = torch.full_like(action_values, float('-inf'))
            mask[valid_actions] = 0
            return action_values + mask
        return action_values
    
    @staticmethod
    def stabilize_logits(logits: torch.Tensor, 
                        clamp_min: float = -10.0, 
                        clamp_max: float = 10.0) -> torch.Tensor:
        """Stabilize logits for numerical stability"""
        if torch.isnan(logits).any():
            logger.warning("NaN detected in logits, replacing with zeros")
            logits = torch.nan_to_num(logits, nan=0.0)
        
        logits = torch.clamp(logits, min=clamp_min, max=clamp_max)
        logits = logits - logits.max(dim=-1, keepdim=True)[0]
        
        return logits
    
    def save_checkpoint_base(self, path: str, 
                            state_dicts: Dict[str, Any],
                            additional_data: Dict[str, Any] = None) -> None:
        """Base checkpoint saving functionality"""
        checkpoint = {
            'algorithm': self.__class__.__name__.replace('Trainer', '').lower(),
            'training_steps': self.training_steps,
            'total_timesteps': self.total_timesteps,  # <- 新增
            'config': self.config,
            'timestamp': datetime.now().isoformat()
        }
        
        checkpoint.update(state_dicts)
        
        if additional_data:
            checkpoint.update(additional_data)
        
        torch.save(checkpoint, path)
        logger.info(f"Checkpoint saved to {path}")
    
    def load_checkpoint_base(self, path: str) -> Dict[str, Any]:
        """Base checkpoint loading functionality"""
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        
        self.training_steps = checkpoint.get('training_steps', 0)
        self.total_timesteps = checkpoint.get('total_timesteps', 0)  # <- 新增
        
        if 'config' in checkpoint:
            self.config.update(checkpoint['config'])
        
        return checkpoint
    
    @abstractmethod
    def save_checkpoint(self, path: str, additional_data: Dict[str, Any] = None):
        """Save model checkpoint - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def load_checkpoint(self, path: str) -> Dict[str, Any]:
        """Load model checkpoint - must be implemented by subclasses"""
        pass
    
    def get_device(self) -> torch.device:
        """Get the device being used"""
        return self.device
    
    def get_training_info(self) -> Dict[str, Any]:  # <- 新增：获取训练信息
        """Get current training information for logging"""
        return {
            'training_steps': self.training_steps,
            'total_timesteps': self.total_timesteps
        }


# 文件：unified_training_manager.py
# 在DQNTrainer类后添加（约第350行）

# ===========================
# PPO Trainer
# ===========================


class RolloutBuffer:
    """Base buffer for storing trajectories in PPO with RAG support and returns normalization"""
    
    def __init__(self, gamma: float = 0.99, normalize_returns: bool = True):
        """Initialize rollout buffer with discount factor
        
        Args:
            gamma: Discount factor for computing returns
            normalize_returns: Whether to normalize returns
        """
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
        self.rag_embeddings = []
        self.old_values = []  # 存储旧的value预测用于clipping
        self.gamma = gamma
        self.normalize_returns = normalize_returns
        print(f"[RolloutBuffer.__init__] gamma={gamma}, normalize_returns={normalize_returns}")
    
    def add(self, state, action, reward, value, log_prob, done, rag_embedding=None, **kwargs):
        """Add transition with optional RAG embedding"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.values.append(value)
        self.log_probs.append(log_prob)
        self.dones.append(done)
        
        # 存储旧的value用于后续的value clipping
        self.old_values.append(value)
        
        # 存储RAG embedding，如果没有则存储零向量
        if rag_embedding is not None:
            self.rag_embeddings.append(rag_embedding)
        else:
            self.rag_embeddings.append(np.zeros(64))  # 默认64维
    
    def get(self):
        """Get all data and compute advantages"""
        if not self.states:
            return None
        
        states = torch.FloatTensor(np.array(self.states)).to(device)
        actions = torch.LongTensor(self.actions).to(device)
        rewards = torch.FloatTensor(self.rewards).to(device)
        values = torch.FloatTensor(self.values).to(device)
        log_probs = torch.FloatTensor(self.log_probs).to(device)
        dones = torch.FloatTensor(self.dones).to(device)
        rag_embeddings = torch.FloatTensor(np.array(self.rag_embeddings)).to(device)
        old_values = torch.FloatTensor(self.old_values).to(device)
        

        # Compute returns and advantages
        returns = self._compute_returns(rewards, values, dones)
        
        # 标准化returns以稳定训练
        if self.normalize_returns and len(returns) > 1:
            returns_mean = returns.mean()
            returns_std = returns.std()
            if returns_std > 1e-8:
                returns = (returns - returns_mean) / (returns_std + 1e-8)
                # 缩放到合理范围
                returns = returns * 10.0  # 将标准化后的returns缩放到[-10, 10]范围
                print(f"[RolloutBuffer.get] Returns normalized: mean={returns_mean:.2f}, std={returns_std:.2f}")
            else:
                print(f"[RolloutBuffer.get] Returns std too small, skipping normalization")
        
        advantages = returns - values
        
        return states, actions, log_probs, returns, advantages, rag_embeddings, old_values
    
    def clear(self):
        """Clear all buffers"""
        self.states = []
        self.actions = []
        self.rewards = []
        self.values = []
        self.log_probs = []
        self.dones = []
        self.rag_embeddings = []
        self.old_values = []
    

    def _compute_returns(self, rewards: torch.Tensor, values: torch.Tensor, dones: torch.Tensor) -> torch.Tensor:
        """Compute discounted returns with reward scaling
        
        Args:
            rewards: Tensor of rewards
            values: Tensor of value estimates
            dones: Tensor of done flags
            
        Returns:
            Tensor of discounted returns
        """
        print(f"[RolloutBuffer._compute_returns] Computing returns with gamma={self.gamma}")
        
        # 检查空张量情况
        if len(rewards) == 0:
            print("[RolloutBuffer._compute_returns] ERROR: Empty rewards tensor!")
            print("[RolloutBuffer._compute_returns] This indicates no data was collected.")
            print("[RolloutBuffer._compute_returns] Check episode collection and buffer operations.")
            # 直接报错，不要静默处理
            # raise ValueError("Cannot compute returns on empty rewards tensor. No experience data collected.")
        
        # 对奖励进行缩放以防止returns过大
        reward_scale = 0.1  # 将奖励缩小10倍
        scaled_rewards = rewards * reward_scale
        
        returns = torch.zeros_like(scaled_rewards)
        running_return = 0
        
        # 从后向前计算折扣回报
        for t in reversed(range(len(scaled_rewards))):
            if dones[t]:
                running_return = 0
            running_return = scaled_rewards[t] + self.gamma * running_return
            returns[t] = running_return
        
        # 打印诊断信息
        print(f"[RolloutBuffer._compute_returns] Raw rewards range: [{rewards.min().item():.2f}, {rewards.max().item():.2f}]")
        print(f"[RolloutBuffer._compute_returns] Scaled returns range: [{returns.min().item():.2f}, {returns.max().item():.2f}]")
            
        return returns
    
    
class TaskAwareRolloutBuffer(RolloutBuffer):  # <- 修改了这一行：继承自RolloutBuffer
    """Task-aware buffer for PPO with experience replay capability"""
    
    def __init__(self, capacity_per_task: int = 10000, min_episodes_per_task: int = 10):
        super().__init__()  # <- 新增：调用父类构造函数
        
        # 任务特定的经验存储
        self.task_buffers = {}  # task_type -> list of episodes
        self.capacity_per_task = capacity_per_task
        self.min_episodes_per_task = min_episodes_per_task
        
        # 当前episode的临时存储（扩展父类功能）
        self.current_episode = {
            'states': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': [],
            'dones': [],
            'task_type': None,
            'rag_contexts': [],  
            'action_infos': []   
        }
        
        # 全局统计
        self.task_counts = defaultdict(int)
        self.total_episodes = 0
        
    def add(self, state, action, reward, value, log_prob, done, 
            rag_embedding=None, action_info=None):  # 修改：统一使用rag_embedding参数名
        """添加单步经验（扩展父类功能）"""
        print(f"[TaskAwareRolloutBuffer.add] Storing experience with rag_embedding shape: {rag_embedding.shape if rag_embedding is not None else None}")
        
        # 调用父类的add方法处理基础数据，传递所有参数
        super().add(state, action, reward, value, log_prob, done, 
                   rag_embedding=rag_embedding)  # 修改：正确传递rag_embedding参数
        
        # 处理扩展数据
        self.current_episode['states'].append(state)
        self.current_episode['actions'].append(action)
        self.current_episode['rewards'].append(reward)
        self.current_episode['values'].append(value)
        self.current_episode['log_probs'].append(log_prob)
        self.current_episode['dones'].append(done)
        
        # 修改：将rag_embedding存储为rag_contexts（保持向后兼容）
        # 如果action_info中包含rag_context信息，优先使用
        if action_info and 'rag_context' in action_info:
            self.current_episode['rag_contexts'].append(action_info['rag_context'])
        else:
            # 否则存储rag_embedding作为context
            self.current_episode['rag_contexts'].append(rag_embedding)
            
        self.current_episode['action_infos'].append(action_info)
        
        # 调试信息
        if done:
            print(f"[TaskAwareRolloutBuffer.add] Episode complete. Total steps: {len(self.current_episode['states'])}")
    
    def set_task_type(self, task_type: str):
        """设置当前episode的任务类型"""
        self.current_episode['task_type'] = task_type
    
    def store_episode(self):
        """存储完整的episode到任务buffer，添加数据验证"""
        task_type = self.current_episode['task_type'] or 'default'
        
        # 验证episode是否有有效数据
        if not self.current_episode['states'] or not self.current_episode['rewards']:
            print(f"[TaskAwareRolloutBuffer.store_episode] WARNING: Empty episode for task {task_type}")
            print(f"  States: {len(self.current_episode['states'])}")
            print(f"  Rewards: {len(self.current_episode['rewards'])}")
            print(f"  Actions: {len(self.current_episode['actions'])}")
            # 清空当前episode并返回，不存储空episode
            self.current_episode = {
                'states': [],
                'actions': [],
                'rewards': [],
                'values': [],
                'log_probs': [],
                'dones': [],
                'task_type': None,
                'rag_contexts': [],
                'action_infos': []
            }
            return
        
        # 验证数据长度一致性
        expected_length = len(self.current_episode['states'])
        for key in ['actions', 'rewards', 'values', 'log_probs', 'dones']:
            if len(self.current_episode[key]) != expected_length:
                print(f"[TaskAwareRolloutBuffer.store_episode] ERROR: Inconsistent data lengths!")
                print(f"  Expected: {expected_length}, {key}: {len(self.current_episode[key])}")
                # 不存储不一致的数据
                return
        
        if task_type not in self.task_buffers:
            self.task_buffers[task_type] = deque(maxlen=self.capacity_per_task)
        
        # 深拷贝当前episode数据
        episode_copy = {
            k: list(v) if isinstance(v, list) else v
            for k, v in self.current_episode.items()
        }
        
        # 计算episode总奖励
        episode_copy['total_reward'] = sum(self.current_episode['rewards'])
        
        self.task_buffers[task_type].append(episode_copy)
        self.task_counts[task_type] += 1
        self.total_episodes += 1
        
        print(f"[TaskAwareRolloutBuffer.store_episode] Stored episode for {task_type}")
        print(f"  Total reward: {episode_copy['total_reward']:.2f}")
        print(f"  Episode length: {expected_length}")
    
    def get(self, current_task_type=None, mix_ratio=0.7):
        """获取训练数据，支持任务感知的采样策略"""
        # 如果没有task buffer，使用父类的get方法  # <- 新增
        if not self.task_buffers:
            return super().get()
            
        episodes_to_process = []
        
        if current_task_type and current_task_type in self.task_buffers:
            # 混合采样策略
            current_task_episodes = int(mix_ratio * self.min_episodes_per_task)
            other_episodes = self.min_episodes_per_task - current_task_episodes
            
            # 从当前任务采样
            current_buffer = list(self.task_buffers[current_task_type])
            if current_buffer:
                sorted_episodes = sorted(current_buffer, 
                                       key=lambda ep: abs(ep.get('total_reward', 0) - 5.0))
                n_current = min(current_task_episodes, len(sorted_episodes))
                episodes_to_process.extend(sorted_episodes[:n_current])
            
            # 从其他任务采样
            other_tasks = [t for t in self.task_buffers if t != current_task_type]
            if other_tasks and other_episodes > 0:
                task_avg_rewards = {}
                for task in other_tasks:
                    task_buffer = self.task_buffers[task]
                    if task_buffer:
                        avg_reward = np.mean([ep.get('total_reward', 0) for ep in task_buffer])
                        task_avg_rewards[task] = avg_reward
                
                # 按平均奖励排序，优先采样困难任务
                sorted_tasks = sorted(other_tasks, key=lambda t: task_avg_rewards.get(t, 0))
                
                episodes_per_task = max(1, other_episodes // len(other_tasks))
                for task in sorted_tasks:
                    task_buffer = list(self.task_buffers[task])
                    if task_buffer:
                        # 同样优先选择中等奖励的episodes
                        sorted_task_episodes = sorted(task_buffer,
                                                    key=lambda ep: abs(ep.get('total_reward', 0) - 5.0))
                        n_select = min(episodes_per_task, len(sorted_task_episodes))
                        episodes_to_process.extend(sorted_task_episodes[:n_select])
        else:
            # 均衡采样所有任务
            for task_type, buffer in self.task_buffers.items():
                if buffer:
                    task_buffer = list(buffer)
                    sampled = np.random.choice(
                        len(task_buffer),
                        min(self.min_episodes_per_task, len(task_buffer)),
                        replace=False
                    )
                    episodes_to_process.extend([task_buffer[i] for i in sampled])
        
        # 合并所有episodes的数据
        if not episodes_to_process:  # <- 新增：空数据检查
            return None
        return self._merge_episodes(episodes_to_process)

    def _merge_episodes(self, episodes):
        """合并多个episodes的数据，过滤空episode"""
        all_states = []
        all_actions = []
        all_log_probs = []
        all_returns = []
        all_advantages = []
        all_rag_embeddings = []
        all_old_values = []
        
        # 过滤并处理有效的episodes
        valid_episodes = 0
        skipped_episodes = 0
        
        for episode in episodes:
            # 检查episode是否有效
            if not episode.get('states') or not episode.get('rewards'):
                print(f"[TaskAwareRolloutBuffer._merge_episodes] Skipping empty episode")
                skipped_episodes += 1
                continue
            
            try:
                # _process_episode_data 现在返回7个值（包含old_values）
                states, actions, log_probs, returns, advantages, rag_embeddings, old_values = self._process_episode_data(episode)
                all_states.append(states)
                all_actions.append(actions)
                all_log_probs.append(log_probs)
                all_returns.append(returns)
                all_advantages.append(advantages)
                all_rag_embeddings.append(rag_embeddings)
                all_old_values.append(old_values)
                valid_episodes += 1
            except ValueError as e:
                print(f"[TaskAwareRolloutBuffer._merge_episodes] Error processing episode: {e}")
                skipped_episodes += 1
                continue
        
        print(f"[TaskAwareRolloutBuffer._merge_episodes] Processed {valid_episodes} valid episodes, skipped {skipped_episodes}")
        
        # 连接所有数据
        if not all_states:
            print(f"[TaskAwareRolloutBuffer._merge_episodes] ERROR: No valid episodes to merge!")
            return None
            
        return (
            torch.cat(all_states),
            torch.cat(all_actions),
            torch.cat(all_log_probs),
            torch.cat(all_returns),
            torch.cat(all_advantages),
            torch.cat(all_rag_embeddings),
            torch.cat(all_old_values)
        )

    def _process_episode_data(self, episode):
        """处理单个episode数据，添加空数据检查"""
        # 首先检查episode是否有效
        if not episode.get('states') or not episode.get('rewards'):
            print(f"[TaskAwareRolloutBuffer._process_episode_data] WARNING: Empty episode data")
            print(f"  States: {len(episode.get('states', []))}")
            print(f"  Rewards: {len(episode.get('rewards', []))}")
            # 返回None或抛出更明确的错误
            raise ValueError(f"Empty episode data: states={len(episode.get('states', []))}, rewards={len(episode.get('rewards', []))}")
        
        states = torch.FloatTensor(np.array(episode['states'])).to(device)
        actions = torch.LongTensor(episode['actions']).to(device)
        rewards = torch.FloatTensor(episode['rewards']).to(device)
        values = torch.FloatTensor(episode['values']).to(device)
        log_probs = torch.FloatTensor(episode['log_probs']).to(device)
        dones = torch.FloatTensor(episode['dones']).to(device)
        
        # 再次验证rewards不为空
        if len(rewards) == 0:
            print(f"[TaskAwareRolloutBuffer._process_episode_data] ERROR: Empty rewards tensor after conversion")
            raise ValueError("Empty rewards tensor after conversion")
        
        # 处理RAG contexts/embeddings
        rag_contexts = episode.get('rag_contexts', [])
        if rag_contexts:
            # 处理存储的rag_contexts
            rag_embeddings_list = []
            for rag_data in rag_contexts:
                if isinstance(rag_data, np.ndarray):
                    # 已经是embedding
                    rag_embeddings_list.append(rag_data)
                elif rag_data is None:
                    # 使用零向量
                    rag_embeddings_list.append(np.zeros(64))
                else:
                    # 其他情况也使用零向量
                    rag_embeddings_list.append(np.zeros(64))
            rag_embeddings = torch.FloatTensor(np.array(rag_embeddings_list)).to(device)
        else:
            # 如果没有rag_contexts，创建与states相同长度的零向量
            print(f"[TaskAwareRolloutBuffer._process_episode_data] No rag_contexts found, using zero embeddings")
            rag_embeddings = torch.zeros(len(states), 64).to(device)
        
        # 计算returns - 使用父类实例的_compute_returns方法
        # 创建临时的RolloutBuffer实例来访问gamma和_compute_returns方法
        temp_buffer = RolloutBuffer(gamma=self.gamma if hasattr(self, 'gamma') else 0.99)
        returns = temp_buffer._compute_returns(rewards, values, dones)
        
        # 计算advantages
        advantages = returns - values
        
        # 获取old_values
        old_values = values.clone()
        
        # 打印调试信息
        print(f"[TaskAwareRolloutBuffer._process_episode_data] Processed episode successfully")
        print(f"  Episode length: {len(states)}")
        print(f"  Rewards range: [{rewards.min().item():.2f}, {rewards.max().item():.2f}]")
        print(f"  Returns range: [{returns.min().item():.2f}, {returns.max().item():.2f}]")
        print(f"  Advantages range: [{advantages.min().item():.2f}, {advantages.max().item():.2f}]")
        
        return states, actions, log_probs, returns, advantages, rag_embeddings, old_values
            
    def clear(self):
        """清空当前episode buffer"""
        super().clear()  # <- 新增：调用父类的clear
        
        # 清空扩展数据
        self.current_episode = {
            'states': [],
            'actions': [],
            'rewards': [],
            'values': [],
            'log_probs': [],
            'dones': [],
            'task_type': None,
            'rag_contexts': [],
            'action_infos': []
        }
    
    def get_task_statistics(self):
        """获取任务分布统计"""
        return {
            task_type: {
                'episodes': len(buffer),
                'total_collected': self.task_counts[task_type]
            }
            for task_type, buffer in self.task_buffers.items()
        }


class PPOTrainer(BaseTrainer):
    """PPO trainer implementation with enhanced GPT-4o-mini distillation"""
    
    def __init__(self, env: 'MDPEnvironment', config: Dict[str, Any]):
        super().__init__(env, config)
        
        # PPO基本参数 - 必须在使用前初始化
        self.gamma = config.get('gamma', 0.99)
        self.gae_lambda = config.get('gae_lambda', 0.95)
        self.n_steps = config.get('n_steps', 2048)
        self.n_epochs = config.get('n_epochs', 10)
        self.batch_size = config.get('batch_size', 64)
        self.clip_range = config.get('clip_range', 0.2)
        self.clip_range_vf = config.get('clip_range_vf', None)
        self.ent_coef = config.get('ent_coef', 0.01)
        self.vf_coef = config.get('vf_coef', 0.5)
        self.max_grad_norm = config.get('max_grad_norm', 0.5)
        
        # Network
        state_dim = env.get_state_dim()
        action_dim = env.num_actions
        
        # 创建网络配置
        network_config = {
            'hidden_dim': config.get('hidden_dim', 256),
            'num_layers': config.get('num_layers', 3),
            'num_heads': config.get('num_heads', 4),
            'dropout': config.get('dropout', 0.1),
            'use_pre_norm': config.get('use_pre_norm', True),
            'use_auxiliary_tasks': config.get('use_auxiliary_tasks', False),
            'use_curiosity': config.get('use_curiosity', False),
            'spectral_norm': config.get('spectral_norm', False),
            'rag_dim': config.get('rag_dim', 64),
            'use_mac_optimization': config.get('use_mac_optimization', False),
            'use_rag_enhancement': config.get('use_rag_enhancement', True),
            'use_tools_input': config.get('use_tools_input', True),
            'tools_dim': config.get('tools_dim', 64),
            'num_tools': config.get('num_tools', action_dim)
        }
        
        print(f"[PPOTrainer.__init__] Creating ActorCriticNetwork with config: use_rag_enhancement={network_config['use_rag_enhancement']}")
        
        # 创建ActorCriticNetwork实例
        self.network = ActorCriticNetwork(state_dim, action_dim, network_config)
        self.network.to(self.device)
        
        try:
            from apex.optimizers import FusedAdam
            self.optimizer = FusedAdam(
                self.network.parameters(),
                lr=self.learning_rate,
                betas=(0.9, 0.999),
                eps=1e-8,
                weight_decay=self.config.get('weight_decay', 0.0)
            )
            logger.info("✓ Using FusedAdam optimizer (faster on V100)")
        except ImportError:
            # 如果没有安装 apex，退回到标准 Adam
            self.optimizer = torch.optim.Adam(
                self.network.parameters(),
                lr=self.learning_rate,
                betas=(0.9, 0.999),
                eps=1e-8
            )
            logger.warning("FusedAdam not available, using standard Adam")   

        def create_scheduler(optimizer, config):
            warmup_steps = config.get('lr_warmup_steps', 100)
            total_steps = config.get('total_training_steps', 10000)
            
            def lr_lambda(step):
                if step < warmup_steps:
                    # Warm-up 阶段：线性增长
                    return float(step) / float(max(1, warmup_steps))
                else:
                    # Cosine 退火阶段
                    progress = float(step - warmup_steps) / float(max(1, total_steps - warmup_steps))
                    return 0.5 * (1.0 + math.cos(math.pi * progress))
            
            return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

        # 使用
        self.lr_scheduler = create_scheduler(self.optimizer, self.config)

            
        # PPO specific parameters
        use_task_aware_buffer = config.get('use_task_aware_buffer', True)
        if use_task_aware_buffer:
            self.rollout_buffer = TaskAwareRolloutBuffer(
                capacity_per_task=config.get('buffer_capacity_per_task', 100),
                min_episodes_per_task=config.get('min_episodes_per_task', 5)
            )
        else:
            self.rollout_buffer = RolloutBuffer(gamma=self.gamma)
            
        # Tracking
        self.current_learning_rate = config.get('learning_rate', 3e-4)
        self.current_task_type = None
        
        # 增强的Teacher guidance参数
        self.use_teacher_guidance = config.get('use_teacher_guidance', True)
        self.teacher_guidance_prob = config.get('teacher_guidance_start_prob', 0.5)
        self.teacher_guidance_decay = config.get('teacher_guidance_decay', 0.995)
        self.teacher_guidance_min_prob = config.get('teacher_guidance_min_prob', 0.05)
        
        # GPT-4o-mini蒸馏参数
        self.use_distillation = config.get('use_distillation', True)
        self.distillation_weight = config.get('distillation_weight', 0.1)
        self.distillation_temperature = config.get('distillation_temperature', 2.0)
        self.teacher_model_name = config.get('teacher_model_name', 'gpt-4o-mini')
        
        # 并发参数
        self.distillation_batch_size = config.get('distillation_batch_size', 10)
        self.max_concurrent_requests = config.get('max_concurrent_requests', 100)
        self.request_timeout = config.get('request_timeout', 10)
        
        # Soft guidance参数
        self.use_soft_guidance = config.get('use_soft_guidance', True)
        self.guidance_temperature = config.get('guidance_temperature', 0.5)
        self.guidance_blend_factor = config.get('guidance_blend_factor', 0.7)
        
        # 自适应guidance
        self.adaptive_guidance = config.get('adaptive_guidance', True)
        self.task_difficulty_scores = {}
        self.model_confidence_threshold = 0.8
        self.llm_client = None
        
        # Episode-level guidance
        self.episode_guidance_mode = config.get('episode_guidance_mode', True)
        self.current_episode_workflow = None
        self.workflow_cache = {}
        self.max_cache_size = 100
        
        # 初始化蒸馏缓存
        self.distillation_cache = EmbeddingDistillationCache(
            cache_dir=config.get('cache_dir', '.distillation_cache'),
            max_size=config.get('cache_size', 10000),
            similarity_threshold=config.get('cache_similarity_threshold', 0.9)
        )
        
        self.cache_lock = threading.RLock()  # 使用可重入锁

        # 初始化工具信息
        self._initialize_tool_info()
        
        # 初始化LLM客户端
        if self.use_teacher_guidance or self.use_distillation:
            self._init_llm_client()
            print(f"[PPOTrainer] Teacher guidance enabled with model: {self.teacher_model_name}")


    def _initialize_tool_info(self):
        """初始化工具信息供teacher使用"""
        self.tool_info = {}
        self.tool_embeddings = {}
        self.tool_categories = {}
        self.tool_dependencies = {}
        
        # 从环境获取工具信息
        if hasattr(self.env, 'action_space'):
            for i, action in enumerate(self.env.action_space):
                # 获取工具名称，处理特殊动作类型
                tool_name = None
                if hasattr(action, 'tool_name'):
                    tool_name = action.tool_name
                elif hasattr(action, 'action_type'):
                    # 特殊动作类型使用action_type作为名称
                    tool_name = str(action.action_type.value) if hasattr(action.action_type, 'value') else str(action.action_type)
                
                if tool_name is None:
                    # 如果还是None，使用索引作为名称
                    tool_name = f"action_{i}"
                    print(f"[PPOTrainer] WARNING: Action at index {i} has no identifiable name, using '{tool_name}'")
                
                self.tool_info[i] = {
                    'name': tool_name,
                    'index': i,
                    'description': getattr(action, 'description', ''),
                    'category': getattr(action, 'category', 'general'),
                    'parameters': getattr(action, 'parameters', []),
                    'returns': getattr(action, 'returns', []),
                    'dependencies': getattr(action, 'dependencies', [])
                }
                
                # 按类别分组
                category = self.tool_info[i]['category']
                if category not in self.tool_categories:
                    self.tool_categories[category] = []
                self.tool_categories[category].append(i)
                
                # 记录依赖关系
                if self.tool_info[i]['dependencies']:
                    self.tool_dependencies[tool_name] = self.tool_info[i]['dependencies']
        
        print(f"[PPOTrainer] Initialized {len(self.tool_info)} tools")
    
        # 打印特殊动作信息
        special_actions = [(i, info) for i, info in self.tool_info.items() 
                        if info['name'].startswith('action_') or 
                        info['name'] in ['NO_OP', 'CREATE_CHECKPOINT', 'RECOVER_ERROR', 'RESTORE_CHECKPOINT']]
        if special_actions:
            print(f"[PPOTrainer] Special actions found: {[info['name'] for _, info in special_actions]}")
            
        # 如果有embedding manager，获取工具embeddings
        if hasattr(self.env, 'mdp') and hasattr(self.env.mdp, 'embedding_manager'):
            embedding_manager = self.env.mdp.embedding_manager
            for i, tool_info in self.tool_info.items():
                tool_name = tool_info['name']
                if hasattr(embedding_manager, 'tool_embeddings') and tool_name in embedding_manager.tool_embeddings:
                    tool_embedding = embedding_manager.tool_embeddings[tool_name]
                    if hasattr(tool_embedding, 'combined_embedding'):
                        self.tool_embeddings[i] = tool_embedding.combined_embedding
        else:
            raise ValueError("No embedding manager")
        
        print(f"[PPOTrainer] Initialized {len(self.tool_info)} tools with {len(self.tool_embeddings)} embeddings")
        print(f"[PPOTrainer] Tool categories: {list(self.tool_categories.keys())}")


            
    def store_experience(self, state: np.ndarray, action: int, reward: float,  # <- 新增：实现统一接口
                        next_state: np.ndarray, done: bool, **kwargs) -> None:
        """Store experience using store_transition"""
        # PPO不需要next_state，直接调用原有的store_transition
        self.store_transition(state, action, reward, done)
    
    def should_train(self) -> bool:  # <- 新增：判断是否应该训练
        """PPO trains every n_steps"""
        return self.total_timesteps > 0 and self.total_timesteps % self.n_steps == 0
    
    def on_episode_end(self) -> None:  # <- 新增：episode结束处理
        """PPO needs to handle episode end for TaskAwareRolloutBuffer"""
        if isinstance(self.rollout_buffer, TaskAwareRolloutBuffer):
            self.rollout_buffer.store_episode()
    
    def _init_llm_client(self):
        """Initialize LLM client for teacher guidance"""
        from api_client_manager import get_api_client, get_model_name
        self.llm_client = get_api_client()
        self.model_name = get_model_name()
        logger.info(f"LLM client initialized for teacher guidance using model: {self.model_name}")

    
    def set_eval_mode(self, eval_mode: bool):  # <- 新增：重写基类方法
        """Set evaluation mode - disable teacher guidance"""
        super().set_eval_mode(eval_mode)
        if eval_mode:
            self.stored_teacher_prob = self.teacher_guidance_prob
            self.teacher_guidance_prob = 0.0
        else:
            if hasattr(self, 'stored_teacher_prob'):
                self.teacher_guidance_prob = self.stored_teacher_prob


    def select_action(self, state: np.ndarray, valid_actions: Optional[List[int]] = None) -> int:
        """Select action using policy network with RAG enhancement and required_tools"""
        # Episode-level workflow guidance
        
        # if (self.use_teacher_guidance and 
        #     self.episode_guidance_mode and 
        #     not self.eval_mode and
        #     hasattr(self.env, 'episode_steps') and 
        #     self.env.episode_steps == 0):
        #     self._get_episode_workflow_guidance()
        
        # Get teacher action if using guidance
        teacher_action = None
        teacher_flag = random.random()
        self.use_teacher_guidance = False
        if self.use_teacher_guidance and not self.eval_mode and teacher_flag < self.teacher_guidance_prob:
            print("使用教师指导模式")
            if self.episode_guidance_mode and self.current_episode_workflow:
                teacher_action = self._get_next_workflow_action(valid_actions)
            if teacher_action is None:
                teacher_action = self._get_teacher_action(state, valid_actions)
        else:
            print(self.teacher_guidance_prob)
            # raise ValueError("No teacher guidance, the flag is ", teacher_flag)
            
        
        # 准备RAG embedding
        rag_embedding = None
        if hasattr(self.env, 'last_rag_context') and self.env.last_rag_context:
            rag_embedding = self.env._encode_rag_embedding(self.env.last_rag_context)
            rag_tensor = torch.FloatTensor(rag_embedding).unsqueeze(0).to(self.device)
        else:
            rag_tensor = torch.zeros(1, self.config.get('rag_dim', 64)).to(self.device)
        
        # 准备required_tools embedding
        required_tools_tensor = None
        if hasattr(self.env, 'current_task_info') and self.env.current_task_info:
            required_tools = self.env.current_task_info.get('required_tools', [])
            if required_tools and hasattr(self.network, 'tools_projection'):
                # 获取embedding_manager
                embedding_manager = None
                if hasattr(self.env, 'mdp') and hasattr(self.env.mdp, 'embedding_manager'):
                    embedding_manager = self.env.mdp.embedding_manager
                
                # 获取网络期望的tools维度
                target_tools_dim = getattr(self.network, 'tools_dim', 64)
                
                # 使用embedding方法编码required_tools
                required_tools_embedding = encode_required_tools_embedding(
                    required_tools,
                    embedding_manager,
                    target_dim=target_tools_dim  # 传入目标维度
                )
                required_tools_tensor = torch.FloatTensor(required_tools_embedding).unsqueeze(0).to(self.device)
                logger.debug(f" Encoded {len(required_tools)} required tools with target dim={target_tools_dim}")
        else:
            logger.debug(f" No required tools found, using zero vector")
            if hasattr(self.network, 'tools_projection'):
                tools_dim = getattr(self.network, 'tools_dim', 64)
                required_tools_tensor = torch.zeros(1, tools_dim).to(self.device)
        
        # 如果网络支持tools输入但没有required_tools，创建零向量
        if required_tools_tensor is None and hasattr(self.network, 'tools_projection'):
            raise ValueError("Network supports tools input but no required_tools provided")
            logger.debug(f" No required tools provided, using zero vector for tools input")
            required_tools_tensor = torch.zeros(1, getattr(self.network, 'tools_dim', 64)).to(self.device)
        
        # 如果网络支持tools输入但没有required_tools，创建零向量

        # Get policy action with RAG and required_tools
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            
            # 根据网络能力调用forward
            if hasattr(self.network, 'tools_projection') and required_tools_tensor is not None:
                # 新版网络，支持三个输入
                logits, value = self.network(state_tensor, rag_tensor, required_tools_tensor)
                logger.debug(f" Using network with RAG and tools embedding input")
            elif hasattr(self.network, 'rag_projection'):
                # 中版网络，只支持RAG
                logits, value = self.network(state_tensor, rag_tensor)
                logger.debug(f" Using network with RAG input only")
            else:
                # 旧版网络，只支持state
                logits, value = self.network(state_tensor)
                print("[WARNING] Network doesn't support RAG or tools input")
            
            # 使用基类的数值稳定化
            if hasattr(self, '_stabilize_logits'):
                logits = self._stabilize_logits(logits)
            
            # Apply action masking if provided
            if valid_actions is not None:
                mask = torch.ones_like(logits[0]) * float('-inf')
                mask[valid_actions] = 0
                logits = logits + mask.unsqueeze(0)
            
            # 创建动作分布
            probs = F.softmax(logits, dim=-1)
            dist = torch.distributions.Categorical(probs)
            
            # 采样或使用教师动作
            if teacher_action is not None:
                action = teacher_action
            else:
                # 普通的动作选择逻辑
                with torch.no_grad():
                    # 调用网络前向传播
                    if hasattr(self.network, 'tools_projection'):
                        logits, value = self.network(state_tensor, rag_tensor, required_tools_tensor)
                    elif hasattr(self.network, 'rag_projection'):
                        logits, value = self.network(state_tensor, rag_tensor)
                    else:
                        logits, value = self.network(state_tensor)
                    
                    # 应用动作掩码并选择动作
                    if valid_actions is not None:
                        mask = torch.zeros_like(logits[0])
                        mask[valid_actions] = 1
                        masked_logits = logits[0] + (mask - 1) * 1e8
                        probs = torch.softmax(masked_logits, dim=0)
                    else:
                        probs = torch.softmax(logits[0], dim=0)
                    
                    dist = torch.distributions.Categorical(probs)
                    action = dist.sample().item()
                    log_prob = dist.log_prob(torch.tensor(action, device=self.device))

                    
                    # 存储value和log_prob供后续使用
                    self.last_value = value.item() if value.dim() == 0 else value[0].item()
                    self.last_log_prob = log_prob.item()
                    self.last_rag_embedding = rag_embedding
                
            return action  # 只返回选择的动作


    def _get_episode_workflow_guidance(self):
        """获取整个episode的workflow指导"""
        if not self.llm_client or not hasattr(self.env, 'current_task'):
            print("[_get_episode_workflow_guidance] Missing llm_client or current_task")
            return
        
        current_task = self.env.current_task
        # 使用getattr安全访问，优先使用description
        task_description = getattr(current_task, 'description', getattr(current_task, 'task_objective', 'Unknown task'))
        task_key = f"{current_task.task_type}_{task_description[:50]}"
        
        # 检查缓存
        if task_key in self.workflow_cache:
            self.current_episode_workflow = self.workflow_cache[task_key].copy()
            self.env.workflow_position = 0
            print(f"[_get_episode_workflow_guidance] Using cached workflow for {task_key}")
            return
        
        # 构建更友好的prompt以避免触发内容过滤
        prompt = f"""I need help planning a workflow for a data processing task. Here are the details:

    Task Category: {current_task.task_type}
    Task Goal: {task_description}

    I have these tools available to use:
    {', '.join(list(self.env.tool_registry.keys()))}

    Could you suggest a good sequence of tools to accomplish this task? Please provide your recommendation as a structured list in JSON format.

    For example, if I were processing CSV data, a good sequence might be:
    ["data_reader", "validator", "transformer", "csv_writer"]

    Please consider:
    - Which tools naturally follow each other
    - Data flow between tools
    - The specific requirements of this task type

    Your suggested tool sequence:"""
        
        # 处理API调用
        workflow = []
        content = ""
        
        # API调用
        response = self.llm_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant specializing in data processing workflows. You help users plan efficient tool execution sequences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_completion_tokens=200
        )
        
        # 解析响应
        content = response.choices[0].message.content.strip()
        
        # 添加调试日志
        print(f"[_get_episode_workflow_guidance] LLM response received, length: {len(content)}")
        
        # 验证响应内容
        if not content:
            print("[_get_episode_workflow_guidance] Empty response from LLM")
            workflow = []
        else:
            # 查找JSON数组模式 - 匹配 [...] 格式
            json_pattern = r'\[\s*(?:"[^"]+"\s*(?:,\s*"[^"]+"\s*)*)?\]'
            json_match = re.search(json_pattern, content)
            
            if json_match:
                json_str = json_match.group(0)
                # 再次验证是否为有效JSON
                if json_str.startswith('[') and json_str.endswith(']'):
                    # 解析JSON
                    print(f"[_get_episode_workflow_guidance] Parsing JSON: {json_str[:100]}...")
                    workflow = json.loads(json_str)
                    logger.debug(f"Extracted workflow: {workflow}")
                else:
                    logger.warning(f"Invalid JSON format in LLM response: {json_str}")
                    print(f"[_get_episode_workflow_guidance] Invalid JSON format")
                    workflow = []
            else:
                logger.warning(f"No JSON array found in LLM response: {content[:200]}")
                print(f"[_get_episode_workflow_guidance] No JSON array found")
                workflow = []
        
        # 确保workflow是列表
        if not isinstance(workflow, list):
            logger.warning(f"Workflow is not a list: {type(workflow)}")
            print(f"[_get_episode_workflow_guidance] Workflow is not a list, resetting")
            workflow = []
        
        # 验证工具名称
        valid_tools = set(self.env.tool_registry.keys())
        validated_workflow = []
        for tool in workflow:
            if isinstance(tool, str) and tool in valid_tools:
                validated_workflow.append(tool)
            else:
                logger.debug(f"Skipping invalid tool: {tool}")
                print(f"[_get_episode_workflow_guidance] Skipping invalid tool: {tool}")
        
        workflow = validated_workflow
        
        # 缓存结果
        if len(self.workflow_cache) >= self.max_cache_size:
            # 移除最旧的条目
            self.workflow_cache.pop(next(iter(self.workflow_cache)))
        
        self.workflow_cache[task_key] = workflow
        self.current_episode_workflow = workflow.copy()
        self.env.workflow_position = 0
        
        logger.debug(f"Generated workflow guidance: {workflow}")
        print(f"[_get_episode_workflow_guidance] Final workflow: {workflow}")
    
    def _get_next_workflow_action(self, valid_actions: Optional[List[int]]) -> Optional[int]:
        """根据workflow建议获取下一个动作"""
        if not self.current_episode_workflow or not hasattr(self.env, 'workflow_position'):
            print("[_get_next_workflow_action] No workflow or position")
            return None
        
        # 检查是否还有建议的工具
        if self.env.workflow_position >= len(self.current_episode_workflow):
            print("[_get_next_workflow_action] Workflow position exceeded")
            return None
        
        # 获取下一个建议的工具
        suggested_tool = self.current_episode_workflow[self.env.workflow_position]
        print(f"[_get_next_workflow_action] Suggesting tool: {suggested_tool}")
        
        # 查找对应的动作
        for idx, action in enumerate(self.env.action_space):
            if (hasattr(action, 'tool_name') and 
                action.tool_name == suggested_tool and
                action.action_type.value == 'invoke_tool'):
                
                # 验证动作有效性
                if valid_actions is None or idx in valid_actions:
                    self.env.workflow_position += 1  # 移动到下一个工具
                    print(f"[_get_next_workflow_action] Found action {idx} for tool {suggested_tool}")
                    return idx
        
        # 如果建议的工具不可用，跳过
        print(f"[_get_next_workflow_action] Tool {suggested_tool} not available, skipping")
        self.env.workflow_position += 1
        return self._get_next_workflow_action(valid_actions)  # 递归尝试下一个


    def _get_teacher_action(self, state: np.ndarray, valid_actions: Optional[List[int]] = None) -> Optional[int]:
        """获取RAG增强的LLM教师动作建议，包含工具信息"""
        if not self.llm_client or not hasattr(self.env, 'current_state'):
            return None
        
        # 构建当前状态的描述
        current_state = self.env.current_state
        task_desc = current_state.task_objective if hasattr(current_state, 'task_objective') else "Complete the task"
        
        # 获取已执行的工具
        executed_tools = []
        if hasattr(current_state, 'execution_sequence'):
            for item in current_state.execution_sequence:
                if isinstance(item, str):
                    executed_tools.append(item)
                elif hasattr(item, 'tool_name'):
                    executed_tools.append(item.tool_name)
        
        # 获取当前任务类型
        task_type = getattr(current_state, 'task_type', 'general')
        
        # 获取required_tools信息
        required_tools = []
        remaining_required_tools = []
        if hasattr(self.env, 'current_task_info') and self.env.current_task_info:
            required_tools = self.env.current_task_info.get('required_tools', [])
            if required_tools:
                executed_set = set(executed_tools)
                remaining_required_tools = [tool for tool in required_tools if tool not in executed_set]
        
        # 初始化RAG增强部分
        rag_enhancement = ""
        
        # 1. 获取语义相似的工具（使用RAG）
        if hasattr(self.env, 'last_rag_context') and self.env.last_rag_context:
            rag_enhancement += "\n## Semantically Related Tools (from RAG):\n"
            for operation, results in self.env.last_rag_context.items():
                if results:
                    top_tools = []
                    for result in results[:3]:
                        if hasattr(result, 'tool_name') and hasattr(result, 'score'):
                            # 找到工具的索引
                            tool_idx = None
                            for idx, info in self.tool_info.items():
                                if info['name'] == result.tool_name:
                                    tool_idx = idx
                                    break
                            if tool_idx is not None:
                                top_tools.append(f"{tool_idx}:{result.tool_name} (score:{result.score:.3f})")
                    if top_tools:
                        rag_enhancement += f"- {operation}: {', '.join(top_tools)}\n"
        
        # 2. 添加工具类别信息
        relevant_categories = set()
        if task_type == 'data_pipeline':
            relevant_categories = {'data', 'transform', 'io'}
        elif task_type == 'api_integration':
            relevant_categories = {'api', 'network', 'integration'}
        elif task_type == 'basic_task':
            relevant_categories = {'file', 'io', 'process', 'basic', 'simple'}
        
        # 3. 构建可用工具的详细描述
        tool_descriptions = []
        for i in (valid_actions or range(len(self.tool_info))):
            if i in self.tool_info:
                info = self.tool_info[i]
                # 检查依赖关系
                deps_met = True
                if info['dependencies']:
                    deps_met = all(dep in executed_tools for dep in info['dependencies'])
                
                # 计算优先级分数
                priority = 0
                if info['name'] in remaining_required_tools:
                    priority = 10  # 最高优先级给required tools
                elif info['category'] in relevant_categories:
                    priority = 5
                if not deps_met:
                    priority = -5  # 依赖未满足的降低优先级
                
                desc = f"{i}: {info['name']} [{info['category']}]"
                if info['description']:
                    desc += f" - {info['description'][:50]}..."
                if info['dependencies']:
                    desc += f" (requires: {', '.join(info['dependencies'])})"
                if priority > 0:
                    desc += f" [Priority: {priority}]"
                
                tool_descriptions.append((priority, desc))
        
        # 按优先级排序
        tool_descriptions.sort(key=lambda x: -x[0])
        tool_desc_text = "\n".join([desc for _, desc in tool_descriptions])
        
        # 构建增强的prompt
        prompt = f"""You are an expert workflow optimizer with complete knowledge of available tools.

        Current Task: {task_desc}
        Task Type: {task_type}
        
        Executed Tools: {executed_tools}
        Required Tools: {required_tools}
        Remaining Required: {remaining_required_tools}
        
        {rag_enhancement}
        
        Available Tools (with priorities):
        {tool_desc_text}
        
        Tool Categories Available: {', '.join(self.tool_categories.keys())}
        
        Consider:
        1. **PRIORITY: Execute remaining required tools first** - these are mandatory
        2. Tool dependencies - some tools require others to be executed first
        3. Logical workflow order based on data flow
        4. Semantic similarity from RAG results
        5. Task type alignment with tool categories
        
        Return ONLY the action index number. Prioritize required tools."""

        # 调用LLM
        try:
            response = self.llm_client.chat.completions.create(
                model=self.teacher_model_name,
                messages=[
                    {"role": "system", "content": "You are an expert in workflow optimization. You have complete knowledge of all available tools and their relationships."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=10
            )
            
            # 解析响应
            content = response.choices[0].message.content.strip()
            match = re.search(r'\d+', content)
            if not match:
                logger.debug("No valid action index found in teacher response")
                return None
            
            action_idx = int(match.group())
            
            # 验证动作有效性
            if valid_actions and action_idx not in valid_actions:
                logger.debug(f"Teacher suggested invalid action {action_idx}")
                return None
            if action_idx >= len(self.env.action_space):
                logger.debug(f"Teacher suggested out-of-range action {action_idx}")
                return None
            
            logger.debug(f"Teacher selected action {action_idx} ({self.tool_info.get(action_idx, {}).get('name', 'unknown')})")
            return action_idx
            
        except Exception as e:
            logger.error(f"Teacher guidance failed: {e}")
            return None


    def _get_single_teacher_action(self, request: Dict) -> int:
        """获取单个状态的teacher推荐动作，利用embedding缓存"""
        task_desc = request['task_desc']
        tool_list = request['tool_list']
        executed_tools = request.get('executed_tools', [])
        required_tools = request.get('required_tools', [])
        rag_context = request.get('rag_context', None)

        with self.cache_lock:
            # 检查缓存
            cached_action = self.distillation_cache.get(task_desc, tool_list, rag_context)
            if cached_action is not None:
                if isinstance(cached_action, dict) and len(cached_action) == 1:
                    action_idx = int(list(cached_action.keys())[0])
                    print(f"[PPOTrainer._get_single_teacher_action] Cache hit! Returning action {action_idx}")
                    return action_idx
                elif isinstance(cached_action, (int, float)):
                    print(f"[PPOTrainer._get_single_teacher_action] Cache hit! Returning action {int(cached_action)}")
                    return int(cached_action)
        
        # 使用EmbeddingDistillationCache进行语义相似度搜索
        # 注意：缓存中存储的是动作索引而非分布
        cached_action = self.distillation_cache.get(task_desc, tool_list, rag_context)
        if cached_action is not None:
            # 缓存命中，直接返回动作
            if isinstance(cached_action, dict) and len(cached_action) == 1:
                # 如果缓存的是单动作的dict格式 {"action_idx": 1.0}
                action_idx = int(list(cached_action.keys())[0])
                print(f"[PPOTrainer._get_single_teacher_action] Cache hit! Returning action {action_idx}")
                return action_idx
            elif isinstance(cached_action, (int, float)):
                # 如果直接缓存的是动作索引
                print(f"[PPOTrainer._get_single_teacher_action] Cache hit! Returning action {int(cached_action)}")
                return int(cached_action)
        
        # 构建prompt - 保持简洁
        tools_info = []
        for i, tool_name in enumerate(tool_list):
            status = "✓" if tool_name in executed_tools else "○"
            required = " [REQUIRED]" if tool_name in required_tools else ""
            tools_info.append(f"{i}: {tool_name} {status}{required}")
        
        # RAG信息 - 充分利用语义搜索结果
        rag_info = ""
        rag_top_suggestions = {}  # 记录每个操作的最佳工具
        
        if rag_context:
            rag_suggestions = []
            for operation, results in rag_context.items():
                if results:
                    # 获取得分最高的工具
                    top_tools = []
                    for r in results[:3]:
                        if hasattr(r, 'tool_name') and hasattr(r, 'score'):
                            top_tools.append((r.tool_name, r.score))
                            # 记录每个操作的最佳工具
                            if operation not in rag_top_suggestions or r.score > rag_top_suggestions[operation][1]:
                                # 找到工具索引
                                try:
                                    tool_idx = tool_list.index(r.tool_name)
                                    rag_top_suggestions[operation] = (tool_idx, r.score)
                                except ValueError:
                                    pass
                    
                    if top_tools:
                        tool_info_str = ', '.join([f"{name}({score:.2f})" for name, score in top_tools])
                        rag_suggestions.append(f"{operation}: {tool_info_str}")
            
            if rag_suggestions:
                rag_info = f"\n\nRAG Semantic Suggestions:\n" + "\n".join(rag_suggestions)
        
        # 找出剩余的必需工具
        remaining_required = [t for t in required_tools if t not in executed_tools]
        
        # 如果有明确的RAG建议且是必需工具，可以直接使用
        if remaining_required and rag_top_suggestions:
            for req_tool in remaining_required:
                try:
                    req_idx = tool_list.index(req_tool)
                    # 检查这个必需工具是否在RAG建议中
                    for op, (suggested_idx, score) in rag_top_suggestions.items():
                        if suggested_idx == req_idx and score > 0.8:  # 高置信度
                            print(f"[PPOTrainer._get_single_teacher_action] High-confidence RAG suggestion for required tool: {req_tool} (score: {score})")
                            # 缓存这个决策
                            self.distillation_cache.put(task_desc, tool_list, {str(req_idx): 1.0}, rag_context)
                            return req_idx
                except ValueError:
                    pass
        
        prompt = f"""Task: {task_desc}

    Available Tools:
    {chr(10).join(tools_info)}

    Executed: {executed_tools}
    Remaining Required: {remaining_required}{rag_info}

    Based on:
    1. Required tools that MUST be executed
    2. Logical workflow dependencies
    3. RAG semantic suggestions above

    Select the BEST next tool index (0-{len(tool_list)-1}). Return ONLY the number!!!!! Don't return anything else!!!!!"""

        print(f"[PPOTrainer._get_single_teacher_action] Making API call for task: {task_desc[:50]}...")
        
        # API调用
        response = self.llm_client.chat.completions.create(
            model="gpt-4o-mini",
            # model="o4-mini",
            messages=[
                {"role": "system", "content": "You are a workflow optimization expert. Analyze the semantic suggestions and required tools to select the optimal next action. Return only a number."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=50,
            timeout=self.request_timeout
        )
        
        content = response.choices[0].message.content.strip()
        print(f"[PPOTrainer._get_single_teacher_action] Raw response: {content}")
        
        # 提取数字
        import re
        match = re.search(r'\d+', content)
        if not match:
            print(f"[PPOTrainer._get_single_teacher_action] ERROR: No number found in response")
            raise ValueError(f"Invalid action response: {content}")
        
        action_idx = int(match.group())
        
        # 验证动作有效性
        if action_idx < 0 or action_idx >= self.env.num_actions:
            print(f"[PPOTrainer._get_single_teacher_action] ERROR: Action {action_idx} out of range")
            raise ValueError(f"Action index {action_idx} out of range")
        
        # 缓存结果 - 使用EmbeddingDistillationCache的语义缓存
        # 存储为单动作的分布格式以兼容现有缓存结构
        with self.cache_lock:
            self.distillation_cache.put(task_desc, tool_list, {str(action_idx): 1.0}, rag_context)
        
        print(f"[PPOTrainer._get_single_teacher_action] Selected action: {action_idx} ({tool_list[action_idx] if action_idx < len(tool_list) else 'unknown'})")
        return action_idx


    def _get_teacher_distributions_batch(self, states: np.ndarray, 
                                        valid_actions_list: Optional[List[List[int]]] = None) -> torch.Tensor:
        """批量获取teacher分布，通过收集单个动作构建，充分利用RAG"""
        batch_size = min(len(states), self.distillation_batch_size)
        
        print(f"[PPOTrainer._get_teacher_distributions_batch] Processing {batch_size} states with RAG enhancement")
        
        # 准备所有请求参数
        requests = []
        for i in range(batch_size):
            state = states[i]
            
            # 获取状态信息
            task_desc = "Complete the task"
            executed_tools = []
            required_tools = []
            tool_list = list(self.env.tool_registry.keys())
            
            # 从current_state获取信息
            if hasattr(self.env, 'current_state'):
                current_state = self.env.current_state
                if hasattr(current_state, 'task_objective'):
                    task_desc = current_state.task_objective
                
                # 获取已执行的工具
                if hasattr(current_state, 'execution_sequence'):
                    for item in current_state.execution_sequence:
                        if isinstance(item, str):
                            executed_tools.append(item)
                        elif hasattr(item, 'tool_name'):
                            executed_tools.append(item.tool_name)
                
                # 获取必需的工具
                if hasattr(self.env, 'current_task_info') and self.env.current_task_info:
                    required_tools = self.env.current_task_info.get('required_tools', [])
            
            # 获取RAG context - 这是关键！
            rag_context = None
            if hasattr(self.env, 'last_rag_context'):
                rag_context = self.env.last_rag_context
                print(f"[PPOTrainer._get_teacher_distributions_batch] State {i} has RAG context with {len(rag_context)} operations")
            elif hasattr(current_state, 'rag_search_results'):
                # 备用：从state中获取
                rag_context = current_state.rag_search_results
            
            requests.append({
                'task_desc': task_desc,
                'tool_list': tool_list,
                'executed_tools': executed_tools,
                'required_tools': required_tools,
                'rag_context': rag_context  # 传递RAG上下文！
            })
        
        # 使用线程池并发执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_requests) as executor:
            # 提交所有任务
            future_to_request = {
                executor.submit(self._get_single_teacher_action, req): i 
                for i, req in enumerate(requests)
            }
            
            # 收集结果 - 保持顺序
            results = [None] * len(requests)
            
            for future in concurrent.futures.as_completed(future_to_request):
                request_idx = future_to_request[future]
                try:
                    action = future.result(timeout=self.request_timeout)
                    results[request_idx] = action
                    print(f"[PPOTrainer._get_teacher_distributions_batch] Got action {action} for request {request_idx}")
                except Exception as e:
                    print(f"[PPOTrainer._get_teacher_distributions_batch] ERROR for request {request_idx}: {e}")
                    raise
        
        # 将动作转换为分布
        print(f"[PPOTrainer._get_teacher_distributions_batch] Converting {len(results)} actions to distributions")
        
        teacher_distributions = []
        for i, action in enumerate(results):
            if action is None:
                print(f"[PPOTrainer._get_teacher_distributions_batch] ERROR: Missing action for index {i}")
                raise ValueError(f"Failed to get teacher action for state {i}")
            
            # 创建分布 - 可以是one-hot或smoothed
            distribution = torch.zeros(self.env.num_actions)
            
            # 方案1：One-hot分布
            # distribution[action] = 1.0
            
            # 方案2：Smoothed分布（推荐）
            smoothing_epsilon = 0.1
            distribution.fill_(smoothing_epsilon / self.env.num_actions)
            distribution[action] = 1.0 - smoothing_epsilon + smoothing_epsilon / self.env.num_actions
            
            # 如果有RAG context，可以根据语义相似度进一步调整分布
            if i < len(requests) and requests[i]['rag_context']:
                rag_context = requests[i]['rag_context']
                tool_list = requests[i]['tool_list']
                
                # 为语义相关的工具分配少量概率
                for operation, results in rag_context.items():
                    for result in results[:3]:  # top-3
                        if hasattr(result, 'tool_name') and hasattr(result, 'score'):
                            try:
                                tool_idx = tool_list.index(result.tool_name)
                                if tool_idx != action:  # 不是主要动作
                                    # 根据语义得分分配小概率
                                    bonus_prob = result.score * 0.05  # 最多5%的额外概率
                                    distribution[tool_idx] += bonus_prob
                            except ValueError:
                                pass
                
                # 重新归一化
                distribution = distribution / distribution.sum()
            
            teacher_distributions.append(distribution)
        
        print(f"[PPOTrainer._get_teacher_distributions_batch] Created {len(teacher_distributions)} distributions with RAG enhancement")
        return torch.stack(teacher_distributions)
    
    def store_transition(self, state: np.ndarray, action: int, reward: float, done: bool):
        """Store transition in rollout buffer with RAG embedding，添加数据验证"""
        # 验证输入数据
        if state is None or (isinstance(state, np.ndarray) and state.size == 0):
            print(f"[PPOTrainer.store_transition] ERROR: Invalid state")
            return
        
        if not hasattr(self, 'last_value') or not hasattr(self, 'last_log_prob'):
            print(f"[PPOTrainer.store_transition] ERROR: Missing last_value or last_log_prob")
            return
        
        # 设置任务类型（如果是TaskAwareRolloutBuffer）
        if isinstance(self.rollout_buffer, TaskAwareRolloutBuffer) and hasattr(self.env, 'current_task'):
            if self.env.episode_steps == 0:
                task_type = getattr(self.env.current_task, 'task_type', 'default')
                self.rollout_buffer.set_task_type(task_type)
                self.current_task_type = task_type
        
        # 获取RAG embedding
        rag_embedding = None
        if hasattr(self, 'last_rag_embedding'):
            rag_embedding = self.last_rag_embedding
        elif hasattr(self.env, 'last_rag_context'):
            # 如果没有预计算的embedding，现场计算
            rag_embedding = self.env._encode_rag_embedding(self.env.last_rag_context)
        
        # 获取动作信息
        action_info = None
        if hasattr(self.env, 'action_space') and action < len(self.env.action_space):
            action_obj = self.env.action_space[action]
            if hasattr(action_obj, '__dict__'):
                action_info = {
                    'tool_name': getattr(action_obj, 'tool_name', None),
                    'semantic_score': getattr(action_obj, 'semantic_score', 0.0),
                    'search_source': getattr(action_obj, 'search_source', 'rule_based'),
                    'confidence': getattr(action_obj, 'confidence', 1.0)
                }
        
        # Store the transition with RAG embedding
        self.rollout_buffer.add(
            state=state,
            action=action,
            reward=reward,
            value=self.last_value,
            log_prob=self.last_log_prob,
            done=done,
            rag_embedding=rag_embedding,
            action_info=action_info
        )
        
        # 如果episode结束且使用TaskAwareRolloutBuffer，存储整个episode
        if done and isinstance(self.rollout_buffer, TaskAwareRolloutBuffer):
            # 验证episode有数据再存储
            if len(self.rollout_buffer.current_episode['states']) > 0:
                self.rollout_buffer.store_episode()
            else:
                print(f"[PPOTrainer.store_transition] WARNING: Episode ended with no data")


    def train_step(self) -> float:
        """增强的PPO训练步骤，包含RAG增强的GPT-4o-mini蒸馏"""
        # Get data from rollout buffer
        if isinstance(self.rollout_buffer, TaskAwareRolloutBuffer):
            rollout_data = self.rollout_buffer.get(
                current_task_type=self.current_task_type,
                mix_ratio=self.config.get('task_mix_ratio', 0.7)
            )
        else:
            rollout_data = self.rollout_buffer.get()
        
        if not rollout_data:
            print("[PPOTrainer.train_step] No rollout data available")
            return 0.0
        
        # 解包数据，包含RAG embeddings和old_values
        if len(rollout_data) == 7:
            states, actions, old_log_probs, returns, advantages, rag_embeddings, old_values = rollout_data
        else:
            states, actions, old_log_probs, returns, advantages, rag_embeddings = rollout_data
            old_values = None
        
        # 检查数据类型和设备
        if isinstance(states, torch.Tensor):
            # 数据已经是tensor，确保在正确的设备上
            states = states.to(self.device)
            actions = actions.to(self.device) if isinstance(actions, torch.Tensor) else torch.LongTensor(actions).to(self.device)
            old_log_probs = old_log_probs.to(self.device) if isinstance(old_log_probs, torch.Tensor) else torch.FloatTensor(old_log_probs).to(self.device)
            returns = returns.to(self.device) if isinstance(returns, torch.Tensor) else torch.FloatTensor(returns).to(self.device)
            advantages = advantages.to(self.device) if isinstance(advantages, torch.Tensor) else torch.FloatTensor(advantages).to(self.device)
            if rag_embeddings is not None:
                rag_embeddings = rag_embeddings.to(self.device) if isinstance(rag_embeddings, torch.Tensor) else torch.FloatTensor(rag_embeddings).to(self.device)
            if old_values is not None:
                old_values = old_values.to(self.device) if isinstance(old_values, torch.Tensor) else torch.FloatTensor(old_values).to(self.device)
        else:
            # 数据是numpy array，需要转换
            states = torch.FloatTensor(states).to(self.device)
            actions = torch.LongTensor(actions).to(self.device)
            old_log_probs = torch.FloatTensor(old_log_probs).to(self.device)
            returns = torch.FloatTensor(returns).to(self.device)
            advantages = torch.FloatTensor(advantages).to(self.device)
            if rag_embeddings is not None:
                rag_embeddings = torch.FloatTensor(rag_embeddings).to(self.device)
            if old_values is not None:
                old_values = torch.FloatTensor(old_values).to(self.device)
        
        # 验证数据长度
        if len(states) < self.batch_size:
            print(f"[PPOTrainer.train_step] Insufficient data: {len(states)} < {self.batch_size}")
            return 0.0
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # 收集teacher分布（修复：独立的蒸馏控制）
        teacher_distributions = None
        if self.use_distillation:
            # 使用独立的蒸馏概率，不依赖teacher_guidance
            distillation_rate = self.config.get('distillation_sample_rate', 1.0)  # 默认总是蒸馏
            
            # 每个epoch的蒸馏概率可以动态调整
            if hasattr(self, 'training_episodes'):
                # 前期多蒸馏，后期逐渐减少
                warmup_episodes = self.config.get('distillation_warmup_episodes', 5000)
                if self.training_episodes < warmup_episodes:
                    distillation_rate = 1.0  # 前期100%蒸馏
                else:
                    # 后期线性衰减到最小值
                    decay_episodes = self.config.get('distillation_decay_episodes', 20000)
                    min_rate = self.config.get('distillation_min_rate', 0.3)
                    decay_progress = min(1.0, (self.training_episodes - warmup_episodes) / decay_episodes)
                    distillation_rate = 1.0 - decay_progress * (1.0 - min_rate)
            
            if random.random() < distillation_rate:
                print(f"[PPOTrainer] Collecting teacher distributions (rate={distillation_rate:.2f}, weight={self.distillation_weight})")
                # 确保states是numpy array传递给批量方法
                states_numpy = states.cpu().numpy() if isinstance(states, torch.Tensor) else states
                teacher_distributions = self._get_teacher_distributions_batch(states_numpy)
                teacher_distributions = teacher_distributions.to(self.device)
                print(f"[PPOTrainer] Collected {len(teacher_distributions)} teacher distributions")
        
        # 追踪统计
        total_loss = 0
        num_updates = 0
        early_stop = False
        kl_divergences = []
        policy_losses = []
        value_losses = []
        distillation_losses = []
        
        # Training epochs
        for epoch in range(self.n_epochs):
            if early_stop:
                break
                
            # Shuffle indices
            indices = np.arange(len(states))
            np.random.shuffle(indices)
            
            # Mini-batch training
            for start_idx in range(0, len(states), self.batch_size):
                batch_indices = indices[start_idx:start_idx + self.batch_size]
                
                # 准备batch数据
                batch_states = states[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_returns = returns[batch_indices]
                batch_advantages = advantages[batch_indices]
                
                # RAG embeddings
                if rag_embeddings is not None:
                    batch_rag = rag_embeddings[batch_indices]
                else:
                    batch_rag = torch.zeros(len(batch_indices), self.config.get('rag_dim', 64)).to(self.device)
                
                # Teacher distributions for distillation
                batch_teacher_dists = None
                if teacher_distributions is not None and start_idx < len(teacher_distributions):
                    end_idx = min(start_idx + self.batch_size, len(teacher_distributions))
                    if end_idx > start_idx:
                        batch_teacher_dists = teacher_distributions[start_idx:end_idx]
                
                # Forward pass
                logits, values = self.network(batch_states, rag_context=batch_rag)
                
                # Calculate log probs and entropy
                dist = torch.distributions.Categorical(logits=logits)
                log_probs = dist.log_prob(batch_actions)
                entropy = dist.entropy().mean()
                
                # Policy loss with clipping
                ratio = torch.exp(log_probs - batch_old_log_probs)
                policy_loss_1 = -batch_advantages * ratio
                policy_loss_2 = -batch_advantages * torch.clamp(
                    ratio, 
                    1 - self.clip_range, 
                    1 + self.clip_range
                )
                policy_loss = torch.max(policy_loss_1, policy_loss_2).mean()
                
                # Value loss
                values_pred = values.squeeze(-1)
                if old_values is not None:
                    batch_old_values = old_values[batch_indices]
                    values_clipped = batch_old_values + torch.clamp(
                        values_pred - batch_old_values,
                        -self.clip_range_vf if self.clip_range_vf else float('inf'),
                        self.clip_range_vf if self.clip_range_vf else float('inf')
                    )
                    value_loss_1 = F.mse_loss(values_pred, batch_returns)
                    value_loss_2 = F.mse_loss(values_clipped, batch_returns)
                    value_loss = torch.max(value_loss_1, value_loss_2)
                else:
                    value_loss = F.mse_loss(values_pred, batch_returns)
                
                # Distillation loss（如果有teacher分布）
                distillation_loss = torch.tensor(0.0).to(self.device)
                if batch_teacher_dists is not None and batch_teacher_dists.shape[0] == batch_states.shape[0]:
                    # 计算student的log probabilities
                    student_log_probs = F.log_softmax(logits / self.distillation_temperature, dim=-1)
                    # 计算teacher的probabilities
                    teacher_probs = batch_teacher_dists.to(self.device)
                    # KL散度损失
                    distillation_loss = F.kl_div(
                        student_log_probs,
                        teacher_probs,
                        reduction='batchmean'
                    ) * (self.distillation_temperature ** 2)
                    distillation_losses.append(distillation_loss.item())
                
                # Total loss
                loss = (policy_loss + 
                    self.vf_coef * value_loss - 
                    self.ent_coef * entropy +
                    self.distillation_weight * distillation_loss)
                
                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                
                # Optimizer step
                self.optimizer.step()
                
                # 更新学习率
                if hasattr(self, 'lr_scheduler'):
                    self.lr_scheduler.step()
                    
                    # 记录当前学习率
                    current_lr = self.optimizer.param_groups[0]['lr']
                    if self.training_steps % 100 == 0:
                        logger.debug(f"Current learning rate: {current_lr:.6f}")
                
                self.training_steps += 1
                
                # Track metrics
                with torch.no_grad():
                    kl_div = (batch_old_log_probs - log_probs).mean().item()
                    kl_divergences.append(kl_div)
                    
                    # Early stopping check
                    if kl_div > 1.5 * 0.01:
                        print(f"[PPOTrainer] Early stopping at epoch {epoch} due to high KL divergence: {kl_div:.4f}")
                        early_stop = True
                        break
                
                total_loss += loss.item()
                policy_losses.append(policy_loss.item())
                value_losses.append(value_loss.item())
                num_updates += 1
                
                # 记录详细统计
                if num_updates % 10 == 0:
                    log_msg = f"[PPOTrainer] Epoch {epoch}, Update {num_updates}: " \
                            f"loss={loss.item():.4f}, policy_loss={policy_loss.item():.4f}, " \
                            f"value_loss={value_loss.item():.4f}, entropy={entropy.item():.4f}"
                    if distillation_loss.item() > 0:
                        log_msg += f", distill_loss={distillation_loss.item():.4f}"
                    print(log_msg)
        
        # Clear rollout buffer
        self.rollout_buffer.clear()
        self.training_steps += 1
        
        # 更新teacher guidance概率（如果使用）
        if self.use_teacher_guidance:
            self.teacher_guidance_prob = max(
                self.teacher_guidance_min_prob,
                self.teacher_guidance_prob * self.teacher_guidance_decay
            )
        
        # 更新统计
        if kl_divergences:
            avg_kl = np.mean(kl_divergences)
            logger.info(f"Average KL divergence: {avg_kl:.4f}")
        
        if distillation_losses:
            avg_distill_loss = np.mean(distillation_losses)
            logger.info(f"Average distillation loss: {avg_distill_loss:.4f}")
            logger.info(f"Distillation applied to {len(distillation_losses)}/{num_updates} batches")
        
        # 保存缓存
        if hasattr(self, 'distillation_cache'):
            self.distillation_cache._save_cache()
        
        # 返回平均损失
        if num_updates > 0:
            avg_loss = total_loss / num_updates
            print(f"[PPOTrainer.train_step] Training completed: {num_updates} updates, avg_loss={avg_loss:.4f}")
            return avg_loss
        else:
            print("[PPOTrainer.train_step] No updates performed")
            return 0.0
        
    def update_exploration(self):
        """PPO doesn't use explicit exploration parameters, but update teacher guidance"""
        if self.use_teacher_guidance:
            self.teacher_guidance_prob = max(
                self.teacher_guidance_min_prob,
                self.teacher_guidance_prob * self.teacher_guidance_decay
            )
    
    def save_checkpoint(self, path: str, additional_data: Dict[str, Any] = None):
        """Save PPO checkpoint"""
        state_dicts = {
            'network_state_dict': self.network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict()
        }
        
        # 保存任务分布统计
        extra_data = {}
        if isinstance(self.rollout_buffer, TaskAwareRolloutBuffer):
            extra_data['task_statistics'] = self.rollout_buffer.get_task_statistics()
            extra_data['task_counts'] = dict(self.rollout_buffer.task_counts)
        
        if additional_data:
            extra_data.update(additional_data)
        
        self.save_checkpoint_base(path, state_dicts, extra_data)
    

    def load_checkpoint(self, path: str) -> Dict[str, Any]:
        """Load model checkpoint and return additional data"""
        checkpoint = self.load_checkpoint_base(path)
        
        # 使用strict=False加载，处理dynamic_adapter的情况
        missing_keys, unexpected_keys = self.network.load_state_dict(
            checkpoint['network_state_dict'], 
            strict=False
        )
        
        # 记录加载信息以便调试
        if missing_keys:
            print(f"[PPOTrainer.load_checkpoint] Missing keys in state_dict: {missing_keys}")
        if unexpected_keys:
            print(f"[PPOTrainer.load_checkpoint] Unexpected keys in state_dict: {unexpected_keys}")
            # 特别处理dynamic_adapter
            dynamic_adapter_keys = [k for k in unexpected_keys if 'dynamic_adapter' in k]
            if dynamic_adapter_keys:
                print(f"[PPOTrainer.load_checkpoint] Dynamic adapter will be recreated on first forward pass")
        
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        
        return checkpoint
# ===========================
# Import Required Components
# ===========================

def import_mdp_components():
    from generalized_mdp_framework import (
        GeneralizedMDP, GeneralizedMDPState, GeneralizedAction,
        ActionType, ToolExecutionStatus, ErrorCategory,
        DataFlowState, TaskDomain, TaskComplexity,
        TaskFeatures, ToolCapability, load_tool_capabilities
    )
    return True, locals()

def import_phase2_scoring():
    """Import Phase 2 scoring components"""
    logger.debug(f" Importing Phase 2 scoring components...")
    from workflow_quality_test_flawed import StableScorer, SimplifiedScoringConfig
    logger.debug(f" Phase 2 scoring components imported successfully")
    return True, StableScorer, SimplifiedScoringConfig


def import_workflow_generator():
    """Import workflow generator for enforcement"""
    logger.debug(f" Importing workflow generator...")
    # Avoid circular import by importing here
    import mdp_workflow_generator
    logger.debug(f" Workflow generator imported successfully")
    return True, mdp_workflow_generator.MDPWorkflowGenerator


# Import components
MDP_AVAILABLE, mdp_components = import_mdp_components()
if MDP_AVAILABLE:
    globals().update(mdp_components)

PHASE2_AVAILABLE, StableScorer, SimplifiedScoringConfig = import_phase2_scoring()
WORKFLOW_AVAILABLE, MDPWorkflowGenerator = import_workflow_generator()


# ===========================
# Task Loading and Management
# ===========================

class TaskManager:
    """Manages task loading and organization"""
    
    def __init__(self, task_path: Optional[str] = None, task_types: Optional[List[str]] = None):
        self.task_path = task_path or "mcp_generated_library/task_library_all_difficulties.json"
        self.tasks = []
        self.tasks_by_type = defaultdict(list)
        self.tasks_by_complexity = defaultdict(list)
        self.tasks_by_difficulty = defaultdict(list)  # 新增：按难度级别组织
        self.target_task_types = task_types
        self._load_tasks()
    
    def _load_tasks(self):
        """Load tasks from file or create samples"""
        task_paths = [
            # Path("mcp_generated_library/task_library_enhanced_v3.json"),  # 优先使用增强版
            Path("mcp_generated_library/task_library_all_difficulties.json")
            # Path(self.task_path),
            # Path("mcp_generated_library/task_library.json"),
            # Path("task_library.json"),
        ]
        
        for path in task_paths:
            if path.exists():
                logger.debug(f" Attempting to load tasks from {path}")
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Handle different formats
                if isinstance(data, dict):
                    if 'tasks' in data:
                        self._process_task_list(data['tasks'])
                    else:
                        self._process_task_list(list(data.values()))
                elif isinstance(data, list):
                    self._process_task_list(data)
                else:
                    print(f"[ERROR] Unknown data format in {path}: {type(data)}")
                    raise ValueError(f"Unknown task data format: {type(data)}")
                
                if self.tasks:
                    # Filter by task types if specified
                    if self.target_task_types:
                        logger.debug(f" Filtering tasks by types: {self.target_task_types}")
                        self._filter_by_types()
                    logger.info(f"Loaded {len(self.tasks)} tasks from {path}")
                    self._organize_tasks()
                    return
                else:
                    print(f"[WARNING] No tasks loaded from {path}")
        
        logger.warning("No task file found, creating sample tasks")
        self._create_sample_tasks()
    
    def _process_task_list(self, tasks_data: List[Any]):
        """Process a list of task data"""
        for i, task_data in enumerate(tasks_data):
            if isinstance(task_data, dict):
                try:
                    task = self._create_task_object(task_data)
                    if task:
                        self.tasks.append(task)
                except Exception as e:
                    logger.error(f"Failed to create task {i}: {e}")
                    # Try to print task data for debugging
                    logger.debug(f"Task data: {json.dumps(task_data, indent=2, default=str)[:200]}...")
            elif isinstance(task_data, str):
                logger.warning(f"Skipping string task data: {task_data[:50]}...")
            else:
                logger.warning(f"Skipping unknown task data type: {type(task_data)}")
    

    def _create_task_object(self, data: dict):
        """Create a task object from dictionary data"""
        class Task:
            def __init__(self, data):
                # Handle different field names
                self.id = data.get('id', data.get('instance_id', f"task_{uuid.uuid4().hex[:8]}"))
                self.instance_id = self.id
                self.task_type = data.get('task_type', 'unknown')
                self.description = data.get('description', '')
                self.complexity = data.get('complexity', 'medium')
                
                # 添加difficulty_level属性读取
                self.difficulty_level = data.get('difficulty_level', 'medium')
                
                # Handle input data
                self.test_input = data.get('test_input', data.get('inputs', {}))
                self.inputs = self.test_input
                
                # Handle output data
                self.expected_output = data.get('expected_output', data.get('expected_outputs', {}))
                self.expected_outputs = self.expected_output
                
                # Handle tools
                self.required_tools = data.get('required_tools', [])
                
                # Metadata
                self.metadata = data.get('metadata', {})
                
                # Additional fields
                self.semantic_features = data.get('semantic_features', {})
        
        return Task(data)
    
    def _organize_tasks(self):
        """Organize tasks by type, complexity and difficulty level"""
        self.tasks_by_type.clear()
        self.tasks_by_complexity.clear()
        self.tasks_by_difficulty.clear()  # 新增：清空难度字典
        
        for task in self.tasks:
            if hasattr(task, 'task_type'):
                self.tasks_by_type[task.task_type].append(task)
            if hasattr(task, 'complexity'):
                self.tasks_by_complexity[task.complexity].append(task)
            if hasattr(task, 'difficulty_level'):  # 新增：按difficulty_level组织
                self.tasks_by_difficulty[task.difficulty_level].append(task)
        
        logger.info(f"Organized tasks: {len(self.tasks_by_type)} types, "
                   f"{len(self.tasks_by_complexity)} complexity levels, "
                   f"{len(self.tasks_by_difficulty)} difficulty levels")
        
        # 打印难度级别统计
        for difficulty, tasks in self.tasks_by_difficulty.items():
            print(f"[TaskManager] Difficulty level '{difficulty}': {len(tasks)} tasks")



    def _filter_by_types(self):
        """Filter tasks by target task types"""
        if not self.target_task_types:
            return
        
        # 记录原始数量
        original_count = len(self.tasks)
        original_type_counts = {}
        for task in self.tasks:
            if hasattr(task, 'task_type'):
                task_type = task.task_type
                original_type_counts[task_type] = original_type_counts.get(task_type, 0) + 1
        
        # 筛选任务
        filtered_tasks = []
        for task in self.tasks:
            if hasattr(task, 'task_type') and task.task_type in self.target_task_types:
                filtered_tasks.append(task)
        
        self.tasks = filtered_tasks
        
        # 记录筛选后的数量
        filtered_type_counts = {}
        for task in self.tasks:
            if hasattr(task, 'task_type'):
                task_type = task.task_type
                filtered_type_counts[task_type] = filtered_type_counts.get(task_type, 0) + 1
        
        # 日志输出
        logger.info(f"Task filtering results:")
        logger.info(f"  Total: {original_count} -> {len(self.tasks)}")
        for task_type in self.target_task_types:
            original = original_type_counts.get(task_type, 0)
            filtered = filtered_type_counts.get(task_type, 0)
            logger.info(f"  {task_type}: {original} -> {filtered}")
        
        # 警告如果某些类型没有任务
        for task_type in self.target_task_types:
            if filtered_type_counts.get(task_type, 0) == 0:
                logger.warning(f"No tasks found for type '{task_type}' in the task library!")
        
        # 如果筛选后没有任何任务，报错
        if not self.tasks:
            raise ValueError(f"No tasks found for types {self.target_task_types} in the task library!")
    
    def _create_sample_tasks(self):
        """Create sample tasks if no file is found"""
        sample_tasks = [
            {
                'id': 'sample_task_1',
                'task_type': 'simple_task',
                'description': 'Process a simple data transformation',
                'complexity': 'easy',
                'test_input': {'data': [1, 2, 3, 4, 5]},
                'expected_output': {'result': [2, 4, 6, 8, 10]},
                'required_tools': ['reader', 'transformer', 'writer']
            },
            {
                'id': 'sample_task_2',
                'task_type': 'data_pipeline',
                'description': 'Build a complete data processing pipeline',
                'complexity': 'medium',
                'test_input': {'source': 'data.csv', 'format': 'csv'},
                'expected_output': {'processed': True, 'output_format': 'json'},
                'required_tools': ['reader', 'parser', 'validator', 'transformer', 'writer']
            },
            {
                'id': 'sample_task_3',
                'task_type': 'api_integration',
                'description': 'Integrate multiple APIs with validation',
                'complexity': 'hard',
                'test_input': {'endpoints': ['api1', 'api2'], 'auth': 'token'},
                'expected_output': {'integrated': True, 'validated': True},
                'required_tools': ['authenticator', 'fetcher', 'validator', 'aggregator', 'poster']
            },
            {
                'id': 'sample_task_4',
                'task_type': 'workflow_automation',
                'description': 'Automate a multi-stage workflow',
                'complexity': 'hard',
                'test_input': {'stages': 5, 'data': [100, 200, 300]},
                'expected_output': {'completed_stages': 5},
                'required_tools': ['reader', 'parser', 'transformer', 'aggregator', 'writer']
            }
        ]
        
        for i, task_data in enumerate(sample_tasks):
            logger.debug(f" Creating sample task {i+1}/{len(sample_tasks)}: {task_data['id']}")
            task = self._create_task_object(task_data)
            if task:
                self.tasks.append(task)
                logger.info(f"Created sample task: {task.id}")
            else:
                # 直接抛出错误，不隐藏问题
                raise ValueError(f"Failed to create sample task from data: {task_data}")
        
        logger.info(f"Created {len(self.tasks)} sample tasks")
        self._organize_tasks()
    
    def get_task(self, task_type: Optional[str] = None, 
                 complexity: Optional[str] = None,
                 difficulty_level: Optional[str] = None) -> Any:  # 新增参数
        """Get a task based on criteria"""
        candidates = self.tasks
        
        # 优先按difficulty_level筛选（用于curriculum learning）
        if difficulty_level and difficulty_level in self.tasks_by_difficulty:
            candidates = self.tasks_by_difficulty[difficulty_level]
            print(f"[TaskManager] Filtering by difficulty_level '{difficulty_level}': {len(candidates)} candidates")
            
            # 如果同时指定了task_type，进一步筛选
            if task_type:
                candidates = [t for t in candidates if hasattr(t, 'task_type') and t.task_type == task_type]
                print(f"[TaskManager] Further filtering by task_type '{task_type}': {len(candidates)} candidates")
        elif task_type and task_type in self.tasks_by_type:
            candidates = self.tasks_by_type[task_type]
        elif complexity and complexity in self.tasks_by_complexity:
            candidates = self.tasks_by_complexity[complexity]
        
        if candidates:
            selected = random.choice(candidates)
            print(f"[TaskManager] Selected task: {getattr(selected, 'id', 'unknown')}, "
                  f"difficulty: {getattr(selected, 'difficulty_level', 'unknown')}")
            return selected
        elif self.tasks:
            print(f"[TaskManager] WARNING: No candidates found, selecting from all {len(self.tasks)} tasks")
            return random.choice(self.tasks)
        else:
            print(f"[TaskManager] ERROR: No tasks available!")
            return None



# ===========================
# MDP Environment Wrapper
# ===========================

# 相同位置的修复代码
# 修改的行用注释标注：# <- 修改了这一行

# 文件：unified_training_manager.py
# 位置：第2360-2450行
# 完整的MDPEnvironment.__init__函数（workflow和scorer初始化部分）

class MDPEnvironment:
    """Environment wrapper for MDP with Phase 2/3 integration"""

    def __init__(self, mdp: GeneralizedMDP, task_manager, 
                use_task_aware_state: bool = True,
                enforce_workflow: bool = False,
                use_phase2_scoring: bool = True,
                normalize_rewards: bool = True,  # 添加这个参数
                trainer=None):  # 添加 trainer 参数
        """Initialize MDP environment"""
        self.mdp = mdp
        self.task_manager = task_manager
        self.use_task_aware_state = use_task_aware_state
        self.enforce_workflow = enforce_workflow
        self.use_phase2_scoring = use_phase2_scoring
        self.normalize_rewards = normalize_rewards  # 保存归一化配置


        self.current_success_rate = 0.0
        self.success_rate_threshold = 0.3  # 默认阈值
        
        # State representation
        # self.state_dim = mdp.state_dim
        
        # Current episode state
        self.current_task = None
        self.current_state = None
        self.episode_steps = 0
        
        # 评估模式标志
        self.is_evaluation_mode = False
        
        # Action space
        self.action_space = self._build_action_space()
        self.num_actions = len(self.action_space)
        self.num_tools = len(mdp.tool_capabilities)
        
        # Create tool registry for verifier
        self.tool_registry = mdp.tool_capabilities
        
        # 创建工具索引映射（用于序列编码）
        self.tool_names = sorted(list(mdp.tool_capabilities.keys()))
        self.tool_to_idx = {tool: idx for idx, tool in enumerate(self.tool_names)}
    
        # Workflow enforcement
        self.workflow_generator = None
        self.current_workflow = None
        self.workflow_step = 0
        
        if self.enforce_workflow and MDPWorkflowGenerator:
            print("[DEBUG] Initializing MDPWorkflowGenerator for workflow enforcement")
            self.workflow_generator = MDPWorkflowGenerator(
                model_path=None,  # 不加载模型文件
                tools_path="./mcp_generated_library/tool_registry_consolidated.json"
            )
            
            # 如果提供了 trainer，共享其网络
            if trainer and hasattr(trainer, 'network'):
                print("[DEBUG] Sharing trainer's network with workflow_generator")
                self.workflow_generator.set_network_reference(
                    trainer.network,
                    algorithm='ppo'
                )
            elif trainer and hasattr(trainer, 'q_network'):
                print("[DEBUG] Sharing trainer's Q-network with workflow_generator")
                self.workflow_generator.set_network_reference(
                    trainer.q_network,
                    algorithm='dqn'
                )
            else:
                print("[WARNING] No trainer network available for workflow_generator")
            
            logger.info("Workflow enforcement enabled with shared network")

        
        self.scorer = None
        if self.use_phase2_scoring and StableScorer:
            # Initialize embedding manager first
            embedding_manager = None
            logger.debug(f" Initializing embedding manager for Phase 2 scoring")
            from mcp_embedding_manager import MCPEmbeddingManager
            embedding_manager = MCPEmbeddingManager()
            
            # Try to load existing index
            index_path = Path(".mcp_embedding_cache/tool_index.pkl")
            embedding_manager.load_index(index_path)
            print(f"[INFO] Loaded tool embeddings for {len(embedding_manager.tool_embeddings)} tools")
            logger.info(f"Loaded embedding manager with {len(embedding_manager.tool_embeddings)} tools")

            
            # Create verifier with embedding manager
            verifier = None
            if PHASE2_AVAILABLE:
                try:
                    from workflow_quality_test_flawed import ToolCallVerifier
                    verifier = ToolCallVerifier(self.tool_registry, embedding_manager=embedding_manager)
                    logger.info("Created ToolCallVerifier for Phase 2 scoring")
                    print(f"[VERIFIER] Created with {len(self.tool_registry)} tools and embedding_manager={'enabled' if embedding_manager else 'disabled'}")
                except Exception as e:
                    logger.warning(f"Failed to create verifier: {e}")
                    print(f"[WARNING] Failed to create verifier: {e}")
            
            # Create StableScorer with both verifier and embedding_manager
            self.scorer = StableScorer(
                SimplifiedScoringConfig(), 
                verifier=verifier,
                embedding_manager=embedding_manager
            )
            logger.info(f"Phase 2 stable scoring enabled with embedding_manager={'yes' if embedding_manager else 'no'}")
        
        # Curriculum learning
        self.curriculum_stage = 0
        

        # 新增：奖励归一化统计
        self.reward_history = []  # 保存最近的奖励历史
        self.reward_history_size = 1000  # 历史窗口大小
        self.reward_mean = 0.0
        self.reward_std = 1.0
        self.min_reward_std = 1.0  # 最小标准差，避免除零
        self.normalize_rewards = True  # 是否启用归一化
        
        # 奖励统计更新计数
        self.reward_update_count = 0
        self.reward_update_frequency = 10  # 每10步更新一次统计
        
        
        # Task instance tracking
        self.current_task_info = {}


        logger.info(f"Environment initialized:")
        logger.info(f"  Tools: {self.num_tools}")
        logger.info(f"  Actions: {self.num_actions}")
        logger.info(f"  Task-aware: {self.use_task_aware_state}")
        logger.info(f"  Workflow enforcement: {self.enforce_workflow}")
        logger.info(f"  Phase 2 scoring: {self.use_phase2_scoring}")


    def set_current_success_rate(self, success_rate: float, threshold: Optional[float] = None):
        """设置当前训练成功率，用于奖励计算
        
        Args:
            success_rate: 当前的任务成功率（0-1）
            threshold: 模式切换阈值
                - success_rate < threshold: 覆盖率模式（只要求执行所有required_tools）
                - success_rate >= threshold: 顺序模式（要求按正确顺序执行）
        """
        self.current_success_rate = success_rate
        if threshold is not None:
            self.success_rate_threshold = threshold
        
        mode = "coverage" if success_rate < self.success_rate_threshold else "sequence"
        print(f"[ENV] Reward mode: {mode} (success_rate={success_rate:.2%} {'<' if success_rate < self.success_rate_threshold else '>='} threshold={self.success_rate_threshold:.2%})")
    

    def _build_action_space(self) -> List[GeneralizedAction]:
        """Build action space from available actions"""
        actions = []
        
        # Add tool invocation actions
        for tool_name in sorted(self.mdp.tool_capabilities.keys()):
            actions.append(GeneralizedAction(
                action_type=ActionType.INVOKE_TOOL,
                tool_name=tool_name
            ))
        
        # Add non-tool actions
        actions.append(GeneralizedAction(ActionType.NO_OP))
        actions.append(GeneralizedAction(ActionType.VALIDATE_OUTPUT))
        actions.append(GeneralizedAction(ActionType.RETRY_TOOL))
        actions.append(GeneralizedAction(ActionType.RECOVER_ERROR))
        
        return actions

    def _decode_action(self, action_idx: int) -> Tuple[ActionType, Optional[str]]:
        """Decode action index to action type and tool name
        
        Args:
            action_idx: Integer action index
            
        Returns:
            Tuple of (ActionType, tool_name or None)
        """
        if action_idx < 0 or action_idx >= len(self.action_space):
            # 默认返回NO_OP
            return ActionType.NO_OP, None
        
        action = self.action_space[action_idx]
        return action.action_type, getattr(action, 'tool_name', None)

    def ensure_required_tools_in_state(self, state: GeneralizedMDPState, task):
        """确保状态的metadata中包含required_tools信息"""
        
        # 初始化metadata（如果不存在）
        if not hasattr(state, 'metadata'):
            state.metadata = {}
        
        # 构建task_instance信息
        task_instance = {
            'task_type': getattr(task, 'task_type', 'unknown'),
            'description': getattr(task, 'description', ''),
            'required_tools': getattr(task, 'required_tools', []),
            'instance_id': getattr(task, 'id', f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            'complexity': getattr(task, 'complexity', 'medium')
        }
        
        # 存储在metadata中
        state.metadata['task_instance'] = task_instance
        
        # 同时为每个required_tool创建期望的里程碑
        if task_instance['required_tools']:
            for i, tool in enumerate(task_instance['required_tools']):
                # 添加顺序相关的里程碑
                state.expected_milestones.add(f"required_tool_{i}_{tool}_completed")
        
        logger.debug(f" Task setup - Type: {task_instance['task_type']}, "
            f"Required tools: {task_instance['required_tools']}")
        
        return state



    def reset(self, task: Optional[Any] = None, 
            task_type: Optional[str] = None,
            curriculum_stage: Optional[int] = None) -> np.ndarray:
        """Reset environment with curriculum support"""
        
        # 更新MDP的课程阶段
        if curriculum_stage is not None and hasattr(self.mdp, 'set_curriculum_stage'):
            self.mdp.set_curriculum_stage(curriculum_stage)
            print(f"[ENV] Reset with curriculum stage {curriculum_stage}")
        
        # Select task based on curriculum
        if task is None:
            # 根据课程阶段选择合适难度的任务
            # 使用curriculum_stage参数，让_select_task内部处理complexity映射
            self.current_task = self._select_task(task_type=task_type, curriculum_stage=curriculum_stage)
        else:
            self.current_task = task
        
        # 其余reset逻辑保持不变...
        self.current_task_info = {
            'id': getattr(self.current_task, 'id', 'unknown'),
            'task_type': getattr(self.current_task, 'task_type', 'unknown'),
            'description': getattr(self.current_task, 'description', ''),
            'required_tools': getattr(self.current_task, 'required_tools', []),
            'complexity': getattr(self.current_task, 'complexity', 'medium'),
            'metadata': getattr(self.current_task, 'metadata', {})
        }
        
        # Create initial state
        if self.use_task_aware_state and hasattr(globals(), 'TaskAwareMDPState'):
            self.current_state = globals()['TaskAwareMDPState'](
                task_id=self.current_task.id,
                task_type=self.current_task.task_type,
                task_objective=self.current_task.description
            )
            self.current_state.task_features = self._extract_task_features(self.current_task)
        else:
            self.current_state = GeneralizedMDPState(
                task_id=self.current_task.id,
                task_type=self.current_task.task_type,
                task_objective=self.current_task.description
            )

        self.current_state.metadata['current_success_rate'] = self.current_success_rate
        self.current_state.metadata['success_rate_threshold'] = self.success_rate_threshold
        self.current_state.metadata['last_action'] = None  # 初始化上一个动作


        print(f"[ENV] State metadata updated - Mode: {'coverage' if self.current_success_rate < self.success_rate_threshold else 'sequence'}")
        print(f"[ENV] Required tools: {self.current_state.metadata.get('required_tools', [])}")

        # 确保required_tools信息在状态中
        self.current_state = self.ensure_required_tools_in_state(
            self.current_state, 
            self.current_task
        )
        
        self._reset_workflow()
        self.episode_steps = 0
        
        return self._encode_state()


    def _select_task(self, task_type: Optional[str] = None,
                    curriculum_stage: Optional[int] = None) -> Any:
        """Select task based on curriculum and type"""
        print(f"[TASK_SELECT] Selecting task for stage {curriculum_stage}")
        
        # 改进的课程难度映射 - 更平滑的难度递进
        if curriculum_stage == 0:
            # Stage 0: 只选择 very_easy 难度的任务
            difficulty_level = 'very_easy'
            print(f"[TASK_SELECT] Stage 0 - Using very_easy tasks only")
        elif curriculum_stage == 1:
            # Stage 1: 随机选择 very_easy 或 easy
            import random
            difficulty_level = random.choice(['very_easy', 'easy'])
            print(f"[TASK_SELECT] Stage 1 - Selected {difficulty_level} difficulty")
        elif curriculum_stage == 2:
            # Stage 2: 主要选择 easy，偶尔选择 medium
            import random
            difficulty_level = random.choices(['easy', 'medium'], weights=[0.7, 0.3])[0]
            print(f"[TASK_SELECT] Stage 2 - Selected {difficulty_level} difficulty")
        elif curriculum_stage == 3:
            # Stage 3: 平衡选择 medium 和 hard
            import random
            difficulty_level = random.choices(['medium', 'hard'], weights=[0.6, 0.4])[0]
            print(f"[TASK_SELECT] Stage 3 - Selected {difficulty_level} difficulty")
        else:
            # Stage 4+: 所有难度
            difficulty_level = None
            print(f"[TASK_SELECT] Stage 4+ - Using all difficulties")
        
        # 使用 TaskManager 获取任务 - 修改：使用difficulty_level而不是complexity
        task = self.task_manager.get_task(task_type=task_type, difficulty_level=difficulty_level)
        
        # 验证任务难度
        if task and hasattr(task, 'difficulty_level'):
            actual_difficulty = getattr(task, 'difficulty_level', 'unknown')
            print(f"[TASK_SELECT] Got task with difficulty: {actual_difficulty}")
            
            # 确保任务难度匹配预期
            if difficulty_level and actual_difficulty != difficulty_level:
                print(f"[TASK_SELECT] WARNING: Expected {difficulty_level}, got {actual_difficulty}")
        
        else:
            raise ValueError("No difficulty_level")
        
        return task
    
    def _extract_task_features(self, task) -> 'TaskFeatures':
        """Extract semantic features from task"""
        features = TaskFeatures()
        
        # Extract from description
        desc_lower = task.description.lower() if hasattr(task, 'description') else ''
        
        features.has_input_requirement = any(kw in desc_lower for kw in ['read', 'load', 'fetch', 'input'])
        features.has_output_requirement = any(kw in desc_lower for kw in ['write', 'save', 'export', 'output'])
        features.requires_validation = 'validat' in desc_lower
        features.requires_transformation = any(kw in desc_lower for kw in ['transform', 'convert', 'process'])
        features.requires_aggregation = any(kw in desc_lower for kw in ['aggregat', 'combin', 'merg'])
        
        # Estimate complexity
        if hasattr(task, 'complexity'):
            comp_map = {'easy': TaskComplexity.SIMPLE, 'medium': TaskComplexity.MODERATE, 'hard': TaskComplexity.COMPLEX}
            features.complexity = comp_map.get(task.complexity, TaskComplexity.MODERATE)
        
        # Estimate steps
        if hasattr(task, 'required_tools'):
            features.estimated_steps = len(task.required_tools)
        
        # Determine domain
        if 'api' in desc_lower:
            features.domain = TaskDomain.API_INTEGRATION
        elif 'file' in desc_lower:
            features.domain = TaskDomain.FILE_OPERATIONS
        elif 'data' in desc_lower:
            features.domain = TaskDomain.DATA_PROCESSING
        
        return features
    


# 文件：unified_training_manager.py
# 位置：第2500-2550行
# 完整的_reset_workflow函数

    def _reset_workflow(self):
        """Reset workflow for enforcement"""
        # 添加严格的None检查
        logger.debug(f" _reset_workflow called, workflow_generator = {self.workflow_generator}")
        logger.debug(f" enforce_workflow = {self.enforce_workflow}")
        
        # 如果workflow_generator为None，直接返回
        if self.workflow_generator is None:
            logger.debug(f" workflow_generator is None, skipping workflow reset")
            self.current_workflow = None
            self.workflow_step = 0
            return
        
        # 检查current_task是否为None
        if self.current_task is None:
            logger.error("current_task is None in _reset_workflow")
            print("[ERROR] No task selected - task library may be empty or path incorrect")
            print("[ERROR] Please check if task_library_all_difficulties.json exists")
            self.current_workflow = None
            self.workflow_step = 0
            # 提供更详细的错误信息
            raise RuntimeError(
                "No task available. Possible causes:\n"
                "1. Task library file not found at: mcp_generated_library/task_library_all_difficulties.json\n"
                "2. Task library is empty\n"
                "3. No tasks match the requested criteria\n"
                "Please ensure the task library file exists and contains valid tasks."
            )
        
        # 检查current_task是否有必要的属性
        if not hasattr(self.current_task, 'task_type'):
            logger.error(f"current_task missing task_type attribute: {self.current_task}")
            print(f"[ERROR] Invalid task object: {self.current_task}")
            self.current_workflow = None
            self.workflow_step = 0
            raise RuntimeError(f"Invalid task object - missing task_type attribute: {self.current_task}")
        
        # 只有在workflow_generator存在时才执行workflow生成
        # 创建task_instance字典，包含完整的任务信息
        task_instance = {
            'task_type': self.current_task.task_type,
            'description': getattr(self.current_task, 'description', ''),
            'required_tools': getattr(self.current_task, 'required_tools', []),
            'id': getattr(self.current_task, 'id', 'unknown'),
            'complexity': getattr(self.current_task, 'complexity', 'medium'),
            'inputs': getattr(self.current_task, 'inputs', {}),
            'expected_outputs': getattr(self.current_task, 'expected_outputs', {})
        }
        
        logger.debug(f" Generating workflow for task_type: {self.current_task.task_type}")
        
        # 使用task_instance生成workflow，启用instance-dependent + RAG
        workflow = self.workflow_generator.generate_workflow(
            self.current_task.task_type,
            task_instance=task_instance
        )
        self.current_workflow = workflow.get('optimal_sequence', [])
        self.workflow_step = 0
        logger.info(f"Generated instance-aware workflow: {self.current_workflow}")
        logger.debug(f" Successfully generated workflow: {self.current_workflow}")

    

    def _encode_state(self) -> np.ndarray:
        """Encode state as vector with Phase 3 support"""
        state = self.current_state
        encoded = []
        
        # Tool states (one-hot encoding)
        for tool_name in sorted(self.mdp.tool_capabilities.keys()):
            if hasattr(state, 'tool_states') and tool_name in state.tool_states:
                status = state.tool_states[tool_name]
                # Handle status encoding
                if hasattr(ToolExecutionStatus, '__members__'):
                    status_list = list(ToolExecutionStatus)
                    status_idx = status_list.index(status) if status in status_list else 0
                else:
                    status_idx = 0
            else:
                status_idx = 0
            
            # One-hot encode (11 possible states)
            one_hot = [0.0] * 11
            one_hot[status_idx] = 1.0
            encoded.extend(one_hot)
        
        # Progress features (10 dimensions)
        progress_features = [
            getattr(state, 'overall_progress', 0.0),
            float(getattr(state, 'workflow_step', 0)) / 50.0,
            float(getattr(state, 'consecutive_errors', 0)) / 10.0,
            float(getattr(state, 'total_errors', 0)) / 20.0,
            float(len(getattr(state, 'execution_sequence', []))) / 20.0,
            float(len(getattr(state, 'milestones_achieved', set()))) / 10.0,
            float(getattr(state, 'current_stage', 0)) / 5.0,
            float(getattr(state, 'recovery_count', 0)) / 5.0,
            getattr(state, 'confidence_score', 1.0),
            min(1.0, getattr(state, 'time_elapsed', 0.0) / 100.0)
        ]
        encoded.extend(progress_features)
        
        # Task-aware features (if available)
        if self.use_task_aware_state and hasattr(state, 'task_features'):
            task_vector = state.task_features.to_vector()
            encoded.extend(task_vector)
        
        # Semantic features (if available)
        if hasattr(state, 'semantic_milestones'):
            semantic_features = [
                float('data_loaded' in state.milestones_achieved),
                float('data_validated' in state.milestones_achieved),
                float('data_transformed' in state.milestones_achieved),
                float('data_exported' in state.milestones_achieved),
                float(getattr(state, 'data_flow_state', DataFlowState.EMPTY) == DataFlowState.VALIDATED),
                float(getattr(state, 'data_flow_state', DataFlowState.EMPTY) == DataFlowState.TRANSFORMED),
                float(len(getattr(state, 'validations_performed', []))) / 5.0,
                float(len(getattr(state, 'semantic_milestones', []))) / 10.0,
                getattr(state, 'subtask_progress', {}).get('input_acquired', 0.0),
                getattr(state, 'subtask_progress', {}).get('validated', 0.0)
            ]
            encoded.extend(semantic_features)
        
        # 序列感知特征 - 包含工具执行位置和顺序信息  # <- 新增了这部分
        sequence_features = self._encode_sequence_features(state)  # <- 新增了这一行
        encoded.extend(sequence_features)  # <- 新增了这一行
        
        return np.array(encoded, dtype=np.float32)


    def _encode_sequence_features(self, state) -> List[float]:
        """编码序列相关特征，基于数据流和语义进展而非required_tools"""
        features = []
        
        # 1. 数据流进展特征（不依赖required_tools）
        data_flow_progression = [
            float(state.data_flow_state == DataFlowState.EMPTY),
            float(state.data_flow_state == DataFlowState.INITIALIZED),
            float(state.data_flow_state == DataFlowState.PARTIAL),  # <- 修改了这一行：用PARTIAL替代原来错误的位置
            float(state.data_flow_state == DataFlowState.TRANSFORMED),
            float(state.data_flow_state == DataFlowState.VALIDATED)  # <- 修改了这一行：VALIDATED是最终状态
        ]
        features.extend(data_flow_progression)  # 5维
        
        # 2. 语义操作覆盖度（已完成的操作类型）
        semantic_coverage = {
            'read': False,
            'validate': False,
            'transform': False,
            'aggregate': False,
            'write': False
        }
        
        # 检查已执行工具的语义操作
        for tool in state.execution_sequence:
            if tool in self.mdp.tool_capabilities:
                capability = self.mdp.tool_capabilities[tool]
                for op in capability.semantic_operations:
                    for key in semantic_coverage:
                        if key in op.lower():
                            semantic_coverage[key] = True
        
        features.extend([float(v) for v in semantic_coverage.values()])  # 5维
        
        # 3. 工具类别转换模式（最近的类别转换）
        tool_category_sequence = []
        for tool in state.execution_sequence[-3:]:  # 最近3个工具
            if tool in self.mdp.tool_capabilities:
                # 获取工具的主要类别
                category = self._get_tool_category(tool)
                tool_category_sequence.append(category)
        
        # 编码类别转换（如：read->transform->write）
        category_transitions = self._encode_category_transitions(tool_category_sequence)
        features.extend(category_transitions)  # 3维
        
        # 4. 执行密度和效率特征
        if len(state.execution_sequence) > 0:
            # 成功率
            success_rate = len([t for t in state.execution_sequence 
                            if state.tool_states.get(t) == ToolExecutionStatus.SUCCESS]) / len(state.execution_sequence)
            # 工具多样性
            diversity = len(set(state.execution_sequence)) / len(state.execution_sequence)
        else:
            success_rate = 0.0
            diversity = 0.0
        
        features.extend([success_rate, diversity])  # 2维
        
        return features  # 总共15维


    def _get_tool_category(self, tool_name: str) -> float:
        """获取工具的语义类别编码 - RAG增强版本"""
        # 首先尝试使用tool_capability_manager（如果存在）
        capability = self.mdp.tool_capabilities.get(tool_name)
        # 获取类别名称 - 通过self.mdp访问tool_capability_manager
        category = self.mdp.tool_capability_manager.get_category(capability)  # <- 修改了这一行：添加self.mdp.
        # 获取类别编码
        category_encoding = self.mdp.tool_capability_manager.get_category_encoding(category)  # <- 修改了这一行：添加self.mdp.
        
        # 如果有嵌入管理器，使用RAG增强
        if self.mdp.embedding_manager:  # <- 修改了这一行：添加条件检查和self.mdp.
            # logger.debug(f" Using RAG enhancement for {tool_name}")
            # 构建搜索查询，包含工具名和语义操作
            search_query = f"{tool_name} {' '.join(capability.semantic_operations)}"
            
            # 搜索语义相似的工具
            search_results = self.mdp.embedding_manager.search(  # <- 修改了这一行：添加self.mdp.
                query=search_query,
                k=10,
                return_scores=True
            )
            
            # 分析搜索结果中的类别分布
            category_scores = {}
            total_score = 0.0
            
            for result in search_results:
                if result.tool_name in self.mdp.tool_capabilities:
                    result_capability = self.mdp.tool_capabilities[result.tool_name]
                    result_category = self.mdp.tool_capability_manager.get_category(result_capability)  # <- 修改了这一行：添加self.mdp.
                    result_encoding = self.mdp.tool_capability_manager.get_category_encoding(result_category)  # <- 修改了这一行：添加self.mdp.
                    
                    # 使用相似度分数加权
                    if result_encoding not in category_scores:
                        category_scores[result_encoding] = 0.0
                    category_scores[result_encoding] += result.score
                    total_score += result.score
            
            # 如果有有效的搜索结果，使用加权平均
            if total_score > 0:
                rag_encoding = sum(encoding * score / total_score 
                                for encoding, score in category_scores.items())
                # 混合原始编码和RAG编码
                final_encoding = category_encoding * 0.6 + rag_encoding * 0.4
                # logger.debug(f" RAG-enhanced encoding for {tool_name}: {final_encoding:.3f}")
                return final_encoding
                
        return category_encoding

    def _encode_category_transitions(self, categories: List[float]) -> List[float]:
        """编码类别转换模式"""
        if len(categories) == 0:
            return [0.0, 0.0, 0.0]
        elif len(categories) == 1:
            return [categories[0], 0.0, 0.0]
        elif len(categories) == 2:
            return [categories[0], categories[1], categories[1] - categories[0]]
        else:
            return [
                categories[0],
                categories[-1],
                np.mean([categories[i+1] - categories[i] for i in range(len(categories)-1)])
            ]

    def _encode_task_type(self, task_type: str) -> List[float]:
        """将任务类型编码为向量"""
        task_types = ['simple_task', 'basic_task', 'data_pipeline', 
                    'api_integration', 'multi_stage_pipeline']
        
        # One-hot编码
        features = [0.0] * len(task_types)
        if task_type in task_types:
            idx = task_types.index(task_type)
            features[idx] = 1.0
        
        return features

    def _evaluate_execution_quality(self, state: GeneralizedMDPState) -> Dict[str, Any]:
        """评估执行质量，用于Phase 2评分
        
        Returns:
            包含评估结果的字典
        """
        evaluation = {
            'success_level': 'failure',
            'required_coverage': 0.0,
            'sequence_score': 0.0,
            'retry_count': 0,
            'error_count': state.total_errors
        }
        
        # 获取required_tools
        required_tools = []
        if hasattr(state, 'metadata') and 'required_tools' in state.metadata:
            required_tools = state.metadata['required_tools']
        elif self.task_instance:
            required_tools = self.task_instance.get('required_tools', [])
        
        if not required_tools:
            # 没有required_tools时的简单评估
            if state.is_successful:
                evaluation['success_level'] = 'full_success'
            elif state.overall_progress > 0.5:
                evaluation['success_level'] = 'partial_success'
            return evaluation
        
        # 计算required_tools覆盖率
        executed_required = [t for t in state.execution_sequence if t in required_tools]
        evaluation['required_coverage'] = len(executed_required) / len(required_tools) if required_tools else 0.0
        
        # 计算序列正确性
        if executed_required:
            correct_order = 0
            for i, tool in enumerate(executed_required):
                expected_index = required_tools.index(tool)
                if i == expected_index:
                    correct_order += 1
            evaluation['sequence_score'] = correct_order / len(executed_required)
        
        # 统计重试次数
        tool_counts = {}
        for tool in state.execution_sequence:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        retry_count = 0
        for tool, count in tool_counts.items():
            if count > 1:
                retry_count += count - 1
        evaluation['retry_count'] = retry_count
        
        # 确定成功级别
        if state.is_successful and evaluation['required_coverage'] >= 0.9:
            evaluation['success_level'] = 'full_success'
        elif state.is_successful or evaluation['required_coverage'] >= 0.5:
            evaluation['success_level'] = 'partial_success'
        
        return evaluation

    def _encode_description_features(self, description: str) -> List[float]:
        """从任务描述中提取简单的语义特征"""
        desc_lower = description.lower()
        
        features = [
            float('read' in desc_lower or 'extract' in desc_lower),
            float('transform' in desc_lower or 'process' in desc_lower),
            float('write' in desc_lower or 'save' in desc_lower),
            float('validate' in desc_lower or 'check' in desc_lower),
            float('sequential' in desc_lower or 'pipeline' in desc_lower)
        ]
        
        return features



    def get_state_dim(self) -> int:
        """Get state dimension"""
        # Base: tools * 11 states + 10 progress features
        base_dim = self.num_tools * 11 + 10
        
        # Add task-aware features
        if self.use_task_aware_state:
            base_dim += 20  # TaskFeatures vector dimension
        
        # Add semantic features
        base_dim += 10
        
        # 添加序列感知特征  # <- 新增了这一行
        base_dim += 15  # 序列特征维度  # <- 新增了这一行
        
        return base_dim
    
    def get_valid_actions(self) -> List[int]:
        """Get valid action indices"""
        if self.enforce_workflow and self.current_workflow:
            # Workflow enforcement
            if self.workflow_step < len(self.current_workflow):
                next_tool = self.current_workflow[self.workflow_step]
                valid_indices = []
                for i, action in enumerate(self.action_space):
                    if (action.action_type == ActionType.INVOKE_TOOL and
                        action.tool_name == next_tool):
                        valid_indices.append(i)
                if valid_indices:
                    return valid_indices
        
        # Otherwise get all semantically valid actions
        valid_actions = self.mdp.get_available_actions(self.current_state)
        valid_indices = []
        
        for i, action in enumerate(self.action_space):
            for valid_action in valid_actions:
                if (action.action_type == valid_action.action_type and
                    action.tool_name == getattr(valid_action, 'tool_name', None)):
                    valid_indices.append(i)
                    break
        
        # Always allow NO_OP
        if not valid_indices:
            for i, action in enumerate(self.action_space):
                if action.action_type == ActionType.NO_OP:
                    valid_indices.append(i)
                    break
        
        return valid_indices




    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """执行动作并返回下一个状态、奖励、完成标志和额外信息"""
        self.episode_steps += 1
        
        # Decode action
        action_type, tool_name = self._decode_action(action)
        
        # 记录上一个动作到当前状态的metadata（用于下一步的奖励计算）
        if hasattr(self.current_state, 'metadata') and self.current_state.metadata is not None:
            self.current_state.metadata['last_action'] = action_type.value
        
        # 创建GeneralizedAction对象
        if action_type == ActionType.INVOKE_TOOL and tool_name:
            action_obj = GeneralizedAction(
                action_type=action_type,
                tool_name=tool_name
            )
        else:
            action_obj = GeneralizedAction(action_type=action_type)
        
        # 执行状态转换
        next_state, reward, done = self.mdp.step(self.current_state, action_obj)
        
        # 确保下一个状态也有当前的成功率信息
        if hasattr(next_state, 'metadata') and next_state.metadata is not None:
            next_state.metadata['current_success_rate'] = self.current_success_rate
            next_state.metadata['success_rate_threshold'] = self.success_rate_threshold
            # 保留required_tools信息
            if 'required_tools' in self.current_state.metadata:
                next_state.metadata['required_tools'] = self.current_state.metadata['required_tools']
        
        # 计算额外的奖励成分
        if self.use_phase2_scoring and done:
            # Phase 2评分
            required_tools = []
            # 修复：使用current_task_info而不是task_instance
            if hasattr(self, 'current_task_info') and self.current_task_info:
                required_tools = self.current_task_info.get('required_tools', [])
            elif hasattr(self, 'current_task') and self.current_task:
                required_tools = getattr(self.current_task, 'required_tools', [])
            
            # 评估执行质量
            evaluation_details = self._evaluate_execution_quality(next_state)
            success_level = evaluation_details.get('success_level', 'failure')
            
            # 计算Phase 2奖励
            phase2_reward = 0.0
            required_coverage = evaluation_details.get('required_coverage', 0.0)
            sequence_score = evaluation_details.get('sequence_score', 0.0)
            retry_count = evaluation_details.get('retry_count', 0)
            
            if success_level == 'full_success':
                # 满分基础
                phase2_reward = 300
                
                # 效率奖励
                steps_taken = len(next_state.execution_sequence)
                expected_steps = len(required_tools) if required_tools else 10
                efficiency_ratio = expected_steps / max(steps_taken, 1)
                efficiency_bonus = min(50, efficiency_ratio * 30)
                phase2_reward += efficiency_bonus
                
                # 顺序正确性奖励
                if sequence_score >= 0.9:
                    phase2_reward += 30
                elif sequence_score >= 0.7:
                    phase2_reward += 15
                    
                # 无重试奖励
                if retry_count == 0:
                    phase2_reward += 20
                    
            elif success_level == 'partial_success':
                # 部分成功基础分
                phase2_reward = 100
                
                # 根据完成度调整
                phase2_reward += required_coverage * 100
                
                # 序列质量奖励
                phase2_reward += sequence_score * 50
                
            else:  # failure
                # 失败惩罚
                phase2_reward = -100
                
                # 根据进度给予部分分数
                if required_coverage > 0.5:
                    phase2_reward += required_coverage * 50
            
            # 用Phase2奖励替换原始奖励
            reward = phase2_reward
            
            phase2_metrics = {
                'phase2_score': phase2_reward / 300,
                'success_level': success_level,
                'retry_count': retry_count,
                'required_coverage': required_coverage,
                'sequence_correctness': sequence_score
            }
        else:
            phase2_metrics = {}
        
        # Info dict
        info = {
            'success': next_state.is_successful,
            'progress': next_state.overall_progress,
            'tools_used': len([s for s in next_state.tool_states.values() 
                            if s == ToolExecutionStatus.SUCCESS]),
            'errors': next_state.total_errors,
            'phase2_metrics': phase2_metrics,
            'episode_steps': self.episode_steps,
            'reward': reward,  # 保存原始奖励值
            # 修复：使用正确的属性
            'required_tools': [],
            'required_coverage': phase2_metrics.get('required_coverage', 0.0),
            'sequence_correctness': phase2_metrics.get('sequence_correctness', 0.0)
        }
        
        # 添加required_tools到info
        if hasattr(self, 'current_task_info') and self.current_task_info:
            info['required_tools'] = self.current_task_info.get('required_tools', [])
        elif hasattr(self, 'current_task') and self.current_task:
            info['required_tools'] = getattr(self.current_task, 'required_tools', [])
        
        # ========== 奖励归一化处理（修复版） ==========
        # 初始化奖励历史和归一化设置
        if not hasattr(self, 'phase2_reward_history'):
            self.phase2_reward_history = []
            self.base_reward_history = []
            self.phase2_stats = {'mean': 0.0, 'std': 100.0}
            self.base_stats = {'mean': 0.0, 'std': 15.0}
            self.reward_update_count = 0
            self.reward_update_frequency = 10
            self.min_reward_std = 1.0
            # 修复：从环境初始化时获取配置，而不是从mdp.config
            self.normalize_rewards = True  # 默认启用归一化
        
        # 记录原始奖励
        info['raw_reward'] = reward
        info['reward_mode'] = 'phase2' if (self.use_phase2_scoring and done) else 'base'
        
        # 根据模式更新对应的历史
        if self.use_phase2_scoring and done:
            self.phase2_reward_history.append(reward)
            if len(self.phase2_reward_history) > 1000:
                self.phase2_reward_history.pop(0)
            history_to_use = self.phase2_reward_history
            stats_to_use = self.phase2_stats
        else:
            self.base_reward_history.append(reward)
            if len(self.base_reward_history) > 1000:
                self.base_reward_history.pop(0)
            history_to_use = self.base_reward_history
            stats_to_use = self.base_stats
        
        # 定期更新统计信息
        self.reward_update_count += 1
        if self.reward_update_count >= self.reward_update_frequency and len(history_to_use) > 10:
            rewards_array = np.array(history_to_use)
            stats_to_use['mean'] = np.mean(rewards_array)
            stats_to_use['std'] = max(self.min_reward_std, np.std(rewards_array))
            self.reward_update_count = 0
            
            # 调试信息
            if self.episode_steps == 1:
                print(f"[NORMALIZE] {info['reward_mode']} mode - Mean: {stats_to_use['mean']:.2f}, "
                    f"Std: {stats_to_use['std']:.2f}, Range: [{np.min(rewards_array):.2f}, {np.max(rewards_array):.2f}]")
        
        # 应用归一化
        if self.normalize_rewards and len(history_to_use) > 10:
            # 使用自适应归一化
            normalized_reward = (reward - stats_to_use['mean']) / stats_to_use['std']
            
            # 自适应裁剪
            if len(history_to_use) > 50:
                percentile_low = np.percentile(history_to_use, 1)
                percentile_high = np.percentile(history_to_use, 99)
                
                if reward < percentile_low:
                    normalized_reward = normalized_reward * 0.5
                elif reward > percentile_high:
                    normalized_reward = normalized_reward * 0.8
            
            # 最终裁剪
            if self.use_phase2_scoring and done:
                clip_range = (-3.0, 3.0)
            else:
                clip_range = (-5.0, 5.0)
            
            normalized_reward = np.clip(normalized_reward, clip_range[0], clip_range[1])
            
            info['normalized_reward'] = normalized_reward
            info['reward_mean'] = stats_to_use['mean']
            info['reward_std'] = stats_to_use['std']
            
            final_reward = normalized_reward
        else:
            # 数据不足时的初始化策略
            if self.use_phase2_scoring and done:
                # Phase2模式：中心100，范围[-100, 300]
                final_reward = (reward - 100.0) / 200.0
            else:
                # 基础模式：中心0，范围[-10, 10]
                final_reward = reward / 10.0
            
            final_reward = np.clip(final_reward, -2.0, 2.0)
            info['scaled_reward'] = final_reward
            info['scaling_mode'] = 'initial'
        
        # 注意：删除了错误的覆盖！
        # final_reward = reward  # <- 这行必须删除！
        
        # 更新当前状态
        self.current_state = next_state
        
        # 计算RAG上下文
        if hasattr(self, '_compute_rag_context_for_state'):
            self.last_rag_context = self._compute_rag_context_for_state(next_state)
            # 预计算embedding
            if self.mdp.embedding_manager:
                self.last_rag_embedding = self._encode_rag_embedding(self.last_rag_context)
        
        # 返回归一化后的奖励
        return self._encode_state(), final_reward, done, info

        def _compute_rag_context_for_state(self, state: GeneralizedMDPState) -> Dict[str, List]:
            """计算当前状态的RAG上下文"""
            rag_context = {}
            
            if not self.mdp.embedding_manager:
                return rag_context
            
            # 基于任务目标和当前进度构建搜索查询
            task_desc = state.task_objective
            
            # 1. 基于整体任务描述的搜索
            if task_desc:
                search_results = self.mdp.embedding_manager.search(
                    query=task_desc,
                    k=10,
                    return_scores=True
                )
                rag_context['task_description'] = search_results
            
            # 2. 基于当前状态的工具搜索
            if state.execution_sequence:
                last_tool = state.execution_sequence[-1]
                query = f"next step after {last_tool} for {task_desc}"
                search_results = self.mdp.embedding_manager.search(
                    query=query,
                    k=5,
                    return_scores=True
                )
                rag_context['next_step'] = search_results
            
            return rag_context

        def _encode_rag_embedding(self, rag_context: Dict[str, List]) -> np.ndarray:
            """将RAG上下文编码为固定维度的向量"""
            rag_dim = self.mdp.config.get('rag_dim', 64)
            
            if not rag_context:
                return np.zeros(rag_dim)
            
            # 简单的编码策略：对所有搜索结果的分数进行加权平均
            all_scores = []
            for results in rag_context.values():
                for _, score in results:
                    all_scores.append(score)
            
            if not all_scores:
                return np.zeros(rag_dim)
            
            # 创建一个基于分数分布的特征向量
            embedding = np.zeros(rag_dim)
            
            # 统计特征
            embedding[0] = np.mean(all_scores)
            embedding[1] = np.std(all_scores)
            embedding[2] = np.max(all_scores) if all_scores else 0
            embedding[3] = np.min(all_scores) if all_scores else 0
            embedding[4] = len(all_scores)
            
            # 分数直方图
            hist, _ = np.histogram(all_scores, bins=min(10, rag_dim - 5))
            embedding[5:5+len(hist)] = hist / (len(all_scores) + 1e-8)
            
            return embedding

        def _evaluate_success_level(self, state: GeneralizedMDPState, 
                                execution_history: List[ToolExecutionResult],  # <- 修改了这一行：将 ToolExecutionEntry 改为 ToolExecutionResult
                                tool_calls: List[str],
                                required_tools: List[str]) -> Tuple[str, Dict]:
            """评估任务完成的成功级别 - 使用语义分析和更严格的判定"""
            evaluation_details = {
                'state_completed': state.is_completed,
                'required_tools_coverage': 0.0,
                'semantic_completion': 0.0,
                'has_output': False,
                'recovery_success': False,
                'successful_tools': 0,
                'task_coherence': 0.0,  # 新增：任务连贯性评分
                'critical_steps_completed': False  # 新增：关键步骤完成
            }
            
            # 使用配置的阈值
            thresholds = self.task_manager.scoring_thresholds if hasattr(self.task_manager, 'scoring_thresholds') else ScoringThresholds()
            logger.debug(f" Using thresholds: partial_coverage={thresholds.partial_success_coverage}")
            
            # 1. 检查required_tools覆盖率
            if required_tools:
                successful_required = sum(1 for tool in required_tools
                                        if any(h.tool_name == tool and h.success 
                                            for h in execution_history))
                evaluation_details['required_tools_coverage'] = successful_required / len(required_tools)
            else:
                evaluation_details['required_tools_coverage'] = 1.0
            
            # 2. 检查输出生成
            output_keywords = [
                'writer', 'export', 'save', 'output', 'post', 
                'publish', 'store', 'emit', 'notify', 'report', 
                'generate', 'filter', 'aggregator', 'compressor'
            ]
            
            for exec_result in execution_history:
                if exec_result.success:
                    tool_lower = exec_result.tool_name.lower()
                    if any(keyword in tool_lower for keyword in output_keywords):
                        evaluation_details['has_output'] = True
                        break
            
            # 3. 计算成功工具数
            evaluation_details['successful_tools'] = sum(1 for r in execution_history if r.success)
            
            # 4. 部分成功判定条件
            partial_success_conditions = []
            
            # 条件A：完成了大部分required_tools（>=60%）
            if required_tools and evaluation_details['required_tools_coverage'] >= thresholds.partial_success_coverage:
                partial_success_conditions.append(f"Completed {evaluation_details['required_tools_coverage']:.0%} of required tools")
            
            # 条件B：有输出生成
            if evaluation_details['has_output']:
                partial_success_conditions.append("Generated output")
            
            # 条件C：达到了特定任务类型的最低要求
            task_min_requirements = thresholds.task_min_requirements
            min_required = task_min_requirements.get(state.task_type, 2)
            if evaluation_details['successful_tools'] >= min_required:
                partial_success_conditions.append(f"Met minimum tool requirement ({evaluation_details['successful_tools']}/{min_required})")
            
            # 5. 判定逻辑
            if state.is_completed and state.is_successful:
                # 完全成功
                return "full_success", evaluation_details
            elif len(partial_success_conditions) >= 2:
                # 部分成功：至少满足2个条件
                evaluation_details['success_reasons'] = partial_success_conditions
                return "partial_success", evaluation_details
            else:
                # 失败
                evaluation_details['failure_reasons'] = [
                    f"Required tools coverage: {evaluation_details['required_tools_coverage']:.0%}",
                    f"Successful tools: {evaluation_details['successful_tools']}",
                    f"Has output: {evaluation_details['has_output']}"
                ]
                return "failure", evaluation_details
        

        def _calculate_sequence_coherence(self, tool_sequence: List[str]) -> float:
            """计算工具序列的连贯性得分"""
            if len(tool_sequence) < 2:
                return 1.0
            
            coherence_score = 0.0
            valid_transitions = 0
            
            # 检查每个相邻工具对的合理性
            for i in range(len(tool_sequence) - 1):
                current_tool = tool_sequence[i]
                next_tool = tool_sequence[i + 1]
                
                # 使用语义搜索检查转换合理性
                query = f"tools that naturally follow after {current_tool}"
                results = self.task_manager.embedding_manager.search(query, k=10, return_scores=True)
                
                for result in results:
                    if result.tool_name == next_tool and result.score > 0.6:
                        valid_transitions += 1
                        break

            
            coherence_score = valid_transitions / (len(tool_sequence) - 1)
            return coherence_score

        def _is_valid_transition_by_category(self, current_tool: str, next_tool: str) -> bool:
            """基于工具类别判断转换是否合理"""
            # 定义合理的类别转换
            valid_transitions = {
                'reader': ['validator', 'parser', 'transformer', 'filter'],
                'scanner': ['reader', 'validator', 'parser'],
                'validator': ['transformer', 'filter', 'aggregator'],
                'transformer': ['validator', 'writer', 'aggregator'],
                'filter': ['aggregator', 'writer', 'transformer'],
                'aggregator': ['writer', 'exporter'],
                'parser': ['transformer', 'validator', 'filter']
            }
            
            # 获取工具类别
            current_category = None
            next_category = None
            
            for category in valid_transitions.keys():
                if category in current_tool.lower():
                    current_category = category
                if category in next_tool.lower():
                    next_category = category
            
            if current_category and next_category:
                return next_category in valid_transitions.get(current_category, [])
            
            # 默认允许
            return True

        def _check_pipeline_stages_semantically(self, successful_tools: set) -> bool:
            """使用语义分析检查管道阶段是否完整"""
            if hasattr(self.task_manager, 'embedding_manager') and self.task_manager.embedding_manager:
                # 语义分析管道阶段
                pipeline_stages = [
                    "data input or reading stage",
                    "data transformation or processing stage", 
                    "data output or writing stage"
                ]
                
                stages_completed = 0
                for stage_query in pipeline_stages:
                    try:
                        results = self.task_manager.embedding_manager.search(stage_query, k=10, return_scores=True)
                        for result in results:
                            if result.tool_name in successful_tools and result.score > 0.7:
                                stages_completed += 1
                                logger.debug(f" Stage '{stage_query}' completed by {result.tool_name}")
                                break
                    except:
                        pass
                
                return stages_completed >= 3
            
            else:
                # 回退到简单检查
                stage_keywords = ['read', 'transform', 'write', 'parse', 'validate']
                stages_found = sum(1 for keyword in stage_keywords 
                                if any(keyword in tool.lower() for tool in successful_tools))
                return stages_found >= 3

        def _check_output_generated(self, execution_history):
            """检查是否生成了输出"""
            output_keywords = [
                'writer', 'export', 'save', 'output', 'post', 
                'publish', 'store', 'emit', 'filter', 'aggregator', 'compressor'
            ]
            
            for exec_result in execution_history:
                if exec_result.success:
                    tool_lower = exec_result.tool_name.lower()
                    if any(keyword in tool_lower for keyword in output_keywords):
                        return True
            return False

# ===========================
# Replay Buffer
# ===========================

# 相同位置的修复代码
# 修改的行用注释标注：# <- 修改了这一行

class ReplayBuffer:
    """Experience replay buffer for DQN training"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
    
    def push(self, state, action, reward, next_state, done, task_type=None):  # <- 修改了这一行：添加task_type参数
        """Store a transition"""
        self.buffer.append((state, action, reward, next_state, done, task_type))  # <- 修改了这一行：存储task_type
    
    def sample(self, batch_size: int):
        """Sample a batch of transitions"""
        batch = random.sample(self.buffer, batch_size)
        
        states = torch.FloatTensor([t[0] for t in batch]).to(device)
        actions = torch.LongTensor([t[1] for t in batch]).to(device)
        rewards = torch.FloatTensor([t[2] for t in batch]).to(device)
        next_states = torch.FloatTensor([t[3] for t in batch]).to(device)
        dones = torch.FloatTensor([t[4] for t in batch]).to(device)
        
        return states, actions, rewards, next_states, dones
    
    def __len__(self):
        return len(self.buffer)

# ===========================
# Task-Aware Memory System
# ===========================

class TaskAwareMemory:
    """Task-aware experience memory with balanced sampling"""
    
    def __init__(self, capacity_per_task: int = 10000, min_samples_per_task: int = 100):
        self.capacity_per_task = capacity_per_task
        self.min_samples_per_task = min_samples_per_task
        self.task_buffers = {}  # task_type -> ReplayBuffer
        self.task_counts = defaultdict(int)  # 统计每个任务的经验数
        self.global_buffer = ReplayBuffer(capacity_per_task * 5)  # 全局缓冲区
        
    def push(self, state, action, reward, next_state, done, task_type=None):
        """Store experience with task awareness"""
        # 存储到全局缓冲区
        self.global_buffer.push(state, action, reward, next_state, done, task_type)
        
        # 如果有任务类型，也存储到任务特定缓冲区
        if task_type:
            if task_type not in self.task_buffers:
                self.task_buffers[task_type] = ReplayBuffer(self.capacity_per_task)
            
            self.task_buffers[task_type].push(state, action, reward, next_state, done, task_type)
            self.task_counts[task_type] += 1
    
    def sample(self, batch_size: int, current_task_type=None, mix_ratio=0.7):
        """Sample with task-aware mixing strategy"""
        if len(self.global_buffer) < batch_size:
            return None
        
        # 如果指定了当前任务类型，混合采样
        if current_task_type and current_task_type in self.task_buffers:
            current_task_samples = int(batch_size * mix_ratio)
            other_samples = batch_size - current_task_samples
            
            # 从当前任务采样
            current_batch = []
            if len(self.task_buffers[current_task_type]) >= current_task_samples:
                current_batch = self._sample_from_buffer(
                    self.task_buffers[current_task_type], 
                    current_task_samples
                )
            
            # 从其他任务均衡采样
            other_batch = self._sample_balanced(other_samples, exclude_task=current_task_type)
            
            # 合并批次
            all_transitions = current_batch + other_batch
            
        else:
            # 均衡采样所有任务
            all_transitions = self._sample_balanced(batch_size)
        
        # 转换为张量
        return self._transitions_to_tensors(all_transitions)
    
    def _sample_balanced(self, num_samples, exclude_task=None):
        """Balanced sampling across task types"""
        available_tasks = [t for t in self.task_buffers.keys() if t != exclude_task]
        
        if not available_tasks:
            # 从全局缓冲区采样
            return self._sample_from_buffer(self.global_buffer, num_samples)
        
        samples_per_task = max(1, num_samples // len(available_tasks))
        remaining = num_samples - (samples_per_task * len(available_tasks))
        
        all_samples = []
        for task_type in available_tasks:
            buffer = self.task_buffers[task_type]
            if len(buffer) > 0:
                n_samples = min(samples_per_task, len(buffer))
                all_samples.extend(self._sample_from_buffer(buffer, n_samples))
        
        # 填充剩余样本
        if remaining > 0 and len(all_samples) < num_samples:
            extra_samples = self._sample_from_buffer(
                self.global_buffer, 
                min(remaining, num_samples - len(all_samples))
            )
            all_samples.extend(extra_samples)
        
        random.shuffle(all_samples)
        return all_samples[:num_samples]
    
    def _sample_from_buffer(self, buffer, num_samples):
        """Sample from a specific buffer"""
        if isinstance(buffer, ReplayBuffer):
            # 临时方法：直接从buffer的内部deque采样
            return random.sample(buffer.buffer, min(num_samples, len(buffer.buffer)))
        return []
    
    def _transitions_to_tensors(self, transitions):
        """Convert transitions to tensors"""
        if not transitions:
            return None
            
        states = torch.FloatTensor([t[0] for t in transitions]).to(device)
        actions = torch.LongTensor([t[1] for t in transitions]).to(device)
        rewards = torch.FloatTensor([t[2] for t in transitions]).to(device)
        next_states = torch.FloatTensor([t[3] for t in transitions]).to(device)
        dones = torch.FloatTensor([t[4] for t in transitions]).to(device)
        
        return states, actions, rewards, next_states, dones
    
    def get_task_statistics(self):
        """Get memory statistics per task type"""
        stats = {}
        for task_type, buffer in self.task_buffers.items():
            stats[task_type] = {
                'count': len(buffer),
                'total_collected': self.task_counts[task_type]
            }
        return stats
    
    def __len__(self):
        return len(self.global_buffer)

# ===========================
# DQN Trainer
# ===========================


# class DQNTrainer(BaseTrainer):
    """DQN trainer implementation"""
    
    def __init__(self, env: 'MDPEnvironment', config: Dict[str, Any]):
        super().__init__(env, config)  # <- 修改：调用基类构造函数
        
        # Network
        state_dim = env.get_state_dim()
        action_dim = env.num_actions
        hidden_dim = config.get('hidden_dim', 256)
        
        self.q_network = DuelingDQN(state_dim, action_dim, hidden_dim).to(self.device)  # <- 修改：使用self.device
        self.target_network = DuelingDQN(state_dim, action_dim, hidden_dim).to(self.device)  # <- 修改
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Optimizer
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=config['learning_rate'])
        self.scheduler = ReduceLROnPlateau(self.optimizer, patience=10, factor=0.5)
        
        # Replay buffer - 使用任务感知记忆系统
        use_task_aware_memory = config.get('use_task_aware_memory', True)
        if use_task_aware_memory:
            self.memory = TaskAwareMemory(
                capacity_per_task=config.get('memory_size', 50000) // 5,
                min_samples_per_task=100
            )
            self.replay_buffer = self.memory  # 兼容性别名
        else:
            self.replay_buffer = ReplayBuffer(config['memory_size'])
        
        # Training parameters
        self.epsilon = config['epsilon_start']
        self.epsilon_decay = config['epsilon_decay']
        self.epsilon_min = config['epsilon_min']
        self.gamma = config['gamma']
        self.batch_size = config['batch_size']
        
        # Statistics
        self.target_update_counter = 0
        self.current_task_type = None
    
    def set_eval_mode(self, eval_mode: bool):  # <- 修改：重写基类方法
        """Set evaluation mode - disable exploration"""
        super().set_eval_mode(eval_mode)
        if eval_mode:
            self.stored_epsilon = self.epsilon
            self.epsilon = 0.0
        else:
            if hasattr(self, 'stored_epsilon'):
                self.epsilon = self.stored_epsilon
    
    def select_action(self, state: np.ndarray, valid_actions: Optional[List[int]] = None) -> int:
        """Select action using epsilon-greedy with optional masking"""
        # Epsilon-greedy
        if not self.eval_mode and random.random() < self.epsilon:  # <- 修改：检查eval_mode
            if valid_actions:
                return random.choice(valid_actions)
            else:
                return random.randint(0, self.env.num_actions - 1)
        
        # Greedy action
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)  # <- 修改：使用self.device
            q_values = self.q_network(state_tensor).squeeze()
            
            if valid_actions:
                # 使用基类的动作掩码方法  # <- 修改
                q_values = self.apply_action_mask(q_values, valid_actions)
                
            return q_values.argmax().item()
    
    def store_experience(self, state: np.ndarray, action: int, reward: float,  # <- 新增：实现统一接口
                        next_state: np.ndarray, done: bool, **kwargs) -> None:
        """Store experience in replay buffer"""
        task_type = kwargs.get('task_type', None)
        
        if isinstance(self.replay_buffer, TaskAwareMemory):
            self.replay_buffer.push(state, action, reward, next_state, done, task_type)
        else:
            self.replay_buffer.push(state, action, reward, next_state, done)

    def should_train(self) -> bool:  # <- 新增：判断是否应该训练
        """DQN trains when replay buffer has enough samples"""
        return len(self.replay_buffer) >= self.config['batch_size']
    
    def on_episode_end(self) -> None:  # <- 新增：episode结束处理
        """DQN doesn't need special episode end handling"""
        pass
    
    
    def train_step(self) -> float:
        """Perform one training step"""
        if len(self.replay_buffer) < self.batch_size:
            return 0.0
        
        # Sample batch - 使用任务感知采样
        if isinstance(self.replay_buffer, TaskAwareMemory):
            batch = self.replay_buffer.sample(
                self.batch_size,
                current_task_type=self.current_task_type,
                mix_ratio=0.7  # 70%来自当前任务，30%来自其他任务
            )
            if batch is None:
                return 0.0
            states, actions, rewards, next_states, dones = batch
        else:
            states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.batch_size)
        
        # Current Q values
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Next Q values (Double DQN)
        with torch.no_grad():
            # Select actions using online network
            next_actions = self.q_network(next_states).argmax(dim=1)
            # Evaluate using target network
            next_q_values = self.target_network(next_states).gather(1, next_actions.unsqueeze(1))
            target_q_values = rewards.unsqueeze(1) + self.gamma * next_q_values * (1 - dones.unsqueeze(1))
        
        # Loss
        loss = F.mse_loss(current_q_values, target_q_values)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        # Update target network
        self.training_steps += 1
        if self.training_steps % self.config['target_update_frequency'] == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
            self.target_update_counter += 1
        
        return loss.item()
    
    def update_exploration(self):
        """Update exploration rate"""
        # 添加基于训练步数的快速衰减
        if self.training_steps < 100:
            fast_decay_rate = 0.995
            self.epsilon = max(0.5, self.epsilon * fast_decay_rate)
        else:
            # 之后使用正常衰减率
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
    
    def save_checkpoint(self, path: str, additional_data: Dict[str, Any] = None):
        """Save training checkpoint"""
        state_dicts = {  # <- 修改：使用基类方法
            'q_network_state_dict': self.q_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon
        }
        
        # 保存任务感知记忆的统计信息
        extra_data = {}
        if isinstance(self.replay_buffer, TaskAwareMemory):
            extra_data['memory_stats'] = self.replay_buffer.get_task_statistics()
        
        if additional_data:
            extra_data.update(additional_data)
        
        self.save_checkpoint_base(path, state_dicts, extra_data)  # <- 修改：使用基类方法
    
    def load_checkpoint(self, path: str) -> Dict[str, Any]:
        """Load training checkpoint and return additional data"""
        checkpoint = self.load_checkpoint_base(path)  # <- 修改：使用基类方法
        
        self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint.get('epsilon', self.epsilon)
        
        return checkpoint
# ===========================
# Curriculum Learning
# ===========================

class CurriculumScheduler:
    """Manages curriculum learning progression"""
    
    def __init__(self, total_episodes: int, config: Optional[Dict[str, Any]] = None):
        self.total_episodes = total_episodes
        self.current_episode = 0
        
        # 从config读取stage_thresholds，如果没有则使用默认值
        if config and 'curriculum_stages' in config:
            self.stage_thresholds = config['curriculum_stages']
            print(f"[CURRICULUM] Loading stage thresholds from config: {self.stage_thresholds}")
        else:
            # 默认值：5个stages
            self.stage_thresholds = [0.1, 0.25, 0.5, 0.75]
            print(f"[CURRICULUM] Using default stage thresholds: {self.stage_thresholds}")
        
        # 从config读取stage names，如果没有则使用默认值
        if config and 'curriculum_stage_names' in config:
            self.stage_names = config['curriculum_stage_names']
        else:
            self.stage_names = ["Very Easy", "Easy", "Medium", "Hard", "Expert"]
        
        # 验证配置一致性
        num_stages = len(self.stage_thresholds) + 1
        if len(self.stage_names) < num_stages:
            # 如果名称不够，自动补充
            for i in range(len(self.stage_names), num_stages):
                self.stage_names.append(f"Stage {i}")
        
        # 添加详细的调试信息
        print(f"[CURRICULUM] Initialized with {total_episodes} total episodes")
        print(f"[CURRICULUM] Number of stages: {num_stages}")
        for i in range(len(self.stage_thresholds)):
            start_ep = int(total_episodes * (self.stage_thresholds[i-1] if i > 0 else 0))
            end_ep = int(total_episodes * self.stage_thresholds[i])
            print(f"[CURRICULUM] Stage {i}: episodes {start_ep}-{end_ep} "
                  f"({(self.stage_thresholds[i-1] if i > 0 else 0)*100:.0f}-{self.stage_thresholds[i]*100:.0f}%) "
                  f"- {self.stage_names[i]}")
        # 最后一个stage
        last_start = int(total_episodes * self.stage_thresholds[-1])
        print(f"[CURRICULUM] Stage {num_stages-1}: episodes {last_start}-{total_episodes} "
              f"({self.stage_thresholds[-1]*100:.0f}-100%) - {self.stage_names[num_stages-1]}")
        
        # 添加调试跟踪
        self.stage_history = []
        self.last_printed_stage = -1
    
    
    def get_stage(self) -> int:
        """Get current curriculum stage"""
        progress = self.current_episode / self.total_episodes
        
        # 添加进度打印（每100个episode打印一次）
        if self.current_episode % 100 == 0:
            print(f"[CURRICULUM] Episode {self.current_episode}/{self.total_episodes} "
                  f"(Progress: {progress:.1%})")
        
        for i, threshold in enumerate(self.stage_thresholds):
            if progress < threshold:
                return i
        
        return len(self.stage_thresholds)
    
    def get_stage_name(self) -> str:
        """Get human-readable stage name"""
        stage = self.get_stage()
        # 添加边界检查，确保不会越界
        if stage < len(self.stage_names):
            name = self.stage_names[stage]
        else:
            # 如果超出范围，使用默认格式
            name = f"Stage {stage}"
            print(f"[CURRICULUM WARNING] Stage {stage} exceeds defined names (max: {len(self.stage_names)-1})")
        
        progress = self.current_episode / self.total_episodes
        return f"{name} (Stage {stage}, Progress: {progress:.1%})"
    

    def update(self):
        """Update progress"""
        # 先获取当前stage
        old_stage = self.get_stage()
        
        # 更新episode计数
        self.current_episode += 1
        
        # 获取新的stage
        new_stage = self.get_stage()
        
        # 记录stage历史
        self.stage_history.append((self.current_episode, new_stage))
        
        # 检查是否进入新阶段
        if new_stage != old_stage:
            print(f"[CURRICULUM] 🎯 Advancing from Stage {old_stage} to Stage {new_stage} "
                f"at episode {self.current_episode}")
            print(f"[CURRICULUM] Progress: {self.current_episode}/{self.total_episodes} = "
                f"{self.current_episode/self.total_episodes:.1%}")
            
            # 显示新stage的特点
            stage_descriptions = {
                0: "Very Easy - Minimal requirements, high tolerance",
                1: "Easy - Basic requirements, moderate tolerance", 
                2: "Medium - Standard requirements, balanced difficulty",
                3: "Hard - Strict requirements, low tolerance",
                4: "Expert - Full requirements, minimal tolerance"
            }
            if new_stage in stage_descriptions:
                print(f"[CURRICULUM] Stage {new_stage}: {stage_descriptions[new_stage]}")
        
            # 每500个episode打印一次详细状态
            if self.current_episode % 500 == 0:
                print(f"[CURRICULUM DEBUG] Current episode: {self.current_episode}, "
                    f"Total episodes: {self.total_episodes}, "
                    f"Stage: {new_stage}, "
                    f"Progress: {self.current_episode/self.total_episodes:.1%}")

# ===========================
# Unified Training Manager (Refactored)
# ===========================

class UnifiedTrainingManager:
    def __init__(self, algorithm: str = 'ppo', 
                checkpoint_dir: str = "checkpoints",
                config_path: Optional[str] = None,
                use_task_aware_state: bool = True,
                use_phase2_scoring: bool = True,
                enforce_workflow: bool = True,
                thresholds: Optional['ScoringThresholds'] = None,
                task_types: Optional[List[str]] = None):
        
        self.algorithm = algorithm.lower()
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Task configuration
        self.use_task_aware_state = use_task_aware_state
        self.use_phase2_scoring = use_phase2_scoring
        self.enforce_workflow = enforce_workflow
        self.thresholds = thresholds
        self.task_types = task_types
        
        # Initialize components
        self.env = None
        self.trainer = None
        self.task_manager = None
        self.mdp = None
        
        # Training state
        self.training_history = defaultdict(list)
        # 确保关键的键被初始化
        self.training_history['rewards'] = []
        self.training_history['success'] = []
        self.training_history['lengths'] = []
        print(f"[DEBUG] Initialized training_history with keys: {list(self.training_history.keys())}")
                
        # Stage-aware best model tracking
        self.best_success_rate = 0.0  # 修复：从-1.0改为0.0，避免显示-100%
        self.stage_best_success_rates = {}  # 当前训练的每个stage最佳成功率
        self.stage_best_weighted_rates = {}  # 新增：每个stage的加权成功率
        self.best_model_stages = {}  # 保存的best model的stage成功率
        self.best_weighted_success_rate = 0.0  # 新增：最佳加权成功率
        self.weighted_best_score = 0.0  # 修复：从-1.0改为0.0
        self.best_model_path = None
        self.current_stage = 0
        self.stage_transition_episodes = []  # 记录stage转换的episode
        self.last_best_update_episode = 0  # 新增：初始化last_best_update_episode

        
        print(f"[UnifiedTrainingManager] Initialized with stage-aware best model tracking")
        
        # Success rate evaluation weights based on stage
        self.stage_weights = {
            0: 0.1,  # Stage 0的成功率权重很低
            1: 0.3,  # Stage 1权重适中
            2: 0.7,  # Stage 2权重较高
            3: 1.0,  # Stage 3+权重最高
        }
        
        # 初始化 LLM 客户端（如果需要）
        self.llm_client = None
        if self.config.get('use_teacher_guidance', False) or self.enforce_workflow:
            self.llm_client = self._get_llm_client()
            
        if self.thresholds:
            logger.info(f"Using scoring thresholds: semantic_match={self.thresholds.semantic_match_threshold}, "
                        f"partial_success={self.thresholds.partial_success_coverage}")
        
        logger.info("UnifiedTrainingManager initialized")
        logger.info(f"Algorithm: {self.algorithm}")
        logger.info(f"Task-aware state: {self.use_task_aware_state}")
        logger.info(f"Workflow enforcement: {self.enforce_workflow}")
        logger.info(f"Phase 2 scoring: {self.use_phase2_scoring}")


    def calculate_weighted_success_rate(self, episode_history: List[Dict]) -> float:
        """计算考虑成功级别的加权成功率
        
        Args:
            episode_history: 最近若干episode的历史记录，每个包含 'success_level' 字段
            
        Returns:
            加权成功率 (0.0 - 1.0)
        """
        if not episode_history:
            return 0.0
        
        # 成功级别权重定义
        success_level_weights = {
            'full_success': 1.0,      # 完全成功
            'partial_success': 0.0,   # 部分成功
            'failure': 0.0,           # 失败
        }
        
        weighted_sum = 0.0
        for episode_data in episode_history:
            # 获取成功级别，默认为failure
            success_level = episode_data.get('success_level', 'failure')
            weight = success_level_weights.get(success_level, 0.0)
            weighted_sum += weight
        
        return weighted_sum / len(episode_history)


    def update_best_model(self, episode: int, recent_success_rate: float, 
                        current_stage: int, save_callback=None, 
                        recent_episode_history: List[Dict] = None):
        """Stage-aware best model update logic using lexicographic ordering
        自适应支持任意数量的stages，并考虑成功级别
        
        Args:
            episode: 当前episode号
            recent_success_rate: 最近的二元成功率（向后兼容）
            current_stage: 当前课程阶段
            save_callback: 保存模型的回调函数
            recent_episode_history: 最近episode的详细历史，包含success_level信息
        """
        
        # 更新当前stage
        if current_stage != self.current_stage:
            self.stage_transition_episodes.append(episode)
            print(f"[BestModel] Stage transition at episode {episode}: {self.current_stage} -> {current_stage}")
            self.current_stage = current_stage
        
        # 计算加权成功率（如果有详细历史）
        if recent_episode_history:
            weighted_success_rate = self.calculate_weighted_success_rate(recent_episode_history)
            print(f"[BestModel] Binary success rate: {recent_success_rate:.2%}, "
                f"Weighted success rate: {weighted_success_rate:.2%}")
            # 使用加权成功率进行比较
            comparison_rate = weighted_success_rate
        else:
            # 向后兼容：如果没有详细历史，使用二元成功率
            comparison_rate = recent_success_rate
            weighted_success_rate = recent_success_rate
        
        # 更新当前stage的成功率（使用加权成功率）
        if current_stage not in self.stage_best_success_rates:
            self.stage_best_success_rates[current_stage] = 0.0
        
        # 同时维护二元和加权成功率
        if current_stage not in self.stage_best_weighted_rates:
            self.stage_best_weighted_rates[current_stage] = 0.0  # 修复：只初始化当前stage，不要重置整个字典
        
        # 判断当前stage是否有改进（使用加权成功率）
        stage_improved = comparison_rate > self.stage_best_success_rates[current_stage]
        if stage_improved:
            self.stage_best_success_rates[current_stage] = comparison_rate
            self.stage_best_weighted_rates[current_stage] = weighted_success_rate
            print(f"[BestModel] New best for stage {current_stage}: {comparison_rate:.2%} (weighted)")
        
        # 字典序比较：优先比较高stage
        should_update = False
        update_reason = ""
        
        # 获取已保存的best model的stage信息
        saved_best_stages = getattr(self, 'best_model_stages', {})
        
        # 动态获取最大stage数
        # 方法1：从curriculum获取（如果可用）
        if hasattr(self, 'env') and hasattr(self.env, 'curriculum'):
            curriculum = self.env.curriculum
            if hasattr(curriculum, 'stage_thresholds'):
                max_stages = len(curriculum.stage_thresholds) + 1  # +1 因为还有最后一个stage
            else:
                max_stages = 4  # 默认值
        else:
            # 方法2：从已知的stage中推断
            known_stages = set(self.stage_best_success_rates.keys()) | set(saved_best_stages.keys())
            max_stages = max(known_stages, default=3) + 1  # 至少支持到当前最大stage+1
        
        print(f"[BestModel] Using max_stages={max_stages} for comparison")
        
        # 新增：首次到达更高stage的特殊处理
        current_max_stage = max(self.stage_best_success_rates.keys(), default=-1)
        saved_max_stage = max(saved_best_stages.keys(), default=-1)
        
        # 如果当前模型到达了更高的stage，并且在该stage有任何成功（即使很低）
        if current_max_stage > saved_max_stage:
            # 检查新stage是否有任何成功
            new_stage_rate = self.stage_best_success_rates.get(current_max_stage, 0.0)
            if new_stage_rate > 0:  # 只要有成功就更新
                should_update = True
                update_reason = f"Reached new stage {current_max_stage} with {new_stage_rate:.2%} success"
                print(f"[BestModel] Prioritizing new stage achievement!")
        
        # 如果不是新stage，则进行标准的字典序比较
        if not should_update:
            # 从最高可能的stage开始比较
            for stage in range(max_stages - 1, -1, -1):  # 动态范围
                current_rate = self.stage_best_success_rates.get(stage, 0.0)
                saved_rate = saved_best_stages.get(stage, 0.0)
                
                if current_rate > saved_rate:
                    # 当前模型在这个stage上更好
                    should_update = True
                    update_reason = f"Better at stage {stage}: {current_rate:.2%} > {saved_rate:.2%}"
                    break
                elif current_rate < saved_rate:
                    # 当前模型在这个stage上更差，不更新
                    should_update = False
                    update_reason = f"Worse at stage {stage}: {current_rate:.2%} < {saved_rate:.2%}"
                    break
                # 如果相等，继续比较下一个stage
            
            # 如果所有stage都相等，保持现状
            if not update_reason:
                should_update = False
                update_reason = "All stages equal, keeping current best"
        
        # 打印比较详情
        print(f"[BestModel] Lexicographic comparison at episode {episode}:")
        print(f"  Current stages: {dict(sorted(self.stage_best_success_rates.items()))}")
        print(f"  Saved best stages: {dict(sorted(saved_best_stages.items()))}")
        print(f"  Decision: {update_reason}")
        
        # 更新best model
        if should_update:
            # 保存当前的stage成功率作为新的best
            self.best_model_stages = self.stage_best_success_rates.copy()
            self.best_success_rate = comparison_rate
            self.best_weighted_success_rate = weighted_success_rate
            self.last_best_update_episode = episode
            
            print(f"[BestModel] ✅ Updating best model at episode {episode}")
            print(f"  Current stage: {current_stage}, Success Rate: {comparison_rate:.2%}")
            print(f"  Weighted Success Rate: {weighted_success_rate:.2%}")
            print(f"  Update reason: {update_reason}")
            
            # 调用保存回调
            if save_callback:
                save_callback(is_best=True)
            
            # 保存stage信息到文件
            self.best_model_path = self.checkpoint_dir / "best_model.pt"
            stage_info_path = self.checkpoint_dir / "best_model_stage_info.json"
            stage_info = {
                'episode': episode,
                'current_stage': current_stage,
                'recent_success_rate': recent_success_rate,
                'weighted_success_rate': weighted_success_rate,
                'stage_best_rates': self.stage_best_success_rates,
                'stage_best_weighted_rates': self.stage_best_weighted_rates,  # 现在这个字典不会被清空了
                'saved_best_stages': self.best_model_stages,
                'update_reason': update_reason,
                'max_stages_detected': max_stages,
                'timestamp': datetime.now().isoformat()
            }
            with open(stage_info_path, 'w') as f:
                json.dump(stage_info, f, indent=2)
            
            # 保存更新历史记录（新增功能）
            history_path = self.checkpoint_dir / "best_model_update_history.json"
            history_entry = {
                'episode': episode,
                'timestamp': datetime.now().isoformat(),
                'current_stage': current_stage,
                'recent_success_rate': recent_success_rate,
                'weighted_success_rate': weighted_success_rate,
                'stage_best_rates': self.stage_best_success_rates.copy(),
                'update_reason': update_reason,
                'training_steps': self.trainer.training_steps if hasattr(self.trainer, 'training_steps') else 0
            }
            
            # 加载现有历史或创建新的
            if history_path.exists():
                with open(history_path, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            history.append(history_entry)
            
            # 保存更新后的历史
            with open(history_path, 'w') as f:
                json.dump(history, f, indent=2)
            
            print(f"[BestModel] Update history saved ({len(history)} entries)")
        else:
            print(f"[BestModel] ❌ Not updating best model")
            print(f"  Reason: {update_reason}")
        
        return should_update
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load or create default configuration"""
        default_config = {
            # DQN parameters
            'learning_rate': 0.0003,
            'batch_size': 64,
            'memory_size': 50000,
            'gamma': 0.95,
            'epsilon_start': 0.3,
            'epsilon_decay': 0.995,
            'epsilon_min': 0.01,
            'target_update_frequency': 50,
            'hidden_dim': 256,
            
            # Training parameters
            'checkpoint_mode': 'full',
            'checkpoint_frequency': 100,
            'checkpoint_keep_recent': 3,
            'checkpoint_keep_interval': 500,
            'checkpoint_size_limit_mb': 500,
            'evaluation_frequency': 50,
            'evaluation_episodes': 10,
            'max_episode_length': 100,  # 🔧 关键修改：从30增加到100
            
            # PPO specific (如果使用PPO)
            'n_steps': 256,
            'n_epochs': 4,
            'clip_range': 0.2,
            
            # Teacher guidance for PPO
            'use_teacher_guidance': False,
            'teacher_guidance_start_prob': 0.01,
            'teacher_guidance_decay': 0.995,
            'teacher_guidance_min_prob': 0.005,
            'episode_guidance_mode': True,
            
            # TaskAwareRolloutBuffer配置
            'use_task_aware_buffer': True,
            'buffer_capacity_per_task': 100,
            'min_episodes_per_task': 10,
            'prioritize_medium_reward': True,
            
            # Curriculum learning
            'use_curriculum': True,
            
            # Action masking
            'use_action_masking': True
        }
    
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
        else:
            raise ValueError("Config file doesnot exist")
        
        return default_config

    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from config directory
        
        Returns:
            dict: Configuration dictionary or empty dict if not found
        """
        # 使用 APIClientManager 的配置
        from api_client_manager import APIClientManager
        manager = APIClientManager()
        return manager._config

    def _get_llm_client(self):
        """Initialize and return LLM client based on environment configuration
        
        Returns:
            OpenAI or AzureOpenAI client instance
        """
        from api_client_manager import get_api_client
        return get_api_client() 


    def setup_environment(self, 
                        tool_registry_path: str = "./mcp_generated_library/tool_registry_consolidated.json",
                        task_library_path: str = "mcp_generated_library/task_library_all_difficulties.json") -> bool:
        """Setup training environment"""
        logger.info("Setting up training environment...")
        
        # Load MDPWorkflowGenerator if needed
        MDPWorkflowGenerator = None
        if self.enforce_workflow:
            try:
                from mdp_workflow_generator import MDPWorkflowGenerator
            except ImportError:
                logger.warning("MDPWorkflowGenerator not available, workflow enforcement disabled")
                self.enforce_workflow = False
        
        # Load Phase 2 components
        StableScorer = None
        if self.use_phase2_scoring:
            try:
                from stable_scorer import StableScorer
                PHASE2_AVAILABLE = True
                logger.info("Phase 2 scoring components loaded")
            except ImportError:
                logger.warning("Phase 2 components not available")
                PHASE2_AVAILABLE = False
                self.use_phase2_scoring = False
        else:
            PHASE2_AVAILABLE = False
        
        if not os.path.exists(tool_registry_path):
            logger.error(f"Tool registry not found: {tool_registry_path}")
            return False
        
        # Try multiple tool registry paths
        tool_paths = [
            Path(tool_registry_path),
            Path("mcp_generated_library/tool_registry_consolidated.json"),
            Path("mcp_generated_library/tool_registry.json"),
            Path("tool_registry.json")
        ]
        
        tool_capabilities = None
        for path in tool_paths:
            if path.exists():
                tool_capabilities = load_tool_capabilities(str(path))
                logger.info(f"Loaded tools from {path}")
                break
        
        if not tool_capabilities:
            logger.error("No tool capabilities loaded!")
            return False
        
        # Create MDP
        self.mdp = GeneralizedMDP(tool_capabilities)
        
        # Load tasks
        self.task_manager = TaskManager(task_library_path, task_types=self.task_types)
        
        # If no tasks were loaded from files, ensure we have sample tasks
        if not self.task_manager.tasks:
            logger.warning("No tasks loaded from files, using sample tasks")
            self.task_manager._create_sample_tasks()
        
        if not self.task_manager.tasks:
            logger.error("Failed to create any tasks!")
            return False
        
        # Create environment（先不传入trainer）
        self.env = MDPEnvironment(
            self.mdp, 
            self.task_manager,
            use_task_aware_state=self.use_task_aware_state,
            enforce_workflow=self.enforce_workflow,
            use_phase2_scoring=self.use_phase2_scoring,
            normalize_rewards=self.config.get('normalize_rewards', True)  # 传入归一化配置
        )
        
        logger.info(f"Environment created with {len(self.task_manager.tasks)} tasks")
        logger.info(f"Task types: {list(self.task_manager.tasks_by_type.keys())}")
        logger.info(f"State dimension: {self.env.get_state_dim()}")
        logger.info(f"Action space: {self.env.num_actions} actions")
        
        # 创建trainer
        if not self.trainer:
            # 现在可以从环境获取正确的状态维度
            state_dim = self.env.get_state_dim()
            action_dim = self.env.num_actions
            
            if self.algorithm == 'dqn':
                self.trainer = DQNTrainer(self.env, self.config)
            elif self.algorithm == 'ppo':
                ppo_config = self.config.copy()
                ppo_config.update({
                    'n_steps': self.config.get('n_steps', 2048),
                    'n_epochs': self.config.get('n_epochs', 10),
                    'batch_size': self.config.get('batch_size', 64),
                    'clip_range': self.config.get('clip_range', 0.2),
                    'ent_coef': self.config.get('ent_coef', 0.01),
                    'vf_coef': self.config.get('vf_coef', 0.5),
                    'gae_lambda': self.config.get('gae_lambda', 0.95),
                    'use_task_aware_buffer': self.config.get('use_task_aware_buffer', True),
                    'use_tools_input': True,
                    'use_rag_enhancement': True
                })
                
                self.trainer = PPOTrainer(self.env, ppo_config)
                
                # 如果需要，可以在这里自定义网络
                if self.algorithm == 'ppo' and hasattr(self.trainer, 'network'):
                    network_config = {
                        'hidden_dim': ppo_config.get('hidden_dim', 256),
                        'num_layers': ppo_config.get('num_layers', 3),
                        'num_heads': ppo_config.get('num_heads', 4),
                        'dropout': ppo_config.get('dropout', 0.1),
                        'use_rag_enhancement': True,
                        'use_tools_input': True,
                        'tools_dim': 64,
                        'rag_dim': 64
                    }
                    self.trainer.network = ActorCriticNetwork(state_dim, action_dim, network_config)
                    self.trainer.network.to(self.trainer.device)
            else:
                logger.error(f"Unknown algorithm: {self.algorithm}")
                return False
        
        # === 关键修复：创建trainer后，立即共享网络给workflow_generator ===
        if self.env.workflow_generator and self.trainer:
            print("[DEBUG] Sharing trainer network with workflow_generator after trainer creation")
            if hasattr(self.trainer, 'network'):
                self.env.workflow_generator.set_network_reference(
                    self.trainer.network,
                    algorithm='ppo'
                )
                logger.info("✅ Shared PPO network with workflow_generator")
            elif hasattr(self.trainer, 'q_network'):
                self.env.workflow_generator.set_network_reference(
                    self.trainer.q_network,
                    algorithm='dqn'
                )
                logger.info("✅ Shared DQN network with workflow_generator")
            else:
                logger.warning("⚠️ Trainer has no network to share with workflow_generator")
        

        # 设置环境的trainer引用（如果需要）
        if hasattr(self.env, 'trainer'):
            self.env.trainer = self.trainer
        
        logger.info("✅ Environment setup complete!")
        return True


    def save_checkpoint(self, path: Path, episode: int, success_rate: float):
        """Save checkpoint with configurable detail level"""
        # 确定checkpoint类型
        checkpoint_mode = self.config.get('checkpoint_mode', 'full')
        logger.debug(f" Saving {checkpoint_mode} checkpoint at episode {episode}")
        
        # 添加调试信息
        print(f"[TrainingManager.save_checkpoint] Episode {episode}: success_rate={success_rate:.2%}, best_success_rate={self.best_success_rate:.2%}")
        print(f"[TrainingManager.save_checkpoint] Saving to: {path}")
        
        # 基础信息（所有checkpoint都包含）
        manager_state = {
            'episode': episode,
            'best_success_rate': self.best_success_rate,
            'algorithm': self.algorithm,
            'state_dim': self.env.get_state_dim(),
            'action_dim': self.env.num_actions,
            'timestamp': datetime.now().isoformat(),
            'checkpoint_mode': checkpoint_mode,
            'metadata': {
                'episode': episode,
                'success_rate': success_rate,
                'timestamp': datetime.now().isoformat(),
                'best_success_rate': self.best_success_rate
            }
        }
        
        # 标准信息（standard和full模式包含）
        if checkpoint_mode in ['standard', 'full']:
            manager_state.update({
                'config': self.config,
                'use_task_aware_state': self.use_task_aware_state,
                'enforce_workflow': self.enforce_workflow,
                'use_phase2_scoring': self.use_phase2_scoring,
            })
        
        # 完整信息（仅full模式包含）
        if checkpoint_mode == 'full':
            logger.debug(f" Full mode checkpoint - including training history")
            manager_state.update({
                'training_history': dict(self.training_history),
                'best_model_path': str(self.best_model_path) if self.best_model_path else None,
            })
        
        # 检查是否是best_model.pt的保存
        is_best_model_save = "best_model.pt" in str(path)
        
        # 如果是普通checkpoint，使用原有逻辑
        if not is_best_model_save:
            # 动态调整保存内容（原有逻辑）
            if checkpoint_mode == 'lightweight':
                # 轻量级：仅保存模型权重
                logger.debug(f" Lightweight mode - saving minimal checkpoint")
                if self.trainer:
                    lightweight_state = {
                        'episode': episode,
                        'algorithm': self.algorithm,
                        'state_dim': self.env.get_state_dim(),
                        'action_dim': self.env.num_actions,
                        'metadata': manager_state['metadata']
                    }
                    if hasattr(self.trainer, 'q_network'):  # DQN
                        lightweight_state['q_network_state_dict'] = self.trainer.q_network.state_dict()
                    elif hasattr(self.trainer, 'network'):  # PPO  
                        lightweight_state['network_state_dict'] = self.trainer.network.state_dict()
                    torch.save(lightweight_state, path)
                logger.debug(f" Lightweight checkpoint saved: {path.stat().st_size / 1024 / 1024:.1f} MB")
            else:
                # 标准或完整：使用trainer的save_checkpoint
                if self.trainer:
                    self.trainer.save_checkpoint(str(path), additional_data=manager_state)
                else:
                    torch.save(manager_state, path)
                logger.debug(f" {checkpoint_mode.capitalize()} checkpoint saved: {path.stat().st_size / 1024 / 1024:.1f} MB")
        else:
            # 如果是best_model.pt，总是保存完整状态
            print(f"[TrainingManager.save_checkpoint] 🎉 Saving best model via update_best_model!")
            
            # 保存best model（确保包含完整状态）
            best_model_state = manager_state.copy()
            best_model_state['training_history'] = dict(self.training_history)
            best_model_state['is_best_model'] = True
            best_model_state['best_success_rate'] = self.best_success_rate  # 使用已更新的best_success_rate
            best_model_state['best_episode'] = episode
            
            # 使用full模式保存best model
            if self.trainer:
                self.trainer.save_checkpoint(str(path), additional_data=best_model_state)
            else:
                torch.save(best_model_state, path)
            
            logger.info(f"✅ Best model saved with success rate: {self.best_success_rate:.2%} at episode {episode}")
        
        logger.info(f"Checkpoint saved to {path}")
        
        # 定期清理旧checkpoint
        self._cleanup_old_checkpoints()



    def _cleanup_old_checkpoints(self, keep_recent: int = 5):
        """自动清理旧的checkpoint文件，保留最近的几个和best_model.pt"""
        try:
            # 获取所有checkpoint文件（不包括best_model.pt和final_model.pt）
            checkpoints = list(self.checkpoint_dir.glob("checkpoint_*.pt"))
            
            if len(checkpoints) <= keep_recent:
                return  # 数量未超过限制，无需清理
            
            # 按修改时间排序（旧的在前）
            checkpoints.sort(key=lambda p: p.stat().st_mtime)
            
            # 计算需要删除的数量
            to_remove = checkpoints[:-keep_recent]
            
            # 删除旧的checkpoint
            for checkpoint in to_remove:
                try:
                    checkpoint.unlink()
                    logger.info(f"Removed old checkpoint: {checkpoint.name}")
                except Exception as e:
                    logger.warning(f"Failed to remove checkpoint {checkpoint.name}: {e}")
            
            logger.info(f"Checkpoint cleanup completed. Kept {keep_recent} recent checkpoints.")
            
        except Exception as e:
            logger.warning(f"Checkpoint cleanup failed: {e}")

    def _find_latest_checkpoint(self) -> Optional[Path]:
        """Find the latest checkpoint file"""
        # First, try to find best_model.pt
        best_model_path = self.checkpoint_dir / "best_model.pt"
        if best_model_path.exists():
            logger.info("Found best_model.pt, using it for resume")
            return best_model_path
        
        # If no best model, try to find checkpoint files
        checkpoints = list(self.checkpoint_dir.glob("checkpoint_*.pt"))
        if not checkpoints:
            return None
        
        # Sort by modification time as a fallback
        checkpoints.sort(key=lambda p: p.stat().st_mtime)
        return checkpoints[-1]
    
    def _load_training_state(self, checkpoint_path: Path) -> int:
        """Load training state from checkpoint and return starting episode"""
        logger.info(f"Loading checkpoint from {checkpoint_path}")
        
        # Load checkpoint through trainer if it exists
        if self.trainer:
            checkpoint = self.trainer.load_checkpoint(str(checkpoint_path))
        else:
            checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        
        # Restore manager state
        if 'training_history' in checkpoint:
            self.training_history = defaultdict(list, checkpoint['training_history'])
        
        if 'best_success_rate' in checkpoint:
            self.best_success_rate = checkpoint['best_success_rate']
        
        if 'best_model_path' in checkpoint:
            self.best_model_path = Path(checkpoint['best_model_path']) if checkpoint['best_model_path'] else None
        
        # Return next episode to start from
        return checkpoint.get('episode', 0) + 1
      

    def _create_initial_best_model(self):
        """创建初始的best_model.pt文件，供工作流生成器使用"""
        best_model_path = self.checkpoint_dir / "best_model.pt"
        
        if not best_model_path.exists():
            print("[DEBUG] Creating initial best_model.pt for workflow generator")
            
            # 确保checkpoint目录存在
            self.checkpoint_dir.mkdir(exist_ok=True)
            
            # 获取环境信息
            state_dim = self.env.get_state_dim()
            action_dim = self.env.num_actions
            
            # 创建初始checkpoint
            initial_checkpoint = {
                'episode': 0,
                'training_steps': 0,
                'algorithm': self.algorithm,
                'config': self.config,
                'state_dim': state_dim,
                'action_dim': action_dim,
                'tool_names': self.env.tool_names,
                'workflow_history': [],
                'training_history': defaultdict(list),
                'created_at': time.time(),
                'best_success_rate': 0.0,
                'stage_best_success_rates': {},
                'best_model_stages': {}
            }
            
            # 添加网络状态
            if hasattr(self.trainer, 'network'):
                initial_checkpoint['network_state_dict'] = self.trainer.network.state_dict()
                initial_checkpoint['model_state_dict'] = self.trainer.network.state_dict()  # 兼容性
            elif hasattr(self.trainer, 'q_network'):
                initial_checkpoint['q_network_state_dict'] = self.trainer.q_network.state_dict()
                initial_checkpoint['model_state_dict'] = self.trainer.q_network.state_dict()  # 兼容性
            
            torch.save(initial_checkpoint, best_model_path)
            logger.info(f"✅ Created initial best_model.pt at {best_model_path}")
            print(f"[DEBUG] Initial model saved with state_dim={state_dim}, action_dim={action_dim}")     

    def train(self, num_episodes: int = 1000, print_frequency: int = 50,
            resume: bool = False) -> bool:
        """Unified training loop for both DQN and PPO"""

        if not resume:
            logger.info("Starting fresh training - cleaning old checkpoints...")
            self._clean_checkpoint_directory()


        if not self.env:
            logger.error("Environment not initialized!")
            return False
        
        # Create trainer if not exists
        if not self.trainer:
            if self.algorithm == 'dqn':
                self.trainer = DQNTrainer(self.env, self.config)
            elif self.algorithm == 'ppo':
                ppo_config = self.config.copy()
                ppo_config.update({
                    'n_steps': 2048,
                    'n_epochs': 10,
                    'batch_size': 64,
                    'clip_range': 0.2,
                    'ent_coef': 0.01,
                    'vf_coef': 0.5,
                    'gae_lambda': 0.95,
                    'use_task_aware_buffer': self.config.get('use_task_aware_buffer', True),
                    'buffer_capacity_per_task': self.config.get('buffer_capacity_per_task', 100),
                    'min_episodes_per_task': self.config.get('min_episodes_per_task', 5),
                    'task_mix_ratio': self.config.get('task_mix_ratio', 0.7)
                })
                self.trainer = PPOTrainer(self.env, ppo_config)
            else:
                logger.error(f"Unknown algorithm: {self.algorithm}")
                return False
            
            logger.info(f"Using {self.algorithm.upper()} algorithm")
            
        if not resume and self.config.get('create_initial_best_model', False):
            self._create_initial_best_model()



        # Resume from checkpoint if requested
        start_episode = 0
        if resume:
            checkpoint_path = self._find_latest_checkpoint()
            if checkpoint_path:
                start_episode = self._load_training_state(checkpoint_path)
                logger.info(f"Resumed from episode {start_episode}")
            else:
                logger.warning("No checkpoint found, starting from scratch")
        
        # Initialize curriculum
        curriculum = None
        if self.config['use_curriculum']:
            curriculum = CurriculumScheduler(num_episodes, config=self.config)
            if resume and start_episode > 0:
                curriculum.current_episode = start_episode
                print(f"[CURRICULUM] Resumed training from episode {start_episode}")
        else:
            raise ValueError("No curriculum")
        
        # Training metrics
        episode_rewards = deque(maxlen=100)
        episode_success = deque(maxlen=100)
        episode_lengths = deque(maxlen=100)
        
        # Load metrics history if resuming
        if resume and 'rewards' in self.training_history:
            episode_rewards.extend(self.training_history['rewards'][-100:])
            episode_success.extend(self.training_history['success'][-100:])
            episode_lengths.extend(self.training_history['lengths'][-100:])
        
        # 收集成功的episodes用于学习
        successful_episodes = []

        if len(episode_success) > 0:
            current_success_rate = np.mean(episode_success)
        else:
            current_success_rate = 0.0
        
        # Main training loop
        logger.info(f"Starting training from episode {start_episode} to {num_episodes}")
        
        for episode in range(start_episode, num_episodes):
            # Get curriculum stage
            curriculum_stage = curriculum.get_stage() if curriculum else None

            if hasattr(self.env, 'set_current_success_rate'):
                # 渐进式阈值策略：
                # - 低于阈值：只要求覆盖所有required_tools（忽略顺序）
                # - 高于阈值：开始强制执行顺序
                if episode < 1000:
                    threshold = 0.1  # 前1000轮：10%阈值，专注于学习工具覆盖
                elif episode < 3000:
                    threshold = 0.2  # 1000-3000轮：20%阈值，开始引入轻微顺序约束
                elif episode < 5000:
                    threshold = 0.3  # 3000-5000轮：30%阈值，标准顺序约束
                else:
                    threshold = 0.4  # 5000+轮：40%阈值，严格顺序约束
                
                self.env.set_current_success_rate(current_success_rate, threshold)
                
                # 每1000轮打印一次模式转换信息
                if episode % 1000 == 0:
                    mode = "coverage" if current_success_rate < threshold else "sequence"
                    print(f"[TRAIN] Episode {episode}: Mode={mode}, Success rate={current_success_rate:.2%}, Threshold={threshold:.2%}")
     
            
            # Reset environment
            state = self.env.reset(curriculum_stage=curriculum_stage)
            episode_reward = 0
            done = False
            
            # 收集episode轨迹用于学习
            episode_trajectory = []
            
            while not done and self.env.episode_steps < self.config['max_episode_length']:
                # Get valid actions if using action masking
                valid_actions = self.env.get_valid_actions() if self.config['use_action_masking'] else None
                
                # Select action
                action = self.trainer.select_action(state, valid_actions)
                
                # Step
                next_state, reward, done, info = self.env.step(action)
                
                # 收集轨迹数据
                if hasattr(self.env, 'current_state') and hasattr(self.env, 'action_space'):
                    action_obj = self.env.action_space[action]
                    episode_trajectory.append((
                        self.env.current_state,
                        action_obj,
                        reward,
                        self.env.current_state
                    ))
                
                # 使用统一接口存储经验
                task_type = None
                if hasattr(self.env, 'current_task') and hasattr(self.env.current_task, 'task_type'):
                    task_type = self.env.current_task.task_type
                
                self.trainer.store_experience(state, action, reward, next_state, done, task_type=task_type)
                self.trainer.step_completed()
                
                # 检查是否应该训练
                if self.trainer.should_train():
                    loss = self.trainer.train_step()
                
                # Update
                episode_reward += reward
                state = next_state
            
            # Episode结束处理
            self.trainer.on_episode_end()
            
            # Episode complete
            success = info.get('success', False)
            episode_rewards.append(episode_reward)
            episode_success.append(float(success))
            episode_lengths.append(self.env.episode_steps)

            current_success_rate = np.mean(episode_success)

            
            # 实时更新training_history
            self.training_history['rewards'].append(episode_reward)
            self.training_history['success'].append(float(success))
            self.training_history['lengths'].append(self.env.episode_steps)
            
            # 更新工具关键性数据
            if hasattr(self.mdp, 'update_tool_criticality') and episode_trajectory:
                final_score = info.get('phase2_metrics', {}).get('phase2_score', 0.0)
                if final_score == 0.0:
                    final_score = 1.0 if success else 0.0
                
                episode_data = {
                    'trajectory': episode_trajectory,
                    'final_score': final_score,
                    'task_type': self.env.current_task.task_type if hasattr(self.env.current_task, 'task_type') else 'unknown',
                    'tool_failures': {}
                }
                
                self.mdp.update_tool_criticality(episode_data)
                
                if success and final_score > 0.8:
                    successful_episodes.append({
                        'trajectory': episode_trajectory,
                        'final_score': final_score,
                        'task_description': self.env.current_task.description if hasattr(self.env.current_task, 'description') else ''
                    })
            
            # Update exploration
            self.trainer.update_exploration()
            
            # Update curriculum - 修复：使用正确的方法名
            if curriculum:
                curriculum.update()  # 使用update而不是step
            
            # 定期更新 MDPWorkflowGenerator 的网络（如果启用了工作流执行）
            if self.enforce_workflow and episode % 100 == 0 and episode > 0:
                if hasattr(self.env, 'workflow_generator') and self.env.workflow_generator:
                    print(f"[Episode {episode}] Updating workflow generator network...")
                    
                    if self.algorithm == 'ppo' and hasattr(self.trainer, 'network'):
                        self.env.workflow_generator.update_network(
                            self.trainer.network.state_dict(),
                            algorithm='ppo'
                        )
                    elif self.algorithm == 'dqn' and hasattr(self.trainer, 'q_network'):
                        self.env.workflow_generator.update_network(
                            self.trainer.q_network.state_dict(),
                            algorithm='dqn'
                        )
            
            # Print progress
            if episode % print_frequency == 0:
                avg_reward = np.mean(list(episode_rewards))
                avg_success = np.mean(list(episode_success))
                avg_length = np.mean(list(episode_lengths))
                
                logger.info(f"Episode {episode}/{num_episodes}:")
                logger.info(f"  Avg Reward: {avg_reward:.2f}")
                logger.info(f"  Success Rate: {avg_success:.2%}")
                logger.info(f"  Avg Length: {avg_length:.1f}")
                
                # 获取算法特定的训练信息
                training_info = self.trainer.get_training_info()
                if self.algorithm == 'dqn' and hasattr(self.trainer, 'epsilon'):
                    logger.info(f"  Epsilon: {self.trainer.epsilon:.3f}")
                elif self.algorithm == 'ppo':
                    logger.info(f"  Total timesteps: {training_info['total_timesteps']}")
                
                if curriculum:
                    logger.info(f"  Curriculum: {curriculum.get_stage_name()}")
                
                # 更新best model（新增的代码）
                if len(episode_success) >= 10:  # 至少有10个episode才计算
                    window_size = min(100, len(episode_success))
                    recent_success_rate = np.mean(list(episode_success)[-window_size:])  # 这行是正确的
                    current_stage = curriculum.get_stage() if curriculum else 0
                    
                    logger.debug(f" Update best model check - Episode {episode}: recent_success_rate={recent_success_rate:.2%} from last {window_size} episodes")

                    
                    # 定义保存回调
                    def save_best_callback(is_best=True):
                        self.save_checkpoint(
                            self.checkpoint_dir / "best_model.pt",
                            episode,
                            recent_success_rate
                        )
                    
                    # 调用update_best_model
                    self.update_best_model(
                        episode=episode,
                        recent_success_rate=recent_success_rate,
                        current_stage=current_stage,
                        save_callback=save_best_callback
                    )

            # Save checkpoint
            if episode % self.config['checkpoint_frequency'] == 0:
                # 计算最近100个episodes的成功率
                # 优先使用 training_history，它应该包含所有历史数据
                if 'success' in self.training_history and len(self.training_history['success']) > 0:
                    recent_episodes = min(100, len(self.training_history['success']))
                    recent_success_list = self.training_history['success'][-recent_episodes:]
                    current_success_rate = np.mean(recent_success_list) if recent_success_list else 0.0
                    print(f"[DEBUG] Using training_history for success rate: {current_success_rate:.2%} from {recent_episodes} episodes")
                    print(f"[DEBUG] training_history has {len(self.training_history['success'])} success records")
                elif len(episode_success) > 0:
                    # fallback: 使用 episode_success deque（最多100个最近的episodes）
                    current_success_rate = np.mean(episode_success)
                    print(f"[DEBUG] Using episode_success deque for success rate: {current_success_rate:.2%} from {len(episode_success)} episodes")
                else:
                    current_success_rate = 0.0
                    print(f"[DEBUG] No success data available, using 0.0%")
                
                print(f"[TrainingManager.train] Checkpoint at episode {episode}")
                print(f"[TrainingManager.train] Recent success rate: {current_success_rate:.2%}")
                print(f"[TrainingManager.train] Current best: {self.best_success_rate:.2%}")
                
                checkpoint_path = self.checkpoint_dir / f"checkpoint_episode_{episode}.pt"
                self.save_checkpoint(checkpoint_path, episode, current_success_rate)


            # Evaluate
            if episode % self.config['evaluation_frequency'] == 0:
                eval_results = self.evaluate(num_episodes=self.config['evaluation_episodes'])
                logger.info(f"Evaluation at episode {episode}: {eval_results}")
                
                # Update scheduler (only for DQN)
                if self.algorithm == 'dqn' and hasattr(self.trainer, 'scheduler'):
                    self.trainer.scheduler.step(eval_results['avg_reward'])
        
        # PPO: 确保最后的数据被训练
        if hasattr(self.trainer.rollout_buffer, 'states') and len(self.trainer.rollout_buffer.states) > 0:
            logger.info("Training on final rollout buffer...")
            self.trainer.train_step()
        elif hasattr(self.trainer.rollout_buffer, 'current_episode') and len(self.trainer.rollout_buffer.current_episode['states']) > 0:
            logger.info("Training on final rollout buffer...")
            self.trainer.train_step()
        
        # 学习关键模式
        if hasattr(self.mdp, 'learn_critical_patterns_from_episodes') and successful_episodes:
            logger.info(f"Learning critical patterns from {len(successful_episodes)} successful episodes...")
            self.mdp.learn_critical_patterns_from_episodes(successful_episodes)
        
        # 保存学习到的工具关键性数据
        if hasattr(self.mdp, 'save_learned_criticality'):
            criticality_path = self.checkpoint_dir / "tool_criticality.json"
            self.mdp.save_learned_criticality(str(criticality_path))
            logger.info(f"Saved tool criticality data to {criticality_path}")
        
        # Final save
        final_path = self.checkpoint_dir / "final_model.pt"
        # 修复：直接使用 episode_success，因为它是 deque 对象
        if episode_success:
            final_success_rate = np.mean(list(episode_success))  # <- 修改了这一行：删除了 .values()
            logger.debug(f" Final success rate calculation: {final_success_rate:.2%} from {len(episode_success)} episodes")
        else:
            final_success_rate = 0.0
            logger.debug(f" No episode_success data, using 0.0%")
        
        self.save_checkpoint(final_path, num_episodes, final_success_rate)
        
        if curriculum:
            print(f"\n[CURRICULUM FINAL] Training completed!")
            print(f"[CURRICULUM FINAL] Total episodes run: {curriculum.current_episode}")
            print(f"[CURRICULUM FINAL] Expected episodes: {curriculum.total_episodes}")
            print(f"[CURRICULUM FINAL] Final stage: {curriculum.get_stage()}")
            print(f"[CURRICULUM FINAL] Final progress: {curriculum.current_episode/curriculum.total_episodes:.1%}")
            
            # 打印stage历史摘要
            # 修复：添加边界检查，避免索引越界
            stage_changes = []
            for i, (ep, st) in enumerate(curriculum.stage_history):
                if ep == 1:  # 第一个episode总是记录
                    stage_changes.append((ep, st))
                elif i > 0 and curriculum.stage_history[i-1][1] != st:  # 检查与前一个记录的stage是否不同
                    stage_changes.append((ep, st))
            
            print(f"[CURRICULUM FINAL] Stage transitions: {stage_changes}")

        logger.info("Training completed!")
        return True

    def _clean_checkpoint_directory(self):
        """清理checkpoint目录中的旧文件（非resume模式下）"""
        logger.info("Cleaning checkpoint directory...")
        
        # 需要保留的文件模式
        config_path = self.checkpoint_dir / "training_config.json"
        config_content = None
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_content = f.read()

        # 删除整个文件夹
        removed_count = 0
        preserved_count = 0

        if self.checkpoint_dir.exists():
            # 计算将要删除的文件数（除了 training_config.json）
            for item in self.checkpoint_dir.iterdir():
                if item.name != "training_config.json":
                    removed_count += 1
            
            # 删除整个文件夹
            import shutil
            print(f"  Removing entire checkpoint directory: {self.checkpoint_dir}")
            shutil.rmtree(self.checkpoint_dir)
            
            # 重新创建文件夹
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
            
            # 恢复 training_config.json
            if config_content is not None:
                with open(config_path, 'w') as f:
                    f.write(config_content)
                print(f"  Preserved: training_config.json")
                preserved_count = 1
        
        # 重置训练相关的状态
        self.best_success_rate = 0.0
        self.stage_best_success_rates = {}
        self.best_model_stages = {}
        self.weighted_best_score = 0.0
        self.best_model_path = None
        self.current_stage = 0
        self.stage_transition_episodes = []
        self.training_history = defaultdict(list)
        self.training_history['rewards'] = []
        self.training_history['success'] = []
        self.training_history['lengths'] = []
        
        logger.info(f"Checkpoint cleanup completed: removed {removed_count} files, preserved {preserved_count} files")

    def evaluate(self, num_episodes: int = 100, model_path: Optional[str] = None) -> Dict[str, float]:
        """Evaluate trained model"""
        if not self.env or not self.trainer:
            logger.error("Environment or trainer not initialized!")
            return {}
        
        if model_path:
            self.trainer.load_checkpoint(model_path)
        
        # 设置评估模式 - 使用trainer的统一方法  # <- 修改
        self.env.is_evaluation_mode = True
        self.trainer.set_eval_mode(True)  # <- 修改：使用统一方法
        
        eval_rewards = []
        eval_success = []
        eval_lengths = []
        
        logger.info(f"Evaluating for {num_episodes} episodes...")
        
        for episode in range(num_episodes):
            state = self.env.reset()
            episode_reward = 0
            done = False
            
            while not done and self.env.episode_steps < self.config['max_episode_length']:
                valid_actions = self.env.get_valid_actions() if self.config['use_action_masking'] else None
                action = self.trainer.select_action(state, valid_actions)
                next_state, reward, done, info = self.env.step(action)
                
                episode_reward += reward
                state = next_state
            
            eval_rewards.append(episode_reward)
            eval_success.append(float(info.get('success', False)))
            eval_lengths.append(self.env.episode_steps)
        
        # 恢复训练模式 - 使用trainer的统一方法  # <- 修改
        self.env.is_evaluation_mode = False
        self.trainer.set_eval_mode(False)  # <- 修改：使用统一方法
        
        # Print results
        logger.info(f"Evaluation Results:")
        logger.info(f"  Avg Reward: {np.mean(eval_rewards):.2f} ± {np.std(eval_rewards):.2f}")
        logger.info(f"  Success Rate: {np.mean(eval_success):.2%}")
        logger.info(f"  Avg Length: {np.mean(eval_lengths):.1f} ± {np.std(eval_lengths):.1f}")
        
        return {
            'avg_reward': np.mean(eval_rewards),
            'success_rate': np.mean(eval_success),
            'avg_length': np.mean(eval_lengths),
            'std_reward': np.std(eval_rewards),
            'std_length': np.std(eval_lengths)
        }

    def analyze_model(self) -> Dict[str, Any]:
        """Analyze trained model performance"""
        # Always try to use best_model.pt first
        best_model_path = self.checkpoint_dir / "best_model.pt"
        
        if best_model_path.exists():
            self.best_model_path = best_model_path
            logger.info(f"Using best_model.pt for analysis")
        elif not self.best_model_path:
            logger.error("No trained model to analyze!")
            return {}
        
        logger.info(f"Analyzing model from {self.best_model_path}")
        
        # Load best model
        self.trainer.load_checkpoint(str(self.best_model_path))
        
        # 设置评估模式  # <- 新增了这部分
        if self.algorithm == 'ppo' and hasattr(self.trainer, 'eval_mode'):
            self.trainer.eval_mode = True
        elif self.algorithm == 'dqn' and hasattr(self.trainer, 'epsilon'):
            old_epsilon = self.trainer.epsilon
            self.trainer.epsilon = 0.0
        
        # Evaluate on different task types
        results = {}
        task_types = list(self.task_manager.tasks_by_type.keys())
        
        for task_type in task_types:
            logger.info(f"Evaluating on {task_type} tasks...")
            type_results = []
            
            for _ in range(10):  # 10 episodes per task type
                state = self.env.reset(task_type=task_type)
                episode_reward = 0
                done = False
                
                while not done and self.env.episode_steps < self.config['max_episode_length']:
                    valid_actions = self.env.get_valid_actions() if self.config['use_action_masking'] else None
                    action = self.trainer.select_action(state, valid_actions)
                    next_state, reward, done, info = self.env.step(action)
                    
                    episode_reward += reward
                    state = next_state
                
                type_results.append({
                    'reward': episode_reward,
                    'success': info.get('success', False),
                    'steps': self.env.episode_steps,
                    'phase2_score': info.get('phase2_metrics', {}).get('phase2_score', 0.0)
                })
            
            # Aggregate results
            results[task_type] = {
                'avg_reward': np.mean([r['reward'] for r in type_results]),
                'success_rate': np.mean([r['success'] for r in type_results]),
                'avg_steps': np.mean([r['steps'] for r in type_results]),
                'avg_phase2_score': np.mean([r['phase2_score'] for r in type_results])
            }
        
        # 恢复训练模式  # <- 新增了这部分
        if self.algorithm == 'ppo' and hasattr(self.trainer, 'eval_mode'):
            self.trainer.eval_mode = False
        elif self.algorithm == 'dqn':
            self.trainer.epsilon = old_epsilon
        
        # Overall statistics
        overall_success = np.mean([r['success_rate'] for r in results.values()])
        overall_phase2 = np.mean([r['avg_phase2_score'] for r in results.values()])
        
        logger.info(f"\nAnalysis Results:")
        logger.info(f"Overall Success Rate: {overall_success:.2%}")
        logger.info(f"Overall Phase 2 Score: {overall_phase2:.3f}")
        
        for task_type, metrics in results.items():
            logger.info(f"\n{task_type}:")
            logger.info(f"  Success Rate: {metrics['success_rate']:.2%}")
            logger.info(f"  Avg Steps: {metrics['avg_steps']:.1f}")
            logger.info(f"  Phase 2 Score: {metrics['avg_phase2_score']:.3f}")
        
        return {
            'task_results': results,
            'overall_success': overall_success,
            'overall_phase2_score': overall_phase2,
            'model_path': str(self.best_model_path)
        }


# ===========================
# Utility Functions for Testing
# ===========================

def test_environment_setup():
    """Test environment setup with all features"""
    logger.info("Testing environment setup...")
    
    manager = UnifiedTrainingManager(
        use_task_aware_state=True,
        enforce_workflow=True,
        use_phase2_scoring=True
    )
    
    if manager.setup_environment():
        logger.info("✅ Environment setup successful!")
        
        # Test reset and step
        state = manager.env.reset()
        logger.info(f"State shape: {state.shape}")
        logger.info(f"State dim: {manager.env.get_state_dim()}")
        
        # Test step
        action = 0
        next_state, reward, done, info = manager.env.step(action)
        logger.info(f"Step successful: reward={reward:.2f}")
        logger.info(f"Info: {info}")
        
        return True
    else:
        logger.error("❌ Environment setup failed!")
        return False


def quick_train_test(episodes: int = 100):
    """Quick training test"""
    logger.info(f"Running quick training test ({episodes} episodes)...")
    
    manager = UnifiedTrainingManager(
        use_task_aware_state=True,
        enforce_workflow=False,  # Start without enforcement
        use_phase2_scoring=True
    )
    
    if manager.setup_environment():
        success = manager.train_dqn(num_episodes=episodes, print_frequency=10)
        if success:
            logger.info("✅ Training completed!")
            # Evaluate
            results = manager.evaluate(num_episodes=10)
            logger.info(f"Evaluation: {results}")
        else:
            logger.error("❌ Training failed!")
    else:
        logger.error("❌ Setup failed!")


# ===========================
# Main Entry Point
# ===========================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified Training Manager")
    parser.add_argument("--test", action="store_true", help="Run quick test")
    parser.add_argument("--episodes", type=int, default=100, help="Number of episodes")
    parser.add_argument("--use-task-aware", action="store_true", default=True,
                       help="Use task-aware state representation")
    parser.add_argument("--no-task-aware", dest="use_task_aware", action="store_false")
    parser.add_argument("--enforce-workflow", action="store_true", default=False,
                       help="Enable workflow enforcement")
    parser.add_argument("--use-phase2", action="store_true", default=True,
                       help="Use Phase 2 scoring")
    parser.add_argument("--no-phase2", dest="use_phase2", action="store_false")
    parser.add_argument("--resume", defalt=False, action="store_true", help="Resume from checkpoint")
    
    args = parser.parse_args()
    
    if args.test:
        test_environment_setup()
        quick_train_test(args.episodes)
    else:
        manager = UnifiedTrainingManager(
            use_task_aware_state=args.use_task_aware,
            enforce_workflow=args.enforce_workflow,
            use_phase2_scoring=args.use_phase2
        )
        
        if manager.setup_environment():
            manager.train_dqn(num_episodes=args.episodes, resume=args.resume)
        else:
            logger.error("Failed to setup environment!")