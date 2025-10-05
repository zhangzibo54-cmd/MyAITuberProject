import websocket
import json
import pygame
import io
import sys

import pyaudio  # <--- 新增
import threading # <--- 新增
import time      # <--- 新增
import torch
import wave
import numpy as np # <--- 新增导入 numpy
import os
import requests


# --- 配置 ---
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False)

(get_speech_timestamps,
 save_audio,
 read_audio,
 VADIterator,
 collect_chunks) = utils

vad_iterator = VADIterator(
    model,
    threshold=0.3,                # 语音活动检测的灵敏度，0.5是默认值，可以根据噪音情况微调
    min_silence_duration_ms= 1200,  # <--- 关键改动：最小静音时长（毫秒）
    speech_pad_ms= 200             # 在检测到的语音前后各增加一点填充，防止切掉首尾的音
)


# --- 音频配置 ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # VAD 和 Whisper 都推荐使用 16kHz
CHUNK_SIZE = 512 # 每次读取的块大小

# 将 "localhost" 替换为你的服务器的 IP 地址或域名
#####📕#####

def get_runpod_pod_details(pod_id: str, api_key: str) -> dict | None:
    """
    使用 RunPod API 获取指定 Pod 的详细信息。

    Args:
        pod_id (str): 你要查询的 RunPod Pod 的唯一 ID。
        api_key (str): 你的 RunPod API 密钥。

    Returns:
        dict | None: 如果请求成功，返回包含 Pod 详细信息的字典。
                      如果失败，返回 None。
    """
    if not pod_id or not api_key:
        print("错误: Pod ID 和 API Key 不能为空。")
        return None

    # 1. 构造完整的 API URL
    url = f"https://api.runpod.io/v2/pods/{pod_id}"

    # 2. 构造请求头，按官方要求格式传入 API Key
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    print(f"正在向 API 发送请求: GET {url}")

    try:
        # 3. 发送 GET 请求
        response = requests.get(url, headers=headers)

        # 4. 检查请求是否成功 (例如 401 未授权, 404 找不到)
        response.raise_for_status()  # 如果状态码是 4xx 或 5xx, 会抛出异常

        # 5. 解析返回的 JSON 数据并返回
        pod_details = response.json()
        return pod_details

    except requests.exceptions.HTTPError as err:
        print(f"HTTP 请求错误: {err}")
        print(f"响应内容: {response.text}")
    except requests.exceptions.RequestException as err:
        print(f"网络或请求发生错误: {err}")
    
    return None

def find_tcp_mapping_from_api(pod_details: dict, internal_port: int) -> tuple | None:
    """
    从 API 返回的 Pod 详情中，解析出某个内部TCP端口对应的【公网IP】和【公网端口】。

    Args:
        pod_details (dict): 从 get_runpod_pod_details 获取到的完整信息。
        internal_port (int): 你要查找的容器内部端口号。

    Returns:
        tuple | None: 如果找到，返回一个包含 (公网IP, 公网端口) 的元组，例如 ("194.68.245.179", 22139)。
                      如果找不到，返回 None。
    """
    if not pod_details:
        return None
        
    ports_list = pod_details.get("runtime", {}).get("ports", [])
    
    for port_info in ports_list:
        # 匹配内部端口号，并且确保映射类型是 tcp
        if port_info.get("privatePort") == internal_port and port_info.get("type") == "tcp":
            public_ip = port_info.get("ip")
            public_port = port_info.get("publicPort")
            return public_ip, public_port
            
    return None

# pod_id = "3jknn3rd4y1vdm"
# api_key = "rpa_47B0MC40E736K0F7NTBGUSRNFRJSMH6T8AM9UOTTbafjuq"
# pod_details = get_runpod_pod_details(pod_id = pod_id,api_key =  api_key)
# public_ip , public_port = find_tcp_mapping_from_api(pod_details,8888) 
# server_url_path = "/ws/stream_utterances"
# SERVER_URL = f"ws://{public_ip}:{public_port}{server_url_path}"

SERVER_URL = "ws://194.68.245.179:22042/ws/stream_utterances" # for test
print(f"现在服务器地址是：{SERVER_URL}")
#####📕#####

# --- 新增：用于线程同步的状态标志 ---
# 这个事件对象将在AI播放音频时被设置 (set)，播放结束后被清除 (clear)
is_playing_event = threading.Event()


# --- 新的、基于 VAD 的音频处理线程 ---
def speech_to_server_thread(ws):
    """
    在一个独立线程中运行，使用 VAD 检测语音，并将完整的句子发送到服务器。
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK_SIZE)
    
    print("\n🎤 语音检测已启动，请开始说话...")
    
    speech_buffer = [] # <--- 关键改动 1: 创建一个列表来手动缓存一句话的音频
    is_speaking = False
    sentence_audio = b'' # <--- 关键修正 1: 初始化变量，确保它始终存在
    start_time = 0 
    MIN_SENTENCE_DURATION_S = 2

    # ### <<< 新增: 状态变量，用于检测是否刚从暂停状态恢复 >>>
    was_paused = False

    try:
        while getattr(ws, 'keep_running', True):

            # ### <<< 修改: 核心逻辑 - 检查是否正在播放音频 >>>
            if is_playing_event.is_set():
                # 如果AI正在说话，我们就在这里等待
                if not was_paused:
                    print("\n🎤 录音已暂停...")
                    was_paused = True
                time.sleep(0.1) # 短暂休眠以降低CPU占用
                continue # 跳过本次循环的录音部分

            # 如果刚从暂停状态恢复
            if was_paused:
                print("\n🎤 录音已恢复，请说话...")
                vad_iterator.reset_states()  # 重置VAD状态，防止误判
                is_speaking = False # 确保说话状态也被重置
                speech_buffer.clear()
                was_paused = False
            # ### <<< 修改结束 >>>

            # 持续从麦克风读取音频数据
            audio_chunk_bytes = stream.read(CHUNK_SIZE)

            # --- 关键修正：将 bytes 转换为 PyTorch Tensor ---
            # 首先，将字节转换为 numpy 数组 (16-bit 整数)
            audio_np = np.frombuffer(audio_chunk_bytes, dtype=np.int16)
            # 然后，将 numpy 数组转换为 PyTorch 张量 (浮点数)
            audio_tensor = torch.from_numpy(audio_np)
            # --- 修正结束 ---
            
            # 将音频块喂给 VAD 迭代器

            speech_dict = vad_iterator(audio_tensor, return_seconds=True)

            if speech_dict:
                if "start" in speech_dict:
                    # VAD 检测到语音开始
                    is_speaking = True
                    speech_buffer.clear()
                    start_time = speech_dict['start'] 
                    print("检测到语音开始...", end="", flush=True)


                if is_speaking:
                    # 只要正在说话，就将音频块添加到缓冲区
                    speech_buffer.append(audio_chunk_bytes)
                # VAD 检测到一句话的结尾
                if "end" in speech_dict and is_speaking:
                    # VAD 检测到刚语音结束
                    is_speaking = False

                    duration = speech_dict['end'] - start_time
                    # --- 关键改动 2: 增加时长判断 ---
                    if duration < MIN_SENTENCE_DURATION_S:
                        # 时长太短，我们认为是噪音，直接忽略
                        print(f" ⚠️结束 (时长: {duration:.2f}s)，但因太短而被忽略。")
                        speech_buffer.clear() # 必须清空，否则会被累积
                        is_speaking = False
                        continue # 直接进入下一次循环，不发送
                    # --- 改动结束 ---
                    print(f"✅ 结束 (时长: {duration:.2f}s)。正在打包并发送...")
                   

                    # --- 关键改动 2: 拼接手动缓存的音频 ---
                    # 拼接列表中的所有音频块
                    sentence_audio = b''.join(speech_buffer)
                    # 清空缓冲区，为下一句话做准备
                    speech_buffer.clear()
                    # --- 改动结束 ---
                
                    # 将原始的 pcm 音频数据打包成 wav 格式的 bytes
                    with io.BytesIO() as wav_buffer:
                        with wave.open(wav_buffer, 'wb') as wf:
                            wf.setnchannels(CHANNELS)
                            wf.setsampwidth(p.get_sample_size(FORMAT))
                            wf.setframerate(RATE)
                            wf.writeframes(sentence_audio)
                        wav_data_to_send = wav_buffer.getvalue()

                    # 将这一整句话的 WAV 数据作为一条二进制消息发送
                    ws.send(wav_data_to_send, opcode=websocket.ABNF.OPCODE_BINARY)
                    print("✅ 已发送一句话的音频到服务器！等待下一句...")

            else:
                # VAD 没有检测到语音
                if is_speaking:
                    # 如果之前在说话，但现在突然没声音了（比如短暂的停顿），
                    # 我们也继续缓存一小会儿，VAD 会在确认静音后发出 "end"
                    speech_buffer.append(audio_chunk_bytes)

    except Exception as e:
        print(f"语音处理线程出错: {e}")
    finally:
        print("🎤 语音处理线程已停止。")
        vad_iterator.reset_states() # 重置 VAD 状态
        if 'stream' in locals() and stream.is_active():
            stream.stop_stream()
            stream.close()
        p.terminate()


# --- 简化后的 speech_to_server_thread 核心逻辑 ---
def speech_to_server_thread_common(ws):
    """
    在一个独立线程中运行，持续从麦克风读取音频流，并以小块形式发送给服务器。
    """
    p = pyaudio.PyAudio()
    # ... (pyaudio stream 初始化保持不变)
    stream = p.open(...)
    
    print("\n🎤 持续音频流上传已启动...")
    
    try:
        while getattr(ws, 'keep_running', True):
            # 持续从麦克风读取音频数据
            audio_chunk_bytes = stream.read(CHUNK_SIZE)
            
            # 直接发送原始的 PCM 音频数据块
            # 注意：这里我们不再进行 VAD 处理，也不再缓存并拼接 WAV 文件。
            # 我们直接发送原始 PCM 数据，或者如果服务器要求 WAV，则发送小块 WAV。

            # 推荐：直接发送原始 PCM 数据（更轻量）
            ws.send(audio_chunk_bytes, opcode=websocket.ABNF.OPCODE_BINARY)

    except Exception as e:
        print(f"音频流上传线程出错: {e}")
    finally:
        # ... (资源清理保持不变)
        pass # VAD 相关的清理可以移除


def run_client():
    """连接到 WebSocket 服务器并处理传入的音频流。"""
    # 初始化 Pygame Mixer
    pygame.mixer.init(frequency=24000) # 使用与服务器端相同的采样率

    # 创建一个 WebSocket 连接
    ws = websocket.WebSocketApp(SERVER_URL,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    print("正在连接到服务器...")
    try:
        # 启动 WebSocket 的永久运行循环
        # 增加 ping_interval 和 ping_timeout 参数
        ws.run_forever(ping_interval=10, ping_timeout=1000)
    except KeyboardInterrupt:
        # 当用户按下 Ctrl+C 时，会触发这个异常
        print("\n捕获到退出信号 (Ctrl+C)... 正在优雅地关闭...")
        
        # 1. 首先，关闭 WebSocket 连接
        #    这会触发 on_close 回调函数  
        ws.close()
        
        # 2. 然后，退出 pygame 子系统
        pygame.quit()
        
        # 3. 最后，退出程序
        print("客户端已退出。")
        sys.exit(0)

# --- 修改 on_open 回调函数 ---
def on_open(ws):
    """
    当 WebSocket 连接成功建立时调用。
    """
    print("已成功连接到服务器！")
    # 创建并启动一个新线程来处理语音检测和上传
    threading.Thread(target=speech_to_server_thread, args=(ws,), daemon=True).start()



def on_error(ws, error):
    if isinstance(error, websocket.WebSocketConnectionClosedException):
        pass
    else:
        print(f"发生错误: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### 连接已关闭 ###")

def on_message(ws, message):
    """
    处理收到的消息。
    它会区分 JSON 元数据和二进制音频数据。
    """
    global expected_audio
    
    if isinstance(message, str):
        # 这是一个 JSON 文本消息 (元数据)
        data = json.loads(message)
        
        # 检查是否是流结束的信号
        if data.get("id") == "DONE":
            print("\n--- 音频流接收完毕 ---")
            ws.close()
            return
            
        print(f"\n正在接收: ID - {data['id']}, 文本 - '{data['text']}'")
        # 设置一个标志，表明下一条消息应该是音频数据
        expected_audio = True
        
    elif isinstance(message, bytes):

        # 这是一个二进制消息 (音频数据)
        print("收到音频数据，正在播放...")
        play_audio_from_bytes(message)
        # 重置标志
        expected_audio = False

def play_audio_from_bytes(audio_bytes: bytes):
    """
    使用 pygame 从内存中的字节数据播放音频。
    
    参数:
        audio_bytes (bytes): 完整的 WAV 格式的二进制数据。
    """
    # 确保 pygame.mixer 已经初始化
    if not pygame.mixer.get_init():
        # 注意：这里的频率应该与服务器端发送的音频采样率一致，
        # 例如 24000 Hz 或 16000 Hz。我们假设服务器端发送的是 24000 Hz 的音频。
        pygame.mixer.init(frequency=24000) 
        print("Pygame Mixer 已初始化。")

    try:
        # ### <<< 修改: 在播放前设置事件 >>>
        is_playing_event.set()
        print("🎧 AI 正在说话，暂停录音...")
        # 1. 使用 io.BytesIO 将内存中的字节数据包装成一个类文件对象
        audio_stream = io.BytesIO(audio_bytes)
        
        # 2. Pygame 的 mixer 可以直接从类文件对象中加载声音
        sound = pygame.mixer.Sound(audio_stream)
        
        # 3. 播放声音
        sound.play()
        
        # 4. 等待音频播放完毕
        # get_busy() 检查是否有任何音频正在播放
        while pygame.mixer.get_busy():
            # 限制循环频率，避免占用过多CPU资源
            pygame.time.Clock().tick(10) 
            
    except pygame.error as e:
        print(f"播放音频时出错: {e}")
        print("请确认服务器端发送的音频数据是有效的 WAV 格式！")
    finally:
        # ### <<< 修改: 在播放后（无论成功或失败）都清除事件 >>>
        print("...AI 说话结束。")
        is_playing_event.clear()


if __name__ == "__main__":
    expected_audio = False
    run_client()