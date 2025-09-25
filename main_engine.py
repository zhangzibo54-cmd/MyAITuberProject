
import threading
import queue
from perception_engine import PerceptionEngine
from memory_system import MemorySystem
from decision_engine import DecisionEngine

from tts_empty import Tts_Empty
from llama_index.embeddings.ollama import OllamaEmbedding
from sub_engines.tts_gptsovits import TTSManager_GPTsovits

from system_events import LogMessageEvent

# engine.py
class MainEngine:
    def __init__(
              self,
              perception_engine: PerceptionEngine ,
              memory_system : MemorySystem ,
              decision_engine : DecisionEngine ,
              tts_engine,
              llm,
              embed_model,
              system_event_queue : queue.Queue
              ):

        self.perception_engine = perception_engine
        self.memory_system = memory_system
        self.decision_engine = decision_engine
        self.tts_engine = tts_engine
        self.llm = llm
        self.embed_model = embed_model
        self.system_event_queue = system_event_queue
        self.system_event_queue.put(LogMessageEvent("✅ 总引擎已接收并装配好所有模块。"))



    def start_all_services(self):
        self.tts_engine.start()
        self.perception_engine.start() #因为start()本身会开启一个子线程
        self.decision_engine.start()
        print(f"main_engine中的perception列长度{self.decision_engine.perception_event_queue.qsize()}")
        self.system_event_queue.put(LogMessageEvent("✅ 已经启动所有引擎"))

    def stop_all_services(self):
        self.tts_engine.stop()
        self.perception_engine.stop()
        self.decision_engine.stop()
        self.system_event_queue.put(LogMessageEvent("✅ 已经停止所有引擎"))
