# completions.py
# code for dealing with LLM stuff in the app
from baml_py import ClientRegistry

from core.baml_client.async_client import b
from core.baml_client.types import SearchOptions, SearchToolCall
from core.models import ChatRequest
from core.llm import get_embedding


async def intent_classifier(query: str) -> SearchOptions:
    return await b.IntentClassifier(query)


async def chat_response(request: ChatRequest, chat_history: list, entries_str: str) -> str:
    cr = ClientRegistry()
    cr.set_primary(f"{request.provider}/{request.model}")

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

    return await b.DirectChat(messages_str, entries_str, {"client_registry": cr})


async def agent_tool_selector(
    user_query: str,
    accumulated_context: str,
    iteration: int,
    max_iterations: int
) -> SearchToolCall:
    """Select the next search tool to use in the agent loop."""
    return await b.AgentToolSelector(user_query, accumulated_context, iteration, max_iterations)


async def agent_synthesizer(
    request: ChatRequest,
    chat_history: list,
    accumulated_context: str,
    search_trace: str
) -> str:
    """Generate final response using accumulated context. Uses user's selected model."""
    cr = ClientRegistry()
    cr.set_primary(f"{request.provider}/{request.model}")

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
        {"client_registry": cr}
    )
