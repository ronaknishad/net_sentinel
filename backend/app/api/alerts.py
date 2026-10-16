from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_db
from backend.app.schemas.requests import AlertUpdate
from backend.app.services import alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
                status: str | None = None, severity: str | None = None,
                analysis_id: int | None = None, db=Depends(get_db)):
    return alerts.list_alerts(db, page, page_size, status, severity, analysis_id)


@router.get("/{alert_id}")
def get_alert(alert_id: int, db=Depends(get_db)):
    return alerts.get_alert(db, alert_id)


@router.patch("/{alert_id}")
def update_alert(alert_id: int, body: AlertUpdate, db=Depends(get_db)):
    """Update the investigation status. Stored in SQLite and kept across restarts."""
    return alerts.update_status(db, alert_id, body.status)
