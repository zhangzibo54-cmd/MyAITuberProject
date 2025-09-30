# /content/drive/MyDrive/MyAITuberProject/system_events.py
TYPE_LOG_MESSAGE = "LOG_MESSAGE"
TYPE_AUDIO_READY = "AUDIO_READY"
TYPE_TEXT_CHUNK =  "TEXT_CHUNK"

class SystemEvent:
    """
    所有系统事件的基类。
    """
    def __init__(self, event_type: str):
        self.type = event_type

class LogMessageEvent(SystemEvent):
    """
    用于传递日志信息的事件。
    """
    def __init__(self, message: str, end = "\n" ,level: str = "INFO"):
        super().__init__("LOG_MESSAGE")
        self.message = message + end
        self.level = level

class TextChunkEvent(SystemEvent):
    """
    用于传递AI生成的文本片段的事件。
    """
    def __init__(self, text: str):
        super().__init__("TEXT_CHUNK")
        self.text = text

class AudioReadyEvent(SystemEvent):
    """
    用于传递已准备好的音频数据的事件。
    """
    def __init__(self, audio_data: bytes, duration: float):
        super().__init__("AUDIO_READY")
        self.audio_data = audio_data
        self.duration = duration
        

