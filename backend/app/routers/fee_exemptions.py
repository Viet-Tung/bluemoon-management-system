from datetime import date  # [SỬA] Bỏ import thừa math, thêm date để kiểm tra chồng chéo ngày và tra đơn giá
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select  # [SỬA] Thêm or_ cho điều kiện kiểm tra khoảng thời gian chồng lấn
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.fee import FeeExemption, FeeRate, FeeType  # [SỬA] Import thêm FeeRate để kiểm tra phí gốc (AC-15.1)
from app.models.property import Household
from app.models.user import AuditLog, User
from app.schemas.fee import (
    DiscountType,  # [SỬA] Import thêm DiscountType để kiểm tra nhánh AMOUNT
    ExemptionCreate,
    ExemptionStatus,
    FeeExemption as FeeExemptionSchema,
    FeeExemptionPage,
)

router = APIRouter(tags=["Fee catalog"])


@router.get(
    "",
    response_model=FeeExemptionPage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách chính sách miễn giảm",
    description="Tra cứu danh sách chính sách miễn giảm có phân trang và bộ lọc theo hộ, khoản thu, trạng thái (US-15). Phân quyền: ADMIN, ACCOUNTANT.",
    operation_id="listExemptions",
)
def list_exemptions(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Kích thước trang (1-100)"),
    household_id: Optional[int] = Query(default=None, description="Lọc theo ID hộ gia đình"),
    fee_type_id: Optional[int] = Query(default=None, description="Lọc theo ID khoản thu"),
    status_filter: Optional[ExemptionStatus] = Query(default=None, alias="status", description="Lọc theo trạng thái (ACTIVE, REVOKED)"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeExemptionPage:
    """Tra cứu danh sách chính sách miễn giảm phí có phân trang và bộ lọc."""
    stmt = select(FeeExemption)

    if household_id is not None:
        stmt = stmt.where(FeeExemption.household_id == household_id)

    if fee_type_id is not None:
        stmt = stmt.where(FeeExemption.fee_type_id == fee_type_id)

    if status_filter is not None:
        stmt = stmt.where(FeeExemption.status == status_filter.value)

    # Đếm tổng số bản ghi
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    # Phân trang và sắp xếp giảm dần theo ID
    offset = (page - 1) * page_size
    items = db.scalars(
        stmt.order_by(FeeExemption.id.desc()).offset(offset).limit(page_size)
    ).all()

    # [SỬA] Truyền đúng các trường của PageMeta (page, page_size, total) giống FeeTypePage để tránh lỗi ValidationError nếu PageMeta cấm extra fields
    return FeeExemptionPage(
        page=page,
        page_size=page_size,
        total=total,
        items=[FeeExemptionSchema.model_validate(x) for x in items],
    )


@router.post(
    "",
    response_model=FeeExemptionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo chính sách miễn giảm",
    description="Tạo chính sách miễn giảm phí cho hộ gia đình (US-15). approved_by tự động lấy từ token của người tạo. Phân quyền: ADMIN, ACCOUNTANT.",
    operation_id="createExemption",
)
def create_exemption(
    req: ExemptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeExemptionSchema:
    """Tạo mới chính sách miễn giảm theo hộ + khoản thu + thời hạn (US-15)."""
    # 1. Kiểm tra tồn tại của Hộ gia đình
    household = db.get(Household, req.household_id)
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình với ID {req.household_id}.",
            details=[{"field": "household_id", "message": f"Hộ gia đình ID {req.household_id} không tồn tại."}],
        )

    # 2. Kiểm tra tồn tại của Khoản thu
    fee_type = db.get(FeeType, req.fee_type_id)
    if not fee_type:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy khoản thu với ID {req.fee_type_id}.",
            details=[{"field": "fee_type_id", "message": f"Khoản thu ID {req.fee_type_id} không tồn tại."}],
        )

    # [SỬA] 2a. Không cho phép tạo chính sách miễn giảm cho khoản thu đã ngừng áp dụng (INACTIVE)
    if fee_type.status != "ACTIVE":
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=f"Khoản thu '{fee_type.code}' đã ngừng áp dụng, không thể tạo chính sách miễn giảm.",
            details=[{"field": "fee_type_id", "message": "Khoản thu đang ở trạng thái INACTIVE."}],
        )

    # [SỬA] 2b. Kiểm tra AC-15.1: Với khoản thu cố định theo hộ (PER_HOUSEHOLD), số tiền giảm không được vượt quá đơn giá gốc
    if fee_type.calc_method == "PER_HOUSEHOLD" and req.discount_type == DiscountType.AMOUNT:
        rate_stmt = (
            select(FeeRate)
            .where(
                FeeRate.fee_type_id == req.fee_type_id,
                FeeRate.effective_from <= req.valid_from,
                or_(FeeRate.effective_to.is_(None), FeeRate.effective_to >= req.valid_from),
            )
            .order_by(FeeRate.effective_from.desc(), FeeRate.id.desc())
            .limit(1)
        )
        applicable_rate = db.scalar(rate_stmt)
        if applicable_rate is not None and req.discount_value > float(applicable_rate.unit_price):
            raise AppAPIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="VALIDATION_ERROR",
                message=f"Số tiền miễn giảm ({int(req.discount_value):,} VNĐ) không được vượt quá đơn giá gốc ({int(applicable_rate.unit_price):,} VNĐ).",
                details=[{"field": "discount_value", "message": "Số tiền miễn giảm vượt quá mức phí gốc của khoản thu."}],
            )

    # [SỬA] 2c. Chặn chồng chéo thời gian hiệu lực với chính sách đang ACTIVE của cùng hộ + khoản thu
    overlap_stmt = select(FeeExemption).where(
        FeeExemption.household_id == req.household_id,
        FeeExemption.fee_type_id == req.fee_type_id,
        FeeExemption.status == "ACTIVE",
        FeeExemption.valid_from <= (req.valid_to or date.max),
        or_(FeeExemption.valid_to.is_(None), FeeExemption.valid_to >= req.valid_from),
    )
    if db.scalar(overlap_stmt):
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="EXEMPTION_OVERLAP",
            message="Hộ gia đình đã có chính sách miễn giảm đang hiệu lực cho khoản thu này trong khoảng thời gian đã chọn.",
            details=[{"field": "valid_from", "message": "Khoảng thời gian hiệu lực bị chồng lấn với chính sách hiện có."}],
        )

    # 3. Tạo bản ghi FeeExemption
    exemption = FeeExemption(
        household_id=req.household_id,
        fee_type_id=req.fee_type_id,
        discount_type=req.discount_type.value,
        discount_value=req.discount_value,
        reason=req.reason,
        decision_no=req.decision_no,
        approved_by=current_user.id,  # AC-16.1: approved_by lấy từ token người tạo
        valid_from=req.valid_from,
        valid_to=req.valid_to,
        status="ACTIVE",
    )
    db.add(exemption)
    db.flush()

    # 4. Ghi nhận Audit Log (AC-16.1, US-32)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    new_state: Dict[str, Any] = {
        "id": exemption.id,
        "household_id": req.household_id,
        "household_code": household.household_code,
        "fee_type_id": req.fee_type_id,
        "fee_type_code": fee_type.code,
        "discount_type": req.discount_type.value,
        "discount_value": req.discount_value,
        "reason": req.reason,
        "decision_no": req.decision_no,
        "approved_by": current_user.id,
        "valid_from": str(req.valid_from),
        "valid_to": str(req.valid_to) if req.valid_to else None,
        "status": "ACTIVE",
    }

    audit = AuditLog(
        user_id=current_user.id,
        action="CREATE_EXEMPTION",
        entity_type="FEE_EXEMPTION",
        entity_id=str(exemption.id),
        old_value=None,
        new_value=new_state,
        reason=f"Tạo chính sách miễn giảm cho hộ '{household.household_code}' đối với khoản thu '{fee_type.code}': giảm {req.discount_value} ({req.discount_type.value}).",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(exemption)

    return FeeExemptionSchema.model_validate(exemption)


@router.post(
    "/{id:int}/revoke",
    response_model=FeeExemptionSchema,
    status_code=status.HTTP_200_OK,
    summary="Thu hồi chính sách miễn giảm",
    description="Thu hồi chính sách miễn giảm đã phê duyệt trước đó (US-16). Trả về 409 ALREADY_REVOKED nếu đã bị thu hồi. Phân quyền: ADMIN, ACCOUNTANT.",
    operation_id="revokeExemption",
)
def revoke_exemption(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> FeeExemptionSchema:
    """Thu hồi chính sách miễn giảm phí (US-16)."""
    exemption = db.get(FeeExemption, id)
    if not exemption:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy chính sách miễn giảm với ID {id}."
        )

    # Kiểm tra nếu đã bị thu hồi trước đó -> 409 ALREADY_REVOKED
    if exemption.status == "REVOKED":
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="ALREADY_REVOKED",
            message=f"Chính sách miễn giảm với ID {id} đã bị thu hồi trước đó.",
            details=[{"field": "status", "message": "Chính sách đang ở trạng thái REVOKED."}],
        )

    old_status = exemption.status
    exemption.status = "REVOKED"

    # Ghi nhận Audit Log (AC-16.1, US-32)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    audit = AuditLog(
        user_id=current_user.id,
        action="REVOKE_EXEMPTION",
        entity_type="FEE_EXEMPTION",
        entity_id=str(exemption.id),
        old_value={"status": old_status},
        new_value={"status": "REVOKED"},
        reason=f"Thu hồi chính sách miễn giảm ID {exemption.id} của hộ ID {exemption.household_id} đối với khoản thu ID {exemption.fee_type_id}.",
        ip_address=client_ip,
        user_agent=user_agent,
    )
    db.add(audit)
    db.commit()
    db.refresh(exemption)

    return FeeExemptionSchema.model_validate(exemption)
    # [SỬA] Đã xóa toàn bộ đoạn thân hàm revoke_exemption bị dán lặp lại phía dưới dòng return này