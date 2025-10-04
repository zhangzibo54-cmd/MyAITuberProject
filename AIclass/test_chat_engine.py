import asyncio
from llama_index.core import VectorStoreIndex, PromptTemplate
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

# 这是一个独立的测试脚本

async def main():
    print("--- 开始一个独立的 ChatEngine 测试 ---")
    
    # 1. 初始化 LLM 和 Embedding 模型
    # 确保你的 Ollama 服务正在运行
    try:
        llm = Ollama(model="llama3", base_url="http://localhost:11434", request_timeout=120.0)
        embed_model = OllamaEmbedding(model_name="bge-m3", base_url="http://localhost:11434")
        print("✅ LLM 和 Embedding 模型初始化成功。")
    except Exception as e:
        print(f"❌ 初始化模型时出错: {e}")
        print("请确保你的 Ollama 服务正在 http://localhost:11434 运行。")
        return

    # 2. 创建一个空的索引（我们只是为了测试 ChatEngine，不需要真实数据）
    index = VectorStoreIndex.from_documents([], embed_model=embed_model)
    print("✅ 空索引创建成功。")

    # 3. 初始化短期记忆
    memory = ChatMemoryBuffer.from_defaults(token_limit=4096)
    print("✅ 短期记忆初始化成功。")

    # 4. 定义和你项目中类似的自定义 Prompt 模板
    # 注意：这里的模板变量 {context_str} 和 {chat_history} 等是 LlamaIndex 内部使用的，必须保留
    custom_context_str = (
        "我们正在进行一次对话。这里有一些可能相关的背景记忆信息：\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n"
        "你正在扮演一个角色：mikumiku。请严格遵守角色设定，并结合上面的背景记忆信息，来回答用户的问题。\n"
        "【mikumiku的核心角色设定(最高指令)】:\n"
        "0. 所有回答【必须】用中文。\n"
        "问题: {query_str}\n"
        "中文回答: "
    )
    custom_context_prompt = PromptTemplate(custom_context_str)

    condense_prompt_str = (
        "请根据以下对话历史和最新的用户问题，生成一个独立的、完整的中文问题。\n"
        "对话历史:\n"
        "---------------------\n"
        "{chat_history}\n"
        "---------------------\n"
        "最新的用户问题: {question}\n"
        "独立的中文问题: "
    )
    custom_condense_prompt = PromptTemplate(condense_prompt_str)
    print("✅ 自定义 Prompt 模板创建成功。")

    # 5. 使用和你项目中完全相同的配置创建 ChatEngine
    chat_engine = index.as_chat_engine(
        llm=llm,
        memory=memory,
        chat_mode="condense_plus_context",
        context_prompt=custom_context_prompt,
        condense_prompt=custom_condense_prompt,
        similarity_top_k=5,
        verbose=True # 打开详细模式，方便观察内部流程
    )
    print("✅ ChatEngine 初始化成功。")

    # 6. 使用简单的字符串进行测试
    print("\n--- 现在，尝试用一个简单的字符串调用 chat_engine.stream_chat() ---")
    user_input = "你好，请用中文介绍一下你自己。"
    
    try:
        response = chat_engine.stream_chat(user_input)
        
        full_text = ""
        print(f"\nAI 回答: ", end="", flush=True)
        for token in response.response_gen:
            print(token, end="", flush=True)
            full_text += token
        
        print("\n\n--- 测试成功！收到了完整响应。---")

    except Exception as e:
        print(f"\n--- 测试失败！在调用 stream_chat 时发生错误 ---")
        # 打印完整的错误信息，包括 traceback
        import traceback
        traceback.print_exc()

import asyncio
from llama_index.llms.ollama import Ollama
from llama_index.core.llms import ChatMessage

async def main2():
    print("--- 开始一个独立的、低级别的 Ollama-LlamaIndex 测试 ---")
    try:
        llm = Ollama(model="llama3", base_url="http://localhost:11434", request_timeout=120.0)
        
        messages = [ChatMessage(role="user", content="你好，请用中文介绍一下你自己。")]
        
        print("\n--- 1. 测试 stream_chat (流式) ---")
        response_stream = llm.stream_chat(messages)
        full_text_stream = ""
        print("AI 流式回答: ", end="", flush=True)
        for r in response_stream:
            full_text_stream += r.delta
            print(r.delta, end="", flush=True)
        print(f"\n流式完整回答: '{full_text_stream}'")

        print("\n--- 2. 测试 achat (非流式异步) ---")
        # achat 是 LlamaIndex 中用于异步非流式调用的标准方法
        response_non_stream = await llm.achat(messages)
        print(f"AI 非流式回答: '{response_non_stream.message.content}'")

    except Exception as e:
        print("\n--- 测试中发生错误 ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main2())

