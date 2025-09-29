from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from app.models import BaseDBModel


class AIMetricsCreate(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=50)
    ticket_id: Optional[str] = None
    user_id: Optional[str] = None
    ai_feature: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    user_rating: Optional[int] = Field(None, ge=1, le=5)
    response_time_ms: Optional[int] = Field(None, ge=0)


class AIMetrics(AIMetricsCreate, BaseDBModel):
    created_at: Optional[datetime] = None
