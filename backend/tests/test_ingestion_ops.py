import pytest
import os
import json

from core.settings import settings
from core.navigation import crawl_journal_entries, extract_tags, duplicate_folder
from pipeline.transcription import encode_entry, insert_transcription
from pipeline.ingestion_ops import transcribe_docs, embed_docs

TEST_DOC_LIMIT = 5


@pytest.fixture
def test_files():
    """Crawl test journal directory and return limited set of files."""
    duplicate_folder(settings.test_settings.test_data_source_dir, settings.test_settings.test_data_dir_path)
    files = crawl_journal_entries(settings.test_settings.test_data_dir_path)
    tags = extract_tags(settings.test_settings.test_data_dir_path)
    return files, tags

@pytest.mark.asyncio
async def test_ingestion_pipeline(test_files):
    files, tags = test_files
    to_transcribe = files.to_transcribe[:TEST_DOC_LIMIT]
    to_embed = files.to_embed[:TEST_DOC_LIMIT]
    embeddings_path = settings.test_settings.test_embedding_storage_path

    if os.path.exists(embeddings_path):
        os.remove(embeddings_path)

    # run transcription before embedding
    await transcribe_docs(to_transcribe, tags)

    # Verify transcriptions were added to markdown files
    for image_path, md_path in to_transcribe:
        assert os.path.exists(md_path), f"Markdown file should exist: {md_path}"
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert "### Transcription" in content, f"Transcription section should be added to {md_path}"

    # run embedding after transcriptions are available
    await embed_docs(to_embed, embeddings_path)

    # Verify embeddings file was created
    assert os.path.exists(embeddings_path), "Embeddings file should be created"

    with open(embeddings_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    assert len(lines) >= 1, "At least one embedding should be written"

    # Verify embedding format
    for line in lines:
        entry = json.loads(line)
        assert "path" in entry, "Embedding entry should have 'path' field"
        assert "embedding" in entry, "Embedding entry should have 'embedding' field"
        assert isinstance(entry["embedding"], list), "Embedding should be a list"
        assert len(entry["embedding"]) > 0, "Embedding should not be empty"

# FILE CRAWLING

def test_crawl_journal_entries(test_files):
    """ Test the `crawl_journal_entries() function using sample data. """
    files, tags = test_files
    # verify files found
    assert len(files.to_transcribe) > 0

    for source_file, md_file in files.to_transcribe:
        # verify source file exists
        assert os.path.exists(source_file)
        # verify markdown files exist or were created
        assert os.path.exists(md_file)
        assert md_file.endswith('.md')
        # validate naming on markdown files
        md_filename = os.path.basename(md_file)
        assert ' ' not in md_filename
        # verify markdown content
        with open(md_file) as f:
            content = f.read()
            assert '![[' in content
            assert os.path.basename(source_file) in content

# FILE PROCESSING STUFF

def test_encode_entry():
    """ Test `encode_entry()` with sample image and PDF """
    # test PDF encoding
    pdf = encode_entry(settings.test_settings.sample_pdf_path)
    assert isinstance(pdf, list)
    assert len(pdf) > 0
    assert all(isinstance(encoded, str) for encoded in pdf)

    # test image encoding
    image = encode_entry(settings.test_settings.sample_image_path)
    assert isinstance(image, list)
    assert len(image) == 1
    assert isinstance(image[0], str)

def test_encode_entry_on_invalid_file():
    with pytest.raises(Exception):
        encode_entry("nonexistent.pdf")

@pytest.fixture
def temp_markdown(tmp_path):
    """ Create a temporary markdown file with different initial states. """
    def _create_markdown(initial_content=""):
        md_file = tmp_path / "test.md"
        with open(md_file, 'w') as f:
            f.write(initial_content)
        return str(md_file)
    return _create_markdown

def test_append_new_transcription(temp_markdown):
    """ Test appending transcription when no transcription section exists. """
    initial_content = """
    # Test Entry
    ### Journal Entry
    ![[test.pdf]]
    """
    md_file = temp_markdown(initial_content)
    test_transcription = "This is an example transcription."
    insert_transcription(md_file, test_transcription)

    # verify content
    with open(md_file, 'r') as f:
        content = f.read()
    
    assert "### Transcription" in content
    assert test_transcription in content

def test_replace_existing_transcription(temp_markdown):
    """ Test replacing an existing transcription. """
    initial_content = """
    # Test Entry
    ### Journal Entry
    ![[test.pdf]]

    ### Transcription
    Old transcription text

    ### Other Section
    Other section text
    """
    md_file = temp_markdown(initial_content)
    new_transcription = "New transcription text"
    insert_transcription(md_file, new_transcription)
    with open(md_file, 'r') as f:
        content = f.read()

    assert "### Transcription" in content
    assert new_transcription in content
    assert "Old transcription text" not in content
    assert "### Other Section" in content
    assert "Other section text" in content

def test_transcription_at_end(temp_markdown):
    """ Ensure replacing transcription at the end of a file works """
    initial_content = """
    # Test Entry
    ### Journal Entry
    ![[test.pdf]]

    ### Transcription
    Old transcription text
    """
    md_file = temp_markdown(initial_content)
    new_transcription = "New transcription"
    insert_transcription(md_file, new_transcription)
    with open(md_file, 'r') as f:
        content = f.read()

    assert new_transcription in content
    assert "Old transcription text" not in content
