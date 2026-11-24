# [SỬA] Thêm Tuple để khai báo kiểu cho danh sách kết quả kèm điểm xếp hạng
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import get_db
from app.core.rbac_middleware import AppAPIException, require_roles
from app.models.property import Apartment, ApartmentOccupancy, Household, Resident
from app.models.vehicle import Vehicle
from app.schemas.search import SearchEntityType, SearchHit, SearchResult

router = APIRouter(tags=["Search & Reports"])


# [THÊM] Hàm chấm điểm độ liên quan trực tiếp trên các trường dữ liệu gốc
# (tránh chấm nhầm tiền tố "Hộ ", "Căn hộ ", "Biển số " trong title)
def _calc_relevance_score(fields: List[Optional[str]], q_lower: str) -> int:
    """0 = khớp chính xác, 1 = khớp tiền tố, 2 = khớp chuỗi con, 3 = khác."""
    best = 3
    for field in fields:
        if not field:
            continue
        val = field.lower()
        if val == q_lower:
            return 0
        if val.startswith(q_lower):
            best = min(best, 1)
        elif q_lower in val:
            best = min(best, 2)
    return best


@router.get(
    "/search",
    response_model=SearchResult,
    status_code=status.HTTP_200_OK,
    summary="Tìm kiếm đa tiêu chí (Omnibox)",
    description=(
        "Tìm kiếm tức thời trên Cư dân, Hộ gia đình, Căn hộ và Phương tiện theo tên, CCCD, "
        "mã căn hộ, mã hộ, số điện thoại hoặc biển số xe (US-23). "
        "Phân quyền: ADMIN, ACCOUNTANT, TREASURER."
    ),
    operation_id="globalSearch",
)
def global_search(
    q: str = Query(
        ...,
        min_length=1,
        max_length=255,
        description="Từ khóa tìm kiếm (tên, CCCD, mã căn, mã hộ, SĐT, biển số...)",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Giới hạn số lượng kết quả trả về (1-50, mặc định 10)",
    ),
    db: Session = Depends(get_db),
    _current_user=Depends(require_roles("ADMIN", "ACCOUNTANT", "TREASURER")),
) -> SearchResult:
    """Omnibox multi-entity search endpoint satisfying AC-23.1."""
    q_clean = q.strip()
    if not q_clean:
        raise AppAPIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="Từ khóa tìm kiếm không được để trống.",
            details=[
                {
                    "field": "q",
                    "message": "Từ khóa tìm kiếm không được chỉ chứa khoảng trắng.",
                }
            ],
        )

    # [SỬA] Escape các ký tự wildcard (\, %, _) để tránh khớp toàn bảng khi user nhập ký tự đặc biệt
    escaped_q = (
        q_clean.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )
    search_pattern = f"%{escaped_q}%"
    q_lower = q_clean.lower()

    # [SỬA] Lưu (score, SearchHit) để sắp xếp theo độ khớp của trường gốc
    scored_hits: List[Tuple[int, SearchHit]] = []

    # 1. Tìm kiếm Hộ gia đình (Household): household_code, contact_phone
    household_stmt = (
        select(Household)
        .options(
            # [SỬA] Đổi joinedload -> selectinload cho quan hệ 1-nhiều (occupancies)
            # để .limit(limit) giới hạn đúng số Hộ thay vì số dòng sau khi JOIN
            selectinload(Household.occupancies).joinedload(ApartmentOccupancy.apartment),
            selectinload(Household.residents),
        )
        .where(
            or_(
                # [SỬA] Thêm escape="\\" khớp với escaped_q
                Household.household_code.ilike(search_pattern, escape="\\"),
                Household.contact_phone.ilike(search_pattern, escape="\\"),
            )
        )
        .order_by(Household.id.asc())
        .limit(limit)
    )
    # [SỬA] Bỏ .unique() vì đã dùng selectinload
    households = db.execute(household_stmt).scalars().all()
    for h in households:
        sub_parts: List[str] = []
        active_occ = next((occ for occ in h.occupancies if occ.end_date is None), None)
        if active_occ and active_occ.apartment:
            sub_parts.append(f"Căn hộ: {active_occ.apartment.code}")
        head = next(
            (res for res in h.residents if res.is_head and not res.is_deleted), None
        )
        if head:
            sub_parts.append(f"Chủ hộ: {head.full_name}")
        if h.contact_phone:
            sub_parts.append(f"SĐT: {h.contact_phone}")
        if h.status != "ACTIVE":
            sub_parts.append(f"Trạng thái: {h.status}")

        # [SỬA] Tính điểm trên mã hộ và SĐT gốc
        score = _calc_relevance_score([h.household_code, h.contact_phone], q_lower)
        scored_hits.append(
            (
                score,
                SearchHit(
                    entity_type=SearchEntityType.HOUSEHOLD,
                    entity_id=h.id,
                    household_id=h.id,
                    title=f"Hộ {h.household_code}",
                    subtitle=" - ".join(sub_parts) if sub_parts else None,
                ),
            )
        )

    # 2. Tìm kiếm Cư dân (Resident): full_name, cccd, phone (bỏ qua resident đã xóa mềm)
    resident_stmt = (
        select(Resident)
        .options(joinedload(Resident.household))
        .where(
            Resident.is_deleted.is_(False),
            or_(
                # [SỬA] Thêm escape="\\"
                Resident.full_name.ilike(search_pattern, escape="\\"),
                Resident.cccd.ilike(search_pattern, escape="\\"),
                Resident.phone.ilike(search_pattern, escape="\\"),
            ),
        )
        .order_by(Resident.id.asc())
        .limit(limit)
    )
    residents = db.execute(resident_stmt).scalars().all()
    for r in residents:
        sub_parts = []
        if r.cccd:
            sub_parts.append(f"CCCD: {r.cccd}")
        if r.phone:
            sub_parts.append(f"SĐT: {r.phone}")
        if r.household:
            sub_parts.append(f"Hộ: {r.household.household_code}")
        role_str = r.relationship_to_head or ("Chủ hộ" if r.is_head else "Thành viên")
        sub_parts.append(role_str)

        # [SỬA] Tính điểm trên tên, CCCD và SĐT gốc
        score = _calc_relevance_score([r.full_name, r.cccd, r.phone], q_lower)
        scored_hits.append(
            (
                score,
                SearchHit(
                    entity_type=SearchEntityType.RESIDENT,
                    entity_id=r.id,
                    household_id=r.household_id,
                    title=r.full_name,
                    subtitle=" - ".join(sub_parts) if sub_parts else None,
                ),
            )
        )

    # 3. Tìm kiếm Căn hộ (Apartment): code
    apt_stmt = (
        select(Apartment)
        .options(
            # [SỬA] Đổi joinedload -> selectinload cho quan hệ 1-nhiều (occupancies)
            selectinload(Apartment.occupancies).joinedload(ApartmentOccupancy.household)
        )
        # [SỬA] Thêm escape="\\"
        .where(Apartment.code.ilike(search_pattern, escape="\\"))
        .order_by(Apartment.id.asc())
        .limit(limit)
    )
    # [SỬA] Bỏ .unique() vì đã dùng selectinload
    apartments = db.execute(apt_stmt).scalars().all()
    for a in apartments:
        # [SỬA] Format area_m2 với :g để bỏ số 0 thừa (78.50m² -> 78.5m²)
        sub_parts = [f"Tầng {a.floor}", f"{a.area_m2:g}m²", f"Trạng thái: {a.status}"]
        active_occ = next((occ for occ in a.occupancies if occ.end_date is None), None)
        h_id: Optional[int] = None
        if active_occ and active_occ.household:
            sub_parts.append(f"Hộ: {active_occ.household.household_code}")
            h_id = active_occ.household_id

        # [SỬA] Tính điểm trên mã căn hộ gốc
        score = _calc_relevance_score([a.code], q_lower)
        scored_hits.append(
            (
                score,
                SearchHit(
                    entity_type=SearchEntityType.APARTMENT,
                    entity_id=a.id,
                    household_id=h_id,
                    title=f"Căn hộ {a.code}",
                    subtitle=" - ".join(sub_parts),
                ),
            )
        )

    # 4. Tìm kiếm Phương tiện (Vehicle): plate_number
    vehicle_stmt = (
        select(Vehicle)
        .options(joinedload(Vehicle.household))
        # [SỬA] Thêm escape="\\"
        .where(Vehicle.plate_number.ilike(search_pattern, escape="\\"))
        .order_by(Vehicle.id.asc())
        .limit(limit)
    )
    vehicles = db.execute(vehicle_stmt).scalars().all()
    for v in vehicles:
        sub_parts = [f"Loại: {v.vehicle_type}"]
        brand_color = " ".join(filter(None, [v.brand, v.color]))
        if brand_color:
            sub_parts.append(brand_color)
        if v.household:
            sub_parts.append(f"Hộ: {v.household.household_code}")
        sub_parts.append(f"Trạng thái: {v.status}")

        # [SỬA] Tính điểm trên biển số gốc
        score = _calc_relevance_score([v.plate_number], q_lower)
        scored_hits.append(
            (
                score,
                SearchHit(
                    entity_type=SearchEntityType.VEHICLE,
                    entity_id=v.id,
                    household_id=v.household_id,
                    title=f"Biển số {v.plate_number}",
                    subtitle=" - ".join(sub_parts),
                ),
            )
        )

    # [SỬA] Sắp xếp theo điểm liên quan (exact -> prefix -> substring) rồi cắt đúng limit
    scored_hits.sort(key=lambda pair: pair[0])

    return SearchResult(items=[hit for _, hit in scored_hits[:limit]])
