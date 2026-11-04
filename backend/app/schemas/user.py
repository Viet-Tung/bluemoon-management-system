from datetime import datetime
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import RoleResponse, UserResponse
from app.schemas.common import PageMeta


class UserCreate(BaseModel):
    """Schema tạo tài khoản nhân sự mới theo docs/openapi.yaml (US-30)."""
    model_config = ConfigDict(extra="ignore")

    username: str = Field(..., min_length=3, max_length=100, description="Tên đăng nhập (tối thiểu 3 ký tự)")
    full_name: str = Field(..., min_length=1, max_length=255, description="Họ và tên đầy đủ")
    email: Optional[str] = Field(default=None, description="Địa chỉ email liên hệ")
    phone: Optional[str] = Field(default=None, max_length=50, description="Số điện thoại")
    role_id: int = Field(..., description="ID vai trò nhân sự (ADMIN, ACCOUNTANT, TREASURER)")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Tên đăng nhập phải có ít nhất 3 ký tự.")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError("Tên đăng nhập chỉ được chứa chữ cái, chữ số và các ký tự: _ . -")
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


class UserUpdate(BaseModel):
    """Schema cập nhật thông tin tài khoản theo docs/openapi.yaml (US-30)."""
    model_config = ConfigDict(extra="ignore")

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255, description="Họ và tên")
    email: Optional[str] = Field(default=None, description="Email")
    phone: Optional[str] = Field(default=None, max_length=50, description="Số điện thoại")
    is_active: Optional[bool] = Field(default=None, description="Trạng thái kích hoạt")

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


class UserWithTempPassword(UserResponse):
    """Phản hồi tạo tài khoản kèm mật khẩu tạm thời (US-30)."""
    temporary_password: str = Field(..., description="Mật khẩu tạm thời theo chuẩn OpenAPI")
    temp_password: Optional[str] = Field(default=None, description="Alias tương thích ngược")

    def __init__(self, **data):
        if "temporary_password" in data and not data.get("temp_password"):
            data["temp_password"] = data["temporary_password"]
        elif "temp_password" in data and not data.get("temporary_password"):
            data["temporary_password"] = data["temp_password"]
        super().__init__(**data)


class TempPassword(BaseModel):
    """Phản hồi cấp lại mật khẩu tạm theo docs/openapi.yaml (US-30, US-29)."""
    model_config = ConfigDict(extra="ignore")

    temporary_password: str = Field(..., description="Mật khẩu tạm thời")
    temp_password: Optional[str] = Field(default=None, description="Alias tương thích ngược")

    def __init__(self, **data):
        if "temporary_password" in data and not data.get("temp_password"):
            data["temp_password"] = data["temporary_password"]
        elif "temp_password" in data and not data.get("temporary_password"):
            data["temporary_password"] = data["temp_password"]
        super().__init__(**data)


class UserPage(PageMeta):
    """Danh sách người dùng phân trang theo docs/openapi.yaml."""
    items: List[UserResponse] = Field(default_factory=list, description="Danh sách người dùng")



class UserRoleUpdate(BaseModel):
    """Schema gán hoặc thu hồi vai trò theo docs/openapi.yaml (US-31)."""
    model_config = ConfigDict(extra="ignore")

    role_id: int = Field(..., description="ID vai trò mới (1: ADMIN, 2: ACCOUNTANT, 3: TREASURER, 4: RESIDENT)")
