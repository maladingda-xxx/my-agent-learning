"""将文本转换成向量"""

from .dependencies import get_settings
from openai import AsyncOpenAI
async def embed_text(text:str) -> list[float]:
    cfg = get_settings()
    client = AsyncOpenAI(
        api_key=cfg.deepseek_api_key,
        base_url=cfg.deepseek_api_base,
    )
    response = await client.embeddings.create(
        model="deepseek-embedding-v1",
        input=[text]
    )
    return response.data[0].embedding

async def embed_documents(texts:list[str]) -> list[list[float]]:
    cfg = get_settings()
    client = AsyncOpenAI(
        api_key=cfg.deepseek_api_key,
        base_url=cfg.deepseek_api_base,
    )
    response = await client.embeddings.create(
        model="deepseek-embedding-v1",
        input=texts,
    )
    return [item.embedding for item in response.data]

