"""
查询改写模块 —— 使用 LLM 生成多个搜索查询
"""
from .llm import call_llm_json

SYSTEM_PROMPT = """你是一个搜索查询优化专家。
用户会给你一个自然语言问题，请你生成 {num_queries} 个不同的搜索查询。
这些查询应该从不同角度描述该问题，以便在向量数据库中找到最相关的文档块。
只输出 JSON 数组，不要加任何额外文字。
"""

async def rewrite_queries(question: str, num_queries: int = 3) -> list[str]:
    """
    使用 LLM 生成多个改写后的查询
    """
    system_prompt = SYSTEM_PROMPT.format(num_queries=num_queries)
    user_message = f"问题：{question}"
    result = await call_llm_json(
        user_message=user_message,
        system_prompt=system_prompt,
        temperature=0.3,
    )
    if isinstance(result, dict) and "error" in result:
        # 如果解析失败，降级为原始问题
        return [question]
    if isinstance(result, list):
        # 确保至少包含原始问题
        queries = [q for q in result if isinstance(q, str) and q.strip()]
        if not queries:
            return [question]
        return queries
    return [question]