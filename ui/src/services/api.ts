import axios from 'axios'
import type { Thread, ThreadMessage } from '../types'

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

export interface ChatRequest {
  query: string
  top_k?: number
  provider: string
  model: string
  thread_id?: string
  message_history?: Array<{
    sender: 'user' | 'bot'
    text: string
    timestamp: Date
  }>
  existing_docs?: Document[]
}

export interface ChatResponse {
  response: string
  docs: [SimilarEntry, number][]
  thread_id?: string
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

  async queryJournal(request: ChatRequest): Promise<ChatResponse> {
    const response = await api.post<ChatResponse>('/query_journal', request)
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

  async addMessageToThread(threadId: string, role: string, content: string): Promise<ThreadMessage> {
    const response = await api.post<ThreadMessage>(`/threads/${threadId}/messages`, {
      role,
      content
    })
    return response.data
  },
}
