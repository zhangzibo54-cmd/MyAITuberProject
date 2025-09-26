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
    
RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd


# 3. 安装Ollama
# 这会把Ollama安装到容器里
RUN curl -fsSL https://ollama.com/install.sh | sh

# 4. 安装所有Python依赖
# 先只复制requirements.txt文件，可以利用Docker的缓存机制
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. 克隆或复制其他项目代码，如下载GPT-SoVITS
# 如果您的GPT-SoVITS代码在本地，就用COPY。如果是从GitHub拉取，就用RUN git clone
# RUN git clone https://github.com/RVC-Boss/GPT-SoVITS.git ./GPT-SoVITS
# 将启动脚本复制到容器中
COPY start.sh /start.sh
RUN chmod +x /start.sh

# 6. 复制您自己的所有项目代码到容器中
COPY . .

# 7. 【重要】提前下载AI模型
# 这一步会将模型文件直接打包进镜像，巨大地节省每次启动服务器的时间
# 注意：这会让你的Docker镜像变得很大！
# 启动ollama服务，拉取模型，然后关闭服务
RUN ollama serve & sleep 5 && \
    ollama pull llama3 && \
    ollama pull nomic-embed-text && \
    pkill ollama
# 你也可以在这里用Python脚本下载Whisper和GPT-SoVITS的模型

# 8. 暴露您服务器程序需要用到的端口
EXPOSE 8888
EXPOSE 22
# 9. 定义容器启动时默认执行的命令
# 例如，启动您的WebSocket服务器
CMD ["/start.sh"]