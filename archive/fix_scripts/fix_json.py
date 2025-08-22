#!/usr/bin/env python3
"""
Fix truncated JSON file by properly closing all open structures
"""

import json
import re

def fix_json_file(filepath):
    """Try to fix a truncated JSON file"""
    try:
        # First try to load it normally
        with open(filepath, 'r') as f:
            data = json.load(f)
        print("File is already valid JSON")
        return data
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}")
        
    # Read the file content
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Count open brackets/braces
    open_braces = content.count('{')
    close_braces = content.count('}')
    open_brackets = content.count('[')
    close_brackets = content.count(']')
    
    print(f"Open braces: {open_braces}, Close braces: {close_braces}")
    print(f"Open brackets: {open_brackets}, Close brackets: {close_brackets}")
    
    # Try to fix by adding missing closing characters
    fixed_content = content.rstrip()
    
    # If it ends with a partial value, remove it
    if fixed_content.endswith('"smart_workflow":'):
        # Remove the incomplete field
        fixed_content = fixed_content[:fixed_content.rfind('"smart_workflow":')-15]  # Also remove comma and newline
    
    # Add closing braces/brackets
    missing_brackets = open_brackets - close_brackets
    missing_braces = open_braces - close_braces
    
    # Close any open structures
    for _ in range(missing_brackets):
        fixed_content += ']'
    for _ in range(missing_braces):
        fixed_content += '}'
    
    # Try to parse the fixed content
    try:
        data = json.loads(fixed_content)
        print("Successfully fixed JSON!")
        
        # Save the fixed version
        with open(filepath + '.fixed', 'w') as f:
            json.dump(data, f, indent=2)
        
        # Replace original
        import shutil
        shutil.move(filepath + '.fixed', filepath)
        
        return data
    except json.JSONDecodeError as e:
        print(f"Still couldn't fix: {e}")
        # Create a minimal valid structure
        print("Creating minimal valid structure...")
        
        # Find the last complete test session
        last_session_match = list(re.finditer(r'"session_id":\s*"([^"]+)"', content))
        if last_session_match:
            last_session_id = last_session_match[-1].group(1)
            # Truncate at a safe point
            safe_truncate_point = content.find(last_session_id) + len(last_session_id) + 50
            if safe_truncate_point < len(content):
                truncated = content[:safe_truncate_point]
                # Close all structures properly
                truncated = truncated.rstrip(',\n\r\t }]')
                
                # Count structures again
                open_braces = truncated.count('{')
                close_braces = truncated.count('}')
                open_brackets = truncated.count('[')
                close_brackets = truncated.count(']')
                
                # Add appropriate closing
                if truncated.endswith('"'):
                    truncated += '}'  # Close the current object
                
                # Close remaining structures
                for _ in range(open_brackets - close_brackets):
                    truncated += ']'
                for _ in range(open_braces - close_braces):
                    truncated += '}'
                
                try:
                    data = json.loads(truncated)
                    print("Successfully created valid truncated JSON!")
                    with open(filepath, 'w') as f:
                        json.dump(data, f, indent=2)
                    return data
                except:
                    pass
        
        # If all else fails, reset to empty valid structure
        print("Resetting to empty structure...")
        empty_db = {
            "created_at": "2025-08-03T21:33:55.261591",
            "total_tests": 0,
            "total_api_calls": 0,
            "models": {},
            "test_sessions": []
        }
        
        with open(filepath, 'w') as f:
            json.dump(empty_db, f, indent=2)
        
        return empty_db

if __name__ == "__main__":
    import sys
    filepath = sys.argv[1] if len(sys.argv) > 1 else "cumulative_test_results/results_database.json"
    fix_json_file(filepath)
    print(f"Fixed {filepath}")