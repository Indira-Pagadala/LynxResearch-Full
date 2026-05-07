import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _run_log_path(run_id: str) -> Path:
    base_dir = settings.LOG_DIR / "runs"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{run_id}.jsonl"


def log_run_event(run_id: str, stage: str, event: str, **data: Any) -> None:
    """
    Append-only structured run event logger.
    One JSON object per line for stable ingestion and debugging.
    """
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "stage": stage,
        "event": event,
        "data": data,
    }
    try:
        path = _run_log_path(run_id)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
    except Exception as exc:
        logger.warning(f"Failed to append run log for {run_id}: {exc}")
