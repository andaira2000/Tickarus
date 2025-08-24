from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class BaseDBModel(BaseModel):
    id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    # Pydantic v2-style config with proper typing
    model_config = ConfigDict(
        from_attributes=True,
        ser_json_timedelta="iso8601",  # or "float" if you prefer seconds as a number
    )
