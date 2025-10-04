# 文件: /app/server.py
# 核心功能: 启动 FastAPI API，初始化 Ollama LLM 和 BGE-M3 嵌入模型。

import os
import sys
import logging
from typing import Optional

import asyncio
import json
import wave
from io import BytesIO
from dataclasses import dataclass, field
from typing import List


# 确保导入了正确的 LlamaIndex 模块
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama as OllamaLLM
from llama_index.core.settings import Settings 

import asyncio
import json
import wave
from io import BytesIO
from dataclasses import dataclass, field
from typing import List

# 假设您已安装 FastAPI
from fastapi import FastAPI,HTTPException ,WebSocket, WebSocketDisconnect

import numpy as np
import librosa
from faster_whisper import WhisperModel


from AIclass.aituber import AItuber
from AIclass.events_class.perception_events import PerceptionEvent
from AIclass.events_class.utterance import UtteranceChunk
from AIclass.sub_engines.perception_engine import PerceptionEngine as PEG

# ----------------------------------------------------
# 1. 配置日志系统
# ----------------------------------------------------
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

asr_model = None # <<<< 新增：全局变量用于持有ASR模型
# ----------------------------------------------------
# 2. 核心初始化函数 (在 FastAPI 启动前运行)
# ----------------------------------------------------
asr_model = None

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

    # --- 4. 新增：初始化 ASR 模型 ---
    try:
        model_size = "large-v3"
        logger.info(f"✅ 正在加载 ASR 模型 (faster-whisper: {model_size})...")
        # 使用全局变量
        global asr_model
        asr_model = WhisperModel(model_size, device="cuda", compute_type="float16")
        logger.info(f"✅ ASR 模型 ({model_size}) 加载成功并已准备就绪。")
    except Exception as e:
        logger.error(f"❌ ASR 模型加载失败: {e}")
        logger.error("请确保 faster-whisper 和相关依赖已正确安装在 venv_ollama 环境中。")
        # ASR 对于此应用至关重要，如果加载失败则退出
        sys.exit(1)

# ----------------------------------------------------
# 3. FastAPI 应用程序启动
# ----------------------------------------------------

# 使用 on_startup 钩子，确保 initialize_rag_components 在服务启动前运行
app = FastAPI(
    on_startup=[initialize_rag_components],
    title="GPT-SoVITS, Ollama RAG Gateway and send-get text_audio"
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


@app.websocket("/ws/stream_utterances")
async def websocket_endpoint(websocket: WebSocket):
    #完成text_audio的传输
    await websocket.accept()
    client_host = websocket.client.host
    print(f"客户端 {client_host} 已连接。")

    # --- 为该客户端会话初始化资源 ---
    # 这个队列用于接收 AITuber 生成的要播放的语音
    output_utterance_queue = asyncio.Queue()
    # 这个队列用于存放识别出的文本，并传递给 AITuber
    perception_event_queue = asyncio.Queue()
    aituber_task = None
    audio_receiver_task = None
    try:
        aituber_task = asyncio.create_task(
                AItuber.main(text_audio_queue=output_utterance_queue,
                             asr_model = asr_model)
            )
        async def receive_audio_handler():
            try:
                while True:
                    # 等待并接收来自客户端的二进制数据
                    audio_bytes = await websocket.receive_bytes()
                    await  PEG.put_audio_queue(audio_data= audio_bytes)
                    print(f"服务器: 收到来自客户端的音频数据块，长度: {len(audio_bytes)}")
                    
                    # ----------------------------------------------------
                    # TODO: 之后在这里添加语音转文本的逻辑。
                    # ASR 处理后的文本，将通过 AITuber 内部的
                    # perception_event_queue 传递给 PerceptionEngine。
                    # ----------------------------------------------------
            except Exception as e:
                    # 当客户端断开时，这个接收循环会正常结束
                    print("音频接收任务停止。")
        audio_receiver_task = asyncio.create_task(receive_audio_handler())
            
        while True:
            chunk = await output_utterance_queue.get()
            if chunk is None:  # 假设 None 是结束信号
                break
            
            metadata = chunk.to_dict()
            await websocket.send_text(json.dumps(metadata))
            if chunk.audio_data:
                await websocket.send_bytes(chunk.audio_data)
    except KeyboardInterrupt:
        print("因为输入CTRL + C而终止了server.py")
    except WebSocketDisconnect:
        # 客户端断开连接时，会触发这个异常
        print("客户端断开，音频接收任务停止。")
    except  Exception as e:
        print(f"服务器传输数据给本地时发生错误：{e}")
    finally:
        if audio_receiver_task and not audio_receiver_task.done():
            audio_receiver_task.cancel()
        if aituber_task and not aituber_task.done():
            aituber_task.cancel()
        await asyncio.gather(aituber_task, audio_receiver_task, return_exceptions=True)

        logger.info(f"客户端的会话已完全结束。")


if __name__ =="__main__":
    import uvicorn
    # 运行服务器，监听所有网络接口(所有人都能请求)的 8888（访问地址porthttp://<服务器IP>:8000） 端口  
    uvicorn.run(app, host="0.0.0.0", port=8888)
  



# ----------------------------------------------------
# 4. Uvicorn 运行 (通常由 start.sh 脚本调用)
# ----------------------------------------------------
# 注意：在您的 start.sh 中，您是直接调用 python3 /app/server.py &
# 确保您的启动命令是正确的，例如：
# /venv_ollama/bin/uvicorn server:app --host 0.0.0.0 --port 8888
# 如果直接运行 python3 /app/server.py，则需要在脚本末尾添加 uvicorn 启动逻辑