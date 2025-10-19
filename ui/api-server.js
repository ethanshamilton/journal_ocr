import express from 'express'
import cors from 'cors'
import fetch from 'node-fetch'
import dotenv from 'dotenv'

dotenv.config()

const app = express()
app.use(cors())
app.use(express.json())

// elasticsearch proxy endpoint
app.post('/api/es/search', async (req, res) => {
  try {
    const { query, topK } = req.body
    
    const response = await fetch('http://localhost:9200/journals/_search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        size: topK || 5,
        query: {
          match: {
            text: query
          }
        }
      })
    })
    
    const data = await response.json()
    const results = data.hits.hits.map((hit) => ({
      id: hit._id,
      title: hit._source.title,
      text: hit._source.text,
      date: hit._source.date,
      tags: hit._source.tags || [],
      score: hit._score
    }))
    
    res.json({ results })
  } catch (error) {
    console.error('elasticsearch proxy error:', error)
    res.status(500).json({ error: 'elasticsearch call failed' })
  }
})

app.post('/api/es/recent', async (req, res) => {
  try {
    const { n } = req.body
    
    const response = await fetch('http://localhost:9200/journals/_search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        size: n || 7,
        sort: [{ date: { order: 'desc' } }],
        query: { match_all: {} }
      })
    })
    
    const data = await response.json()
    const results = data.hits.hits.map((hit) => ({
      id: hit._id,
      title: hit._source.title,
      text: hit._source.text,
      date: hit._source.date,
      tags: hit._source.tags || [],
      score: hit._score
    }))
    
    res.json({ results })
  } catch (error) {
    console.error('elasticsearch proxy error:', error)
    res.status(500).json({ error: 'elasticsearch call failed' })
  }
})

// llm proxy endpoint
app.post('/api/llm', async (req, res) => {
  try {
    const { provider, model, prompt } = req.body
    
    if (provider === 'anthropic') {
      // map frontend model names to actual anthropic model names
      const modelMap = {
        'claude-3-5-sonnet-20241022': 'claude-3-5-sonnet-20241022',
        'claude-3-5-opus-20241022': 'claude-3-5-opus-20241022', 
        'claude-3-5-sonnet-4': 'claude-3-5-sonnet-4'
      }
      const actualModel = modelMap[model] || 'claude-3-5-sonnet-20241022'
      
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'x-api-key': process.env.ANTHROPIC_API_KEY,
          'Content-Type': 'application/json',
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify({
          model: actualModel,
          max_tokens: 1024,
          messages: [{ role: 'user', content: prompt }]
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error('anthropic api error:', errorData)
        return res.status(response.status).json({ error: errorData })
      }
      
      const data = await response.json()
      return res.json({ response: data.content[0].text })
    } else if (provider === 'openai') {
      console.log('openai request:', { model, prompt: prompt.substring(0, 100) + '...' })
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: prompt }],
          max_completion_tokens: 4096
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        console.error('openai api error:', errorData)
        return res.status(response.status).json({ error: errorData })
      }
      
      const data = await response.json()
      return res.json({ response: data.choices[0].message.content })
    } else {
      return res.status(400).json({ error: 'unsupported provider' })
    }
  } catch (error) {
    console.error('llm proxy error:', error)
    res.status(500).json({ error: 'llm call failed' })
  }
})

const port = process.env.PORT || 3000
app.listen(port, () => {
  console.log(`api server running on port ${port}`)
})
