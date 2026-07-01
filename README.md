# Archive — RAG Q&A Bot

Apne documents (PDF, TXT, DOCX, MD) upload karo, aur unke baare mein sawaal pucho.
Backend documents ko chunks mein todta hai, embeddings banata hai, aur sawaal puchne par
sirf relevant excerpts Claude ko bhejta hai — taaki answers tumhare documents par based ho.

## ✨ Key Features (jo recruiter ko impress karenge)

1. **Multi-turn conversation memory** — follow-up questions samajhta hai ("uske baare mein
   zyada batao", "why?") kyunki har session ki chat history yaad rakhta hai.
2. **Confidence scoring** — har answer ke saath high/medium/low confidence badge dikhta hai,
   based on vector similarity — yeh dikhata hai ki RAG retrieval quality samajh aati hai.
3. **Streaming responses** — jawab live "type" hota hua dikhta hai (Server-Sent Events se),
   jaisa ChatGPT mein hota hai, na ki static "loading…" spinner.

## Folder Structure

```
rag-qa-bot/
├── backend/          FastAPI server (Python)
│   ├── main.py        API routes (incl. streaming + session-based chat)
│   ├── rag_engine.py  document parsing + embeddings + conversation memory + Claude calls
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/          React app (Vite)
│   └── src/
└── render.yaml         deploy config for Render.com
```

## 1. Local Setup (apne computer pe chalu karna)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

`.env` file kholo aur apna Claude API key daalo:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
```

> API key yahan se milegi: https://console.anthropic.com/settings/keys

Backend chalu karo:
```bash
uvicorn main:app --reload --port 8000
```

Pehli baar chalane par `sentence-transformers` model download hoga (~80MB), thoda time lagega.

### Frontend

Naye terminal mein:
```bash
cd frontend
npm install
npm run dev
```

Browser mein kholo: `http://localhost:5173`

## 2. Hosting (Production mein daalna)

### Backend → Render.com

1. Is folder ko GitHub repo mein push karo (neeche steps hain).
2. [render.com](https://render.com) par jaake "New +" → "Blueprint" choose karo.
3. Apna GitHub repo connect karo. Render `render.yaml` ko khud detect kar lega.
4. Jab pucha jaaye, `ANTHROPIC_API_KEY` environment variable daalo (apni real key).
5. Deploy hone do — backend ka URL milega jaise `https://rag-qa-bot-backend.onrender.com`

### Frontend → Render.com (ya Vercel/Netlify)

Render blueprint frontend ko bhi deploy kar dega static site ke roop mein.
Bas ek environment variable set karna hoga: `VITE_API_URL` = tumhara backend ka URL
(step 5 mein jo mila).

**Vercel use karna hai to:**
```bash
cd frontend
npm install -g vercel
vercel
```
Deploy ke time `VITE_API_URL` environment variable add karo Vercel dashboard mein.

## 3. GitHub par push karna (agar abhi nahi kiya)

```bash
cd rag-qa-bot
git init
git add .
git commit -m "Initial commit: RAG Q&A Bot"
git branch -M main
git remote add origin https://github.com/<tumhara-username>/rag-qa-bot.git
git push -u origin main
```

## Important Notes

- **Free tier note:** Render ka free tier kuch der inactive rehne par "sleep" ho jaata hai —
  pehli request thodi slow ho sakti hai (cold start, ~30-50 seconds).
- **Vector index in-memory hai:** Agar backend restart hota hai, uploaded documents ka index
  clear ho jaayega — phir se upload karna padega. (Production-grade ke liye Pinecone/Qdrant
  jaise persistent vector DB use kar sakte ho, lekin abhi ke liye yeh simple aur free hai.)
- **CORS:** Abhi `allow_origins=["*"]` hai (sabko allow karta hai). Production mein isse apne
  frontend ke exact URL tak restrict kar dena (`backend/main.py` mein).
