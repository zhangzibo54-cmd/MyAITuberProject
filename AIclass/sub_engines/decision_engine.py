import threading
import time
import queue
import asyncio

from events_class.perception_events import PerceptionEvent
from events_class.commands import Command
from events_class.system_events import LogMessageEvent


class DecisionEngine:
    def __init__(self, perception_event_queue: asyncio.Queue, command_queue: asyncio.Queue, system_event_queue: asyncio.Queue ):
        self.perception_event_queue = perception_event_queue
        print(f"初始化时p_event有{self.perception_event_queue.qsize()}个")
        self.command_queue = command_queue
        self.system_event_queue = system_event_queue
        self._is_running = False
        self._decision_task = None

    async def start(self):
        print("正要开启decision engine")
        if self._decision_task is None or self._decision_task.done():
            print("开启decision engine")
            self._is_running = True
            self._decision_task = asyncio.create_task(self._decision_loop())

    async def _map_event_to_command(self, perception_event: PerceptionEvent) -> Command:
        if perception_event.type == "KEYBOARD_INPUT":
            return Command("CHAT", perception_event.data)
        elif perception_event.type == "STOP":
            return Command("STOP")

    async def _decision_loop(self):
        await self.system_event_queue.put(LogMessageEvent("decision loop开始执行，来自系统"))
        while self._is_running:
            try:
                p_event = await self.perception_event_queue.get()
                command = await self._map_event_to_command(p_event)
                await self.command_queue.put(command)
                await self.system_event_queue.put(LogMessageEvent(f"转换perception_event到command类型为{command.type}，并放入了command_queue中"))
                print(f"转换perception_event到command类型为{command.type}，并放入了command_queue中")
            except Exception as e:
                await self.system_event_queue.put(LogMessageEvent(f"决策引擎发生错误：{e}"))
                break
            await asyncio.sleep(2)

    async def stop(self):
        self._is_running = False
        await self.system_event_queue.put(LogMessageEvent("\n stop the decision engine"))

