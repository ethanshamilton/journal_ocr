import asyncio
import time
import tiktoken
from datetime import datetime
from typing import AsyncGenerator

from backend.baml_client.types import SearchOptions, AnalysisStep
from backend.completions import intent_classifier, get_embedding, chat_response 
from backend.lancedb_client import AsyncLocalLanceDB
from backend.models import ChatRequest, ChatResponse, Entry, RetrievedDoc

async def default_llm_flow(lance: AsyncLocalLanceDB, req: ChatRequest) -> ChatResponse:
    entries = []
    response_docs = []
    entries_str = ""

    if req.existing_docs:
        entries_str = "Here are the relevant journal entries from our previous conversation:\n"
        for i, doc in enumerate(req.existing_docs, 1):
            entries_str += f"Entry {i}:\n"
            entries_str += f"  title: {doc.get('title', 'Untitled')}\n"
            entries_str += f"  content: {doc.get('content', '')}\n"
            entries_str += "\n"
    else:
        # do normal retrieval
        query_intent = await intent_classifier(req.query)
        print("query intent:", query_intent)

        if query_intent == SearchOptions.VECTOR:
            query_embedding = await get_embedding(req.query)
            entries = await lance.get_similar_entries(query_embedding, req.top_k)
            for i, (entry, distance) in enumerate(entries, 1):
                entry_dict = entry.model_dump(exclude={"embedding"})
                entries_str += f"Entry {i} (Distance: {distance})\n"
                for k, v in entry_dict.items():
                    entries_str += f"   {k}: {v}\n"
                entries_str += "\n"
                entry_for_response = entry.model_copy(update={"embedding": None})
                response_docs.append(RetrievedDoc(entry=entry_for_response, distance=distance))

        elif query_intent == SearchOptions.RECENT:
            entries = await lance.get_recent_entries()
            for i, entry in enumerate(entries, 1):
                entry_dict = entry.model_dump(exclude={"embedding"})
                entries_str += f"Entry {i}:\n"
                for k, v in entry_dict.items():
                    entries_str += f"   {k}: {v}\n"
                entries_str += "\n"
                entry_for_response = entry.model_copy(update={"embedding": None})
                response_docs.append(RetrievedDoc(entry=entry_for_response, distance=None))

    chat_history = await _load_chat_history(lance, req)

    llm_response = await chat_response(req, chat_history, entries_str)

    return ChatResponse(response=llm_response, docs=response_docs, thread_id=req.thread_id)

async def _load_chat_history(lance: AsyncLocalLanceDB, request: ChatRequest) -> list[dict]:
    # get thread history from lancedb if present
    db_messages = []
    if request.thread_id:
        try:
            thread_messages = await lance.get_thread_messages(request.thread_id)
            if thread_messages:
                for msg in thread_messages:
                    role = msg.get("role", "user")
                    if role not in ["user", "assistant"]:
                        role = "user"
                    content = msg.get("content", "")
                    db_messages.append({"role": role, "content": content})
        except Exception as e:
            print(f"Error loading thread messages: {e}")

    # also include message history from request if provided (for temporary chats)
    temp_messages = []
    if request.message_history:
        for msg in request.message_history:
            role = msg.get("sender", "user")
            if role not in ["user", "assistant"]:
                role = "user"
            content = msg.get("text", "")
            temp_messages.append({"role": role, "content": content})

    return db_messages + temp_messages
