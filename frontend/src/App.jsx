import React, { useState, useRef, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Persist a session id for this browser tab so follow-up questions keep context
const SESSION_ID = (() => {
  const existing = sessionStorage.getItem('rag_session_id')
  if (existing) return existing
  const fresh = crypto.randomUUID()
  sessionStorage.setItem('rag_session_id', fresh)
  return fresh
})()

const CONFIDENCE_LABEL = {
  high: { text: 'High confidence', className: 'confidence-high' },
  medium: { text: 'Medium confidence', className: 'confidence-medium' },
  low: { text: 'Low confidence', className: 'confidence-low' },
}

export default function App() {
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [indexedFiles, setIndexedFiles] = useState([])
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)
  const chatEndRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleFileSelect = (e) => {
    setFiles(Array.from(e.target.files))
  }

  const handleUpload = async () => {
    if (files.length === 0) return
    setUploading(true)
    setError(null)

    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))

    try {
      const res = await fetch(`${API_URL}/upload`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
      const data = await res.json()
      setIndexedFiles((prev) => [...prev, ...data.files])
      setFiles([])
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleAsk = async (e) => {
    e.preventDefault()
    if (!question.trim() || asking) return

    const userQuestion = question.trim()
    setMessages((prev) => [...prev, { role: 'user', text: userQuestion }])
    setQuestion('')
    setAsking(true)
    setError(null)

    // Add a placeholder assistant message that we'll fill in as tokens stream in
    setMessages((prev) => [...prev, { role: 'assistant', text: '', sources: [], confidence: null, streaming: true }])

    try {
      const res = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQuestion, session_id: SESSION_ID }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to get answer')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n\n')
        buffer = lines.pop() // keep any incomplete chunk for next read

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const event = JSON.parse(line.slice(6))

          if (event.type === 'meta') {
            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              updated[updated.length - 1] = { ...last, sources: event.sources, confidence: event.confidence }
              return updated
            })
          } else if (event.type === 'token') {
            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              updated[updated.length - 1] = { ...last, text: last.text + event.text }
              return updated
            })
          } else if (event.type === 'error') {
            throw new Error(event.message)
          } else if (event.type === 'done') {
            setMessages((prev) => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              updated[updated.length - 1] = { ...last, streaming: false }
              return updated
            })
          }
        }
      }
    } catch (err) {
      setError(err.message)
      setMessages((prev) => prev.slice(0, -2)) // remove question + empty assistant bubble
    } finally {
      setAsking(false)
    }
  }

  const handleClearConversation = async () => {
    try {
      await fetch(`${API_URL}/chat/${SESSION_ID}/history`, { method: 'DELETE' })
    } catch {
      // non-critical if this fails; clear local state regardless
    }
    setMessages([])
  }

  return (
    <div className="page">
      <header className="header">
        <h1>Archive</h1>
        <p className="subtitle">Upload documents. Ask questions. Get answers grounded in your sources.</p>
      </header>

      <section className="upload-panel">
        <div className="upload-row">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx,.md"
            onChange={handleFileSelect}
            id="file-input"
            className="file-input"
          />
          <label htmlFor="file-input" className="file-label">
            {files.length > 0 ? `${files.length} file(s) selected` : 'Choose documents (.pdf, .txt, .docx, .md)'}
          </label>
          <button onClick={handleUpload} disabled={uploading || files.length === 0} className="btn-upload">
            {uploading ? 'Indexing…' : 'Upload & Index'}
          </button>
        </div>

        {indexedFiles.length > 0 && (
          <div className="indexed-list">
            <span className="indexed-label">Indexed:</span>
            {indexedFiles.map((name, i) => (
              <span key={i} className="indexed-chip">{name}</span>
            ))}
          </div>
        )}
      </section>

      {error && <div className="error-banner">{error}</div>}

      <section className="chat-panel">
        <div className="chat-toolbar">
          {messages.length > 0 && (
            <button className="btn-clear" onClick={handleClearConversation}>
              Clear conversation
            </button>
          )}
        </div>

        <div className="chat-window">
          {messages.length === 0 && (
            <div className="empty-state">
              <p>No questions yet.</p>
              <p className="empty-hint">Upload a document above, then ask something about it.</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              <div className="message-label">{msg.role === 'user' ? 'You' : 'Archive'}</div>
              <div className="message-text">
                {msg.text}
                {msg.streaming && <span className="cursor-blink">▍</span>}
              </div>
              {msg.confidence && (
                <div className="message-meta">
                  <span className={`confidence-badge ${CONFIDENCE_LABEL[msg.confidence].className}`}>
                    {CONFIDENCE_LABEL[msg.confidence].text}
                  </span>
                  {msg.sources && msg.sources.length > 0 && (
                    <span className="message-sources">Sources: {msg.sources.join(', ')}</span>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <form onSubmit={handleAsk} className="ask-form">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask something about your documents… (follow-ups work too)"
            disabled={asking || indexedFiles.length === 0}
            className="ask-input"
          />
          <button type="submit" disabled={asking || !question.trim()} className="btn-ask">
            {asking ? 'Thinking…' : 'Ask'}
          </button>
        </form>
      </section>
    </div>
  )
}
