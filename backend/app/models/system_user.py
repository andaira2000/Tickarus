from typing import Optional
from pydantic import BaseModel
from enum import Enum
from app.models import BaseDBModel


class SystemUserType(str, Enum):
    CI_AUTOMATION = "ci_automation"
    AI_ASSISTANT = "ai_assistant"
    DATA_PROCESSOR = "data_processor"
    NOTIFICATION_SERVICE = "notification_service"


class SystemUserBase(BaseModel):
    name: str
    type: SystemUserType
    description: Optional[str] = None
    is_active: bool = True


class SystemUserCreate(SystemUserBase):
    pass


class SystemUserUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[SystemUserType] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SystemUser(SystemUserBase, BaseDBModel):
    pass
