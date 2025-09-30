import websocket
import json
import pygame
import io
import sys
# --- 配置 ---
# 将 "localhost" 替换为你的服务器的 IP 地址或域名

#####📕#####
SERVER_URL = "ws://194.68.245.179:8000/ws/stream_utterances"
#####📕#####

def play_audio_from_bytes(audio_bytes: bytes):
    """使用 pygame 从内存中的字节数据播放音频。"""
    try:
        # Pygame 的 mixer 可以从类文件对象 (file-like object) 中加载声音
        audio_stream = io.BytesIO(audio_bytes)
        sound = pygame.mixer.Sound(audio_stream)
        sound.play()
        
        # 等待音频播放完毕
        # get_busy() 检查是否有任何音频正在播放
        while pygame.mixer.get_busy():
            pygame.time.Clock().tick(10)
    except pygame.error as e:
        print(f"播放音频时出错: {e}")
        print("请确认音频数据是有效的 WAV 格式。")

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
        ws.run_forever()
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

def on_open(ws):
    print("已成功连接到服务器！等待接收音频流...")

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

if __name__ == "__main__":
    expected_audio = False
    run_client()