from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PageMeta


class BackupStatus(str, Enum):
    """Trạng thái của tác vụ sao lưu CSDL."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class BackupJob(BaseModel):
    """Schema thông tin tiến trình / tác vụ sao lưu CSDL theo docs/openapi.yaml (US-45)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="Định danh duy nhất của tác vụ sao lưu")
    status: str = Field(..., description="Trạng thái tiến trình sao lưu (QUEUED, RUNNING, SUCCEEDED, FAILED)")
    requested_by: Optional[int] = Field(default=None, description="ID người dùng yêu cầu thủ công (null nếu là cronjob)")
    requested_at: datetime = Field(..., description="Thời điểm khởi tạo yêu cầu sao lưu")
    finished_at: Optional[datetime] = Field(default=None, description="Thời điểm hoàn tất sao lưu (null nếu đang chạy hoặc thất bại)")
    size_bytes: Optional[int] = Field(default=None, description="Dung lượng tệp sao lưu tính bằng bytes")


class BackupJobPage(PageMeta):
    """Danh sách lịch sử sao lưu CSDL phân trang theo docs/openapi.yaml (US-45)."""
    items: List[BackupJob] = Field(default_factory=list, description="Danh sách các tác vụ sao lưu")

