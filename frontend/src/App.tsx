import { useState, useRef, useEffect } from 'react'
import './App.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [lastResponseId, setLastResponseId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/v1/responses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: 'claude-haiku-4-5-20251001',
          input: userMessage,
          stream: true,  // Enable streaming
          store: true,
          previous_response_id: lastResponseId,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // Handle SSE streaming
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('Response body is not readable')
      }

      let streamedText = ''
      let responseId = ''
      let buffer = '' // Buffer to accumulate partial chunks

      // Add placeholder message for streaming
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])
      const assistantMessageIndex = messages.length + 1 // +1 because we just added the user message

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Decode chunk and add to buffer
        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk

        // Split by double newline to find complete SSE events
        const events = buffer.split('\n\n')

        // Keep the last incomplete event in the buffer for next iteration
        buffer = events.pop() || ''

        // Process complete events
        for (const event of events) {
          const lines = event.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const jsonData = line.slice(6) // Remove 'data: ' prefix

              try {
                const eventData = JSON.parse(jsonData)

                // Handle different event types
                if (eventData.type === 'response.output_text.delta') {
                  // Update streaming text
                  streamedText += eventData.delta
                  setMessages(prev => {
                    const newMessages = [...prev]
                    if (newMessages[assistantMessageIndex]) {
                      newMessages[assistantMessageIndex] = {
                        role: 'assistant',
                        content: streamedText
                      }
                    }
                    return newMessages
                  })
                } else if (eventData.type === 'response.completed') {
                  // Store response ID for multi-turn conversations
                  responseId = eventData.response.id
                  setLastResponseId(responseId)
                }
              } catch (e) {
                // Ignore parse errors for non-JSON lines
              }
            }
          }
        }
      }

    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`
      }])
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
    <div className="app">
      <div className="chat-header">
        <h1>Claude Agent Chat</h1>
        <p className="model-info">Model: claude-haiku-4-5-20251001</p>
      </div>

      <div className="messages-container">
        {messages.length === 0 && (
          <div className="empty-state">
            <p>Start a conversation with Claude Agent</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index} className={`message ${message.role}`}>
            <div className="message-role">{message.role === 'user' ? 'You' : 'Claude'}</div>
            <div className="message-content">{message.content}</div>
          </div>
        ))}

        {isLoading && (
          <div className="message assistant">
            <div className="message-role">Claude</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
          disabled={isLoading}
          rows={3}
        />
        <button onClick={sendMessage} disabled={isLoading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}

export default App
