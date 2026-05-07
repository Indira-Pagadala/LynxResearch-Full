# app/utils/progress_emitter.py

import asyncio
import json
import logging
from typing import AsyncGenerator
from datetime import datetime
from app.utils.run_logger import log_run_event

logger = logging.getLogger(__name__)

# Global dict: run_id → asyncio.Queue
# The API SSE endpoint subscribes to these queues
_progress_queues: dict[str, asyncio.Queue] = {}
_progress_seq: dict[str, int] = {}


def get_or_create_queue(run_id: str) -> asyncio.Queue:
    if run_id not in _progress_queues:
        _progress_queues[run_id] = asyncio.Queue(maxsize=100)
    return _progress_queues[run_id]


def remove_queue(run_id: str):
    _progress_queues.pop(run_id, None)


async def emit_progress(run_id: str, stage: str, progress: int, message: str = ""):
    """
    Push a progress event into the run's queue.
    The SSE endpoint will pick this up and stream it to the frontend.
    """
    queue = get_or_create_queue(run_id)
    seq = _progress_seq.get(run_id, 0) + 1
    _progress_seq[run_id] = seq
    event = {
        "run_id": run_id,
        "stage": stage,
        "progress": progress,
        "message": message,
        "seq": seq,
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        queue.put_nowait(event)
        logger.info(f"[{run_id}] {stage} — {progress}% — {message}")
        log_run_event(run_id, stage, "progress", progress=progress, message=message, seq=seq)
    except asyncio.QueueFull:
        logger.warning(f"Progress queue full for run {run_id}, dropping event")
        log_run_event(run_id, stage, "progress_drop", progress=progress, message=message, seq=seq)


async def progress_event_generator(run_id: str) -> AsyncGenerator[str, None]:
    """
    SSE generator. FastAPI streams this to the frontend.
    Usage in route: return EventSourceResponse(progress_event_generator(run_id))
    """
    queue = get_or_create_queue(run_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"

                # Stop streaming when done or failed
                if event.get("stage") in ("done", "failed"):
                    break
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    finally:
        remove_queue(run_id)
        _progress_seq.pop(run_id, None)