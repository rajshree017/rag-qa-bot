# Archive — RAG Q&A Bot

A Retrieval-Augmented Generation (RAG) based Q&A system — upload your documents (PDF, TXT, DOCX, MD) and ask questions about them. The backend chunks documents, builds embeddings, and retrieves only the most relevant excerpts to generate accurate, grounded answers.

## Demo

▶️ [Watch Demo](https://drive.google.com/file/d/1eMYVzjbskW1gavRAaSNceSXkKsz_5WjU/view?usp=sharing)

## Key Features

- **Multi-turn conversation memory** — Understands follow-up questions using session-based chat history.
- **Confidence scoring** — Shows a high/medium/low confidence badge with each answer, based on vector similarity.
- **Streaming responses** — Answers stream live, token by token (Server-Sent Events), just like ChatGPT.

## Tech Stack

| Layer     | Technology                                          |
|-----------|------------------------------------------------------|
| Backend   | Python, FastAPI, FAISS, Sentence Transformers, Groq API |
| Frontend  | React, Vite                                         |
| Hosting   | Render.com (free tier)                              |

## How It Works

1. User uploads a document (PDF/TXT/DOCX/MD)
2. Backend splits it into chunks and generates embeddings using Sentence Transformers
3. Embeddings are indexed in FAISS for fast similarity search
4. On each question, the most relevant chunks are retrieved and passed to the Groq LLM
5. Answer streams back in real time, along with a confidence score

## Getting Started

### Backend

\`\`\`bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Add your API key in .env
uvicorn main:app --reload --port 8000
\`\`\`

### Frontend

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

Open: `http://localhost:5173`

## License

This project is open source and available for learning purposes.
