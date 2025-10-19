import type { LLMConfig } from '../types'

export class LLMService {
  async generateResponse(prompt: string, config: LLMConfig): Promise<string> {
    if (config.provider === 'anthropic') {
      return this.callAnthropic(prompt, config.model)
    } else {
      return this.callOpenAI(prompt, config.model)
    }
  }

  private async callAnthropic(prompt: string, model: string): Promise<string> {
    const response = await fetch('/api/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'anthropic',
        model,
        prompt
      })
    })

    if (!response.ok) {
      throw new Error(`llm proxy error: ${response.statusText}`)
    }

    const data = await response.json()
    return data.response
  }

  private async callOpenAI(prompt: string, model: string): Promise<string> {
    const response = await fetch('/api/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'openai',
        model,
        prompt
      })
    })

    if (!response.ok) {
      throw new Error(`llm proxy error: ${response.statusText}`)
    }

    const data = await response.json()
    return data.response
  }

  async generateWithContext(
    query: string, 
    context: string, 
    config: LLMConfig
  ): Promise<string> {
    const prompt = `
i am giving you access to some of my journal entries in order to help answer the following question:
${query}

here are the journal entries:
${context}
`

    return this.generateResponse(prompt, config)
  }

  classifyIntent(query: string): 'vector' | 'recent' | 'none' {
    const recentKeywords = ['recent', 'lately', 'last', 'this week', 'today', 'yesterday']
    const hasRecentIntent = recentKeywords.some(keyword => 
      query.toLowerCase().includes(keyword)
    )
    
    if (hasRecentIntent) return 'recent'
    if (query.trim().length < 3) return 'none'
    return 'vector'
  }
}
