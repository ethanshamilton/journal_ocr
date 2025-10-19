# setup guide

## 1. install dependencies
```bash
npm install
```

## 2. set up environment variables
create a `.env.local` file in the `ui` directory:

```env
# api keys for llm services (for the api proxy)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# elasticsearch configuration  
VITE_ES_ENDPOINT=http://localhost:9200
```

## 3. start the api proxy
```bash
npm run api
```

## 4. start elasticsearch
make sure elasticsearch is running on localhost:9200

## 5. start the app
```bash
npm run dev
```

## features

- **real llm calls** - anthropic and openai apis
- **elasticsearch integration** - with fallback to mock data
- **localStorage threads** - persistent chat history
- **mock data fallback** - works even without elasticsearch

## troubleshooting

- if elasticsearch isn't running, the app will use mock data
- if api keys aren't set, you'll get errors in the console
- cors issues with elasticsearch are handled with fallbacks
