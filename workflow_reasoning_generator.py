# 相同位置的修复代码
# 修改的行用注释标注：# <- 修改了这一行

#!/usr/bin/env python3  # <- 修改了这一行：添加shebang
"""  # <- 修改了这一行：添加模块文档字符串
Workflow Reasoning Generator
============================
统一的workflow reasoning生成器，消除重复代码
"""  # <- 修改了这一行

from typing import Dict, List, Optional  # <- 修改了这一行：添加类型导入
from tool_capability_manager import ToolCapabilityManager  # <- 修改了这一行：添加必要的导入


class WorkflowReasoningGenerator:
    """统一的workflow reasoning生成器"""
    
    def __init__(self, tool_capabilities: Dict, tool_capability_manager: ToolCapabilityManager):
        """初始化reasoning生成器"""
        self.tool_capabilities = tool_capabilities
        self.tool_capability_manager = tool_capability_manager
        
        # 任务类型到描述的映射
        self.task_context_mapping = {
            "data_pipeline": "handling data transformation",
            "api_integration": "managing API communication", 
            "basic_task": "processing file operations",
            "basic_task": "executing basic workflow",
            "multi_stage_pipeline": "orchestrating complex pipeline",
            "simple_task": "performing simple operations"
        }
    
    def generate_reasoning(self, task_type: str, optimal_sequence: List[str]) -> List[str]:
        """生成reasoning步骤（统一实现）"""
        if not optimal_sequence:
            return ["No tools required for this task"]
        
        reasoning_steps = []
        categories = self.tool_capability_manager.categorize_tool_sequence(
            optimal_sequence, self.tool_capabilities
        )
        
        for i, (tool, category) in enumerate(zip(optimal_sequence, categories)):
            # 基础reasoning
            if i == 0:
                reasoning = f"Step {i+1}: Use {tool} to initialize the workflow"
            elif i == len(optimal_sequence) - 1:
                reasoning = f"Step {i+1}: Use {tool} to finalize the workflow"
            else:
                # 基于类别转换生成更智能的reasoning
                prev_category = categories[i-1] if i > 0 else None
                next_category = categories[i+1] if i < len(categories)-1 else None
                reasoning = self._generate_transition_reasoning(
                    i+1, tool, category, prev_category, next_category
                )
            
            # 添加语义操作信息
            if tool in self.tool_capabilities:
                capability = self.tool_capabilities[tool]
                if hasattr(capability, 'semantic_operations') and capability.semantic_operations:
                    ops = capability.semantic_operations[:2]
                    reasoning += f" ({', '.join(ops)})"
            
            # 添加任务上下文
            task_context = self.task_context_mapping.get(
                task_type, "executing workflow"
            )
            reasoning += f" - {task_context}"
            
            reasoning_steps.append(reasoning)
        
        return reasoning_steps
    
    def _generate_transition_reasoning(self, step_num: int, tool: str, 
                                     category: str, prev_category: str, 
                                     next_category: str) -> str:
        """基于类别转换生成reasoning"""
        # 智能化的转换描述
        transition_templates = {
            ('input', 'validation'): "validate the loaded data",
            ('validation', 'transformation'): "transform the validated data",
            ('transformation', 'aggregation'): "aggregate the transformed results",
            ('aggregation', 'output'): "prepare aggregated data for output",
            ('transformation', 'output'): "prepare transformed data for output"
        }
        
        key = (prev_category, category) if prev_category else (category, next_category)
        transition_desc = transition_templates.get(key, "process data")
        
        return f"Step {step_num}: Use {tool} to {transition_desc}"
    
    def generate_contextual_reasoning(self, task_instance: Dict, 
                                    optimal_sequence: List[str], 
                                    operations: List[str]) -> List[str]:
        """生成基于任务实例的上下文reasoning"""
        reasoning_steps = []
        task_type = task_instance.get('task_type', 'unknown')
        
        for i, tool in enumerate(optimal_sequence):
            capability = self.tool_capabilities.get(tool)
            category = self.tool_capability_manager.get_category(capability) if capability else 'general'
            
            # 基础reasoning
            reasoning = f"Step {i+1}: Use {tool}"
            
            # 添加类别信息
            if category != 'general':
                reasoning += f" ({category} tool)"
            
            # 添加操作上下文
            if i < len(operations) and operations[i]:
                reasoning += f" for '{operations[i]}'"
            elif capability and hasattr(capability, 'semantic_operations'):
                ops = capability.semantic_operations[:2]
                reasoning += f" to {', '.join(ops)}"
            
            # 添加依赖信息
            if capability and hasattr(capability, 'dependencies') and capability.dependencies:
                deps = ', '.join(capability.dependencies[:2])
                if len(capability.dependencies) > 2:
                    deps += f" +{len(capability.dependencies)-2} more"
                reasoning += f" (requires: {deps})"
            
            reasoning_steps.append(reasoning)
        
        return reasoning_steps
    
    def generate_tool_reasoning(self, tool_name: str, position: int, 
                               task_instance: Dict, context: Dict) -> str:
        """生成单个工具选择的reasoning"""
        reasons = []
        
        # 基于位置的reasoning
        if position == 0:
            reasons.append("Initial data loading/setup step")
        elif position == len(context.get('sequence', [])) - 1:
            reasons.append("Final output/completion step")
        
        # 基于工具能力的reasoning
        if tool_name in self.tool_capabilities:
            capability = self.tool_capabilities[tool_name]
            category = self.tool_capability_manager.get_category(capability)
            reasons.append(f"{category} tool")
            
            if hasattr(capability, 'semantic_operations'):
                ops = capability.semantic_operations[:2]
                reasons.append(f"performs {', '.join(ops)}")
        
        # 基于任务需求
        if 'required_tools' in task_instance and tool_name in task_instance['required_tools']:
            reasons.append("Required tool for this task")
        
        return "; ".join(reasons) if reasons else "Standard workflow step"
    
    def generate_workflow_guidance(self, workflow: Dict) -> str:
        """生成workflow执行指导"""
        optimal_sequence = workflow.get('optimal_sequence', [])
        critical_tools = workflow.get('critical_tools', [])
        
        if not optimal_sequence:
            return "No specific workflow guidance available."
        
        guidance_parts = ["Workflow Execution Guide:"]
        
        # 使用统一的reasoning生成
        reasoning_steps = self.generate_reasoning(
            workflow.get('task_type', 'unknown'), 
            optimal_sequence
        )
        
        for i, (tool, reasoning) in enumerate(zip(optimal_sequence, reasoning_steps), 1):
            if tool in critical_tools:
                guidance_parts.append(f"{i}. {tool} (CRITICAL)")
            else:
                guidance_parts.append(f"{i}. {tool}")
            guidance_parts.append(f"   {reasoning}")
        
        return '\n'.join(guidance_parts)