"""
Test Suite for User Story US-23: Công cụ Tìm kiếm đa tiêu chí (Omnibox).

Specification & Standards:
- docs/openapi.yaml:
  - GET /search (operationId: globalSearch, US-23)
  - Roles: ADMIN, ACCOUNTANT, TREASURER
  - Query params:
    - q: string, minLength=1, required
    - limit: integer, min=1, max=50, default=10
  - Response 200: SearchResult (items: List[SearchHit])
    - SearchHit: entity_type (HOUSEHOLD, APARTMENT, RESIDENT, VEHICLE), entity_id, household_id, title, subtitle
- docs/API_CONTRACT.md (Section 3.17.1)
- docs/PRODUCT_BACKLOG.md (F-04.1, WBS 2.4.1, AC-23.1):
  - Tra cứu thông tin ngay lập tức theo tên, CCCD, mã căn, SĐT, biển số.
  - Tốc độ phản hồi <= 1 giây trên tập dữ liệu 1.000 hộ và 5.000 nhân khẩu.
"""

import time
from datetime import date
import pytest
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.property import Apartment, ApartmentOccupancy, Household, Resident
from app.models.user import Role, User
from app.models.vehicle import Vehicle
from app.schemas.search import SearchEntityType


# ==============================================================================
# Helper Functions & Fixtures for Auth Tokens
# ==============================================================================

def make_headers(
    role: str = "ADMIN",
    sub: str = "1",
    username: str = "admin_test",
    must_change_password: bool = False,
):
    token = create_access_token({
        "sub": str(sub),
        "username": username,
        "role": role,
        "must_change_password": must_change_password,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def treasurer_headers(db_session):
    """Provide a dedicated TREASURER auth header with actual user in DB."""
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us23"))
    if not user:
        user = User(
            username="treasurer_test_us23",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US23",
            email="treasurer_23@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        db_session.commit()
    return make_headers(role="TREASURER", sub=str(user.id), username=user.username)


@pytest.fixture
def must_change_headers(db_session):
    """Provide auth header for a user requiring password change."""
    user = db_session.scalar(select(User).where(User.username == "must_change_test_us23"))
    if not user:
        user = User(
            username="must_change_test_us23",
            password_hash=get_password_hash("ChangeMePass123!"),
            full_name="Đổi Mật Khẩu Test US23",
            email="changeme_23@bluemoon.local",
            role_id=1,
            is_active=True,
            must_change_password=True,
        )
        db_session.add(user)
        db_session.commit()
    return make_headers(role="ADMIN", sub=str(user.id), username=user.username, must_change_password=True)


# ==============================================================================
# Fixtures for US-23 Test Data
# ==============================================================================

@pytest.fixture(autouse=True)
def setup_us23_data(db_session):
    """Seed dedicated test entities for US-23 test scenarios."""
    # Ensure Treasurer role exists
    treasurer_role = db_session.execute(select(Role).where(Role.code == "TREASURER")).scalar_one_or_none()
    if not treasurer_role:
        treasurer_role = Role(id=3, code="TREASURER", name="Thủ quỹ")
        db_session.add(treasurer_role)
        db_session.commit()

    # Apartments
    apt1 = Apartment(id=101, code="APT_US23_101", floor=1, area_m2=85.5, status="ACTIVE")
    apt2 = Apartment(id=102, code="APT_US23_102", floor=2, area_m2=60.0, status="ACTIVE")
    apt_vacant = Apartment(id=103, code="APT_US23_VACANT", floor=3, area_m2=100.0, status="ACTIVE")
    apt_special = Apartment(id=104, code="APT_US23_X01", floor=4, area_m2=75.0, status="ACTIVE")
    db_session.add_all([apt1, apt2, apt_vacant, apt_special])

    # Households
    hh1 = Household(id=101, household_code="HH_US23_001", contact_phone="0911223344", status="ACTIVE")
    hh2 = Household(id=102, household_code="HH_US23_002", contact_phone="0988776655", status="ACTIVE")
    hh_inactive = Household(id=103, household_code="HH_US23_INACTIVE", contact_phone="0933445566", status="INACTIVE")
    hh_wildcard = Household(id=104, household_code="HH_US23X001", contact_phone="0977889900", status="ACTIVE")
    db_session.add_all([hh1, hh2, hh_inactive, hh_wildcard])

    # Occupancies
    occ1 = ApartmentOccupancy(
        id=101,
        apartment_id=101,
        household_id=101,
        start_date=date(2025, 1, 1),
        end_date=None,
    )
    occ2 = ApartmentOccupancy(
        id=102,
        apartment_id=102,
        household_id=102,
        start_date=date(2025, 1, 1),
        end_date=None,
    )
    db_session.add_all([occ1, occ2])

    # Residents
    r1 = Resident(
        id=101,
        household_id=101,
        full_name="Nguyễn Văn An",
        date_of_birth=date(1985, 5, 20),
        gender="NAM",
        cccd="001202000001",
        phone="0911223344",
        is_head=True,
        relationship_to_head="Chủ hộ",
        residence_status="THUONG_TRU",
        is_deleted=False,
    )
    r2 = Resident(
        id=102,
        household_id=101,
        full_name="Trần Thị Bình",
        date_of_birth=date(1988, 8, 15),
        gender="NU",
        cccd="001202000002",
        phone="0922334455",
        is_head=False,
        relationship_to_head="Vợ",
        residence_status="THUONG_TRU",
        is_deleted=False,
    )
    r3 = Resident(
        id=103,
        household_id=102,
        full_name="Lê Văn Cường",
        date_of_birth=date(1990, 10, 10),
        gender="NAM",
        cccd="001202000003",
        phone="0988776655",
        is_head=True,
        relationship_to_head="Chủ hộ",
        residence_status="THUONG_TRU",
        is_deleted=False,
    )
    r_deleted = Resident(
        id=104,
        household_id=101,
        full_name="Phạm Đã Xóa",
        date_of_birth=date(1992, 1, 1),
        gender="NAM",
        cccd="001202999999",
        phone="0999999999",
        is_head=False,
        relationship_to_head="Em trai",
        residence_status="DA_CHUYEN_DI",
        is_deleted=True,
    )
    db_session.add_all([r1, r2, r3, r_deleted])

    # Vehicles
    v1 = Vehicle(
        id=101,
        household_id=101,
        plate_number="29A-888.88",
        vehicle_type="CAR",
        brand="Toyota",
        color="Đen",
        status="ACTIVE",
    )
    v2 = Vehicle(
        id=102,
        household_id=102,
        plate_number="29B-999.99",
        vehicle_type="MOTORBIKE",
        brand="Honda",
        color="Đỏ",
        status="ACTIVE",
    )
    v3 = Vehicle(
        id=103,
        household_id=101,
        plate_number="30F-111.11",
        vehicle_type="CAR",
        brand="Mazda",
        color="Trắng",
        status="INACTIVE",
    )
    db_session.add_all([v1, v2, v3])

    db_session.commit()

    yield

    # Cleanup test data created for US-23
    db_session.query(Vehicle).filter(Vehicle.id.in_([101, 102, 103])).delete(synchronize_session=False)
    db_session.query(Resident).filter(Resident.id.in_([101, 102, 103, 104])).delete(synchronize_session=False)
    db_session.query(ApartmentOccupancy).filter(ApartmentOccupancy.id.in_([101, 102])).delete(synchronize_session=False)
    db_session.query(Household).filter(Household.id.in_([101, 102, 103, 104])).delete(synchronize_session=False)
    db_session.query(Apartment).filter(Apartment.id.in_([101, 102, 103, 104])).delete(synchronize_session=False)
    db_session.commit()


# ==============================================================================
# 1. Authentication & RBAC Tests (AC-44.1, API Contract 3.17.1)
# ==============================================================================

def test_search_unauthenticated_returns_401(client):
    """GET /search without token must return 401 UNAUTHENTICATED."""
    res = client.get("/search?q=Nguyen")
    assert res.status_code == 401
    data = res.json()
    assert data["code"] == "UNAUTHENTICATED"


def test_search_resident_forbidden_returns_403(client):
    """GET /search called by RESIDENT role must return 403 FORBIDDEN."""
    headers = make_headers(role="RESIDENT", sub="3", username="resident_101")
    res = client.get("/search?q=Nguyen", headers=headers)
    assert res.status_code == 403
    data = res.json()
    assert data["code"] == "FORBIDDEN"


def test_search_must_change_password_returns_403(client, must_change_headers):
    """GET /search called with must_change_password=True must return 403 PASSWORD_CHANGE_REQUIRED."""
    res = client.get("/search?q=Nguyen", headers=must_change_headers)
    assert res.status_code == 403
    data = res.json()
    assert data["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_search_admin_success_200(client):
    """GET /search called by ADMIN role must return 200 OK."""
    headers = make_headers(role="ADMIN", sub="1", username="admin_test")
    res = client.get("/search?q=An", headers=headers)
    assert res.status_code == 200
    assert "items" in res.json()


def test_search_accountant_success_200(client):
    """GET /search called by ACCOUNTANT role must return 200 OK."""
    headers = make_headers(role="ACCOUNTANT", sub="2", username="accountant_test")
    res = client.get("/search?q=An", headers=headers)
    assert res.status_code == 200
    assert "items" in res.json()


def test_search_treasurer_success_200(client, treasurer_headers):
    """GET /search called by TREASURER role must return 200 OK."""
    res = client.get("/search?q=An", headers=treasurer_headers)
    assert res.status_code == 200
    assert "items" in res.json()


# ==============================================================================
# 2. Input Validation Tests (HTTP 400 VALIDATION_ERROR)
# ==============================================================================

def test_search_missing_q_returns_400(client):
    """GET /search without query param q must return 400 VALIDATION_ERROR."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search", headers=headers)
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_search_empty_q_returns_400(client):
    """GET /search with empty string q='' must return 400 VALIDATION_ERROR."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=", headers=headers)
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_search_whitespace_only_q_returns_400(client):
    """GET /search with whitespace only q='   ' must return 400 VALIDATION_ERROR."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=%20%20%20", headers=headers)
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_search_limit_less_than_1_returns_400(client):
    """GET /search with limit=0 must return 400 VALIDATION_ERROR."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=Nguyen&limit=0", headers=headers)
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"


def test_search_limit_greater_than_50_returns_400(client):
    """GET /search with limit=51 must return 400 VALIDATION_ERROR."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=Nguyen&limit=51", headers=headers)
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"


# ==============================================================================
# 3. Entity-Specific Search Tests (RESIDENT, HOUSEHOLD, APARTMENT, VEHICLE)
# ==============================================================================

def test_search_by_resident_name(client):
    """Search by resident full_name returns RESIDENT hit with proper format."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=Nguyễn Văn An", headers=headers)
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    hit = items[0]
    assert hit["entity_type"] == SearchEntityType.RESIDENT
    assert hit["title"] == "Nguyễn Văn An"
    assert hit["household_id"] == 101
    assert "001202000001" in hit["subtitle"]
    assert "0911223344" in hit["subtitle"]
    assert "Chủ hộ" in hit["subtitle"]


def test_search_by_resident_cccd(client):
    """Search by resident CCCD/CMND returns RESIDENT hit."""
    headers = make_headers(role="ACCOUNTANT")
    res = client.get("/search?q=001202000002", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(
        h["entity_type"] == SearchEntityType.RESIDENT and h["title"] == "Trần Thị Bình"
        for h in items
    )


def test_search_by_resident_phone(client, treasurer_headers):
    """Search by resident phone returns matching resident."""
    res = client.get("/search?q=0922334455", headers=treasurer_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(
        h["entity_type"] == SearchEntityType.RESIDENT and h["title"] == "Trần Thị Bình"
        for h in items
    )


def test_search_soft_deleted_resident_not_returned(client):
    """Residents with is_deleted=True must not be returned in search results."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=Phạm Đã Xóa", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert not any(h["title"] == "Phạm Đã Xóa" for h in items)

    # Search by deleted resident CCCD
    res2 = client.get("/search?q=001202999999", headers=headers)
    assert res2.status_code == 200
    assert not any(h["entity_type"] == SearchEntityType.RESIDENT for h in res2.json()["items"])


def test_search_by_household_code(client):
    """Search by household_code returns HOUSEHOLD hit with active apartment & head info."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=HH_US23_001", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    hh_hits = [h for h in items if h["entity_type"] == SearchEntityType.HOUSEHOLD]
    assert len(hh_hits) >= 1
    hh = hh_hits[0]
    assert hh["title"] == "Hộ HH_US23_001"
    assert hh["household_id"] == 101
    assert "APT_US23_101" in hh["subtitle"]
    assert "Nguyễn Văn An" in hh["subtitle"]


def test_search_by_household_contact_phone(client):
    """Search by household contact_phone returns HOUSEHOLD hit."""
    headers = make_headers(role="ACCOUNTANT")
    res = client.get("/search?q=0988776655", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    hh_hits = [h for h in items if h["entity_type"] == SearchEntityType.HOUSEHOLD]
    assert any("HH_US23_002" in h["title"] for h in hh_hits)


def test_search_inactive_household_shows_status_in_subtitle(client):
    """Inactive household shows 'Trạng thái: INACTIVE' in subtitle."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=HH_US23_INACTIVE", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    hh_hits = [h for h in items if h["entity_type"] == SearchEntityType.HOUSEHOLD]
    assert len(hh_hits) >= 1
    assert "INACTIVE" in hh_hits[0]["subtitle"]


def test_search_by_apartment_code(client):
    """Search by apartment code returns APARTMENT hit with floor, area, and occupied household."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=APT_US23_101", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    apt_hits = [h for h in items if h["entity_type"] == SearchEntityType.APARTMENT]
    assert len(apt_hits) >= 1
    apt = apt_hits[0]
    assert apt["title"] == "Căn hộ APT_US23_101"
    assert apt["household_id"] == 101
    assert "Tầng 1" in apt["subtitle"]
    assert "HH_US23_001" in apt["subtitle"]


def test_search_vacant_apartment(client):
    """Vacant apartment returns APARTMENT hit with household_id=None."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=APT_US23_VACANT", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    apt_hits = [h for h in items if h["entity_type"] == SearchEntityType.APARTMENT]
    assert len(apt_hits) >= 1
    apt = apt_hits[0]
    assert apt["household_id"] is None
    assert "Tầng 3" in apt["subtitle"]


def test_search_by_vehicle_plate(client):
    """Search by vehicle plate_number returns VEHICLE hit."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=29A-888.88", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    veh_hits = [h for h in items if h["entity_type"] == SearchEntityType.VEHICLE]
    assert len(veh_hits) >= 1
    veh = veh_hits[0]
    assert veh["title"] == "Biển số 29A-888.88"
    assert veh["household_id"] == 101
    assert "CAR" in veh["subtitle"]
    assert "Toyota" in veh["subtitle"]
    assert "ACTIVE" in veh["subtitle"]


def test_search_inactive_vehicle(client, treasurer_headers):
    """Inactive vehicle is also searchable and displays INACTIVE status."""
    res = client.get("/search?q=30F-111.11", headers=treasurer_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    veh_hits = [h for h in items if h["entity_type"] == SearchEntityType.VEHICLE]
    assert len(veh_hits) >= 1
    assert "INACTIVE" in veh_hits[0]["subtitle"]


# ==============================================================================
# 4. Relevance Ranking & Wildcard Escaping Tests
# ==============================================================================

def test_search_relevance_ranking_exact_match_first(client):
    """Exact match on raw field must be ranked before prefix/substring matches."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=HH_US23_001", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    # First item must be the exact household
    assert items[0]["title"] == "Hộ HH_US23_001"
    assert items[0]["entity_type"] == SearchEntityType.HOUSEHOLD


def test_search_wildcard_escaping_underscore(client):
    """Underscore in query must be escaped so HH_US23_001 matches HH_US23_001, not HH_US23X001."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=HH_US23_001", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    hh_titles = [h["title"] for h in items if h["entity_type"] == SearchEntityType.HOUSEHOLD]
    assert "Hộ HH_US23_001" in hh_titles
    assert "Hộ HH_US23X001" not in hh_titles


def test_search_wildcard_escaping_percent(client):
    """Percent sign in query must be escaped as literal character."""
    headers = make_headers(role="ADMIN")
    res = client.get("/search?q=HH%US23", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    # No entity has literal '%', so it should return empty
    assert len(items) == 0


def test_search_limit_enforced(client):
    """Parameter limit must restrict the total number of items returned."""
    headers = make_headers(role="ADMIN")
    # 'US23' matches 4 apartments, 4 households, 4 residents, 3 vehicles (total 15)
    res = client.get("/search?q=US23&limit=3", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 3


def test_search_alias_api_v1_and_root(client):
    """Both /search and /api/v1/search must function identically."""
    headers = make_headers(role="ADMIN")
    res_root = client.get("/search?q=APT_US23_101", headers=headers)
    res_v1 = client.get("/api/v1/search?q=APT_US23_101", headers=headers)
    assert res_root.status_code == 200
    assert res_v1.status_code == 200
    assert res_root.json() == res_v1.json()


# ==============================================================================
# 5. Performance Benchmark Test (AC-23.1, NFR-005: <= 1.0s on 1,000 households & 5,000 residents)
# ==============================================================================

def test_search_performance_benchmark_scale_dataset(client, db_session):
    """
    AC-23.1 & NFR-005 Verification:
    Omnibox search response time must be <= 1.0 second on a scaled dataset of 1,000 households and 5,000 residents.
    """
    headers = make_headers(role="ADMIN")

    # Bulk create 1,000 households
    bulk_households = [
        Household(
            id=1000 + i,
            household_code=f"HH_BENCH_{i:04d}",
            contact_phone=f"09{i:08d}",
            status="ACTIVE",
        )
        for i in range(1000)
    ]
    db_session.bulk_save_objects(bulk_households)

    # Bulk create 5,000 residents (5 residents per household)
    bulk_residents = []
    res_id = 10000
    for h_idx in range(1000):
        hh_id = 1000 + h_idx
        for r_idx in range(5):
            res_id += 1
            bulk_residents.append(
                Resident(
                    id=res_id,
                    household_id=hh_id,
                    full_name=f"Cư Dân Bench {res_id}",
                    date_of_birth=date(1990, 1, 1),
                    gender="NAM" if r_idx % 2 == 0 else "NU",
                    cccd=f"001{res_id:09d}",
                    phone=f"08{res_id:08d}",
                    is_head=(r_idx == 0),
                    relationship_to_head="Chủ hộ" if r_idx == 0 else "Thành viên",
                    residence_status="THUONG_TRU",
                    is_deleted=False,
                )
            )
    db_session.bulk_save_objects(bulk_residents)
    db_session.commit()

    try:
        # Measure response time on multiple realistic query patterns
        test_queries = ["BENCH_0500", "001000012500", "0900000500", "Cư Dân Bench 10500"]
        for q in test_queries:
            start_time = time.perf_counter()
            res = client.get(f"/search?q={q}&limit=10", headers=headers)
            elapsed_time = time.perf_counter() - start_time

            assert res.status_code == 200
            data = res.json()
            assert len(data["items"]) >= 1

            # NFR-005 & AC-23.1 Assertion: response time must be <= 1.0s
            assert elapsed_time <= 1.0, f"Query '{q}' took {elapsed_time:.3f}s, exceeding 1.0s limit (AC-23.1)"

    finally:
        # Clean up benchmark data
        db_session.query(Resident).filter(Resident.id >= 10000).delete(synchronize_session=False)
        db_session.query(Household).filter(Household.id >= 1000).delete(synchronize_session=False)
        db_session.commit()
