import threading
import time
import queue

from perception_events import PerceptionEvent
from commands import Command
from system_events import LogMessageEvent
# from commands import Command # 假设Command在单独文件中

class DecisionEngine:
    # input_queue,output_quue
    def __init__(self, perception_event_queue: queue.Queue, command_queue: queue.Queue, system_event_queue: queue.Queue ):
        # input and output
        self.perception_event_queue = perception_event_queue
        print(f"初始化时p_event有{self.perception_event_queue.qsize()}个")
        self.command_queue = command_queue
        # log
        self.system_event_queue = system_event_queue

        #thread Event() Initially state is clear
        self._is_running = threading.Event()
        self._decision_thread = None
    def start(self):
      # open the thread, set the flag
      print("正要开启decision engine")
      if self._decision_thread is None or not self._decision_thread.is_alive():
        print("开启decision engine")
        self._is_running.set()##必须要先设置这个然后再开启线程，否则下面的while语句可能直接退出掉，导致线程死亡
        self._decision_thread = threading.Thread(target = self._decision_loop, daemon = True)
        self._decision_thread.start()


    def _map_event_to_command(self, perception_event: PerceptionEvent) -> Command:
        if perception_event.type == "KEYBOARD_INPUT":
            return Command("CHAT", perception_event.data)
        elif perception_event.type == "STOP":
            return Command("STOP")

    def _decision_loop(self):
        #every second, try to get eventqueue and change that to command
        # put that into command queue
        # 当外界调用stop函数时，该线程停止
        self.system_event_queue.put(LogMessageEvent("decision loop开始执行，来自系统"))
        while self._is_running.is_set():
          # print(f"decision engine is working length of perception {self.perception_event_queue.qsize()}")

          try:
            p_event = self.perception_event_queue.get_nowait()
            command = self._map_event_to_command(p_event)
            self.command_queue.put(command)
            self.system_event_queue.put(LogMessageEvent(f"转换perception_event到command类型为{command.type}，并放入了command_queue中"))
            print(f"转换perception_event到command类型为{command.type}，并放入了command_queue中")
          except queue.Empty:
            pass
          except Exception as e:
            self.system_event_queue.put(LogMessageEvent(f"决策引擎发生错误：{e}"))
            break
          time.sleep(2)

    def stop(self):
      #used by the AItuber
      self._is_running.clear()

      self.system_event_queue.put(LogMessageEvent("\n stop the decision engine"))

