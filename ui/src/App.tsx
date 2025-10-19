import { useState } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import { ChatInterface } from './components/ChatInterface'
import type { JournalEntry, Message } from './types/index'

function App() {
  const [documents, setDocuments] = useState<JournalEntry[]>([])

  const handleLoadThread = (threadId: string, messages: Message[]) => {
    // use the exposed function from ChatInterface
    if ((window as any).loadThreadIntoChat) {
      ;(window as any).loadThreadIntoChat(threadId, messages)
    }
  }

  return (
    <div className="app">
      <div className="app-container">
        <Sidebar documents={documents} onLoadThread={handleLoadThread} />
        <ChatInterface setDocuments={setDocuments} onLoadThread={handleLoadThread} />
      </div>
    </div>
  )
}

export default App
