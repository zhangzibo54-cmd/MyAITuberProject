# 文件: /app/server.py
# 核心功能: 启动 FastAPI API，初始化 Ollama LLM 和 BGE-M3 嵌入模型。

import os
import sys
import logging
from typing import Optional

# 确保导入了正确的 LlamaIndex 模块
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama as OllamaLLM
from llama_index.core.settings import Settings 

# 假设您已安装 FastAPI
from fastapi import FastAPI, HTTPException

# ----------------------------------------------------
# 1. 配置日志系统
# ----------------------------------------------------
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# ----------------------------------------------------
# 2. 核心初始化函数 (在 FastAPI 启动前运行)
# ----------------------------------------------------
def initialize_rag_components():
    """
    初始化 Ollama 客户端、嵌入模型等 RAG 核心组件。
    此函数将在 FastAPI 应用程序启动时自动调用 (on_startup)。
    """
    
    # 假设 Ollama 服务运行在容器内部的默认端口
    OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_EMBED_MODEL = "bge-m3"  # 确保 start.sh 已经 pull 并预热了这个模型
    OLLAMA_LLM_MODEL = "llama3"    # 确保 start.sh 已经 pull 了这个模型

    # --- 1. 配置 Ollama 嵌入模型 (BGE-M3) ---
    try:
        logger.info(f"✅ 尝试配置 Ollama 嵌入模型: {OLLAMA_EMBED_MODEL}...")
        
        # 使用 OllamaEmbedding 类，通过 Ollama API 调用 BGE-M3
        embed_model = OllamaEmbedding(
            model_name=OLLAMA_EMBED_MODEL,
            base_url=OLLAMA_URL,
        )
        # 将 BGE-M3 设置为 LlamaIndex 的默认嵌入模型
        Settings.embed_model = embed_model
        logger.info("✅ BGE-M3 嵌入模型已通过 Ollama API 配置成功。")
        
    except Exception as e:
        logger.error(f"❌ Ollama 嵌入模型配置失败: {e}")
        logger.error("请确认 1. Ollama 服务已启动; 2. bge-m3 模型已被拉取/预热。")
        # 如果嵌入模型配置失败，RAG 无法进行，故终止程序
        sys.exit(1)
        
    # --- 2. 配置 Ollama LLM 客户端 ---
    try:
        logger.info(f"🔗 配置 Ollama LLM 客户端 ({OLLAMA_LLM_MODEL})...")
        llm_client = OllamaLLM(model=OLLAMA_LLM_MODEL, base_url=OLLAMA_URL)
        
        # 将 Ollama LLM 设置为 LlamaIndex 的默认 LLM
        Settings.llm = llm_client
        logger.info(f"🔗 Ollama LLM ({OLLAMA_LLM_MODEL}) 客户端配置成功。")
        
    except Exception as e:
        # LLM 客户端配置失败，虽然 RAG 会受影响，但我们暂不终止服务
        logger.error(f"❌ Ollama LLM 客户端配置失败: {e}")
        
    # --- 3. 核心 RAG 索引加载 (留空待填充) ---
    # 这里应该加载您的向量索引 (VectorStoreIndex)
    logger.info("🚧 RAG 核心索引加载逻辑待填充。")
    
    logger.info("🎉 RAG 核心组件初始化完成。")

# ----------------------------------------------------
# 3. FastAPI 应用程序启动
# ----------------------------------------------------

# 使用 on_startup 钩子，确保 initialize_rag_components 在服务启动前运行
app = FastAPI(
    on_startup=[initialize_rag_components],
    title="GPT-SoVITS & Ollama RAG Gateway"
) 

@app.get("/")
def read_root():
    """基础健康检查"""
    return {
        "status": "RAG API running", 
        "llm_configured": Settings.llm is not None,
        "embed_model_configured": Settings.embed_model is not None
    }

# 示例: 待填充的查询路由
@app.post("/query")
def query_rag_endpoint(query_text: str):
    """处理用户的 RAG 查询请求。"""
    
    if Settings.llm is None:
         raise HTTPException(status_code=503, detail="LLM 服务尚未就绪或配置失败。")
         
    # 🚧 待填充: 在这里调用 index.as_query_engine().query(query_text)
    
    return {"query": query_text, "response": "RAG 逻辑待实现。"}


# ----------------------------------------------------
# 4. Uvicorn 运行 (通常由 start.sh 脚本调用)
# ----------------------------------------------------
# 注意：在您的 start.sh 中，您是直接调用 python3 /app/server.py &
# 确保您的启动命令是正确的，例如：
# /venv_ollama/bin/uvicorn server:app --host 0.0.0.0 --port 8888
# 如果直接运行 python3 /app/server.py，则需要在脚本末尾添加 uvicorn 启动逻辑