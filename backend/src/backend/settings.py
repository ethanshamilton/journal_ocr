import os

from dotenv import load_dotenv
from pydantic import BaseModel

_ = load_dotenv()

class Credentials(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

class LanceDBSettings(BaseModel):
    chat_storage_path: str = "/Users/hamiltones/code/journal_ocr_ext/journal_ocr/data/chats.json"
    embedding_storage_path: str = "/Users/hamiltones/Documents/Journal/embeddings.json"
    journal_storage_path: str = "/Users/hamiltones/Documents/Journal/Daily Pages"

class ModelSettings(BaseModel):
    embedding_model: str = "gemini-embedding-exp-03-07" # Google models only
    transcription_model: str = "gpt-5.2" # OpenAI models only

class Settings(BaseModel):
    credentials: Credentials = Credentials()
    lancedb: LanceDBSettings = LanceDBSettings()
    models: ModelSettings = ModelSettings()

settings = Settings()
