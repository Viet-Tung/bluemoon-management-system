from datetime import date, datetime
# [THÊM] Decimal & ROUND_HALF_UP để làm tròn an toàn tiền tệ từ Numeric(14, 2) sang int (VNĐ)
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
# [SỬA] Thêm Any cho helper validator
from typing import Any, List, Optional
# [SỬA] Thêm model_validator để kiểm tra chéo due_date >= period_month
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import PageMeta


# [THÊM] Helper làm tròn VNĐ nguyên trước khi ép kiểu int trong Pydantic v2,
# tránh lỗi ResponseValidationError (HTTP 500) nếu DB trả về Decimal có phần lẻ (vd: 70000.50)
def _round_vnd(v: Any) -> Any:
    if isinstance(v, Decimal) and v.is_finite():
        return int(v.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if isinstance(v, float):
        d = Decimal(str(v))
        if d.is_finite():
            return int(d.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return v


class BillingPeriodStatus(str, Enum):
    """Trạng thái kỳ thu phí (US-17, US-37)."""
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class InvoiceStatus(str, Enum):
    """Trạng thái giấy báo nộp phí (US-17, US-37, US-47)."""
    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"


class BillingPeriodCreate(BaseModel):
    """Schema tạo kỳ thu mới (POST /billing-periods)."""
    model_config = ConfigDict(extra="ignore")

    period_month: date = Field(
        ...,
        description="Ngày 1 của tháng (định dạng YYYY-MM-01)",
        json_schema_extra={"example": "2026-11-01"},
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Tên kỳ thu (VD: Kỳ thu tháng 11/2026)",
        json_schema_extra={"example": "Kỳ thu phí tháng 11/2026"},
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Hạn nộp phí của kỳ",
        json_schema_extra={"example": "2026-11-20"},
    )

    @field_validator("period_month")
    @classmethod
    def validate_period_month(cls, v: date) -> date:
        if v.day != 1:
            raise ValueError("Kỳ thu phí phải bắt đầu vào ngày 1 của tháng (YYYY-MM-01).")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Tên kỳ thu không được để trống hoặc chỉ chứa khoảng trắng.")
        return s

    # [THÊM] Chặn hạn nộp phí nhỏ hơn ngày bắt đầu kỳ thu
    @model_validator(mode="after")
    def validate_due_date(self) -> "BillingPeriodCreate":
        if self.due_date is not None and self.due_date < self.period_month:
            raise ValueError(
                "Hạn nộp phí (due_date) không được nhỏ hơn ngày bắt đầu kỳ thu (period_month)."
            )
        return self


class BillingPeriod(BaseModel):
    """Schema chi tiết kỳ thu trả về cho client."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="ID kỳ thu")
    period_month: date = Field(..., description="Ngày 1 của tháng")
    name: str = Field(..., description="Tên kỳ thu")
    due_date: Optional[date] = Field(default=None, description="Hạn nộp phí")
    status: BillingPeriodStatus = Field(
        default=BillingPeriodStatus.DRAFT,
        description="Trạng thái kỳ thu (DRAFT, OPEN, CLOSED)",
    )
    generated_at: Optional[datetime] = Field(default=None, description="Thời điểm chạy tính phí tự động")
    closed_at: Optional[datetime] = Field(default=None, description="Thời điểm chốt kỳ")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class BillingPeriodPage(PageMeta):
    """Phân trang danh sách kỳ thu."""
    items: List[BillingPeriod] = Field(default_factory=list, description="Danh sách kỳ thu")
    # Lưu ý: Nếu PageMeta trong app/schemas/common.py đã có sẵn total_pages thì có thể bỏ dòng này
    total_pages: Optional[int] = Field(default=None, description="Tổng số trang")


class GenerateResult(BaseModel):
    """Kết quả chạy động cơ tính phí (POST /billing-periods/{id}/generate) (US-17, US-37)."""
    model_config = ConfigDict(extra="ignore")

    households_processed: int = Field(..., ge=0, description="Số hộ gia đình đã xử lý")
    invoices_created: int = Field(..., ge=0, description="Số hóa đơn đã tạo hoặc cập nhật")
    total_fee_amount: int = Field(
        default=0,
        ge=0,
        description="Tổng số tiền phát sinh phải nộp (VNĐ)",
    )

    # [THÊM] Tự động làm tròn nếu engine trả về Decimal
    @field_validator("total_fee_amount", mode="before")
    @classmethod
    def coerce_total_fee_amount(cls, v: Any) -> Any:
        return _round_vnd(v)


class InvoiceItem(BaseModel):
    """Chi tiết từng dòng phí trong giấy báo nộp phí (US-17, US-37, US-47)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="ID dòng chi tiết phí")
    invoice_id: int = Field(..., description="ID hóa đơn")
    fee_type_id: int = Field(..., description="ID khoản thu")
    fee_name: str = Field(..., description="Tên khoản thu (VD: Phí gửi xe máy, Phí quản lý)")
    quantity: float = Field(..., ge=0, description="Số lượng (số xe, m2, kWh...)")
    unit_price: int = Field(..., ge=0, description="Đơn giá áp dụng (VNĐ)")
    gross_amount: int = Field(..., ge=0, description="Thành tiền trước miễn giảm (VNĐ)")
    discount_amount: int = Field(default=0, ge=0, description="Số tiền được miễn giảm (VNĐ)")
    net_amount: int = Field(..., ge=0, description="Số tiền thực tế phải nộp (VNĐ)")
    paid_amount: int = Field(default=0, ge=0, description="Số tiền đã thanh toán (VNĐ)")
    description: Optional[str] = Field(
        default=None,
        description="Diễn giải cách tính (VD: '2 Xe máy × 70.000 đ', '85,5 m² × 7.000 đ')",
    )

    # [THÊM] Chuẩn hóa các cột Numeric(14, 2) từ ORM sang int VNĐ an toàn
    @field_validator(
        "unit_price",
        "gross_amount",
        "discount_amount",
        "net_amount",
        "paid_amount",
        mode="before",
    )
    @classmethod
    def coerce_money_fields(cls, v: Any) -> Any:
        return _round_vnd(v)


class Invoice(BaseModel):
    """Giấy báo nộp phí tổng hợp của hộ trong kỳ (US-17, US-37, US-47)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="ID giấy báo nộp phí")
    billing_period_id: Optional[int] = Field(None, description="ID kỳ thu")
    household_id: int = Field(..., description="ID hộ gia đình")
    household_code: str = Field(default="", description="Mã hộ gia đình")
    apartment_id: Optional[int] = Field(default=None, description="ID căn hộ")
    apartment_code: Optional[str] = Field(default=None, description="Mã căn hộ (nếu có)")
    apartment_area: float = Field(..., ge=0, description="Snapshot diện tích căn hộ (m2)")
    fee_amount: int = Field(..., ge=0, description="Tổng các khoản phí phát sinh kỳ này (VNĐ)")
    discount_amount: int = Field(default=0, ge=0, description="Tổng số tiền được miễn giảm (VNĐ)")
    previous_debt: int = Field(default=0, ge=0, description="Nợ cũ lũy kế từ các kỳ trước (VNĐ)")
    credit_applied: int = Field(default=0, ge=0, description="Số dư có được trích bù trừ (VNĐ)")
    total_due: int = Field(
        ...,
        ge=0,
        description="Tổng thực tế phải nộp = fee_amount - discount_amount + previous_debt - credit_applied (AC-17.1)",
    )
    paid_amount: int = Field(default=0, ge=0, description="Số tiền đã thanh toán (VNĐ)")
    status: InvoiceStatus = Field(
        default=InvoiceStatus.UNPAID,
        description="Trạng thái thanh toán (UNPAID, PARTIAL, PAID)",
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # [THÊM] Chuẩn hóa các cột Numeric(14, 2) từ ORM sang int VNĐ an toàn
    @field_validator(
        "fee_amount",
        "discount_amount",
        "previous_debt",
        "credit_applied",
        "total_due",
        "paid_amount",
        mode="before",
    )
    @classmethod
    def coerce_money_fields(cls, v: Any) -> Any:
        return _round_vnd(v)


class InvoiceDetail(Invoice):
    """Chi tiết giấy báo nộp phí kèm danh sách từng khoản phí (GET /invoices/{id})."""
    items: List[InvoiceItem] = Field(
        default_factory=list,
        description="Danh sách từng khoản phí chi tiết (phí gửi xe, phí quản lý...)",
    )


class InvoicePage(PageMeta):
    """Phân trang danh sách giấy báo nộp phí (GET /invoices)."""
    items: List[Invoice] = Field(default_factory=list, description="Danh sách giấy báo nộp phí")
    total_pages: Optional[int] = Field(default=None, description="Tổng số trang")


# ==============================================================================
# SCHEMAS CHO CHỈ SỐ ĐIỆN / NƯỚC (US-38)
# ==============================================================================

class UtilityReadingBase(BaseModel):
    """Schema cơ sở cho chỉ số điện/nước (US-38)."""
    household_id: int = Field(..., description="ID hộ gia đình")
    fee_type_id: int = Field(..., description="ID loại phí (điện, nước)")
    billing_period_id: int = Field(..., description="ID kỳ tính phí")
    previous_index: float = Field(..., ge=0, description="Chỉ số đầu kỳ")
    current_index: float = Field(..., ge=0, description="Chỉ số cuối kỳ")


class UtilityReadingCreate(UtilityReadingBase):
    """Schema tạo chỉ số điện/nước mới (POST /utility-readings)."""
    model_config = ConfigDict(extra="ignore")

    unit_price: Optional[int] = Field(
        default=None,
        ge=0,
        description="Tùy chọn; mặc định lấy đơn giá hiệu lực của khoản thu",
    )

    @model_validator(mode="after")
    def validate_indexes(self) -> "UtilityReadingCreate":
        if self.current_index < self.previous_index:
            raise ValueError(
                "Chỉ số cuối kỳ (current_index) phải lớn hơn hoặc bằng chỉ số đầu kỳ (previous_index)."
            )
        return self


class UtilityReadingUpdate(BaseModel):
    """Schema sửa chỉ số điện/nước (PATCH /utility-readings/{id})."""
    model_config = ConfigDict(extra="ignore")

    previous_index: Optional[float] = Field(default=None, ge=0, description="Chỉ số đầu kỳ mới")
    current_index: Optional[float] = Field(default=None, ge=0, description="Chỉ số cuối kỳ mới")
    unit_price: Optional[int] = Field(default=None, ge=0, description="Đơn giá mới (VNĐ)")

    @model_validator(mode="after")
    def validate_indexes(self) -> "UtilityReadingUpdate":
        if (
            self.current_index is not None
            and self.previous_index is not None
            and self.current_index < self.previous_index
        ):
            raise ValueError(
                "Chỉ số cuối kỳ (current_index) phải lớn hơn hoặc bằng chỉ số đầu kỳ (previous_index)."
            )
        return self


class UtilityReading(BaseModel):
    """Schema thông tin chỉ số điện/nước trả về cho client."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="ID bản ghi chỉ số điện/nước")
    household_id: int = Field(..., description="ID hộ gia đình")
    household_code: str = Field(default="", description="Mã hộ gia đình")
    fee_type_id: int = Field(..., description="ID khoản thu")
    fee_name: str = Field(default="", description="Tên khoản thu (VD: Tiền điện, Tiền nước)")
    billing_period_id: int = Field(..., description="ID kỳ thu")
    previous_index: float = Field(..., ge=0, description="Chỉ số đầu kỳ")
    current_index: float = Field(..., ge=0, description="Chỉ số cuối kỳ")
    consumption: float = Field(..., ge=0, description="Lượng tiêu thụ (current_index - previous_index)")
    unit_price: int = Field(..., ge=0, description="Đơn giá áp dụng (VNĐ)")
    amount: int = Field(..., ge=0, description="Thành tiền = consumption * unit_price (VNĐ)")
    recorded_by: Optional[int] = Field(default=None, description="ID nhân viên ghi nhận")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("unit_price", "amount", mode="before")
    @classmethod
    def coerce_money_fields(cls, v: Any) -> Any:
        return _round_vnd(v)

    @field_validator("previous_index", "current_index", "consumption", mode="before")
    @classmethod
    def coerce_index_fields(cls, v: Any) -> Any:
        if isinstance(v, Decimal):
            return float(v)
        return v


class UtilityReadingPage(PageMeta):
    """Phân trang danh sách chỉ số điện/nước (GET /utility-readings)."""
    items: List[UtilityReading] = Field(default_factory=list, description="Danh sách chỉ số điện/nước")
    total_pages: Optional[int] = Field(default=None, description="Tổng số trang")
