from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import PageMeta


def _validate_cccd(v: Optional[str]) -> Optional[str]:
    if v is not None and v.strip() != "":
        v = v.strip()
        # Validate định dạng CCCD/CMND 9 hoặc 12 số
        if not v.isdigit() or len(v) not in (9, 12):
            raise ValueError("CCCD/CMND phải gồm 9 hoặc 12 chữ số hợp lệ.")
        return v
    return None


class ResidentBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    gender: str = Field(..., pattern="^(NAM|NU|KHAC)$")
    cccd: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    relationship_to_head: Optional[str] = Field(None, max_length=100)
    is_head: bool = False


class ResidentCreate(ResidentBase):
    @field_validator("cccd")
    @classmethod
    def validate_cccd(cls, v: Optional[str]) -> Optional[str]:
        return _validate_cccd(v)


class ResidentUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, pattern="^(NAM|NU|KHAC)$")
    cccd: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    relationship_to_head: Optional[str] = Field(None, max_length=100)

    @field_validator("cccd")
    @classmethod
    def validate_cccd(cls, v: Optional[str]) -> Optional[str]:
        return _validate_cccd(v)


class ResidentResponse(ResidentBase):
    id: int
    household_id: int
    residence_status: str
    status_effective_date: Optional[date] = None
    status_reason: Optional[str] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResidentPage(PageMeta):
    items: List[ResidentResponse] = Field(default_factory=list, description="Danh sách nhân khẩu")