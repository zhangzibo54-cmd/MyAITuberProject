# ---------------------------------------------------------------------------
#  ipywidgets 版本的 PerceptionEngine
# ---------------------------------------------------------------------------
import io
import os
import librosa
import numpy as np
import asyncio

from AIclass.events_class.perception_events import PerceptionEvent,TYPE_ASR_TRANSCRIPT, TYPE_AUDIO, TYPE_KEYBOARD_INPUT
from AIclass.events_class.system_events import LogMessageEvent
import AIclass.events_class.perception_events as pe

import numpy as np
from faster_whisper import WhisperModel
# ---------------------------------------------------------------------------
#  V2 版本: 解决了UI重复和输出冲突的问题
# ---------------------------------------------------------------------------
class PerceptionEngine:

    CLIENT_CHUNK_TIMEOUT = 10  # 假设我们每 10个客户端块 (~640ms) 检查一次静音
    SILENCE_TIMEOUT_SECONDS = 1.2 # 期望的静音超时时
    AUDIO_QUEUE = asyncio.Queue()

    @staticmethod
    async def put_audio_queue(audio_data):
        PerceptionEngine.AUDIO_QUEUE.put_nowait(PerceptionEvent(pe.TYPE_AUDIO,audio_data))
        try:
            print(f"成功放入audio_queue，现在其长度为{PerceptionEngine.AUDIO_QUEUE.qsize()}")
        except:
            pass
    #在本地，负责不断放入的perception_event到perception_event_queue里面
    def __init__(self, perception_event_queue: asyncio.Queue, system_event_queue: asyncio.Queue,asr_model):
        self.perception_event_queue = perception_event_queue
        self.system_event_queue = system_event_queue
        self.asr_model = asr_model  # <<<< 新增：持有 ASR 模型实例
        self._asr_task = None       # <<<< 新增：用于管理 ASR 处理任务
        self.is_running = asyncio.Event()

        # --- 新增状态变量 ---
        self.audio_buffer = bytearray()           # 缓存所有接收到的原始音频块
        self.current_transcript = ""              # 存储当前句子的部分转录结果
        self.is_utterance_active = False          # 标记当前是否正在处理一句话
        # --- 新增配置常量 ---
        self.MAX_SILENCE_CHUNKS = int(self.SILENCE_TIMEOUT_SECONDS / (1024 / 16000)) 
        self.current_silence_count = 0 # 当前已收到的连续静音块数量
        
        # 保持转录阈值 (0.96秒)
        self.MIN_TRANSCRIPTION_CHUNKS = 15

    def _transcribe_audio_bytes(self, audio_bytes: bytes) -> str:
        """
        将内存中的二进制音频数据转录为文本的辅助函数。
        """
        if not self.asr_model:
            print("错误: ASR 模型未初始化。")
            return ""
        try:
            audio_stream = io.BytesIO(audio_bytes)
            waveform, _ = librosa.load(audio_stream, sr=16000, mono=True)
            
            if waveform.dtype != np.float32:
                waveform = waveform.astype(np.float32)

            segments, _ = self.asr_model.transcribe(waveform, beam_size=5)
            
            full_text = "".join(segment.text for segment in segments).strip()
            return full_text
        except Exception as e:
            print(f"ASR 转录过程中发生错误: {e}")
            return ""

    async def _asr_processing_loop(self):
        self.is_running.set()
        while self.is_running.is_set():
            try:
                # 从静态队列中获取音频事件
                audio_event = await PerceptionEngine.AUDIO_QUEUE.get()
                if audio_event.data == None:
                    await self.stop()
                    print("perception_AUDIO_QUEUE收到None信号，停止执行中")
                    break
                audio_bytes = audio_event.data

                print(f"ASR 循环: 取出音频数据块 (长度: {len(audio_bytes)} B)，开始转录...")
                
                # 执行转录
                transcribed_text = self._transcribe_audio_bytes(audio_bytes)

                if transcribed_text:
                    print(f"ASR 结果: '{transcribed_text}'")
                    # 将转录结果作为新的感知事件放入 AITuber 的主感知队列
                    # 您可以使用 TYPE_KEYBOARD_INPUT 来模拟文本输入，或者创建一个新的类型
                    new_event = PerceptionEvent(TYPE_ASR_TRANSCRIPT, transcribed_text)
                    self.perception_event_queue.put_nowait(new_event)
                else:
                    print("ASR 结果为空，已忽略。")
                
                # PerceptionEngine.AUDIO_QUEUE.task_done()

            except asyncio.CancelledError:
                print("ASR 处理循环被取消。")
                break
            except Exception as e:
                print(f"ASR 处理循环中发生未知错误: {e}")

    async def start(self):
        # #在测试中先禁用
        if self.asr_model:
            # 创建并启动 ASR 处理的后台任务
            self._asr_task = asyncio.create_task(self._asr_processing_loop())
            print("PerceptionEngine 已启动")
        else:
            print("警告: 未提供 ASR 模型，语音识别功能将不可用。")
        await self.receive_data()
        pass
        # 启动感知引擎的异步逻辑

    async def receive_data(self):
        # 使用websocket或其他来接收信息，
        # 定义一个ws，ws会有个接收到信息执行的函数参数，
        # 在函数参数里面处理就行

        # 为了测试而执行
        
        # typ = pe.TYPE_KEYBOARD_INPUT
        # self.perception_event_queue.put_nowait(PerceptionEvent(typ,"你好"))
        # self.perception_event_queue.put_nowait(PerceptionEvent(typ,"谢谢"))
        # self.perception_event_queue.put_nowait(PerceptionEvent(typ,"小笼包"))
        # self.perception_event_queue.put_nowait(PerceptionEvent(typ,"再见"))
        pass


    async def stop(self):
        self.is_running.clear()
        if self._asr_task and not self._asr_task.done():
            self._asr_task.cancel()
            await asyncio.sleep(0.1) # 给予取消操作一点时间
        # 停止感知引擎的异步逻辑
        print("PerceptionEngine 已停止")





async def generate_test_audio_bytes(filepath="hello.wav"):
    """
    加载一个真实的 16kHz 单声道 WAV 文件并返回其字节流。
    """
    try:
        # 1. 确保 filepath 指向一个真实的、16kHz 采样率、单声道的 WAV 文件
        with open(filepath, "rb") as f:
            audio_bytes = f.read()
        print(f"成功加载测试音频文件: {filepath} ({len(audio_bytes)} bytes)")
        return audio_bytes
    except FileNotFoundError:
        print(f"\n=== 严重警告：找不到 '{filepath}' 文件！请创建一个真实的 16kHz 单声道 WAV 文件进行测试！===")
        print("=== 正在生成一个静音音频作为代替，这通常会导致 ASR 结果为空。===")
        # 生成一个静音的 BytesIO
        duration = 1.0  # 1秒
        sample_rate = 16000
        waveform = np.zeros(int(sample_rate * duration), dtype=np.float32)
        
        # 需要一个库将 float32 编码为 WAV 字节流。如果 librosa.output 不可用，您可能需要安装 `soundfile` 并使用它。
        # 假设您已配置好环境
        bio = io.BytesIO()
        try:
            # 这是一个简化且可能不准确的方法，最好使用 soundfile 或类似的
            import soundfile as sf
            sf.write(bio, waveform, sample_rate, format='wav')
            return bio.getvalue()
        except Exception as e:
            print(f"无法生成 WAV 字节流：{e}。跳过音频测试。")
            return b''


async def test_perception_engine():
    # 1. 初始化 ASR 模型（Faster Whisper）
    print("正在加载 Faster Whisper 模型...")
    # 推荐使用 "small" 模型进行测试
    asr_model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    print("Faster Whisper 模型加载完成。")

    # 2. 初始化 Queues
    perception_queue = asyncio.Queue()
    system_queue = asyncio.Queue()

    # 3. 实例化 PerceptionEngine
    engine = PerceptionEngine(perception_queue, system_queue, asr_model)

    # 4. 启动引擎
    await engine.start()

    # 获取当前脚本所在的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构造文件的绝对路径
    audio_file_path = os.path.join(current_dir, "hello.wav")
    # 5. 模拟音频输入 (需要一个真实的 'hello.wav' 文件)
    test_audio_bytes = await generate_test_audio_bytes(filepath=audio_file_path)
    if test_audio_bytes:
        # 将音频数据放入 PerceptionEngine 的静态队列
        await PerceptionEngine.put_audio_queue(test_audio_bytes)
        await PerceptionEngine.put_audio_queue(None)
        await engine.start()

        
    # 8. 停止引擎
    # await engine.stop()

# 运行测试
if __name__ == "__main__":
    # 在运行前，请确保您：
    # 1. 创建了一个名为 **'hello.wav'** 的音频文件 
    # 2. 确保它是 **16kHz 采样率，单声道 (Mono)** 格式。
    # 3. 文件中包含一段清晰的语音，例如“你好，世界”。
    print("--- PerceptionEngine ASR 功能测试开始 ---")
    asyncio.run(test_perception_engine())
    print("--- PerceptionEngine ASR 功能测试结束 ---")


