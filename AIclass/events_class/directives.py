# 文件名: directives.py
# 作用: 定义服务器与客户端之间的通信协议 (语言合同)。

# --- 指令类型 (Directive Types) ---
# 这是一个“词汇表”，定义了所有合法的指令类型
TYPE_TEXT_CHUNK = "TEXT_CHUNK"         # AI生成的文本块 (用于字幕)
TYPE_AUDIO_CHUNK = "AUDIO_CHUNK"       # AI生成的音频块 (用于播放)
TYPE_ACTION_FINISHED = "ACTION_FINISHED" # AI一句话说完的信号
TYPE_ANIMATION = "ANIMATION"           # AI要做的动作指令

# ---
# 在代码中，我们将手动创建符合这些规范的字典，然后将其序列化为JSON。
#
# 示例结构:
#
# {"type": "TEXT_CHUNK", "id": "uuid-123", "data": "你好呀！"}
# {"type": "AUDIO_CHUNK", "id": "uuid-123", "data": "base64..."}
# {"type": "ANIMATION", "name": "wave_hand"}
#