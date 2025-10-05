
#!/bin/bash

# --- 1. 配置模型和路径 ---

export MPLBACKEND='agg'

SCRIPT_DIR=$(dirname "$0")
REQUIREMENTS_FILE_GPTS="${SCRIPT_DIR}/requirements_gpts.txt"
REQUIREMENTS_FILE_OLLAMA="${SCRIPT_DIR}/requirements_ollama.txt"
# 确保所有 GPT-SoVITS 子模块路径被识别
export PYTHONPATH="/app:/app/GPT-SoVITS:/app/GPT-SoVITS/GPT_SoVITS:/app/GPT-SoVITS/GPT_SOVITS/module:/app/GPT-SoVITS/GPT_SOVITS/eres2net:$PYTHONPATH"

XINGTONG_FOLDER="/app/XingTong"
PRETRAINED_FOLDER="/app/GPT-SoVITS/GPT_SoVITS/pretrained_models" 
API_PY_PATH="/app/GPT-SoVITS/api.py"

SOVITS_PATH="${XINGTONG_FOLDER}/sovits.pth"
GPT_PATH="${XINGTONG_FOLDER}/gpt.ckpt"
HUBERT_PATH="${PRETRAINED_FOLDER}/chinese-hubert-base"
BERT_PATH="${PRETRAINED_FOLDER}/chinese-roberta-wwm-ext-large"

DEFAULT_REF_WAV_PATH="${XINGTONG_FOLDER}/ref.wav"
DEFAULT_REF_TEXT="等你，我想想，嗯。"
DEFAULT_REF_LANG="zh"
GPT_SOVITS_PORT=9880
BIND_ADDRESS="0.0.0.0"

VENV_GPTS="/app/venv_gpts"
VENV_OLLAMA="/app/venv_ollama"

echo "🛠️ 正在修复 GPT-SoVITS 模块导入路径 (PYTHONPATH)..."
export PYTHONPATH="/app:/app/GPT-SoVITS:/app/GPT-SoVITS/GPT_SoVITS:/app/GPT-SoVITS/GPT_SOVITS/module:/app/GPT-SoVITS/GPT_SOVITS/eres2net:$PYTHONPATH"

# --- 1. SSH服务和清理 ---
echo "🚀 启动 SSH 服务..."
/usr/sbin/sshd -D &

echo "🧹 正在清理可能残留的旧服务器进程..."
fuser -k 9880/tcp || true
fuser -k 11434/tcp || true
fuser -k 8888/tcp || true
sleep 1

# --- 2. 核心：检查并安装 Python 虚拟环境 ---
if [ ! -d "${VENV_GPTS}" ]; then
    echo "📦 正在安装 GPT-SoVITS Python 虚拟环境..."
    python3 -m venv ${VENV_GPTS}
    ${VENV_GPTS}/bin/python3 -m pip install --upgrade pip
    # 从 PyTorch 官方源在线安装，指定 CUDA 12.1 版本
    # 【修改点】去掉版本号，让 pip 自动选择兼容版本
    ${VENV_GPTS}/bin/python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ${VENV_GPTS}/bin/python3 -m pip install --no-cache-dir -r "${REQUIREMENTS_FILE_GPTS}"
fi

if [ ! -d "${VENV_OLLAMA}" ]; then
    echo "📦 正在安装 Ollama/API Python 虚拟环境..."
    python3 -m venv ${VENV_OLLAMA}
    ${VENV_OLLAMA}/bin/python3 -m pip install --upgrade pip
    # 从 PyTorch 官方源在线安装，指定 CUDA 12.1 版本
    # 【修改点】去掉版本号，让 pip 自动选择兼容版本
    ${VENV_GPTS}/bin/python3 -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    # 继续安装其他依赖
    ${VENV_OLLAMA}/bin/python3 -m pip install --no-cache-dir -r "${REQUIREMENTS_FILE_OLLAMA}"
fi
# 添加缓存文件夹，一个GPTS的修复
FASTLANG_CACHE_PATH="/app/GPT-SoVITS/GPT_SoVITS/pretrained_models/fast_langdetect"
echo "📂 正在确保 fast_langdetect 缓存路径存在: ${FASTLANG_CACHE_PATH}"
mkdir -p "${FASTLANG_CACHE_PATH}"

echo "⚙️ 正在执行 API 修复补丁 (patch_api.py)..."
/venv_gpts/bin/python3 "${SCRIPT_DIR}/patch_api.py"

# --- 3. 启动服务 ---
echo "=== 正在检查 nvcc 是否安装,似乎没有必要，之前是为了whisper的修复才安装的，但实际问题是duicrtranslate的版本依赖==="
if command -v nvcc &> /dev/null
then
    echo "nvcc 已安装。跳过安装步骤。"
else
    echo "nvcc 未找到。开始安装 CUDA Toolkit..."
    
    # 检查并安装基本工具
    apt update
    apt install -y wget dpkg ca-certificates

    # --- 步骤 1: 添加 NVIDIA 仓库 ---
    echo "下载并安装 CUDA 密钥包..."
    if wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb -O /tmp/cuda-keyring.deb; then
        dpkg -i /tmp/cuda-keyring.deb
        rm /tmp/cuda-keyring.deb
    else
        echo "CUDA 密钥下载失败 (404 或其他错误)。请检查 URL。"
        exit 1
    fi

    # --- 步骤 2: 安装 CUDA Toolkit ---
    echo "更新 APT 列表并安装 cuda-toolkit..."
    apt update
    apt install -y cuda-toolkit
    
    # 确保 PATH 变量在当前会话中设置
    export PATH="/usr/local/cuda/bin:$PATH"
    
    echo "=== 安装完成 ==="
fi


echo "🌐 检查并下载 NLTK 语言数据包..."
source ${VENV_GPTS}/bin/activate
python3 -c "import nltk; nltk_packages = ['averaged_perceptron_tagger', 'punkt', 'cmudict', 'averaged_perceptron_tagger_eng']; [nltk.download(package, quiet=True) for package in nltk_packages]"
deactivate
echo "✅ NLTK数据包已准备就绪。"

echo "🚀 激活 GPT-SoVITS 环境并修复路径..."
source ${VENV_GPTS}/bin/activate
export PYTHONPATH="/app:/app/GPT-SoVITS:/app/GPT-SoVITS/GPT_SoVITS:/app/GPT-SoVITS/GPT_SOVITS/module:/app/GPT-SoVITS/GPT_SOVITS/eres2net:$PYTHONPATH"

if [ "$IS_REMOTE_SERVER" = "true" ]; then
    echo "🚀 检测到远程服务器环境。启动 GPT-SoVITS API 服务器..."
    (
    #防止找不到文件执行，其中（）代表内部执行命令，在执行结束后自动回到原文件夹
    source ${VENV_GPTS}/bin/activate
    export PYTHONPATH="/app:/app/GPT-SoVITS:/app/GPT-SoVITS/GPT_SoVITS:/app/GPT-SoVITS/GPT_SOVITS/module:/app/GPT-SoVITS/GPT_SOVITS/eres2net:$PYTHONPATH"
    cd /app/GPT-SoVITS
    ${VENV_GPTS}/bin/python3 "${API_PY_PATH}" \
        -s "${SOVITS_PATH}" \
        -g "${GPT_PATH}" \
        -hb "${HUBERT_PATH}" \
        -b "${BERT_PATH}" \
        -dr "${DEFAULT_REF_WAV_PATH}" \
        -dt "${DEFAULT_REF_TEXT}" \
        -dl "${DEFAULT_REF_LANG}" \
        -a "${BIND_ADDRESS}" \
        -p "${GPT_SOVITS_PORT}" \
        -d "cuda" &
    )
else
    echo "⚠️ 未检测到远程服务器标志。跳过启动 GPT-SoVITS API 服务器。"
fi

if [ "$IS_REMOTE_SERVER" = "true" ]; then
    echo "🚀 2/3: 启动 Ollama 服务和 LLM 模型..."

    echo "🔄 正在检查并安装/更新 Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
    # ✅ 新增：强制 Ollama 使用 GPU
    # 【关键修正】使用 find 命令找到的精确路径来设置环境变量，
    # 之前的路径不对这个我们通过查找 find / -name "libcublas.so*" 2>/dev/null找到的
    # 【最终修正版】根据系统真实文件结构定制的路径，
    #   实际上在采用上述安装ollama的方法后，不需要再设置这个路径了
    # export LD_LIBRARY_PATH="/usr/local/cuda-12.1/targets/x86_64-linux/lib:/usr/local/cuda-12.1/lib64:${LD_LIBRARY_PATH}"

    # 后台启动ollama服务 ---
    /usr/local/bin/ollama serve &

    echo "⏱️ 等待 Ollama 服务启动..."
    sleep 10

    OLLAMA_MODEL_ID="llama3:latest"
    OLLAMA_EMBED_MODEL="bge-m3:latest"

    echo "⬇️ 检查并拉取 Ollama 模型: ${OLLAMA_MODEL_ID}..."
    if ! /usr/local/bin/ollama list | grep -q "${OLLAMA_MODEL_ID}"; then
        /usr/local/bin/ollama pull "${OLLAMA_MODEL_ID}" &> /dev/null
        /usr/local/bin/ollama run "${OLLAMA_MODEL_ID}" "hello" &> /dev/null
    fi

    echo "⬇️ 检查并拉取 Ollama 嵌入模型: ${OLLAMA_EMBED_MODEL}..."
    if ! /usr/local/bin/ollama list | grep -q "${OLLAMA_EMBED_MODEL}"; then
        /usr/local/bin/ollama pull "${OLLAMA_EMBED_MODEL}" &> /dev/null
        echo "🔥 正在预热 ${OLLAMA_EMBED_MODEL}..."
        /usr/local/bin/ollama run "${OLLAMA_EMBED_MODEL}" "预热" &> /dev/null
    fi

    source ${VENV_OLLAMA}/bin/activate
    echo "🚀 启动主程序 server.py (LLM/API 逻辑)..."
    # 这里时用unicorn运行的所以需要相对路径而非绝对路径
    # MODULE_PATH="start_configure.server:app"
    # ${VENV_OLLAMA}/bin/uvicorn ${MODULE_PATH} --host 0.0.0.0 --port 8888 &

    ${VENV_OLLAMA}/bin/uvicorn server:app --host 0.0.0.0 --port 8888 &
    deactivate
    echo "✅ Ollama 服务和模型和server.py的执行已准备完毕."
else
    echo "⚠️ Ollama 和 LLM/RAG API 启动跳过 (非远程环境)."
fi

# --- 4. 保持容器持续运行 ---
echo "✅ 所有服务启动完毕，保持容器运行..."
tail -f /dev/null
