import { useState } from 'react'
import './ChatInterface.css'
import { apiService } from '../services/api'
import type { Document } from '../types'
import ReactMarkdown from 'react-markdown'

const providers = [
  {
    label: "Anthropic",
    value: "anthropic",
    models: [
      { label: "Claude Opus 4", value: "claude-opus-4-20250514" },
      { label: "Claude Sonnet 4", value: "claude-sonnet-4-20250514" },
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
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ setDocuments }) => {

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
      // query journal
      const combinedResponse = await apiService.queryJournal({
          query,
          top_k: 5, 
          provider: selectedModel.provider,
          model: selectedModel.model
        })
      
      // Prepare similar entries to be sent to DocumentViewer
      const similarDocs: Document[] = combinedResponse.docs.map(([entry, score], i) => ({
        id: i + 1,
        title: entry.title || `Similar Entry ${i + 1}`,
        content: entry.text || JSON.stringify(entry)
      }))

      setDocuments(similarDocs)

      const botMessage: Message = {
        id: Date.now() + 1,
        text: combinedResponse.response,
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
        <h3>Journal Chat</h3>
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
