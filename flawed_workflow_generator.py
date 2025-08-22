#!/usr/bin/env python3
"""
Flawed Workflow Generator Implementation - FIXED VERSION
========================================================
修复了ToolCapability对象访问问题
"""

import random
import copy
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# 文件：flawed_workflow_generator.py
# 位置：第18-60行（FlawedWorkflowGenerator类初始化和新增方法）

class FlawedWorkflowGenerator:
    """生成各种类型的flawed workflows - RAG增强版"""
    
    def __init__(self, tool_registry: Dict[str, Any], 
                 embedding_manager: Optional[Any] = None,
                 tool_capabilities: Optional[Dict[str, Any]] = None):
        """
        初始化生成器
        
        Args:
            tool_registry: 工具注册表，值可以是ToolCapability对象或字典
            embedding_manager: 可选的嵌入管理器，用于语义搜索
            tool_capabilities: 可选的工具能力字典
        """
        self.tool_registry = tool_registry
        self.tool_categories = self._categorize_tools()
        from mcp_embedding_manager import get_embedding_manager
        self.embedding_manager = get_embedding_manager()    
        self.tool_capabilities = tool_capabilities or {}
        
        # 缓存语义相似工具
        self._semantic_cache = {}
        
        # 新增：required_tools过滤器
        self.required_tools_filter = None
        
        print(f"[FlawedWorkflowGenerator] Initialized with {len(tool_registry)} tools")
        print(f"[FlawedWorkflowGenerator] RAG support: {'enabled' if embedding_manager else 'disabled'}")
    
    def set_required_tools_filter(self, required_tools: List[str]):
        """设置required_tools过滤器
        
        Args:
            required_tools: 只对这些工具产生flaw，如果为None则对所有工具产生flaw
        """
        self.required_tools_filter = set(required_tools) if required_tools else None
        if self.required_tools_filter:
            print(f"[FlawedWorkflowGenerator] Set required_tools filter: {required_tools}")
    
    def _filter_by_required_tools(self, tools: List[str]) -> List[str]:
        """根据required_tools过滤工具列表
        
        Args:
            tools: 原始工具列表
            
        Returns:
            过滤后的工具列表
        """
        if self.required_tools_filter is None:
            return tools
        
        # 只返回在required_tools中的工具
        filtered = [t for t in tools if t in self.required_tools_filter]
        
        # 如果过滤后没有工具，返回原列表（避免空列表导致的错误）
        return filtered if filtered else tools    
        
    def _categorize_tools(self) -> Dict[str, List[str]]:
        """将工具按类别分组"""
        categories = defaultdict(list)
        
        for tool_name, tool_def in self.tool_registry.items():
            # 从工具名称推断类别
            if '_' in tool_name:
                category = tool_name.split('_')[0]
            else:
                category = 'general'
            
            categories[category].append(tool_name)
        
        return dict(categories)
    
    def _get_tool_attribute(self, tool_def: Any, attr: str, default: Any = None) -> Any:
        """
        安全地获取工具属性，支持对象和字典两种格式
        
        Args:
            tool_def: 工具定义（ToolCapability对象或字典）
            attr: 属性名
            default: 默认值
            
        Returns:
            属性值或默认值
        """
        # 如果是对象，使用getattr
        if hasattr(tool_def, attr):
            return getattr(tool_def, attr, default)
        # 如果是字典，使用get
        elif isinstance(tool_def, dict):
            return tool_def.get(attr, default)
        else:
            return default
    
    def _find_semantically_similar_tools(self, tool_name: str, 
                                       exclude_same_function: bool = True) -> List[Tuple[str, float]]:
        """
        使用RAG查找语义相似的工具
        
        Args:
            tool_name: 原始工具名
            exclude_same_function: 是否排除功能相同的工具
            
        Returns:
            [(tool_name, similarity_score)]列表
        """
        # 检查缓存
        cache_key = f"{tool_name}_{exclude_same_function}"
        if cache_key in self._semantic_cache:
            return self._semantic_cache[cache_key]
        
        similar_tools = []
        
        if self.embedding_manager and tool_name in self.tool_capabilities:
            logger.debug(f" Finding semantically similar tools for {tool_name}")
            
            # 获取原工具的语义操作
            capability = self.tool_capabilities[tool_name]
            semantic_ops = self._get_tool_attribute(capability, 'semantic_operations', [])
            
            # 构建搜索查询
            query = f"{tool_name} {' '.join(semantic_ops)}"
            
            # 执行语义搜索
            search_results = self.embedding_manager.search(
                query=query,
                k=20,  # 搜索更多结果以便筛选
                return_scores=True
            )
            
            # 筛选结果
            for result in search_results:
                if result.tool_name == tool_name:
                    continue  # 跳过自己
                
                if exclude_same_function:
                    # 检查是否功能不同
                    result_capability = self.tool_capabilities.get(result.tool_name)
                    if result_capability:
                        result_ops = self._get_tool_attribute(result_capability, 'semantic_operations', [])
                        # 如果语义操作重叠太多，认为功能相同
                        overlap = set(semantic_ops) & set(result_ops)
                        if len(overlap) / max(len(semantic_ops), len(result_ops), 1) > 0.7:
                            continue
                
                similar_tools.append((result.tool_name, result.score))
                
                if len(similar_tools) >= 5:  # 最多返回5个
                    break
            
            logger.debug(f" Found {len(similar_tools)} similar tools for {tool_name}")
        
        # 缓存结果
        self._semantic_cache[cache_key] = similar_tools
        return similar_tools
    
    def generate_all_flaws(self, optimal_workflow: Dict, 
                          severity: str = 'medium') -> Dict[str, Dict]:
        """生成所有类型的flawed workflows"""
        flawed_workflows = {}
        
        # 1. 顺序错误
        flawed_workflows['order_flaw_swap'] = self.introduce_order_flaw(
            optimal_workflow, method='swap', severity=severity)
        flawed_workflows['order_flaw_dependency'] = self.introduce_order_flaw(
            optimal_workflow, method='dependency', severity=severity)
        
        # 2. 工具误用
        flawed_workflows['tool_misuse_similar'] = self.introduce_tool_misuse(
            optimal_workflow, method='similar', severity=severity)
        flawed_workflows['tool_misuse_wrong_category'] = self.introduce_tool_misuse(
            optimal_workflow, method='wrong_category', severity=severity)
        
        # 3. 参数错误
        flawed_workflows['param_missing'] = self.introduce_parameter_flaw(
            optimal_workflow, method='missing', severity=severity)
        flawed_workflows['param_wrong_type'] = self.introduce_parameter_flaw(
            optimal_workflow, method='wrong_type', severity=severity)
        
        # 4. 步骤缺失
        flawed_workflows['missing_middle'] = self.introduce_missing_steps(
            optimal_workflow, method='middle', severity=severity)
        flawed_workflows['missing_validation'] = self.introduce_missing_steps(
            optimal_workflow, method='validation', severity=severity)
        
        # 5. 冗余步骤
        flawed_workflows['redundant_duplicate'] = self.introduce_redundancy(
            optimal_workflow, method='duplicate', severity=severity)
        flawed_workflows['redundant_unnecessary'] = self.introduce_redundancy(
            optimal_workflow, method='unnecessary', severity=severity)
        
        # 6. 逻辑断裂
        flawed_workflows['logic_break_format'] = self.introduce_logic_break(
            optimal_workflow, method='format', severity=severity)
        flawed_workflows['logic_break_unrelated'] = self.introduce_logic_break(
            optimal_workflow, method='unrelated', severity=severity)
        
        # 7. RAG相关缺陷（新增）
        if self.embedding_manager:
            flawed_workflows['semantic_mismatch'] = self.introduce_semantic_mismatch(
                optimal_workflow, severity=severity)
            flawed_workflows['semantic_drift'] = self.introduce_semantic_drift(
                optimal_workflow, severity=severity)
        
        return flawed_workflows
        
    def _update_smart_actions(self, workflow: Dict) -> None:
        """
        根据optimal_sequence更新smart_actions的顺序
        只更新step编号，保持所有其他信息不变
        """
        if 'smart_actions' not in workflow or not workflow.get('optimal_sequence'):
            return
        
        # 创建工具名到smart_action的映射
        action_map = {action['tool_name']: action for action in workflow['smart_actions']}
        
        # 根据新的optimal_sequence重建smart_actions
        new_smart_actions = []
        for i, tool_name in enumerate(workflow['optimal_sequence']):
            if tool_name in action_map:
                # 复制原有的action信息
                action = action_map[tool_name].copy()
                # 只更新step编号
                action['step'] = i + 1
                new_smart_actions.append(action)
            else:
                # 如果是新添加的工具（如redundancy），创建最小化的action
                new_smart_actions.append({
                    'tool_name': tool_name,
                    'step': i + 1,
                    'search_source': 'unknown',
                    'semantic_score': 0.0,
                    'confidence': 0.5,
                    'alternatives': [],
                    'reasoning': '',  # 保持空，不添加任何理由
                    'dependencies': [],
                    'expected_outcome': {},
                    'mcp_protocol': {}
                })
        
        workflow['smart_actions'] = new_smart_actions

    def introduce_order_flaw(self, workflow: Dict, method: str = 'swap', 
                        severity: str = 'medium') -> Dict:
        """引入顺序错误"""
        flawed = copy.deepcopy(workflow)
        
        # 获取optimal sequence
        optimal_seq = workflow.get('optimal_sequence', [])
        if not optimal_seq or len(optimal_seq) < 2:
            return flawed
        
        # 新增：获取在required_tools中的工具索引
        if self.required_tools_filter:
            valid_indices = [i for i, tool in enumerate(optimal_seq) 
                            if tool in self.required_tools_filter]
            if len(valid_indices) < 2:
                # 如果required_tools中的工具少于2个，无法产生顺序错误
                print(f"[DEBUG] Not enough required tools for order flaw: {len(valid_indices)}")
                return flawed
        else:
            valid_indices = list(range(len(optimal_seq)))
        
        if method == 'swap':
            # 随机交换相邻步骤（只交换required_tools）
            if severity == 'light':
                # 只交换一对
                if len(valid_indices) >= 2:
                    # 找到相邻的valid_indices
                    adjacent_pairs = [(valid_indices[i], valid_indices[i+1]) 
                                    for i in range(len(valid_indices)-1) 
                                    if valid_indices[i+1] - valid_indices[i] == 1]
                    if adjacent_pairs:
                        idx1, idx2 = random.choice(adjacent_pairs)
                        optimal_seq[idx1], optimal_seq[idx2] = optimal_seq[idx2], optimal_seq[idx1]
                    else:
                        # 如果没有相邻的，交换任意两个
                        idx1, idx2 = random.sample(valid_indices, 2)
                        optimal_seq[idx1], optimal_seq[idx2] = optimal_seq[idx2], optimal_seq[idx1]
            elif severity == 'medium':
                # 交换2-3对
                num_swaps = min(random.randint(2, 3), len(valid_indices) // 2)
                for _ in range(num_swaps):
                    if len(valid_indices) >= 2:
                        idx1, idx2 = random.sample(valid_indices, 2)
                        optimal_seq[idx1], optimal_seq[idx2] = optimal_seq[idx2], optimal_seq[idx1]
            else:  # severe
                # 只打乱required_tools的顺序
                if valid_indices:
                    required_tools = [optimal_seq[i] for i in valid_indices]
                    random.shuffle(required_tools)
                    for i, idx in enumerate(valid_indices):
                        optimal_seq[idx] = required_tools[i]
        
        elif method == 'dependency':
            # 将依赖步骤前置（破坏依赖关系）
            # 只移动required_tools中有依赖的工具
            for i in reversed(valid_indices):
                tool = optimal_seq[i]
                if tool in self.tool_registry:
                    tool_def = self.tool_registry[tool]
                    deps = self._get_tool_attribute(tool_def, 'dependencies', [])
                    if deps:
                        # 将这个工具移到最前面，破坏依赖
                        optimal_seq.insert(0, optimal_seq.pop(i))
                        if severity == 'light':
                            break  # 只移动一个
        
        flawed['optimal_sequence'] = optimal_seq
        flawed['flaw_type'] = f'order_{method}'
        flawed['flaw_severity'] = severity
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        return flawed


    def introduce_tool_misuse(self, workflow: Dict, method: str = 'similar', 
                            severity: str = 'medium') -> Dict:
        """引入工具误用 - 增强RAG支持"""
        flawed = copy.deepcopy(workflow)
        optimal_seq = workflow.get('optimal_sequence', [])
        
        if not optimal_seq:
            return flawed
        
        # 新增：只对required_tools中的工具进行替换
        if self.required_tools_filter:
            valid_indices = [i for i, tool in enumerate(optimal_seq) 
                            if tool in self.required_tools_filter]
            if not valid_indices:
                print(f"[DEBUG] No required tools found for tool misuse")
                return flawed
        else:
            valid_indices = list(range(len(optimal_seq)))
        
        # 决定替换多少工具
        if severity == 'light':
            num_replacements = 1
        elif severity == 'medium':
            num_replacements = min(2, len(valid_indices) // 2)
        else:  # severe
            num_replacements = len(valid_indices) // 2 + 1
        
        # 从valid_indices中选择要替换的索引
        replaced_indices = random.sample(valid_indices, 
                                    min(num_replacements, len(valid_indices)))
        
        # 记录替换信息
        flawed['tool_replacements'] = []
        
        for idx in replaced_indices:
            current_tool = optimal_seq[idx]
            replacement_tool = None
            
            if method == 'similar':
                # 优先使用语义搜索找相似工具
                if self.embedding_manager:
                    similar_tools = self._find_semantically_similar_tools(
                        current_tool, exclude_same_function=True)
                    if similar_tools:
                        # 选择相似但功能不同的工具
                        replacement_tool = similar_tools[0][0]  # 最相似的
                        print(f"[DEBUG] Replacing {current_tool} with semantically similar {replacement_tool}")
                
                # 如果没有找到，使用原方法
                if not replacement_tool:
                    category = self._get_tool_category(current_tool)
                    alternatives = [t for t in self.tool_categories.get(category, []) 
                                if t != current_tool]
                    if alternatives:
                        replacement_tool = random.choice(alternatives)
            
            elif method == 'wrong_category':
                # 替换为完全不同类别的工具
                other_categories = [cat for cat in self.tool_categories 
                                if cat != self._get_tool_category(current_tool)]
                if other_categories:
                    wrong_category = random.choice(other_categories)
                    if self.tool_categories[wrong_category]:
                        replacement_tool = random.choice(self.tool_categories[wrong_category])
            
            if replacement_tool:
                optimal_seq[idx] = replacement_tool
                flawed['tool_replacements'].append({
                    'position': idx,
                    'original': current_tool,
                    'replacement': replacement_tool,
                    'method': method
                })
        
        flawed['optimal_sequence'] = optimal_seq
        flawed['flaw_type'] = f'tool_{method}'
        flawed['flaw_severity'] = severity
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        return flawed
    
    def introduce_parameter_flaw(self, workflow: Dict, method: str = 'missing', 
                               severity: str = 'medium') -> Dict:
        """引入参数错误"""
        flawed = copy.deepcopy(workflow)
        
        # 在workflow中添加参数错误标记
        # 实际参数错误会在prompt生成时体现
        flawed['parameter_flaws'] = []
        
        optimal_seq = workflow.get('optimal_sequence', [])
        
        if severity == 'light':
            num_flaws = 1
        elif severity == 'medium':
            num_flaws = min(2, len(optimal_seq))
        else:  # severe
            num_flaws = len(optimal_seq) // 2 + 1
        
        flaw_indices = random.sample(range(len(optimal_seq)), 
                                   min(num_flaws, len(optimal_seq)))
        
        for idx in flaw_indices:
            tool = optimal_seq[idx]
            if method == 'missing':
                flawed['parameter_flaws'].append({
                    'tool': tool,
                    'index': idx,
                    'type': 'missing_required',
                    'description': 'Missing required parameter'
                })
            elif method == 'wrong_type':
                flawed['parameter_flaws'].append({
                    'tool': tool,
                    'index': idx,
                    'type': 'wrong_type',
                    'description': 'Wrong parameter type'
                })
            elif method == 'wrong':
                # 处理 'wrong' 方法 - 使用错误的参数值
                flawed['parameter_flaws'].append({
                    'tool': tool,
                    'index': idx,
                    'type': 'wrong_value',
                    'description': 'Wrong parameter value'
                })
        
        flawed['flaw_type'] = f'parameter_{method}'
        flawed['flaw_severity'] = severity
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        
        return flawed
    


    def introduce_missing_steps(self, workflow: Dict, method: str = 'middle', 
                            severity: str = 'medium') -> Dict:
        """引入步骤缺失"""
        flawed = copy.deepcopy(workflow)
        optimal_seq = workflow.get('optimal_sequence', [])
        
        if not optimal_seq or len(optimal_seq) < 3:
            return flawed
        
        # 新增：只删除required_tools中的工具
        if self.required_tools_filter:
            valid_indices = [i for i, tool in enumerate(optimal_seq) 
                            if tool in self.required_tools_filter]
            if not valid_indices:
                print(f"[DEBUG] No required tools found for missing steps")
                return flawed
        else:
            valid_indices = list(range(len(optimal_seq)))
        
        if method == 'middle':
            # 删除中间步骤
            if severity == 'light':
                # 删除一个中间步骤
                middle_indices = [i for i in valid_indices if 0 < i < len(optimal_seq) - 1]
                if middle_indices:
                    idx = random.choice(middle_indices)
                    optimal_seq.pop(idx)
            elif severity == 'medium':
                # 删除2个步骤
                num_to_remove = min(2, len(valid_indices) - 1)
                if num_to_remove > 0:
                    indices_to_remove = sorted(random.sample(valid_indices, num_to_remove), reverse=True)
                    for idx in indices_to_remove:
                        optimal_seq.pop(idx)
            else:  # severe
                # 只保留首尾（如果它们在required_tools中）
                new_seq = []
                if 0 in valid_indices:
                    new_seq.append(optimal_seq[0])
                # 添加不在required_tools中的工具
                for i, tool in enumerate(optimal_seq):
                    if tool not in self.required_tools_filter:
                        new_seq.append(tool)
                if len(optimal_seq) - 1 in valid_indices and optimal_seq[-1] not in new_seq:
                    new_seq.append(optimal_seq[-1])
                optimal_seq = new_seq
        
        elif method == 'validation':
            # 删除所有验证相关的步骤（只删除required_tools中的）
            optimal_seq = [tool for i, tool in enumerate(optimal_seq) 
                        if not (i in valid_indices and 
                                ('validat' in tool.lower() or 'check' in tool.lower()))]
        
        elif method == 'critical':
            # 删除关键步骤 - 删除中间的重要步骤，保留首尾
            if len(optimal_seq) > 2:
                if severity == 'light':
                    # 删除1个中间关键步骤
                    if len(valid_indices) > 2:
                        middle_indices = [i for i in valid_indices if 0 < i < len(optimal_seq) - 1]
                        if middle_indices:
                            idx = random.choice(middle_indices)
                            optimal_seq.pop(idx)
                elif severity == 'medium':
                    # 删除1-2个中间步骤
                    middle_indices = [i for i in valid_indices if 0 < i < len(optimal_seq) - 1]
                    if middle_indices:
                        num_to_remove = min(2, len(middle_indices))
                        indices_to_remove = sorted(random.sample(middle_indices, num_to_remove), reverse=True)
                        for idx in indices_to_remove:
                            optimal_seq.pop(idx)
                else:  # severe
                    # 删除所有中间步骤，只保留首尾
                    if len(optimal_seq) > 2:
                        optimal_seq = [optimal_seq[0], optimal_seq[-1]]
        else:
            # 默认处理：删除随机步骤
            if severity == 'light':
                if valid_indices:
                    idx = random.choice(valid_indices)
                    optimal_seq.pop(idx)
            elif severity == 'medium':
                num_to_remove = min(2, len(valid_indices))
                if num_to_remove > 0:
                    indices_to_remove = sorted(random.sample(valid_indices, num_to_remove), reverse=True)
                    for idx in indices_to_remove:
                        optimal_seq.pop(idx)
            else:  # severe
                # 删除一半的步骤
                num_to_remove = len(valid_indices) // 2
                if num_to_remove > 0:
                    indices_to_remove = sorted(random.sample(valid_indices, num_to_remove), reverse=True)
                    for idx in indices_to_remove:
                        optimal_seq.pop(idx)
        
        flawed['optimal_sequence'] = optimal_seq
        flawed['flaw_type'] = f'missing_{method}'
        flawed['flaw_severity'] = severity
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        return flawed
    
    def introduce_redundancy(self, workflow: Dict, method: str = 'duplicate', 
                           severity: str = 'medium') -> Dict:
        """引入冗余步骤"""
        flawed = copy.deepcopy(workflow)
        optimal_seq = workflow.get('optimal_sequence', [])
        
        if not optimal_seq:
            return flawed
        
        if method == 'duplicate':
            # 重复某些步骤
            if severity == 'light':
                # 重复一个步骤
                idx = random.randint(0, len(optimal_seq) - 1)
                optimal_seq.insert(idx + 1, optimal_seq[idx])
            elif severity == 'medium':
                # 重复2-3个步骤
                for _ in range(random.randint(2, 3)):
                    idx = random.randint(0, len(optimal_seq) - 1)
                    optimal_seq.insert(idx + 1, optimal_seq[idx])
            else:  # severe
                # 每个步骤都重复
                new_seq = []
                for tool in optimal_seq:
                    new_seq.extend([tool, tool])
                optimal_seq = new_seq
        
        elif method == 'unnecessary':
            # 添加不必要的工具
            unnecessary_tools = ['utility_logger', 'utility_cache', 'utility_tracker']
            
            if severity == 'light':
                insertions = 1
            elif severity == 'medium':
                insertions = 3
            else:  # severe
                insertions = len(optimal_seq)
            
            for _ in range(insertions):
                idx = random.randint(0, len(optimal_seq))
                tool = random.choice(unnecessary_tools)
                if tool in self.tool_registry:
                    optimal_seq.insert(idx, tool)
        
        flawed['optimal_sequence'] = optimal_seq
        flawed['flaw_type'] = f'redundancy_{method}'
        flawed['flaw_severity'] = severity
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        return flawed
    
    def introduce_logic_break(self, workflow: Dict, method: str = 'format', 
                            severity: str = 'medium') -> Dict:
        """引入逻辑断裂"""
        flawed = copy.deepcopy(workflow)
        optimal_seq = workflow.get('optimal_sequence', [])
        
        if not optimal_seq:
            return flawed
        
        if method == 'format':
            # 标记某些步骤的输出格式不匹配
            flawed['format_mismatches'] = []
            
            if severity == 'light':
                num_breaks = 1
            elif severity == 'medium':
                num_breaks = 2
            else:  # severe
                num_breaks = len(optimal_seq) // 2
            
            break_indices = random.sample(range(len(optimal_seq) - 1), 
                                        min(num_breaks, len(optimal_seq) - 1))
            
            for idx in break_indices:
                flawed['format_mismatches'].append({
                    'between': (optimal_seq[idx], optimal_seq[idx + 1]),
                    'issue': 'Output format incompatible with next step input'
                })
        
        elif method == 'unrelated':
            # 插入与任务无关的步骤
            unrelated_tools = self._get_unrelated_tools(optimal_seq)
            
            if severity == 'light':
                insertions = 1
            elif severity == 'medium':
                insertions = 2
            else:  # severe
                insertions = len(optimal_seq) // 2
            
            for _ in range(insertions):
                if unrelated_tools:
                    idx = random.randint(1, len(optimal_seq) - 1)
                    optimal_seq.insert(idx, random.choice(unrelated_tools))
        
        flawed['optimal_sequence'] = optimal_seq
        flawed['flaw_type'] = f'logic_{method}'
        flawed['flaw_severity'] = severity
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        return flawed
    
    def introduce_semantic_mismatch(self, workflow: Dict, severity: str = 'medium') -> Dict:
        """引入语义不匹配错误 - RAG特定缺陷"""
        flawed = copy.deepcopy(workflow)
        optimal_seq = workflow.get('optimal_sequence', [])
        
        if not optimal_seq or not self.embedding_manager:
            return flawed
        
        logger.debug(f" Introducing semantic mismatch with severity: {severity}")
        
        # 决定替换多少工具
        if severity == 'light':
            num_replacements = 1
        elif severity == 'medium':
            num_replacements = min(2, len(optimal_seq) // 3)
        else:  # severe
            num_replacements = len(optimal_seq) // 2
        
        # 记录语义替换信息
        flawed['semantic_mismatches'] = []
        
        replaced_indices = random.sample(range(len(optimal_seq)), 
                                       min(num_replacements, len(optimal_seq)))
        
        for idx in replaced_indices:
            current_tool = optimal_seq[idx]
            
            # 找到语义相似但实际功能不匹配的工具
            similar_tools = self._find_semantically_similar_tools(
                current_tool, exclude_same_function=True)
            
            if similar_tools:
                # 选择相似度在0.6-0.8之间的工具（太相似或太不同都不好）
                candidates = [(tool, score) for tool, score in similar_tools 
                             if 0.6 <= score <= 0.8]
                
                if candidates:
                    replacement_tool, similarity_score = candidates[0]
                else:
                    replacement_tool, similarity_score = similar_tools[0]
                
                optimal_seq[idx] = replacement_tool
                
                flawed['semantic_mismatches'].append({
                    'position': idx,
                    'original': current_tool,
                    'replacement': replacement_tool,
                    'similarity_score': similarity_score,
                    'reason': 'Semantically similar but functionally different'
                })
                
                logger.debug(f" Replaced {current_tool} with {replacement_tool} (similarity: {similarity_score:.3f})")
        
        flawed['optimal_sequence'] = optimal_seq
        flawed['flaw_type'] = 'semantic_mismatch'
        flawed['flaw_severity'] = severity
        flawed['uses_rag_detection'] = True  # 标记这个缺陷需要RAG来检测
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        return flawed
    
    def introduce_semantic_drift(self, workflow: Dict, severity: str = 'medium') -> Dict:
        """引入语义漂移 - 工具选择逐渐偏离原始意图"""
        flawed = copy.deepcopy(workflow)
        optimal_seq = workflow.get('optimal_sequence', [])
        
        if not optimal_seq or len(optimal_seq) < 3 or not self.embedding_manager:
            return flawed
        
        logger.debug(f" Introducing semantic drift with severity: {severity}")
        
        # 语义漂移从某个点开始
        if severity == 'light':
            drift_start = len(optimal_seq) - 2  # 最后几步开始漂移
        elif severity == 'medium':
            drift_start = len(optimal_seq) // 2  # 中间开始漂移
        else:  # severe
            drift_start = 2  # 早期就开始漂移
        
        flawed['semantic_drift_info'] = {
            'drift_start': drift_start,
            'original_tools': optimal_seq[drift_start:],
            'replacements': []
        }
        
        # 从drift_start开始，每个工具基于前一个工具选择
        for idx in range(drift_start, len(optimal_seq)):
            if idx == drift_start:
                # 第一个漂移：基于原工具找相似的
                base_tool = optimal_seq[idx]
            else:
                # 后续漂移：基于上一个替换的工具
                base_tool = optimal_seq[idx - 1]
            
            similar_tools = self._find_semantically_similar_tools(
                base_tool, exclude_same_function=True)
            
            if similar_tools:
                # 选择中等相似度的工具，造成逐渐漂移
                replacement_tool, similarity_score = similar_tools[0]
                optimal_seq[idx] = replacement_tool
                
                flawed['semantic_drift_info']['replacements'].append({
                    'position': idx,
                    'original': flawed['semantic_drift_info']['original_tools'][idx - drift_start],
                    'replacement': replacement_tool,
                    'based_on': base_tool,
                    'similarity_score': similarity_score
                })
                
                logger.debug(f" Drift at position {idx}: {replacement_tool} (based on {base_tool})")
        
        flawed['optimal_sequence'] = optimal_seq
        flawed['flaw_type'] = 'semantic_drift'
        flawed['flaw_severity'] = severity
        flawed['uses_rag_detection'] = True  # 标记这个缺陷需要RAG来检测
        # 更新smart_actions以匹配新的sequence
        self._update_smart_actions(flawed)

        return flawed
    
    def _get_tool_category(self, tool_name: str) -> str:
        """获取工具的类别"""
        if '_' in tool_name:
            return tool_name.split('_')[0]
        return 'general'
    
    def _get_unrelated_tools(self, current_tools: List[str]) -> List[str]:
        """获取与当前任务无关的工具"""
        # 获取当前工具的类别
        current_categories = set(self._get_tool_category(tool) for tool in current_tools)
        
        # 找出不相关的类别
        unrelated = []
        for category, tools in self.tool_categories.items():
            if category not in current_categories:
                unrelated.extend(tools[:2])  # 每个不相关类别取2个工具
        
        return unrelated
    
    def get_available_flaw_types(self) -> Dict[str, List[str]]:
        """
        获取所有可用的缺陷类型，按类别分组
        
        Returns:
            Dict[类别名, List[缺陷类型]]
        """
        return {
            'order': ['order_flaw_swap', 'order_flaw_dependency'],
            'tool': ['tool_misuse_similar', 'tool_misuse_wrong_category'],
            'parameter': ['param_missing', 'param_wrong_type'],
            'missing': ['missing_middle', 'missing_validation'],
            'redundant': ['redundant_duplicate', 'redundant_unnecessary'],
            'logic': ['logic_break_format', 'logic_break_unrelated'],
            'semantic': ['semantic_mismatch', 'semantic_drift']  # 需要RAG
        }
    
    def inject_specific_flaw(self, workflow: Dict, flaw_type: str, 
                           severity: str = 'severe') -> Dict:
        """
        注入特定类型的缺陷（用于鲁棒性测试）
        
        Args:
            workflow: 原始工作流
            flaw_type: 缺陷类型
            severity: 严重程度
            
        Returns:
            带有特定缺陷的工作流
        """
        # 映射缺陷类型到具体方法
        flaw_mapping = {
            'sequence_disorder': lambda w, s: self.introduce_order_flaw(w, 'dependency', s),
            'tool_misuse': lambda w, s: self.introduce_tool_misuse(w, 'similar', s),
            'parameter_error': lambda w, s: self.introduce_parameter_flaw(w, 'wrong', s),
            'missing_step': lambda w, s: self.introduce_missing_steps(w, 'critical', s),
            'redundant_operations': lambda w, s: self.introduce_redundancy(w, 'duplicate', s),
            'logical_inconsistency': lambda w, s: self.introduce_logic_break(w, 'format', s),
            'semantic_drift': lambda w, s: self.introduce_semantic_drift(w, s)
        }
        
        if flaw_type not in flaw_mapping:
            raise ValueError(f"Unknown flaw type: {flaw_type}")
        
        # 生成特定缺陷
        flawed_workflow = flaw_mapping[flaw_type](workflow, severity)
        
        # 添加缺陷类型标记
        flawed_workflow['injected_flaw_type'] = flaw_type
        flawed_workflow['flaw_severity'] = severity
        
        return flawed_workflow

    def generate_selective_flaws(self, optimal_workflow: Dict,
                                flaw_selection: Dict[str, str] = None,
                                random_selection: bool = True,
                                force_severe: bool = False) -> Dict[str, Dict]:
        """
        选择性生成缺陷workflows
        
        Args:
            optimal_workflow: 最优workflow
            flaw_selection: 指定每个severity要生成的缺陷类型
            random_selection: 如果为True且未指定flaw_selection，则随机选择
            force_severe: 如果为True，所有缺陷都使用severe级别（用于测试极端情况）
        
        Returns:
            生成的缺陷workflows字典
        """
        flawed_workflows = {}
        
        # 如果没有指定选择，则根据random_selection决定
        if not flaw_selection:
            if random_selection:
                flaw_selection = self._random_select_flaws()
            else:
                return {}
        
        # 根据选择生成缺陷
        for severity, flaw_type in flaw_selection.items():
            if severity not in ['light', 'medium', 'severe']:
                print(f"[WARNING] Invalid severity: {severity}, skipping")
                continue
            
            # 决定使用的severity级别
            actual_severity = 'severe' if force_severe else severity
            
            # 生成指定的缺陷类型
            flawed_workflow = self._generate_single_flaw(
                optimal_workflow, flaw_type, actual_severity
            )
            
            if flawed_workflow:
                # 使用组合键：缺陷类型_实际严重程度
                key = f"{flaw_type}_{actual_severity}"
                flawed_workflows[key] = flawed_workflow
                if force_severe:
                    print(f"[DEBUG] Generated {flaw_type} with forced {actual_severity} severity (requested: {severity})")
                else:
                    print(f"[DEBUG] Generated {flaw_type} with {actual_severity} severity")
        
        return flawed_workflows
        
    def _random_select_flaws(self) -> Dict[str, str]:
        """
        为每个severity随机选择一种缺陷类型
        
        Returns:
            Dict[severity, flaw_type]
        """
        all_flaw_types = []
        for category_flaws in self.get_available_flaw_types().values():
            all_flaw_types.extend(category_flaws)
        
        # 移除需要RAG的缺陷（如果embedding_manager不可用）
        if not self.embedding_manager:
            all_flaw_types = [f for f in all_flaw_types 
                            if not f.startswith('semantic_')]
        
        # 为每个severity随机选择不同的缺陷
        selected_flaws = random.sample(all_flaw_types, min(3, len(all_flaw_types)))
        
        selection = {}
        severities = ['light', 'medium', 'severe']
        for i, severity in enumerate(severities):
            if i < len(selected_flaws):
                selection[severity] = selected_flaws[i]
            else:
                # 如果缺陷类型不够，循环使用
                selection[severity] = selected_flaws[i % len(selected_flaws)]
        
        logger.debug(f" Random flaw selection: {selection}")
        return selection
    
    def _generate_single_flaw(self, workflow: Dict, flaw_type: str, 
                            severity: str) -> Optional[Dict]:
        """
        生成单个指定类型的缺陷
        
        Args:
            workflow: 原始workflow
            flaw_type: 缺陷类型
            severity: 严重程度
            
        Returns:
            缺陷workflow或None
        """
        # 映射缺陷类型到生成方法
        flaw_generators = {
            # Order flaws
            'order_flaw_swap': lambda: self.introduce_order_flaw(
                workflow, method='swap', severity=severity),
            'order_flaw_dependency': lambda: self.introduce_order_flaw(
                workflow, method='dependency', severity=severity),
            
            # Tool misuse
            'tool_misuse_similar': lambda: self.introduce_tool_misuse(
                workflow, method='similar', severity=severity),
            'tool_misuse_wrong_category': lambda: self.introduce_tool_misuse(
                workflow, method='wrong_category', severity=severity),
            
            # Parameter flaws
            'param_missing': lambda: self.introduce_parameter_flaw(
                workflow, method='missing', severity=severity),
            'param_wrong_type': lambda: self.introduce_parameter_flaw(
                workflow, method='wrong_type', severity=severity),
            
            # Missing steps
            'missing_middle': lambda: self.introduce_missing_steps(
                workflow, method='middle', severity=severity),
            'missing_validation': lambda: self.introduce_missing_steps(
                workflow, method='validation', severity=severity),
            
            # Redundancy
            'redundant_duplicate': lambda: self.introduce_redundancy(
                workflow, method='duplicate', severity=severity),
            'redundant_unnecessary': lambda: self.introduce_redundancy(
                workflow, method='unnecessary', severity=severity),
            
            # Logic breaks
            'logic_break_format': lambda: self.introduce_logic_break(
                workflow, method='format', severity=severity),
            'logic_break_unrelated': lambda: self.introduce_logic_break(
                workflow, method='unrelated', severity=severity),
        }
        
        # Semantic flaws (需要embedding_manager)
        if self.embedding_manager:
            flaw_generators.update({
                'semantic_mismatch': lambda: self.introduce_semantic_mismatch(
                    workflow, severity=severity),
                'semantic_drift': lambda: self.introduce_semantic_drift(
                    workflow, severity=severity),
            })
        
        # 生成指定的缺陷
        if flaw_type in flaw_generators:
            return flaw_generators[flaw_type]()
        else:
            print(f"[ERROR] Unknown flaw type: {flaw_type}")
            return None
    
    def get_recommended_flaw_selection(self) -> Dict[str, str]:
        """
        获取推荐的缺陷选择（基于经验的最有代表性的缺陷）
        
        Returns:
            Dict[severity, flaw_type]
        """
        # 推荐的缺陷类型组合，每个severity使用不同的缺陷类型
        if self.embedding_manager:
            # 有RAG支持时的推荐
            recommended_types = {
                'light': 'order_flaw_swap',        # 轻微：简单的顺序错误
                'medium': 'semantic_mismatch',     # 中等：语义不匹配
                'severe': 'missing_middle'         # 严重：缺失关键步骤
            }
        else:
            # 无RAG支持时的推荐
            recommended_types = {
                'light': 'order_flaw_swap',        # 轻微：简单的顺序错误
                'medium': 'tool_misuse_similar',   # 中等：相似工具误用
                'severe': 'missing_middle'         # 严重：缺失关键步骤
            }
        
        print(f"[DEBUG] Recommended flaw selection: {recommended_types}")
        return recommended_types