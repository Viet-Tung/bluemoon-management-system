from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PageMeta


class ApartmentBase(BaseModel):
    """Thông tin cơ bản của căn hộ."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    code: str = Field(..., min_length=1, max_length=50, description="Mã căn hộ duy nhất (VD: P.1002)")
    floor: int = Field(..., ge=0, description="Số tầng (>= 0)")
    area_m2: float = Field(..., gt=0, description="Diện tích căn hộ tính theo m2 (> 0, AC-01.1)")
    note: Optional[str] = Field(default=None, description="Ghi chú về căn hộ")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Mã căn hộ không được để trống.")
        return v


class ApartmentCreate(ApartmentBase):
    """Schema tạo căn hộ mới (US-01, AC-01.1)."""
    pass


class ApartmentUpdate(BaseModel):
    """Schema cập nhật thông tin căn hộ (US-01)."""
    model_config = ConfigDict(extra="ignore")

    floor: Optional[int] = Field(default=None, ge=0, description="Số tầng (>= 0)")
    area_m2: Optional[float] = Field(default=None, gt=0, description="Diện tích căn hộ (> 0)")
    status: Optional[str] = Field(default=None, description="Trạng thái căn hộ (ACTIVE, INACTIVE)")
    note: Optional[str] = Field(default=None, description="Ghi chú")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip().upper()
            if v not in ("ACTIVE", "INACTIVE"):
                raise ValueError("Trạng thái chỉ có thể là ACTIVE hoặc INACTIVE.")
        return v


class Apartment(BaseModel):
    """Schema chi tiết căn hộ trả về client theo docs/openapi.yaml."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="ID căn hộ")
    code: str = Field(..., description="Mã căn hộ")
    floor: int = Field(..., description="Số tầng")
    area_m2: float = Field(..., description="Diện tích m2")
    status: str = Field(..., description="Trạng thái (ACTIVE, INACTIVE)")
    note: Optional[str] = Field(default=None, description="Ghi chú")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")


class ApartmentPage(PageMeta):
    """Danh sách căn hộ phân trang theo docs/openapi.yaml."""
    items: List[Apartment] = Field(default_factory=list, description="Danh sách căn hộ")

