# Agent Guidelines for journal_ocr

## Build/Lint/Test Commands
- **Python tests**: `uv run pytest` (all tests) or `uv run pytest tests/test_completions.py::test_encode_entry` (single test)
- **Python env**: Use `uv` for dependency management (Python 3.13+)
- **Backend server**: `uv run uvicorn backend.api:app --reload` (port 8000)
- **Frontend dev**: `cd ui && npm run dev` (Vite, port 5173)
- **Frontend lint**: `cd ui && npm run lint`
- **Frontend build**: `cd ui && npm run build` (TypeScript check + Vite build)

## Code Style Guidelines

### Python
- **Imports**: Group stdlib, third-party, then local imports (see `api.py:1-14`, `completions.py:1-20`)
- **Types**: Use type hints (e.g., `list[str]`, `Optional[T]`, `AsyncGenerator`, `Literal`)
- **Models**: Use Pydantic BaseModel for data structures with Field descriptions (see `models.py`)
- **Async**: Prefer async/await for I/O operations; use `AsyncAnthropic`, `AsyncOpenAI` clients
- **Error handling**: Raise HTTPException for API errors, pytest.raises for test assertions
- **Naming**: snake_case for functions/variables, PascalCase for classes

### TypeScript/React
- **Types**: Use TypeScript interfaces for props and data structures (see `types.tsx`)
- **Imports**: Group React, third-party, local components, services, types, CSS (see `ChatInterface.tsx:1-5`)
- **Components**: Functional components with TypeScript FC<Props> pattern
- **State**: useState/useEffect hooks for local state management
- **API calls**: Centralize in `services/api.ts` using axios
