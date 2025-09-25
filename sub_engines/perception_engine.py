
# ---------------------------------------------------------------------------
#  ipywidgets 版本的 PerceptionEngine
# ---------------------------------------------------------------------------
import threading
import queue
import ipywidgets as widgets
from IPython.display import display as ipy_display, clear_output

from perception_events import PerceptionEvent
from system_events import LogMessageEvent

# ---------------------------------------------------------------------------
#  V2 版本: 解决了UI重复和输出冲突的问题
# ---------------------------------------------------------------------------
class PerceptionEngine:
    def __init__(self, perception_event_queue: queue.Queue , system_event_queue: queue.Queue):
        return None
    def start(self):
        return None

    def stop(self):
        return None

