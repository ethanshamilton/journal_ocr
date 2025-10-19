import { useState, useEffect } from 'react'
import './ChatViewer.css'
import { ThreadService } from '../services/threads'
import type { Thread, Message } from '../types'

interface ChatViewerProps {
  onLoadThread: (threadId: string, messages: Message[]) => void
}

const ChatViewer = ({ onLoadThread }: ChatViewerProps) => {
  const [threads, setThreads] = useState<Thread[]>([])
  const [loading, setLoading] = useState(false)
  const [editingThreadId, setEditingThreadId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')
  
  const threadService = new ThreadService()

  useEffect(() => {
    loadThreads()
  }, [])

  const loadThreads = () => {
    try {
      setLoading(true)
      const threadsData = threadService.getThreads()
      setThreads(threadsData)
    } catch (error) {
      console.error('Error loading threads:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadThread = (threadId: string) => {
    try {
      const thread = threadService.getThread(threadId)
      if (thread) {
        onLoadThread(threadId, thread.messages)
      }
    } catch (error) {
      console.error('Error loading thread messages:', error)
    }
  }

  const handleDeleteThread = (threadId: string) => {
    try {
      const success = threadService.deleteThread(threadId)
      if (success) {
        setThreads(threads.filter(t => t.id !== threadId))
      }
    } catch (error) {
      console.error('Error deleting thread:', error)
    }
  }

  const handleStartEdit = (thread: Thread) => {
    setEditingThreadId(thread.id)
    setEditTitle(thread.title)
  }

  const handleSaveEdit = () => {
    if (!editingThreadId || !editTitle.trim()) {
      handleCancelEdit()
      return
    }
    
    try {
      const success = threadService.updateThreadTitle(editingThreadId, editTitle.trim())
      if (success) {
        setThreads(threads.map(t => 
          t.id === editingThreadId 
            ? { ...t, title: editTitle.trim() }
            : t
        ))
        setEditingThreadId(null)
        setEditTitle('')
      }
    } catch (error) {
      console.error('Error updating thread title:', error)
      handleCancelEdit()
    }
  }

  const handleCancelEdit = () => {
    setEditingThreadId(null)
    setEditTitle('')
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
            key={thread.id}
            className="thread-item"
            onClick={() => handleLoadThread(thread.id)}
            onDoubleClick={() => handleStartEdit(thread)}
          >
            <div className="thread-header">
              {editingThreadId === thread.id ? (
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  onBlur={handleSaveEdit}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveEdit()
                    if (e.key === 'Escape') handleCancelEdit()
                  }}
                  className="edit-title-input"
                  autoFocus
                />
              ) : (
                <h4>{thread.title}</h4>
              )}
              <button
                className="delete-thread"
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteThread(thread.id)
                }}
              >
                ×
              </button>
            </div>
            <div className="thread-meta">
              <span>{new Date(thread.updatedAt).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ChatViewer
