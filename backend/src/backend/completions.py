# completions.py
# code for dealing with LLM stuff in the app
import logging
from pathlib import Path

from baml_py import ClientRegistry

from core.baml_client.async_client import b
from core.baml_client.types import SearchOptions, SearchToolCall
from core.models import ChatRequest
from core.llm import get_embedding
from backend.personalities import Personality

logger = logging.getLogger(__name__)

CUSTOM_INSTRUCTIONS_PATH = Path(__file__).resolve().parents[3] / "CUSTOM_INSTRUCTIONS.md"


def load_custom_instructions() -> str:
    """Load optional user-provided instructions from CUSTOM_INSTRUCTIONS.md."""
    try:
        if not CUSTOM_INSTRUCTIONS_PATH.exists():
            return ""
        return CUSTOM_INSTRUCTIONS_PATH.read_text(encoding="utf-8").strip()
    except Exception as e:
        logger.warning(f"Failed to load custom instructions from {CUSTOM_INSTRUCTIONS_PATH}: {e}")
        return ""


async def intent_classifier(query: str) -> SearchOptions:
    return await b.IntentClassifier(query)


async def classify_personality(query: str, personalities: list[Personality]) -> Personality | None:
    """Classify the query and return the matching personality, or None for default."""
    if not personalities:
        return None

    options_str = "\n".join(
        f"- {p.title}: {p.description}" for p in personalities
    )
    selected_title = await b.PersonalityClassifier(query, options_str)
    selected_title = selected_title.strip()

    for p in personalities:
        if p.title.lower() == selected_title.lower():
            logger.info(f"Selected personality: {p.title}")
            return p

    logger.info(f"Classifier returned '{selected_title}', no match found — using default")
    return None


async def chat_response(request: ChatRequest, chat_history: list, entries_str: str, personality_prompt: str = "") -> str:
    cr = ClientRegistry()
    cr.set_primary(f"{request.provider}/{request.model}")
    custom_instructions = load_custom_instructions()

    # prepare messages list
    chat_history.append({
        "role": "user",
        "content": f"""
        <QUERY>{request.query}</QUERY>
        """
    })

    # convert messages to string for LLM
    messages_intermediate = []
    for msg in chat_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        messages_intermediate.append(f"[{role.upper()}]: {content}")
    messages_str = "\n\n".join(messages_intermediate)

    return await b.DirectChat(messages_str, entries_str, custom_instructions, personality_prompt, {"client_registry": cr})


async def agent_tool_selector(
    user_query: str,
    accumulated_context: str,
    search_trace: str,
    iteration: int,
    max_iterations: int
) -> SearchToolCall:
    """Select the next search tool to use in the agent loop."""
    return await b.AgentToolSelector(user_query, accumulated_context, search_trace, iteration, max_iterations)


async def agent_synthesizer(
    request: ChatRequest,
    chat_history: list,
    accumulated_context: str,
    search_trace: str,
    personality_prompt: str = ""
) -> str:
    """Generate final response using accumulated context. Uses user's selected model."""
    cr = ClientRegistry()
    cr.set_primary(f"{request.provider}/{request.model}")
    custom_instructions = load_custom_instructions()

    # format chat history with current query
    chat_history.append({
        "role": "user",
        "content": f"<QUERY>{request.query}</QUERY>"
    })

    messages_intermediate = []
    for msg in chat_history:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        messages_intermediate.append(f"[{role.upper()}]: {content}")
    messages_str = "\n\n".join(messages_intermediate)

    return await b.AgentSynthesizer(
        request.query,
        messages_str,
        accumulated_context,
        search_trace,
        custom_instructions,
        personality_prompt,
        {"client_registry": cr}
    )
