"""
Document upload and RAG endpoints
"""
import os
import time
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# In-memory document store
_documents_db: dict = {}


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    size_bytes: int
    status: str
    created_at: float
    chunks: int = 0


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for RAG processing."""
    # Validate file type
    extension = file.filename.split(".")[-1].lower() if file.filename else ""
    if extension not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{extension}' not allowed. Allowed: {settings.ALLOWED_FILE_TYPES}"
        )
    
    # Read content
    content = await file.read()
    
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )
    
    doc_id = str(uuid.uuid4())
    
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}.{extension}")
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Parse and chunk the document
    chunks = await _process_document(content, extension, doc_id)
    
    document = {
        "id": doc_id,
        "filename": file.filename,
        "file_type": extension,
        "size_bytes": len(content),
        "status": "processed",
        "created_at": time.time(),
        "chunks": len(chunks),
        "file_path": file_path,
        "chunk_data": chunks[:5],  # Store first 5 chunks for retrieval demo
    }
    _documents_db[doc_id] = document
    
    return DocumentResponse(
        id=doc_id,
        filename=file.filename,
        file_type=extension,
        size_bytes=len(content),
        status="processed",
        created_at=time.time(),
        chunks=len(chunks),
    )


async def _process_document(content: bytes, extension: str, doc_id: str) -> List[str]:
    """Parse and chunk a document for RAG."""
    text = ""
    
    try:
        if extension == "txt" or extension == "md":
            text = content.decode("utf-8", errors="ignore")
        
        elif extension == "pdf":
            try:
                import pypdf
                import io
                reader = pypdf.PdfReader(io.BytesIO(content))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                text = content.decode("utf-8", errors="ignore")
        
        elif extension in ("py", "js", "ts", "json", "yaml"):
            text = content.decode("utf-8", errors="ignore")
        
        elif extension == "docx":
            try:
                import docx
                import io
                doc = docx.Document(io.BytesIO(content))
                text = "\n".join(para.text for para in doc.paragraphs)
            except ImportError:
                text = content.decode("utf-8", errors="ignore")
        
        else:
            text = content.decode("utf-8", errors="ignore")
    
    except Exception:
        text = content.decode("utf-8", errors="ignore")
    
    # Simple chunking (500 chars with 50 overlap)
    chunk_size = 500
    overlap = 50
    chunks = []
    
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    
    return chunks


@router.get("", response_model=List[DocumentResponse])
async def list_documents():
    """List all uploaded documents."""
    docs = []
    for doc in _documents_db.values():
        docs.append(DocumentResponse(
            id=doc["id"],
            filename=doc["filename"],
            file_type=doc["file_type"],
            size_bytes=doc["size_bytes"],
            status=doc["status"],
            created_at=doc["created_at"],
            chunks=doc["chunks"],
        ))
    return sorted(docs, key=lambda x: x.created_at, reverse=True)


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document."""
    doc = _documents_db.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Clean up file
    try:
        if os.path.exists(doc["file_path"]):
            os.remove(doc["file_path"])
    except Exception:
        pass
    
    del _documents_db[document_id]
    return {"message": "Document deleted"}


@router.get("/{document_id}/chunks")
async def get_document_chunks(document_id: str):
    """Get document chunks for RAG inspection."""
    doc = _documents_db.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "document_id": document_id,
        "filename": doc["filename"],
        "total_chunks": doc["chunks"],
        "sample_chunks": doc.get("chunk_data", []),
    }
