from datetime import date, datetime, time
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.user import AuditLog, User
from app.schemas.audit_log import AuditLogPage, AuditLogResponse

router = APIRouter(tags=["System"])


@router.get(
    "",
    response_model=AuditLogPage,
    status_code=status.HTTP_200_OK,
    summary="Xem và lọc nhật ký thao tác",
    description="Truy xuất và lọc lịch sử kiểm toán bất biến các thao tác nhạy cảm trong hệ thống (US-32). Phân quyền: ADMIN.",
)
def list_audit_logs(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi trên một trang (tối đa 100)"),
    user_id: Optional[int] = Query(default=None, description="Lọc theo ID người dùng thực hiện thao tác"),
    action: Optional[str] = Query(default=None, description="Lọc theo mã hành động (ví dụ: CHANGE_ROLE, LOCK_USER)"),
    entity_type: Optional[str] = Query(default=None, description="Lọc theo loại thực thể (ví dụ: USER, HOUSEHOLD)"),
    from_date: Optional[date] = Query(default=None, alias="from", description="Lọc từ ngày (định dạng YYYY-MM-DD)"),
    to_date: Optional[date] = Query(default=None, alias="to", description="Lọc đến ngày (định dạng YYYY-MM-DD)"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    """
    Truy xuất danh sách nhật ký kiểm toán với các bộ lọc linh hoạt (US-32 / AC-32.1).
    Chỉ dành riêng cho Ban Quản Trị (ADMIN).
    """
    # Kiểm tra tính hợp lệ của khoảng thời gian
    if from_date is not None and to_date is not None and from_date > to_date:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Khoảng thời gian không hợp lệ: 'from' không được lớn hơn 'to'.",
            details=[
                {
                    "field": "from",
                    "message": f"Ngày bắt đầu '{from_date}' lớn hơn ngày kết thúc '{to_date}'."
                }
            ],
        )

    filters = []

    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)

    if action is not None and action.strip() != "":
        filters.append(AuditLog.action == action.strip())

    if entity_type is not None and entity_type.strip() != "":
        filters.append(AuditLog.entity_type == entity_type.strip())

    if from_date is not None:
        start_dt = datetime.combine(from_date, time.min)
        filters.append(AuditLog.created_at >= start_dt)

    if to_date is not None:
        end_dt = datetime.combine(to_date, time.max)
        filters.append(AuditLog.created_at <= end_dt)

    # Đếm tổng số bản ghi thỏa mãn điều kiện lọc
    total = db.scalar(
        select(func.count(AuditLog.id)).where(*filters)
    ) or 0

    # Phân trang và sắp xếp giảm dần theo thời gian (mới nhất lên đầu)
    offset = (page - 1) * page_size
    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = db.scalars(stmt).all()

    return AuditLogPage(
        items=[AuditLogResponse.model_validate(r) for r in records],
        page=page,
        page_size=page_size,
        total=total,
    )

