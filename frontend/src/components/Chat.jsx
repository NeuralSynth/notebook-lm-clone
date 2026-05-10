import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { streamChat } from '../api'
import styles from './Chat.module.css'

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`${styles.msg} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.avatar}>
        {isUser ? <User size={13} /> : <Bot size={13} />}
      </div>
      <div className={styles.bubble}>
        {msg.role === 'assistant' && !isUser && (
          <span className={styles.role}>Assistant</span>
        )}
        <p className={styles.text}>{msg.content || <span className={styles.cursor}>▍</span>}</p>
      </div>
    </div>
  )
}

export default function Chat({ hasDocuments }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send() {
    const query = input.trim()
    if (!query || streaming) return
    setInput('')

    const userMsg = { role: 'user', content: query, id: Date.now() }
    const assistantMsg = { role: 'assistant', content: '', id: Date.now() + 1 }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setStreaming(true)

    await streamChat({
      query,
      onChunk: (text) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMsg.id
              ? { ...m, content: m.content + text }
              : m
          )
        )
      },
      onDone: () => setStreaming(false),
      onError: (err) => {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMsg.id
              ? { ...m, content: `Error: ${err}` }
              : m
          )
        )
        setStreaming(false)
      },
    })
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.messages}>
        {messages.length === 0 && (
          <div className={styles.empty}>
            <span className={styles.emptyTitle}>Ask anything about your documents</span>
            <span className={styles.emptySub}>Answers are grounded in what you've uploaded</span>
          </div>
        )}
        {messages.map(msg => <Message key={msg.id} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      <div className={styles.inputRow}>
        <textarea
          ref={inputRef}
          className={styles.input}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={hasDocuments ? 'Ask a question…' : 'Upload a document first'}
          disabled={!hasDocuments || streaming}
          rows={1}
        />
        <button
          className={styles.send}
          onClick={send}
          disabled={!hasDocuments || streaming || !input.trim()}
        >
          {streaming
            ? <Loader2 size={16} className={styles.spinner} />
            : <Send size={16} />
          }
        </button>
      </div>
    </div>
  )
}
