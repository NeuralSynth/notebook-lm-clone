import { useState, useEffect } from 'react'
import { BookOpen, Menu, X } from 'lucide-react'
import UploadZone from './components/Upload'
import DocumentList from './components/DocumentList'
import Chat from './components/Chat'
import { listDocuments } from './api'
import styles from './App.module.css'

export default function App() {
  const [documents, setDocuments] = useState([])
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch(() => {})
  }, [])

  function onUploaded(doc) {
    setDocuments(prev => [...prev, doc])
  }

  function onDeleted(docId) {
    setDocuments(prev => prev.filter(d => d.doc_id !== docId))
  }

  return (
    <div className={styles.layout}>
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div className={styles.overlay} onClick={() => setIsSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`${styles.sidebar} ${isSidebarOpen ? styles.sidebarOpen : ''}`}>
        <div className={styles.brand}>
          <BookOpen size={18} className={styles.brandIcon} />
          <span className={styles.brandName}>NotebookLM</span>
          <button className={styles.closeButton} onClick={() => setIsSidebarOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <div className={styles.section}>
          <h2 className={styles.sectionLabel}>Upload</h2>
          <UploadZone onUploaded={onUploaded} />
        </div>

        <div className={styles.section}>
          <h2 className={styles.sectionLabel}>
            Documents
            {documents.length > 0 && (
              <span className={styles.badge}>{documents.length}</span>
            )}
          </h2>
          <DocumentList documents={documents} onDeleted={onDeleted} />
        </div>

        <div className={styles.footer}>
          <span>RAG · Gemini · Qdrant</span>
        </div>
      </aside>

      {/* Main chat area */}
      <main className={styles.main}>
        <header className={styles.header}>
          <button className={styles.menuButton} onClick={() => setIsSidebarOpen(true)}>
            <Menu size={20} />
          </button>
          <div className={styles.headerTitleWrap}>
            <h1 className={styles.title}>Document Chat</h1>
            <span className={styles.subtitle}>
              {documents.length === 0
                ? 'Upload a document to begin'
                : `Searching across ${documents.length} document${documents.length > 1 ? 's' : ''}`
              }
            </span>
          </div>
        </header>

        <div className={styles.chatWrap}>
          <Chat hasDocuments={documents.length > 0} />
        </div>
      </main>
    </div>
  )
}
