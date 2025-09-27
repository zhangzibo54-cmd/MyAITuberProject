#!/bin/bash

# --- 1. 配置模型和路径 ---

# 所有的项目文件（包括 GPT-SoVITS, XingTong, KusanagiNene 文件夹）
# 都通过 Dockerfile 中的 COPY . . 被复制到了 /app 目录。
export MPLBACKEND='agg' # 避免 matplotlib 启动图形界面

XINGTONG_FOLDER="/app/XingTong"
PRETRAINED_FOLDER="/app/GPT-SoVITS/pretrained_models"
API_PY_PATH="/app/GPT-SoVITS/api.py"

# 模型文件路径
SOVITS_PATH="${XINGTONG_FOLDER}/sovits.pth"
GPT_PATH="${XINGTONG_FOLDER}/gpt.ckpt"
HUBERT_PATH="${PRETRAINED_FOLDER}/chinese-hubert-base"
BERT_PATH="${PRETRAINED_FOLDER}/chinese-roberta-wwm-ext-large"

# 默认参考音频（假设您已将参考音频文件复制到了 /app/reference_audio/default.wav）
DEFAULT_REF_WAV_PATH="/app/reference_audio/default.wav"
DEFAULT_REF_TEXT="你好，这是一个默认参考文本"
DEFAULT_REF_LANG="zh"
GPT_SOVITS_PORT=9880
BIND_ADDRESS="0.0.0.0"


# --- 2. 预启动和清理 ---

# 确保 fast_langdetect 缓存路径存在（解决 Colab 中遇到的缓存问题）
FASTLANG_CACHE_PATH="/app/GPT-SoVITS/GPT_SoVITS/pretrained_models/fast_langdetect"
echo "📂 正在确保 fast_langdetect 缓存路径存在: ${FASTLANG_CACHE_PATH}"
mkdir -p "${FASTLANG_CACHE_PATH}"


# --- 3. 启动服务 ---

# 3.1 启动 SSH 服务

# 3.2 运行你的主 Python 脚本 (使用 /venv_ollama 环境)
echo "🚀 启动主程序 server.py (LLM/API 逻辑)..."
/venv_ollama/bin/python3 /app/server.py &

# 3.3 关键：GPT-SoVITS API 服务的条件启动
if [ "$IS_REMOTE_SERVER" = "true" ]; then
    echo "🚀 检测到远程服务器环境。启动 GPT-SoVITS API 服务器..."
    /venv_gpts/bin/python3 "${API_PY_PATH}" \
        -s "${SOVITS_PATH}" \
        -g "${GPT_PATH}" \
        -dr "${DEFAULT_REF_WAV_PATH}" \
        -dt "${DEFAULT_REF_TEXT}" \
        -dl "${DEFAULT_REF_LANG}" \
        -a "${BIND_ADDRESS}" \
        -p "${GPT_SOVITS_PORT}" \
        -d "cuda" &
else
    echo "⚠️ 未检测到远程服务器标志。跳过启动 GPT-SoVITS API 服务器。"
fi


# --- 4. 保持容器持续运行 ---
echo "✅ 所有服务启动完毕，保持容器运行..."
tail -f /dev/null