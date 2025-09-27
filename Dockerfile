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
    && rm -rf /var/lib/apt/lists/*



# 3. 安装Ollama
# 这会把Ollama安装到容器里
COPY install_ollama.sh .
RUN chmod +x install_ollama.sh && ./install_ollama.sh && rm install_ollama.sh

# --- 【核心修改】 ---
# 4. 【新】直接从本地项目文件夹复制预先下载好的Ollama模型
#    这将取代原来耗时的 RUN ollama pull 命令
COPY ollama_models /root/.ollama/models/
# --- 修改结束 ---
# 你也可以在这里用Python脚本下载Whisper和GPT-SoVITS的模型

# 确保 python3 拥有 pip 模块
RUN apt-get update && apt-get install -y \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*
# 5. 安装所有Python依赖
# 先只复制requirements.txt文件，可以利用Docker的缓存机制
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# 6. 修复 SSHD 配置 (解决 PTY/TCP 转发错误)
RUN apt-get update && apt-get install -y openssh-server && \
    rm -rf /var/lib/apt/lists/*

    # 假设你的公钥文件就在本地，名为 id_ed25519.pub
    #  将你的公钥文件（id_ed25519.pub）复制到容器中
COPY id_ed25519.pub /root/.ssh/authorized_keys

RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh && \
    chmod 600 /root/.ssh/authorized_keys && \
    mkdir /var/run/sshd && \
    echo 'PermitRootLogin prohibit-password' >> /etc/ssh/sshd_config







# 7. 暴露您服务器程序需要用到的端口
EXPOSE 8888 22


# 8. 复制您自己的所有项目代码到容器中放在最下方目录不然会影响缓存
# 这样可以最大化利用Docker的缓存机制，只要文件有变化copy..就不会利用缓存
#只要有一行不利用缓存，接下来的就都不会利用缓存，尽量把耗时的变动少的放前面
#避免每次代码变动都

# 9. 定义容器启动时默认执行的命令

COPY start.sh /start.sh
RUN chmod +x /start.sh
# 10. 克隆或复制其他项目代码，如下载GPT-SoVITS
# 如果您的GPT-SoVITS代码在本地，就用COPY。如果是从GitHub拉取，就用RUN git clone
# RUN git clone https://github.com/RVC-Boss/GPT-SoVITS.git ./GPT-SoVITS
# 将启动脚本复制到容器中

COPY . . 

# 例如，启动您的WebSocket服务器
CMD ["/start.sh"]