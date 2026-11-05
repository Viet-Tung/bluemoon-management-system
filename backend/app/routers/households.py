from datetime import date
import re
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.core.security import generate_secure_temporary_password, get_password_hash
from app.models.property import Apartment, ApartmentOccupancy, Household, Resident
from app.models.user import AuditLog, Role, User
from app.schemas.household import (
    Household as HouseholdSchema,
    HouseholdChangeHead,
    HouseholdTransferRequest,
    HouseholdCreate,
    HouseholdCreated,
    HouseholdDeactivate,
    HouseholdPage,
    HouseholdUpdate,
    ResidentAccount,
)

router = APIRouter(tags=["Households"])


def build_household_schema(db: Session, household: Household) -> HouseholdSchema:
    """Tập hợp dữ liệu từ apartment_occupancies, apartments và residents để tạo HouseholdSchema hoàn chỉnh."""
    # 1. Tìm căn hộ hiện tại đang cư trú (end_date IS NULL)
    occupancy_stmt = (
        select(ApartmentOccupancy, Apartment)
        .join(Apartment, Apartment.id == ApartmentOccupancy.apartment_id)
        .where(
            ApartmentOccupancy.household_id == household.id,
            ApartmentOccupancy.end_date.is_(None)
        )
    )
    occ_row = db.execute(occupancy_stmt).first()
    apt_id = None
    apt_code = None
    apt_floor = None
    apt_area = None
    if occ_row:
        _occ, apt = occ_row
        apt_id = apt.id
        apt_code = apt.code
        apt_floor = apt.floor
        apt_area = float(apt.area_m2) if apt.area_m2 is not None else None

    # 2. Tìm thông tin chủ hộ hiện tại
    head_stmt = (
        select(Resident)
        .where(
            Resident.household_id == household.id,
            Resident.is_head.is_(True),
            Resident.is_deleted.is_(False),
            Resident.residence_status.in_(["THUONG_TRU", "TAM_VANG"])
        )
    )
    head_resident = db.scalar(head_stmt)
    head_id = head_resident.id if head_resident else None
    head_name = head_resident.full_name if head_resident else None
    head_phone = head_resident.phone if head_resident else None

    # 3. Đếm số lượng nhân khẩu đang thường trú hoặc tạm vắng
    member_stmt = (
        select(func.count(Resident.id))
        .where(
            Resident.household_id == household.id,
            Resident.is_deleted.is_(False),
            Resident.residence_status.in_(["THUONG_TRU", "TAM_VANG"])
        )
    )
    member_count = db.scalar(member_stmt) or 0

    return HouseholdSchema(
        id=household.id,
        household_code=household.household_code,
        status=household.status,
        contact_phone=household.contact_phone,
        contact_email=household.contact_email,
        note=household.note,
        apartment_id=apt_id,
        apartment_code=apt_code,
        floor=apt_floor,
        area_m2=apt_area,
        head_resident_id=head_id,
        head_name=head_name,
        head_phone=head_phone,
        member_count=member_count,
        created_at=household.created_at,
        updated_at=household.updated_at
    )


def check_household_has_debt(db: Session, household_id: int) -> bool:
    """
    Kiểm tra hộ gia đình có công nợ chưa tất toán không (AC-02.1, DEBT_NOT_SETTLED).
    Kiểm tra linh hoạt bảng invoices hoặc v_household_debt nếu đã khởi tạo.
    """
    try:
        from sqlalchemy import text
        res = db.execute(
            text(
                "SELECT 1 FROM invoices "
                "WHERE household_id = :hid "
                "AND (status IN ('UNPAID', 'PARTIALLY_PAID', 'OVERDUE') "
                "     OR (total_due IS NOT NULL AND paid_amount IS NOT NULL AND total_due > paid_amount)) "
                "LIMIT 1"
            ),
            {"hid": household_id}
        ).first()
        if res is not None:
            return True
    except Exception:
        # Bảng invoices chưa tồn tại trong schema Sprint 1 (Minimal Cluster)
        pass

    return False


@router.get(
    "",
    response_model=HouseholdPage,
    status_code=status.HTTP_200_OK,
    summary="Danh sách hộ gia đình",
    description="Tra cứu và lọc danh sách hộ gia đình theo mã hộ, tên chủ hộ, SĐT và trạng thái (US-01). Phân quyền: ADMIN, ACCOUNTANT.",
)
def list_households(
    page: int = Query(default=1, ge=1, description="Số trang (bắt đầu từ 1)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Số lượng bản ghi mỗi trang (1-100)"),
    q: Optional[str] = Query(default=None, description="Tìm theo mã hộ, tên chủ hộ, SĐT"),
    status_param: Optional[str] = Query(default=None, alias="status", description="Lọc theo trạng thái (ACTIVE, INACTIVE)"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> HouseholdPage:
    """Liệt kê danh sách hộ gia đình kèm phân trang và tìm kiếm theo OpenAPI spec."""
    query = select(Household)

    if status_param is not None:
        status_clean = status_param.strip().upper()
        if status_clean not in ("ACTIVE", "INACTIVE"):
            raise AppAPIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                code="VALIDATION_ERROR",
                message="Trạng thái chỉ có thể là ACTIVE hoặc INACTIVE."
            )
        query = query.where(Household.status == status_clean)

    if q and q.strip():
        q_pattern = f"%{q.strip()}%"
        # Tìm hộ theo mã hộ, SĐT liên hệ, hoặc tên/SĐT nhân khẩu trong hộ
        matching_residents_hh = (
            select(Resident.household_id)
            .where(
                Resident.is_deleted.is_(False),
                or_(
                    Resident.full_name.ilike(q_pattern),
                    Resident.phone.ilike(q_pattern)
                )
            )
        )
        query = query.where(
            or_(
                Household.household_code.ilike(q_pattern),
                Household.contact_phone.ilike(q_pattern),
                Household.id.in_(matching_residents_hh)
            )
        )

    # Đếm tổng số bản ghi phù hợp
    total_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(total_stmt) or 0

    # Phân trang và sắp xếp theo ID
    items_stmt = query.order_by(Household.id.asc()).offset((page - 1) * page_size).limit(page_size)
    households = db.scalars(items_stmt).all()

    items = [build_household_schema(db, h) for h in households]

    return HouseholdPage(
        page=page,
        page_size=page_size,
        total=total,
        items=items
    )


@router.post(
    "",
    response_model=HouseholdCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo hộ gia đình mới",
    description="Tạo hộ gia đình mới, gán căn hộ, tạo chủ hộ và tự động sinh tài khoản cư dân (US-01, AC-01.2, AC-30.2, D-12). Phân quyền: ADMIN.",
)
def create_household(
    req: HouseholdCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN")),
) -> HouseholdCreated:
    """Tạo hộ gia đình mới trong 1 giao dịch ACID nguyên tử."""
    # 1. Kiểm tra trùng lặp mã hộ gia đình (case-insensitive)
    existing_code = db.scalar(
        select(Household).where(func.lower(Household.household_code) == req.household_code.strip().lower())
    )
    if existing_code:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_HOUSEHOLD_CODE",
            message=f"Mã hộ gia đình '{req.household_code.strip()}' đã tồn tại trên hệ thống."
        )

    # 2. Nếu có gán căn hộ, kiểm tra căn hộ tồn tại và đang trống
    apartment = None
    if req.apartment_id is not None:
        apartment = db.scalar(select(Apartment).where(Apartment.id == req.apartment_id))
        if not apartment:
            raise AppAPIException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="NOT_FOUND",
                message=f"Không tìm thấy căn hộ có ID {req.apartment_id}."
            )

        active_occupancy = db.scalar(
            select(ApartmentOccupancy).where(
                ApartmentOccupancy.apartment_id == req.apartment_id,
                ApartmentOccupancy.end_date.is_(None)
            )
        )
        if active_occupancy:
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="APARTMENT_OCCUPIED",
                message=f"Căn hộ '{apartment.code}' đang có hộ gia đình khác cư trú."
            )

    # 3. Nếu có thông tin chủ hộ, kiểm tra trùng lặp CCCD toàn hệ thống (AC-05.2)
    if req.head and req.head.cccd:
        existing_cccd = db.scalar(
            select(Resident).where(
                Resident.cccd == req.head.cccd.strip(),
                Resident.is_deleted.is_(False)
            )
        )
        if existing_cccd:
            raise AppAPIException(
                status_code=status.HTTP_409_CONFLICT,
                code="DUPLICATE_CCCD",
                message=f"Số CCCD/CMND '{req.head.cccd.strip()}' đã tồn tại trên hệ thống."
            )

    # 4. Giao dịch ACID nguyên tử tạo Hộ gia đình, Lịch sử cư trú, Chủ hộ và Tài khoản cư dân
    # 4.1. Tạo bản ghi Hộ gia đình
    new_household = Household(
        household_code=req.household_code.strip(),
        status="ACTIVE",
        contact_phone=req.contact_phone.strip() if req.contact_phone else None,
        contact_email=req.contact_email.strip() if req.contact_email else None,
        note=req.note.strip() if req.note else None
    )
    db.add(new_household)
    db.flush()

    # 4.2. Gắn căn hộ nếu được chỉ định
    if req.apartment_id is not None:
        occupancy = ApartmentOccupancy(
            apartment_id=req.apartment_id,
            household_id=new_household.id,
            start_date=req.occupancy_start_date or date.today(),
            end_date=None
        )
        db.add(occupancy)

    # 4.3. Tạo nhân khẩu chủ hộ nếu có thông tin
    head_resident = None
    if req.head:
        head_resident = Resident(
            household_id=new_household.id,
            full_name=req.head.full_name.strip(),
            date_of_birth=req.head.date_of_birth,
            gender=req.head.gender.strip().upper(),
            cccd=req.head.cccd.strip() if req.head.cccd else None,
            phone=req.head.phone.strip() if req.head.phone else (req.contact_phone.strip() if req.contact_phone else None),
            email=req.head.email.strip() if req.head.email else (req.contact_email.strip() if req.contact_email else None),
            relationship_to_head=req.head.relationship_to_head.strip() if req.head.relationship_to_head else "CHỦ HỘ",
            is_head=True,
            residence_status="THUONG_TRU",
            is_deleted=False
        )
        db.add(head_resident)
        db.flush()

    # 4.4. Tự động sinh tài khoản cư dân mặc định cho hộ mới (D-12, AC-30.2)
    resident_role = db.scalar(select(Role).where(Role.code == "RESIDENT"))
    if not resident_role:
        resident_role = Role(id=4, code="RESIDENT", name="Cư dân")
        db.add(resident_role)
        db.flush()

    clean_code = re.sub(r"[^a-zA-Z0-9_.-]", "_", new_household.household_code.strip().lower())
    base_username = f"res_{clean_code}"
    username = base_username
    counter = 1
    while db.scalar(select(User).where(func.lower(User.username) == username.lower())):
        username = f"{base_username}_{counter}"
        counter += 1

    temp_password = generate_secure_temporary_password(12)
    hashed_password = get_password_hash(temp_password)

    user_full_name = req.head.full_name.strip() if req.head else f"Cư dân {new_household.household_code}"
    user_email = req.head.email.strip() if req.head and req.head.email else (req.contact_email.strip() if req.contact_email else None)
    user_phone = req.head.phone.strip() if req.head and req.head.phone else (req.contact_phone.strip() if req.contact_phone else None)

    resident_user = User(
        username=username,
        password_hash=hashed_password,
        full_name=user_full_name,
        email=user_email,
        phone=user_phone,
        role_id=resident_role.id,
        household_id=new_household.id,
        is_active=True,
        must_change_password=True,
        failed_login_count=0
    )
    db.add(resident_user)

    # Commit toàn bộ giao dịch
    db.commit()
    db.refresh(new_household)

    base_household = build_household_schema(db, new_household)

    return HouseholdCreated(
        **base_household.model_dump(),
        resident_account=ResidentAccount(
            username=username,
            temporary_password=temp_password
        )
    )


@router.get(
    "/{id:int}",
    response_model=HouseholdSchema,
    status_code=status.HTTP_200_OK,
    summary="Chi tiết hộ gia đình",
    description="Xem thông tin chi tiết một hộ gia đình kèm thông tin căn hộ và chủ hộ (US-01). Phân quyền: ADMIN, ACCOUNTANT.",
)
def get_household(
    id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN", "ACCOUNTANT")),
) -> HouseholdSchema:
    """Lấy thông tin chi tiết hộ gia đình theo ID."""
    household = db.scalar(select(Household).where(Household.id == id))
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình có ID {id}."
        )

    return build_household_schema(db, household)


@router.patch(
    "/{id:int}",
    response_model=HouseholdSchema,
    status_code=status.HTTP_200_OK,
    summary="Cập nhật thông tin liên hệ của hộ",
    description="Cập nhật thông tin liên hệ (SĐT, email, ghi chú) của hộ gia đình (US-02). Phân quyền: ADMIN.",
)
def update_household(
    id: int,
    req: HouseholdUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("ADMIN")),
) -> HouseholdSchema:
    """Cập nhật thông tin liên hệ của hộ gia đình theo ID."""
    household = db.scalar(select(Household).where(Household.id == id))
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình có ID {id}."
        )

    update_data = req.model_dump(exclude_unset=True)
    if "contact_phone" in update_data:
        household.contact_phone = req.contact_phone.strip() if req.contact_phone else None
    if "contact_email" in update_data:
        household.contact_email = req.contact_email.strip() if req.contact_email else None
    if "note" in update_data:
        household.note = req.note.strip() if req.note else None

    db.commit()
    db.refresh(household)

    return build_household_schema(db, household)


@router.post(
    "/{id:int}/deactivate",
    response_model=HouseholdSchema,
    status_code=status.HTTP_200_OK,
    summary="Ngừng quản lý hộ",
    description="Chỉ được ngừng khi hộ không còn công nợ. Hộ chuyển sang INACTIVE, không xóa dữ liệu (US-02). Phân quyền: ADMIN.",
)
def deactivate_household(
    id: int,
    req: HouseholdDeactivate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> HouseholdSchema:
    """Ngừng quản lý hộ gia đình khi hộ không còn công nợ."""
    household = db.scalar(select(Household).where(Household.id == id))
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình có ID {id}."
        )

    # 1. Kiểm tra tất toán công nợ (AC-02.1)
    if check_household_has_debt(db, household.id):
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DEBT_NOT_SETTLED",
            message="Hộ gia đình còn công nợ chưa tất toán, không thể ngừng quản lý."
        )

    old_status = household.status
    household.status = "INACTIVE"

    # 2. Kết thúc lưu trú hiện tại trong apartment_occupancies nếu có
    active_occupancy = db.scalar(
        select(ApartmentOccupancy).where(
            ApartmentOccupancy.household_id == household.id,
            ApartmentOccupancy.end_date.is_(None)
        )
    )
    if active_occupancy:
        active_occupancy.end_date = date.today()
        active_occupancy.end_reason = req.reason.strip()

    # 3. Vô hiệu hóa tài khoản cư dân liên kết với hộ nếu có
    resident_user = db.scalar(
        select(User).where(
            User.household_id == household.id,
            User.is_active.is_(True)
        )
    )
    if resident_user:
        resident_user.is_active = False

    # 4. Ghi nhận Audit Log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    audit = AuditLog(
        user_id=current_user.id,
        action="DEACTIVATE_HOUSEHOLD",
        entity_type="HOUSEHOLD",
        entity_id=str(household.id),
        old_value={"status": old_status},
        new_value={"status": "INACTIVE"},
        reason=req.reason.strip(),
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit)

    db.commit()
    db.refresh(household)

    return build_household_schema(db, household)


@router.post(
    "/{id:int}/transfer",
    response_model=HouseholdSchema,
    status_code=status.HTTP_200_OK,
    summary="Chuyển nhượng căn hộ từ hộ này sang hộ mới",
    description="`{id}` là hộ đang giữ căn hộ. Kết thúc `apartment_occupancies` của hộ cũ và mở bản ghi mới cho `new_household_id` tại `effective_date`. Hộ cũ phải hết công nợ (US-03, AC-03.1). Phân quyền: ADMIN.",
)
def transfer_household(
    id: int,
    req: HouseholdTransferRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> HouseholdSchema:
    """Chuyển nhượng quyền cư trú căn hộ từ hộ gia đình hiện tại sang hộ gia đình mới (US-03)."""
    # 1. Kiểm tra tồn tại hộ gia đình cũ ({id})
    old_household = db.scalar(select(Household).where(Household.id == id))
    if not old_household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình có ID {id}."
        )

    # 2. Kiểm tra tồn tại hộ gia đình mới (new_household_id)
    new_household = db.scalar(select(Household).where(Household.id == req.new_household_id))
    if not new_household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình nhận chuyển nhượng có ID {req.new_household_id}."
        )

    # 3. Không cho phép chuyển nhượng cho chính hộ đó
    if old_household.id == new_household.id:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Không thể chuyển nhượng căn hộ cho chính hộ gia đình đó."
        )

    # 4. Kiểm tra trạng thái hoạt động của cả hai hộ
    if old_household.status != "ACTIVE":
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Hộ gia đình chuyển nhượng đã ngừng hoạt động (INACTIVE), không thể thực hiện chuyển nhượng."
        )

    if new_household.status != "ACTIVE":
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Hộ gia đình nhận chuyển nhượng đã ngừng hoạt động (INACTIVE), không thể nhận chuyển nhượng căn hộ."
        )

    # 5. Kiểm tra hộ cũ có đang cư trú tại căn hộ nào không (HOUSEHOLD_HAS_NO_APARTMENT)
    old_occupancy_row = db.execute(
        select(ApartmentOccupancy, Apartment)
        .join(Apartment, Apartment.id == ApartmentOccupancy.apartment_id)
        .where(
            ApartmentOccupancy.household_id == old_household.id,
            ApartmentOccupancy.end_date.is_(None)
        )
    ).first()

    if not old_occupancy_row:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="HOUSEHOLD_HAS_NO_APARTMENT",
            message="Hộ gia đình hiện không cư trú tại căn hộ nào, không thể chuyển nhượng."
        )

    old_occupancy, apt = old_occupancy_row

    # 6. Kiểm tra ngày hiệu lực chuyển nhượng không được trước ngày bắt đầu cư trú của hộ cũ
    if req.effective_date < old_occupancy.start_date:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=f"Ngày hiệu lực chuyển nhượng ({req.effective_date}) không được trước ngày bắt đầu cư trú của hộ cũ ({old_occupancy.start_date})."
        )

    # 7. Kiểm tra tất toán công nợ của hộ cũ (AC-03.1, DEBT_NOT_SETTLED)
    if check_household_has_debt(db, old_household.id):
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DEBT_NOT_SETTLED",
            message="Hộ gia đình còn công nợ chưa tất toán, không thể chuyển nhượng căn hộ."
        )

    # 8. Kiểm tra hộ mới đã có căn hộ khác đang cư trú chưa (APARTMENT_OCCUPIED)
    new_hh_active_occ = db.scalar(
        select(ApartmentOccupancy).where(
            ApartmentOccupancy.household_id == new_household.id,
            ApartmentOccupancy.end_date.is_(None)
        )
    )
    if new_hh_active_occ:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="APARTMENT_OCCUPIED",
            message="Hộ gia đình nhận chuyển nhượng hiện đang cư trú tại một căn hộ khác."
        )

    # Kiểm tra căn hộ có bản ghi cư trú nào khác đang mở không
    other_apt_occ = db.scalar(
        select(ApartmentOccupancy).where(
            ApartmentOccupancy.apartment_id == apt.id,
            ApartmentOccupancy.household_id != old_household.id,
            ApartmentOccupancy.end_date.is_(None)
        )
    )
    if other_apt_occ:
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="APARTMENT_OCCUPIED",
            message=f"Căn hộ '{apt.code}' đang có hộ gia đình khác cư trú."
        )

    # 9. Thực thi chuyển nhượng trong giao dịch ACID
    old_occupancy.end_date = req.effective_date
    old_occupancy.end_reason = req.reason.strip() if req.reason else f"Chuyển nhượng căn hộ sang hộ {new_household.household_code}"

    new_occupancy = ApartmentOccupancy(
        apartment_id=apt.id,
        household_id=new_household.id,
        start_date=req.effective_date,
        end_date=None,
        end_reason=None
    )
    db.add(new_occupancy)

    # 10. Ghi nhận Audit Log
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    audit = AuditLog(
        user_id=current_user.id,
        action="TRANSFER_APARTMENT",
        entity_type="HOUSEHOLD",
        entity_id=str(old_household.id),
        old_value={
            "household_id": old_household.id,
            "household_code": old_household.household_code,
            "apartment_id": apt.id,
            "apartment_code": apt.code
        },
        new_value={
            "household_id": new_household.id,
            "household_code": new_household.household_code,
            "apartment_id": apt.id,
            "apartment_code": apt.code,
            "effective_date": req.effective_date.isoformat()
        },
        reason=req.reason.strip() if req.reason else f"Chuyển nhượng căn hộ {apt.code} từ hộ {old_household.household_code} sang hộ {new_household.household_code}.",
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit)

    db.commit()
    db.refresh(new_household)

    return build_household_schema(db, new_household)


@router.put(
    "/{id:int}/head",
    response_model=HouseholdSchema,
    status_code=status.HTTP_200_OK,
    summary="Đổi chủ hộ",
    description="Hạ chủ hộ cũ và nâng nhân khẩu mới trong cùng một giao dịch. Ghi audit CHANGE_HEAD (US-02, US-05, AC-02.1). Phân quyền: ADMIN.",
)
def change_household_head(
    id: int,
    req: HouseholdChangeHead,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN")),
) -> HouseholdSchema:
    """Thay đổi chủ hộ đại diện của hộ gia đình trong 1 giao dịch ACID nguyên tử."""
    household = db.scalar(select(Household).where(Household.id == id))
    if not household:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy hộ gia đình có ID {id}."
        )

    if household.status != "ACTIVE":
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Hộ gia đình đã ngừng hoạt động (INACTIVE), không thể thay đổi chủ hộ."
        )

    # 1. Kiểm tra tất toán công nợ trước khi đổi chủ hộ (AC-02.1, D-06)
    if check_household_has_debt(db, household.id):
        raise AppAPIException(
            status_code=status.HTTP_409_CONFLICT,
            code="DEBT_NOT_SETTLED",
            message="Hộ gia đình còn công nợ chưa tất toán, không thể thay đổi chủ hộ."
        )

    # 2. Tìm nhân khẩu mới được chỉ định làm chủ hộ
    new_head = db.scalar(
        select(Resident).where(
            Resident.id == req.new_head_resident_id,
            Resident.household_id == household.id,
            Resident.is_deleted.is_(False)
        )
    )
    if not new_head:
        raise AppAPIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"Không tìm thấy nhân khẩu hợp lệ có ID {req.new_head_resident_id} thuộc hộ gia đình này."
        )

    if new_head.residence_status not in ("THUONG_TRU", "TAM_VANG"):
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message=f"Nhân khẩu '{new_head.full_name}' có trạng thái '{new_head.residence_status}', không thể chỉ định làm chủ hộ."
        )

    # 3. Giao dịch nguyên tử ACID đổi chủ hộ
    # Hạ chủ hộ cũ nếu có
    existing_heads = db.scalars(
        select(Resident).where(
            Resident.household_id == household.id,
            Resident.is_head.is_(True),
            Resident.is_deleted.is_(False)
        )
    ).all()

    old_head_info = None
    for h in existing_heads:
        if old_head_info is None:
            old_head_info = {"head_resident_id": h.id, "head_name": h.full_name}
        h.is_head = False
        if h.relationship_to_head == "CHỦ HỘ":
            h.relationship_to_head = "THÀNH VIÊN"

    # Nâng nhân khẩu mới lên chủ hộ
    new_head.is_head = True
    new_head.relationship_to_head = "CHỦ HỘ"
    new_head.status_effective_date = req.effective_date
    if req.reason:
        new_head.status_reason = req.reason.strip()

    # Đồng bộ thông tin đại diện cho tài khoản cư dân của hộ (nếu có)
    resident_user = db.scalar(
        select(User).where(User.household_id == household.id)
    )
    if resident_user:
        resident_user.full_name = new_head.full_name
        if new_head.email:
            resident_user.email = new_head.email
        if new_head.phone:
            resident_user.phone = new_head.phone

    # Ghi nhận Audit Log CHANGE_HEAD (AC-02.1)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    audit = AuditLog(
        user_id=current_user.id,
        action="CHANGE_HEAD",
        entity_type="HOUSEHOLD",
        entity_id=str(household.id),
        old_value=old_head_info,
        new_value={
            "head_resident_id": new_head.id,
            "head_name": new_head.full_name,
            "effective_date": req.effective_date.isoformat()
        },
        reason=req.reason.strip() if req.reason else f"Thay đổi chủ hộ sang {new_head.full_name}.",
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(audit)

    db.commit()
    db.refresh(household)

    return build_household_schema(db, household)
