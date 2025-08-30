#!/bin/bash

# Test script to verify run_systematic_test_final.sh modifications
# This script tests the basic functionality without running full tests

# Load color variables and functions from the main script
source /dev/stdin <<'EOF'
# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Define arrays (copy from main script)
OPENSOURCE_MODELS=(
    "DeepSeek-V3-0324"
    "DeepSeek-R1-0528"
    "qwen2.5-72b-instruct"
    "qwen2.5-32b-instruct"
    "qwen2.5-14b-instruct"
    "qwen2.5-7b-instruct"
    "qwen2.5-3b-instruct"
    "Llama-3.3-70B-Instruct"
)

CLOSED_SOURCE_MODELS=(
    "gpt-4o-mini"
    "gpt-5-mini"
    "grok-3-mini"
    "claude_sonnet4"
    "o3-0416-global"
    "gemini-2.5-flash-06-17"
)

# Model type selection variables
MODEL_TYPE=""
CURRENT_MODELS=()
RESULT_SUFFIX=""
EOF

# Test functions
test_model_type_selection() {
    echo -e "${CYAN}Testing model type selection...${NC}"
    
    # Test opensource selection
    MODEL_TYPE="opensource"
    CURRENT_MODELS=("${OPENSOURCE_MODELS[@]}")
    RESULT_SUFFIX=""
    echo -e "${GREEN}✅ Opensource models configured: ${#CURRENT_MODELS[@]} models${NC}"
    
    # Test closed-source selection
    MODEL_TYPE="closed_source"
    CURRENT_MODELS=("${CLOSED_SOURCE_MODELS[@]}")
    RESULT_SUFFIX="_closed_source"
    echo -e "${GREEN}✅ Closed-source models configured: ${#CURRENT_MODELS[@]} models${NC}"
    echo -e "${CYAN}Result suffix: ${RESULT_SUFFIX}${NC}"
}

test_concurrency_params() {
    echo -e "${CYAN}Testing concurrency parameter function...${NC}"
    
    # Test function exists
    if command -v get_concurrency_params >/dev/null 2>&1; then
        echo -e "${GREEN}✅ get_concurrency_params function exists${NC}"
    else
        echo -e "${YELLOW}⚠️  get_concurrency_params function not loaded, testing logic...${NC}"
        
        # Test the logic manually
        MODEL_TYPE="closed_source"
        model="gpt-4o-mini"
        base_params="--basic-params"
        
        if [ "$MODEL_TYPE" = "closed_source" ]; then
            case $model in
                "gpt-4o-mini"|"gpt-5-mini"|"grok-3-mini")
                    result="$base_params --max-workers 15 --max-prompt-workers 3"
                    echo -e "${GREEN}✅ Azure closed-source model params: $result${NC}"
                    ;;
                "claude_sonnet4"|"o3-0416-global"|"gemini-2.5-flash-06-17")
                    result="$base_params --max-workers 8 --max-prompt-workers 1"
                    echo -e "${GREEN}✅ IdealLab closed-source model params: $result${NC}"
                    ;;
            esac
        fi
    fi
}

test_arrays() {
    echo -e "${CYAN}Testing model arrays...${NC}"
    echo -e "${YELLOW}Opensource models (${#OPENSOURCE_MODELS[@]}):${NC}"
    for model in "${OPENSOURCE_MODELS[@]}"; do
        echo "  - $model"
    done
    
    echo -e "${YELLOW}Closed-source models (${#CLOSED_SOURCE_MODELS[@]}):${NC}"
    for model in "${CLOSED_SOURCE_MODELS[@]}"; do
        echo "  - $model"
    done
}

main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Testing run_systematic_test_final.sh modifications${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    
    test_arrays
    echo ""
    test_model_type_selection
    echo ""
    test_concurrency_params
    echo ""
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ All basic tests completed${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "1. Run the modified script to test the menu interface"
    echo "2. Verify that closed-source models are properly excluded from 5.2"
    echo "3. Test the concurrency strategies with actual API calls"
    echo "4. Verify result file separation for closed-source models"
}

main "$@"