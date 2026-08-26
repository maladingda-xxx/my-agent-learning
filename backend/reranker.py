"""
重排序模块 —— 使用 LLM 对候选文档块打分排序
"""
import json
from .llm import call_llm_json

SYSTEM_PROMPT = """你是一名信息检索评估专家。
我会给你一个用户问题，以及若干个候选文档块（编号从 0 开始）。
请对每个候选块与问题的相关性打分，分数为 0 到 10 的整数，10 表示完全相关，0 表示完全不相关。
只输出 JSON 数组，格式： [{"id": 0, "score": 8}, {"id": 1, "score": 3}, ...]
不要输出任何额外文字。"""

async def rerank_chunks(question: str, chunks: list[dict]) -> list[dict]:
    """
    使用 LLM 对 chunks 进行相关性打分，返回按分数降序排序的 chunks
    """
    if not chunks:
        return []

    # 构建候选块文本
    candidates = []
    for i, chunk in enumerate(chunks):
        # 截断前 300 字符用于打分，节省 token
        text = chunk["document"][:300]
        candidates.append(f"[{i}] {text}")

    user_message = f"用户问题：{question}\n\n候选文档块：\n" + "\n".join(candidates)

    result = await call_llm_json(
        user_message=user_message,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.0,
    )

    # 解析打分结果
    scores = {}
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and "id" in item and "score" in item:
                try:
                    idx = int(item["id"])
                    score = float(item["score"])
                    scores[idx] = score
                except (ValueError, TypeError):
                    continue

    # 如果打分失败，保留原始顺序
    if not scores:
        return chunks

    # 为每个 chunk 附上 score，然后排序
    scored_chunks = []
    for i, chunk in enumerate(chunks):
        score = scores.get(i, 0.0)
        scored_chunks.append((score, chunk))

    # 按分数降序
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored_chunks]