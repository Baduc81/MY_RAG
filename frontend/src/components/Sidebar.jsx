import { useRef, useState } from 'react'
import './Sidebar.css'

const SUPPORTED = '.pdf,.csv,.docx,.doc,.txt'

export default function Sidebar({ apiBase, documents, onDocumentsChange }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  const handleUpload = async (files) => {
    if (!files || files.length === 0) return
    setError(null)
    setUploading(true)

    const formData = new FormData()
    for (const file of files) {
      formData.append('files', file)
    }

    try {
      const res = await fetch(`${apiBase}/upload`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Upload failed (${res.status})`)
      }
      await onDocumentsChange()
    } catch (err) {
      setError(err.message || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (filename) => {
    if (!window.confirm(`Remove "${filename}"?`)) return
    try {
      await fetch(`${apiBase}/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      })
      await onDocumentsChange()
    } catch {
      /* ignore */
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="sidebar-title">Documents</span>
        <button
          className="upload-btn"
          onClick={() => !uploading && inputRef.current?.click()}
          disabled={uploading}
          title="Upload more documents"
        >
          {uploading ? '…' : '+'}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={SUPPORTED}
          className="file-input-hidden"
          onChange={(e) => handleUpload(e.target.files)}
        />
      </div>

      {uploading && (
        <div className="sidebar-progress">
          <div className="mini-spinner" />
          <span>Indexing…</span>
        </div>
      )}

      {error && (
        <div className="sidebar-error" role="alert">
          ⚠️ {error}
        </div>
      )}

      <ul className="doc-list">
        {documents.map((doc) => (
          <li key={doc.filename} className="doc-item">
            <span className="doc-icon">{getFileIcon(doc.filename)}</span>
            <span className="doc-name" title={doc.filename}>
              {doc.filename}
            </span>
            <button
              className="doc-delete-btn"
              onClick={() => handleDelete(doc.filename)}
              title="Remove document"
            >
              ×
            </button>
          </li>
        ))}
      </ul>

      {documents.length === 0 && !uploading && (
        <p className="sidebar-empty">No documents yet.</p>
      )}
    </aside>
  )
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop()?.toLowerCase()
  const icons = { pdf: '📄', csv: '📊', docx: '📝', doc: '📝', txt: '📃' }
  return icons[ext] || '📁'
}
