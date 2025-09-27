# 1. 选择一个包含CUDA和PyTorch的基础镜像
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

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
    && rm -rf /var/lib/apt/lists/*

# 3. 安装Ollama (通过本地脚本，优化缓存)
COPY install_ollama.sh .
RUN chmod +x install_ollama.sh && ./install_ollama.sh && rm install_ollama.sh

# 4. 复制预先下载好的Ollama模型 (利用缓存)
COPY ollama_models /root/.ollama/models/

# --- 5. 核心：创建并安装隔离的 Python 虚拟环境 ---

# 复制依赖文件
COPY requirements_gpts.txt .
COPY requirements_ollama.txt .

# A. 创建 GPT-SoVITS 依赖环境 (numpy < 2.0)
RUN python3 -m venv /venv_gpts && \
    /venv_gpts/bin/python3 -m pip install --upgrade pip && \
    # 安装 PyTorch 及其相关库（必须从官方源安装以获取 GPU 支持）
    /venv_gpts/bin/python3 -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    /venv_gpts/bin/python3 -m pip install --no-cache-dir -r requirements_gpts.txt && \
    rm requirements_gpts.txt

# B. 创建 Ollama/API 依赖环境 (pydantic 2.x, 兼容 numpy 2.x)
RUN python3 -m venv /venv_ollama && \
    /venv_ollama/bin/python3 -m pip install --upgrade pip && \
    # 安装 PyTorch 及其相关库
    /venv_ollama/bin/python3 -m pip install torch torchaudio torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    /venv_ollama/bin/python3 -m pip install --no-cache-dir -r requirements_ollama.txt && \
    rm requirements_ollama.txt

# 6. 修复 SSHD 配置
# 确保 id_ed25519.pub 在本地项目目录中
COPY id_ed25519.pub /root/.ssh/authorized_keys

RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    chmod 600 /root/.ssh/authorized_keys && \
    mkdir /var/run/sshd && \
    echo 'PermitRootLogin prohibit-password' >> /etc/ssh/sshd_config

# 7. 暴露您服务器程序需要用到的端口
EXPOSE 8888 22

# 8. 复制项目代码和启动脚本
# 注意：这行 COPY . . 已经将本地的 GPT-SoVITS 目录复制进来，无需 git clone
COPY start.sh /start.sh
RUN chmod +x /start.sh

COPY . . 

# 9. 定义容器启动时默认执行的命令 (启动 start.sh)
CMD ["/start.sh"]