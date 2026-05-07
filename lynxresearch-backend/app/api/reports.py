# app/api/reports.py

import uuid
import logging
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.report import Report
from app.schemas.report import ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/{run_id}", response_model=ReportResponse)
async def get_report_metadata(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get report metadata for a completed run."""
    result = await db.execute(
        select(Report).where(Report.run_id == run_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{run_id}/download")
async def download_report(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Download the PDF report.
    Browser receives it as an attachment → auto-downloads to user's PC.
    """
    result = await db.execute(
        select(Report).where(Report.run_id == run_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not yet generated")

    pdf_path = Path(report.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on server")

    filename = f"LynxResearch_{str(run_id)[:8]}.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{run_id}/markdown")
async def get_report_markdown(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return raw markdown content for frontend preview."""
    result = await db.execute(
        select(Report).where(Report.run_id == run_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    markdown = _truncate_after_references(report.markdown_content or "")
    markdown = _rewrite_chart_paths(markdown, str(run_id))
    return {"run_id": str(run_id), "markdown": markdown}


def _rewrite_chart_paths(markdown: str, run_id: str) -> str:
    """
    Convert local chart file paths in markdown image tags to backend URLs so
    charts render in the report viewer without regenerating assets.
    """
    def repl(match: re.Match) -> str:
        alt = match.group(1)
        raw_path = match.group(2).strip()
        filename = Path(raw_path).name
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
            return match.group(0)
        return f"![{alt}](http://localhost:8000/runs/{run_id}/charts/{filename})"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, markdown)


def _truncate_after_references(content: str) -> str:
    lines = content.splitlines()
    ref_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^\s*#{1,3}\s*References\s*$", line, flags=re.IGNORECASE):
            ref_idx = i
            break
    if ref_idx == -1:
        return content
    end_idx = len(lines)
    for i in range(ref_idx + 1, len(lines)):
        if re.match(r"^\s*#{1,3}\s+", lines[i]):
            end_idx = i
            break
    return "\n".join(lines[:end_idx]).strip()