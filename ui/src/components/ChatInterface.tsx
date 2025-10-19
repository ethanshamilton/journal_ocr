import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { ChatService } from '../services/chat'
import { ThreadService } from '../services/threads'
import type { JournalEntry, Thread, LLMConfig, Message } from '../types'
import './ChatInterface.css'

const providers = [
  {
    label: "anthropic",
    value: "anthropic",
    models: [
      { label: "claude sonnet 4.5", value: "claude-3-5-sonnet-20241022" },
      { label: "claude opus 4", value: "claude-3-5-opus-20241022" },
      { label: "claude sonnet 4", value: "claude-3-5-sonnet-4" }
    ],
  },
  {
    label: "openai",
    value: "openai",
    models: [
      { label: "gpt-5", value: "gpt-5-2025-08-07" }
    ],
  },
]

interface ChatInterfaceProps {
  setDocuments: React.Dispatch<React.SetStateAction<JournalEntry[]>>
  onLoadThread?: (threadId: string, messages: any[]) => void
}

export function ChatInterface({ setDocuments, onLoadThread }: ChatInterfaceProps) {
  const [selectedModel, setSelectedModel] = useState<LLMConfig>({
    provider: "anthropic",
    model: "claude-3-5-sonnet-20241022"
  })

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: "hello! i'm here to help you search through your documents. what would you like to know?",
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null)
  const [isThreadSaved, setIsThreadSaved] = useState(false)
  const [retrievedDocs, setRetrievedDocs] = useState<JournalEntry[]>([])

  const chatService = new ChatService()
  const threadService = new ThreadService()

  const loadThread = (threadId: string, threadMessages: any[]) => {
    setCurrentThreadId(threadId)
    setIsThreadSaved(true)
    setRetrievedDocs([]) // clear retrieved docs when loading a thread
    
    // convert and set the messages
    const convertedMessages: Message[] = threadMessages.map((msg, index) => ({
      id: msg.id || (index + 1).toString(),
      content: msg.content,
      role: msg.role === 'user' ? 'user' : 'assistant',
      timestamp: new Date(msg.timestamp)
    }))
    setMessages(convertedMessages)
  }

  // expose loadThread function to parent
  useEffect(() => {
    if (onLoadThread) {
      (window as any).loadThreadIntoChat = loadThread
    }
  }, [onLoadThread])

  const saveChat = async () => {
    const thread = threadService.createThread()
    setCurrentThreadId(thread.id)
    setIsThreadSaved(true)
    
    // save all existing messages to the new thread
    try {
      for (const message of messages) {
        if (message.role !== 'assistant' || !message.content.includes("hello! i'm here to help")) {
          await threadService.addMessage(thread.id, message.role, message.content)
        }
      }
    } catch (error) {
      console.error('error saving existing messages to thread:', error)
    }
  }

  const startNewChat = () => {
    setCurrentThreadId(null)
    setIsThreadSaved(false)
    setRetrievedDocs([])
    setMessages([{
      id: '1',
      role: 'assistant',
      content: "hello! i'm here to help you search through your documents. what would you like to know?",
      timestamp: new Date()
    }])
  }

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const query = input
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      let similarDocs: JournalEntry[] = []
      let responseText = ""
      
      // only do retrieval if this is the first message or we don't have docs yet
      if (retrievedDocs.length === 0) {
        // query journal with retrieval
        const combinedResponse = await chatService.queryJournal({
          query,
          topK: 5, 
          provider: selectedModel.provider,
          model: selectedModel.model,
          threadId: currentThreadId || undefined,
          messageHistory: isThreadSaved ? undefined : messages // only send history for temporary chats
        })
        
        similarDocs = combinedResponse.docs
        setRetrievedDocs(similarDocs)
        setDocuments(similarDocs)
        responseText = combinedResponse.response
      } else {
        // use existing docs, just query with context
        const response = await chatService.queryJournal({
          query,
          topK: 0, // no retrieval needed
          provider: selectedModel.provider,
          model: selectedModel.model,
          threadId: currentThreadId || undefined,
          messageHistory: isThreadSaved ? undefined : messages,
          existingDocs: retrievedDocs
        })
        
        responseText = response.response
      }

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responseText,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, botMessage])

      // save messages to thread if we have one and it's saved
      if (currentThreadId && isThreadSaved) {
        try {
          await threadService.addMessage(currentThreadId, 'user', query)
          await threadService.addMessage(currentThreadId, 'assistant', responseText)
        } catch (error) {
          console.error('error saving messages to thread:', error)
        }
      }
    } catch (error) {
      console.error('error querying api:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'sorry, i encountered an error while processing your request.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="chat-title">
          <h3>journal chat</h3>
          {currentThreadId && (
            <div className="thread-info">
              <span className="thread-id">thread: {currentThreadId.slice(0, 8)}...</span>
            </div>
          )}
        </div>
        <div className="chat-actions">
          {!isThreadSaved && (
            <button onClick={saveChat} className="save-chat-btn">
              save chat
            </button>
          )}
          <button onClick={startNewChat} className="new-chat-btn">
            new chat
          </button>
        </div>
        <select
          value={`${selectedModel.provider}:${selectedModel.model}`}
          onChange={e => {
            const [provider, model] = e.target.value.split(":")
            setSelectedModel({ provider: provider as 'anthropic' | 'openai', model })
          }}
        >
          {providers.map(provider => (
            <optgroup key={provider.value} label={provider.label}>
              {provider.models.map(model => (
                <option
                  key={`${provider.value}-${model.value}`}
                  value={`${provider.value}:${model.value}`}
                >
                  {model.label}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
      
      <div className="chat-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.role === 'user' ? 'user-message' : 'bot-message'}`}
          >
            <div className="message-content">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            <div className="message-timestamp">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message bot-message">
            <div className="message-content loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
      </div>
      
      <form onSubmit={sendMessage} className="chat-input">
        <div className="input-container">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="ask a question about your documents..."
            rows={3}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="send-button"
          >
            send
          </button>
        </div>
      </form>
    </div>
  )
}
