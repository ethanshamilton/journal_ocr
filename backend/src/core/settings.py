import os

from dotenv import load_dotenv
from pydantic import BaseModel

_ = load_dotenv()

class Credentials(BaseModel):
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

class FileStorageSettings(BaseModel):
    chat_storage_path: str = "/Users/hamiltones/code/journal_ocr_ext/journal_ocr/data/chats.json"
    embedding_storage_path: str = "/Users/hamiltones/OneDrive/Journal/embeddings.jsonl"
    journal_storage_path: str = "/Users/hamiltones/OneDrive/Journal/Daily Pages"
    evergreen_storage_path: str = "/Users/hamiltones/OneDrive/Journal/Evergreen"

class ModelSettings(BaseModel):
    embedding_model: str = "gemini-embedding-001" # Google models only
    transcription_model: str = "gpt-5" # OpenAI models only

class TestSettings(BaseModel):
    test_data_source_dir: str = "/Users/hamiltones/OneDrive/Journal/test"
    test_data_dir_path: str = "/Users/hamiltones/code/journal_ocr_ext/test_data/test_journal"
    sample_pdf_path: str = f"/Users/hamiltones/code/journal_ocr_ext/test_data/samples/sample.pdf"
    sample_image_path: str = f"/Users/hamiltones/code/journal_ocr_ext/test_data/samples/sample.jpg"
    test_embedding_storage_path: str = f"{test_data_dir_path}/embeddings.jsonl"

class Settings(BaseModel):
    credentials: Credentials = Credentials()
    file_storage: FileStorageSettings = FileStorageSettings()
    models: ModelSettings = ModelSettings()
    test_settings: TestSettings = TestSettings()

settings = Settings()
