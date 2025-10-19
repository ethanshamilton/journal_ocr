import { useState } from 'react'
import './DocumentViewer.css'
import type { JournalEntry } from '../types'

interface DocumentViewerProps {
  documents: JournalEntry[]
}

const DocumentViewer = ({ documents }: DocumentViewerProps) => {
  const [selectedDocument, setSelectedDocument] = useState<JournalEntry | null>(null)

  return (
    <div className="document-viewer">
      <div className="document-list">
        <h3>Documents</h3>
        <div className="document-items">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className={`document-item ${selectedDocument?.id === doc.id ? 'selected' : ''}`}
              onClick={() => setSelectedDocument(doc)}
            >
              <h4>{doc.title}</h4>
            </div>
          ))}
        </div>
      </div>
      
      <div className="document-content">
        {selectedDocument ? (
          <div>
            <h3>{selectedDocument.title}</h3>
            <div className="document-meta">
              <p><strong>Date:</strong> {selectedDocument.date}</p>
              {selectedDocument.tags && selectedDocument.tags.length > 0 && (
                <p><strong>Tags:</strong> {selectedDocument.tags.join(', ')}</p>
              )}
              {selectedDocument.score && (
                <p><strong>Relevance Score:</strong> {selectedDocument.score.toFixed(3)}</p>
              )}
            </div>
            <div 
              className="content"
              style={{ whiteSpace : 'pre-line' }}
            >
              {selectedDocument.text}
            </div>
          </div>
        ) : (
          <div className="no-document">
            <p>Select a document to view its content</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default DocumentViewer
