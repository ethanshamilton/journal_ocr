export interface Document {
    id: number
    title: string
    content: string
}

export interface Thread {
    thread_id: string
    title: string
    tags?: string[]
    created_at: string
    updated_at: string
}

export interface SearchIteration {
    iteration: number
    tool: string
    reasoning: string
    query: string | null
    results_count: number
    new_entries_added: number
}

export interface ThreadMessage {
    message_id: string
    thread_id: string
    timestamp: string
    role: 'user' | 'assistant'
    content: string
}
