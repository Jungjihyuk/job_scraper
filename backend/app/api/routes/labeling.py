"""
CSV 기반 라벨 Import/Export API 엔드포인트.
"""

import io
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.logging import create_development_logger
from app.services.labeling import export_postings, import_labeled

logger = create_development_logger(__name__)

router = APIRouter(prefix="/api/labeling", tags=["Labeling"])


@router.get("/export")
def export_csv(
    field: Literal["domain", "technology"] | None = Query(None),
    limit: int = Query(500, ge=1, le=10000),
    include_all: bool = Query(False),
    db: Session = Depends(get_db_session),
):
    """공고를 CSV 파일로 다운로드."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8"
    ) as tmp:
        tmp_path = tmp.name

    count = export_postings(
        session=db,
        output_path=tmp_path,
        field=field,
        limit=limit,
        include_all=include_all,
    )

    content = Path(tmp_path).read_bytes()
    Path(tmp_path).unlink(missing_ok=True)

    filename = "all_postings.csv" if include_all else "unlabeled.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Count": str(count),
        },
    )


@router.post("/import")
async def import_csv(
    file: UploadFile = File(...),
    dry_run: bool = Query(False),
    skip_existing: bool = Query(False),
    db: Session = Depends(get_db_session),
):
    """라벨링된 CSV를 업로드하여 DB에 반영."""
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".csv", delete=False
    ) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = import_labeled(
            session=db,
            csv_path=tmp_path,
            dry_run=dry_run,
            skip_existing=skip_existing,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return result
