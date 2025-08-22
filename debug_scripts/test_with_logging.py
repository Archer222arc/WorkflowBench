#!/usr/bin/env python3
"""
Test with full logging for qwen2.5-72b-instruct
"""
import json
import os
from pathlib import Path
from datetime import datetime
from mdp_workflow_generator import MDPWorkflowGenerator
from workflow_quality_test_flawed import WorkflowQualityTester

def test_single_task():
    """Run single test and capture logs"""
    
    # Initialize generator
    print("Initializing generator...")
    generator = MDPWorkflowGenerator(
        model_path='checkpoints/best_model.pt'
    )
    
    # Initialize tester
    print("Initializing tester...")
    tester = WorkflowQualityTester(
        generator=generator,
        save_logs=True  # Ensure logs are saved
    )
    
    # Get a single task - task_instances is a dict of lists
    if 'simple_task' not in tester.task_instances:
        print("No simple_task instances found!")
        return
    
    task_instances = tester.task_instances['simple_task']
    if not task_instances:
        print("No simple_task instances found!")
        return
    
    task = task_instances[0]
    print(f"\nTask: {task.get('description', 'No description')[:100]}...")
    print(f"Required tools: {task.get('required_tools', [])}")
    
    # Generate workflow
    print("\nGenerating workflow...")
    workflow = generator.generate_workflow_for_instance(
        task_instance=task,
        prompt_type='optimal'
    )
    print(f"Generated workflow: {workflow['sequence']}")
    
    # Test with qwen model
    print("\nTesting with qwen2.5-72b-instruct...")
    
    # Import InteractiveExecutor directly
    from interactive_executor import InteractiveExecutor
    
    # Create executor
    executor = InteractiveExecutor(
        model="qwen2.5-72b-instruct",
        tool_registry=generator.full_tool_registry,
        embedding_manager=generator.embedding_manager,
        enable_search=True,
        tool_success_rate=0.8
    )
    
    # Create test prompt
    prompt = f"""You are a workflow execution agent. Your task is to execute the following workflow step by step.

Task: {task.get('description', '')}

Required workflow sequence:
{json.dumps(workflow['sequence'], indent=2)}

Available tools:
{json.dumps(list(generator.full_tool_registry.keys())[:10], indent=2)}
... and more

IMPORTANT: You must execute each tool in the workflow sequence using the format:
<tool_call>
{{"tool_name": "tool_name_here", "parameters": {{"param1": "value1"}}}}
</tool_call>

Start by executing the first tool in the workflow sequence."""

    print("\nPrompt preview:")
    print("-" * 50)
    print(prompt[:500] + "...")
    print("-" * 50)
    
    # Execute
    result = executor.execute_workflow(
        task=task,
        workflow_sequence=workflow['sequence'],
        prompt_type='optimal'
    )
    
    print(f"\nExecution result:")
    print(f"Success: {result.get('success', False)}")
    print(f"Tool calls: {len(result.get('tool_calls', []))}")
    print(f"Turns: {result.get('turns', 0)}")
    
    # Save the result with conversation history
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"qwen_test_log_{timestamp}.json"
    
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'task': task,
            'workflow': workflow,
            'prompt': prompt,
            'result': result,
            'conversation_history': result.get('conversation_history', [])
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nFull log saved to: {log_file}")
    
    # Print first conversation turn
    if result.get('conversation_history'):
        print("\n" + "="*60)
        print("FIRST CONVERSATION TURN:")
        print("="*60)
        first = result['conversation_history'][0]
        print(f"\nUSER:\n{first.get('user', 'N/A')[:1000]}")
        print(f"\nASSISTANT:\n{first.get('assistant', 'N/A')[:1000]}")

if __name__ == "__main__":
    test_single_task()