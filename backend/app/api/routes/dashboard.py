from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ticket import TicketModel
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import build_dashboard_summary


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db)):
    tickets = db.query(TicketModel).all()

    return build_dashboard_summary(tickets)