"""
RAG Q&A Bot - FastAPI Backend
Upload documents, build a vector index, and chat with your documents using Claude.
"""
import json
import os
import shutil
import uuid
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rag_engine import RAGEngine

app = FastAPI(title="RAG Q&A Bot API")

# Allow the frontend (any origin during dev; restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set this to your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_docs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# One global RAG engine instance holding the vector index + chat logic
engine = RAGEngine()


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: str


@app.get("/")
def health_check():
    return {"status": "ok", "message": "RAG Q&A Bot backend is running"}


@app.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more documents (.pdf, .txt, .docx).
    These get chunked, embedded, and added to the vector index.
    """
    saved_files = []
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".pdf", ".txt", ".docx", ".md"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

        unique_name = f"{uuid.uuid4().hex}{ext}"
        save_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        saved_files.append({"original_name": file.filename, "path": save_path})

    # Process and index the documents
    chunks_added = engine.add_documents([f["path"] for f in saved_files])

    return {
        "message": f"Uploaded and indexed {len(saved_files)} file(s)",
        "files": [f["original_name"] for f in saved_files],
        "chunks_added": chunks_added,
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question. The engine retrieves relevant chunks from indexed
    documents and asks Claude to answer using only that context, plus
    this session's recent conversation history (so follow-ups work).
    """
    if not engine.has_documents():
        raise HTTPException(
            status_code=400,
            detail="No documents indexed yet. Upload a document first via /upload.",
        )

    answer, sources, confidence = engine.answer_question(request.question, request.session_id)
    return ChatResponse(answer=answer, sources=sources, confidence=confidence)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Same as /chat but streams the answer token-by-token via Server-Sent Events.
    Each event is a JSON object: {"type": "meta"|"token"|"done"|"error", ...}
    """
    if not engine.has_documents():
        raise HTTPException(
            status_code=400,
            detail="No documents indexed yet. Upload a document first via /upload.",
        )

    def event_generator():
        try:
            for event in engine.stream_answer(request.question, request.session_id):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.delete("/chat/{session_id}/history")
def clear_chat_history(session_id: str):
    """Clear conversation memory for a session, without touching the document index."""
    engine.clear_history(session_id)
    return {"message": f"Conversation history cleared for session '{session_id}'"}


@app.get("/status")
def status():
    return {
        "documents_indexed": engine.num_documents(),
        "chunks_indexed": engine.num_chunks(),
    }


@app.delete("/reset")
def reset():
    """Clear the entire index and uploaded files (start fresh)."""
    engine.reset()
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return {"message": "Index and uploaded files cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
