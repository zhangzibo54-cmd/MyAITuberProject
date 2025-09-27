#!/bin/bash

# 1. 启动 SSH 服务
/usr/sbin/sshd -D &


# 2. 运行你的 Python 脚本
python3 /app/server.py &

# 3. 保持容器持续运行
tail -f /dev/null