from pydantic import BaseModel, ConfigDict, Field


class ImportResult(BaseModel):
    """Schema kết quả import file Excel theo OpenAPI specification."""
    model_config = ConfigDict(extra="ignore")

    total_rows: int = Field(..., description="Tổng số dòng dữ liệu trong file")
    imported_rows: int = Field(..., description="Số dòng đã import thành công vào hệ thống")