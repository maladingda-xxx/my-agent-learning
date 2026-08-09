"""
文档加载和切割模块
支持 PDF、Markdown、TXT
"""
import os
import json
import fitz  # PyMuPDF

def load_pdf(file_path: str) -> list[dict]:
    """
    从 PDF 提取文本，返回列表，每个元素为一页的内容及其元数据。
    """
    result = []
    doc = fitz.open(file_path)
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            result.append({
                "text": text,
                "metadata": {
                    "source": os.path.basename(file_path),
                    "page": page_num + 1,
                    "type": "pdf"
                }
            })
    doc.close()
    return result

def load_text(file_path: str) -> list[dict]:
    """加载纯文本文件（TXT / Markdown）"""
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    if not text.strip():
        return []
    return [{
        "text": text,
        "metadata": {
            "source": os.path.basename(file_path),
            "type": "txt" if file_path.endswith('.txt') else "markdown"
        }
    }]

def load_document(file_path: str) -> list[dict]:
    """根据文件扩展名自动选择加载器"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        return load_pdf(file_path)
    elif ext in ['.md', '.txt']:
        return load_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def split_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    固定长度切割文本。
    chunk_size: 每块最大字符数
    overlap: 相邻块重叠字符数
    """
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def split_documents(docs: list[dict], chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    对 load_document 返回的文档列表进行切割，每块保持 metadata。
    """
    all_chunks = []
    for doc in docs:
        text = doc['text']
        meta = doc['metadata']
        chunks = split_text(text, chunk_size, overlap)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "text": chunk,
                "metadata": {
                    **meta,
                    "chunk_id": i,
                    "total_chunks": len(chunks)
                }
            })
    return all_chunks

def save_chunks_to_json(chunks: list[dict], output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)