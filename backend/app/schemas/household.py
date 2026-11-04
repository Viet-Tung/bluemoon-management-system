from datetime import date, datetime
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PageMeta


class ResidentAccount(BaseModel):
    """Thông tin tài khoản cư dân tự động sinh theo D-12."""
    model_config = ConfigDict(extra="ignore")

    username: str = Field(..., description="Tên đăng nhập tự động sinh")
    temporary_password: str = Field(..., description="Mật khẩu tạm thời cho lần đăng nhập đầu tiên")


class ResidentCreate(BaseModel):
    """Schema tạo nhân khẩu cư dân ban đầu (chủ hộ hoặc thành viên)."""
    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(..., min_length=1, max_length=255, description="Họ và tên đầy đủ")
    date_of_birth: date = Field(..., description="Ngày sinh")
    gender: str = Field(..., description="Giới tính (NAM, NU, KHAC)")
    cccd: Optional[str] = Field(default=None, description="CCCD/CMND 9-12 chữ số")
    phone: Optional[str] = Field(default=None, max_length=50, description="Số điện thoại")
    email: Optional[str] = Field(default=None, description="Địa chỉ email")
    relationship_to_head: Optional[str] = Field(default=None, max_length=100, description="Quan hệ với chủ hộ")
    is_head: bool = Field(default=False, description="Có phải chủ hộ không")

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in ("NAM", "NU", "KHAC"):
            raise ValueError("Giới tính chỉ có thể là NAM, NU hoặc KHAC.")
        return v

    @field_validator("cccd")
    @classmethod
    def validate_cccd(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not re.match(r"^[0-9]{9,12}$", v):
                raise ValueError("CCCD/CMND phải là chuỗi từ 9 đến 12 chữ số.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$", v):
                raise ValueError("Email không đúng định dạng.")
        return v


class HouseholdCreate(BaseModel):
    """Schema tạo hộ gia đình mới (US-01, AC-01.2, AC-30.2)."""
    model_config = ConfigDict(extra="ignore")

    household_code: str = Field(..., min_length=1, max_length=50, description="Mã hộ gia đình duy nhất (VD: HO-1002)")
    apartment_id: Optional[int] = Field(default=None, description="ID căn hộ gán cho hộ (bỏ trống nếu chưa gán)")
    occupancy_start_date: Optional[date] = Field(default=None, description="Ngày bắt đầu cư trú (mặc định là ngày hiện tại)")
    contact_phone: Optional[str] = Field(default=None, max_length=50, description="Số điện thoại liên hệ")
    contact_email: Optional[str] = Field(default=None, description="Email liên hệ")
    note: Optional[str] = Field(default=None, description="Ghi chú về hộ gia đình")
    head: Optional[ResidentCreate] = Field(default=None, description="Thông tin chủ hộ tạo cùng lúc")

    @field_validator("household_code")
    @classmethod
    def validate_household_code(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Mã hộ gia đình không được để trống.")
        return v

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$", v):
                raise ValueError("Email liên hệ không đúng định dạng.")
        return v


class HouseholdUpdate(BaseModel):
    """Schema cập nhật thông tin hộ gia đình (US-02)."""
    model_config = ConfigDict(extra="ignore")

    contact_phone: Optional[str] = Field(default=None, max_length=50, description="Số điện thoại liên hệ")
    contact_email: Optional[str] = Field(default=None, description="Email liên hệ")
    note: Optional[str] = Field(default=None, description="Ghi chú")

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$", v):
                raise ValueError("Email không đúng định dạng.")
        return v


class HouseholdDeactivate(BaseModel):
    """Schema yêu cầu ngừng quản lý hộ gia đình (US-02)."""
    model_config = ConfigDict(extra="ignore")

    reason: str = Field(..., min_length=1, description="Lý do ngừng quản lý hộ gia đình")

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Lý do ngừng quản lý không được để trống.")
        return v


class HouseholdChangeHead(BaseModel):
    """Schema đổi chủ hộ đại diện (US-02, US-05, AC-02.1)."""
    model_config = ConfigDict(extra="ignore")

    new_head_resident_id: int = Field(..., description="ID nhân khẩu mới được chỉ định làm chủ hộ")
    effective_date: date = Field(..., description="Ngày có hiệu lực thay đổi chủ hộ")
    reason: Optional[str] = Field(default=None, description="Lý do thay đổi chủ hộ")


class Household(BaseModel):
    """Schema chi tiết hộ gia đình theo docs/openapi.yaml."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="ID hộ gia đình")
    household_code: str = Field(..., description="Mã hộ gia đình")
    status: str = Field(..., description="Trạng thái (ACTIVE, INACTIVE)")
    contact_phone: Optional[str] = Field(default=None, description="Số điện thoại liên hệ")
    contact_email: Optional[str] = Field(default=None, description="Email liên hệ")
    note: Optional[str] = Field(default=None, description="Ghi chú")
    apartment_id: Optional[int] = Field(default=None, description="ID căn hộ hiện tại")
    apartment_code: Optional[str] = Field(default=None, description="Mã căn hộ hiện tại")
    floor: Optional[int] = Field(default=None, description="Tầng căn hộ")
    area_m2: Optional[float] = Field(default=None, description="Diện tích căn hộ")
    head_resident_id: Optional[int] = Field(default=None, description="ID chủ hộ hiện tại")
    head_name: Optional[str] = Field(default=None, description="Tên chủ hộ")
    head_phone: Optional[str] = Field(default=None, description="Số điện thoại chủ hộ")
    member_count: int = Field(default=0, description="Số lượng nhân khẩu")
    created_at: datetime = Field(..., description="Thời gian tạo")
    updated_at: datetime = Field(..., description="Thời gian cập nhật")


class HouseholdCreated(Household):
    """Schema trả về khi tạo hộ gia đình thành công kèm tài khoản cư dân (US-01, AC-30.2)."""
    resident_account: Optional[ResidentAccount] = Field(
        default=None,
        description="Thông tin tài khoản cư dân tự động cấp cho hộ mới"
    )


class HouseholdPage(PageMeta):
    """Danh sách hộ gia đình phân trang theo docs/openapi.yaml."""
    items: List[Household] = Field(default_factory=list, description="Danh sách hộ gia đình")
