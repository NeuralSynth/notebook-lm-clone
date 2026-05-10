const BASE = import.meta.env.VITE_API_URL || ''

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/api/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Upload failed' }))
    throw new Error(err.detail || 'Upload failed')
  }
  return res.json()
}

export async function listDocuments() {
  const res = await fetch(`${BASE}/api/documents`)
  if (!res.ok) throw new Error('Failed to fetch documents')
  const data = await res.json()
  return data.documents
}

export async function deleteDocument(docId) {
  const res = await fetch(`${BASE}/api/documents/${docId}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete document')
  return res.json()
}

/**
 * Stream chat response via SSE.
 * onChunk(text) called for each streamed token.
 * onDone() called when stream completes.
 * onError(msg) called on error.
 */
export async function streamChat({ query, docIds, onChunk, onDone, onError }) {
  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, doc_ids: docIds || null }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat failed' }))
    onError(err.detail || 'Chat failed')
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep incomplete line

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const event = JSON.parse(line.slice(6))
        if (event.type === 'chunk') onChunk(event.text)
        else if (event.type === 'done') onDone()
        else if (event.type === 'error') onError(event.message)
      } catch {}
    }
  }
}
