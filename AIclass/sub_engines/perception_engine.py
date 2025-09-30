# ---------------------------------------------------------------------------
#  ipywidgets 版本的 PerceptionEngine
# ---------------------------------------------------------------------------

import threading
import queue
import asyncio

from AIclass.events_class.perception_events import PerceptionEvent
from AIclass.events_class.system_events import LogMessageEvent

# ---------------------------------------------------------------------------
#  V2 版本: 解决了UI重复和输出冲突的问题
# ---------------------------------------------------------------------------
class PerceptionEngine:
    def __init__(self, perception_event_queue: asyncio.Queue, system_event_queue: asyncio.Queue):
        self.perception_event_queue = perception_event_queue
        self.system_event_queue = system_event_queue

    async def start(self):
        # 启动感知引擎的异步逻辑
        await print("PerceptionEngine 已启动")

    async def stop(self):
        # 停止感知引擎的异步逻辑
        await print("PerceptionEngine 已停止")

