# llm.py
# shared LLM utilities used by both backend and pipeline
import asyncio

from google import genai

from core.settings import settings

google_client = genai.Client(api_key=settings.credentials.GOOGLE_API_KEY)


async def get_embedding(text: str) -> list[float]:
    """Runs text transcription through Gemini embedding model, retrying on 429 errors."""
    try:
        response = await google_client.aio.models.embed_content(
            model=settings.models.embedding_model,
            contents=text,
        )
        if response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
        else:
            raise ValueError("No embeddings returned from API")
    except Exception as _:
        print("Rate limited... retrying in 5")
        await asyncio.sleep(5)
        return await get_embedding(text)
