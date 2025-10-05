
import chromadb
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import Document

from AIclass.events_class.system_events import LogMessageEvent

import asyncio

class MemorySystem:
    def __init__(self, embed_model, system_event_queue, google_drive_db_path="/app/my_ai_memory/chroma_db"):
        #google_drive_db_path 时长期记忆db储存的位置
        self.db_path = google_drive_db_path

        # embed_model to deal with memory search
        self.embed_model = embed_model

        def init_index():
            db = chromadb.PersistentClient(path=self.db_path)
            chroma_collection = db.get_or_create_collection("long_term_memory")
            #多行数列，第一行是文档，第三行是对应的向量

            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
            #一个基于上述集合collection的书架

            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            #书架的注册系统
            # 创建向量索引，这是LlamaIndex中操作记忆的核心
            # 如果数据库中已有记忆，它会自动加载

            index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=self.embed_model,
            )

            return index

        self.index = init_index()# 先设为None,embedding_model下载好之后再改回来

        # to log
        self.system_event_queue = system_event_queue

    async def init_and_get_index(self):

        "create vector_store, storage_contex and index, then return index"

        db = chromadb.PersistentClient(path=self.db_path)
        chroma_collection = db.get_or_create_collection("long_term_memory")
        #多行数列，第一行是文档，第三行是对应的向量

        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        #一个基于上述集合collection的书架

        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        #书架的注册系统
        # 创建向量索引，这是LlamaIndex中操作记忆的核心
        # 如果数据库中已有记忆，它会自动加载


        index = VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=self.embed_model,
        )
        #s书架的管理员，  storage_context,index都自动关联到同一对象，
        # 当index被调用修改时storage_。。被自动修改
        return index

    async def memorize(self, text_to_remember):
        """
        MemorySystem作用的地方3/3 

        # 将新的文本信息存入长期记忆
        # :param text_to_remember: 需要被记住的字符串
        # """


        # LlamaIndex需要将文本包装成Document对象
        document = Document(text=text_to_remember)
        self.index.insert(document)
        print(f"🧠 新记忆已存入: '{text_to_remember}'")

    async def recall(self, query_text, similarity_top_k=3):
        """
        根据查询文本，从记忆中“回忆”最相关的信息。
        :param query_text: 用于查询的文本。
        :param similarity_top_k: 返回最相似结果的数量。
        :return: 相关记忆的列表。
        """
        retriever = self.index.as_retriever(similarity_top_k=similarity_top_k)
        nodes = await retriever.aretrieve(query_text)
        
        results = []
        if nodes:
            print(f"🧠 根据 '{query_text}' 回忆起以下内容:")
            for node in nodes:
                results.append({'id': node.node.node_id, 'text': node.node.get_content(), 'score': node.score})
                print(f"   - [ID: {node.node.node_id}, Score: {node.score:.4f}]: {node.node.get_content()}")
        else:
            print(f"🧠 对于 '{query_text}'，没有找到相关记忆。")
            
        return results

    async def list_all_memories(self):
        """
        【查看功能】列出数据库中所有已存储的记忆。
        直接从ChromaDB集合中获取数据。
        """
        print("\n--- 📖 查看所有记忆 ---")
        memories = self.chroma_collection.get()
        if not memories['ids']:
            print("   记忆库为空。")
            return None
            
        for i, doc_id in enumerate(memories['ids']):
            text = memories['documents'][i]
            metadata = memories['metadatas'][i]
            print(f" - ID: {doc_id}")
            print(f"   内容: {text}")
            print(f"   元数据: {metadata}")
            print("-" * 10)
        return memories  

    async def forget(self, memory_id):
        """
        【删除功能】根据提供的ID从记忆库中删除一条记忆。
        :param memory_id: 要删除的记忆的唯一ID (可以通过 list_all_memories 获取)。
        """
        try:
            # 直接操作ChromaDB集合进行删除
            self.chroma_collection.delete(ids=[memory_id])
            # 注意：LlamaIndex的索引可能需要重建或更新才能完全同步状态，
            # 但对于ChromaDB后端，直接删除通常是有效的。
            print(f"🗑️ 记忆已删除 (ID: {memory_id})")
            print(f"🗑️ 记忆已删除 (ID: {memory_id})")
        except Exception as e:
            error_msg = f"删除记忆 (ID: {memory_id}) 时出错: {e}"
            print(error_msg)

if __name__ == "__main__":
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.llms.ollama import Ollama
    
    embed_model = OllamaEmbedding(model_name="bge-m3", base_url="http://localhost:11434")##
    system_event_queue = asyncio.Queue()
    ai_memory = MemorySystem(embed_model=embed_model, system_event_queue=system_event_queue)
    asyncio.run(ai_memory.memorize("初音未来又叫miku，是日本著名的虚拟歌姬"))
    asyncio.run(ai_memory.memorize("初音未来又叫miku，是日本著名的虚拟歌姬"))
    





