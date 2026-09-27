from typing import Literal

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=10)
    customer: str = Field(min_length=2, max_length=120)
    customerEmail: EmailStr
    category: str = Field(default="General", max_length=80)


class TicketBulkCreate(BaseModel):
    """Create multiple tickets in a single request.
    
    Only should be used during testing..."""

    analyze: bool = False  #!!! defaults to 'False' so that a random request doesn't trigger OpenAI calls. In the generated JSON, it is explicit.
    tickets: list[TicketCreate] = Field(
        min_length=1,
        max_length=100,
    )
    

class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject: str
    body: str
    customer: str
    customerEmail: str
    category: str
    priority: Literal["Low", "Medium", "High", "Very High"]
    sentiment: Literal["Negative", "Neutral", "Positive"]
    sla: str
    slaState: Literal["critical", "warning", "safe"]
    status: Literal["Open", "In Progress", "Resolved"]
    updatedAt: str
    owner: str


class TicketBulkCreateResult(BaseModel):
    """Result of a bulk ticket creation request."""

    createdCount: int
    analysisScheduled: bool
    tickets: list[TicketRead]