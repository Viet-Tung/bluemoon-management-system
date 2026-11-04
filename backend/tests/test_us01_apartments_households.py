import uuid
import pytest
from sqlalchemy import text

from app.core.security import create_access_token, get_password_hash
from app.models.user import User


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================

@pytest.fixture(autouse=True)
def clean_tables(db_session):
    """Ensure database tables related to US-01 are clean before and after each test."""
    def _do_clean():
        try:
            db_session.execute(text("DELETE FROM apartment_occupancies"))
            db_session.execute(text("DELETE FROM residents"))
            db_session.execute(text("DELETE FROM households"))
            db_session.execute(text("DELETE FROM apartments"))
            db_session.commit()
        except Exception:
            db_session.rollback()

    _do_clean()
    yield
    _do_clean()


def make_token(
    role: str = "ADMIN",
    user_id: str = "1",
    username: str = "admin_test",
    must_change_password: bool = False,
    household_id: int | None = None
) -> dict:
    """Helper to create authorization header with JWT token."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "must_change_password": must_change_password
    }
    if household_id is not None:
        payload["household_id"] = household_id
    token = create_access_token(payload)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_accountant(db_session):
    """Authorization header for ACCOUNTANT user (user_id=2)."""
    return make_token(role="ACCOUNTANT", user_id="2", username="accountant_test")


@pytest.fixture
def auth_headers_treasurer(db_session):
    """Authorization header for TREASURER user."""
    u = db_session.query(User).filter_by(role_id=3).first()
    if not u:
        u = User(
            id=5,
            username="treasurer_test",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test",
            email="treasurer@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False
        )
        db_session.add(u)
        db_session.commit()
    return make_token(role="TREASURER", user_id=str(u.id), username=u.username)


@pytest.fixture
def auth_headers_pwd_change(db_session):
    """Authorization header for an ADMIN user with must_change_password=True."""
    u = db_session.query(User).filter_by(username="pwd_change_admin").first()
    if not u:
        u = User(
            id=6,
            username="pwd_change_admin",
            password_hash=get_password_hash("AdminPass123!"),
            full_name="Quản Trị Phải Đổi Pass",
            email="pwd_admin@bluemoon.local",
            role_id=1,
            is_active=True,
            must_change_password=True
        )
        db_session.add(u)
        db_session.commit()
    return make_token(role="ADMIN", user_id=str(u.id), username=u.username, must_change_password=True)


def gen_code(prefix: str = "P") -> str:
    """Generate unique code to avoid any test collision."""
    return f"{prefix}.{uuid.uuid4().hex[:6].upper()}"


# =============================================================================
# 1. POST /api/v1/apartments (Tạo căn hộ mới)
# =============================================================================

class TestCreateApartment:
    def test_post_apartment_success_minimal(self, client, auth_headers_admin):
        """Happy path: Create apartment with only required fields (code, floor, area_m2)."""
        code = gen_code("P")
        payload = {"code": code, "floor": 10, "area_m2": 72.5}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == code
        assert data["floor"] == 10
        assert data["area_m2"] == 72.5
        assert data["status"] == "ACTIVE"
        assert "id" in data
        assert "created_at" in data

    def test_post_apartment_success_all_fields(self, client, auth_headers_admin):
        """Happy path: Create apartment with optional note field."""
        code = gen_code("P")
        payload = {"code": code, "floor": 5, "area_m2": 85.0, "note": "Căn góc view đẹp"}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["note"] == "Căn góc view đẹp"

    def test_post_apartment_ground_floor_zero(self, client, auth_headers_admin):
        """Boundary: floor=0 is valid (minimum 0)."""
        code = gen_code("G")
        payload = {"code": code, "floor": 0, "area_m2": 150.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["floor"] == 0

    def test_post_apartment_high_floor(self, client, auth_headers_admin):
        """Boundary: high floor e.g. floor=50."""
        code = gen_code("PH")
        payload = {"code": code, "floor": 50, "area_m2": 250.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["floor"] == 50

    def test_post_apartment_decimal_area(self, client, auth_headers_admin):
        """Area precision: area_m2 with 2 decimal places."""
        code = gen_code("P")
        payload = {"code": code, "floor": 12, "area_m2": 68.75}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["area_m2"] == 68.75

    def test_post_apartment_vietnamese_unicode_note(self, client, auth_headers_admin):
        """Unicode support in note."""
        code = gen_code("P")
        payload = {"code": code, "floor": 7, "area_m2": 60.0, "note": "Căn hộ tiêu chuẩn BQT bàn giao"}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["note"] == "Căn hộ tiêu chuẩn BQT bàn giao"

    def test_post_apartment_duplicate_code_conflict(self, client, auth_headers_admin):
        """Conflict 409: DUPLICATE_APARTMENT_CODE when creating identical code."""
        code = gen_code("DUP")
        payload = {"code": code, "floor": 8, "area_m2": 65.0}
        resp1 = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp1.status_code == 201

        resp2 = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp2.status_code == 409
        err = resp2.json()
        assert err["code"] == "DUPLICATE_APARTMENT_CODE"

    def test_post_apartment_missing_code(self, client, auth_headers_admin):
        """Validation 400: Missing required code field."""
        payload = {"floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_empty_code(self, client, auth_headers_admin):
        """Validation 400: Empty string code."""
        payload = {"code": "", "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_whitespace_code(self, client, auth_headers_admin):
        """Validation 400: Whitespace only code."""
        payload = {"code": "   ", "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_missing_floor(self, client, auth_headers_admin):
        """Validation 400: Missing required floor field."""
        payload = {"code": gen_code("P"), "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_negative_floor(self, client, auth_headers_admin):
        """Validation 400: Negative floor (minimum is 0)."""
        payload = {"code": gen_code("P"), "floor": -1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_floor_wrong_type(self, client, auth_headers_admin):
        """Validation 400: String passed for floor integer."""
        payload = {"code": gen_code("P"), "floor": "invalid", "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_missing_area(self, client, auth_headers_admin):
        """Validation 400: Missing required area_m2 field."""
        payload = {"code": gen_code("P"), "floor": 2}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_zero_area(self, client, auth_headers_admin):
        """Validation 400: area_m2=0 (AC-01.1: area > 0, exclusiveMinimum)."""
        payload = {"code": gen_code("P"), "floor": 2, "area_m2": 0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_negative_area(self, client, auth_headers_admin):
        """Validation 400: Negative area_m2."""
        payload = {"code": gen_code("P"), "floor": 2, "area_m2": -45.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_area_wrong_type(self, client, auth_headers_admin):
        """Validation 400: Non-numeric area."""
        payload = {"code": gen_code("P"), "floor": 2, "area_m2": "fifty"}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_empty_body(self, client, auth_headers_admin):
        """Validation 400: Empty JSON object."""
        resp = client.post("/api/v1/apartments", json={}, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_post_apartment_unauthenticated(self, client):
        """RBAC 401: Request without Authorization header."""
        payload = {"code": gen_code("P"), "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload)
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_post_apartment_invalid_token(self, client):
        """RBAC 401: Invalid JWT token."""
        headers = {"Authorization": "Bearer invalid.token.string"}
        payload = {"code": gen_code("P"), "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=headers)
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_post_apartment_forbidden_accountant(self, client, auth_headers_accountant):
        """RBAC 403: Role ACCOUNTANT cannot create apartment."""
        payload = {"code": gen_code("P"), "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_accountant)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_post_apartment_forbidden_treasurer(self, client, auth_headers_treasurer):
        """RBAC 403: Role TREASURER cannot create apartment."""
        payload = {"code": gen_code("P"), "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_treasurer)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_post_apartment_forbidden_resident(self, client, auth_headers_resident_101):
        """RBAC 403: Role RESIDENT cannot create apartment."""
        payload = {"code": gen_code("P"), "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_resident_101)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_post_apartment_password_change_required(self, client, auth_headers_pwd_change):
        """RBAC 403: must_change_password=True blocks access with PASSWORD_CHANGE_REQUIRED."""
        payload = {"code": gen_code("P"), "floor": 1, "area_m2": 50.0}
        resp = client.post("/api/v1/apartments", json=payload, headers=auth_headers_pwd_change)
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 2. GET /api/v1/apartments (Danh sách căn hộ)
# =============================================================================

class TestListApartments:
    def test_list_apartments_admin_success(self, client, auth_headers_admin):
        """Happy path: ADMIN lists apartments, returns ApartmentPage schema."""
        client.post("/api/v1/apartments", json={"code": gen_code("L1"), "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        resp = client.get("/api/v1/apartments", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_apartments_accountant_success(self, client, auth_headers_admin, auth_headers_accountant):
        """Happy path: ACCOUNTANT has read permission for apartments."""
        client.post("/api/v1/apartments", json={"code": gen_code("L2"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        resp = client.get("/api/v1/apartments", headers=auth_headers_accountant)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_apartments_pagination_defaults(self, client, auth_headers_admin):
        """Pagination: Default page=1, page_size=20."""
        resp = client.get("/api/v1/apartments", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_apartments_pagination_custom_page_and_size(self, client, auth_headers_admin):
        """Pagination: Custom page=1, page_size=2."""
        for i in range(3):
            client.post("/api/v1/apartments", json={"code": gen_code(f"P{i}"), "floor": 10 + i, "area_m2": 55.0}, headers=auth_headers_admin)
        resp = client.get("/api/v1/apartments?page=1&page_size=2", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2
        assert data["total"] >= 3

    def test_list_apartments_filter_by_floor(self, client, auth_headers_admin):
        """Filter: Query param floor filters accurately."""
        c1 = gen_code("F3")
        c2 = gen_code("F4")
        client.post("/api/v1/apartments", json={"code": c1, "floor": 3, "area_m2": 50.0}, headers=auth_headers_admin)
        client.post("/api/v1/apartments", json={"code": c2, "floor": 4, "area_m2": 50.0}, headers=auth_headers_admin)

        resp = client.get("/api/v1/apartments?floor=3", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(it["floor"] == 3 for it in items)
        codes = [it["code"] for it in items]
        assert c1 in codes
        assert c2 not in codes

    def test_list_apartments_filter_by_status_active(self, client, auth_headers_admin):
        """Filter: Query param status=ACTIVE."""
        c = gen_code("ACT")
        client.post("/api/v1/apartments", json={"code": c, "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        resp = client.get("/api/v1/apartments?status=ACTIVE", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(it["status"] == "ACTIVE" for it in items)

    def test_list_apartments_filter_by_status_inactive(self, client, auth_headers_admin):
        """Filter: Query param status=INACTIVE after deactivating an apartment."""
        c = gen_code("INACT")
        res = client.post("/api/v1/apartments", json={"code": c, "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        client.patch(f"/api/v1/apartments/{apt_id}", json={"status": "INACTIVE"}, headers=auth_headers_admin)

        resp = client.get("/api/v1/apartments?status=INACTIVE", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(it["id"] == apt_id for it in items)
        assert all(it["status"] == "INACTIVE" for it in items)

    def test_list_apartments_filter_floor_no_results(self, client, auth_headers_admin):
        """Filter: Non-existent floor returns empty items with total=0."""
        resp = client.get("/api/v1/apartments?floor=9999", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_apartments_invalid_page_zero(self, client, auth_headers_admin):
        """Validation 400: page=0 is invalid (minimum 1)."""
        resp = client.get("/api/v1/apartments?page=0", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_apartments_invalid_page_negative(self, client, auth_headers_admin):
        """Validation 400: page=-1 is invalid."""
        resp = client.get("/api/v1/apartments?page=-1", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_apartments_invalid_page_size_zero(self, client, auth_headers_admin):
        """Validation 400: page_size=0 is invalid (minimum 1)."""
        resp = client.get("/api/v1/apartments?page_size=0", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_apartments_invalid_page_size_exceeds_max(self, client, auth_headers_admin):
        """Validation 400: page_size=101 exceeds maximum (100)."""
        resp = client.get("/api/v1/apartments?page_size=101", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_apartments_invalid_status_enum(self, client, auth_headers_admin):
        """Validation 400: Invalid enum value for status."""
        resp = client.get("/api/v1/apartments?status=UNKNOWN_STATUS", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_apartments_unauthenticated(self, client):
        """RBAC 401: Missing token."""
        resp = client.get("/api/v1/apartments")
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_list_apartments_forbidden_treasurer(self, client, auth_headers_treasurer):
        """RBAC 403: TREASURER role has no permission to list apartments."""
        resp = client.get("/api/v1/apartments", headers=auth_headers_treasurer)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_list_apartments_forbidden_resident(self, client, auth_headers_resident_101):
        """RBAC 403: RESIDENT role has no permission to list apartments."""
        resp = client.get("/api/v1/apartments", headers=auth_headers_resident_101)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_list_apartments_password_change_required(self, client, auth_headers_pwd_change):
        """RBAC 403: PASSWORD_CHANGE_REQUIRED."""
        resp = client.get("/api/v1/apartments", headers=auth_headers_pwd_change)
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 3. GET /api/v1/apartments/{id} (Chi tiết căn hộ)
# =============================================================================

class TestGetApartmentById:
    def test_get_apartment_by_id_admin_success(self, client, auth_headers_admin):
        """Happy path: ADMIN retrieves apartment detail by ID."""
        code = gen_code("G1")
        res = client.post("/api/v1/apartments", json={"code": code, "floor": 3, "area_m2": 65.0, "note": "Ghi chú test"}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.get(f"/api/v1/apartments/{apt_id}", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == apt_id
        assert data["code"] == code
        assert data["floor"] == 3
        assert data["area_m2"] == 65.0
        assert data["status"] == "ACTIVE"
        assert data["note"] == "Ghi chú test"
        assert "created_at" in data

    def test_get_apartment_by_id_accountant_success(self, client, auth_headers_admin, auth_headers_accountant):
        """Happy path: ACCOUNTANT retrieves apartment detail."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("G2"), "floor": 4, "area_m2": 70.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.get(f"/api/v1/apartments/{apt_id}", headers=auth_headers_accountant)
        assert resp.status_code == 200
        assert resp.json()["id"] == apt_id

    def test_get_apartment_by_id_not_found(self, client, auth_headers_admin):
        """Not found 404: Non-existent apartment ID."""
        resp = client.get("/api/v1/apartments/999999", headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_get_apartment_by_id_invalid_type(self, client, auth_headers_admin):
        """Path param validation: Non-numeric string ID returns 404 as route/resource not found."""
        resp = client.get("/api/v1/apartments/invalid_id", headers=auth_headers_admin)
        assert resp.status_code == 404

    def test_get_apartment_by_id_unauthenticated(self, client, auth_headers_admin):
        """RBAC 401: Unauthenticated request."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("G3"), "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.get(f"/api/v1/apartments/{apt_id}")
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_get_apartment_by_id_forbidden_treasurer(self, client, auth_headers_admin, auth_headers_treasurer):
        """RBAC 403: TREASURER role forbidden."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("G4"), "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.get(f"/api/v1/apartments/{apt_id}", headers=auth_headers_treasurer)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_get_apartment_by_id_forbidden_resident(self, client, auth_headers_admin, auth_headers_resident_101):
        """RBAC 403: RESIDENT role forbidden."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("G5"), "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.get(f"/api/v1/apartments/{apt_id}", headers=auth_headers_resident_101)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_get_apartment_by_id_password_change_required(self, client, auth_headers_admin, auth_headers_pwd_change):
        """RBAC 403: PASSWORD_CHANGE_REQUIRED."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("G6"), "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.get(f"/api/v1/apartments/{apt_id}", headers=auth_headers_pwd_change)
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 4. PATCH /api/v1/apartments/{id} (Cập nhật căn hộ)
# =============================================================================

class TestPatchApartment:
    def test_patch_apartment_area_success(self, client, auth_headers_admin):
        """Happy path: Update area_m2."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U1"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": 65.5}, headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.json()["area_m2"] == 65.5

    def test_patch_apartment_floor_success(self, client, auth_headers_admin):
        """Happy path: Update floor."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U2"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"floor": 8}, headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.json()["floor"] == 8

    def test_patch_apartment_status_to_inactive_success(self, client, auth_headers_admin):
        """Happy path: Update status to INACTIVE (Soft deactivation - no hard delete)."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U3"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"status": "INACTIVE"}, headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.json()["status"] == "INACTIVE"

    def test_patch_apartment_note_success(self, client, auth_headers_admin):
        """Happy path: Update note."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U4"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"note": "Đã sửa đổi ghi chú"}, headers=auth_headers_admin)
        assert resp.status_code == 200
        assert resp.json()["note"] == "Đã sửa đổi ghi chú"

    def test_patch_apartment_multiple_fields_success(self, client, auth_headers_admin):
        """Happy path: Update floor, area_m2, note, and status simultaneously."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U5"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        payload = {"floor": 15, "area_m2": 95.0, "status": "INACTIVE", "note": "Căn hộ sửa chữa lớn"}
        resp = client.patch(f"/api/v1/apartments/{apt_id}", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["floor"] == 15
        assert data["area_m2"] == 95.0
        assert data["status"] == "INACTIVE"
        assert data["note"] == "Căn hộ sửa chữa lớn"

    def test_patch_apartment_zero_area_fails(self, client, auth_headers_admin):
        """Validation 400: area_m2=0 is invalid (exclusiveMinimum)."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U6"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": 0}, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_patch_apartment_negative_area_fails(self, client, auth_headers_admin):
        """Validation 400: Negative area_m2 is invalid."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U7"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": -20.0}, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_patch_apartment_negative_floor_fails(self, client, auth_headers_admin):
        """Validation 400: Negative floor is invalid."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U8"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"floor": -5}, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_patch_apartment_invalid_status_fails(self, client, auth_headers_admin):
        """Validation 400: Invalid enum for status."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U9"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"status": "DELETED"}, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_patch_apartment_not_found(self, client, auth_headers_admin):
        """Not found 404: Updating non-existent apartment ID."""
        resp = client.patch("/api/v1/apartments/999999", json={"area_m2": 70.0}, headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_patch_apartment_unauthenticated(self, client, auth_headers_admin):
        """RBAC 401: Unauthenticated request."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U10"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": 70.0})
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_patch_apartment_forbidden_accountant(self, client, auth_headers_admin, auth_headers_accountant):
        """RBAC 403: ACCOUNTANT role cannot modify apartment."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U11"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": 70.0}, headers=auth_headers_accountant)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_patch_apartment_forbidden_treasurer(self, client, auth_headers_admin, auth_headers_treasurer):
        """RBAC 403: TREASURER role cannot modify apartment."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U12"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": 70.0}, headers=auth_headers_treasurer)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_patch_apartment_forbidden_resident(self, client, auth_headers_admin, auth_headers_resident_101):
        """RBAC 403: RESIDENT role cannot modify apartment."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U13"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": 70.0}, headers=auth_headers_resident_101)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_patch_apartment_password_change_required(self, client, auth_headers_admin, auth_headers_pwd_change):
        """RBAC 403: PASSWORD_CHANGE_REQUIRED."""
        res = client.post("/api/v1/apartments", json={"code": gen_code("U14"), "floor": 2, "area_m2": 60.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]
        resp = client.patch(f"/api/v1/apartments/{apt_id}", json={"area_m2": 70.0}, headers=auth_headers_pwd_change)
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 5. POST /api/v1/households (Tạo hộ gia đình mới & sinh tài khoản cư dân)
# =============================================================================

class TestCreateHousehold:
    def test_create_household_without_apartment_success(self, client, auth_headers_admin):
        """Happy path: Create household without apartment (apartment_id null), auto creates resident account."""
        h_code = gen_code("HO")
        payload = {"household_code": h_code}
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["household_code"] == h_code
        assert data["status"] == "ACTIVE"
        assert data["apartment_id"] is None
        assert "resident_account" in data
        assert "username" in data["resident_account"]
        assert "temporary_password" in data["resident_account"]

    def test_create_household_with_apartment_success(self, client, auth_headers_admin):
        """Happy path: Create household linked to an existing apartment."""
        apt_code = gen_code("P")
        res_apt = client.post("/api/v1/apartments", json={"code": apt_code, "floor": 5, "area_m2": 80.0}, headers=auth_headers_admin)
        apt_id = res_apt.json()["id"]

        h_code = gen_code("HO")
        payload = {"household_code": h_code, "apartment_id": apt_id}
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["apartment_id"] == apt_id
        assert data["apartment_code"] == apt_code
        assert data["floor"] == 5
        assert data["area_m2"] == 80.0

    def test_create_household_with_head_resident_male(self, client, auth_headers_admin):
        """Happy path: Create household with head resident (gender=NAM)."""
        h_code = gen_code("HO")
        payload = {
            "household_code": h_code,
            "head": {
                "full_name": "Trần Văn Nam",
                "date_of_birth": "1985-06-15",
                "gender": "NAM",
                "cccd": "001085001234",
                "phone": "0912345678",
                "email": "nam.tran@example.com",
                "is_head": True
            }
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["head_name"] == "Trần Văn Nam"
        assert data["head_phone"] == "0912345678"
        assert data["member_count"] == 1

    def test_create_household_with_head_resident_female(self, client, auth_headers_admin):
        """Happy path: Create household with head resident (gender=NU)."""
        h_code = gen_code("HO")
        payload = {
            "household_code": h_code,
            "head": {
                "full_name": "Lê Thị Hoa",
                "date_of_birth": "1990-11-20",
                "gender": "NU",
                "cccd": "001190005678",
                "phone": "0987654321",
                "is_head": True
            }
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["head_name"] == "Lê Thị Hoa"

    def test_create_household_with_head_resident_other_gender(self, client, auth_headers_admin):
        """Happy path: Create household with head resident (gender=KHAC)."""
        h_code = gen_code("HO")
        payload = {
            "household_code": h_code,
            "head": {
                "full_name": "Nguyễn Hoàng Anh",
                "date_of_birth": "1998-01-01",
                "gender": "KHAC",
                "is_head": True
            }
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["head_name"] == "Nguyễn Hoàng Anh"

    def test_create_household_with_contact_info(self, client, auth_headers_admin):
        """Happy path: Create household with contact phone, email, and note."""
        h_code = gen_code("HO")
        payload = {
            "household_code": h_code,
            "contact_phone": "0901234567",
            "contact_email": "household@bluemoon.local",
            "note": "Hộ mới chuyển vào"
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["contact_phone"] == "0901234567"
        assert data["contact_email"] == "household@bluemoon.local"
        assert data["note"] == "Hộ mới chuyển vào"

    def test_create_household_with_custom_start_date(self, client, auth_headers_admin):
        """Happy path: Custom occupancy_start_date."""
        h_code = gen_code("HO")
        payload = {
            "household_code": h_code,
            "occupancy_start_date": "2026-02-01"
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201

    def test_create_household_generates_resident_account(self, client, auth_headers_admin):
        """D-12 Requirement: Creating household automatically provisions resident account."""
        h_code = gen_code("HO")
        resp = client.post("/api/v1/households", json={"household_code": h_code}, headers=auth_headers_admin)
        assert resp.status_code == 201
        acc = resp.json().get("resident_account")
        assert acc is not None
        assert isinstance(acc["username"], str) and len(acc["username"]) > 0
        assert isinstance(acc["temporary_password"], str) and len(acc["temporary_password"]) >= 8

    def test_create_household_duplicate_code_conflict(self, client, auth_headers_admin):
        """Conflict 409: DUPLICATE_HOUSEHOLD_CODE when household_code already exists."""
        h_code = gen_code("HO_DUP")
        resp1 = client.post("/api/v1/households", json={"household_code": h_code}, headers=auth_headers_admin)
        assert resp1.status_code == 201

        resp2 = client.post("/api/v1/households", json={"household_code": h_code}, headers=auth_headers_admin)
        assert resp2.status_code == 409
        assert resp2.json()["code"] == "DUPLICATE_HOUSEHOLD_CODE"

    def test_create_household_apartment_occupied_conflict(self, client, auth_headers_admin):
        """Conflict 409: APARTMENT_OCCUPIED when assigning an apartment that is already actively occupied."""
        res_apt = client.post("/api/v1/apartments", json={"code": gen_code("P"), "floor": 1, "area_m2": 50.0}, headers=auth_headers_admin)
        apt_id = res_apt.json()["id"]

        h1 = client.post("/api/v1/households", json={"household_code": gen_code("H1"), "apartment_id": apt_id}, headers=auth_headers_admin)
        assert h1.status_code == 201

        h2 = client.post("/api/v1/households", json={"household_code": gen_code("H2"), "apartment_id": apt_id}, headers=auth_headers_admin)
        assert h2.status_code == 409
        assert h2.json()["code"] == "APARTMENT_OCCUPIED"

    def test_create_household_duplicate_cccd_conflict(self, client, auth_headers_admin):
        """Conflict 409: DUPLICATE_CCCD when head resident has identical CCCD as an existing resident."""
        cccd = "001099887766"
        p1 = {
            "household_code": gen_code("H1"),
            "head": {"full_name": "Người A", "date_of_birth": "1990-01-01", "gender": "NAM", "cccd": cccd, "is_head": True}
        }
        res1 = client.post("/api/v1/households", json=p1, headers=auth_headers_admin)
        assert res1.status_code == 201

        p2 = {
            "household_code": gen_code("H2"),
            "head": {"full_name": "Người B", "date_of_birth": "1992-02-02", "gender": "NAM", "cccd": cccd, "is_head": True}
        }
        res2 = client.post("/api/v1/households", json=p2, headers=auth_headers_admin)
        assert res2.status_code == 409
        assert res2.json()["code"] == "DUPLICATE_CCCD"

    def test_create_household_nonexistent_apartment_not_found(self, client, auth_headers_admin):
        """Not found 404: Linking to apartment_id that does not exist."""
        payload = {"household_code": gen_code("HO"), "apartment_id": 999999}
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_create_household_missing_code(self, client, auth_headers_admin):
        """Validation 400: Missing required household_code."""
        payload = {"contact_phone": "0912345678"}
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_empty_code(self, client, auth_headers_admin):
        """Validation 400: Empty household_code string."""
        payload = {"household_code": ""}
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_invalid_email(self, client, auth_headers_admin):
        """Validation 400: Malformed contact_email format."""
        payload = {"household_code": gen_code("HO"), "contact_email": "not-a-valid-email"}
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_invalid_start_date_format(self, client, auth_headers_admin):
        """Validation 400: Invalid date format for occupancy_start_date."""
        payload = {"household_code": gen_code("HO"), "occupancy_start_date": "2026/01/01"}
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_head_missing_fullname(self, client, auth_headers_admin):
        """Validation 400: Head resident missing required full_name."""
        payload = {
            "household_code": gen_code("HO"),
            "head": {"date_of_birth": "1990-01-01", "gender": "NAM"}
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_head_missing_dob(self, client, auth_headers_admin):
        """Validation 400: Head resident missing required date_of_birth."""
        payload = {
            "household_code": gen_code("HO"),
            "head": {"full_name": "Nguyễn Văn A", "gender": "NAM"}
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_head_missing_gender(self, client, auth_headers_admin):
        """Validation 400: Head resident missing required gender."""
        payload = {
            "household_code": gen_code("HO"),
            "head": {"full_name": "Nguyễn Văn A", "date_of_birth": "1990-01-01"}
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_head_invalid_gender(self, client, auth_headers_admin):
        """Validation 400: Head resident invalid enum for gender."""
        payload = {
            "household_code": gen_code("HO"),
            "head": {"full_name": "Nguyễn Văn A", "date_of_birth": "1990-01-01", "gender": "UNKNOWN"}
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_head_invalid_cccd_short(self, client, auth_headers_admin):
        """Validation 400: CCCD < 9 digits pattern failure."""
        payload = {
            "household_code": gen_code("HO"),
            "head": {"full_name": "Nguyễn Văn A", "date_of_birth": "1990-01-01", "gender": "NAM", "cccd": "12345"}
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_head_invalid_cccd_long(self, client, auth_headers_admin):
        """Validation 400: CCCD > 12 digits pattern failure."""
        payload = {
            "household_code": gen_code("HO"),
            "head": {"full_name": "Nguyễn Văn A", "date_of_birth": "1990-01-01", "gender": "NAM", "cccd": "123456789012345"}
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_head_invalid_cccd_letters(self, client, auth_headers_admin):
        """Validation 400: CCCD containing alphabetic letters."""
        payload = {
            "household_code": gen_code("HO"),
            "head": {"full_name": "Nguyễn Văn A", "date_of_birth": "1990-01-01", "gender": "NAM", "cccd": "00109012345A"}
        }
        resp = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_household_unauthenticated(self, client):
        """RBAC 401: Unauthenticated request."""
        resp = client.post("/api/v1/households", json={"household_code": gen_code("HO")})
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_create_household_forbidden_accountant(self, client, auth_headers_accountant):
        """RBAC 403: Role ACCOUNTANT cannot create household."""
        resp = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_accountant)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_create_household_forbidden_treasurer(self, client, auth_headers_treasurer):
        """RBAC 403: Role TREASURER cannot create household."""
        resp = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_treasurer)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_create_household_forbidden_resident(self, client, auth_headers_resident_101):
        """RBAC 403: Role RESIDENT cannot create household."""
        resp = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_resident_101)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_create_household_password_change_required(self, client, auth_headers_pwd_change):
        """RBAC 403: PASSWORD_CHANGE_REQUIRED."""
        resp = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_pwd_change)
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 6. GET /api/v1/households (Danh sách hộ gia đình)
# =============================================================================

class TestListHouseholds:
    def test_list_households_admin_success(self, client, auth_headers_admin):
        """Happy path: ADMIN lists households, returns HouseholdPage."""
        client.post("/api/v1/households", json={"household_code": gen_code("HL1")}, headers=auth_headers_admin)
        resp = client.get("/api/v1/households", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_list_households_accountant_success(self, client, auth_headers_admin, auth_headers_accountant):
        """Happy path: ACCOUNTANT has read permission to list households."""
        client.post("/api/v1/households", json={"household_code": gen_code("HL2")}, headers=auth_headers_admin)
        resp = client.get("/api/v1/households", headers=auth_headers_accountant)
        assert resp.status_code == 200
        assert "items" in resp.json()

    def test_list_households_pagination_defaults(self, client, auth_headers_admin):
        """Pagination: Default page=1, page_size=20."""
        resp = client.get("/api/v1/households", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_households_pagination_custom(self, client, auth_headers_admin):
        """Pagination: Custom page=1, page_size=2."""
        for i in range(3):
            client.post("/api/v1/households", json={"household_code": gen_code(f"H{i}")}, headers=auth_headers_admin)
        resp = client.get("/api/v1/households?page=1&page_size=2", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2
        assert data["total"] >= 3

    def test_list_households_filter_by_status_active(self, client, auth_headers_admin):
        """Filter: status=ACTIVE."""
        client.post("/api/v1/households", json={"household_code": gen_code("H_ACT")}, headers=auth_headers_admin)
        resp = client.get("/api/v1/households?status=ACTIVE", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(it["status"] == "ACTIVE" for it in items)

    def test_list_households_filter_by_status_inactive(self, client, auth_headers_admin):
        """Filter: status=INACTIVE."""
        resp = client.get("/api/v1/households?status=INACTIVE", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(it["status"] == "INACTIVE" for it in items)

    def test_list_households_search_query_code(self, client, auth_headers_admin):
        """Search query: Matches household_code."""
        target_code = gen_code("SEARCH_TARGET")
        client.post("/api/v1/households", json={"household_code": target_code}, headers=auth_headers_admin)
        client.post("/api/v1/households", json={"household_code": gen_code("OTHER")}, headers=auth_headers_admin)

        resp = client.get(f"/api/v1/households?q={target_code}", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(it["household_code"] == target_code for it in items)

    def test_list_households_search_query_phone(self, client, auth_headers_admin):
        """Search query: Matches contact_phone."""
        h_code = gen_code("H_TEL")
        phone = "0988776655"
        client.post("/api/v1/households", json={"household_code": h_code, "contact_phone": phone}, headers=auth_headers_admin)

        resp = client.get(f"/api/v1/households?q={phone}", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(it["household_code"] == h_code for it in items)

    def test_list_households_search_no_results(self, client, auth_headers_admin):
        """Search query: No match returns empty items and total=0."""
        resp = client.get("/api/v1/households?q=NON_EXISTENT_QUERY_STRING_XYZ", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_households_invalid_page_zero(self, client, auth_headers_admin):
        """Validation 400: page=0 is invalid."""
        resp = client.get("/api/v1/households?page=0", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_households_invalid_page_negative(self, client, auth_headers_admin):
        """Validation 400: page=-1 is invalid."""
        resp = client.get("/api/v1/households?page=-1", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_households_invalid_page_size_zero(self, client, auth_headers_admin):
        """Validation 400: page_size=0 is invalid."""
        resp = client.get("/api/v1/households?page_size=0", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_households_invalid_page_size_exceeds_max(self, client, auth_headers_admin):
        """Validation 400: page_size=101 exceeds maximum (100)."""
        resp = client.get("/api/v1/households?page_size=101", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_households_invalid_status_enum(self, client, auth_headers_admin):
        """Validation 400: Invalid status enum value."""
        resp = client.get("/api/v1/households?status=ARCHIVED_STATUS", headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_list_households_unauthenticated(self, client):
        """RBAC 401: Missing token."""
        resp = client.get("/api/v1/households")
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_list_households_forbidden_treasurer(self, client, auth_headers_treasurer):
        """RBAC 403: Role TREASURER cannot list households."""
        resp = client.get("/api/v1/households", headers=auth_headers_treasurer)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_list_households_forbidden_resident(self, client, auth_headers_resident_101):
        """RBAC 403: Role RESIDENT cannot list households."""
        resp = client.get("/api/v1/households", headers=auth_headers_resident_101)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_list_households_password_change_required(self, client, auth_headers_pwd_change):
        """RBAC 403: PASSWORD_CHANGE_REQUIRED."""
        resp = client.get("/api/v1/households", headers=auth_headers_pwd_change)
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 7. GET /api/v1/households/{id} (Chi tiết hộ gia đình)
# =============================================================================

class TestGetHouseholdById:
    def test_get_household_by_id_admin_success(self, client, auth_headers_admin):
        """Happy path: ADMIN retrieves household detail."""
        h_code = gen_code("HO")
        res = client.post("/api/v1/households", json={"household_code": h_code, "note": "Hộ chi tiết"}, headers=auth_headers_admin)
        h_id = res.json()["id"]

        resp = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == h_id
        assert data["household_code"] == h_code
        assert data["status"] == "ACTIVE"
        assert data["note"] == "Hộ chi tiết"
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_household_by_id_accountant_success(self, client, auth_headers_admin, auth_headers_accountant):
        """Happy path: ACCOUNTANT retrieves household detail."""
        res = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_admin)
        h_id = res.json()["id"]

        resp = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_accountant)
        assert resp.status_code == 200
        assert resp.json()["id"] == h_id

    def test_get_household_by_id_with_head_resident_details(self, client, auth_headers_admin):
        """Happy path: Verify head_name, head_phone, member_count returned in details."""
        h_code = gen_code("HO")
        payload = {
            "household_code": h_code,
            "head": {
                "full_name": "Phạm Quốc Tuấn",
                "date_of_birth": "1980-05-10",
                "gender": "NAM",
                "cccd": "001080009988",
                "phone": "0911223344",
                "is_head": True
            }
        }
        res = client.post("/api/v1/households", json=payload, headers=auth_headers_admin)
        h_id = res.json()["id"]

        resp = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["head_name"] == "Phạm Quốc Tuấn"
        assert data["head_phone"] == "0911223344"
        assert data["member_count"] == 1
        assert data["head_resident_id"] is not None

    def test_get_household_by_id_with_apartment_details(self, client, auth_headers_admin):
        """Happy path: Verify apartment_code, floor, area_m2 returned when assigned."""
        apt_code = gen_code("P")
        res_apt = client.post("/api/v1/apartments", json={"code": apt_code, "floor": 8, "area_m2": 92.5}, headers=auth_headers_admin)
        apt_id = res_apt.json()["id"]

        res = client.post("/api/v1/households", json={"household_code": gen_code("HO"), "apartment_id": apt_id}, headers=auth_headers_admin)
        h_id = res.json()["id"]

        resp = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert data["apartment_id"] == apt_id
        assert data["apartment_code"] == apt_code
        assert data["floor"] == 8
        assert data["area_m2"] == 92.5

    def test_get_household_by_id_not_found(self, client, auth_headers_admin):
        """Not found 404: Non-existent household ID."""
        resp = client.get("/api/v1/households/999999", headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_get_household_by_id_invalid_id_type(self, client, auth_headers_admin):
        """Path param validation: Non-numeric ID in path parameter returns 404 as resource not found."""
        resp = client.get("/api/v1/households/not_an_id", headers=auth_headers_admin)
        assert resp.status_code == 404

    def test_get_household_by_id_unauthenticated(self, client, auth_headers_admin):
        """RBAC 401: Missing token."""
        res = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_admin)
        h_id = res.json()["id"]
        resp = client.get(f"/api/v1/households/{h_id}")
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHENTICATED"

    def test_get_household_by_id_forbidden_treasurer(self, client, auth_headers_admin, auth_headers_treasurer):
        """RBAC 403: Role TREASURER cannot access household details."""
        res = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_admin)
        h_id = res.json()["id"]
        resp = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_treasurer)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_get_household_by_id_forbidden_resident(self, client, auth_headers_admin, auth_headers_resident_101):
        """RBAC 403: Role RESIDENT cannot access admin household details (must use /portal/*)."""
        res = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_admin)
        h_id = res.json()["id"]
        resp = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_resident_101)
        assert resp.status_code == 403
        assert resp.json()["code"] == "FORBIDDEN"

    def test_get_household_by_id_password_change_required(self, client, auth_headers_admin, auth_headers_pwd_change):
        """RBAC 403: PASSWORD_CHANGE_REQUIRED."""
        res = client.post("/api/v1/households", json={"household_code": gen_code("HO")}, headers=auth_headers_admin)
        h_id = res.json()["id"]
        resp = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_pwd_change)
        assert resp.status_code == 403
        assert resp.json()["code"] == "PASSWORD_CHANGE_REQUIRED"


# =============================================================================
# 8. DOMAIN INVARIANTS & INTEGRATION (T-01, T-02, AC-01.1, AC-01.2, D-12)
# =============================================================================

class TestDomainInvariantsUS01:
    def test_domain_invariant_ac01_decoupled_entities(self, client, auth_headers_admin):
        """AC-01.2: Physical units (apartments) strictly decoupled from resident units (households).

        - An apartment can exist without any household.
        - A household can exist without any apartment.
        """
        # 1. Apartment exists independently
        apt_code = gen_code("ISO_APT")
        res_apt = client.post("/api/v1/apartments", json={"code": apt_code, "floor": 3, "area_m2": 60.0}, headers=auth_headers_admin)
        assert res_apt.status_code == 201
        apt_id = res_apt.json()["id"]

        # 2. Household exists independently
        h_code = gen_code("ISO_HO")
        res_h = client.post("/api/v1/households", json={"household_code": h_code}, headers=auth_headers_admin)
        assert res_h.status_code == 201
        h_id = res_h.json()["id"]

        # Check independence
        apt_detail = client.get(f"/api/v1/apartments/{apt_id}", headers=auth_headers_admin).json()
        assert apt_detail["code"] == apt_code

        h_detail = client.get(f"/api/v1/households/{h_id}", headers=auth_headers_admin).json()
        assert h_detail["apartment_id"] is None
        assert h_detail["apartment_code"] is None

    def test_domain_invariant_apartment_status_soft_deactivation(self, client, auth_headers_admin):
        """No hard delete invariant: Apartment status transitioned to INACTIVE remains preserved in database."""
        apt_code = gen_code("SOFT_DEL")
        res = client.post("/api/v1/apartments", json={"code": apt_code, "floor": 1, "area_m2": 55.0}, headers=auth_headers_admin)
        apt_id = res.json()["id"]

        # Deactivate
        patch_res = client.patch(f"/api/v1/apartments/{apt_id}", json={"status": "INACTIVE"}, headers=auth_headers_admin)
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "INACTIVE"

        # Still accessible by GET detail
        get_res = client.get(f"/api/v1/apartments/{apt_id}", headers=auth_headers_admin)
        assert get_res.status_code == 200
        assert get_res.json()["status"] == "INACTIVE"

