from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
# [SỬA] Thêm Computed để ánh xạ chuẩn cột GENERATED ALWAYS AS (...) STORED trên PostgreSQL & SQLite
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Computed,
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
    utility_readings: Mapped[List["UtilityReading"]] = relationship(
        "UtilityReading",
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
        ForeignKey("billing_periods.id"),
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
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    previous_debt: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    credit_applied: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    total_due: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )  # = fee_amount - discount_amount + previous_debt - credit_applied (AC-17.1)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
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
        CheckConstraint("apartment_area >= 0", name="chk_invoices_apartment_area_nonneg"),
        CheckConstraint("fee_amount >= 0", name="chk_invoices_fee_amount_nonneg"),
        CheckConstraint("discount_amount >= 0", name="chk_invoices_discount_amount_nonneg"),
        CheckConstraint("previous_debt >= 0", name="chk_invoices_previous_debt_nonneg"),
        CheckConstraint("credit_applied >= 0", name="chk_invoices_credit_applied_nonneg"),
        CheckConstraint("total_due >= 0", name="chk_invoices_total_due_nonneg"),
        CheckConstraint("paid_amount >= 0", name="chk_invoices_paid_amount_nonneg"),
        CheckConstraint("discount_amount <= fee_amount", name="chk_invoices_discount_le_fee"),
        CheckConstraint(
            "credit_applied <= fee_amount - discount_amount + previous_debt",
            name="chk_invoices_credit_le_net_due",
        ),
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
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0"),
        server_default="0",
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

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
        # [THÊM] Bổ sung 3 CheckConstraint nghiệp vụ khớp 01_schema.sql
        CheckConstraint("discount_amount <= gross_amount", name="chk_invoice_items_discount_le_gross"),
        CheckConstraint("net_amount = gross_amount - discount_amount", name="chk_invoice_items_net_formula"),
        CheckConstraint("paid_amount <= net_amount", name="chk_invoice_items_paid_le_net"),
    )

    @property
    def fee_name(self) -> str:
        return self.fee_type.name if self.fee_type else ""


class UtilityReading(Base, TimestampMixin):
    """Bảng utility_readings (US-38): Chỉ số tiêu thụ điện nước do nhà cung cấp gửi."""
    __tablename__ = "utility_readings"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    household_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("households.id"),
        nullable=False,
        index=True,
    )
    fee_type_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("fee_types.id"),
        nullable=False,
        index=True,
    )
    # [SỬA] Bỏ ondelete="CASCADE" để khớp 01_schema.sql
    billing_period_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("billing_periods.id"),
        nullable=False,
        index=True,
    )
    previous_index: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    current_index: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    # [SỬA] Dùng Computed khớp GENERATED ALWAYS AS (current_index - previous_index) STORED
    consumption: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        Computed("current_index - previous_index", persisted=True),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )  # Snapshot đơn giá tại thời điểm nhập
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )  # consumption * unit_price
    recorded_by: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id"),
        nullable=True,
    )

    # Relationships
    household: Mapped["Household"] = relationship(
        "Household",
        foreign_keys=[household_id],
        lazy="joined",
    )
    fee_type: Mapped["FeeType"] = relationship(
        "FeeType",
        foreign_keys=[fee_type_id],
        lazy="joined",
    )
    billing_period: Mapped["BillingPeriod"] = relationship(
        "BillingPeriod",
        back_populates="utility_readings",
    )
    recorder: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[recorded_by],
        lazy="joined",
    )

    __table_args__ = (
        UniqueConstraint(
            "household_id",
            "fee_type_id",
            "billing_period_id",
            name="uq_utility_readings_household_fee_period",
        ),
        CheckConstraint("previous_index >= 0", name="chk_utility_readings_previous_index_nonneg"),
        CheckConstraint("current_index >= previous_index", name="chk_utility_readings_current_ge_previous"),
        CheckConstraint("unit_price >= 0", name="chk_utility_readings_unit_price_nonneg"),
        CheckConstraint("amount >= 0", name="chk_utility_readings_amount_nonneg"),
        Index("ix_utility_readings_period_fee", "billing_period_id", "fee_type_id"),
    )

    @property
    def household_code(self) -> str:
        return self.household.household_code if self.household else ""

    @property
    def fee_name(self) -> str:
        return self.fee_type.name if self.fee_type else ""