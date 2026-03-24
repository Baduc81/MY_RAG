import { useState, useRef, useEffect } from 'react'
import Sidebar from './Sidebar.jsx'
import ChatMessage from './ChatMessage.jsx'
import './ChatInterface.css'

export default function ChatInterface({ apiBase, documents, onDocumentsChange }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hello! I'm your RAG assistant. I have access to ${documents.length} document(s). Ask me anything about them!`,
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    const query = input.trim()
    if (!query || loading) return

    const userMsg = { id: Date.now(), role: 'user', content: query }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${apiBase}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })

      const data = await res.json()
      const answer = res.ok
        ? data.answer
        : data.detail || 'Something went wrong. Please try again.'

      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'assistant', content: answer },
      ])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: 'Network error. Please check the backend is running.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-layout">
      <Sidebar
        apiBase={apiBase}
        documents={documents}
        onDocumentsChange={onDocumentsChange}
      />

      <main className="chat-main">
        <header className="chat-header">
          <span className="chat-header-title">RAG Assistant</span>
          <span className="chat-header-sub">
            {documents.length} document{documents.length !== 1 ? 's' : ''} loaded
          </span>
        </header>

        <div className="chat-messages">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          {loading && (
            <div className="chat-thinking">
              <span className="thinking-dot" />
              <span className="thinking-dot" />
              <span className="thinking-dot" />
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <footer className="chat-footer">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              className="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents…"
              rows={1}
              disabled={loading}
            />
            <button
              className="send-btn"
              onClick={sendMessage}
              disabled={!input.trim() || loading}
              aria-label="Send"
            >
              ↑
            </button>
          </div>
          <p className="input-hint">Press Enter to send · Shift+Enter for new line</p>
        </footer>
      </main>
    </div>
  )
}
