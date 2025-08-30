#!/bin/bash
# 智能数据收集器环境变量自动配置脚本
# 根据测试场景自动选择最佳配置

detect_test_scale() {
    # 根据测试参数自动检测规模
    local num_instances="${1:-5}"
    local scale="small"
    
    if [ "$num_instances" -le 5 ]; then
        scale="small"
    elif [ "$num_instances" -le 20 ]; then
        scale="medium"
    elif [ "$num_instances" -le 100 ]; then
        scale="large"
    else
        scale="ultra"
    fi
    
    echo "$scale"
}

# 如果环境变量未设置，则设置智能默认值
if [ -z "$USE_SMART_COLLECTOR" ]; then
    export USE_SMART_COLLECTOR="true"
    
    # 检测测试规模
    if [ -n "$NUM_INSTANCES" ]; then
        detected_scale=$(detect_test_scale "$NUM_INSTANCES")
    elif [ -n "$CUSTOM_INSTANCES" ]; then
        # 从自定义实例参数提取数量
        if [[ "$CUSTOM_INSTANCES" =~ ^([0-9]+) ]]; then
            num="${BASH_REMATCH[1]}"
            detected_scale=$(detect_test_scale "$num")
        else
            detected_scale="small"
        fi
    else
        detected_scale="small"
    fi
    
    # 如果COLLECTOR_SCALE未设置，使用检测到的规模
    if [ -z "$COLLECTOR_SCALE" ]; then
        export COLLECTOR_SCALE="$detected_scale"
    fi
    
    # 如果NUM_TESTS未设置，根据规模设置
    if [ -z "$NUM_TESTS" ]; then
        case "$COLLECTOR_SCALE" in
            small)
                export NUM_TESTS="5"
                ;;
            medium)
                export NUM_TESTS="20"
                ;;
            large)
                export NUM_TESTS="100"
                ;;
            ultra)
                export NUM_TESTS="200"
                ;;
            *)
                export NUM_TESTS="5"
                ;;
        esac
    fi
    
    # 存储格式默认使用JSON
    if [ -z "$STORAGE_FORMAT" ]; then
        export STORAGE_FORMAT="json"
    fi
    
    # 静默模式标志（避免重复输出）
    if [ "$1" != "--quiet" ]; then
        echo "🔧 智能数据收集器自动配置:"
        echo "   USE_SMART_COLLECTOR: $USE_SMART_COLLECTOR"
        echo "   COLLECTOR_SCALE: $COLLECTOR_SCALE"
        echo "   NUM_TESTS: $NUM_TESTS"
        echo "   STORAGE_FORMAT: $STORAGE_FORMAT"
    fi
fi

# 返回成功
return 0 2>/dev/null || exit 0