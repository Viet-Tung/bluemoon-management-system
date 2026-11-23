from datetime import date
from typing import Any, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.property import Household, Resident
from app.models.user import AuditLog, User
from app.schemas.resident import (
    ResidentCreate,
    ResidentPage,
    ResidentResponse,
    ResidentUpdate,
)

router = APIRouter(tags=["Residents"])


def calculate_age(dob: date) -> int:
    """Tính tuổi chính xác theo ngày sinh so với ngày hiện tại."""
    today = date.today()
    return today.year - dob.year - (
        (today.month, today.day) < (dob.month, dob.day)
    )


def _validate_dob(dob: date) -> None:
    if dob > date.today():
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Ngày sinh không được lớn hơn ngày hiện tại.",
            details=[{"field": "date_of_birth", "message": "Ngày sinh không hợp lệ (nằm ở tương lai)."}],
        )


def _clean_full_name(full_name: str) -> str:
    cleaned = full_name.strip()
    if not cleaned:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Họ và tên không được để trống hoặc chỉ chứa khoảng trắng.",
            details=[{"field": "full_name", "message": "Không được chỉ chứa khoảng trắng."}],
        )
    return cleaned


def _create_audit_log(
    db: Session,
    request: Request,
    user_id: int,
    action: str,
    entity_id: int,
    old_value: Optional[dict[str, Any]],
    new_value: Optional[dict[str, Any]],
    reason: str,
) -> None:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type="RESIDENT",
            entity_id=str(entity_id),
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            ip_address=client_ip,
            user_agent=user_agent,
        )
    )


# =====================================================================
# US-06: GET /households/{id}/residents — Danh sách nhân khẩu trong hộ
# =====================================================================
@router.get(
    "/households/{household_id:int}/residents",
    response_model=ResidentPage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách nhân khẩu trong hộ",
    description="Lấy danh sách nhân khẩu trong một hộ gia đình (US-06). Phân quyền: ADMIN, ACCOUNTANT.",
)
def list_household_residents(
    household_id: int,
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Số bản ghi mỗi trang (1-100)"),
    residence_status: Optional[str] = Query(default=None, description="Lọc theo trạng thái cư trú"),
    include_deleted: bool = Query(default=False, description="Bao gồm cả nhân khẩu đã xóa logic (chỉ ADMIN)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> ResidentPage:
    # 1. Kiểm tra hộ gia đình tồn tại
    household = db.scalar(select(Household).where(Household.id == household_id))
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình có ID {household_id}.",
        )

    # 2. Xây dựng truy vấn
    query = select(Resident).where(Resident.household_id == household_id)

    # Chỉ ADMIN mới được xem bản ghi đã xóa nếu include_deleted=True
    if not include_deleted or current_user.role.code != "ADMIN":
        query = query.where(Resident.is_deleted.is_(False))

    if residence_status:
        status_clean = residence_status.strip().upper()
        query = query.where(Resident.residence_status == status_clean)

    # 3. Đếm tổng số bản ghi
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0

    # 4. Phân trang: Chủ hộ lên đầu, sau đó sắp xếp theo ID tăng dần
    residents = db.scalars(
        query.order_by(Resident.is_head.desc(), Resident.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return ResidentPage(
        items=[ResidentResponse.model_validate(r) for r in residents],
        page=page,
        page_size=page_size,
        total=total,
    )


# =====================================================================
# US-05: POST /households/{id}/residents — Thêm nhân khẩu mới
# =====================================================================
@router.post(
    "/households/{household_id:int}/residents",
    response_model=ResidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm nhân khẩu mới",
    description="Thêm mới một nhân khẩu vào hộ gia đình (US-05). Phân quyền: ADMIN.",
)
def create_resident(
    household_id: int,
    req: ResidentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> ResidentResponse:
    # 1. Kiểm tra hộ gia đình tồn tại
    household = db.scalar(select(Household).where(Household.id == household_id))
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình có ID {household_id}.",
        )

    full_name_clean = _clean_full_name(req.full_name)
    _validate_dob(req.date_of_birth)

    # 2. Tính tuổi và kiểm tra ràng buộc CCCD (AC-05.2, AC-05.3)
    age = calculate_age(req.date_of_birth)
    cccd_clean = req.cccd

    # Nhân khẩu từ 14 tuổi trở lên bắt buộc phải có CCCD
    if age >= 14 and not cccd_clean:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Nhân khẩu từ 14 tuổi trở lên bắt buộc phải có số CCCD/CMND.",
            details=[{"field": "cccd", "message": "Bắt buộc đối với nhân khẩu từ 14 tuổi trở lên."}],
        )

    # Kiểm tra trùng lặp CCCD trên toàn hệ thống với các nhân khẩu đang hoạt động
    if cccd_clean:
        existing_cccd = db.scalar(
            select(Resident).where(
                Resident.cccd == cccd_clean,
                Resident.is_deleted.is_(False),
            )
        )
        if existing_cccd:
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_CCCD",
                message=f"Số CCCD/CMND '{cccd_clean}' đã tồn tại trên hệ thống (thuộc nhân khẩu '{existing_cccd.full_name}').",
            )

    # 3. Kiểm tra ràng buộc Chủ hộ duy nhất (AC-05.1)
    if req.is_head:
        existing_head = db.scalar(
            select(Resident).where(
                Resident.household_id == household_id,
                Resident.is_head.is_(True),
                Resident.is_deleted.is_(False),
            )
        )
        if existing_head:
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="HEAD_ALREADY_EXISTS",
                message=f"Hộ gia đình đã có chủ hộ đang hoạt động là '{existing_head.full_name}'. Vui lòng sử dụng chức năng đổi chủ hộ nếu muốn thay thế.",
            )

    # 4. Xác định quan hệ với chủ hộ mặc định
    rel = req.relationship_to_head.strip() if req.relationship_to_head and req.relationship_to_head.strip() else (
        "CHỦ HỘ" if req.is_head else "THÀNH VIÊN"
    )

    new_resident = Resident(
        household_id=household_id,
        full_name=full_name_clean,  
        date_of_birth=req.date_of_birth,
        gender=req.gender.strip().upper(),
        cccd=cccd_clean,
        phone=req.phone.strip() if req.phone and req.phone.strip() else None,
        email=req.email.strip() if req.email and req.email.strip() else None,
        relationship_to_head=rel,
        is_head=req.is_head,
        residence_status="THUONG_TRU",
        status_effective_date=date.today(),
        is_deleted=False,
    )
    db.add(new_resident)
    db.flush()

    # 5. Ghi Audit Log (US-32)
    _create_audit_log(
        db=db,
        request=request,
        user_id=current_user.id,
        action="CREATE_RESIDENT",
        entity_id=new_resident.id,
        old_value=None,
        new_value={
            "id": new_resident.id,
            "household_id": household_id,
            "full_name": new_resident.full_name,
            "date_of_birth": new_resident.date_of_birth.isoformat(),
            "gender": new_resident.gender,
            "cccd": new_resident.cccd,
            "is_head": new_resident.is_head,
        },
        reason=f"Thêm nhân khẩu '{new_resident.full_name}' vào hộ ID {household_id}.",
    )
    db.commit()
    db.refresh(new_resident)

    return ResidentResponse.model_validate(new_resident)


# =====================================================================
# US-06: GET /residents/{id} — Chi tiết nhân khẩu
# =====================================================================
@router.get(
    "/residents/{resident_id:int}",
    response_model=ResidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết nhân khẩu",
    description="Tra cứu thông tin chi tiết một nhân khẩu (US-06). Phân quyền: ADMIN, ACCOUNTANT.",
)
def get_resident(
    resident_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> ResidentResponse:
    resident = db.scalar(
        select(Resident).where(
            Resident.id == resident_id,
            Resident.is_deleted.is_(False),
        )
    )
    if not resident:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy thông tin nhân khẩu có ID {resident_id}.",
        )

    return ResidentResponse.model_validate(resident)


# =====================================================================
# US-06: PATCH /residents/{id} — Cập nhật nhân khẩu
# =====================================================================
@router.patch(
    "/residents/{resident_id:int}",
    response_model=ResidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật nhân khẩu",
    description="Cập nhật thông tin nhân khẩu (US-06). Phân quyền: ADMIN.",
)
def update_resident(
    resident_id: int,
    req: ResidentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> ResidentResponse:
    resident = db.scalar(
        select(Resident).where(
            Resident.id == resident_id,
            Resident.is_deleted.is_(False),
        )
    )
    if not resident:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy thông tin nhân khẩu có ID {resident_id}.",
        )

    fields_set = req.model_fields_set

    new_full_name = None
    if "full_name" in fields_set and req.full_name is not None:
        new_full_name = _clean_full_name(req.full_name)

    target_dob = req.date_of_birth if ("date_of_birth" in fields_set and req.date_of_birth is not None) else resident.date_of_birth
    if "date_of_birth" in fields_set and req.date_of_birth is not None:
        _validate_dob(req.date_of_birth)

    target_cccd_clean = req.cccd if "cccd" in fields_set else resident.cccd

    # Kiểm tra tuổi & CCCD bắt buộc
    age = calculate_age(target_dob)
    if age >= 14 and not target_cccd_clean:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Nhân khẩu từ 14 tuổi trở lên bắt buộc phải có số CCCD/CMND.",
            details=[{"field": "cccd", "message": "Bắt buộc đối với nhân khẩu từ 14 tuổi trở lên."}],
        )

    # Kiểm tra trùng CCCD nếu có thay đổi CCCD
    if target_cccd_clean and target_cccd_clean != resident.cccd:
        existing_cccd = db.scalar(
            select(Resident).where(
                Resident.cccd == target_cccd_clean,
                Resident.id != resident.id,
                Resident.is_deleted.is_(False),
            )
        )
        if existing_cccd:
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_CCCD",
                message=f"Số CCCD/CMND '{target_cccd_clean}' đã tồn tại trên hệ thống (thuộc nhân khẩu '{existing_cccd.full_name}').",
            )

    old_val = {
        "full_name": resident.full_name,
        "date_of_birth": resident.date_of_birth.isoformat() if resident.date_of_birth else None,
        "gender": resident.gender,
        "cccd": resident.cccd,
        "phone": resident.phone,
        "email": resident.email,
        "relationship_to_head": resident.relationship_to_head,
    }

    if new_full_name is not None:
        resident.full_name = new_full_name
    if "date_of_birth" in fields_set and req.date_of_birth is not None:
        resident.date_of_birth = req.date_of_birth
    if "gender" in fields_set and req.gender is not None:
        resident.gender = req.gender.strip().upper()
    if "cccd" in fields_set:
        resident.cccd = target_cccd_clean
    if "phone" in fields_set:
        resident.phone = req.phone.strip() if req.phone and req.phone.strip() else None
    if "email" in fields_set:
        resident.email = req.email.strip() if req.email and req.email.strip() else None
    if "relationship_to_head" in fields_set:
        resident.relationship_to_head = (
            req.relationship_to_head.strip()
            if req.relationship_to_head and req.relationship_to_head.strip()
            else None
        )

    # Ghi Audit Log (US-32)
    _create_audit_log(
        db=db,
        request=request,
        user_id=current_user.id,
        action="UPDATE_RESIDENT",
        entity_id=resident.id,
        old_value=old_val,
        new_value={
            "full_name": resident.full_name,
            "date_of_birth": resident.date_of_birth.isoformat() if resident.date_of_birth else None,
            "gender": resident.gender,
            "cccd": resident.cccd,
            "phone": resident.phone,
            "email": resident.email,
            "relationship_to_head": resident.relationship_to_head,
        },
        reason=f"Cập nhật thông tin nhân khẩu '{resident.full_name}'.",
    )
    db.commit()
    db.refresh(resident)

    return ResidentResponse.model_validate(resident)


# =====================================================================
# US-06: DELETE /residents/{id} — Xóa logic nhân khẩu
# =====================================================================
@router.delete(
    "/residents/{resident_id:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa logic nhân khẩu",
    description="Xóa mềm nhân khẩu khỏi hệ thống (US-06, AC-06.1). Chặn xóa nếu là chủ hộ của hộ đang hoạt động. Phân quyền: ADMIN.",
)
def delete_resident(
    resident_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
):
    resident = db.scalar(
        select(Resident).where(
            Resident.id == resident_id,
            Resident.is_deleted.is_(False),
        )
    )
    if not resident:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy thông tin nhân khẩu có ID {resident_id}.",
        )

    # AC-06.1: Chặn xóa Chủ hộ khi hộ vẫn đang hoạt động
    if resident.is_head:
        household = db.scalar(select(Household).where(Household.id == resident.household_id))
        if household and household.status == "ACTIVE":
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="CANNOT_DELETE_HEAD",
                message=f"Không thể xóa nhân khẩu '{resident.full_name}' vì đang là Chủ hộ của một hộ gia đình đang hoạt động. Vui lòng chỉ định Chủ hộ mới trước khi xóa.",
            )

    # Xóa logic (Soft delete)
    resident.is_deleted = True
    resident.deleted_at = func.now()
    resident.deleted_by = current_user.id
    resident.delete_reason = "Xóa logic bởi quản trị viên"

    # Ghi Audit Log (US-32)
    _create_audit_log(
        db=db,
        request=request,
        user_id=current_user.id,
        action="DELETE_RESIDENT",
        entity_id=resident.id,
        old_value={
            "id": resident.id,
            "household_id": resident.household_id,
            "full_name": resident.full_name,
            "is_head": resident.is_head,
            "cccd": resident.cccd,
        },
        new_value={"is_deleted": True},
        reason=f"Xóa logic nhân khẩu '{resident.full_name}' khỏi hộ ID {resident.household_id}.",
    )
    db.commit()

    return None