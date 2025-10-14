import { useState, useEffect } from 'react'
import './ChatViewer.css'
import { apiService } from '../services/api'
import type { Thread, ThreadMessage } from '../types'

interface ChatViewerProps {
  onLoadThread: (threadId: string, messages: ThreadMessage[]) => void
}

const ChatViewer = ({ onLoadThread }: ChatViewerProps) => {
  const [threads, setThreads] = useState<Thread[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadThreads()
  }, [])

  const loadThreads = async () => {
    try {
      setLoading(true)
      const threadsData = await apiService.getThreads()
      setThreads(threadsData)
    } catch (error) {
      console.error('Error loading threads:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadThread = async (threadId: string, existingMessages: ThreadMessage[]) => {
    try {
      // if we don't have messages yet, fetch them
      let messages = existingMessages
      if (messages.length === 0) {
        messages = await apiService.getThreadMessages(threadId)
      }
      onLoadThread(threadId, messages)
    } catch (error) {
      console.error('Error loading thread messages:', error)
    }
  }

  const handleDeleteThread = async (threadId: string) => {
    try {
      await apiService.deleteThread(threadId)
      setThreads(threads.filter(t => t.thread_id !== threadId))
    } catch (error) {
      console.error('Error deleting thread:', error)
    }
  }

  return (
    <div className="chat-viewer">
      <div className="thread-list-header">
        <h3>Chat Threads</h3>
        <button onClick={loadThreads} disabled={loading}>
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>
      <div className="thread-items">
        {threads.map((thread) => (
          <div
            key={thread.thread_id}
            className="thread-item"
            onClick={() => handleLoadThread(thread.thread_id, [])}
          >
            <div className="thread-header">
              <h4>{thread.title}</h4>
              <button
                className="delete-thread"
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteThread(thread.thread_id)
                }}
              >
                ×
              </button>
            </div>
            <div className="thread-meta">
              <span>{new Date(thread.updated_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ChatViewer
