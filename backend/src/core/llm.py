# llm.py
# shared LLM utilities used by both backend and pipeline
import asyncio
import random

from google import genai

from core.settings import settings

google_client = genai.Client(api_key=settings.credentials.GOOGLE_API_KEY)


async def get_embedding(text: str, max_retries: int = 5) -> list[float] | None:
    """Runs text transcription through Gemini embedding model, retrying on 429 errors."""
    for attempt in range(max_retries):
        try:
            response = await google_client.aio.models.embed_content(
                model=settings.models.embedding_model,
                contents=text
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
            else:
                raise ValueError("No embeddings returned from API")
        except Exception as e:
            print(f"Exception: {e}")
            if "429" in str(e):
                if attempt == max_retries - 1:
                    raise
                base_delay = 2 ** attempt
                jitter = random.uniform(0, 1)
                delay = base_delay + jitter
                print(f"Rate limited, retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
            else:
                raise

