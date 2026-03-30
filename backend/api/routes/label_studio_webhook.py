"""
Label Studio Webhook Handler.
annotation 완료 이벤트를 수신하여 domain_review_staging 테이블에 기록.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.database import get_db_session
from backend.core.logging import create_development_logger

logger = create_development_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _extract_domain_from_annotation(annotation: dict) -> Optional[dict]:
    """
    Label Studio annotation result에서 domain 값과 review_note를 추출.

    annotation.result 형태:
    [
      {"from_name": "domain", "type": "choices", "value": {"choices": ["금융"]}},
      {"from_name": "review_note", "type": "textarea", "value": {"text": ["메모"]}}
    ]
    """
    domain = None
    note = None

    for item in annotation.get("result", []):
        if item.get("from_name") == "domain" and item.get("type") == "choices":
            choices = item.get("value", {}).get("choices", [])
            if choices:
                domain = choices[0]
        elif item.get("from_name") == "review_note" and item.get("type") == "textarea":
            texts = item.get("value", {}).get("text", [])
            if texts:
                note = texts[0]

    return {"domain": domain, "note": note} if domain else None


@router.post("/label-studio")
async def handle_label_studio_webhook(
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Label Studio webhook endpoint.
    ANNOTATION_CREATED / ANNOTATION_UPDATED 이벤트를 처리.
    """
    payload = await request.json()

    action = payload.get("action")
    if action not in ("ANNOTATION_CREATED", "ANNOTATION_UPDATED"):
        return {"status": "ignored", "action": action}

    annotation = payload.get("annotation", {})
    task = payload.get("task", {})
    task_data = task.get("data", {})

    posting_id = task_data.get("posting_id")
    if not posting_id:
        raise HTTPException(status_code=400, detail="Missing posting_id in task data")

    annotation_id = annotation.get("id")
    result = _extract_domain_from_annotation(annotation)

    if not result or not result["domain"]:
        raise HTTPException(status_code=400, detail="No domain found in annotation")

    ai_domain = task_data.get("ai_domain")

    try:
        # UPSERT: posting_id + annotation_id 기준
        upsert_sql = text("""
            INSERT INTO domain_review_staging
                (posting_id, reviewed_domain, ai_predicted_domain, reviewer_note,
                 annotation_id, reviewed_at, status)
            VALUES
                (:posting_id, :reviewed_domain, :ai_predicted_domain, :reviewer_note,
                 :annotation_id, :reviewed_at, 'pending')
            ON CONFLICT (posting_id, annotation_id) DO UPDATE SET
                reviewed_domain = EXCLUDED.reviewed_domain,
                reviewer_note = EXCLUDED.reviewer_note,
                reviewed_at = EXCLUDED.reviewed_at,
                status = 'pending'
        """)

        db.execute(
            upsert_sql,
            {
                "posting_id": str(posting_id),
                "reviewed_domain": result["domain"],
                "ai_predicted_domain": ai_domain,
                "reviewer_note": result.get("note"),
                "annotation_id": annotation_id,
                "reviewed_at": datetime.utcnow(),
            },
        )
        db.commit()

        logger.info(
            f"Webhook processed: posting_id={posting_id}, "
            f"domain={result['domain']}, action={action}"
        )

        return {
            "status": "ok",
            "posting_id": posting_id,
            "domain": result["domain"],
            "action": action,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Webhook handler error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
