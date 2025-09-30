
#!/bin/bash

# --- 1. 配置模型和路径 ---

export MPLBACKEND='agg'

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

VENV_GPTS="/venv_gpts"
VENV_OLLAMA="/venv_ollama"

echo "🛠️ 正在修复 GPT-SoVITS 模块导入路径 (PYTHONPATH)..."
export PYTHONPATH="/app:/app/GPT-SoVITS:/app/GPT-SoVITS/GPT_SoVITS:/app/GPT-SoVITS/GPT_SOVITS/module:/app/GPT-SoVITS/GPT_SOVITS/eres2net:$PYTHONPATH"

# --- 1. SSH服务和清理 ---
echo "🚀 启动 SSH 服务..."
/usr/sbin/sshd -D &

echo "🧹 正在清理可能残留的旧服务器进程 (端口 9880)..."
fuser -k 9880/tcp || true
sleep 1

# --- 2. 核心：检查并安装 Python 虚拟环境 ---
if [ ! -d "${VENV_GPTS}" ]; then
    echo "📦 正在安装 GPT-SoVITS Python 虚拟环境..."
    python3 -m venv ${VENV_GPTS}
    ${VENV_GPTS}/bin/python3 -m pip install --upgrade pip
    # 从 PyTorch 官方源在线安装，指定 CUDA 12.1 版本
    ${VENV_GPTS}/bin/python3 -m pip install torch==2.1.0 torchvision==0.17.2 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu121
    # 继续安装其他依赖
    ${VENV_GPTS}/bin/python3 -m pip install --no-cache-dir -r requirements_gpts.txt
fi

if [ ! -d "${VENV_OLLAMA}" ]; then
    echo "📦 正在安装 Ollama/API Python 虚拟环境..."
    python3 -m venv ${VENV_OLLAMA}
    ${VENV_OLLAMA}/bin/python3 -m pip install --upgrade pip
    # 从 PyTorch 官方源在线安装，指定 CUDA 12.1 版本
    ${VENV_GPTS}/bin/python3 -m pip install torch==2.1.0 torchvision==0.17.2 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu121
    # 继续安装其他依赖
    ${VENV_OLLAMA}/bin/python3 -m pip install --no-cache-dir -r requirements_ollama.txt
fi

FASTLANG_CACHE_PATH="/app/GPT-SoVITS/GPT_SoVITS/pretrained_models/fast_langdetect"
echo "📂 正在确保 fast_langdetect 缓存路径存在: ${FASTLANG_CACHE_PATH}"
mkdir -p "${FASTLANG_CACHE_PATH}"

echo "⚙️ 正在执行 API 修复补丁 (patch_api.py)..."
/venv_gpts/bin/python3 /app/patch_api.py

# --- 3. 启动服务 ---
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

    # ✅ 新增：强制 Ollama 使用 GPU
    export LD_LIBRARY_PATH="/usr/local/nvidia/lib64:/usr/local/cuda/lib64:/usr/local/lib:/usr/lib/x86_64-linux-gnu:${PYTHONPATH}:${LD_LIBRARY_PATH}"
    /usr/local/bin/ollama serve & 
    echo "⏱️ 等待 Ollama 服务启动..."
    sleep 20

    OLLAMA_MODEL_ID="llama3:latest"
    OLLAMA_EMBED_MODEL="bge-m3:latest"

    echo "⬇️ 检查并拉取 Ollama 模型: ${OLLAMA_MODEL_ID}..."
    if ! /usr/local/bin/ollama list | grep -q "${OLLAMA_MODEL_ID}"; then
        /usr/local/bin/ollama pull "${OLLAMA_MODEL_ID}" &> /dev/null
    fi

    echo "⬇️ 检查并拉取 Ollama 嵌入模型: ${OLLAMA_EMBED_MODEL}..."
    if ! /usr/local/bin/ollama list | grep -q "${OLLAMA_EMBED_MODEL}"; then
        /usr/local/bin/ollama pull "${OLLAMA_EMBED_MODEL}" &> /dev/null
        echo "🔥 正在预热 ${OLLAMA_EMBED_MODEL}..."
        /usr/local/bin/ollama run "${OLLAMA_EMBED_MODEL}" "预热" &> /dev/null
    fi

    source ${VENV_OLLAMA}/bin/activate
    echo "🚀 启动主程序 server.py (LLM/API 逻辑)..."
    ${VENV_OLLAMA}/bin/python3 /app/server.py &
    deactivate
    echo "✅ Ollama 服务和模型和server.py的执行已准备完毕."
else
    echo "⚠️ Ollama 和 LLM/RAG API 启动跳过 (非远程环境)."
fi

# --- 4. 保持容器持续运行 ---
echo "✅ 所有服务启动完毕，保持容器运行..."
tail -f /dev/null
