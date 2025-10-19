import { v4 as uuidv4 } from 'uuid'
import type { Thread, Message } from '../types/index'

export class ThreadService {
  private storageKey = 'journal_threads'

  saveThread(thread: Thread): void {
    const threads = this.getThreads()
    const existingIndex = threads.findIndex(t => t.id === thread.id)
    
    if (existingIndex >= 0) {
      threads[existingIndex] = thread
    } else {
      threads.push(thread)
    }
    
    localStorage.setItem(this.storageKey, JSON.stringify(threads))
  }

  getThreads(): Thread[] {
    const stored = localStorage.getItem(this.storageKey)
    if (!stored) return []
    
    const threads = JSON.parse(stored) as Thread[]
    return threads.map((t: Thread) => ({
      ...t,
      createdAt: this.parseDate(t.createdAt),
      updatedAt: this.parseDate(t.updatedAt),
      messages: t.messages.map((m: Message) => ({
        ...m,
        timestamp: this.parseDate(m.timestamp)
      }))
    }))
  }

  private parseDate(dateInput: any): Date {
    try {
      const date = new Date(dateInput)
      return isNaN(date.getTime()) ? new Date() : date
    } catch {
      return new Date()
    }
  }

  getThread(id: string): Thread | null {
    const threads = this.getThreads()
    return threads.find(t => t.id === id) || null
  }

  createThread(title?: string, initialMessage?: string): Thread {
    const thread: Thread = {
      id: uuidv4(),
      title: title || `chat ${new Date().toLocaleString()}`,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date()
    }

    if (initialMessage) {
      thread.messages.push({
        id: uuidv4(),
        role: 'user',
        content: initialMessage,
        timestamp: new Date()
      })
    }

    this.saveThread(thread)
    return thread
  }

  addMessage(threadId: string, role: 'user' | 'assistant', content: string): Message {
    const thread = this.getThread(threadId)
    if (!thread) {
      throw new Error(`thread ${threadId} not found`)
    }

    const message: Message = {
      id: uuidv4(),
      role,
      content,
      timestamp: new Date()
    }

    thread.messages.push(message)
    thread.updatedAt = new Date()
    this.saveThread(thread)

    return message
  }

  deleteThread(id: string): boolean {
    const threads = this.getThreads()
    const filtered = threads.filter(t => t.id !== id)
    
    if (filtered.length === threads.length) {
      return false // thread not found
    }
    
    localStorage.setItem(this.storageKey, JSON.stringify(filtered))
    return true
  }

  updateThreadTitle(id: string, title: string): boolean {
    const thread = this.getThread(id)
    if (!thread) return false

    thread.title = title
    thread.updatedAt = new Date()
    this.saveThread(thread)
    return true
  }
}
