TYPE_KEYBOARD_INPUT = "KEYBOARD_INPUT"
TYPE_STOP = "STOP"
TYPE_AUDIO = "AUDIO"
TYPE_ASR_TRANSCRIPT = "asr_transcript"
class PerceptionEvent:
    def __init__(self, event_type: str, data: any = None):
        self.type = event_type  # 行为类型，例如 "CHAT" 或 "STOP"
        self.data = data         # 行为所需的数据，例如聊天的文本
