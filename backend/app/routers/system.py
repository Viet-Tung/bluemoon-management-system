from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.user import AuditLog, BackupJob as BackupJobModel, User
from app.schemas.system import BackupJob, BackupJobPage, BackupStatus

router = APIRouter(tags=["System"])


@router.post(
    "/backups",
    response_model=BackupJob,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Chạy sao lưu thủ công",
    description="Kích hoạt một tiến trình sao lưu CSDL thủ công chạy nền (US-45). Phân quyền: ADMIN.",
)
def create_backup(
    request: Request,
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> BackupJob:
    """
    Kích hoạt sao lưu thủ công. Trả về mã HTTP 202 Accepted với thông tin BackupJob.
    Tự động ghi nhận nhật ký thao tác kiểm toán (Audit Log).
    """
    new_job = BackupJobModel(
        status=BackupStatus.QUEUED.value,
        requested_by=current_user.id,
        requested_at=datetime.now(timezone.utc),
    )
    db.add(new_job)
    db.flush()

    # Ghi nhận Audit Log (AC-32.1 / NFR-001)
    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_BACKUP",
        entity_type="SYSTEM",
        entity_id=str(new_job.id),
        new_value={"job_id": new_job.id, "status": new_job.status},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit)
    db.commit()
    db.refresh(new_job)

    return BackupJob.model_validate(new_job)


@router.get(
    "/backups",
    response_model=BackupJobPage,
    status_code=status.HTTP_200_OK,
    summary="Lịch sử sao lưu",
    description="Truy xuất danh sách lịch sử các tác vụ sao lưu CSDL theo phân trang (US-45). Phân quyền: ADMIN.",
)
def list_backups(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi trên một trang (tối đa 100)"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Lọc theo trạng thái sao lưu"),
    current_user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> BackupJobPage:
    """
    Truy xuất lịch sử sao lưu CSDL phân trang, sắp xếp theo thời gian mới nhất.
    Chỉ dành riêng cho Ban Quản Trị (ADMIN).
    """
    filters = []
    if status_filter is not None and status_filter.strip() != "":
        valid_statuses = {s.value for s in BackupStatus}
        if status_filter.strip().upper() in valid_statuses:
            filters.append(BackupJobModel.status == status_filter.strip().upper())
        else:
            # Nếu truyền status không hợp lệ, trả về danh sách rỗng thay vì crash
            filters.append(BackupJobModel.status == status_filter.strip())

    total = db.scalar(
        select(func.count(BackupJobModel.id)).where(*filters)
    ) or 0

    offset = (page - 1) * page_size
    stmt = (
        select(BackupJobModel)
        .where(*filters)
        .order_by(BackupJobModel.requested_at.desc(), BackupJobModel.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = db.scalars(stmt).all()

    return BackupJobPage(
        items=[BackupJob.model_validate(r) for r in records],
        page=page,
        page_size=page_size,
        total=total,
    )

