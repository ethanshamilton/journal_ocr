import type { JournalEntry, SearchRequest, SearchResponse } from '../types/index'

export class ElasticsearchService {
  private baseUrl = 'http://localhost:9200'

  async searchEntries(request: SearchRequest): Promise<SearchResponse> {
    try {
      const response = await fetch('/api/es/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: request.query,
          topK: request.topK || 5
        })
      })

      if (!response.ok) {
        throw new Error(`elasticsearch proxy failed: ${response.statusText}`)
      }

      const data = await response.json()
      return { results: data.results }
    } catch (error) {
      console.error('elasticsearch error:', error)
      // fallback to mock data
      return {
        results: [
          {
            id: 'mock-1',
            title: 'sample journal entry',
            text: 'this is a sample journal entry for testing',
            date: '2024-01-01',
            tags: ['test'],
            score: 0.95
          }
        ]
      }
    }
  }

  async getRecentEntries(n: number = 7): Promise<JournalEntry[]> {
    try {
      const response = await fetch('/api/es/recent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n })
      })

      if (!response.ok) {
        throw new Error(`elasticsearch proxy failed: ${response.statusText}`)
      }

      const data = await response.json()
      return data.results
    } catch (error) {
      console.error('elasticsearch error:', error)
      // fallback to mock data
      return [
        {
          id: 'recent-1',
          title: 'recent entry 1',
          text: 'this is a recent journal entry',
          date: '2024-01-15',
          tags: ['recent'],
          score: 1.0
        }
      ]
    }
  }

  async vectorSearch(query: string, topK: number = 5): Promise<JournalEntry[]> {
    // this would need the query embedding - for now return regular search
    return this.searchEntries({ query, topK }).then(r => r.results)
  }
}
