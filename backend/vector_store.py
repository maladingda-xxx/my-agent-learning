"""
向量数据库模块 —— 使用 Chroma
"""
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import os

# Chroma 数据持久化目录
CHROMA_DIR = "data/chroma_db"

# 初始化 Chroma 客户端（持久化模式）
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# 获取或创建集合（类似 SQL 中的表）
# 使用内嵌的 embedding 函数（仅作标识，实际我们不使用它生成向量）
collection = chroma_client.get_or_create_collection(
    name="knowledge_base",
    metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
)

def add_documents(docs: list[dict], embeddings: list[list[float]], doc_ids: list[str]):
    """
    将文档块、向量和元数据插入 Chroma
    docs: list of chunk dicts (包含 text 和 metadata)
    embeddings: 对应向量列表
    doc_ids: 唯一 ID 列表
    """
    # 准备数据
    texts = [doc["text"] for doc in docs]
    metadatas = [doc["metadata"] for doc in docs]

    collection.add(
        ids=doc_ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

def query_similar(query_embedding: list[float], top_k: int = 3) -> list[dict]:
    """
    根据查询向量返回最相似的 top_k 个文档
    返回格式: [{"id": ..., "document": ..., "metadata": ..., "distance": ...}]
    """
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
    # 重组为友好的列表
    output = []
    if results["ids"] and len(results["ids"][0]) > 0:
        for i in range(len(results["ids"][0])):
            output.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
    return output

def get_all_documents() -> tuple[list[str], list[str], list[dict]]:
    """
    获取集合中所有文档的文本、id 和 metadata。
    返回: (texts, ids, metadatas)
    """
    data = collection.get()
    texts = data.get("documents", [])
    ids = data.get("ids", [])
    metadatas = data.get("metadatas", [])
    return texts, ids, metadatas