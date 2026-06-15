from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class TicketPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketSentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


ALLOWED_TICKET_CATEGORIES = [
    "Billing",
    "Technical",
    "Account",
    "Feature Request",
    "Complaint",
    "General",
]


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    customer_email: EmailStr
    category: str | None = None
    priority: TicketPriority | None = None
    sentiment: TicketSentiment | None = None
    assigned_queue: str | None = None
    assigned_agent_id: str | None = None


class TicketUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1)
    customer_email: EmailStr | None = None
    status: TicketStatus | None = None
    category: str | None = None
    priority: TicketPriority | None = None
    sentiment: TicketSentiment | None = None
    assigned_queue: str | None = None
    assigned_agent_id: str | None = None


class TicketOverrideRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    priority: TicketPriority
    override_reason: str | None = Field(None, max_length=500)


class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    customer_email: EmailStr
    status: TicketStatus
    category: str | None
    priority: TicketPriority
    sentiment: TicketSentiment
    assigned_queue: str | None
    assigned_agent_id: str | None
    created_by: str
    created_at: datetime
    updated_at: datetime
    ai_category: str | None = None
    ai_priority: TicketPriority | None = None
    ai_sentiment: TicketSentiment | None = None
    ai_confidence: float | None = None
    ai_explanation: str | None = None
    category_override: str | None = None
    priority_override: TicketPriority | None = None
    override_reason: str | None = None
    overridden_by: str | None = None
    overridden_by_name: str | None = None
    overridden_by_email: str | None = None
    overridden_at: datetime | None = None
    has_manual_override: bool = False
