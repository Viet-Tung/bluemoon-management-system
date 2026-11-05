from datetime import date
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.fee import FeeType
from app.models.user import AuditLog, User
from app.schemas.fee import (
    FeeGroup,
    FeeStatus,
    FeeType as FeeTypeSchema,
    FeeTypeCreate,
    FeeTypePage,
    FeeTypeUpdate,
)

router = APIRouter(tags=["Fee catalog"])


def get_current_unit_price(db: Session, fee_type_id: int) -> Optional[int]:
    """Tra cứu đơn giá đang có hiệu lực trong ngày hiện tại nếu đã có bảng fee_rates."""
    try:
        today = date.today()
        stmt = text("""
            SELECT unit_price FROM fee_rates
            WHERE fee_type_id = :id
              AND effective_from <= :today
              AND (effective_to IS NULL OR effective_to >= :today)
            ORDER BY effective_from DESC, id DESC
            LIMIT 1
        """)
        row = db.execute(stmt, {"id": fee_type_id, "today": today}).fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        pass
    return None


@router.get(
    "",
    response_model=FeeTypePage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách khoản thu",
    description="Tra cứu danh mục khoản thu có phân trang và bộ lọc nhóm phí, trạng thái (US-12). Phân quyền: ADMIN, ACCOUNTANT.",
)
def list_fee_types(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Kích thước trang (1-100)"),
    status_param: Optional[str] = Query(default=None, alias="status", description="Lọc theo trạng thái (ACTIVE, INACTIVE)"),
    fee_group: Optional[str] = Query(default=None, description="Lọc theo nhóm phí (MANAGEMENT, PARKING, UTILITY, OTHER)"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeTypePage:
    """Danh sách danh mục khoản thu bắt buộc kèm phân trang."""
    query = select(FeeType)

    if status_param is not None:
        status_clean = status_param.strip().upper()
        if status_clean not in (FeeStatus.ACTIVE.value, FeeStatus.INACTIVE.value):
            raise AppAPIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="VALIDATION_ERROR",
                message="Trạng thái chỉ có thể là ACTIVE hoặc INACTIVE."
            )
        query = query.where(FeeType.status == status_clean)

    if fee_group is not None:
        group_clean = fee_group.strip().upper()
        valid_groups = [g.value for g in FeeGroup]
        if group_clean not in valid_groups:
            raise AppAPIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="VALIDATION_ERROR",
                message=f"Nhóm phí không hợp lệ. Cho phép: {', '.join(valid_groups)}."
            )
        query = query.where(FeeType.fee_group == group_clean)

    total_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(total_stmt) or 0

    items_stmt = query.order_by(FeeType.id.asc()).offset((page - 1) * page_size).limit(page_size)
    fee_types = db.scalars(items_stmt).all()

    items = []
    for ft in fee_types:
        ft.current_unit_price = get_current_unit_price(db, ft.id)
        items.append(FeeTypeSchema.model_validate(ft))

    return FeeTypePage(
        page=page,
        page_size=page_size,
        total=total,
        items=items
    )


@router.post(
    "",
    response_model=FeeTypeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo khoản thu mới",
    description="Khai báo khoản thu bắt buộc mới vào danh mục phí (US-12, AC-12.1). Phân quyền: ADMIN, ACCOUNTANT.",
)
def create_fee_type(
    req: FeeTypeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeTypeSchema:
    """Tạo mới khoản thu, kiểm tra trùng mã khoản thu (DUPLICATE_FEE_CODE)."""
    clean_code = req.code.strip().upper()

    existing = db.scalar(
        select(FeeType).where(func.lower(FeeType.code) == clean_code.lower())
    )
    if existing:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_FEE_CODE",
            message=f"Mã khoản thu '{clean_code}' đã tồn tại trên hệ thống."
        )

    new_fee = FeeType(
        code=clean_code,
        name=req.name.strip(),
        fee_group=req.fee_group.value,
        calc_method=req.calc_method.value,
        unit_label=req.unit_label.strip(),
        vehicle_type=req.vehicle_type.value if req.vehicle_type else None,
        is_pass_through=req.is_pass_through,
        provider_id=req.provider_id,
        cycle=req.cycle.value,
        due_day=req.due_day,
        status="ACTIVE",
        description=req.description.strip() if req.description else None,
        created_by=current_user.id
    )
    db.add(new_fee)
    db.flush()

    # Ghi nhận Audit Log (AC-32.1)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_FEE_TYPE",
        entity_type="FEE_TYPE",
        entity_id=str(new_fee.id),
        old_value=None,
        new_value={
            "code": new_fee.code,
            "name": new_fee.name,
            "fee_group": new_fee.fee_group,
            "calc_method": new_fee.calc_method,
            "unit_label": new_fee.unit_label,
            "vehicle_type": new_fee.vehicle_type,
            "cycle": new_fee.cycle,
            "due_day": new_fee.due_day,
            "status": new_fee.status,
        },
        reason=f"Tạo mới khoản thu '{new_fee.code}' ({new_fee.name}).",
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit)
    db.commit()
    db.refresh(new_fee)

    new_fee.current_unit_price = get_current_unit_price(db, new_fee.id)
    return FeeTypeSchema.model_validate(new_fee)


@router.get(
    "/{id}",
    response_model=FeeTypeSchema,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết khoản thu",
    description="Tra cứu chi tiết một khoản thu theo ID (US-12). Phân quyền: ADMIN, ACCOUNTANT.",
)
def get_fee_type(
    id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeTypeSchema:
    """Lấy chi tiết một khoản thu theo ID."""
    fee_type = db.get(FeeType, id)
    if not fee_type:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy khoản thu với ID {id}."
        )

    fee_type.current_unit_price = get_current_unit_price(db, fee_type.id)
    return FeeTypeSchema.model_validate(fee_type)


@router.patch(
    "/{id}",
    response_model=FeeTypeSchema,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật khoản thu",
    description="Cập nhật thông tin khoản thu (US-12). Bất biến code và calc_method theo FeeTypeUpdate schema. Phân quyền: ADMIN, ACCOUNTANT.",
)
def update_fee_type(
    id: int,
    req: FeeTypeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeTypeSchema:
    """Cập nhật thông tin khoản thu theo OpenAPI spec FeeTypeUpdate."""
    fee_type = db.get(FeeType, id)
    if not fee_type:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy khoản thu với ID {id}."
        )

    old_state: Dict[str, Any] = {
        "name": fee_type.name,
        "unit_label": fee_type.unit_label,
        "cycle": fee_type.cycle,
        "due_day": fee_type.due_day,
        "description": fee_type.description,
        "provider_id": fee_type.provider_id,
    }

    # Cập nhật các trường được phép trong FeeTypeUpdate
    if req.name is not None:
        fee_type.name = req.name.strip()
    if req.unit_label is not None:
        fee_type.unit_label = req.unit_label.strip()
    if req.provider_id is not None:
        fee_type.provider_id = req.provider_id
    if req.cycle is not None:
        fee_type.cycle = req.cycle.value
    if req.due_day is not None:
        fee_type.due_day = req.due_day
    if req.description is not None:
        fee_type.description = req.description.strip() if req.description else None

    # Ghi nhận Audit Log (AC-32.1)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    new_state: Dict[str, Any] = {
        "name": fee_type.name,
        "unit_label": fee_type.unit_label,
        "cycle": fee_type.cycle,
        "due_day": fee_type.due_day,
        "description": fee_type.description,
        "provider_id": fee_type.provider_id,
    }

    audit = AuditLog(
        user_id=current_user.id,
        action="UPDATE_FEE_TYPE",
        entity_type="FEE_TYPE",
        entity_id=str(fee_type.id),
        old_value=old_state,
        new_value=new_state,
        reason=f"Cập nhật thông tin khoản thu '{fee_type.code}'.",
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit)
    db.commit()
    db.refresh(fee_type)

    fee_type.current_unit_price = get_current_unit_price(db, fee_type.id)
    return FeeTypeSchema.model_validate(fee_type)


@router.post(
    "/{id}/deactivate",
    response_model=FeeTypeSchema,
    status_code=status.HTTP_200_OK,
    summary="Ngừng áp dụng khoản thu",
    description="Chuyển trạng thái khoản thu sang INACTIVE, cấm xóa vật lý (US-13, AC-13.1). Phân quyền: ADMIN, ACCOUNTANT.",
)
def deactivate_fee_type(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeTypeSchema:
    """Ngừng áp dụng khoản thu (chuyển sang INACTIVE, không xóa vật lý theo AC-13.1)."""
    fee_type = db.get(FeeType, id)
    if not fee_type:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy khoản thu với ID {id}."
        )

    old_status = fee_type.status
    fee_type.status = "INACTIVE"

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="DEACTIVATE_FEE",
        entity_type="FEE_TYPE",
        entity_id=str(fee_type.id),
        old_value={"status": old_status},
        new_value={"status": "INACTIVE"},
        reason=f"Ngừng áp dụng khoản thu '{fee_type.code}'.",
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit)
    db.commit()
    db.refresh(fee_type)

    fee_type.current_unit_price = get_current_unit_price(db, fee_type.id)
    return FeeTypeSchema.model_validate(fee_type)
