from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.property import Apartment
from app.schemas.apartment import (
    Apartment as ApartmentSchema,
    ApartmentCreate,
    ApartmentPage,
    ApartmentUpdate,
)

router = APIRouter(tags=["Apartments"])


@router.get(
    "",
    response_model=ApartmentPage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách căn hộ",
    description="Tra cứu và lọc danh sách căn hộ theo tầng và trạng thái (US-01). Phân quyền: ADMIN, ACCOUNTANT.",
)
def list_apartments(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi mỗi trang (1-100)"),
    floor: Optional[int] = Query(default=None, description="Lọc theo số tầng"),
    status_param: Optional[str] = Query(default=None, alias="status", description="Lọc theo trạng thái (ACTIVE, INACTIVE)"),
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> ApartmentPage:
    """Liệt kê danh sách căn hộ kèm phân trang và bộ lọc theo OpenAPI spec."""
    query = select(Apartment)

    if floor is not None:
        query = query.where(Apartment.floor == floor)

    if status_param is not None:
        status_clean = status_param.strip().upper()
        if status_clean not in ("ACTIVE", "INACTIVE"):
            raise AppAPIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="VALIDATION_ERROR",
                message="Trạng thái chỉ có thể là ACTIVE hoặc INACTIVE."
            )
        query = query.where(Apartment.status == status_clean)

    # Đếm tổng số bản ghi phù hợp
    total_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(total_stmt) or 0

    # Phân trang và sắp xếp theo mã căn hộ
    items_stmt = query.order_by(Apartment.code.asc()).offset((page - 1) * page_size).limit(page_size)
    apartments = db.scalars(items_stmt).all()

    return ApartmentPage(
        page=page,
        page_size=page_size,
        total=total,
        items=[ApartmentSchema.model_validate(a) for a in apartments]
    )


@router.post(
    "",
    response_model=ApartmentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo căn hộ mới",
    description="Khai báo căn hộ vật lý mới với diện tích > 0 (US-01, AC-01.1). Phân quyền: ADMIN.",
)
def create_apartment(
    req: ApartmentCreate,
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles("ADMIN")),
) -> ApartmentSchema:
    """Tạo căn hộ mới, kiểm tra trùng mã căn hộ."""
    # Kiểm tra trùng lặp mã căn hộ (case-insensitive)
    existing = db.scalar(
        select(Apartment).where(func.lower(Apartment.code) == req.code.strip().lower())
    )
    if existing:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_APARTMENT_CODE",
            message=f"Mã căn hộ '{req.code.strip()}' đã tồn tại trên hệ thống."
        )

    new_apartment = Apartment(
        code=req.code.strip(),
        floor=req.floor,
        area_m2=req.area_m2,
        status="ACTIVE",
        note=req.note.strip() if req.note else None
    )
    db.add(new_apartment)
    db.commit()
    db.refresh(new_apartment)

    return ApartmentSchema.model_validate(new_apartment)


@router.get(
    "/{id:int}",
    response_model=ApartmentSchema,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết căn hộ",
    description="Xem thông tin chi tiết của một căn hộ theo ID (US-01). Phân quyền: ADMIN, ACCOUNTANT.",
)
def get_apartment(
    id: int,
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> ApartmentSchema:
    """Lấy thông tin chi tiết căn hộ theo ID."""
    apartment = db.scalar(select(Apartment).where(Apartment.id == id))
    if not apartment:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy căn hộ có ID {id}."
        )

    return ApartmentSchema.model_validate(apartment)


@router.patch(
    "/{id:int}",
    response_model=ApartmentSchema,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật căn hộ",
    description="Cập nhật diện tích, tầng, trạng thái hoặc ghi chú căn hộ (US-01). Phân quyền: ADMIN.",
)
def update_apartment(
    id: int,
    req: ApartmentUpdate,
    db: Session = Depends(get_db),
    _current_user = Depends(require_roles("ADMIN")),
) -> ApartmentSchema:
    """Cập nhật thông tin căn hộ."""
    apartment = db.scalar(select(Apartment).where(Apartment.id == id))
    if not apartment:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy căn hộ có ID {id}."
        )

    if req.floor is not None:
        apartment.floor = req.floor
    if req.area_m2 is not None:
        apartment.area_m2 = req.area_m2
    if req.status is not None:
        apartment.status = req.status
    if req.note is not None:
        apartment.note = req.note.strip() if req.note else None

    db.commit()
    db.refresh(apartment)

    return ApartmentSchema.model_validate(apartment)

