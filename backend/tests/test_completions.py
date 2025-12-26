import pytest

from backend.completions import intent_classifier
from core.baml_client.async_client import b
from core.baml_client.types import SearchOptions
from pipeline.transcription import encode_entry, insert_transcription


### Intent Classifier Tests

@pytest.mark.asyncio
async def test_intent_classifier_returns_valid_response():
    """Test that intent_classifier returns a successful response from the LLM."""
    query = "What have I been thinking about lately?"
    result = await intent_classifier(query)
    
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
    ]
    
    for query in test_queries:
        result = await intent_classifier(query)
        assert result == SearchOptions.VECTOR.value, f"Query '{query}' should return VECTOR, got {result}"


@pytest.mark.asyncio
async def test_intent_classifier_recent_route():
    """Test that recent search is selected for temporal/recent queries."""
    test_queries = [
        "What did I write about lately?",
        "Show me my recent thoughts",
        "What have I been thinking about over the past week?",
    ]
    
    for query in test_queries:
        result = await intent_classifier(query)
        assert result == SearchOptions.RECENT.value, f"Query '{query}' should return RECENT, got {result}"
   
