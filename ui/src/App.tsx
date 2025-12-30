import { useState, useEffect } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import ChatInterface from './components/ChatInterface'
import LoadingScreen from './components/LoadingScreen'
import { apiService } from './services/api'
import type { Document, ThreadMessage } from './types'

function App() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [isBackendReady, setIsBackendReady] = useState(false)

  useEffect(() => {
    let isMounted = true

    const checkBackendStatus = async () => {
      try {
        const response = await apiService.checkStatus()
        if (response.status === 'ready' && isMounted) {
          setIsBackendReady(true)
        }
      } catch {
        // Backend not up yet, continue polling
      }
    }

    // Check immediately on mount
    checkBackendStatus()

    // Poll every 2 seconds
    const intervalId = window.setInterval(checkBackendStatus, 2000)

    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [])

  const handleLoadThread = (threadId: string, messages: ThreadMessage[]) => {
    // use the exposed function from ChatInterface
    if ((window as any).loadThreadIntoChat) {
      ;(window as any).loadThreadIntoChat(threadId, messages)
    }
  }

  if (!isBackendReady) {
    return <LoadingScreen />
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
