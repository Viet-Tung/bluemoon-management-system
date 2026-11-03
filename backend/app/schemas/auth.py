from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TokenPayload(BaseModel):
    """Payload được mã hóa bên trong JWT Access Token."""
    model_config = ConfigDict(extra="ignore")

    sub: str
    username: str
    role: str
    household_id: Optional[int] = None
    must_change_password: bool = False
    exp: Optional[int] = None
    iat: Optional[int] = None


class RoleResponse(BaseModel):
    """Đặc tả Role trả về theo docs/openapi.yaml."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    code: str = Field(..., description="Mã vai trò: ADMIN, ACCOUNTANT, TREASURER, RESIDENT")
    name: str = Field(..., description="Tên hiển thị vai trò")
    description: Optional[str] = Field(default=None, description="Mô tả quyền hạn")


class UserResponse(BaseModel):
    """Đặc tả thông tin User trả về theo docs/openapi.yaml."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    username: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: RoleResponse
    household_id: Optional[int] = None
    is_active: bool = True
    must_change_password: bool = False
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Dữ liệu yêu cầu đăng nhập theo docs/openapi.yaml."""
    model_config = ConfigDict(extra="ignore")

    username: str = Field(..., min_length=1, description="Tên đăng nhập")
    password: str = Field(..., min_length=1, description="Mật khẩu tài khoản")


class LoginResponse(BaseModel):
    """Phản hồi đăng nhập thành công theo docs/openapi.yaml."""
    model_config = ConfigDict(extra="ignore")

    token: str = Field(..., description="JWT Access Token")
    token_type: str = Field(default="Bearer", description="Loại token")
    expires_in: int = Field(..., description="Số giây token còn hiệu lực")
    user: UserResponse = Field(..., description="Thông tin tài khoản đăng nhập")
