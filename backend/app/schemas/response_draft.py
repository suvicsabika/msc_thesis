from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResponseDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticketId: str
    draft: str
    requiresApproval: bool
    reason: str
    createdAt: datetime
    updatedAt: datetime