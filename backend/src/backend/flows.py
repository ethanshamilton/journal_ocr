import asyncio
import time
import tiktoken
from datetime import datetime
from typing import AsyncGenerator

from backend.baml_client.types import SearchOptions, AnalysisStep
from backend.completions import intent_classifier, get_embedding, chat_response, comprehensive_analysis
from backend.lancedb_client import AsyncLocalLanceDB
from backend.models import ChatRequest, ChatResponse, Entry, RetrievedDoc

async def comprehensive_analysis_flow(lance: AsyncLocalLanceDB, req: ChatRequest) -> dict:
    print("running comprehensive analysis")

    encoder = tiktoken.get_encoding("cl100k_base")
    tokens_this_minute = 0
    minute_start = time.time()
    TPM_LIMIT = 30_000

    # prepare chat history
    chat_history = await _load_chat_history(lance, req)

    # iterate through years from 2018 to present
    current_year = datetime.now().year
    years = list(range(2018, current_year + 1))

    analyses = []
    for year in years:
        print(f"\nprocessing year: {year}")
        entries = await lance.get_entries_by_date_range(f"{year}-01-01", f"{year}-12-31")
        chunks = _chunk_entries_by_tokens(entries, encoder, (TPM_LIMIT-2000))

        subyear_analyses = []
        for chunk in chunks:
            if chunk == "":
                continue

            print(type(chunk))
            print(chunk[0])
            token_count = int(len(encoder.encode(chunk)) * 1.05)
            print(f"token count for {year}: {token_count}")

            # check rate limiting
            elapsed = time.time() - minute_start
            if elapsed >= 60:
                tokens_this_minute = 0
                minute_start = time.time()

            if tokens_this_minute + token_count > TPM_LIMIT:
                wait_time = 60 - elapsed
                print(f"approaching TPM limit, waiting: {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                tokens_this_minute = 0
                minute_start = time.time()

            if len(chunks) == 1:
                analysis = await comprehensive_analysis(req, [], chunk, AnalysisStep.YEAR)
                analyses.append(analysis)
                print(f"\nreasoning: {analysis.reasoning}\n\nanalysis: {analysis.analysis}\n\nexcerpts: {analysis.excerpts}\n")
            elif len(chunks) != 1:
                analysis = await comprehensive_analysis(req, [], chunk, AnalysisStep.YEAR)
                subyear_analyses.append(analysis)
                print(f"\nreasoning: {analysis.reasoning}\n\nanalysis: {analysis.analysis}\n\nexcerpts: {analysis.excerpts}\n")

        if len(subyear_analyses) != 0:
            subyear_analyses_str = ""
            for analysis in subyear_analyses:
                subyear_analyses_str += f"""
                <ANALYSIS>{analysis.analysis}</ANALYSIS>
                <EXCERPTS>{analysis.excerpts}</EXCERPTS>
                """
            analysis = await comprehensive_analysis(req, [], subyear_analyses_str, AnalysisStep.YEAR)
            analyses.append(analysis)
            print(f"\nreasoning: {analysis.reasoning}\n\nanalysis: {analysis.analysis}\n\nexcerpts: {analysis.excerpts}\n")

    analyses_str = ""
    for analysis in analyses:
        analyses_str += f"""
        <ANALYSIS>{analysis.analysis}</ANALYSIS>
        <EXCERPTS>{analysis.excerpts}</EXCERPTS>
        """
    final_analysis = await comprehensive_analysis(req, chat_history, analyses_str, AnalysisStep.FINAL)
    print(f"\nFINAL ANALYSIS\n\nreasoning: {final_analysis.reasoning}\n\nanalysis: {final_analysis.analysis}\n\nexcerpts: {final_analysis.excerpts}\n")

    # prepare result for caching
    result = {
        "query": req.query,
        "provider": req.provider,
        "model": req.model,
        "timestamp": datetime.now().isoformat(),
        "year_analyses": [
            {
                "year": year,
                "reasoning": analysis.reasoning,
                "analysis": analysis.analysis,
                "excerpts": analysis.excerpts
            }
            for year, analysis in zip(years, analyses)
        ],
        "final_analysis": {
            "reasoning": final_analysis.reasoning,
            "analysis": final_analysis.analysis,
            "excerpts": final_analysis.excerpts
        }
    }

    return result

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

def _chunk_entries_by_tokens(entries: list[Entry], encoder: tiktoken.Encoding, max_tokens_per_chunk: int = 28_000) -> list[str]:
    chunks = []
    current_chunk = []
    current_tokens = 0

    for entry in entries:
        entry_dict = entry.model_dump(exclude={"embedding"})
        entry_str = f"Entry {len(current_chunk) + 1}\n"
        for k, v in entry_dict.items():
            entry_str += f"    {k}: {v}\n"
        entry_str += "\n"

        entry_tokens = len(encoder.encode(entry_str))

        if current_tokens + entry_tokens > max_tokens_per_chunk and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_tokens = 0

        current_chunk.append(entry_str)
        current_tokens += entry_tokens

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

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
