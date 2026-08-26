"""RAG 对话端点 —— POST /chat/rag"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
import time

from .session_store import get_history, add_to_history
from .services import log_chat
from .dependencies import get_settings
from .settings import Settings
from .qa_service import rag_chat

router = APIRouter(prefix="/chat", tags=["rag"])


class RagChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(default="default")
    top_k: int = Field(default=3, ge=1, le=10)

    @field_validator("message")
    @classmethod
    def message_not_only_spaces(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("消息不能为空或全为空格")
        return v.strip()


class SourceInfo(BaseModel):
    chunk_id: str
    document_preview: str
    source: str | None = None
    page: int | None = None
    distance: float | None = None


class RagChatResponse(BaseModel):
    reply: str
    model: str
    sources: list[SourceInfo] = []
    empty_knowledge_base: bool = False
    timestamp: float


@router.post("/rag", response_model=RagChatResponse)
async def chat_rag(
    request: RagChatRequest,
    config: Settings = Depends(get_settings),
):
    start = time.time()

    # 获取历史并追加当前消息
    history = get_history(request.session_id)
    messages = history + [{"role": "user", "content": request.message}]

    # RAG 编排
    answer, sources, empty_kb = await rag_chat(
        message=request.message,
        history=messages,
        top_k=request.top_k,
    )

    elapsed = time.time() - start

    # 存储对话历史
    add_to_history(request.session_id, "user", request.message)
    add_to_history(request.session_id, "assistant", answer)

    # 记录日志
    log_chat(request.message, answer, request.session_id)

    return RagChatResponse(
        reply=answer,
        model=config.model_name,
        sources=sources,
        empty_knowledge_base=empty_kb,
        timestamp=elapsed,
    )
