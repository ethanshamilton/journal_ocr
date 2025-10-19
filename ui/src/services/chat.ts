import { ElasticsearchService } from './elasticsearch'
import { LLMService } from './llm'
import { ThreadService } from './threads'
import type { ChatRequest, ChatResponse, JournalEntry, LLMConfig, Thread, Message } from '../types'

export class ChatService {
  private esService = new ElasticsearchService()
  private llmService = new LLMService()
  private threadService = new ThreadService()

  async queryJournal(request: ChatRequest): Promise<ChatResponse> {
    let entries: JournalEntry[] = []
    let entriesStr = ""

    // if we have existing docs, use those instead of doing retrieval
    if (request.existingDocs && request.existingDocs.length > 0) {
      entriesStr = "here are the relevant journal entries from our previous conversation:\n"
      request.existingDocs.forEach((doc, i) => {
        entriesStr += `entry ${i + 1}:\n`
        entriesStr += `  title: ${doc.title}\n`
        entriesStr += `  content: ${doc.text}\n\n`
      })
      entries = request.existingDocs
    } else {
      // do normal retrieval
      const intent = this.llmService.classifyIntent(request.query)

      if (intent === 'vector') {
        entries = await this.esService.vectorSearch(request.query, request.topK || 5)
      } else if (intent === 'recent') {
        entries = await this.esService.getRecentEntries(7)
      }
      // if intent === 'none', no retrieval

      // format entries for prompt
      entries.forEach((entry, i) => {
        entriesStr += `entry ${i + 1} (score: ${entry.score || 0}):\n`
        entriesStr += `  title: ${entry.title}\n`
        entriesStr += `  text: ${entry.text}\n`
        entriesStr += `  date: ${entry.date}\n`
        if (entry.tags.length > 0) {
          entriesStr += `  tags: ${entry.tags.join(', ')}\n`
        }
        entriesStr += "\n"
      })
    }

    // get thread message history if thread_id provided
    let threadHistory = ""
    if (request.threadId) {
      const thread: Thread | null = this.threadService.getThread(request.threadId)
      if (thread && thread.messages && thread.messages.length > 0) {
        threadHistory = "\n\nprevious conversation:\n"
        thread.messages.forEach((msg: Message) => {
          const role = msg.role === 'user' ? 'user' : 'assistant'
          threadHistory += `${role}: ${msg.content}\n`
        })
      }
    }

    // also include message history from request if provided (for temporary chats)
    let tempHistory = ""
    if (request.messageHistory && request.messageHistory.length > 0) {
      tempHistory = "\n\ncurrent conversation:\n"
      request.messageHistory.forEach(msg => {
        const role = msg.role === 'user' ? 'user' : 'assistant'
        tempHistory += `${role}: ${msg.content}\n`
      })
    }

    // generate response
    const config: LLMConfig = {
      provider: request.provider as 'anthropic' | 'openai',
      model: request.model
    }

    const response = await this.llmService.generateWithContext(
      request.query,
      entriesStr + threadHistory + tempHistory,
      config
    )

    return {
      response,
      docs: entries,
      threadId: request.threadId
    }
  }
}
