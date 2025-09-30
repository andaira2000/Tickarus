from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseDBModel(BaseModel):
    id: UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        ser_json_timedelta="iso8601",
    )
