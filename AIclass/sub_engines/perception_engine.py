# ---------------------------------------------------------------------------
#  ipywidgets 版本的 PerceptionEngine
# ---------------------------------------------------------------------------

import threading
import queue
import asyncio

from AIclass.events_class.perception_events import PerceptionEvent
from AIclass.events_class.system_events import LogMessageEvent
import AIclass.events_class.perception_events as pe
# ---------------------------------------------------------------------------
#  V2 版本: 解决了UI重复和输出冲突的问题
# ---------------------------------------------------------------------------
class PerceptionEngine:
    #在本地，负责不断放入的perception_event到perception_event_queue里面
    def __init__(self, perception_event_queue: asyncio.Queue, system_event_queue: asyncio.Queue):
        self.perception_event_queue = perception_event_queue
        self.system_event_queue = system_event_queue
        self.is_running = asyncio.Event()

    async def start(self):
        
        # 启动感知引擎的异步逻辑
        print("PerceptionEngine 已启动")

    async def receive_data(self):
        # 使用websocket或其他来接收信息，
        # 定义一个ws，ws会有个接收到信息执行的函数参数，
        # 在函数参数里面处理就行

        # 为了测试而执行
        typ = pe.TYPE_KEYBOARD_INPUT
        self.perception_event_queue.put_nowait(PerceptionEvent(typ,"你好"))
        self.perception_event_queue.put_nowait(PerceptionEvent(typ,"谢谢"))
        self.perception_event_queue.put_nowait(PerceptionEvent(typ,"小笼包"))
        self.perception_event_queue.put_nowait(PerceptionEvent(typ,"再见"))
        pass


    async def stop(self):
        self.is_running.clear()
        # 停止感知引擎的异步逻辑
        print("PerceptionEngine 已停止")

