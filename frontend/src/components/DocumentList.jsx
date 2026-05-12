import { useState } from 'react'
import { Trash2, FileText, File, Loader2, AlertCircle } from 'lucide-react'
import { deleteDocument } from '../api'
import styles from './DocumentList.module.css'

function fileIcon(filename) {
  const ext = filename?.split('.').pop()?.toLowerCase()
  return ext === 'pdf' ? <FileText size={14} /> : <File size={14} />
}

export default function DocumentList({ documents, onDeleted }) {
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState(null)

  async function handleDelete(docId) {
    if (deletingId) return
    setError(null)
    setDeletingId(docId)
    try {
      await deleteDocument(docId)
      onDeleted(docId)
    } catch (e) {
      console.error(e)
      setError({ id: docId, message: e.message })
    } finally {
      setDeletingId(null)
    }
  }

  if (!documents.length) {
    return (
      <div className={styles.empty}>
        <span>No documents yet</span>
      </div>
    )
  }

  return (
    <ul className={styles.list}>
      {documents.map(doc => (
        <li key={doc.doc_id} className={styles.item}>
          <div className={styles.icon}>{fileIcon(doc.filename)}</div>
          <div className={styles.info}>
            <span className={styles.name} title={doc.filename}>{doc.filename}</span>
            <span className={styles.meta}>{doc.chunks} chunks · {doc.pages} pages</span>
          </div>
          <button
            className={`${styles.del} ${deletingId === doc.doc_id ? styles.deleting : ''}`}
            onClick={() => handleDelete(doc.doc_id)}
            title={error?.id === doc.doc_id ? error.message : "Remove document"}
            disabled={deletingId === doc.doc_id}
          >
            {deletingId === doc.doc_id ? (
              <Loader2 size={13} className={styles.spinner} />
            ) : error?.id === doc.doc_id ? (
              <AlertCircle size={13} className={styles.errIcon} />
            ) : (
              <Trash2 size={13} />
            )}
          </button>
        </li>
      ))}
    </ul>
  )
}
