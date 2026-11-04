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


class Apartment(Base, TimestampMixin):
    """Bảng apartments (US-01, T-01): Thực thể căn hộ vật lý."""
    __tablename__ = "apartments"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    floor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    area_m2: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    occupancies: Mapped[List["ApartmentOccupancy"]] = relationship(
        "ApartmentOccupancy",
        back_populates="apartment",
        cascade="all, delete-orphan"
    )


class Household(Base, TimestampMixin):
    """Bảng households (US-01, T-02): Thực thể hộ gia đình."""
    __tablename__ = "households"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    household_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    occupancies: Mapped[List["ApartmentOccupancy"]] = relationship(
        "ApartmentOccupancy",
        back_populates="household",
        cascade="all, delete-orphan"
    )
    residents: Mapped[List["Resident"]] = relationship(
        "Resident",
        back_populates="household",
        cascade="all, delete-orphan"
    )


class ApartmentOccupancy(Base):
    """Bảng apartment_occupancies: Liên kết lịch sử cư trú giữa Căn hộ và Hộ gia đình."""
    __tablename__ = "apartment_occupancies"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    apartment_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("apartments.id"),
        nullable=False,
        index=True
    )
    household_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("households.id"),
        nullable=False,
        index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    end_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="occupancies")
    household: Mapped["Household"] = relationship("Household", back_populates="occupancies")


class Resident(Base, TimestampMixin):
    """Bảng residents (US-05..07): Danh sách nhân khẩu cư trú trong hộ gia đình."""
    __tablename__ = "residents"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    household_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("households.id"),
        nullable=False,
        index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # NAM, NU, KHAC
    cccd: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    relationship_to_head: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_head: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    residence_status: Mapped[str] = mapped_column(
        String(20),
        default="THUONG_TRU",
        nullable=False
    )  # THUONG_TRU, TAM_VANG, DA_CHUYEN_DI, DA_QUA_DOI
    status_effective_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("users.id"),
        nullable=True
    )
    delete_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    household: Mapped["Household"] = relationship("Household", back_populates="residents")

