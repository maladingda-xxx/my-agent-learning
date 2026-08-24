from fastapi import APIRouter, HTTPException, Query
from reranker import rerank_chunks
from embedding import embed_text
from vector_store import query_similar
from query_rewriter import rewrite_queries
from hybrid_retriever import hybrid_retrieve

router = APIRouter(prefix="/retrieve", tags=["retrieve"])


@router.get("/")

async def retrieve(query: str = Query(..., min_length=1, description="检索查询文本")):
    try:
        query_embedding = await embed_text(query)
    except Exception as e:
        raise HTTPException(500, f"Embedding failed: {e}")

    results = query_similar(query_embedding)

    return {
        "query": query,
        "num_results": len(results),
        "results": results,
    }


async def retrieve_relevant_chunks(question: str, top_k: int = 3) -> list[dict]:
    """原始简单检索：仅用向量相似度"""
    q_embedding = await embed_text(question)
    results = query_similar(q_embedding, top_k=top_k)
    return results
async def retrieve_relevant_chunks_advanced(question: str, top_k: int = 3) -> list[dict]:
    """
    高级检索：查询改写 + 多查询合并 + LLM 重排序
    """
    # 1. 生成 3 个改写查询
    queries = await rewrite_queries(question, num_queries=3)
    # 2. 对每个查询检索 top_k * 2 个候选（先多取一些）
    candidates = []
    seen_ids = set()
    for q in queries:
        q_embedding = await embed_text(q)
        results = query_similar(q_embedding, top_k=top_k * 2)
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)
    # 3. LLM 重排序
    reranked = await rerank_chunks(question, candidates)
    # 4. 返回前 top_k 个
    return reranked[:top_k]

async def retrieve_relevant_chunks_hybrid(question: str, top_k: int = 3) -> list[dict]:
    """混合检索接口"""
    return await hybrid_retrieve(question, top_k)