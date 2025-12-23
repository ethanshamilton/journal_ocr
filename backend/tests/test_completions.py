import pytest
import backend.completions as completions
from backend.models import SearchOptions

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


### Intent Classifier Tests

@pytest.mark.asyncio
async def test_intent_classifier_returns_valid_response():
    """Test that intent_classifier returns a successful response from the LLM."""
    query = "What have I been thinking about lately?"
    result = await completions.intent_classifier(query)
    
    # Verify we get a valid SearchOptions value
    assert isinstance(result, str)
    assert result in [opt.value for opt in SearchOptions]


@pytest.mark.asyncio
async def test_intent_classifier_vector_route():
    """Test that vector search is selected for semantic/topical queries."""
    test_queries = [
        "What were my thoughts about machine learning?",
        "Tell me about times I felt anxious",
        "What did I write about relationships?",
        "Find entries related to career decisions"
    ]
    
    for query in test_queries:
        result = await completions.intent_classifier(query)
        assert result == SearchOptions.VECTOR.value, f"Query '{query}' should return VECTOR, got {result}"


@pytest.mark.asyncio
async def test_intent_classifier_recent_route():
    """Test that recent search is selected for temporal/recent queries."""
    test_queries = [
        "What have I been up to recently?",
        "What did I write about lately?",
        "Show me my recent thoughts",
        "What have I been thinking about over the past week?",
        "What happened in the last few days?"
    ]
    
    for query in test_queries:
        result = await completions.intent_classifier(query)
        assert result == SearchOptions.RECENT.value, f"Query '{query}' should return RECENT, got {result}"


@pytest.mark.asyncio
async def test_intent_classifier_none_route():
    """Test that NONE is selected for queries that don't need retrieval."""
    test_queries = [
        "Hello, how are you?",
        "Thanks for your help!",
        "Can you help me understand how this works?",
        "What can you do?"
    ]
    
    for query in test_queries:
        result = await completions.intent_classifier(query)
        assert result == SearchOptions.NONE.value, f"Query '{query}' should return NONE, got {result}"


@pytest.mark.asyncio
async def test_intent_classifier_coverage():
    """Test that all SearchOptions enum values can be returned."""
    # Collect results from various queries
    vector_query = "What did I write about artificial intelligence?"
    recent_query = "What have I written lately?"
    none_query = "Hello!"
    
    vector_result = await completions.intent_classifier(vector_query)
    recent_result = await completions.intent_classifier(recent_query)
    none_result = await completions.intent_classifier(none_query)
    
    results = {vector_result, recent_result, none_result}
    
    # Verify we got all three distinct values
    assert SearchOptions.VECTOR.value in results, "VECTOR route should be reachable"
    assert SearchOptions.RECENT.value in results, "RECENT route should be reachable"
    assert SearchOptions.NONE.value in results, "NONE route should be reachable"
    
    # Verify all are distinct
    assert len(results) == 3, f"Expected 3 distinct results, got {len(results)}: {results}"
    