export interface JournalEntry {
  id: string
  title: string
  text: string
  date: string
  tags: string[]
  score?: number
}

export interface Thread {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface ChatRequest {
  query: string
  topK?: number
  provider: string
  model: string
  threadId?: string
  messageHistory?: Message[]
  existingDocs?: JournalEntry[]
}

export interface ChatResponse {
  response: string
  docs: JournalEntry[]
  threadId?: string
}

export interface SearchRequest {
  query: string
  topK?: number
}

export interface SearchResponse {
  results: JournalEntry[]
}

export type IntentType = 'vector' | 'recent' | 'none'

export interface LLMConfig {
  provider: 'anthropic' | 'openai'
  model: string
}
