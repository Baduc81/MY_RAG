import { useState, useRef } from 'react'
import './OnboardingScreen.css'

const SUPPORTED = '.pdf,.csv,.docx,.doc,.txt'

export default function OnboardingScreen({ apiBase, onUploadComplete }) {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [progress, setProgress] = useState(null)
  const inputRef = useRef(null)

  const handleFiles = async (files) => {
    if (!files || files.length === 0) return
    setError(null)
    setUploading(true)
    setProgress('Uploading and indexing documents…')

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

      setProgress('Indexing complete! Opening chat…')
      await onUploadComplete()
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.')
      setProgress(null)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    handleFiles(e.dataTransfer.files)
  }

  const handleDragOver = (e) => e.preventDefault()

  return (
    <div className="onboarding-root">
      <div className="onboarding-card">
        <div className="onboarding-icon">🤖</div>
        <h1 className="onboarding-title">RAG Assistant</h1>
        <p className="onboarding-subtitle">
          Upload your documents to get started. You can ask questions about
          PDFs, Word documents, spreadsheets, and text files.
        </p>

        <div
          className={`drop-zone ${uploading ? 'drop-zone--disabled' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => !uploading && inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && !uploading && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={SUPPORTED}
            className="file-input-hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {uploading ? (
            <div className="drop-zone-content">
              <div className="spinner-large" />
              <p className="progress-text">{progress}</p>
            </div>
          ) : (
            <div className="drop-zone-content">
              <div className="drop-icon">📂</div>
              <p className="drop-primary">Drag & drop files here</p>
              <p className="drop-secondary">or click to browse</p>
              <p className="drop-hint">Supported: PDF, DOCX, DOC, CSV, TXT</p>
            </div>
          )}
        </div>

        {error && (
          <div className="error-banner" role="alert">
            ⚠️ {error}
          </div>
        )}
      </div>
    </div>
  )
}
