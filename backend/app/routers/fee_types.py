from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select  # [SỬA] Bỏ text, thêm or_ để dùng ORM cho get_current_unit_price
from sqlalchemy.exc import IntegrityError  # [SỬA] Thêm IntegrityError để bắt lỗi xung đột đồng thời trên DB
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles, sanitize_ip_address
from app.models.fee import FeeRate, FeeType, ServiceProvider
from app.models.user import AuditLog, User
from app.schemas.fee import (
    FeeGroup,
    FeeRate as FeeRateSchema,
    FeeRateCreate,
    FeeStatus,
    FeeType as FeeTypeSchema,
    FeeTypeCreate,
    FeeTypePage,
    FeeTypeUpdate,
)

router = APIRouter(tags=["Fee catalog"])


# [SỬA] Chuyển từ raw SQL (text) sang SQLAlchemy ORM cho đồng bộ với model FeeRate
def get_current_unit_price(db: Session, fee_type_id: int) -> Optional[int]:
    """Tra cứu đơn giá đang có hiệu lực trong ngày hiện tại."""
    today = date.today()
    stmt = (
        select(FeeRate.unit_price)
        .where(
            FeeRate.fee_type_id == fee_type_id,
            FeeRate.effective_from <= today,
            or_(FeeRate.effective_to.is_(None), FeeRate.effective_to >= today),
        )
        .order_by(FeeRate.effective_from.desc(), FeeRate.id.desc())
        .limit(1)
    )
    val = db.scalar(stmt)
    return int(val) if val is not None else None


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

    if req.provider_id is not None:
        provider = db.get(ServiceProvider, req.provider_id)
        if not provider:
            raise AppAPIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="VALIDATION_ERROR",
                message=f"Nhà cung cấp dịch vụ ID {req.provider_id} không tồn tại.",
                details=[{"field": "provider_id", "message": f"Không tìm thấy provider_id={req.provider_id}."}],
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
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_FEE_CODE",
            message=f"Mã khoản thu '{clean_code}' đã tồn tại hoặc tham chiếu không hợp lệ."
        )

    # Ghi nhận Audit Log (AC-32.1)
    client_ip = sanitize_ip_address(request.client.host if request.client else None)
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
    "/{id:int}",
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
    "/{id:int}",
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

    if req.name is not None:
        fee_type.name = req.name.strip()
    if req.unit_label is not None:
        fee_type.unit_label = req.unit_label.strip()
    if req.provider_id is not None:
        provider = db.get(ServiceProvider, req.provider_id)
        if not provider:
            raise AppAPIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="VALIDATION_ERROR",
                message=f"Nhà cung cấp dịch vụ ID {req.provider_id} không tồn tại.",
                details=[{"field": "provider_id", "message": f"Không tìm thấy provider_id={req.provider_id}."}],
            )
        fee_type.provider_id = req.provider_id
    if req.cycle is not None:
        fee_type.cycle = req.cycle.value
    if req.due_day is not None:
        fee_type.due_day = req.due_day
    if req.description is not None:
        fee_type.description = req.description.strip() if req.description else None

    client_ip = sanitize_ip_address(request.client.host if request.client else None)
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
    "/{id:int}/deactivate",
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

    client_ip = sanitize_ip_address(request.client.host if request.client else None)
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


@router.get(
    "/{id:int}/rates",
    response_model=List[FeeRateSchema],
    status_code=status.HTTP_200_OK,
    summary="Lịch sử đơn giá của khoản thu",
    description="Lấy danh sách lịch sử đơn giá theo ngày hiệu lực của khoản thu (US-14). Phân quyền: ADMIN, ACCOUNTANT.",
)
def list_fee_rates(
    id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> List[FeeRateSchema]:
    """Lấy danh sách toàn bộ lịch sử đơn giá của khoản thu, sắp xếp theo ngày hiệu lực giảm dần."""
    fee_type = db.get(FeeType, id)
    if not fee_type:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy khoản thu với ID {id}."
        )

    stmt = (
        select(FeeRate)
        .where(FeeRate.fee_type_id == id)
        .order_by(FeeRate.effective_from.desc(), FeeRate.id.desc())
    )
    rates = db.scalars(stmt).all()
    return [FeeRateSchema.model_validate(r) for r in rates]


@router.post(
    "/{id:int}/rates",
    response_model=FeeRateSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Cập nhật đơn giá mới",
    description="Cập nhật đơn giá mới kèm ngày bắt đầu hiệu lực (US-14). Tự động khép đơn giá đang áp dụng trước đó vào ngày trước ngày hiệu lực mới. Phân quyền: ADMIN, ACCOUNTANT.",
)
def create_fee_rate(
    id: int,
    req: FeeRateCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeRateSchema:
    """
    Cập nhật đơn giá mới cho khoản thu (US-14, AC-14.1):
    - Kiểm tra xung đột ngày hiệu lực (RATE_OVERLAP, HTTP 409).
    - Đơn giá đang áp dụng (effective_to IS NULL) được tự khép lại vào ngày trước req.effective_from.
    - Ghi nhận Audit Log (action=CREATE_FEE_RATE).
    """
    fee_type = db.get(FeeType, id)
    if not fee_type:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy khoản thu với ID {id}."
        )

    if req.unit_price < 0:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Đơn giá phải là số nguyên không âm (>= 0).",
            details=[{"field": "unit_price", "message": "Đơn giá phải lớn hơn hoặc bằng 0."}]
        )

    # Lấy tất cả các đơn giá hiện có của khoản thu này
    existing_rates = db.scalars(
        select(FeeRate)
        .where(FeeRate.fee_type_id == id)
        .order_by(FeeRate.effective_from.asc())
    ).all()

    active_rate = next((r for r in existing_rates if r.effective_to is None), None)

    # [SỬA] Đẩy toàn bộ bước kiểm tra xung đột lên TRƯỚC khi thay đổi dữ liệu trong session
    if active_rate and req.effective_from <= active_rate.effective_from:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="RATE_OVERLAP",
            message=f"Ngày bắt đầu hiệu lực ({req.effective_from}) phải sau ngày bắt đầu của đơn giá hiện tại ({active_rate.effective_from}).",
            details=[{
                "field": "effective_from",
                "message": f"Xung đột với đơn giá đang áp dụng từ {active_rate.effective_from}."
            }]
        )

    for r in existing_rates:
        if r is active_rate:
            continue
        if r.effective_to is not None and r.effective_from <= req.effective_from <= r.effective_to:
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="RATE_OVERLAP",
                message=f"Ngày hiệu lực ({req.effective_from}) bị chồng lấn với đơn giá từ {r.effective_from} đến {r.effective_to}.",
                details=[{
                    "field": "effective_from",
                    "message": f"Nằm trong khoảng [{r.effective_from}, {r.effective_to}]."
                }]
            )
        if r.effective_from >= req.effective_from:
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="RATE_OVERLAP",
                message=f"Ngày hiệu lực ({req.effective_from}) bị chồng lấn với đơn giá hiệu lực từ {r.effective_from}.",
                details=[{
                    "field": "effective_from",
                    "message": f"Đơn giá ID {r.id} đã bắt đầu từ {r.effective_from}."
                }]
            )

    # [SỬA] Bọc transaction trong try/except IntegrityError và thêm db.flush() sau khi khép đơn giá cũ
    try:
        old_state = None
        if active_rate:
            old_state = {
                "rate_id": active_rate.id,
                "unit_price": int(active_rate.unit_price),
                "effective_from": str(active_rate.effective_from),
                "effective_to": None,
            }
            active_rate.effective_to = req.effective_from - timedelta(days=1)
            db.flush()  # [SỬA] Ép chạy UPDATE trước INSERT để không vướng EXCLUDE USING gist trên PostgreSQL

        new_rate = FeeRate(
            fee_type_id=id,
            unit_price=req.unit_price,
            effective_from=req.effective_from,
            effective_to=None,
            created_by=current_user.id,
        )
        db.add(new_rate)
        db.flush()

        # Ghi nhận Audit Log (AC-14.1, US-32)
        client_ip = sanitize_ip_address(request.client.host if request.client else None)
        user_agent = request.headers.get("user-agent")
        new_state = {
            "rate_id": new_rate.id,
            "fee_type_id": id,
            "fee_type_code": fee_type.code,
            "unit_price": req.unit_price,
            "effective_from": str(req.effective_from),
            "effective_to": None,
        }

        audit = AuditLog(
            user_id=current_user.id,
            action="CREATE_FEE_RATE",
            entity_type="FEE_RATE",
            entity_id=str(new_rate.id),
            old_value=old_state,
            new_value=new_state,
            reason=f"Cập nhật đơn giá mới {req.unit_price:,} VNĐ cho khoản thu '{fee_type.code}' có hiệu lực từ {req.effective_from} (tự động khép đơn giá cũ).",
            ip_address=client_ip,
            user_agent=user_agent,
        )
        db.add(audit)
        db.commit()
        db.refresh(new_rate)

        return FeeRateSchema.model_validate(new_rate)

    except IntegrityError:
        db.rollback()
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="RATE_OVERLAP",
            message="Xung đột khoảng thời gian hiệu lực đơn giá trên cơ sở dữ liệu.",
        )