from fastapi import APIRouter, HTTPException, Query

from embedding import embed_text
from vector_store import query_similar

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
