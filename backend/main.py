from fastapi import FastAPI
from pydantic import BaseModel,Field,fiels_validator
import asyncio
import time
import random
from services import log_chat

class ChatRequest(BaseModel):
    message:str = Field(...,min_length=1,max_length=500,description="用户消息")
    mood:str = Field(...,default="happy",description="用户情绪")
    @field_validator("message")
    @classmethod
    def message_not_only_spaces(cls,v:str):
        """自定义验证：消息不能全是空格"""
        if not v.strip():
            raise ValueError("消息不能为空或全为空格")
        return v.strip()
    
class ChatResponse(BaseModel):
    reply:str
    model:str
    timestamp:float

async def mock_llm(message:str, mood:str) -> str:
    """异步模拟LLM调用，内部使用asyncio.sleep模拟I/O延迟"""
    await asyncio.sleep(0.5)


    if"你好" in message:
        return "你好，我是AI助手（模拟版），有什么可以帮助你的？"
    elif "天气" in message:
        return "查询天气功能尚未接入，请等待。"
    else:
        base = random.choice([
            "这是一个好问题，但是当前是模拟版本，无法回答你的问题",
            "答案在风中",
            "我会在未来的版本中认真回答你"
        ])
    if mood == "sad":
        base+="😢"
    else:
        base+="🙂"
    return base
    

app = FastAPI(title="AI-Agent-Learning API",version = "0.2.0")

@app.post("/chat",response_model=ChatResponse)

async def chat(request:ChatRequest):
    """处理用户消息，调用模拟LLM并返回回答"""
    start_time = time.time()

    answer = await mock_llm(request.message, request.mood)

    elapsed = time.time() - start_time

    log_chat(request.message,answer)

    return ChatResponse(
        reply = answer,
        model = "mock-LLM-v0",
        timestamp = elapsed
    )

@app.get("/health")
def health_check():
    return {"status":"ok"}