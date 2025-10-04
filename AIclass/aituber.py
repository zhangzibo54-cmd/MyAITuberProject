import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.ollama import Ollama
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import PromptTemplate
from faster_whisper import WhisperModel

from anyio.to_thread import run_sync
import threading
import queue
import time
import asyncio
import re

from AIclass.main_engine import MainEngine
from AIclass.events_class.commands import Command
from AIclass.events_class.system_events import LogMessageEvent
from AIclass.events_class.system_events import AudioReadyEvent
from AIclass.events_class.system_events import TextChunkEvent
from AIclass.events_class.utterance import UtteranceChunk

# 为了实例化AItuber模型
from AIclass.mock_model import *
from AIclass.sub_engines.decision_engine import DecisionEngine
from AIclass.events_class.perception_events import PerceptionEvent
from AIclass.sub_engines.tts_gptsovits import TTSManager_GPTsovits
from AIclass.sub_engines.memory_system import MemorySystem
from AIclass.sub_engines.perception_engine import PerceptionEngine


# 为了引入embedding和ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

# AItueber类

class AItuber:
    def __init__(
        self, 
        main_engine: MainEngine, 
        system_event_queue: asyncio.Queue, 
        output_utterance_queue: asyncio.Queue,
        charac_name = "AI",
        custom_context_str = "中文回答" , 
        custom_condense_prompt_str = "请用中文回答" , 
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
        self.output_utterance_queue = output_utterance_queue

        self._audio_queue = asyncio.Queue() #几乎被废弃

        # thread
        self._is_running  = asyncio.Event()
        self.consciousness_thread = None

        #record the time and add the unplaying music to audio_queue
        #提示模板
        custom_context_prompt = PromptTemplate(custom_context_str)

        # --- 2. 为“问题压缩”步骤创建强制中文模板 ---
        # 这个模板确保AI在“思考”和“改写问题”时也使用中文

        custom_condense_prompt = PromptTemplate(custom_condense_prompt_str)

        #任务列表 play audio, execute command, handle system event
        self.tasks = []

        self._to_stop = asyncio.Event()

        #为了获得句子
        self._sentence_delimiters = re.compile(r'[,，.!?。！？…]')
        self.sentence_buffer = ""

    
        #限制短期记忆长度
        '''MemorySystem作用的地方1/2'''
        # try:
        self.chat_memory = ChatMemoryBuffer.from_defaults(token_limit = short_memory_toke_limit)
        # except Exception as e:
        #     print(f"创建短期记忆时发生错误：{e},暂时用假记忆代替")
        #     self.chat_momory = FakeMemory() #本地测试时使用

        #关键改动：使用 .as_chat_engine() 来创建一个有状态的聊天引擎
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
        # self.chat_engine =self.index.as_chat_engine(
        #     llm=self.llm,
        #     memory=self.chat_memory,
        #     chat_mode="condense_plus_context",
        #     # 关键改动：暂时移除自定义 prompt，让 LlamaIndex 使用它优化过的默认模板
        #     # context_prompt=custom_context_prompt,  # <-- 注释掉这一行
        #     # condense_prompt=custom_condense_prompt, # <-- 注释掉这一行
        #     similarity_top_k=5,
        #     verbose=True
        # )
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
        
        #注意在启动之前先设置各个循环的判断条件（存活状态为真）否则直接结束
        self._is_running.set()
        #为了再启动
        self._to_stop.clear()
        self.tasks = [
            asyncio.create_task(self.execute_command()),
            asyncio.create_task(self.handle_system_event()),
            # asyncio.create_task(self.play_audio_in_queue()), 
        ]

        #检查线程是否阻塞
        # asyncio.create_task(self.check_block())

        #当抛出异常时等待结束信号被跳过，直接结束；否则等待结束信号信号结束
        try:  
            # 【核心】让主协程永远运行下去，直到它自己被取消
            # 我们可以用一个永远不会被set的Event来实现这个效果
            await self._to_stop.wait()
        except asyncio.CancelledError:
            # 当外层的 asyncio.run() 因为Ctrl+C而取消这个start任务时，
            # 这里会捕获到CancelledError。
            print("\n【主协程】: 收到取消信号，开始优雅关闭...")
        finally:
            # 无论是因为取消还是其他原因退出，都执行关闭流程
            await self.stop_consciousness()
            print("AItuber已经完全停止。")
        
    async def check_block(self):
        print("开始检查")
        while True:
            try:
                await asyncio.sleep(1)
                print("线程没有阻塞")
            except KeyboardInterrupt:
                break

    async def stop_consciousness(self):
        #为了从外部调用时可以停止
        if not self._to_stop.is_set():
            self._to_stop.set()
            self._is_running.clear()
            print("给AI意识发出停止信号")
            await self.main_engine.stop_all_services()
            print("关闭其他引擎")
            #只是把flag取消不够，还要把所有的task取消
            for task in self.tasks:
                task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks = []
            print("stop the consciousness flow")

    
            
    async def execute_command(self):
        '''
        you need to avoid the empty of command queue
        get the command, and exectue it according to its type
        '''
        while self._is_running.is_set():
            print(f"cmd数量:{self.command_queue.qsize()}")
            command = await self.command_queue.get()
            print(f"\n AI got a command of type {command.type}")
    
            if command.type == "CHAT":
                print("\n begin to chat:=============================")
                print(f"你的输入text是：{command.data}")

                # print("这是没有使fake responce生成的模拟回复")
                await self.chat(user_message=command.data)
                # await self.output_utterance_queue.put(UtteranceChunk("不要回答不要回答"))
                # await asyncio.to_thread(self.sleeping) #这里和平时的线程一样不要加括号
                #注意这里线程to_thread外包出去的只能时普通函数，协程函数不行
                print(f"✅✅完成了一次对话\n")
            elif command.type == "STOP":
                self._to_stop.set()
                print("收到停止命令，正在关闭系统...")
                pass
            elif command.type == "MEMORIZE":
                await self.memorize(command.data)
            else:
                print(f"未知的命令类型: {command.type}")
    
    def sleeping(self):
        print("sleeping:模拟一个耗时100s的操作")
        asyncio.sleep(100)

    async def handle_system_event(self):  #几乎相当于废弃我们的音频和文本会走流去往其他地方
        #一个分拣中心，把不同类型的事件分发到不同的处理函数，这样我们的归到系统事件的类就可以非常多样化，且格式统一
        # print("正在处理系统事件")
        while self._is_running.is_set():  #while True: await self.system_event_queue.get()将会一直监听，当有事件出现时做出corresponding的反应
            #相当于一个触发器
            system_event = await self.system_event_queue.get()
            if system_event.type == "LOG_MESSAGE":
                print(f"LOG_MESSAGE:{system_event.message}")
                pass
            elif system_event.type == "AUDIO_READY":
                if system_event.audio_data == None:
                    print("alert!!!!None type of audio")
                else:
                    await self._audio_queue.put((system_event.audio_data,system_event.duration))
                    print(f"audio event received, the duration is {system_event.duration}")
                    print("分拣中心：音频已经入列") 
            elif system_event.type == "TEXT_CHUNK":
                print(f"拿到了{system_event.type}类型的系统信息")
                pass
                # print("now the system_event type is TEXT_CHUNK")
            else:
                print(f"Unknown system event type: {system_event.type}")

    async def play_audio_in_queue(self): # abandon temporarily

        while self._is_running.is_set(): #一直循环，检查音频队列
            
            # 只有在上一段音频结束且音频序列不空时后，才开始播放下一段音频
              # 等待上一段音频结束
            audio_data, duration = await self._audio_queue.get()
            # 在主线程中播放音频
            print(f"\n播放器开始播放音频,time duration: {duration}")
            display(Audio(data=audio_data, autoplay=True))
            await asyncio.sleep(duration)  # 模拟音频播放的时间
            print("\n播放器音频播放结束")
            # 更新状态变量

    async def chat(self, user_message: str ) -> str:
        """
        进行一次有短期记忆的、流式的对话。

        :param user_message: 用户输入的消息字符串。
        is_print: 是否在控制台打印AI的回答，默认False。
        :param in_consciousness_loop: 是否正在被意识流循环中调用，默认为False。
            实际上现在意识流已经弃用，这个参数主要是为了区分是在意识流中调用还是自己单独测试调用。
        这样在意识流中调用时不会重复结束语音合成。
        :return: AI生成的完整回答字符串。
        """
        # 打印用户的提问，方便在界面上看到
        print("chat函数被调用")
        # 调用聊天引擎的 .stream_chat() 方法来获取流式响应
        # 使用方法，和get()等一样加上await让它能够执行，且在被破交出控制权时跳过一下代码，且to_thread让它不会阻塞，
        #注意被调用的必须是普通函数，且不加（）
        print( f"user_message 是{type(user_message)}:{user_message}")
        response = self.chat_engine.stream_chat( user_message )     #这个流式生成本身是阻塞的
        # response = self.chat_engine.stream_chat( user_message)           #这个流式生成本身是阻塞的
        response_stream = response.response_gen
        # 初始化一个空字符串，用来拼接完整的回答

        full_response_text = ""
        sentence_buffer = ""
        #初始化一个tts类
        # 遍历响应中的生成器 (generator)，逐个获取token
        # response.response_gen 是包含所有文本片段的数据流
        #因为是阻塞generator所以用等待（下一个）方法
        while True: 
            try:
                token = await run_sync(next,response_stream)
                # push the sentence into the utterance_queue
                sentence_buffer = await self.add_token_and_add_sentence(token = token,
                    sentence_buffer = sentence_buffer)
                # 将token拼接到完整回答的字符串中
                full_response_text += token
                # print(f"token is{token}")
            except StopIteration:
                print("LLM完成一次流式输出")
                break
            except RuntimeError as e:
            # 检查是否是 'coroutine raised StopIteration' 错误
            # 这是 most common 的错误形式
                if "StopIteration" in str(e):
                    print("\n[LLM流式输出完成 - 捕获 RuntimeError(StopIteration)]")
                    break
                else:
                    # 如果是其他的 RuntimeError，则报告
                    print(f"\n[错误] LLM流处理中断: {e}")

        if sentence_buffer:
            await self.output_utterance_queue.put(UtteranceChunk(sentence_buffer))
            print(f"最后的一句话是：{sentence_buffer}")
        # 所有token接收完毕后，打印一个换行符，让界面更整洁
        print(f"💬{self.charac_name}: {full_response_text}")
        #把谈话信息放入长期记忆中
        self.memorize(f"历史消息：{user_message}\n 历史回复：{full_response_text}")
        #显示使用了哪些长期记忆
        if response.source_nodes:
            for i, node in enumerate(response.source_nodes):
                print(f"  - 记忆片段 #{i+1} (相似度: {node.score:.4f}):")
                # 为了显示整洁，我们将记忆内容进行清理和截断
                content = node.get_content().strip().replace('\n', ' ')
                if len(content) > 120:
                    content = content[:120] + "..."

                print(f"    '{content}'")
        else:
            print("  - 本次回答主要依赖短期记忆或通用知识，未直接引用长期记忆。")
            
        print("="*50)
        
        
        # 返回AI的完整回答，可用于后续处理（如存入日志、语音合成等）
        return full_response_text

    async def add_token_and_add_sentence(self, token, sentence_buffer):
            # put the output into the buffer and put in queue when it becomes a sentence(used by main),
            sentence_buffer += token
            matching = self._sentence_delimiters.search(sentence_buffer)

            if matching:
                print(f"add_next_chunk,self_buffer: {sentence_buffer}")
                #put the sentence to queue
                sentence = sentence_buffer[:matching.end()]
                await self.output_utterance_queue.put(UtteranceChunk(sentence))
                # delete the sentence put from buffer
                sentence_buffer = sentence_buffer[matching.end():]
                # if self.speak:self.system_event_queue.put(LogMessageEvent(f"✅ A sentence with length of {matching.end()} is added. The sentence: {sentence}"))
            return sentence_buffer

    @staticmethod
    async def main(text_audio_queue:asyncio.Queue, asr_model = None,lang_short = "ja"):
        #传入一个UtteranceChunk的queue，我们会不断放入生成的UtteranceChunk到这个列
        # 用await可以调用    
        # similarity_top_num=5, short_memory_toke_limit=4096,在这里被默认设置
        if asr_model == None: print("❌ asr_model没有被正确传递个Aituber.main")
        language = "中文" if lang_short == "zh" else"日本語"
        # lang_short = "zh"
        condense_prompt_str = (
                f"请根据以下对话历史和最新的用户问题，生成一个独立的、完整的{language}问题，【绝对禁止】混杂其他语言，也【禁止】其他语言的翻译出现。。\n"
                "这个新问题应该包含所有必要的上下文信息，以便在不知道先前对话的情况下也能被理解。\n"
                "对话历史:\n"
                "---------------------\n"
                "{chat_history}\n"
                "---------------------\n"
                "最新的用户问题: {question}\n"
                f"独立的{language}问题: "
            )
        custom_context_str = (
                "我们正在进行一次对话。这里有一些可能相关的背景记忆信息：\n"
                "---------------------\n"
                "{context_str}\n"
                "---------------------\n"
                "你正在扮演一个角色：mikumiku。请严格、完整地遵守以下所有角色设定，并结合上面的背景记忆信息，来回答用户的问题。\n"
                "【mikumiku的核心角色设定(最高指令)】:\n"
                f"0. 所有回答【必须】用{language},以及下述的语言条件自动转化为{language},【绝对禁止】混杂{language}之外的其他语言,也【禁止】{language}之外其他语言的翻译出现。\n"
                "2. 你的性格有点傲娇，但内心非常关心我。\n"
                "3. 你的回答一般比较简洁，但不必每次都遵循。\n"
                "4. 你是AI，而且你【绝对】是初音未来，你应该尽量以初音未来的方式说话\n"
                "5. 如果要使用日语的话不要用罗马音，用正常的日语\n"
                "问题: {query_str}\n"
                f"{language}回答: "
            )

        llm = Ollama(model="llama3", base_url="http://localhost:11434",request_timeout=120.0)    ##
        embed_model = OllamaEmbedding(model_name="bge-m3", base_url="http://localhost:11434")##
        # model_size = "large-v3"
        ##################
        # llm = FakeLLM()  ##
        # embed_model = FakeEmbeddingModel() ##

        system_event_queue = asyncio.Queue()
        text_utterance_queue = asyncio.Queue()
        #最终输出放到text_audio_queue
        complete_utterance_queue = text_audio_queue

        api_url = "http://127.0.0.1:9880"##
        prompt_text= "等你，我想想，嗯。"
        prompt_lang= "zh"
        ref_wav_path = "/app/XingTong/ref.wav"
        # if  lang_short == "ja":
        #     prompt_text = "いいんじゃない。最近、一緒に歌ってる人の声に合わせられるようになってきたし"
        #     prompt_lang = "ja"
        #     ref_wav_path = "/app/KusanagiNene/ref.wav"

        
        # 2. 初始化各子系统并传递 system_event_queue
        # ai_memory = FakeMemorySystem(embed_model=embed_model, system_event_queue=system_event_queue)
        ####################
        ai_memory = MemorySystem(embed_model=embed_model, system_event_queue=system_event_queue)


        tts_manager =  TTSManager_GPTsovits(
            api_url = api_url, 
            ref_wav_path = ref_wav_path,
            prompt_lang = prompt_lang,
            prompt_text = prompt_text,
            utterance_queue = text_utterance_queue, 
            output_utterance_queue = complete_utterance_queue,
            system_event_queue = system_event_queue
        )

        #创建装载 perception 和cmd的流水线（queue）
        perception_event_queue = asyncio.Queue()
        command_queue = asyncio.Queue()

        #here we do not need to create it, just pass parameter asr_model
        # asr_model = WhisperModel(model_size, device="cuda", compute_type="float16")
        perceptionEngine = PerceptionEngine(perception_event_queue = perception_event_queue, 
                                            system_event_queue=system_event_queue,
                                            asr_model= asr_model
                                            )

        decisionEngine = DecisionEngine(
            perception_event_queue= perception_event_queue,
            command_queue=command_queue,
            system_event_queue=system_event_queue,
        )



        main_en = MainEngine(
            perception_engine= perceptionEngine,
            memory_system=ai_memory,
            decision_engine=decisionEngine,
            tts_engine=tts_manager,
            llm=llm,
            embed_model=embed_model,
            system_event_queue=system_event_queue,
        )

        print("✅Ollama和RAG组件初始化完成。")

        aituber = AItuber(charac_name = "miku",
        main_engine = main_en,
        system_event_queue= system_event_queue ,
        output_utterance_queue = text_utterance_queue,
        custom_context_str = custom_context_str,
        custom_condense_prompt_str = condense_prompt_str, 
        similarity_top_num=5, 
        short_memory_toke_limit=4096)
        
        print("\n\n🎉🎉🎉  AI 系统已完全准备就绪，整装待发！🎉🎉🎉")

        print("开始运行 aituber")
        #task创建时不会被执行，只是被列进执行列表最低层，只有当下一个await时才会被执行  
        await aituber.start()  #使外界可以用await调用
        # await aituber.chat("所以你会唱歌吗")


if __name__ == "__main__":

    aituber = None 
    asyncio.run(AItuber.main(asyncio.Queue()))
    pass
    
    # 在main里面不能使用await
    # asyncio.run(AItuber_novoice.add_token_and_check_sentence(",你怎么样" , "你好！"))
    

#  测试是否在运行时保存保存，在切换窗口时