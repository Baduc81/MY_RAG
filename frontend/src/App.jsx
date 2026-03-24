import { useState, useEffect, useCallback } from 'react'
import OnboardingScreen from './components/OnboardingScreen.jsx'
import ChatInterface from './components/ChatInterface.jsx'
import './App.css'

const API_BASE = '/api'

export default function App() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`)
      if (res.ok) {
        const data = await res.json()
        setDocuments(data)
      }
    } catch {
      // backend not yet available — keep empty
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  if (loading) {
    return (
      <div className="app-loading">
        <div className="spinner" />
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <OnboardingScreen
        apiBase={API_BASE}
        onUploadComplete={fetchDocuments}
      />
    )
  }

  return (
    <ChatInterface
      apiBase={API_BASE}
      documents={documents}
      onDocumentsChange={fetchDocuments}
    />
  )
}
