from datetime import date
import re
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.core.security import generate_secure_temporary_password, get_password_hash
from app.models.property import Apartment, ApartmentOccupancy, Household, Resident
from app.models.user import Role, User
from app.schemas.household import (
    Household as HouseholdSchema,
    HouseholdCreate,
    HouseholdCreated,
    HouseholdPage,
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
    _current_user = Depends(require_roles("ADMIN", "ACCOUNTANT")),
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
    _current_user = Depends(require_roles("ADMIN")),
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
    _current_user = Depends(require_roles("ADMIN", "ACCOUNTANT")),
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

