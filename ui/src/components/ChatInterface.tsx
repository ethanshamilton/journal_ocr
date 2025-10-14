import { useState, useEffect } from 'react'
import './ChatInterface.css'
import { apiService } from '../services/api'
import type { Document, ThreadMessage } from '../types'
import ReactMarkdown from 'react-markdown'

const providers = [
  {
    label: "Anthropic",
    value: "anthropic",
    models: [
      { label: "Claude Sonnet 4.5", value: "claude-sonnet-4-5-20250929" },
      { label: "Claude Opus 4", value: "claude-opus-4-20250514" },
      { label: "Claude Sonnet 4", value: "claude-sonnet-4-20250514" }
    ],
  },
  {
    label: "OpenAI",
    value: "openai",
    models: [
      { label: "GPT-4.1", value: "gpt-4.1" },
      { label: "GPT-4.5", value: "gpt-4.5-preview" },
    ],
  },
]

interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
}

interface ChatInterfaceProps {
  setDocuments: React.Dispatch<React.SetStateAction<Document[]>>
  onLoadThread?: (threadId: string, messages: ThreadMessage[]) => void
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ setDocuments, onLoadThread }) => {

  const [selectedModel, setSelectedModel] = useState({
    provider: "anthropic",
    model: "claude-opus-4-20250514"
  })

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Hello! I'm here to help you search through your documents. What would you like to know?",
      sender: 'bot',
      timestamp: new Date()
    }
  ])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null)
  const [isThreadSaved, setIsThreadSaved] = useState(false)
  const [retrievedDocs, setRetrievedDocs] = useState<Document[]>([])

  const loadThread = (threadId: string, threadMessages: ThreadMessage[]) => {
    setCurrentThreadId(threadId)
    setIsThreadSaved(true) // loaded threads are already saved
    const convertedMessages = threadMessages.map((msg, index) => ({
      id: index + 1,
      text: msg.content,
      sender: msg.role === 'user' ? 'user' as const : 'bot' as const,
      timestamp: new Date(msg.timestamp)
    }))
    setMessages(convertedMessages)
    setRetrievedDocs([]) // clear retrieved docs when loading a thread
  }

  // expose loadThread function to parent
  useEffect(() => {
    if (onLoadThread) {
      // this is a bit hacky but works for now
      (window as any).loadThreadIntoChat = loadThread
    }
  }, [onLoadThread])

  const saveChat = async () => {
    const response = await apiService.createThread()
    setCurrentThreadId(response.thread_id)
    setIsThreadSaved(true)
    
    // save all existing messages to the new thread
    try {
      for (const message of messages) {
        if (message.sender !== 'bot' || message.text !== "Hello! I'm here to help you search through your documents. What would you like to know?") {
          await apiService.addMessageToThread(response.thread_id, message.sender === 'user' ? 'user' : 'assistant', message.text)
        }
      }
    } catch (error) {
      console.error('Error saving existing messages to thread:', error)
    }
  }

  const startNewChat = () => {
    setCurrentThreadId(null)
    setIsThreadSaved(false)
    setRetrievedDocs([]) // clear retrieved docs for new chat
    setMessages([{
      id: 1,
      text: "Hello! I'm here to help you search through your documents. What would you like to know?",
      sender: 'bot',
      timestamp: new Date()
    }])
  }

  const sendMessage = async () => {
    if (!inputText.trim()) return

    const query = inputText
    const userMessage: Message = {
      id: Date.now(),
      text: query,
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      let similarDocs: Document[] = []
      let responseText = ""
      
      // only do retrieval if this is the first message or we don't have docs yet
      if (retrievedDocs.length === 0) {
        // query journal with retrieval
        const combinedResponse = await apiService.queryJournal({
            query,
            top_k: 5, 
            provider: selectedModel.provider,
            model: selectedModel.model,
            thread_id: currentThreadId || "",
            message_history: isThreadSaved ? undefined : messages // only send history for temporary chats
          })
        
        // Prepare similar entries to be sent to DocumentViewer
        similarDocs = combinedResponse.docs.map(([entry], i) => ({
          id: i + 1,
          title: entry.title || `Similar Entry ${i + 1}`,
          content: entry.text || JSON.stringify(entry)
        }))
        
        setRetrievedDocs(similarDocs)
        setDocuments(similarDocs)
        responseText = combinedResponse.response
        
        // get the response from the combined response
        const botMessage: Message = {
          id: Date.now() + 1,
          text: combinedResponse.response,
          sender: 'bot',
          timestamp: new Date()
        }
        setMessages(prev => [...prev, botMessage])
      } else {
        // use existing docs, just query with context
        const response = await apiService.queryJournal({
            query,
            top_k: 0, // no retrieval needed
            provider: selectedModel.provider,
            model: selectedModel.model,
            thread_id: currentThreadId || "",
            message_history: isThreadSaved ? undefined : messages,
            existing_docs: retrievedDocs // pass existing docs
          })
        
        responseText = response.response
        const botMessage: Message = {
          id: Date.now() + 1,
          text: response.response,
          sender: 'bot',
          timestamp: new Date()
        }
        setMessages(prev => [...prev, botMessage])
      }

      // save messages to thread if we have one and it's saved
      if (currentThreadId && isThreadSaved) {
        try {
          await apiService.addMessageToThread(currentThreadId, 'user', query)
          await apiService.addMessageToThread(currentThreadId, 'assistant', responseText)
        } catch (error) {
          console.error('Error saving messages to thread:', error)
        }
      }
    } catch (error) {
      console.error('Error querying API:', error)
      const errorMessage: Message = {
        id: Date.now() + 1,
        text: 'Sorry, I encountered an error while processing your request. Please make sure the backend is running.',
        sender: 'bot',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-interface">
      <div className="chat-header">
        <div className="chat-title">
          <h3>Journal Chat</h3>
          {currentThreadId && (
            <div className="thread-info">
              <span className="thread-id">Thread: {currentThreadId.slice(0, 8)}...</span>
            </div>
          )}
        </div>
        <div className="chat-actions">
          {!isThreadSaved && (
            <button onClick={saveChat} className="save-chat-btn">
              Save Chat
            </button>
          )}
          <button onClick={startNewChat} className="new-chat-btn">
            New Chat
          </button>
        </div>
        <select
          value={`${selectedModel.provider}:${selectedModel.model}`}
          onChange={e => {
            const[provider, model] = e.target.value.split(":");
            setSelectedModel({ provider, model })
          }}
        >
          {providers.map(provider => (
            <optgroup key={provider.value} label={provider.label}>
              {provider.models.map(model => (
                <option
                  key={model.value}
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
            className={`message ${message.sender === 'user' ? 'user-message' : 'bot-message'}`}
          >
            <div className="message-content">
              <ReactMarkdown>{message.text}</ReactMarkdown>
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
      
      <div className="chat-input">
        <div className="input-container">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your documents..."
            rows={3}
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputText.trim() || isLoading}
            className="send-button"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatInterface
