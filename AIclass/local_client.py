# local_client.py (本地客户端)
import asyncio
import json
import base64
import numpy as np
import sounddevice as sd
from aiohttp import ClientSession
from AIclass.events_class.utterance import UtteranceChunk

# 服务器地址
SERVER_URL = "http://localhost:8080/api/generate_utterance"
SAMPLE_RATE = 32000 # 假设音频采样率和服务器端一致

# --- 辅助函数：反序列化 ---
def serializable_to_chunk(data: dict) -> UtteranceChunk:
    """将字典反序列化为 UtteranceChunk 对象。"""
    audio_data_b64 = data.get("audio_data_b64")
    # 将 base64 字符串解码回 bytes
    audio_data = base64.b64decode(audio_data_b64) if audio_data_b64 else b''
    
    return UtteranceChunk(
        text=data["text"],
        id=data["id"],
        audio_data=audio_data
    )

# --- 异步播放函数 ---
async def play_audio_chunk(chunk: UtteranceChunk):
    """
    异步播放单个 UtteranceChunk 的音频数据。
    使用 sounddevice 的非阻塞流播放。
    """
    print(f"本地: 正在播放片段: '{chunk.text}' (ID: {chunk.id[:4]}...)")
    if not chunk.audio_data:
        print("本地: 无音频数据，跳过播放。")
        return

    # 将 bytes 转换为 numpy 数组 (sounddevice 需要 numpy 格式)
    # 假设是 int16 格式 (16bit)
    audio_array = np.frombuffer(chunk.audio_data, dtype=np.int16)

    # 创建一个 Future，当播放完成时设置它
    done_future = asyncio.Future()
    
    def callback(outdata, frames, time, status):
        """sounddevice 播放完成后的回调函数。"""
        if status:
            print(status)
        if frames == 0:
            # 播放流结束
            if not done_future.done():
                done_future.set_result(True)

    # 使用 sd.RawOutputStream 播放，并在播放完成后设置 Future
    # blocksize=0 表示不阻塞，由 sounddevice 内部处理缓冲区
    stream = sd.RawOutputStream(
        samplerate=SAMPLE_RATE,
        channels=1, # 单声道
        dtype='int16',
        callback=callback,
        finished_callback=lambda: done_future.set_result(True)
    )

    with stream:
        # 写入数据并等待播放完成
        stream.write(chunk.audio_data) # 写入全部数据
        await done_future # 等待播放流结束
        
    print(f"本地: 片段播放完成: '{chunk.text[:5]}...'")


# --- 主控制协程 ---
async def main_playback_pipeline():
    """
    整个传输和播放流程的主协程。
    """
    print("本地: 启动 UtteranceChunk 传输与播放流程...")
    
    # 1. 异步获取数据
    async with ClientSession() as session:
        try:
            print("本地: 正在从服务器拉取数据...")
            async with session.get(SERVER_URL) as response:
                if response.status != 200:
                    print(f"本地: 错误：服务器返回状态码 {response.status}")
                    return

                raw_data = await response.json()
                print("本地: 数据拉取成功。")

        except Exception as e:
            print(f"本地: 网络请求失败: {e}")
            return

    # 2. 反序列化数据
    try:
        chunks: list[UtteranceChunk] = [serializable_to_chunk(d) for d in raw_data]
    except Exception as e:
        print(f"本地: 数据反序列化失败: {e}")
        return

    # 3. 顺序播放
    print(f"本地: 共收到 {len(chunks)} 个 UtteranceChunk。开始顺序播放...")
    for chunk in chunks:
        # await 确保一个 chunk 播放完毕后才开始下一个 chunk
        await play_audio_chunk(chunk)
        
    print("本地: 所有 UtteranceChunk 播放完毕。")


if __name__ == "__main__":
    # 记得先启动 remote_server.py
    print("请确保 remote_server.py 正在运行在 http://localhost:8080")
    try:
        asyncio.run(main_playback_pipeline())
    except KeyboardInterrupt:
        print("本地: 流程中断。")