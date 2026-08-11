import uuid
from pathlib import Path
import shutil

from fastapi import APIRouter, UploadFile, File, HTTPException

from documents import load_document, split_documents, save_chunks_to_json
from embedding import embed_documents
from vector_store import add_documents

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = Path("data/uploads")
CHUNKS_DIR = Path("data/chunks")


@router.post("/")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file selected")

    # 保存上传文件
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 加载文档
    try:
        docs = load_document(str(file_path))
    except Exception as e:
        raise HTTPException(500, f"Failed to load document: {e}")

    # 切割
    chunks = split_documents(docs)

    # 保存 chunks JSON
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    base_name = Path(file.filename).stem
    chunk_file = CHUNKS_DIR / f"{base_name}_chunks.json"
    save_chunks_to_json(chunks, str(chunk_file))

    # 向量化并存入 Chroma
    texts = [chunk["text"] for chunk in chunks]
    doc_ids = [str(uuid.uuid4()) for _ in chunks]

    try:
        embeddings = await embed_documents(texts)
    except Exception as e:
        raise HTTPException(500, f"Embedding failed: {e}")

    add_documents(chunks, embeddings, doc_ids)

    return {
        "filename": file.filename,
        "num_documents": len(docs),
        "num_chunks": len(chunks),
        "chunk_file": str(chunk_file),
        "vectorized": True,
    }
