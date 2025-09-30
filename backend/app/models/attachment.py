from typing import Optional
from pydantic import BaseModel
from uuid import UUID


class Attachment(BaseModel):
    id: Optional[UUID] = None
    ticket_id: UUID
    file_name: str
    url: str
