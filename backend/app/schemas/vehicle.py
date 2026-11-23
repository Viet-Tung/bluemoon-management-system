from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PageMeta
from app.schemas.fee import VehicleType


# [THÊM] Helper dùng chung để đảm bảo logic chuẩn hóa đồng nhất giữa Create và Update
def _normalize_plate_number(v: str) -> str:
    # Xóa toàn bộ khoảng trắng (đầu, cuối và ở giữa) rồi viết hoa
    s = "".join(v.split()).upper()
    if not s:
        raise ValueError("Biển số xe không được để trống hoặc chỉ chứa khoảng trắng.")
    return s


def _clean_optional_str(v: Optional[str]) -> Optional[str]:
    if v is not None:
        s = v.strip()
        return s if s else None
    return None


class VehicleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class VehicleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    plate_number: str = Field(..., min_length=1, max_length=50, description="Biển số xe")
    vehicle_type: VehicleType = Field(..., description="Loại phương tiện (MOTORBIKE, CAR, BICYCLE)")
    brand: Optional[str] = Field(default=None, max_length=100, description="Hãng sản xuất / nhãn hiệu xe")
    color: Optional[str] = Field(default=None, max_length=50, description="Màu sơn xe")


class VehicleCreate(VehicleBase):
    """Schema đăng ký phương tiện mới cho hộ gia đình (US-36)."""

    household_id: int = Field(..., gt=0, description="ID hộ gia đình sở hữu phương tiện")
    registered_date: Optional[date] = Field(default=None, description="Ngày bắt đầu đăng ký gửi xe (mặc định hôm nay)")

    # [SỬA] Dùng helper xóa toàn bộ khoảng trắng thay vì chỉ strip()
    @field_validator("plate_number")
    @classmethod
    def validate_plate_number(cls, v: str) -> str:
        return _normalize_plate_number(v)

    @field_validator("brand", "color")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        return _clean_optional_str(v)


class VehicleUpdate(BaseModel):
    """Schema cập nhật thông tin phương tiện (US-36)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    plate_number: Optional[str] = Field(default=None, min_length=1, max_length=50, description="Biển số xe mới")
    vehicle_type: Optional[VehicleType] = Field(default=None, description="Loại phương tiện")
    brand: Optional[str] = Field(default=None, max_length=100, description="Nhãn hiệu")
    color: Optional[str] = Field(default=None, max_length=50, description="Màu sơn")

    # [SỬA] Chặn client gửi tường minh {"plate_number": null} gây lỗi 500 ở DB (vì cột nullable=False)
    @field_validator("plate_number")
    @classmethod
    def validate_plate_number_if_present(cls, v: Optional[str]) -> str:
        if v is None:
            raise ValueError("Biển số xe không được để trống (null).")
        return _normalize_plate_number(v)

    # [THÊM] Chặn client gửi tường minh {"vehicle_type": null}
    @field_validator("vehicle_type")
    @classmethod
    def validate_vehicle_type_if_present(cls, v: Optional[VehicleType]) -> VehicleType:
        if v is None:
            raise ValueError("Loại phương tiện không được để trống (null).")
        return v

    @field_validator("brand", "color")
    @classmethod
    def clean_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        return _clean_optional_str(v)


class VehicleUnregister(BaseModel):
    """Schema hủy đăng ký gửi xe của hộ gia đình (US-36)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    unregistered_date: Optional[date] = Field(default=None, description="Ngày hủy đăng ký gửi xe (mặc định hôm nay)")


class Vehicle(BaseModel):
    """Chi tiết phương tiện trả về cho client (US-36)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="ID phương tiện")
    household_id: int = Field(..., description="ID hộ gia đình")
    plate_number: str = Field(..., description="Biển số xe")
    vehicle_type: VehicleType = Field(..., description="Loại phương tiện")
    brand: Optional[str] = Field(default=None, description="Nhãn hiệu")
    color: Optional[str] = Field(default=None, description="Màu sơn")
    status: VehicleStatus = Field(default=VehicleStatus.ACTIVE, description="Trạng thái (ACTIVE, INACTIVE)")
    registered_date: date = Field(..., description="Ngày đăng ký")
    unregistered_date: Optional[date] = Field(default=None, description="Ngày hủy đăng ký")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VehiclePage(PageMeta):
    """Phân trang danh sách phương tiện (US-36)."""
    items: List[Vehicle] = Field(default_factory=list, description="Danh sách phương tiện")