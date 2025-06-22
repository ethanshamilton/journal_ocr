import { useState } from 'react'
import './App.css'
import DocumentViewer from './components/DocumentViewer'
import ChatInterface from './components/ChatInterface'

function App() {
  const [documents, setDocuments] = useState([
    { id: 1, title: "Document 1", content: "Sample document content..." },
    { id: 2, title: "Document 2", content: "Another document content..." },
    { id: 3, title: "Document 3", content: "More document content..." }
  ])

  return (
    <div className="app">
      <div className="app-container">
        <DocumentViewer documents={documents} />
        <ChatInterface />
      </div>
    </div>
  )
}

export default App
