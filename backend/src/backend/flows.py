import asyncio
import time
import tiktoken
from datetime import datetime
from typing import AsyncGenerator

from core.baml_client.types import SearchOptions, SearchToolType
from core.lancedb_client import AsyncLocalLanceDB
from core.log_config import setup_logging
from core.models import ChatRequest, ChatResponse, Entry, RetrievedDoc, AgentSearchState
from core.llm import get_embedding
from backend.completions import intent_classifier, chat_response, agent_tool_selector, agent_synthesizer

logger = setup_logging()


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
        logger.info(f"Query intent: {query_intent}")

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
            logger.error(f"Error loading thread messages: {e}")

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


MAX_AGENT_ITERATIONS = 5


RECENT_PRESEED_COUNT = 4


async def agentic_llm_flow(lance: AsyncLocalLanceDB, req: ChatRequest) -> ChatResponse:
    """
    Agentic search loop that iteratively selects and executes search tools
    to gather comprehensive context before generating a response.
    """
    state = AgentSearchState()

    # always pre-seed with recent entries for temporal context
    recent_entries = await lance.get_recent_entries(RECENT_PRESEED_COUNT)
    new_count = state.add_entries(recent_entries)
    state.record_iteration(
        iteration=0,
        tool="RECENT_ENTRIES_PRESEED",
        reasoning="Always include recent entries for temporal context",
        query=None,
        results_count=len(recent_entries),
        new_entries=new_count
    )
    logger.info(f"Pre-seeded with {new_count} recent entries")

    # agent loop - iteratively select and execute tools
    for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
        try:
            tool_call = await agent_tool_selector(
                user_query=req.query,
                accumulated_context=state.get_context_string(),
                search_trace=state.get_trace_string(),
                iteration=iteration,
                max_iterations=MAX_AGENT_ITERATIONS
            )
            logger.info(f"Agent iteration {iteration}: {tool_call.tool} - {tool_call.reasoning[:80]}...")

            if tool_call.tool == SearchToolType.DONE:
                state.record_iteration(
                    iteration=iteration,
                    tool="DONE",
                    reasoning=tool_call.reasoning,
                    query=None,
                    results_count=0,
                    new_entries=0
                )
                break

            # execute the selected tool
            entries = await _execute_agent_tool(lance, tool_call)
            new_count = state.add_entries(entries)

            state.record_iteration(
                iteration=iteration,
                tool=tool_call.tool.value,
                reasoning=tool_call.reasoning,
                query=tool_call.query,
                results_count=len(entries),
                new_entries=new_count
            )

            logger.info(f"Agent retrieved {len(entries)} entries, {new_count} new")

        except Exception as e:
            logger.error(f"Error in agent iteration {iteration}: {e}")
            # fallback: do a simple vector search and break
            if not state.accumulated_entries:
                query_embedding = await get_embedding(req.query)
                if query_embedding:
                    fallback_entries = await lance.get_similar_entries(query_embedding, req.top_k)
                    for entry, _ in fallback_entries:
                        state.add_entry(entry)
            break

    # load chat history
    chat_history = await _load_chat_history(lance, req)

    # synthesize final response
    llm_response = await agent_synthesizer(
        request=req,
        chat_history=chat_history,
        accumulated_context=state.get_context_string(),
        search_trace=state.get_trace_string()
    )

    # build response docs for frontend
    response_docs = []
    for entry in state.accumulated_entries.values():
        entry_for_response = entry.model_copy(update={"embedding": None})
        response_docs.append(RetrievedDoc(entry=entry_for_response, distance=None))

    return ChatResponse(response=llm_response, docs=response_docs, thread_id=req.thread_id)


async def agentic_llm_flow_stream(lance: AsyncLocalLanceDB, req: ChatRequest) -> AsyncGenerator[dict, None]:
    """
    Streaming version of agentic_llm_flow that yields SSE events
    for each search iteration and the final response.
    """
    state = AgentSearchState()

    # always pre-seed with recent entries for temporal context
    recent_entries = await lance.get_recent_entries(RECENT_PRESEED_COUNT)
    new_count = state.add_entries(recent_entries)
    state.record_iteration(
        iteration=0,
        tool="RECENT_ENTRIES_PRESEED",
        reasoning="Always include recent entries for temporal context",
        query=None,
        results_count=len(recent_entries),
        new_entries=new_count
    )
    logger.info(f"Pre-seeded with {new_count} recent entries")

    yield {
        "event": "search_iteration",
        "data": {
            "iteration": 0,
            "tool": "RECENT_ENTRIES_PRESEED",
            "reasoning": "Always include recent entries for temporal context",
            "query": None,
            "results_count": len(recent_entries),
            "new_entries_added": new_count,
        }
    }

    # agent loop - iteratively select and execute tools
    for iteration in range(1, MAX_AGENT_ITERATIONS + 1):
        try:
            tool_call = await agent_tool_selector(
                user_query=req.query,
                accumulated_context=state.get_context_string(),
                search_trace=state.get_trace_string(),
                iteration=iteration,
                max_iterations=MAX_AGENT_ITERATIONS
            )
            logger.info(f"Agent iteration {iteration}: {tool_call.tool} - {tool_call.reasoning[:80]}...")

            if tool_call.tool == SearchToolType.DONE:
                state.record_iteration(
                    iteration=iteration,
                    tool="DONE",
                    reasoning=tool_call.reasoning,
                    query=None,
                    results_count=0,
                    new_entries=0
                )
                yield {
                    "event": "search_iteration",
                    "data": {
                        "iteration": iteration,
                        "tool": "DONE",
                        "reasoning": tool_call.reasoning,
                        "query": None,
                        "results_count": 0,
                        "new_entries_added": 0,
                    }
                }
                break

            # execute the selected tool
            entries = await _execute_agent_tool(lance, tool_call)
            new_count = state.add_entries(entries)

            state.record_iteration(
                iteration=iteration,
                tool=tool_call.tool.value,
                reasoning=tool_call.reasoning,
                query=tool_call.query,
                results_count=len(entries),
                new_entries=new_count
            )

            yield {
                "event": "search_iteration",
                "data": {
                    "iteration": iteration,
                    "tool": tool_call.tool.value,
                    "reasoning": tool_call.reasoning,
                    "query": tool_call.query,
                    "results_count": len(entries),
                    "new_entries_added": new_count,
                }
            }

            logger.info(f"Agent retrieved {len(entries)} entries, {new_count} new")

        except Exception as e:
            logger.error(f"Error in agent iteration {iteration}: {e}")
            if not state.accumulated_entries:
                query_embedding = await get_embedding(req.query)
                if query_embedding:
                    fallback_entries = await lance.get_similar_entries(query_embedding, req.top_k)
                    for entry, _ in fallback_entries:
                        state.add_entry(entry)
            break

    # load chat history
    chat_history = await _load_chat_history(lance, req)

    # synthesize final response
    llm_response = await agent_synthesizer(
        request=req,
        chat_history=chat_history,
        accumulated_context=state.get_context_string(),
        search_trace=state.get_trace_string()
    )

    # build response docs for frontend
    response_docs = []
    for entry in state.accumulated_entries.values():
        entry_for_response = entry.model_copy(update={"embedding": None})
        response_docs.append(RetrievedDoc(entry=entry_for_response, distance=None))

    yield {
        "event": "chat_response",
        "data": ChatResponse(response=llm_response, docs=response_docs, thread_id=req.thread_id).model_dump()
    }


async def _execute_agent_tool(lance: AsyncLocalLanceDB, tool_call) -> list[Entry]:
    """Execute the selected search tool and return entries."""
    limit = tool_call.limit or 5

    match tool_call.tool:
        case SearchToolType.VECTOR_SEARCH:
            query = tool_call.query or ""
            query_embedding = await get_embedding(query)
            if not query_embedding:
                return []
            results = await lance.get_similar_entries(query_embedding, limit)
            return [entry for entry, _ in results]

        case SearchToolType.RECENT_ENTRIES:
            return await lance.get_recent_entries(limit)

        case SearchToolType.DATE_RANGE_SEARCH:
            start = tool_call.start_date
            end = tool_call.end_date
            if not start or not end:
                return []
            return await lance.get_entries_by_date_range(start, end, limit)

        case _:
            return []
