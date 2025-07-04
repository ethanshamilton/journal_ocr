import axios from 'axios'
import type { ModuleNamespace } from 'vite/types/hot.js'

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

export interface CombinedRequest {
  query: string
  top_k?: number
  provider: string
  model: string
}

export interface CombinedResponse {
  response: string
  docs: [SimilarEntry, number][]
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

  async queryJournal(request: CombinedRequest): Promise<CombinedResponse> {
    const response = await api.post<CombinedResponse>('/query_journal', request)
    return response.data
  },
}
