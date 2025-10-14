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

export interface ThreadMessage {
    message_id: string
    thread_id: string
    timestamp: string
    role: 'user' | 'assistant'
    content: string
}
