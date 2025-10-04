
import threading
import time
import queue
import asyncio

from AIclass.events_class.perception_events import PerceptionEvent,TYPE_ASR_TRANSCRIPT
from AIclass.events_class.commands import Command
from AIclass.events_class.system_events import LogMessageEvent

TYPE_AUDIO_TEXT = "AUDIO_TEXT"
class DecisionEngine:
    def __init__(self, perception_event_queue: asyncio.Queue, command_queue: asyncio.Queue, system_event_queue: asyncio.Queue ):
        self.perception_event_queue = perception_event_queue
        print(f"初始化时p_event有{self.perception_event_queue.qsize()}个")
        self.command_queue = command_queue
        self.system_event_queue = system_event_queue
        self._is_running = asyncio.Event()
        self._decision_task = None

    async def start(self):
        print("正要开启decision engine")
        if self._decision_task is None or self._decision_task.done():
            print("开启decision engine")
            self._is_running.set()
            self._decision_task = asyncio.create_task(self._decision_loop())

    async def _map_event_to_command(self, perception_event: PerceptionEvent) -> Command:
        command = None
        if perception_event.type == "KEYBOARD_INPUT" or perception_event.type == TYPE_ASR_TRANSCRIPT:
            command = Command("CHAT", perception_event.data)
        elif perception_event.type == "STOP":
            command = Command("STOP")
        
        if command:
            print(f"map to cmd:生成的cmd类型为:{command.type}")
        else:
            print(f"未知的perception类型:{perception_event.type}")

        return command
        

    async def _decision_loop(self):
        print("decision loop开始监听，--来自decision系统")
        while self._is_running.is_set():
            try:
                # print(f"decision_loop 正在运行:待处理事件数量{self.perception_event_queue.qsize()}")
                p_event = await asyncio.wait_for(self.perception_event_queue.get(), timeout=1.0)
                command = await self._map_event_to_command(p_event) #这一步之后可能会变得耗时
                if command:
                    await self.command_queue.put(command)
                    print(f"decision loop:转换perception_event到command类型为{command.type}，并放入了command_queue中")
            except asyncio.TimeoutError:
                # print("一秒内perception_event_queue没有接收到事件")
                pass
            except Exception as e:
                print(f"决策引擎发生错误：{e}")
                break
        print("decision loop已停止")

    async def stop(self):
        self._is_running.clear()
        print("\n stop the decision engine")

