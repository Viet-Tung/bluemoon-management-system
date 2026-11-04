from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PageMeta


class AuditLogResponse(BaseModel):
    """Schema nhật ký thao tác kiểm toán chi tiết theo docs/openapi.yaml (US-32)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="Định danh duy nhất của bản ghi nhật ký")
    user_id: Optional[int] = Field(default=None, description="ID người dùng thực hiện thao tác (null nếu là hệ thống)")
    action: str = Field(..., description="Mã hành động nghiệp vụ (ví dụ: CHANGE_ROLE, LOCK_USER, UNLOCK_USER, RESET_PASSWORD, ACCESS_DENIED)")
    entity_type: str = Field(..., description="Loại thực thể bị tác động (ví dụ: USER, HOUSEHOLD, APARTMENT)")
    entity_id: Optional[str] = Field(default=None, description="Định danh thực thể bị tác động")
    old_value: Optional[Dict[str, Any]] = Field(default=None, description="Giá trị dữ liệu trước khi thay đổi")
    new_value: Optional[Dict[str, Any]] = Field(default=None, description="Giá trị dữ liệu sau khi thay đổi")
    reason: Optional[str] = Field(default=None, description="Lý do hoặc mô tả chi tiết của hành động")
    ip_address: Optional[str] = Field(default=None, description="Địa chỉ IP của client")
    user_agent: Optional[str] = Field(default=None, description="Thông tin User-Agent của client")
    created_at: datetime = Field(..., description="Thời điểm ghi nhận thao tác")


class AuditLogPage(PageMeta):
    """Danh sách nhật ký thao tác phân trang theo docs/openapi.yaml (US-32)."""
    items: List[AuditLogResponse] = Field(default_factory=list, description="Danh sách bản ghi nhật ký kiểm toán")

