"""
混合检索模块：结合向量检索和 BM25 关键词检索，使用 RRF 融合
"""
import asyncio
from rank_bm25 import BM25Okapi
import re
from .vector_store import get_all_documents, query_similar
from .embedding import embed_text

def tokenize(text: str) -> list[str]:
    """
    简单分词：提取中文单字和英文单词。
    生产环境建议使用 jieba 等专业分词器。
    """
    # 匹配中文字符，或英文单词/数字
    tokens = re.findall(r'[\u4e00-\u9fa5]|[a-zA-Z0-9]+', text.lower())
    return tokens

def bm25_search(question: str, top_k: int = 5) -> list[dict]:
    """
    使用 BM25 在向量库的所有文档中检索，返回结果列表。
    每个结果包含 id, document, metadata, score (BM25分数)。
    """
    texts, ids, metadatas = get_all_documents()
    if not texts:
        return []

    # 初始化 BM25
    tokenized_corpus = [tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized_corpus)

    query_tokens = tokenize(question)
    scores = bm25.get_scores(query_tokens)

    # 构建结果
    results = []
    for idx, score in enumerate(scores):
        results.append({
            "id": ids[idx],
            "document": texts[idx],
            "metadata": metadatas[idx],
            "score": float(score)
        })
    # 按分数降序
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]

async def hybrid_retrieve(question: str, top_k: int = 3) -> list[dict]:
    """
    混合检索：
    1. 向量检索 -> top_k * 2 候选
    2. BM25 检索 -> top_k * 2 候选
    3. RRF 融合，返回前 top_k
    """
    # 1. 向量检索
    q_embedding = await embed_text(question)
    vector_results = query_similar(q_embedding, top_k=top_k * 2)  # 多取一些

    # 2. BM25 检索
    bm25_results = bm25_search(question, top_k=top_k * 2)

    # 3. RRF 融合
    k = 60  # RRF 常数
    rrf_scores = {}

    # 向量结果打分
    for rank, item in enumerate(vector_results, start=1):
        doc_id = item["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)

    # BM25 结果打分
    for rank, item in enumerate(bm25_results, start=1):
        doc_id = item["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank)

    # 按 RRF 分数排序
    sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

    # 构建最终结果：从原始结果中查找文档内容
    id_to_item = {}
    for item in vector_results + bm25_results:
        id_to_item[item["id"]] = item

    final_results = []
    for doc_id, score in sorted_ids[:top_k]:
        item = id_to_item.get(doc_id)
        if item:
            final_results.append({
                "id": doc_id,
                "document": item["document"],
                "metadata": item["metadata"],
                "rrf_score": score
            })
    return final_results