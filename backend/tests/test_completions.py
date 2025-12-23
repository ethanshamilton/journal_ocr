import pytest
import src.completions as completions

SAMPLE_PDF = "data/sample_data/10-2024/10-07-2024 PM.pdf"
SAMPLE_IMAGE = "data/sample_data/06-2023/06-01-2023 AM-128.jpg"

def test_encode_entry():
    """ Test `encode_entry()` with sample image and PDF """
    # test PDF encoding
    pdf = completions.encode_entry(SAMPLE_PDF)
    assert isinstance(pdf, list)
    assert len(pdf) > 0
    assert all(isinstance(encoded, str) for encoded in pdf)

    # test image encoding
    image = completions.encode_entry(SAMPLE_IMAGE)
    assert isinstance(image, list)
    assert len(image) == 1
    assert isinstance(image[0], str)

def test_encode_entry_on_invalid_file():
    with pytest.raises(Exception):
        completions.encode_entry("nonexistent.pdf")

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
    completions.insert_transcription(md_file, test_transcription)

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
    completions.insert_transcription(md_file, new_transcription)
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
    completions.insert_transcription(md_file, new_transcription)
    with open(md_file, 'r') as f:
        content = f.read()

    assert new_transcription in content
    assert "Old transcription text" not in content
    