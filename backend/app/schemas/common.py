from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    """Chi tiết lỗi tại từng trường hoặc từng dòng import."""
    model_config = ConfigDict(extra="ignore")

    field: Optional[str] = Field(default=None, description="Tên trường dữ liệu bị lỗi")
    message: str = Field(..., description="Chi tiết nguyên nhân lỗi")
    row: Optional[int] = Field(default=None, description="Số dòng nếu phát sinh khi import file")


class Error(BaseModel):
    """Cấu trúc lỗi chuẩn hóa 100% theo docs/API_CONTRACT.md (Chương 1.2)."""
    model_config = ConfigDict(extra="ignore")

    code: str = Field(..., description="Mã lỗi dạng SNAKE_CASE", json_schema_extra={"example": "VALIDATION_ERROR"})
    message: str = Field(..., description="Mô tả thân thiện với người dùng")
    details: List[ErrorDetail] = Field(default_factory=list, description="Danh sách chi tiết lỗi")


class PageMeta(BaseModel):
    """Thông tin phân trang chuẩn."""
    model_config = ConfigDict(extra="ignore")

    page: int = Field(default=1, ge=1, description="Trang hiện tại")
    page_size: int = Field(default=20, ge=1, le=100, description="Kích thước trang")
    total: int = Field(default=0, ge=0, description="Tổng số bản ghi")
