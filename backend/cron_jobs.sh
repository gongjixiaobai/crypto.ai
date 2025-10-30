#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 从.env文件加载环境变量
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# 设置服务器地址和端口
SERVER_URL="http://38.175.194.75:8000"

# 生成token（使用已有的CRON_SECRET_KEY），并清理可能的额外字符
TOKEN=$(echo "$CRON_SECRET_KEY" | sed 's/%0d$//' | sed 's/\r$//')

# 调用3分钟间隔的任务
curl -s -G "$SERVER_URL/api/cron/3-minutes-run-interval" --data-urlencode "token=$TOKEN" > /dev/null 2>&1

echo "$(date): Executed 3-minutes-run-interval cron job"