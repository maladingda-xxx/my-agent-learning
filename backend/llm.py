"""LLM 调用模块 —— 封装对Deepseek API的所有交互"""

import asyncio
import json
from openai import AsyncOpenAI
from settings import settings
from dependencies import get_settings

SYSTEM_PROMPT = """你是一个知识渊博且严谨的AI助手。
你的回答应当：
1.准确、简洁、有条理
2.如果与用户问的问题你不确定，请明确说”我不确定”，不要编造
3.使用中文回答，除非用户使用其他语言提问
"""

def _create_client(config=None):
    cfg = config or settings
    return AsyncOpenAI(
        api_key=cfg.deepseek_api_key,
        base_url=cfg.deepseek_api_base,
    )

async def call_llm(
        user_message:str,
        system_prompt:str=SYSTEM_PROMPT,
        temperature:float=None,
        max_tokens:int=None,
) ->str:
    """调用deepseek api，返回模型的文本回复。
    参数：
        user_message:用户的消息
        system_prrompt:系统提示词
        temperature：温度（默认取settings中的值）
        max_tokens:最大生成tokens数
    返回：
        模型的文本回复
    异常：
        ValueError:API Key无效或未配置
        ConnectionError：网络问题
        Exception：其他API错误
    """

    cfg = get_settings()
    temp = temperature if temperature is not None else cfg.temperature
    max_tok = max_tokens if max_tokens is not None else cfg.max_tokens

    if not cfg.deepseek_api_key or cfg.deepseek_api_key == "sk-placeholder":
        return "错误，请在.env中设置有效的DEEPSEEK_API_KEY"

    client = _create_client(cfg)
    try:
        response = await client.chat.completions.create(
            model=cfg.model_name,
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_message},
            ],
            temperature=temp,
            max_tokens=max_tok,
        )

        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)

        if "401" in error_msg or "Invalid API Key" in error_msg or "AuthenticationError" in error_msg:
            return "错误：API Key 无效，请检查 .env 中的 OPENAI_API_KEY"
        elif "429" in error_msg or "Rate limit" in error_msg:
            return "错误：请求太频繁，请稍后再试"
        elif "timeout" in error_msg.lower():
            return "错误：请求超时，请检查网络连接"
        else:
            return f"错误：API 调用失败 - {error_msg}"
async def call_llm_with_mood(user_message:str, mood:str, model_name:str = None) -> str:
    """根据 mood 调整 system prompt，让回复带情绪色彩。
    这是我们项目特有的封装，演示如何在不同场景复用 call_llm。"""

    mood_prompt = {
        "happy":SYSTEM_PROMPT + "\n请用热情、积极的语气回答，但要保持内容准确。",
        "sad": SYSTEM_PROMPT + "\n请用温和、共情的语气回答，但保持内容准确。",
    }

    prompt = mood_prompt.get(mood,SYSTEM_PROMPT)
    return await call_llm(user_message,system_prompt=prompt)

async def call_llm_multi_turn(
        message:list[dict],
        system_prompt:str=SYSTEM_PROMPT,
        temperature:float=None,
        max_tokens:int=None,
    ) -> str:
    cfg = get_settings()
    temp = temperature if temperature is not None else cfg.temperature
    max_tok = max_tokens if max_tokens is not None else cfg.max_tokens
    if not cfg.deepseek_api_key or cfg.deepseek_api_key == "sk-placeholder":
        return "错误：请在.env中设置有效的DEEPSEEK_API_KEY"

    client = _create_client(cfg)

    full_messages = [{"role":"system","content":system_prompt}] + message
    try:
        response = await client.chat.completions.create(
            model=cfg.model_name,
            messages=full_messages,
            temperature=temp,
            max_tokens=max_tok,
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "AuthenticationError" in error_msg:
            return "错误：API Key无效"
        elif "429" in error_msg or "Rate Limit" in error_msg:
            return "错误：请求太频繁"
        elif "timeout" in error_msg:
            return "错误：请求超时"
        else:
            return f"错误：API 调用失败——{error_msg}"


async def call_llm_json(
        user_message: str,
        system_prompt: str = SYSTEM_PROMPT,
        temperature: float = None,
        max_tokens: int = None,
):
    """调用 LLM 并尝试把返回内容解析为 JSON。

    返回：
        成功解析时返回对应的 dict/list；
        解析失败时返回 {"error": "..."}，由调用方自行降级处理。
    """
    text = await call_llm(
        user_message=user_message,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    cleaned = text.strip()
    # 容错：去掉模型可能包裹的 markdown 代码块（```json ... ```）
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return {"error": f"JSON 解析失败: {text[:200]}"}
        