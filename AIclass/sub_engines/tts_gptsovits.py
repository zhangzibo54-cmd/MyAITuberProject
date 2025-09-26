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
import threading
import queue
import re

###为了再colab环境播放的导入
from IPython.display import Audio, display, clear_output # <-- 关键导入
from io import BytesIO # <-- 关键导入
import time
from pydub import AudioSegment
###

from events_class.system_events import LogMessageEvent
from events_class.system_events import AudioReadyEvent

# read the output from llm(main),
# put the output into the buffer and put in queue when it becomes a sentence(used by main),
# change the queue to generator (continuely run unitil stream finished), to audio and thread
class TTSManager_GPTsovits:

  def __init__(self, api_url: str , ref_wav_path: str, prompt_text: str, prompt_lang: str, system_event_queue:queue.Queue ,sampling_rate = 32000 ,speak = False,lang_short = "zh" ,tts_auto_lang = True):

    # log_queue and audio_queue 会分别接收产生的audio文件和queue文件

    self._audio_queue = queue.Queue()

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
    self._sentence_queue = queue.Queue()
    self._sentence_buffer = ""
    self._sentence_delimiters = re.compile(r'[,，.!?。！？…]')

    # signal of ending
    self._is_running = threading.Event()


    # open one tts thread
    self._working_sentence_thread = None# not self._tts(), other it will directly run
    # self._working_sentence_thread.start()
    self._working_audio_thread = None
    # self._working_audio_thread.start()

    # after this timeout, we will reminder the queue is empty for 10s
    self.queue_empty_timeout = 100


  def start(self):
    self._is_running.set()
    if self._working_audio_thread is None or not self._working_audio_thread.is_alive():
      self._working_audio_thread = threading.Thread(target = self._audio_play)
      self._working_audio_thread.start()
    if self._working_sentence_thread is None or not self._working_sentence_thread.is_alive():
      self._working_sentence_thread = threading.Thread(target = self._tts) # not self._tts(), other it will directly run
      self._working_sentence_thread.start()

    if self.speak:
      self.system_event_queue.put(LogMessageEvent(f"\n tts and audio play started."))

  def _tts(self):
    if self.speak: print("\n start the _tts func")
    while True:

      try:
        sentence = self._sentence_queue.get(timeout = 10) #
        print(f"audio queue长度：{self._audio_queue.qsize()}")
        if self.speak: self.system_event_queue.put(LogMessageEvent(f"✅tts get the sentence:{sentence}"))
        if sentence == None:
          # put None to end the play and reset the signal
          self._audio_queue.put(None)
          if self.speak:self.system_event_queue.put(LogMessageEvent("\n✅end the _tts thread"))
          self._is_running.clear()
          break
        if self.speak:self.system_event_queue.put(LogMessageEvent(f"\n dealing _tts() with sentence : '{sentence.strip()}'"))
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

        # play the audio
        response = requests.post(self.api_url, json=payload, timeout = self.queue_empty_timeout)
        if self.speak:print(f"✅已经发送给tts服务器的参数,url = {self.api_url}, payload = {payload}")
        if self.speak:print(f"其中文本为: {sentence}")

        if response.status_code == 200:
          if self.speak:print("\n✅ 请求成功！服务器已返回有效的音频数据。")
          audio_size = len(response.content)

          # put the audioready event to the sys queue
          audio_bytes = response.content
          audio_data = audio_bytes
          duration_in_seconds = len(audio_data) / (2.1*self.sampling_rate)
          self._audio_queue.put((audio_data, sentence))

          self.system_event_queue.put(AudioReadyEvent(audio_data = audio_data, duration = duration_in_seconds))

          if self.speak: print(f"audio_data的长度：'{len(audio_data)}',此时入列后queue长度{self._audio_queue.qsize()}")
          try:
            output_filename ="miko.wav"
            with open(output_filename,"wb") as f:
              f.write(audio_data)
            # if self.speak:self.system_event_queue.put(LogMessageEvent(f"audio文件已经保存到miko.wav"))
          except IOError as e:
            if self.speak:self.system_event_queue.put(LogMessageEvent(f"audio文件保存失败，{e}"))


        else:
          if self.speak:print("\n ❌请求服务器tts失败")

      except queue.Empty:
        # if self.speak:self.system_event_queue.put(LogMessageEvent(f"sentence_queue has been empty since {self.queue_empty_timeout}s ago ---from _tts()"))
        pass
      except Exception as e:
        # to avoid other errors to destroy the thread
        if self.speak:print(f"❌tts has an error:{e}")
        pass

  def stop(self):
    # stop two threads
    if self._is_running.is_set():
      self._sentence_queue.put(None)
      self._is_running.clear()
    # self.system_event_queue.put(LogMessageEvent("\n stop the tts engine"))

  def _audio_play(self):
    while True:

      print("audio_play is running")
      try:


        audio_sentence = self._audio_queue.get(timeout = self.queue_empty_timeout)

        if audio_sentence == None:
          if self.speak:print("None!!!✅audio_play thread is over")
          break
        else:
          if self.speak: print(f"语言文本对的长度为 {len(audio_sentence)}")
        audio_data = audio_sentence[0]
        if self.speak:print("✅已经从audio queue中取出audio data")
         # ElevenLabs 默认输出 mp3，所以 format="mp3"
        #####
        #we just need to change the following to change the paly device of voice
        try:
          duration_in_seconds = len(audio_data) / (2.1*self.sampling_rate)

          # print(f"[INFO] 本句音频时长: {duration_in_seconds:.2f} 秒")
          # 3. 播放音频 (autoplay=True)
          # clear_output(wait=True)
          display(Audio(data=audio_data,rate= self.sampling_rate, autoplay=True))

          # 4. 【关键】暂停代码，等待音频播放完毕
          # 可以增加一点点缓冲时间，比如 0.5 秒
          if self.speak:print(f"\n播放的音频段的长度：{duration_in_seconds}")
          if self.speak:print(f"播放视频的文本{audio_sentence[1]}\n")
          time.sleep(duration_in_seconds)
        except Exception as e:
          if self.speak:print(f"确认声音长度或者播放时出现错误，{e}")

        ####
      except queue.Empty:
        if self.speak:print(f"audio queue has been empty since {self.queue_empty_timeout}s ago. ---from _audio_play()")
        pass
      # to avoid other errors to destroy the thread
      except Exception as e:
        if self.speak:print(f"❌audio_play has an error:{e}")
        pass




  def add_next_chunk(self, token):
    # put the output into the buffer and put in queue when it becomes a sentence(used by main),
    self._sentence_buffer += token
    # print(f"self_buffer{self._sentence_buffer}")
    matching = self._sentence_delimiters.search(self._sentence_buffer)

    if matching:

      print("add_next_chunk ",end =" ")
      print(f"self_buffer: {self._sentence_buffer}")
      #put the sentence to queue
      sentence = self._sentence_buffer[:matching.end()]
      self._sentence_queue.put(sentence)
      # delete the sentence put from buffer
      self._sentence_buffer = self._sentence_buffer[matching.end():]
      # if self.speak:self.system_event_queue.put(LogMessageEvent(f"✅ A sentence with length of {matching.end()} is added. The sentence: {sentence}"))
      print(f"\n_is_running.is_set()为{self._is_running.is_set()}")

      if not self._is_running.is_set():
        self.start()
        print("start the tts")


  def finish_streaming(self):
    # put the remaining things in buffer to queue
    if self._sentence_buffer.strip():
      self._sentence_queue.put(self._sentence_buffer)
    # end the _sentence_iterator()
    if self._is_running.is_set():
      self._sentence_queue.put(None)
    #fistly wait for the end of all sentence to generator, secondly
    self._working_sentence_thread.join()
    self._working_audio_thread.join()
