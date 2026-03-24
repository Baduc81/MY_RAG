import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './ChatMessage.css'

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : 'message-row--ai'}`}>
      <div className="message-avatar">
        {isUser ? '🧑' : '🤖'}
      </div>
      <div className={`message-bubble ${isUser ? 'bubble--user' : 'bubble--ai'}`}>
        {isUser ? (
          <p className="message-text">{message.content}</p>
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="message-markdown"
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </div>
  )
}
