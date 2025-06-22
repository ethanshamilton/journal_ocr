import { useState } from 'react'
import './DocumentViewer.css'

interface Document {
  id: number
  title: string
  content: string
}

interface DocumentViewerProps {
  documents: Document[]
}

const DocumentViewer = ({ documents }: DocumentViewerProps) => {
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)

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
            <div className="content">
              {selectedDocument.content}
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