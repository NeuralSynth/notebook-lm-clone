import { useState, useRef } from 'react'
import { Upload, Loader2 } from 'lucide-react'
import { uploadDocument } from '../api'
import styles from './Upload.module.css'

export default function UploadZone({ onUploaded }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  async function handleFile(file) {
    if (uploading) return
    
    setError(null)
    setUploading(true)
    try {
      const doc = await uploadDocument(file)
      onUploaded(doc)
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file).catch(console.error)
  }

  function onInputChange(e) {
    const file = e.target.files[0]
    if (file) handleFile(file).catch(console.error)
    e.target.value = ''
  }

  return (
    <div
      className={`${styles.zone} ${dragging ? styles.dragging : ''} ${uploading ? styles.uploading : ''}`}
      onClick={() => !uploading && inputRef.current.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md"
        style={{ display: 'none' }}
        onChange={onInputChange}
      />
      <div className={styles.inner}>
        {uploading ? (
          <Loader2 className={styles.spinner} size={22} />
        ) : (
          <Upload size={20} className={styles.icon} />
        )}
        <span className={styles.label}>
          {uploading ? 'Processing document…' : 'Drop PDF or TXT'}
        </span>
        <span className={styles.sub}>
          {uploading ? 'Chunking & indexing' : 'or click to browse'}
        </span>
      </div>
      {error && <div className={styles.error}>{error}</div>}
    </div>
  )
}
