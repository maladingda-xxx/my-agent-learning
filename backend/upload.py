from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
from documents import load_document, split_documents, save_chunks_to_json

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
    
    return {
        "filename": file.filename,
        "num_documents": len(docs),
        "num_chunks": len(chunks),
        "chunk_file": str(chunk_file)
    }