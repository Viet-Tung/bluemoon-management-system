from datetime import date, datetime
# [THÊM] Dùng Decimal cho toàn bộ cột Numeric để tránh sai số làm tròn của float
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
# [SỬA] Xóa import thừa `func`
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.fee import FeeType
    from app.models.property import Apartment, Household
    from app.models.user import User


class BillingPeriod(Base, TimestampMixin):
    """Bảng billing_periods (US-17, US-37): Kỳ tính phí hàng tháng."""
    __tablename__ = "billing_periods"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    period_month: Mapped[date] = mapped_column(
        Date,
        unique=True,
        nullable=False,
        index=True,
    )  # Ngày 1 của tháng
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )
    # [SỬA] Thêm server_default="DRAFT" khớp với default tầng SQL
    status: Mapped[str] = mapped_column(
        String(20),
        default="DRAFT",
        server_default="DRAFT",
        nullable=False,
    )  # DRAFT, OPEN, CLOSED
    generated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    invoices: Mapped[List["Invoice"]] = relationship(
        "Invoice",
        back_populates="billing_period",
        cascade="all, delete-orphan",
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )


class Invoice(Base, TimestampMixin):
    """Bảng invoices (US-17, US-37, US-47): Giấy báo nộp phí 1 hộ / 1 kỳ."""
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    billing_period_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("billing_periods.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    household_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("households.id"),
        nullable=False,
        index=True,
    )
    apartment_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("apartments.id"),
        nullable=True,
    )
    # [SỬA] Đổi toàn bộ cột Numeric sang Mapped[Decimal] + default=Decimal("0") + server_default="0"
    apartment_area: Mapped[Decimal] = mapped_column(
        Numeric(8, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Snapshot diện tích lúc tạo giấy báo
    fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Tổng phí phát sinh kỳ này (chưa trừ miễn giảm)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Tổng tiền được miễn giảm
    previous_debt: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Nợ cũ lũy kế chưa thanh toán từ các kỳ trước
    credit_applied: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Tiền trích từ số dư có để bù trừ
    total_due: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )  # = fee_amount - discount_amount + previous_debt - credit_applied (AC-17.1)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Tiền đã thanh toán
    # [SỬA] Thêm server_default="UNPAID"
    status: Mapped[str] = mapped_column(
        String(20),
        default="UNPAID",
        server_default="UNPAID",
        nullable=False,
    )  # UNPAID, PARTIAL, PAID

    # Relationships
    billing_period: Mapped["BillingPeriod"] = relationship(
        "BillingPeriod",
        back_populates="invoices",
    )
    household: Mapped["Household"] = relationship(
        "Household",
        foreign_keys=[household_id],
        lazy="joined",
    )
    apartment: Mapped[Optional["Apartment"]] = relationship(
        "Apartment",
        foreign_keys=[apartment_id],
        lazy="joined",
    )
    items: Mapped[List["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("billing_period_id", "household_id", name="uq_invoices_period_household"),
        # [THÊM] Chặn diện tích âm
        CheckConstraint("apartment_area >= 0", name="chk_invoices_apartment_area_nonneg"),
        CheckConstraint("total_due >= 0", name="chk_invoices_total_due_nonneg"),
        CheckConstraint("fee_amount >= 0", name="chk_invoices_fee_amount_nonneg"),
        CheckConstraint("discount_amount >= 0", name="chk_invoices_discount_amount_nonneg"),
        CheckConstraint("previous_debt >= 0", name="chk_invoices_previous_debt_nonneg"),
        CheckConstraint("credit_applied >= 0", name="chk_invoices_credit_applied_nonneg"),
        CheckConstraint("paid_amount >= 0", name="chk_invoices_paid_amount_nonneg"),
        Index("ix_invoices_household_period", "household_id", "billing_period_id"),
        Index("ix_invoices_period_status", "billing_period_id", "status"),
    )

    @property
    def household_code(self) -> str:
        return self.household.household_code if self.household else ""


class InvoiceItem(Base):
    """Bảng invoice_items (US-17, US-37, US-47): Chi tiết từng dòng phí trong giấy báo."""
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    invoice_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fee_type_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("fee_types.id"),
        nullable=False,
        index=True,
    )
    # [SỬA] Đổi sang Mapped[Decimal]
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )  # Số xe / m2 / kWh...
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )  # Snapshot đơn giá tại kỳ tính
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )  # quantity * unit_price
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Số tiền được miễn giảm cho dòng phí này
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )  # = gross_amount - discount_amount
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )  # Số tiền đã thanh toán cho dòng phí này
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )  # VD: "2 Xe máy × 70.000 đ"

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="items",
    )
    fee_type: Mapped["FeeType"] = relationship(
        "FeeType",
        foreign_keys=[fee_type_id],
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint("invoice_id", "fee_type_id", name="uq_invoice_items_invoice_fee"),
        CheckConstraint("quantity >= 0", name="chk_invoice_items_quantity_nonneg"),
        CheckConstraint("unit_price >= 0", name="chk_invoice_items_unit_price_nonneg"),
        CheckConstraint("gross_amount >= 0", name="chk_invoice_items_gross_amount_nonneg"),
        CheckConstraint("discount_amount >= 0", name="chk_invoice_items_discount_amount_nonneg"),
        CheckConstraint("net_amount >= 0", name="chk_invoice_items_net_amount_nonneg"),
        CheckConstraint("paid_amount >= 0", name="chk_invoice_items_paid_amount_nonneg"),
    )

    @property
    def fee_name(self) -> str:
        return self.fee_type.name if self.fee_type else ""