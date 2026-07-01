import os
from typing import List, Tuple, Dict, Generator
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from docx import Document
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 4
MAX_HISTORY_TURNS = 6
GROQ_MODEL = "llama-3.3-70b-versatile"

DISTANCE_HIGH_CONFIDENCE = 0.7
DISTANCE_MEDIUM_CONFIDENCE = 1.1

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using ONLY the provided document excerpts and the prior conversation. If the answer isn't in the excerpts, say you don't know based on the uploaded documents. Always be concise and cite which excerpt number you used, like [Excerpt 1]."""

def distance_to_confidence(distance: float) -> str:
    if distance <= DISTANCE_HIGH_CONFIDENCE:
        return "high"
    if distance <= DISTANCE_MEDIUM_CONFIDENCE:
        return "medium"
    return "low"

def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == ".docx":
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    if ext in (".txt", ".md"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    raise ValueError(f"Unsupported file extension: {ext}")

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]

class RAGEngine:
    def __init__(self):
        self.embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.dimension = self.embedder.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunk_store: List[str] = []
        self.source_store: List[str] = []
        self._doc_count = 0
        self.conversations: Dict[str, List[dict]] = {}
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set.")
        self.client = Groq(api_key=api_key)

    def add_documents(self, file_paths: List[str]) -> int:
        total_chunks_added = 0
        for path in file_paths:
            text = extract_text(path)
            chunks = chunk_text(text)
            if not chunks:
                continue
            embeddings = self.embedder.encode(chunks, convert_to_numpy=True)
            self.index.add(embeddings.astype(np.float32))
            self.chunk_store.extend(chunks)
            self.source_store.extend([os.path.basename(path)] * len(chunks))
            total_chunks_added += len(chunks)
            self._doc_count += 1
        return total_chunks_added

    def has_documents(self) -> bool:
        return len(self.chunk_store) > 0

    def num_documents(self) -> int:
        return self._doc_count

    def num_chunks(self) -> int:
        return len(self.chunk_store)

    def retrieve(self, question: str, top_k: int = TOP_K) -> List[Tuple[str, str, float]]:
        query_embedding = self.embedder.encode([question], convert_to_numpy=True).astype(np.float32)
        k = min(top_k, len(self.chunk_store))
        distances, indices = self.index.search(query_embedding, k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            results.append((self.chunk_store[idx], self.source_store[idx], float(dist)))
        return results

    def _get_history(self, session_id: str) -> List[dict]:
        return self.conversations.setdefault(session_id, [])

    def _append_history(self, session_id: str, role: str, content: str):
        history = self._get_history(session_id)
        history.append({"role": role, "content": content})
        max_messages = MAX_HISTORY_TURNS * 2
        if len(history) > max_messages:
            del history[: len(history) - max_messages]

    def clear_history(self, session_id: str):
        self.conversations[session_id] = []

    def _build_context_and_sources(self, question: str):
        retrieved = self.retrieve(question)
        context_blocks = []
        sources = []
        best_distance = None
        for i, (chunk, source, distance) in enumerate(retrieved, start=1):
            context_blocks.append(f"[Excerpt {i}] (from {source})\n{chunk}")
            if source not in sources:
                sources.append(source)
            if best_distance is None or distance < best_distance:
                best_distance = distance
        context_text = "\n\n".join(context_blocks)
        confidence = distance_to_confidence(best_distance) if best_distance is not None else "low"
        return context_text, sources, confidence

    def answer_question(self, question: str, session_id: str = "default") -> Tuple[str, List[str], str]:
        context_text, sources, confidence = self._build_context_and_sources(question)
        user_message = f"Document excerpts:\n\n{context_text}\n\nQuestion: {question}\n\nAnswer using only the information in the excerpts above."
        history = self._get_history(session_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_message}]
        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=1024,
        )
        answer_text = response.choices[0].message.content
        self._append_history(session_id, "user", question)
        self._append_history(session_id, "assistant", answer_text)
        return answer_text, sources, confidence

    def stream_answer(self, question: str, session_id: str = "default") -> Generator[dict, None, None]:
        context_text, sources, confidence = self._build_context_and_sources(question)
        yield {"type": "meta", "sources": sources, "confidence": confidence}
        user_message = f"Document excerpts:\n\n{context_text}\n\nQuestion: {question}\n\nAnswer using only the information in the excerpts above."
        history = self._get_history(session_id)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": user_message}]
        full_answer = ""
        stream = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=1024,
            stream=True,
        )
        for chunk in stream:
            text = chunk.choices[0].delta.content or ""
            if text:
                full_answer += text
                yield {"type": "token", "text": text}
        self._append_history(session_id, "user", question)
        self._append_history(session_id, "assistant", full_answer)
        yield {"type": "done"}

    def reset(self):
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunk_store = []
        self.source_store = []
        self._doc_count = 0
        self.conversations = {}