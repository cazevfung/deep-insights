"""
Export routes for downloadable assets.
"""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from loguru import logger

# Ensure project root on sys.path for ResearchSession imports inside service.
import sys

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.services.pdf_export_service import (
    PdfExportError,
    SessionNotFoundError,
    generate_phase_report_pdf,
)

router = APIRouter()


@router.get("/phase-report/{session_id}")
async def export_phase_report(session_id: str) -> Response:
    """
    Generate and stream the phase report PDF for a given session.
    """
    try:
        pdf_bytes = generate_phase_report_pdf(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PdfExportError as exc:
        logger.error("PDF export failed for session %s: %s", session_id, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error generating PDF for session %s", session_id)
        raise HTTPException(status_code=500, detail="Failed to generate PDF") from exc

    filename = f"research-report-{session_id}.pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "no-cache",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)




