from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SearchEntityType(str, Enum):
    """Loại thực thể tìm kiếm trong Omnibox (US-23)."""
    HOUSEHOLD = "HOUSEHOLD"
    APARTMENT = "APARTMENT"
    RESIDENT = "RESIDENT"
    VEHICLE = "VEHICLE"


class SearchHit(BaseModel):
    """Một kết quả tìm kiếm đơn lẻ trong Omnibox."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    entity_type: SearchEntityType = Field(
        ...,
        description="Loại thực thể: HOUSEHOLD, APARTMENT, RESIDENT, VEHICLE"
    )
    entity_id: int = Field(..., description="ID của thực thể")
    household_id: Optional[int] = Field(
        default=None,
        description="ID hộ gia đình liên quan (nếu có)"
    )
    title: str = Field(..., description="Tiêu đề hiển thị chính")
    subtitle: Optional[str] = Field(
        default=None,
        description="Tiêu đề phụ / thông tin chi tiết hỗ trợ nhận diện nhanh"
    )


class SearchResult(BaseModel):
    """Tập hợp kết quả tìm kiếm Omnibox."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    items: List[SearchHit] = Field(
        default_factory=list,
        description="Danh sách kết quả tìm kiếm gộp từ nhiều thực thể"
    )
