from fastapi import FastAPI, Depends
from pydantic import BaseModel, Field, field_validator
import asyncio
import random
import time
from services import log_chat, read_recent_logs
from dependencies import get_settings
from settings import Settings

# ---------- 模型 ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    mood: str = Field(default="happy")

    @field_validator("message")
    @classmethod
    def message_not_only_spaces(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("消息不能为空或全为空格")
        return v.strip()

class ChatResponse(BaseModel):
    reply: str
    model: str
    timestamp: float

# ---------- 模拟 LLM（明天会替换为真实异步调用） ----------
async def mock_llm(message: str, mood: str, model_name: str) -> str:
    """接收配置中的模型名，虽然目前只是展示"""
    await asyncio.sleep(0.3)
    if "你好" in message:
        base = f"你好！我是 {model_name}（模拟版）"
    else:
        base = random.choice(["这是个好问题。", "收到。", "我在思考……"])
    return base + (" 😢" if mood == "sad" else " 😊")

# ---------- FastAPI ----------
app = FastAPI(title="AI-Agent-Learning API", version="0.3.0")

# ---------- 路由 ----------
@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    config: Settings = Depends(get_settings)  # 注入配置
):
    start = time.time()
    answer = await mock_llm(request.message, request.mood, config.model_name)
    elapsed = time.time() - start
    
    # 异步记录日志（文件写入仍是同步，暂时接受）
    log_chat(request.message, answer)
    
    return ChatResponse(
        reply=answer,
        model=config.model_name,  # 实际模型名
        timestamp=elapsed
    )

@app.get("/history")
async def history(n: int = 5, config: Settings = Depends(get_settings)):
    lines = read_recent_logs(config.chat_history_max_retrieve)
    return {"history": lines[-n:]}

@app.get("/health")
def health():
    return {"status": "ok"}