# 1. 选择一个包含CUDA和PyTorch的基础镜像
# FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime AS builder
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04 AS builder
# 2. 设置工作目录并安装基础工具
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
# --- 第三阶段：安装系统依赖和核心工具 ---
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ffmpeg \
    build-essential \
    cmake \
    openssh-server \
    python3-pip \
    python3-venv \
    psmisc \
    pciutils \
    && rm -rf /var/lib/apt/lists/*



# 8. 复制项目代码和启动脚本
# 以下文件全在start_configure
# 复制依赖文件
# 复制我们刚刚创建的补丁脚本
# 创建一个补丁脚本 patch_api.py 来修复 api.py 中的导入

COPY start_configure/ ./start_configure/
# 6. 修复 SSHD 配置
# 确保 id_ed25519.pub 在本地项目目录中
COPY start_configure/id_ed25519.pub /root/.ssh/authorized_keys

RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    chmod 600 /root/.ssh/authorized_keys && \
    mkdir /var/run/sshd && \
    echo 'PermitRootLogin prohibit-password' >> /etc/ssh/sshd_config



COPY . . 



RUN chmod +x start_configure/start.sh
# ----------------------------------------------------------------------
# 【新增阶段】: 从官方最新镜像中获取最新的 Ollama 二进制文件
# ----------------------------------------------------------------------
FROM ollama/ollama:latest AS ollama_source
# 这一行就是保证我们能拿到最新版 /usr/bin/ollama 程序的关键

# ----------------------------------------------------------------------
# 阶段 2: 最终应用镜像 (将 Ollama 程序复制过来)
# ----------------------------------------------------------------------
FROM builder AS final_stage

# 关键修正：将最新的 Ollama 程序复制到你的最终镜像中
# /usr/bin/ollama 是程序本体。这会覆盖你旧镜像中的 /usr/local/bin/ollama。
COPY --from=ollama_source /usr/bin/ollama /usr/local/bin/ollama

# 7. 暴露端口 (放在最终阶段)
EXPOSE 8888 22 9880 11434 
# 添加 GPT-SoVITS 和 Ollama 的端口

# 9. 定义容器启动时默认执行的命令 (启动 start.sh)
CMD ["/bin/bash","start_configure/start.sh"]