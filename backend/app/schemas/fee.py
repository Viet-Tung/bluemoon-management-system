from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import PageMeta


class FeeGroup(str, Enum):
    MANAGEMENT = "MANAGEMENT"
    PARKING = "PARKING"
    UTILITY = "UTILITY"
    OTHER = "OTHER"


class CalcMethod(str, Enum):
    PER_M2 = "PER_M2"
    PER_HOUSEHOLD = "PER_HOUSEHOLD"
    PER_PERSON = "PER_PERSON"
    PER_VEHICLE = "PER_VEHICLE"
    METERED = "METERED"


class VehicleType(str, Enum):
    MOTORBIKE = "MOTORBIKE"
    CAR = "CAR"
    BICYCLE = "BICYCLE"


class FeeCycle(str, Enum):
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class FeeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class FeeTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    code: str = Field(..., min_length=1, max_length=50, description="Mã định danh khoản thu (VD: PQL, P_XE_MAY)")
    name: str = Field(..., min_length=1, max_length=255, description="Tên khoản thu")
    fee_group: FeeGroup = Field(..., description="Nhóm phí")
    calc_method: CalcMethod = Field(..., description="Phương pháp tính")
    unit_label: str = Field(..., min_length=1, max_length=50, description="Đơn vị tính (m2, hộ, người, xe, kWh, m3)")
    vehicle_type: Optional[VehicleType] = Field(default=None, description="Bắt buộc khi calc_method = PER_VEHICLE")
    is_pass_through: bool = Field(default=False, description="Thu hộ: không gộp vào công nợ phí quản lý")
    provider_id: Optional[int] = Field(default=None, description="Nhà cung cấp dùng cho khoản thu hộ")
    cycle: FeeCycle = Field(default=FeeCycle.MONTHLY, description="Kỳ tính phí")
    due_day: Optional[int] = Field(default=None, ge=1, le=31, description="Hạn nộp phí hàng tháng (1-31)")
    description: Optional[str] = Field(default=None, description="Mô tả chi tiết")


class FeeTypeCreate(FeeTypeBase):
    """Schema tạo khoản thu mới (US-12)."""

    @field_validator("code", "name", "unit_label")
    @classmethod
    def check_non_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Trường không được để trống hoặc chỉ chứa khoảng trắng.")
        return s

    @model_validator(mode="after")
    def validate_vehicle_type(self) -> "FeeTypeCreate":
        if self.calc_method == CalcMethod.PER_VEHICLE and not self.vehicle_type:
            raise ValueError("vehicle_type bắt buộc khi calc_method là PER_VEHICLE")
        return self


class FeeTypeUpdate(BaseModel):
    """Schema cập nhật khoản thu (US-12). Tuân thủ 100% docs/openapi.yaml."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    name: Optional[str] = Field(default=None, max_length=255)
    unit_label: Optional[str] = Field(default=None, max_length=50)
    provider_id: Optional[int] = Field(default=None)
    cycle: Optional[FeeCycle] = Field(default=None)
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    description: Optional[str] = Field(default=None)

    @field_validator("name", "unit_label")
    @classmethod
    def check_non_empty_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Trường không được chỉ chứa khoảng trắng.")
            return s
        return v


class FeeType(BaseModel):
    """Schema chi tiết khoản thu trả về cho client."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    code: str
    name: str
    fee_group: FeeGroup
    calc_method: CalcMethod
    unit_label: str
    vehicle_type: Optional[VehicleType] = None
    is_pass_through: bool = False
    provider_id: Optional[int] = None
    cycle: FeeCycle = FeeCycle.MONTHLY
    due_day: Optional[int] = None
    status: FeeStatus = FeeStatus.ACTIVE
    description: Optional[str] = None
    current_unit_price: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class FeeTypePage(PageMeta):
    """Phân trang danh sách khoản thu."""
    items: List[FeeType] = Field(default_factory=list)
