import { Trash2, FileText, File } from 'lucide-react'
import { deleteDocument } from '../api'
import styles from './DocumentList.module.css'

function fileIcon(filename) {
  const ext = filename?.split('.').pop()?.toLowerCase()
  return ext === 'pdf' ? <FileText size={14} /> : <File size={14} />
}

export default function DocumentList({ documents, onDeleted }) {
  async function handleDelete(docId) {
    try {
      await deleteDocument(docId)
      onDeleted(docId)
    } catch (e) {
      console.error(e)
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
            className={styles.del}
            onClick={() => handleDelete(doc.doc_id)}
            title="Remove document"
          >
            <Trash2 size={13} />
          </button>
        </li>
      ))}
    </ul>
  )
}
