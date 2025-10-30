#!/bin/bash

# 这个脚本被设计为每分钟运行一次，但实际会执行3次（每次间隔20秒）

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 执行指标收集任务
./metrics_cron.sh