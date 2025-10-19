#!/bin/bash

echo "🚀 installing dependencies for client-side journal ocr app..."

# install new dependencies
npm install ai @ai-sdk/anthropic @ai-sdk/openai date-fns uuid

echo "✅ dependencies installed!"
echo ""
echo "next steps:"
echo "1. set up your api keys in .env.local:"
echo "   ANTHROPIC_API_KEY=your_key_here"
echo "   OPENAI_API_KEY=your_key_here"
echo ""
echo "2. make sure elasticsearch is running on localhost:9200"
echo ""
echo "3. run: npm run dev"
echo ""
echo "the app is now client-side only! 🎉"
