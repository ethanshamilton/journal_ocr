# completions.py
# code for dealing with LLM stuff in the app
from baml_py import ClientRegistry

from core.baml_client.async_client import b
from core.baml_client.types import SearchOptions
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
