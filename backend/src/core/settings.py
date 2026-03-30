import os

from dotenv import load_dotenv
from pydantic import BaseModel

_ = load_dotenv()

class Credentials(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

class FileStorageSettings(BaseModel):
    chat_storage_path: str = "/home/neurostack/code/journal_ocr/data/chats.json"
    embedding_storage_path: str = "/mnt/c/Users/Administrator/OneDrive/Journal/embeddings.jsonl"
    journal_storage_path: str = "/mnt/c/Users/Administrator/OneDrive/Journal/Daily Pages"
    evergreen_storage_path: str = "/mnt/c/Users/Administrator/OneDrive/Journal/Evergreen"

class ModelSettings(BaseModel):
    embedding_model: str = "gemini-embedding-001" # Google models only
    transcription_model: str = "gpt-5" # OpenAI models only

class TestSettings(BaseModel):
    test_data_source_dir: str = ""
    test_data_dir_path: str = ""
    sample_pdf_path: str = ""
    sample_image_path: str = ""
    test_embedding_storage_path: str = f"{test_data_dir_path}/embeddings.jsonl"

class Settings(BaseModel):
    credentials: Credentials = Credentials()
    file_storage: FileStorageSettings = FileStorageSettings()
    models: ModelSettings = ModelSettings()
    test_settings: TestSettings = TestSettings()

settings = Settings()
