
import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.llms.ollama import Ollama
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import PromptTemplate

import threading
import queue
import time

from AIclass.main_engine import MainEngine
from events_class.commands import Command
from events_class.system_events import LogMessageEvent
from events_class.system_events import AudioReadyEvent
from events_class.system_events import TextChunkEvent

# AItueber类

class AItuber:
    def __init__( self,
            main_engine: MainEngine,
            system_event_queue: queue.Queue,
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

        # thread
        self._is_running  = threading.Event()
        self.consciousness_thread = None

        #record the time and add the unplaying music to audio_queue
        self.last_audio_start_time = time.time()
        self._audio_duration = 0
        self._audio_queue = queue.Queue()

        #提示模板
        custom_context_prompt = PromptTemplate(custom_context_str)

        # --- 2. 为“问题压缩”步骤创建强制中文模板 ---
        # 这个模板确保AI在“思考”和“改写问题”时也使用中文

        custom_condense_prompt = PromptTemplate(custom_condense_prompt_str)


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


    def memorize(self, text_to_remember):
        #实现记忆
        self.memory_system.memorize(text_to_remember)

    def start(self):
        self.main_engine.start_all_services() # 全引擎启动包括了perceptionn UI的创建 再主线程里创建UI
        # 启动子线程来运行意识循环
        if not self.consciousness_thread or not self.consciousness_thread.is_alive():
            self._is_running.set()
            self.consciousness_thread = threading.Thread(
                target=self.consciousness_loop,
                 # 设置为守护线程，主程序退出时自动终止
            )
            self.consciousness_thread.start()
            print("AI意识循环已在后台启动。")

    def consciousness_loop(self):

      '''
      先启动其他引擎，
      每一秒，接收来自decision_queue（会被decision_不断处理）的指令，分别为聊天和停止进行不同反应
      当收到停止指令或者发生未知错误（非 空queue错误）时，结束进程（clear flag）并停止所有引擎
      '''
      self.system_event_queue.put(LogMessageEvent(f"开始执行意识流！！！"))
      self._is_running.set()
      self.main_engine.start_all_services()
      while self._is_running.is_set():
        # self.system_event_queue.put(LogMessageEvent("正在意识流loop中"))
        # print("意识流正在工作")
        try:
          # deal with different commands

          self.command = self.command_queue.get_nowait()
          self.execute_command(self.command)
          print(f"执行了一个命令：{self.command.type}")
          pass
        except queue.Empty:
          pass
        except Exception as e:
          self.system_event_queue.put(LogMessageEvent(f"意识loop执行命令时发生错误：{e}"))
          self.stop_consciousness_loop()
          break
        try:
          # deal with system_event. (play the audio, log the print() content in the thread)
          system_event = self.system_event_queue.get_nowait()
          self.handle_system_event(system_event)

        except queue.Empty:
          pass
        except Exception as e:
          print(f"意识loop在处理系统事件时发生错误：{e}")
          self.stop_consciousness_loop()
          break

        # self.play_audio_in_queue() # abandon temporarily
        time.sleep(1)


    def stop_consciousness_loop(self):
      self._is_running.clear()
      self.main_engine.stop_all_services()
      print("stop the consciousness flow")

    def execute_command(self,command):
        '''
        you need to avoid the empty of command queue
        get the command, and exectue it according to its type
        '''
        if command.type == "CHAT":
          # daemon=True 意味着当主程序退出时，这个线程也会跟着退出
          self.system_event_queue.put(LogMessageEvent(f"💬{self.charac_name}: {command.type}"))
          print("\n begin to chat:=====================")
          chat_thread = threading.Thread(target=self.chat, kwargs={ 'user_message': command.data,
                                         'in_consciousness_loop': True,
                                          'is_print' : True
                                                        })
          chat_thread.start()
          # print("\n end chat")
        elif command.type == "STOP":
          self.stop_consciousness_loop()
          pass
        elif command.type == "MEMORIZE":
          self.memorize(command.data)
        else:
          print(f"Unknown command type: {command.type}")


    def handle_system_event(self, system_event):
        # print("正在处理系统事件")
        if system_event.type == "LOG_MESSAGE":
          # print(system_event.message)
          pass
          '''use print here'''
        elif system_event.type == "AUDIO_READY":
          self._audio_queue.put((system_event.audio_data,system_event.duration))
          if system_event.audio_data == None:
            print("alert!!!!None type of audio")
          else:
            print(f"safe, the length of audio data is {len(system_event.audio_data)}")
        elif system_event.type == "TEXT_CHUNK":
          print(system_event.type)
          pass
          # print("now the system_event type is TEXT_CHUNK")
        else:
          print(f"Unknown system event type: {system_event.type}")

    def play_audio_in_queue(self):

      current_time = time.time()
      # 检查上一段音频是否播放完毕
      if (current_time - self.last_audio_start_time) >= self._audio_duration and not self._audio_queue.empty():
        audio_data, duration = self._audio_queue.get_nowait()
        # 在主线程中播放音频
        print(f"\n开始播放音频,time duration: {duration}")
        display(Audio(data=audio_data, autoplay=True))

        # 更新状态变量
        self._audio_duration = duration
        self.last_audio_start_time = current_time

    def chat(self, user_message: str,  in_consciousness_loop = False,is_print = False,) -> str:
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
        self.system_event_queue.put(LogMessageEvent(f"💬{self.charac_name}: {full_response_text}"))
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

                self.system_event_queue.put(LogMessageEvent(f"    '{content}'"))
                if is_print:
                  print(f"    '{content}'")
        else:
            print("  - 本次回答主要依赖短期记忆或通用知识，未直接引用长期记忆。")
            if is_print:
              print("  - 本次回答主要依赖短期记忆或通用知识，未直接引用长期记忆。")

        print("="*50)

        # 返回AI的完整回答，可用于后续处理（如存入日志、语音合成等）
        return full_response_text


