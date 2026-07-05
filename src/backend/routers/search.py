from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.deps import get_graph
from backend.schemas import ResumeRequest, SearchRequest, SearchResponse
from backend.services import agent, sessions

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, graph=Depends(get_graph)):
    sessions.record_session(req.thread_id, req.message)
    return await agent.run_message(graph, req.thread_id, req.message, req.rater_model)


@router.post("/search/resume", response_model=SearchResponse)
async def resume(req: ResumeRequest, graph=Depends(get_graph)):
    return await agent.resume(graph, req.thread_id, req.filters)


def _sse(events: AsyncIterator[dict]) -> StreamingResponse:
    # starlette cancels the generator when the client disconnects, which cancels
    # the underlying graph run; failures become a terminal error frame
    async def gen() -> AsyncIterator[str]:
        try:
            async for evt in events:
                yield f"data: {json.dumps(evt)}\n\n"
        except Exception as e:  # noqa: BLE001 — surfaced to the client, stream must end cleanly
            yield f"data: {json.dumps({'event': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/search/stream")
async def search_stream(req: SearchRequest, graph=Depends(get_graph)):
    sessions.record_session(req.thread_id, req.message)
    return _sse(agent.stream_message(graph, req.thread_id, req.message, req.rater_model))


@router.post("/search/resume/stream")
async def resume_stream(req: ResumeRequest, graph=Depends(get_graph)):
    return _sse(agent.stream_resume(graph, req.thread_id, req.filters))
