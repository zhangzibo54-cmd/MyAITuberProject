class MockModel:
    def __init__(self, *args, **kwargs):
        self.index = FakeIndex()

    async def generate_response(self, *args, **kwargs):
        return "这是一个模拟的响应。"

class FakeEmbeddingModel:
    def __init__(self, *args, **kwargs):
        self.index = FakeIndex()

    async def embed(self, *args, **kwargs):
        return [0.0] * 768  # 返回一个固定长度的零向量作为模拟嵌入

class FakeIndex:
    def __init__(self, *args, **kwargs):
        pass

    async def query(self, *args, **kwargs):
        return "这是一个模拟的索引查询结果。"

    def as_chat_engine(self,*args, **kwargs):
        return FakeChatEngine()

import asyncio
from typing import AsyncGenerator, List # 引入类型提示，让代码更清晰

# --- 模拟LlamaIndex的底层数据结构 ---
# 这是一个模拟的Node，用于source_nodes
class FakeNode:
    def __init__(self, content: str, score: float):
        self.score = score
        self._content = content
    def get_content(self) -> str:
        return self._content

# --- 您的Fake类，经过了精确的类型匹配修改 ---

class FakeLLM:
    """这是一个模拟的LLM，它会返回一个可以调用.stream_chat()的对象"""
    def as_chat_engine(self, *args, **kwargs):
        # 这个方法现在返回的是我们新定义的、行为更真实的FakeChatEngine
        return FakeChatEngine()

class FakeChatEngine:
    """这是一个模拟的聊天引擎"""
    def __init__(self, *args, **kwargs):
        pass

    def stream_chat(self, user_message: str, *args, **kwargs) -> "FakeResponse":
        """
        这个方法现在会根据用户输入，返回一个包含特定流式响应的FakeResponse对象。
        """
        print(f"【模拟引擎】: 收到了用户消息 “{user_message}”，正在准备模拟流式响应...")
        
        # 我们可以根据输入，返回不同的模拟回复
        if "你好" in user_message:
            response_chunks = ["你好呀！", "很高兴", "认识你！", "喵~🐱"]
        else:
            response_chunks = ["嗯...", "让我想想...", "这是一个模拟的", "通用回复。"]
            
        return FakeResponse(response_chunks=response_chunks)

class FakeResponse:
    """
    这是一个模拟的、与LlamaIndex的StreamingChatResponse行为一致的响应对象。
    """
    def __init__(self, response_chunks: List[str]):
        # 1. source_nodes 应该是一个【同步】迭代器
        #    我们模拟返回两个记忆片段
        print("开始生成模拟回复")
        self.source_nodes = iter([
            FakeNode("这是第一个相关的记忆片段。", 0.85),
            FakeNode("这是第二个相关的记忆片段。", 0.72)
        ])
        
        # 2. 【核心修改】response_gen 必须是一个【异步生成器】
        self.response_gen = self._create_async_generator(response_chunks)

    async def _create_async_generator(self, chunks: List[str]) -> AsyncGenerator[str, None]:
        """
        一个辅助函数，用于从一个普通的列表创建一个异步生成器。
        """
        print("开始生成模拟回复的generator")
        for chunk in chunks:
            # 模拟网络或计算延迟，让流式效果更明显
            await asyncio.sleep(3) 
            # 使用 yield 来逐个返回文本块
            print("生成模拟回复的片段")
            yield chunk

class FakeTTSEngine:
    def __init__(self, *args, **kwargs):
        self.system_event_queue = kwargs.get('system_event_queue', None)    

        pass

    async def start(self):
        pass

    async def stop(self):
        pass



class FakePerceptionEngine:
    def __init__(self, *args, **kwargs):
        self.perception_event_queue = kwargs.get('perception_event_queue', None)
        self.system_event_queue = kwargs.get('system_event_queue', None)    
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

class FakeDecisionEngine:
    def __init__(self, *args, **kwargs):
        self.perception_event_queue = kwargs.get('perception_event_queue', None)
        self.command_queue = kwargs.get('command_queue', None)
        self.system_event_queue = kwargs.get('system_event_queue', None)    
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

class FakeMemorySystem:

    def __init__(self, *args, **kwargs):
        self.index = FakeIndex()   
        pass

    async def start(self):
        pass

    async def stop(self):
        pass

class FakeTTSRes:
    def __init__(self):
        self.status_code = 200
        self.content = b"a"
        pass