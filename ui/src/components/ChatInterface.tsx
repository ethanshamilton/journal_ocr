import { useState } from 'react'
import './ChatInterface.css'
import { apiService } from '../services/api'
import type { Document } from '../types'

interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
  timestamp: Date
}

interface ChatInterfaceProps {
  setDocuments: React.Dispatch<React.SetStateAction<Document[]>>
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ setDocuments }) => {
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
      // Get similar entries from backend
      const similarEntries = await apiService.getSimilarEntries({ query, top_k: 5 })
      
      // Prepare similar entries to be sent to DocumentViewer
      const similarDocs: Document[] = similarEntries.results.map(([entry, score], i) => ({
        id: i + 1,
        title: entry.title || `Similar Entry ${i + 1}`,
        content: entry.text || JSON.stringify(entry)
      }))

      setDocuments(similarDocs)

      // Build context from similar entries
      let entriesStr = ""
      similarEntries.results.forEach(([entry, score], i) => {
        entriesStr += `Entry ${i + 1} (Score: ${score}):\n`
        Object.entries(entry).forEach(([k, v]) => {
          if (k !== "embedding") {
            entriesStr += `  ${k}: ${v}\n`
          }
        })
        entriesStr += "\n"
      })

      // Query LLM with context
      const prompt = `I am giving you access to some of my journal entries in order to help answer the following question:
${query}

Here are the journal entries:
${entriesStr}

Please don't respond in markdown, just plain text.`

      const llmResponse = await apiService.queryLLM({
        prompt,
        provider: "anthropic",
        model: "claude-sonnet-4-20250514"
      })

      const botMessage: Message = {
        id: Date.now() + 1,
        text: llmResponse.response,
        sender: 'bot',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, botMessage])
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
        <h3>Chat Assistant</h3>
      </div>
      
      <div className="chat-messages">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`message ${message.sender === 'user' ? 'user-message' : 'bot-message'}`}
          >
            <div className="message-content">
              {message.text}
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
