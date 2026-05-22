from __future__ import annotations
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import require_admin, CurrentUser
from app.models.schemas import IngestResponse
from app.ingestion.pdf_loader import PDFLoader
from app.ingestion.confluence import ConfluenceLoader

router = APIRouter()
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


@router.post("/ingest/pdf", response_model=IngestResponse)
async def ingest_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Form(default="general"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_admin),
) -> IngestResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    safe_name = f"{uuid.uuid4()}_{Path(file.filename).name}"
    dest = UPLOADS_DIR / safe_name

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Run ingestion in background so the request returns immediately
    background_tasks.add_task(_run_pdf_ingestion, str(dest), collection)

    return IngestResponse(
        job_id=safe_name,
        status="pending",
        message=f"Ingestion de '{file.filename}' démarrée en arrière-plan",
    )


async def _run_pdf_ingestion(file_path: str, collection: str) -> None:
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        loader = PDFLoader(file_path)
        await loader.ingest(db, collection)


@router.post("/ingest/confluence", response_model=IngestResponse)
async def ingest_confluence(
    space_key: str,
    collection: str = "general",
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(require_admin),
) -> IngestResponse:
    loader = ConfluenceLoader(space_key)
    chunks_count = await loader.ingest(db, collection)
    return IngestResponse(
        job_id=f"confluence-{space_key}",
        status="done",
        chunks_count=chunks_count,
        message=f"Espace Confluence '{space_key}' ingéré : {chunks_count} chunks",
    )
