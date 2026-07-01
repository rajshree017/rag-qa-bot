\# Archive — RAG Q\&A Bot



Upload your documents (PDF, TXT, DOCX, MD) and ask questions about them.

The backend chunks documents, builds embeddings, and retrieves only relevant excerpts to answer your questions accurately.



\## Key Features



1\. \*\*Multi-turn conversation memory\*\* — Understands follow-up questions using session-based chat history.

2\. \*\*Confidence scoring\*\* — Shows high/medium/low confidence badge with each answer based on vector similarity.

3\. \*\*Streaming responses\*\* — Answer streams live token by token (Server-Sent Events), just like ChatGPT.



\## Tech Stack



\- \*\*Backend:\*\* Python, FastAPI, FAISS, Sentence Transformers, Groq API

\- \*\*Frontend:\*\* React, Vite

\- \*\*Hosting:\*\* Render.com (free tier)



\## Setup



\### Backend

```bash

cd backend

python -m venv venv

venv\\Scripts\\activate

pip install -r requirements.txt

copy .env.example .env

\# Add your API key in .env

uvicorn main:app --reload --port 8000

```



\### Frontend

```bash

cd frontend

npm install

npm run dev

```



Open: `http://localhost:5173`

