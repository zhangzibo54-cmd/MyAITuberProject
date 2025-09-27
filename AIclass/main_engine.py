import asyncio
from sub_engines.perception_engine import PerceptionEngine
from sub_engines.memory_system import MemorySystem
from sub_engines.decision_engine import DecisionEngine

from sub_engines.tts_empty import Tts_Empty

from llama_index.embeddings.ollama import OllamaEmbedding
from sub_engines.tts_gptsovits import TTSManager_GPTsovits

from events_class.system_events import LogMessageEvent

class MainEngine:
    def __init__(
              self,
              perception_engine: PerceptionEngine ,
              memory_system : MemorySystem ,
              decision_engine : DecisionEngine ,
              tts_engine,
              llm,
              embed_model,
              system_event_queue : asyncio.Queue
              ):

        self.perception_engine = perception_engine
        self.memory_system = memory_system
        self.decision_engine = decision_engine
        self.tts_engine = tts_engine
        self.llm = llm
        self.embed_model = embed_model
        self.system_event_queue = system_event_queue

    async def start_all_services(self):
        try:
            await self.tts_engine.start()
            await self.perception_engine.start()
            await self.decision_engine.start()
            print(f"main_engine中的perception列长度{self.decision_engine.perception_event_queue.qsize()}")
            await self.system_event_queue.put(LogMessageEvent("✅ 已经启动所有引擎"))
        except Exception as e:
            print(f"启动引擎时发生错误：{e}")

    async def stop_all_services(self):
        try:
            await self.tts_engine.stop()
            await self.perception_engine.stop()
            await self.decision_engine.stop()
            await self.system_event_queue.put(LogMessageEvent("✅ 已经停止所有引擎"))
        except Exception as e:
            print(f"停止引擎时发生错误：{e}")
