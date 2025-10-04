#这里的线程，我们把所有有输入输出都用while True来和queue.get来监听，利用queue来互相传递数据，
#当想要结束时在queue末尾放入None就行,这样后续的第一个在处理玩queue之后才能结束，防止未处理玩就结束的情况
#queue.get()会阻塞线程，并且在听到None时手动break结束线程

# 定义tts类，语音系统的实

#这里的线程，我们把所有有输入输出都用while True来和queue.get来监听，利用queue来互相传递数据，
#当想要结束时在queue末尾放入None就行,这样后续的第一个在处理玩queue之后才能结束，防止未处理玩就结束的情况
#queue.get()会阻塞线程，并且在听到None时手动break结束线程

# 定义tts类，语音系统的实

# model_id = "eleven_multilingual_v2"
# voice_id = "XJ2fW4ybq7HouelYYGcL"
#设置api key
# import os
# # "YOUR_ELEVENLABS_API_KEY" 替换为自己的密钥
# os.environ["ELEVEN_API_KEY"] = "sk_b6d8da12b5221361400f576582a52833eed4afdc1b9f2700"
# TEST_API_KEY = "sk_b6d8da12b5221361400f576582a52833eed4afdc1b9f2700"

import requests
import asyncio

from io import BytesIO # <-- 关键导入
import time
# from pydub import AudioSegment
###

from AIclass.events_class.system_events import LogMessageEvent
from AIclass.events_class.system_events import AudioReadyEvent
from AIclass.events_class.utterance import UtteranceChunk
# read the output from llm(main),
# put the output into the buffer and put in queue when it becomes a sentence(used by main),
# change the queue to generator (continuely run unitil stream finished), to audio and thread
class TTSManager_GPTsovits:

  def __init__(self, 
    api_url: str , 
    ref_wav_path: str, 
    prompt_text: str, 
    prompt_lang: str, 
    utterance_queue:asyncio.Queue,
    output_utterance_queue: asyncio.Queue,
    system_event_queue:asyncio.Queue ,
    sampling_rate = 32000,
    speak = True,
    lang_short = "zh" ,
    tts_auto_lang = True,
    ):

    # log_queue and audio_queue 会分别接收产生的audio文件和queue文件

    self.utterance_queue = utterance_queue
    self.output_utterance_queue = output_utterance_queue 
    self.current_utterance = None

    self.api_url = api_url.strip('/') # 主推理端点

    # 当其为falses时会禁用所有print
    self.speak = speak

    # 保存参考音频信息，用于每次请求
    self.ref_wav_path = ref_wav_path
    self.prompt_text = prompt_text
    self.prompt_lang = prompt_lang
    if tts_auto_lang == True:
      self.text_lang = "auto"
    else:
      self.text_lang = lang_short

    # to record the system_event including LogMessage and AudioReady
    self.system_event_queue = system_event_queue

    self.sampling_rate = sampling_rate

    # to put the output into the buffer and put in queue when meet with some marks(used by main)

    # signal of ending
    self._is_running = asyncio.Event()

    # open one tts thread

    # self._working_sentence_thread.start()
    self._working_audio_task = None
    # self._working_audio_thread.start()

    # after this timeout, we will reminder the queue is empty for 10s
    self.queue_empty_timeout = 100


  async def start(self): 
    if self._working_audio_task is None or not self._working_audio_task.done():
      self._is_running.set()
      self._working_audio_task =  asyncio.create_task(self._tts())
      # while self._is_running.is_set():
      #     await asyncio.sleep(1)
      #     print(f"待处理文本queue长度{self.utterance_queue.qsize()}")  
      #当我们引入这一段时会阻塞任何还ａｗａｉｔ　gather之后的操作　别忘了我们使用await启动的start
      #在实际考虑中我们可以把await看作一个把后面的整个函数连同整个await拿过来的操作
      #而creat_task看作单开一个线程


    if self.speak:
      print(f"\n tts started.")

  async def _tts(self):
    if self.speak: print("\n 开启了 _tts ")
    while self._is_running.is_set():
      # print("进入了tts的循环")
      try:
        self.current_utterance = await asyncio.wait_for(self.utterance_queue.get(), timeout=2) #
        sentence = self.current_utterance.text
        print(f"utterance queue长度：{self.utterance_queue.qsize()}")
        if self.speak: print(f"✅tts get the sentence:{sentence}")

        # tts and it will not block the following codes

        payload = {
                      "refer_wav_path": self.ref_wav_path,
                      "prompt_text": self.prompt_text,
                      "prompt_language": self.prompt_lang,
                      "text": sentence,
                      "text_language": self.text_lang # 假设Miko主要说中文
              }
        # print(f"self.prompt_lang{self.prompt_lang}")
        if self.speak:print(f"👉将要发送给tts服务器的参数,url = {self.api_url}, payload = {payload}")
        if self.speak:print(f"其中文本为: {sentence}")
        response = await asyncio.to_thread( requests.post, self.api_url, json=payload, timeout = self.queue_empty_timeout)
        
        # test by using fake model
        # from AIclass.mock_model import FakeTTSRes
        # response = FakeTTSRes()

        if self.speak:print(f"✅已经发送给tts服务器的参数,url = {self.api_url}, payload = {payload}")
        if self.speak:print(f"其中文本为: {sentence}")
        
        if response.status_code == 200:
          if self.speak:print("\n✅ 请求成功！服务器已返回有效的音频数据。")
          audio_size = len(response.content)
          # put the audioready event to the sys queue
          audio_data = response.content
          duration_in_seconds = len(audio_data) / (2.1*self.sampling_rate)
          self.current_utterance.audio_data = audio_data
          self.output_utterance_queue.put_nowait(self.current_utterance)
          if self.speak: print(f"audio_data的长度：'{len(audio_data)}',此时入列后output queue长度{self.output_utterance_queue.qsize()}")

          try:
            output_filename ="miko.wav"
            with open(output_filename,"wb") as f:
              f.write(audio_data)
            # if self.speak:self.system_event_queue.put(LogMessageEvent(f"audio文件已经保存到miko.wav"))
          except IOError as e:
            if self.speak:self.system_event_queue.put(LogMessageEvent(f"audio文件保存失败，{e}"))


        else:
          if self.speak:print("\n ❌请求服务器tts失败")
      except asyncio.TimeoutError:
                # print(f"2秒内perception_event_queue没有接收到事件,text utterance queue长度{self.utterance_queue.qsize()}")
                pass
      except Exception as e:
        # to avoid other errors to destroy the thread
        if self.speak:print(f"❌tts has an error:{e}")
        

  async def stop(self):
    # stop two threads
    if self._is_running.is_set():
        self._is_running.clear()
        print(f"停止tts,还有{utterance_queue.qsize()}个未处理")
        # self.system_event_queue.put(LogMessageEvent("\n stop the tts engine"))

  # def _audio_play(self):
  #   while True:

  #     print("audio_play is running")
  #     try:


  #       audio_sentence = self._audio_queue.get(timeout = self.queue_empty_timeout)

  #       if audio_sentence == None:
  #         if self.speak:print("None!!!✅audio_play thread is over")
  #         break
  #       else:
  #         if self.speak: print(f"语言文本对的长度为 {len(audio_sentence)}")
  #       audio_data = audio_sentence[0]
  #       if self.speak:print("✅已经从audio queue中取出audio data")
  #        # ElevenLabs 默认输出 mp3，所以 format="mp3"
  #       #####
  #       #we just need to change the following to change the paly device of voice
  #       try:
  #         duration_in_seconds = len(audio_data) / (2.1*self.sampling_rate)

  #         # print(f"[INFO] 本句音频时长: {duration_in_seconds:.2f} 秒")
  #         # 3. 播放音频 (autoplay=True)
  #         # clear_output(wait=True)
  #         display(Audio(data=audio_data,rate= self.sampling_rate, autoplay=True))

  #         # 4. 【关键】暂停代码，等待音频播放完毕
  #         # 可以增加一点点缓冲时间，比如 0.5 秒
  #         if self.speak:print(f"\n播放的音频段的长度：{duration_in_seconds}")
  #         if self.speak:print(f"播放视频的文本{audio_sentence[1]}\n")
  #         time.sleep(duration_in_seconds)
  #       except Exception as e:
  #         if self.speak:print(f"确认声音长度或者播放时出现错误，{e}")

  #       ####
  #     except queue.Empty:
  #       if self.speak:print(f"audio queue has been empty since {self.queue_empty_timeout}s ago. ---from _audio_play()")
  #       pass
  #     # to avoid other errors to destroy the thread
  #     except Exception as e:
  #       if self.speak:print(f"❌audio_play has an error:{e}")
  #       pass




  # def add_next_chunk(self, token):
  #   # put the output into the buffer and put in queue when it becomes a sentence(used by main),
  #   self._sentence_buffer += token
  #   # print(f"self_buffer{self._sentence_buffer}")
  #   matching = self._sentence_delimiters.search(self._sentence_buffer)

  #   if matching:

  #     print("add_next_chunk ",end =" ")
  #     print(f"self_buffer: {self._sentence_buffer}")
  #     #put the sentence to queue
  #     sentence = self._sentence_buffer[:matching.end()]
  #     self._sentence_queue.put(sentence)
  #     # delete the sentence put from buffer
  #     self._sentence_buffer = self._sentence_buffer[matching.end():]
  #     # if self.speak:self.system_event_queue.put(LogMessageEvent(f"✅ A sentence with length of {matching.end()} is added. The sentence: {sentence}"))
  #     print(f"\n_is_running.is_set()为{self._is_running.is_set()}")

  #     if not self._is_running.is_set():
  #       self.start()
  #       print("start the tts")


  # def finish_streaming(self):
  #   # put the remaining things in buffer to queue
  #   if self._sentence_buffer.strip():
  #     self._sentence_queue.put(self._sentence_buffer)
  #   # end the _sentence_iterator()
  #   if self._is_running.is_set():
  #     self._sentence_queue.put(None)
  #   #fistly wait for the end of all sentence to generator, secondly
  #   self._working_sentence_thread.join()
  #   self._working_audio_thread.join()


if __name__ == "__main__":
  api_url = ""
  ref_wav_path = ""
  prompt_lang = "zh"
  prompt_text ="wait"

  utterance_queue = asyncio.Queue()
  output_utterance_queue = asyncio.Queue()
  system_event_queue = asyncio.Queue()

  tts = TTSManager_GPTsovits(api_url = api_url, ref_wav_path = ref_wav_path,prompt_lang = prompt_lang,
  prompt_text = prompt_text,
  utterance_queue = utterance_queue, 
  output_utterance_queue = output_utterance_queue,system_event_queue = system_event_queue)
  utterance_queue.put_nowait(UtteranceChunk("你好"))
  utterance_queue.put_nowait(UtteranceChunk("你好"))
  utterance_queue.put_nowait(UtteranceChunk("你好"))
  try:
    asyncio.run( tts.start() )
  except KeyboardInterrupt:
    pass