import { NextRequest, NextResponse } from 'next/server'
import { generateText } from 'ai'
import { anthropic } from '@ai-sdk/anthropic'
import { openai } from '@ai-sdk/openai'

export async function POST(req: NextRequest) {
  try {
    const { messages, model, provider } = await req.json()

    const aiModel = provider === 'anthropic' 
      ? anthropic(model)
      : openai(model)

    const result = await generateText({
      model: aiModel,
      messages: messages.map((msg: any) => ({
        role: msg.role,
        content: msg.content
      }))
    })

    return NextResponse.json({ 
      content: result.text,
      role: 'assistant'
    })
  } catch (error) {
    console.error('chat api error:', error)
    return NextResponse.json(
      { error: 'failed to generate response' },
      { status: 500 }
    )
  }
}
