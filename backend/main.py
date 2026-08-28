from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
import time
from services import log_chat
from dependencies import get_settings
from settings import Settings
from llm import call_llm_multi_turn
from session_store import get_history,add_to_history,clear_history
from retrieve import retrieve_relevant_chunks_advanced
from retrieve import retrieve_relevant_chunks_hybrid
from llm import call_llm_with_tools
from agent_service import ask_agent
from qa_service import rag_chat_stream

# ---------- 模型 ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id:str = Field(default="default")
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


class RetrieveRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=10)


# ---------- FastAPI ----------
app = FastAPI(title="AI-Agent-Learning API", version="0.5.0")

# CORS —— 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from upload import router as upload_router
from retrieve import router as retrieve_router
from rag_router import router as rag_router
app.include_router(upload_router)
app.include_router(retrieve_router)
app.include_router(rag_router)

# ---------- 路由 ----------
@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    config: Settings = Depends(get_settings)  # 注入配置
):
    start = time.time()

    history = get_history(request.session_id)
    messages = history + [{"role":"user","content":request.message}]
    system_prompt = """你是一个严谨且知识渊博的AI助手。
    你的回答应该准确，简洁，有条理。
    如果用户问的问题你不确定，请明确回答“我不确定”，不要编造。
    """

    if request.mood == "sad":
        system_prompt += "\n请用温和共情的语气回答，但保持内容准确。"
    elif request.mood == "happy":
        system_prompt += "\n请用热情积极的语气回答，但保持内容准确。"
    
    answer = await call_llm_multi_turn(
        message=messages,
        system_prompt=system_prompt,
    )

    elapsed = time.time() - start

    add_to_history(request.session_id,"user",request.message)
    add_to_history(request.session_id,"assistant",answer)
    # 异步记录日志（文件写入仍是同步，暂时接受）
    log_chat(request.message, answer, request.session_id)
    
    return ChatResponse(
        reply=answer,
        model=config.model_name,  # 实际模型名
        timestamp=elapsed
    )
@app.delete("/session/{session_id}")
async def clear_session(session_id:str):
    clear_history(session_id)
    return {"status":"cleared","session_id":session_id}

@app.get("/history")
async def history(session_id:str="default"):
    return {"history":get_history(session_id)}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/retrieve_advanced")
async def retrieve_advanced(req: RetrieveRequest):
    results = await retrieve_relevant_chunks_advanced(req.question, req.top_k)
    return {
        "question": req.question,
        "results": results
    }

@app.post("/retrieve_hybrid")
async def retrieve_hybrid(req: RetrieveRequest):
    results = await retrieve_relevant_chunks_hybrid(req.question, req.top_k)
    return {
        "question": req.question,
        "results": results
    }

class ToolChatRequest(BaseModel):
    message:str
    session_id:str = "default"
class ToolChatResponse(BaseModel):
    reply:str
    session_id:str
@app.post("/chat_with_tools",response_model=ToolChatResponse)
async def chat_with_tools(req:ToolChatRequest):
    system_prompt = "你是一个有用的助手，可以调用工具来帮助回答用户的问题"
    message = [{"role":"user","content":req.message}]
    answer = await call_llm_with_tools(message,system_prompt=system_prompt)
    return ToolChatResponse(reply=answer,session_id=req.session_id)

class AgentRequest(BaseModel):
    question:str
    session_id:str = "default"
class AgentResponse(BaseModel):
    answer:str
    session_id:str
@app.post("/agent",response_model=AgentResponse)
async def agent_endpoint(req:AgentRequest):
    answer = await ask_agent(req.question,req.session_id)
    return AgentResponse(answer=answer,session_id=req.session_id)


# ---------- SSE 流式对话 ----------
@app.post("/chat/rag/stream")
async def chat_rag_stream(request: ChatRequest):
    """SSE 流式 RAG 对话端点。返回 text/event-stream。"""
    history = get_history(request.session_id)
    history_with_current = history + [{"role": "user", "content": request.message}]

    async def event_generator():
        full_answer = ""
        async for chunk in rag_chat_stream(request.message, history_with_current):
            # 第一个 chunk 是 JSON 元数据，用特殊 event 类型发送
            if chunk.startswith('{"type"'):
                yield f"event: meta\ndata: {chunk}\n\n"
            else:
                full_answer += chunk
                yield f"data: {chunk}\n\n"
        # 流结束后发送 done 事件
        yield "event: done\ndata: [DONE]\n\n"
        # 存储到会话历史
        add_to_history(request.session_id, "user", request.message)
        add_to_history(request.session_id, "assistant", full_answer)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )