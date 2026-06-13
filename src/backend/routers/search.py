from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.deps import get_graph
from backend.schemas import ResumeRequest, SearchRequest, SearchResponse
from backend.services import agent

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, graph=Depends(get_graph)):
    return await agent.run_message(graph, req.thread_id, req.message, req.rater_model)


@router.post("/search/resume", response_model=SearchResponse)
async def resume(req: ResumeRequest, graph=Depends(get_graph)):
    return await agent.resume(graph, req.thread_id, req.filters)
