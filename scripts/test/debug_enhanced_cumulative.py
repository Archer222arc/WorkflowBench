#\!/usr/bin/env python3
"""Debug enhanced cumulative manager的AI分类逻辑"""

# Monkey patch enhanced cumulative manager
import sys
from enhanced_cumulative_manager import EnhancedCumulativeManager

original_categorize_and_count = EnhancedCumulativeManager.categorize_and_count

def debug_categorize_and_count(self, error_msg):
    """Debug版本显示分类过程"""
    print(f"\n[DEBUG] categorize_and_count called with error_msg: '{error_msg}'")
    print(f"[DEBUG] use_ai_classification: {self.use_ai_classification}")
    print(f"[DEBUG] ai_classifier exists: {self.ai_classifier is not None}")
    
    result = original_categorize_and_count(self, error_msg)
    print(f"[DEBUG] categorize_and_count result: {result}")
    return result

# 应用monkey patch
EnhancedCumulativeManager.categorize_and_count = debug_categorize_and_count

print("Enhanced cumulative manager已被debug patch")
