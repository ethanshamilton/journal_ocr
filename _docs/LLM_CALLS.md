# LLM Calls Analysis - Instructor Framework Usage

This document identifies all locations in the backend where the instructor framework is used for LLM calls. These are the points that need to be migrated to BAML.

## Summary

The instructor framework is used in **5 distinct locations** across the codebase, all in `completions.py`. These handle structured LLM outputs using Pydantic models.

## Detailed Breakdown

### 1. Intent Classification -- FIXED
**Location:** `completions.py:135-142`  
**Function:** `intent_classifier(query: str) -> str`  
**Pydantic Model:** `QueryIntent` (models.py:23-24)  
**Purpose:** Classifies user queries to determine retrieval strategy (RECENT, VECTOR, or NONE)  
**Provider:** OpenAI (gpt-5-mini-2025-08-07)  
**Called from:** 
- `flows.py:122` in `default_llm_flow`
- `flows.py:173` in `default_llm_flow_stream`

---

### 2. Prompt Generation
**Location:** `completions.py:162-194`  
**Function:** `prompt_generator(client: instructor.AsyncInstructor, prompt: str, step: Literal["SUBYEAR", "YEAR", "FINAL"]) -> str`  
**Pydantic Model:** `str` (built-in type)  
**Purpose:** Dynamically generates prompts for multi-step analysis  
**Provider:** Flexible (passed as parameter)  
**Called from:** 
- `completions.py:276` in `comprehensive_analysis`

---

### 3. Helper Function: Get Instructor Client
**Location:** `completions.py:196-203`  
**Function:** `_get_async_instructor_client(provider: str) -> instructor.AsyncInstructor`  
**Purpose:** Factory function to create provider-specific instructor clients (anthropic/openai)  
**Called from:** Functions #4, #5, and #6 below

---

### 4. Direct Chat Response -- FIXED
**Location:** `completions.py:205-236`  
**Function:** `chat_response(request: ChatRequest, chat_history: list, entries_str: str) -> str`  
**Pydantic Model:** `DirectChatResponse` (models.py:26-28)  
**Purpose:** Standard chat completion with structured output  
**Provider:** Flexible (anthropic/openai via request)  
**Called from:** 
- `flows.py:150` in `default_llm_flow`

---

### 5. Streaming Chat Response -- REMOVED
**Location:** `completions.py:238-266`  
**Function:** `chat_response_stream(request: ChatRequest, chat_history: list, entries_str: str) -> AsyncGenerator[DirectChatResponse, None]`  
**Pydantic Model:** `DirectChatResponse` (models.py:26-28)  
**Purpose:** Streaming version of chat completion with partial structured outputs  
**Provider:** Flexible (anthropic/openai via request)  
**Uses:** `client.chat.completions.create_partial()` for streaming  
**Called from:** 
- `flows.py:201` in `default_llm_flow_stream`

---

### 6. Comprehensive Analysis
**Location:** `completions.py:268-322`  
**Function:** `comprehensive_analysis(request: ChatRequest, chat_history: list, entries_str: str, step: Literal["SUBYEAR", "YEAR", "FINAL"]) -> ComprehensiveAnalysis`  
**Pydantic Model:** `ComprehensiveAnalysis` (models.py:30-33)  
**Purpose:** Multi-step analysis with structured output including reasoning, analysis, and excerpts  
**Provider:** Flexible (anthropic/openai via request)  
**Special Features:** Includes retry logic with exponential backoff for rate limiting  
**Called from:** 
- `flows.py:56` (YEAR step)
- `flows.py:60` (SUBYEAR step)
- `flows.py:71` (YEAR step for subyear aggregation)
- `flows.py:81` (FINAL step)

---

## Dependencies

**Import:** `completions.py:6`  
**Package:** `pyproject.toml:12` - `"instructor>=1.11.3"`

---

## Pydantic Models to Migrate

All these models need to be translated to BAML schemas:

1. **`QueryIntent`** (models.py:23-24)
   - Field: `intent: SearchOptions` (Enum: RECENT, VECTOR, NONE)

2. **`DirectChatResponse`** (models.py:26-28)
   - Field: `response: str`

3. **`ComprehensiveAnalysis`** (models.py:30-33)
   - Field: `reasoning: str`
   - Field: `analysis: str`
   - Field: `excerpts: list[str]`

---

## Migration Considerations

### Questions to Address:

1. **Multi-provider support:** Currently the code supports both OpenAI and Anthropic dynamically. Does BAML handle provider switching as elegantly, or should we lock to one provider per function?

2. **Streaming support:** The `chat_response_stream` function uses instructor's `create_partial` for streaming structured outputs. Does BAML have equivalent streaming capabilities for partial Pydantic model parsing?

3. **Retry logic:** The `comprehensive_analysis` function has custom retry logic with exponential backoff. Should this be preserved in the BAML migration or does BAML handle this internally?

4. **Prompt generation:** The `prompt_generator` function uses instructor to return a raw `str` type (not a complex model). Is this a pattern we want to keep in BAML, or should we use standard API calls for simple string responses?

5. **Error handling:** Currently rate limit errors are detected by string matching in exception messages. Should we implement more robust error handling during migration?

---

## Migration Strategy

### Phase 1: Simple Models
- Migrate `QueryIntent` (simplest - single enum field)
- Migrate `DirectChatResponse` (simple - single string field)

### Phase 2: Complex Models
- Migrate `ComprehensiveAnalysis` (complex - multiple fields including list)
- Migrate `prompt_generator` (special case - returns raw string)

### Phase 3: Integration
- Update `_get_async_instructor_client` to use BAML
- Test streaming functionality
- Verify retry logic works correctly
- Update all callsites in `flows.py`

### Phase 4: Cleanup
- Remove instructor dependency from `pyproject.toml`
- Remove instructor import from `completions.py`
- Update tests to use BAML patterns
