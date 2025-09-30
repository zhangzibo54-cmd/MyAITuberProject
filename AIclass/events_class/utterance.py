# 文件名: utterance.py
from dataclasses import dataclass, field
import uuid

def generate_chunk_id() -> str:
    """生成一个唯一的字符串ID"""
    return str(uuid.uuid4())

@dataclass
class UtteranceChunk:
    """
    代表一个可被AITuber“说出”的、最小的、带ID的片段。
    它封装了需要同步的文本和音频数据。
    """
    text: str
    # 使用field来为id提供一个默认的、自动生成的唯一值 防止所有实例共享一个id,
    # 没有field的话下面的语句只会在类的定义完成时执行一次
    id: str = field(default_factory=generate_chunk_id)
    audio_data: bytes = None # 音频数据在TTS生成后才会被填充

if __name__ == "__main__":
    utterance1 = UtteranceChunk("a")
    utterance2 = UtteranceChunk("a")
    print(utterance1.id)
    print(utterance2.id)