from datetime import date
# [THÊM] TYPE_CHECKING để hỗ trợ type hint cho "Household" mà không gây circular import
from typing import TYPE_CHECKING, Optional

# [SỬA] Xóa `Text` thừa; thêm `Index` và `text` để khai báo partial unique index
from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# [THÊM] Khai báo import phục vụ static type checker (Pylance/Mypy)
# Lưu ý: chỉnh lại đường dẫn import nếu class Household nằm ở file khác (vd: app.models.property)
if TYPE_CHECKING:
    from app.models.property import Household


class Vehicle(Base, TimestampMixin):
    """
    Bảng vehicles (US-36, US-37): Quản lý phương tiện đăng ký gửi xe của hộ gia đình.
    Tuân thủ 100% database/01_schema.sql và docs/openapi.yaml.
    """
    __tablename__ = "vehicles"

    # [THÊM] Partial unique index ở tầng DB: chặn trùng biển số khi ACTIVE,
    # nhưng vẫn cho phép đăng ký lại biển số cũ nếu bản ghi trước đã INACTIVE.
    # Hỗ trợ đồng thời cả PostgreSQL (prod) và SQLite (chạy pytest).
    __table_args__ = (
        Index(
            "uq_vehicles_active_plate",
            "plate_number",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'"),
        ),
    )

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
    # [SỬA] Thêm index=True để tối ưu tìm kiếm theo biển số ở GET /vehicles và check trùng
    plate_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String(20), nullable=False)  # MOTORBIKE, CAR, BICYCLE
    brand: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # [SỬA] Thêm server_default="ACTIVE" để khớp default tầng SQL và index=True để tối ưu lọc xe ACTIVE cho US-17
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        server_default="ACTIVE",
        nullable=False,
        index=True,
    )  # ACTIVE, INACTIVE
    registered_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    unregistered_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Quan hệ với hộ gia đình
    household: Mapped["Household"] = relationship("Household", backref="vehicles")