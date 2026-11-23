from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FeeType(Base, TimestampMixin):
    """Bảng fee_types (US-12, US-13): Khoản thu bắt buộc trong danh mục phí."""
    __tablename__ = "fee_types"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    fee_group: Mapped[str] = mapped_column(String(50), nullable=False)  # MANAGEMENT, PARKING, UTILITY, OTHER
    calc_method: Mapped[str] = mapped_column(String(50), nullable=False)  # PER_M2, PER_HOUSEHOLD, PER_PERSON, PER_VEHICLE, METERED
    unit_label: Mapped[str] = mapped_column(String(50), nullable=False)  # m2, hộ, người, xe, kWh, m3...
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # MOTORBIKE, CAR, BICYCLE
    is_pass_through: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        nullable=True
    )
    cycle: Mapped[str] = mapped_column(String(50), default="MONTHLY", nullable=False)  # MONTHLY, QUARTERLY, YEARLY
    due_day: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)  # 1..31
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, INACTIVE
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id"),
        nullable=True
    )

    rates: Mapped[List["FeeRate"]] = relationship(
        "FeeRate",
        back_populates="fee_type",
        cascade="all, delete-orphan",
        order_by="desc(FeeRate.effective_from)",
    )

    @property
    def current_unit_price(self) -> Optional[int]:
        return getattr(self, "_current_unit_price", None)

    @current_unit_price.setter
    def current_unit_price(self, val: Optional[int]):
        self._current_unit_price = val


class FeeRate(Base):
    """Bảng fee_rates (US-14): Lịch sử đơn giá theo ngày hiệu lực."""
    __tablename__ = "fee_rates"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    fee_type_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("fee_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_price: Mapped[float] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    effective_from: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    effective_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    fee_type: Mapped["FeeType"] = relationship("FeeType", back_populates="rates")


