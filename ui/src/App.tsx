import { useState } from 'react'
import './App.css'
import DocumentViewer from './components/DocumentViewer'
import ChatInterface from './components/ChatInterface'
import type { Document } from './types'

function App() {
  const [documents, setDocuments] = useState<Document[]>([])

  return (
    <div className="app">
      <div className="app-container">
        <DocumentViewer documents={documents} />
        <ChatInterface setDocuments={setDocuments} />
      </div>
    </div>
  )
}

export default App
