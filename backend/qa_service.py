"""RAG 对话编排模块 —— embed查询 → 检索Chroma → 构建prompt → 调用LLM"""

from embedding import embed_text
from vector_store import query_similar, collection
from llm import call_llm_multi_turn, call_llm_stream


RAG_SYSTEM_PROMPT = """你是一个严谨且知识渊博的AI助手。请根据以下从文档中检索到的相关信息回答用户的问题。

## 检索到的文档片段
{context}

## 回答规则
1. 优先基于上述文档片段回答问题，确保回答准确、有据可查
2. 如果文档片段中包含答案，请引用来源（标注文档名称或片段编号）
3. 如果文档片段信息不足以回答问题，请明确说明"根据现有文档，无法确定答案"，然后可以结合你的通用知识补充说明
4. 不要编造文档中不存在的信息
5. 使用中文回答，除非用户使用其他语言提问
"""

FALLBACK_SYSTEM_PROMPT = """你是一个严谨且知识渊博的AI助手。

注意：当前知识库中没有已上传的文档，请基于你的通用知识回答用户的问题。

## 回答规则
1. 准确、简洁、有条理
2. 如果你不确定，请明确说"我不确定"，不要编造
3. 使用中文回答，除非用户使用其他语言提问
"""


def format_context(results: list[dict]) -> str:
    """将检索结果格式化为 prompt 中的上下文文本"""
    parts = []
    for i, r in enumerate(results, 1):
        doc_text = r.get("document", "")
        metadata = r.get("metadata", {})
        source = metadata.get("source", "未知")
        page = metadata.get("page", "")
        page_info = f" (第{page}页)" if page else ""
        parts.append(f"[片段{i}] 来源: {source}{page_info}\n{doc_text}")
    return "\n\n".join(parts)


def format_sources(results: list[dict]) -> list[dict]:
    """将检索结果格式化为 API 响应中的 sources 字段"""
    sources = []
    for r in results:
        doc_text = r.get("document", "")
        metadata = r.get("metadata", {})
        sources.append({
            "chunk_id": r.get("id", ""),
            "document_preview": doc_text[:200] if doc_text else "",
            "source": metadata.get("source"),
            "page": metadata.get("page"),
            "distance": r.get("distance"),
        })
    return sources


async def rag_chat(
    message: str,
    history: list[dict],
    top_k: int = 3,
):
    """
    RAG 对话编排核心函数。

    参数:
        message: 当前用户消息
        history: 完整的对话历史（包含当前用户消息）
        top_k: 检索返回的文档片段数

    返回:
        (answer, sources, empty_knowledge_base)
    """
    # 1. 检查知识库是否为空
    doc_count = collection.count()
    empty_kb = doc_count == 0

    # 2. 检索相关文档
    sources = []
    if not empty_kb:
        try:
            query_embedding = await embed_text(message)
            results = query_similar(query_embedding, top_k)
            context_text = format_context(results)
            sources = format_sources(results)
            system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)
        except Exception:
            # 检索失败时降级为空知识库模式
            system_prompt = FALLBACK_SYSTEM_PROMPT
            empty_kb = True
            sources = []
    else:
        system_prompt = FALLBACK_SYSTEM_PROMPT

    # 3. 调用 LLM
    answer = await call_llm_multi_turn(
        message=history,
        system_prompt=system_prompt,
    )

    return answer, sources, empty_kb


async def rag_chat_stream(
    message: str,
    history: list[dict],
    top_k: int = 3,
    model: str = None,
    api_key: str = None,
    api_base: str = None,
):
    """
    RAG 对话的流式版本。
    先做检索（同步完成），然后流式生成回答。

    yield 的内容:
        - 首先 yield 一个 JSON 元数据行（sources、empty_kb 信息）
        - 之后逐 token yield 文本片段
    """
    import json as _json

    # 1. 检查知识库是否为空
    doc_count = collection.count()
    empty_kb = doc_count == 0

    # 2. 检索相关文档
    sources = []
    if not empty_kb:
        try:
            query_embedding = await embed_text(message)
            results = query_similar(query_embedding, top_k)
            context_text = format_context(results)
            sources = format_sources(results)
            system_prompt = RAG_SYSTEM_PROMPT.format(context=context_text)
        except Exception:
            system_prompt = FALLBACK_SYSTEM_PROMPT
            empty_kb = True
            sources = []
    else:
        system_prompt = FALLBACK_SYSTEM_PROMPT

    # 3. 先 yield 元数据（前端据此显示来源信息）
    meta = {"type": "meta", "sources": sources, "empty_kb": empty_kb}
    yield _json.dumps(meta, ensure_ascii=False)

    # 4. 流式生成回答
    async for token in call_llm_stream(
        messages=history,
        system_prompt=system_prompt,
        model=model,
        api_key=api_key,
        api_base=api_base,
    ):
        yield token
