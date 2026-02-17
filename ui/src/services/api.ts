import axios from 'axios'
import type { Thread, ThreadMessage, SearchIteration } from '../types'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface QueryRequest {
  query: string
  top_k?: number
}

export interface LLMRequest {
  prompt: string
  provider: string
  model: string
}

export interface SimilarEntry {
  [key: string]: any
}

export interface SimilarEntriesResponse {
  results: [SimilarEntry, number][]
}

export interface LLMResponse {
  response: string
}

export interface Entry {
  date: string
  title: string
  text: string
  tags: string[]
  embedding?: number[] | null
}

export interface RetrievedDoc {
  entry: Entry
  distance: number | null
}

export interface ChatRequest {
  query: string
  top_k?: number
  provider: string
  model: string
  thread_id?: string
  message_history?: Array<{
    sender: 'user' | 'assistant'
    text: string
    timestamp: Date
  }>
  existing_docs?: Document[]
}

export interface ChatResponse {
  response: string
  docs: RetrievedDoc[]
  thread_id?: string
}

export interface StatusResponse {
  status: string
}

export const apiService = {
  async getSimilarEntries(request: QueryRequest): Promise<SimilarEntriesResponse> {
    const response = await api.post<SimilarEntriesResponse>('/similar_entries', {
      query: request.query,
      top_k: request.top_k || 5,
    })
    return response.data
  },

  async queryLLM(request: LLMRequest): Promise<LLMResponse> {
    const response = await api.post<LLMResponse>('/query_llm', request)
    return response.data
  },

  // Thread management methods
  async createThread(title?: string, initialMessage?: string): Promise<{ thread_id: string; created_at: string }> {
    const response = await api.post('/threads', {
      title,
      initial_message: initialMessage
    })
    return response.data
  },

  async getThreads(): Promise<Thread[]> {
    const response = await api.get<Thread[]>('/threads')
    return response.data
  },

  async getThread(threadId: string): Promise<Thread> {
    const response = await api.get<Thread>(`/threads/${threadId}`)
    return response.data
  },

  async getThreadMessages(threadId: string): Promise<ThreadMessage[]> {
    const response = await api.get<ThreadMessage[]>(`/threads/${threadId}/messages`)
    return response.data
  },

  async deleteThread(threadId: string): Promise<void> {
    await api.delete(`/threads/${threadId}`)
  },

  async updateThreadTitle(threadId: string, title: string): Promise<void> {
    await api.put(`/threads/${threadId}`, { title })
  },

  async addMessageToThread(threadId: string, role: string, content: string): Promise<ThreadMessage> {
    const response = await api.post<ThreadMessage>(`/threads/${threadId}/messages`, {
      role,
      content
    })
    return response.data
  },

  async queryJournalStream(
    request: ChatRequest,
    onIteration: (iteration: SearchIteration) => void,
    onComplete: (response: ChatResponse) => void,
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/journal_chat_agent/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })

    if (!response.ok || !response.body) {
      throw new Error(`Stream request failed: ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      let currentEvent = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          if (currentEvent === 'search_iteration') {
            onIteration(data as SearchIteration)
          } else if (currentEvent === 'chat_response') {
            onComplete(data as ChatResponse)
          }
        }
      }
    }
  },

  async checkStatus(): Promise<StatusResponse> {
    const response = await api.get<StatusResponse>('/status')
    return response.data
  },
}
