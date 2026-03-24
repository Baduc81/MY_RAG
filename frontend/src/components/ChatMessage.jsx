import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './ChatMessage.css'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'
  const [showContext, setShowContext] = useState(false)
  const contextChunks = Array.isArray(message.contextChunks) ? message.contextChunks : []
  const hasContext = !isUser && contextChunks.length > 0

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : 'message-row--ai'}`}>
      <div className="message-avatar">
        {isUser ? '🧑' : '🤖'}
      </div>
      <div className={`message-bubble ${isUser ? 'bubble--user' : 'bubble--ai'}`}>
        {isUser ? (
          <p className="message-text">{message.content}</p>
        ) : (
          <>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              className="message-markdown"
            >
              {message.content}
            </ReactMarkdown>

            {hasContext && (
              <div className="message-context-wrap">
                <button
                  type="button"
                  className="message-context-btn"
                  onClick={() => setShowContext((prev) => !prev)}
                >
                  {showContext ? 'Hide chunks' : `View chunks (${contextChunks.length})`}
                </button>

                {showContext && (
                  <div className="message-context-panel">
                    {contextChunks.map((chunk) => (
                      <div className="context-chunk" key={`chunk-${message.id}-${chunk.index}`}>
                        <div className="context-chunk-head">
                          <span>Chunk {chunk.index}</span>
                          <span>{chunk.source_file || 'unknown source'}</span>
                        </div>

                        <pre className="context-chunk-text">{chunk.text}</pre>

                        {chunk.tables_html.length > 0 && (
                          <div className="context-table-wrap">
                            {chunk.tables_html.map((table, idx) => (
                              <pre key={`table-${chunk.index}-${idx}`} className="context-table-html">
                                {table}
                              </pre>
                            ))}
                          </div>
                        )}

                        {chunk.has_images && (
                          <p className="context-image-flag">Contains image content in original chunk.</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
