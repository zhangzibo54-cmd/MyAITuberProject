import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.ollama import Ollama
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import PromptTemplate

import threading
import queue
import time
import asyncio

from AIclass.main_engine import MainEngine
from events_class.commands import Command
from events_class.system_events import LogMessageEvent
from events_class.system_events import AudioReadyEvent
from events_class.system_events import TextChunkEvent

# AItueber类

class AItuber:
    def __init__(
        self, 
        main_engine: MainEngine, 
        system_event_queue: asyncio.Queue, 
        charac_name = "",
        custom_context_str = "" , 
        custom_condense_prompt_str = "", 
        similarity_top_num = 5, 
        short_memory_toke_limit = 4096
    ):
        # """
        # 在传参时要注意main_engine 的perception 和 decision engine的event queue应该是同一个
        # 初始化记忆系统
        # main_engine 包含perception, memory, decision ,tts
        # command_queue decision_engine 的输出向量
        # :param index: LlamaIndex的向量索引
        # :param llm: Ollama的LLM实例
        # """
        self.main_engine = main_engine

        #initialize all the engine and an memory index
        self.perception_engine = main_engine.perception_engine
        self.decision_engine = main_engine.decision_engine
        self.memory_system = main_engine.memory_system
        self.index = self.memory_system.index
        self.tts_manager = main_engine.tts_engine # 直接接收一个TTSManager实例
        self.llm = main_engine.llm
        self.embed_model = main_engine.embed_model

        # input and output stream for engine
        self.event_queue = self.decision_engine.perception_event_queue # for output of perception
        self.command_queue = self.decision_engine.command_queue # for output of decision engine
        self.command = Command(None)

        # name
        self.charac_name = charac_name

        # ability of talking
        self.similarity_top_num = similarity_top_num
        self.short_memory_toke_limit = short_memory_toke_limit

        # log information
        self.system_event_queue = system_event_queue
        self._audio_queue = asyncio.Queue()

        # thread
        self._is_running  = threading.Event()
        self.consciousness_thread = None

        #record the time and add the unplaying music to audio_queue
        self.last_audio_start_time = time.time()
        self._audio_duration = 0

        #提示模板
        custom_context_prompt = PromptTemplate(custom_context_str)

        # --- 2. 为“问题压缩”步骤创建强制中文模板 ---
        # 这个模板确保AI在“思考”和“改写问题”时也使用中文

        custom_condense_prompt = PromptTemplate(custom_condense_prompt_str)

        #任务列表 play audio, execute command, handle system event
        self.tasks = []

        #限制短期记忆长度
        '''MemorySystem作用的地方1/2'''
        self.chat_memory = ChatMemoryBuffer.from_defaults(token_limit = short_memory_toke_limit)

        # 关键改动：使用 .as_chat_engine() 来创建一个有状态的聊天引擎
        self.chat_engine = self.index.as_chat_engine(
            llm = self.llm,
            memory = self.chat_memory,
            # chat_mode="condense_plus_context" 是一种先进的模式
            # 它会智能地将对话历史和RAG检索结果结合
            chat_mode = "condense_plus_context",
            # verbose=True, # 设置为True可以看到它内部的思考过程

            similarity_top_k = similarity_top_num,
            # 关键改动在这里！
            context_prompt = custom_context_prompt,
            condense_prompt = custom_condense_prompt

        )
        print("✅ 全功能记忆系统已准备就绪 (包含短期记忆和长期记忆)。")

        # print("✅ 加载了强制中文输出模板。")

    async def memorize(self, text_to_remember):
        #实现记忆
        try:
            await self.memory_system.memorize(text_to_remember)
        except Exception as e:
            print(f"记忆时发生错误：{e}")

    async def start(self):
        '''
        启动AItuber的意识流
        1. 启动所有引擎
        2. 启动意识流loop(已经弃用)
        3. 启动处理系统事件的协程
        4. 启动处理命令的协程
        5. 启动播放音频的协程
        6. 捕捉键盘中断，停止所有引擎和协  
        '''
        #启动全部引擎
        await self.main_engine.start_all_services()
        self.tasks = [
            asyncio.create_task(self.execute_command()),
            asyncio.create_task(self.handle_system_event()),
            asyncio.create_task(self.play_audio_in_queue()),
        ]
        try:
            await asyncio.gather(*self.tasks)
            print("AItuber已经启动")
        except KeyboardInterrupt:
            print("AItuber正在手动停止中")
            await self.stop_consciousness()
            print("AItuber已经完全停止")
        except asyncio.CancelledError:
            print("AItuber的任务被取消")
            await self.stop_consciousness()
            print("AItuber已经完全停止")

    async def stop_consciousness(self):
        self._is_running.clear()
        await self.main_engine.stop_all_services()
        #只是把flag取消不够，还要把所有的task取消
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        print("stop the consciousness flow")

    async def execute_command(self):
        '''
        you need to avoid the empty of command queue
        get the command, and exectue it according to its type
        '''
        while True:
            command = await self.command_queue.get()
            print(f"\n got a command of type {command.type}")
    
            if command.type == "CHAT":
                print("\n begin to chat:=====================")
                # asyncio.create_task(self.chat(user_message=command.data, in_consciousness_loop=True, is_print=True))
                print(f"\n模拟谈话中，用户输入是: {command.data}")
            elif command.type == "STOP":
                await self.stop_consciousness_loop()
                pass
            elif command.type == "MEMORIZE":
                await self.memorize(command.data)
            else:
                print(f"未知的命令类型: {command.type}")

    async def handle_system_event(self):
        # print("正在处理系统事件")
        if system_event.type == "LOG_MESSAGE":
            # print(system_event.message)
            pass
            '''use print here'''
        elif system_event.type == "AUDIO_READY":
            await self._audio_queue.put((system_event.audio_data,system_event.duration))
            print(f"audio event received, the duration is {system_event.duration}")
            if system_event.audio_data == None:
                print("alert!!!!None type of audio")
            else:
                print("模拟播放音频中") 
        elif system_event.type == "TEXT_CHUNK":
            print(system_event.type)
            pass
            # print("now the system_event type is TEXT_CHUNK")
        else:
            print(f"Unknown system event type: {system_event.type}")

    async def play_audio_in_queue(self): # abandon temporarily
        current_time = time.time()
        # 检查上一段音频是否播放完毕
        if (current_time - self.last_audio_start_time) >= self._audio_duration and not self._audio_queue.empty():
            audio_data, duration = await self._audio_queue.get()
            # 在主线程中播放音频
            print(f"\n开始播放音频,time duration: {duration}")
            display(Audio(data=audio_data, autoplay=True))

        # 更新状态变量
        self._audio_duration = duration
        self.last_audio_start_time = current_time

    async def chat(self, user_message: str,  in_consciousness_loop = False,is_print = False,) -> str:
        """
        进行一次有短期记忆的、流式的对话。

        :param user_message: 用户输入的消息字符串。
        :return: AI生成的完整回答字符串。
        """
        # 打印用户的提问，方便在界面上看到

        # 调用聊天引擎的 .stream_chat() 方法来获取流式响应
        response = self.chat_engine.stream_chat(user_message)

        # 初始化一个空字符串，用来拼接完整的回答
        full_response_text = ""

        #初始化一个tts类
        tts_manager = self.tts_manager
        # 遍历响应中的生成器 (generator)，逐个获取token
        # response.response_gen 是包含所有文本片段的数据流
        for token in response.response_gen:
            '''tts作用的地方1/2'''
            tts_manager.add_next_chunk(token)
            # 将token拼接到完整回答的字符串中
            full_response_text += token
        '''tts作用的地方2/2'''
        #只有当不在意识流时，自己测试调用的话会自动结束
        if not in_consciousness_loop:
            tts_manager.finish_streaming()
        # 所有token接收完毕后，打印一个换行符，让界面更整洁
        await self.system_event_queue.put(LogMessageEvent(f"💬{self.charac_name}: {full_response_text}"))
        if is_print:
            print(f"💬{self.charac_name}: {full_response_text}")

        #显示使用了哪些长期记忆
        if response.source_nodes:
            for i, node in enumerate(response.source_nodes):
                print(f"  - 记忆片段 #{i+1} (相似度: {node.score:.4f}):")
                if is_print:
                    print(f"  - 记忆片段 #{i+1} (相似度: {node.score:.4f}): ")

                # 为了显示整洁，我们将记忆内容进行清理和截断
                content = node.get_content().strip().replace('\n', ' ')
                if len(content) > 120:
                    content = content[:120] + "..."

                await self.system_event_queue.put(LogMessageEvent(f"    '{content}'"))
                if is_print:
                    print(f"    '{content}'")
        else:
            print("  - 本次回答主要依赖短期记忆或通用知识，未直接引用长期记忆。")
            if is_print:
                print("  - 本次回答主要依赖短期记忆或通用知识，未直接引用长期记忆。")

        print("="*50)

        # 返回AI的完整回答，可用于后续处理（如存入日志、语音合成等）
        return full_response_text

if __name__ == "__main__":

    llm = None
    embed_model = None

    import asyncio
    from sub_engines.memory_system import MemorySystem
    from sub_engines.perception_engine import PerceptionEngine
    from sub_engines.decision_engine import DecisionEngine
    from sub_engines.tts_empty import Tts_Empty

    # 1. 创建异步队列
    system_event_queue = asyncio.Queue()

    # 2. 初始化各子系统并传递 system_event_queue
    ai_memory = MemorySystem(embed_model=embed_model, system_event_queue=system_event_queue)
    tts_manager = Tts_Empty()
    ban_tts = False

    event_queue = asyncio.Queue()
    command_queue = asyncio.Queue()
    perceptionEngine = PerceptionEngine(event_queue, system_event_queue=system_event_queue)
    decisionEngine = DecisionEngine(
        perception_event_queue=event_queue,
        command_queue=command_queue,
        system_event_queue=system_event_queue
    )

    main_en = MainEngine(
        perception_engine=perceptionEngine,
        memory_system=ai_memory,
        decision_engine=decisionEngine,
        tts_engine=tts_manager,
        llm=llm,
        embed_model=embed_model,
        system_event_queue=system_event_queue
    )

    print("✅ Ollama和RAG组件初始化完成。")

    AItuber_novoice = AItuber(charac_name = character_name,main_engine = main_en,system_event_queue= system_event_queue ,custom_context_str = custom_context_str,
                custom_condense_prompt_str = custom_condense_prompt_str)
    print("\n\n🎉🎉🎉  AI 系统已完全准备就绪，整装待发！🎉🎉🎉")

    command_queue.put_nowait(Command("CHAT", "你好"))
    command_queue.put_nowait(Command("CHAT", "你是谁？"))
    command_queue.put_nowait(Command("CHAT", "你能做什么？"))
    command_queue.put_nowait(Command("MEMORIZE", "记住这个信息"))
    command_queue.put_nowait(Command("CHAT", "你刚才记住了什么？"))
    command_queue.put_nowait(Command("STOP"))
    asyncio.run(AItuber_novoice.start())

