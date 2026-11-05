"""
Test Suite for User Story US-12: Quản lý danh mục khoản thu bắt buộc (Fee Catalog).

Scope of User Story US-12:
- GET /fee-types (List fee types, filter by status, fee_group, pagination)
- POST /fee-types (Create new fee type, enforce uniqueness, validate vehicle_type when calc_method is PER_VEHICLE)
- PATCH /fee-types/{id} (Update fee type details, cannot change code/calc_method when in use, validate inputs)

Standards:
- docs/openapi.yaml & docs/API_CONTRACT.md
- docs/backend_spec/sprint_1/SPRINT_1_BACKEND_SPEC.md (US-12)
"""

import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.user import User


# ==============================================================================
# Helper Functions & Fixtures for Authentication & Role-based Access Control
# ==============================================================================

def make_headers(
    role: str = "ADMIN",
    sub: str = "1",
    username: str = "admin_test",
    must_change_password: bool = False
):
    """Generate Authorization header with specified JWT payload."""
    token = create_access_token({
        "sub": str(sub),
        "username": username,
        "role": role,
        "must_change_password": must_change_password
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    return make_headers(role="ADMIN", sub="1", username="admin_test")


@pytest.fixture
def accountant_headers():
    return make_headers(role="ACCOUNTANT", sub="2", username="accountant_test")


@pytest.fixture
def treasurer_headers(db_session):
    treasurer = db_session.query(User).filter(User.username == "treasurer_test").first()
    if not treasurer:
        treasurer = User(
            id=5,
            username="treasurer_test",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test",
            email="treasurer@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False
        )
        db_session.add(treasurer)
        db_session.commit()
    return make_headers(role="TREASURER", sub=str(treasurer.id), username=treasurer.username)


@pytest.fixture
def resident_headers():
    return make_headers(role="RESIDENT", sub="3", username="resident_101")


@pytest.fixture
def pwd_change_required_headers(db_session):
    user = db_session.query(User).filter(User.must_change_password.is_(True)).first()
    if not user:
        user = User(
            username="admin_must_change_us12",
            password_hash=get_password_hash("AdminPass123!"),
            full_name="Admin Must Change",
            email="admin_change_12@bluemoon.local",
            role_id=1,
            is_active=True,
            must_change_password=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return make_headers(role="ADMIN", sub=str(user.id), username=user.username, must_change_password=True)



# ==============================================================================
# 1. RBAC & Authentication Tests (GET, POST, PATCH)
# ==============================================================================

def test_get_fee_types_unauthenticated(client):
    """GET /fee-types without token must return 401 UNAUTHENTICATED."""
    res = client.get("/fee-types")
    assert res.status_code == 401
    data = res.json()
    assert data.get("code") == "UNAUTHENTICATED"


def test_get_fee_types_invalid_token(client):
    """GET /fee-types with invalid token must return 401 UNAUTHENTICATED."""
    res = client.get("/fee-types", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert res.status_code == 401
    data = res.json()
    assert data.get("code") == "UNAUTHENTICATED"


def test_get_fee_types_forbidden_treasurer(client, treasurer_headers):
    """GET /fee-types called by TREASURER must return 403 FORBIDDEN."""
    res = client.get("/fee-types", headers=treasurer_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "FORBIDDEN"


def test_get_fee_types_forbidden_resident(client, resident_headers):
    """GET /fee-types called by RESIDENT must return 403 FORBIDDEN."""
    res = client.get("/fee-types", headers=resident_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "FORBIDDEN"


def test_get_fee_types_password_change_required(client, pwd_change_required_headers):
    """GET /fee-types called when must_change_password=True must return 403 PASSWORD_CHANGE_REQUIRED."""
    res = client.get("/fee-types", headers=pwd_change_required_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "PASSWORD_CHANGE_REQUIRED"


def test_post_fee_types_unauthenticated(client):
    """POST /fee-types without token must return 401 UNAUTHENTICATED."""
    payload = {
        "code": "PQL_TEST_AUTH",
        "name": "Phí quản lý test auth",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload)
    assert res.status_code == 401
    data = res.json()
    assert data.get("code") == "UNAUTHENTICATED"


def test_post_fee_types_invalid_token(client):
    """POST /fee-types with invalid token must return 401 UNAUTHENTICATED."""
    payload = {
        "code": "PQL_TEST_AUTH",
        "name": "Phí quản lý test auth",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers={"Authorization": "Bearer garbage"})
    assert res.status_code == 401
    data = res.json()
    assert data.get("code") == "UNAUTHENTICATED"


def test_post_fee_types_forbidden_treasurer(client, treasurer_headers):
    """POST /fee-types called by TREASURER must return 403 FORBIDDEN."""
    payload = {
        "code": "PQL_TEST_TREASURER",
        "name": "Phí quản lý test treasurer",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=treasurer_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "FORBIDDEN"


def test_post_fee_types_forbidden_resident(client, resident_headers):
    """POST /fee-types called by RESIDENT must return 403 FORBIDDEN."""
    payload = {
        "code": "PQL_TEST_RESIDENT",
        "name": "Phí quản lý test resident",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=resident_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "FORBIDDEN"


def test_post_fee_types_password_change_required(client, pwd_change_required_headers):
    """POST /fee-types called when must_change_password=True must return 403 PASSWORD_CHANGE_REQUIRED."""
    payload = {
        "code": "PQL_TEST_PWD",
        "name": "Phí quản lý test pwd",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=pwd_change_required_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "PASSWORD_CHANGE_REQUIRED"


def test_patch_fee_types_unauthenticated(client):
    """PATCH /fee-types/{id} without token must return 401 UNAUTHENTICATED."""
    res = client.patch("/fee-types/1", json={"name": "New Name"})
    assert res.status_code == 401
    data = res.json()
    assert data.get("code") == "UNAUTHENTICATED"


def test_patch_fee_types_invalid_token(client):
    """PATCH /fee-types/{id} with invalid token must return 401 UNAUTHENTICATED."""
    res = client.patch("/fee-types/1", json={"name": "New Name"}, headers={"Authorization": "Bearer bad"})
    assert res.status_code == 401
    data = res.json()
    assert data.get("code") == "UNAUTHENTICATED"


def test_patch_fee_types_forbidden_treasurer(client, treasurer_headers):
    """PATCH /fee-types/{id} called by TREASURER must return 403 FORBIDDEN."""
    res = client.patch("/fee-types/1", json={"name": "New Name"}, headers=treasurer_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "FORBIDDEN"


def test_patch_fee_types_forbidden_resident(client, resident_headers):
    """PATCH /fee-types/{id} called by RESIDENT must return 403 FORBIDDEN."""
    res = client.patch("/fee-types/1", json={"name": "New Name"}, headers=resident_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "FORBIDDEN"


def test_patch_fee_types_password_change_required(client, pwd_change_required_headers):
    """PATCH /fee-types/{id} called when must_change_password=True must return 403 PASSWORD_CHANGE_REQUIRED."""
    res = client.patch("/fee-types/1", json={"name": "New Name"}, headers=pwd_change_required_headers)
    assert res.status_code == 403
    data = res.json()
    assert data.get("code") == "PASSWORD_CHANGE_REQUIRED"


# ==============================================================================
# 2. POST /fee-types - Input Validation Errors (400 VALIDATION_ERROR)
# ==============================================================================

def test_post_fee_types_empty_body(client, admin_headers):
    """POST /fee-types with empty JSON body must return 400 VALIDATION_ERROR."""
    res = client.post("/fee-types", json={}, headers=admin_headers)
    assert res.status_code == 400
    data = res.json()
    assert data.get("code") == "VALIDATION_ERROR"


def test_post_fee_types_missing_code(client, admin_headers):
    """POST /fee-types missing required 'code' field must return 400 VALIDATION_ERROR."""
    payload = {
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_missing_name(client, admin_headers):
    """POST /fee-types missing required 'name' field must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_TEST_NAME",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_missing_fee_group(client, admin_headers):
    """POST /fee-types missing required 'fee_group' field must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_TEST_GROUP",
        "name": "Phí quản lý",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_missing_calc_method(client, admin_headers):
    """POST /fee-types missing required 'calc_method' field must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_TEST_CALC",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_missing_unit_label(client, admin_headers):
    """POST /fee-types missing required 'unit_label' field must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_TEST_UNIT",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_invalid_fee_group(client, admin_headers):
    """POST /fee-types with invalid fee_group enum value must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_INVALID_GRP",
        "name": "Phí quản lý",
        "fee_group": "UNKNOWN_GROUP",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_invalid_calc_method(client, admin_headers):
    """POST /fee-types with invalid calc_method enum value must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_INVALID_CALC",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "INVALID_CALC",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_invalid_cycle(client, admin_headers):
    """POST /fee-types with invalid cycle enum value must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_INVALID_CYCLE",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "cycle": "DAILY"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_due_day_zero(client, admin_headers):
    """POST /fee-types with due_day=0 (< minimum 1) must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_DUE_0",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "due_day": 0
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_due_day_negative(client, admin_headers):
    """POST /fee-types with due_day=-5 must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_DUE_NEG",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "due_day": -5
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_due_day_above_31(client, admin_headers):
    """POST /fee-types with due_day=32 (> maximum 31) must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_DUE_32",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "due_day": 32
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_due_day_large(client, admin_headers):
    """POST /fee-types with due_day=100 must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "PQL_DUE_100",
        "name": "Phí quản lý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "due_day": 100
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_invalid_vehicle_type(client, admin_headers):
    """POST /fee-types with invalid vehicle_type enum value must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "P_TRUCK",
        "name": "Phí xe tải",
        "fee_group": "PARKING",
        "calc_method": "PER_VEHICLE",
        "unit_label": "xe",
        "vehicle_type": "TRUCK"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_missing_vehicle_type_when_per_vehicle(client, admin_headers):
    """POST /fee-types with calc_method=PER_VEHICLE but vehicle_type missing must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "P_XE_KHONG_LOAI",
        "name": "Phí giữ xe thiếu loại xe",
        "fee_group": "PARKING",
        "calc_method": "PER_VEHICLE",
        "unit_label": "xe"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_post_fee_types_null_vehicle_type_when_per_vehicle(client, admin_headers):
    """POST /fee-types with calc_method=PER_VEHICLE and vehicle_type=None must return 400 VALIDATION_ERROR."""
    payload = {
        "code": "P_XE_NULL_LOAI",
        "name": "Phí giữ xe loại xe null",
        "fee_group": "PARKING",
        "calc_method": "PER_VEHICLE",
        "unit_label": "xe",
        "vehicle_type": None
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


# ==============================================================================
# 3. POST /fee-types - Happy Path, Calculations & Conflicts
# ==============================================================================

def test_create_fee_type_minimal_fields_admin(client, admin_headers):
    """POST /fee-types by ADMIN with minimal required fields succeeds with 201 Created."""
    payload = {
        "code": "PQL_MINIMAL_01",
        "name": "Phí quản lý cơ bản",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "PQL_MINIMAL_01"
    assert data["name"] == "Phí quản lý cơ bản"
    assert data["fee_group"] == "MANAGEMENT"
    assert data["calc_method"] == "PER_M2"
    assert data["unit_label"] == "m2"
    assert data["cycle"] == "MONTHLY"
    assert data["status"] == "ACTIVE"
    assert data["is_pass_through"] is False
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_fee_type_minimal_fields_accountant(client, accountant_headers):
    """POST /fee-types by ACCOUNTANT with minimal required fields succeeds with 201 Created."""
    payload = {
        "code": "PQL_ACC_01",
        "name": "Phí quản lý do kế toán tạo",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    res = client.post("/fee-types", json=payload, headers=accountant_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "PQL_ACC_01"
    assert data["status"] == "ACTIVE"


def test_create_fee_type_full_fields(client, admin_headers):
    """POST /fee-types with all optional fields provided succeeds with 201 Created."""
    payload = {
        "code": "P_XE_OTO_VIP",
        "name": "Phí gửi xe ô tô VIP",
        "fee_group": "PARKING",
        "calc_method": "PER_VEHICLE",
        "unit_label": "xe",
        "vehicle_type": "CAR",
        "is_pass_through": False,
        "provider_id": None,
        "cycle": "MONTHLY",
        "due_day": 10,
        "description": "Khoản phí trông giữ xe ô tô tầng hầm B1"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "P_XE_OTO_VIP"
    assert data["name"] == "Phí gửi xe ô tô VIP"
    assert data["fee_group"] == "PARKING"
    assert data["calc_method"] == "PER_VEHICLE"
    assert data["vehicle_type"] == "CAR"
    assert data["cycle"] == "MONTHLY"
    assert data["due_day"] == 10
    assert data["description"] == "Khoản phí trông giữ xe ô tô tầng hầm B1"
    assert data["status"] == "ACTIVE"


def test_create_fee_type_calc_method_per_household(client, admin_headers):
    """POST /fee-types with calc_method=PER_HOUSEHOLD succeeds."""
    payload = {
        "code": "PHI_AN_NINH_HO",
        "name": "Phí an ninh trật tự theo hộ",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_HOUSEHOLD",
        "unit_label": "hộ",
        "cycle": "MONTHLY",
        "due_day": 15
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["calc_method"] == "PER_HOUSEHOLD"
    assert data["unit_label"] == "hộ"


def test_create_fee_type_calc_method_per_person(client, admin_headers):
    """POST /fee-types with calc_method=PER_PERSON succeeds."""
    payload = {
        "code": "PHI_BE_BOI_NGUOI",
        "name": "Phí sử dụng bể bơi theo đầu người",
        "fee_group": "OTHER",
        "calc_method": "PER_PERSON",
        "unit_label": "người",
        "cycle": "MONTHLY",
        "due_day": 20
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["calc_method"] == "PER_PERSON"
    assert data["unit_label"] == "người"


def test_create_fee_type_calc_method_metered(client, admin_headers):
    """POST /fee-types with calc_method=METERED succeeds."""
    payload = {
        "code": "NUOC_SINH_HOAT",
        "name": "Tiền nước sinh hoạt",
        "fee_group": "UTILITY",
        "calc_method": "METERED",
        "unit_label": "m3",
        "cycle": "MONTHLY",
        "due_day": 25,
        "is_pass_through": True
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["calc_method"] == "METERED"
    assert data["unit_label"] == "m3"
    assert data["is_pass_through"] is True


def test_create_fee_type_per_vehicle_motorbike(client, admin_headers):
    """POST /fee-types with calc_method=PER_VEHICLE and vehicle_type=MOTORBIKE succeeds."""
    payload = {
        "code": "P_XE_MAY_01",
        "name": "Phí gửi xe máy",
        "fee_group": "PARKING",
        "calc_method": "PER_VEHICLE",
        "unit_label": "xe",
        "vehicle_type": "MOTORBIKE"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["vehicle_type"] == "MOTORBIKE"


def test_create_fee_type_per_vehicle_bicycle(client, admin_headers):
    """POST /fee-types with calc_method=PER_VEHICLE and vehicle_type=BICYCLE succeeds."""
    payload = {
        "code": "P_XE_DAP_01",
        "name": "Phí gửi xe đạp",
        "fee_group": "PARKING",
        "calc_method": "PER_VEHICLE",
        "unit_label": "xe",
        "vehicle_type": "BICYCLE"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["vehicle_type"] == "BICYCLE"


def test_create_fee_type_cycle_quarterly(client, admin_headers):
    """POST /fee-types with cycle=QUARTERLY succeeds."""
    payload = {
        "code": "PHI_BAO_TRI_QUY",
        "name": "Phí bảo trì định kỳ theo quý",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "cycle": "QUARTERLY"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["cycle"] == "QUARTERLY"


def test_create_fee_type_cycle_yearly(client, admin_headers):
    """POST /fee-types with cycle=YEARLY succeeds."""
    payload = {
        "code": "PHI_NIEN_LIEM_NAM",
        "name": "Phí niên liễm thường niên",
        "fee_group": "OTHER",
        "calc_method": "PER_HOUSEHOLD",
        "unit_label": "hộ",
        "cycle": "YEARLY"
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["cycle"] == "YEARLY"


def test_create_fee_type_boundary_due_day_min_1(client, admin_headers):
    """POST /fee-types with minimum valid boundary due_day=1 succeeds."""
    payload = {
        "code": "P_DUE_DAY_MIN",
        "name": "Phí ngày hạn mùng 1",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "due_day": 1
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["due_day"] == 1


def test_create_fee_type_boundary_due_day_max_31(client, admin_headers):
    """POST /fee-types with maximum valid boundary due_day=31 succeeds."""
    payload = {
        "code": "P_DUE_DAY_MAX",
        "name": "Phí ngày hạn ngày 31",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2",
        "due_day": 31
    }
    res = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res.status_code == 201
    assert res.json()["due_day"] == 31


def test_create_fee_type_duplicate_code_conflict(client, admin_headers):
    """POST /fee-types with duplicate 'code' must return 409 DUPLICATE_FEE_CODE."""
    payload = {
        "code": "PQL_DUPLICATE_CHECK",
        "name": "Phí quản lý kiểm tra trùng",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    # First create
    res1 = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res1.status_code == 201

    # Second create with identical code
    res2 = client.post("/fee-types", json=payload, headers=admin_headers)
    assert res2.status_code == 409
    data = res2.json()
    assert data.get("code") == "DUPLICATE_FEE_CODE"


def test_create_fee_type_duplicate_code_case_different(client, admin_headers):
    """POST /fee-types with duplicate code (case variations or exact) verifies conflict logic."""
    code = "FEE_DUP_TEST_01"
    payload1 = {
        "code": code,
        "name": "Khoản thu 1",
        "fee_group": "MANAGEMENT",
        "calc_method": "PER_M2",
        "unit_label": "m2"
    }
    payload2 = {
        "code": code,
        "name": "Khoản thu 2 tên khác",
        "fee_group": "OTHER",
        "calc_method": "PER_HOUSEHOLD",
        "unit_label": "hộ"
    }
    res1 = client.post("/fee-types", json=payload1, headers=admin_headers)
    assert res1.status_code == 201

    res2 = client.post("/fee-types", json=payload2, headers=admin_headers)
    assert res2.status_code == 409
    assert res2.json().get("code") == "DUPLICATE_FEE_CODE"


# ==============================================================================
# 4. GET /fee-types - Query Validation, Pagination, and Filtering
# ==============================================================================

def test_get_fee_types_success_default_pagination(client, admin_headers):
    """GET /fee-types without params returns 200 with default page=1, page_size=20."""
    res = client.get("/fee-types", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "page" in data
    assert "page_size" in data
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_get_fee_types_success_accountant(client, accountant_headers):
    """GET /fee-types by ACCOUNTANT succeeds with 200."""
    res = client.get("/fee-types", headers=accountant_headers)
    assert res.status_code == 200
    assert isinstance(res.json()["items"], list)


def test_get_fee_types_page_zero(client, admin_headers):
    """GET /fee-types with page=0 (< minimum 1) must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?page=0", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_page_negative(client, admin_headers):
    """GET /fee-types with page=-1 must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?page=-1", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_page_non_integer(client, admin_headers):
    """GET /fee-types with page=abc must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?page=abc", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_page_size_zero(client, admin_headers):
    """GET /fee-types with page_size=0 (< minimum 1) must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?page_size=0", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_page_size_negative(client, admin_headers):
    """GET /fee-types with page_size=-10 must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?page_size=-10", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_page_size_above_max(client, admin_headers):
    """GET /fee-types with page_size=101 (> maximum 100) must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?page_size=101", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_invalid_status_param(client, admin_headers):
    """GET /fee-types with invalid status query param must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?status=DELETED", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_invalid_fee_group_param(client, admin_headers):
    """GET /fee-types with invalid fee_group query param must return 400 VALIDATION_ERROR."""
    res = client.get("/fee-types?fee_group=INVALID_GROUP", headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_get_fee_types_filter_status_active(client, admin_headers):
    """GET /fee-types?status=ACTIVE returns only items with status ACTIVE."""
    # Ensure at least one active item is created
    client.post(
        "/fee-types",
        json={
            "code": "FILTER_ACT_01",
            "name": "Phí lọc active",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    res = client.get("/fee-types?status=ACTIVE", headers=admin_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert item["status"] == "ACTIVE"


def test_get_fee_types_filter_status_inactive(client, admin_headers):
    """GET /fee-types?status=INACTIVE returns only items with status INACTIVE."""
    res = client.get("/fee-types?status=INACTIVE", headers=admin_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    for item in items:
        assert item["status"] == "INACTIVE"


def test_get_fee_types_filter_fee_group_parking(client, admin_headers):
    """GET /fee-types?fee_group=PARKING returns only PARKING fee items."""
    client.post(
        "/fee-types",
        json={
            "code": "FILTER_PARK_01",
            "name": "Phí lọc parking",
            "fee_group": "PARKING",
            "calc_method": "PER_VEHICLE",
            "vehicle_type": "MOTORBIKE",
            "unit_label": "xe"
        },
        headers=admin_headers
    )
    res = client.get("/fee-types?fee_group=PARKING", headers=admin_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert item["fee_group"] == "PARKING"


def test_get_fee_types_filter_fee_group_utility(client, admin_headers):
    """GET /fee-types?fee_group=UTILITY returns only UTILITY fee items."""
    client.post(
        "/fee-types",
        json={
            "code": "FILTER_UTIL_01",
            "name": "Phí lọc tiện ích",
            "fee_group": "UTILITY",
            "calc_method": "METERED",
            "unit_label": "m3"
        },
        headers=admin_headers
    )
    res = client.get("/fee-types?fee_group=UTILITY", headers=admin_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert item["fee_group"] == "UTILITY"


def test_get_fee_types_filter_combined_status_and_group(client, admin_headers):
    """GET /fee-types?status=ACTIVE&fee_group=MANAGEMENT combines both filters accurately."""
    res = client.get("/fee-types?status=ACTIVE&fee_group=MANAGEMENT", headers=admin_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    for item in items:
        assert item["status"] == "ACTIVE"
        assert item["fee_group"] == "MANAGEMENT"


def test_get_fee_types_pagination_pages(client, admin_headers):
    """Verify pagination slices items according to page and page_size."""
    # Seed 3 items
    for i in range(1, 4):
        client.post(
            "/fee-types",
            json={
                "code": f"PAGE_FEE_{i}_{i*10}",
                "name": f"Fee for pagination {i}",
                "fee_group": "OTHER",
                "calc_method": "PER_M2",
                "unit_label": "m2"
            },
            headers=admin_headers
        )

    res_p1 = client.get("/fee-types?page=1&page_size=2", headers=admin_headers)
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["page"] == 1
    assert data_p1["page_size"] == 2
    assert len(data_p1["items"]) <= 2

    res_p2 = client.get("/fee-types?page=2&page_size=2", headers=admin_headers)
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert data_p2["page"] == 2
    assert data_p2["page_size"] == 2


def test_get_fee_types_boundary_page_size_max_100(client, admin_headers):
    """GET /fee-types?page_size=100 succeeds at maximum boundary."""
    res = client.get("/fee-types?page=1&page_size=100", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["page_size"] == 100


# ==============================================================================
# 5. PATCH /fee-types/{id} - Validation Errors, NotFound & Conflicts
# ==============================================================================

def test_patch_fee_type_not_found(client, admin_headers):
    """PATCH /fee-types/{id} with non-existent id must return 404 NOT_FOUND."""
    res = client.patch("/fee-types/99999999", json={"name": "Không tồn tại"}, headers=admin_headers)
    assert res.status_code == 404
    data = res.json()
    assert data.get("code") == "NOT_FOUND"


def test_patch_fee_type_invalid_id_format(client, admin_headers):
    """PATCH /fee-types/invalid_id must return 400 VALIDATION_ERROR or 422."""
    res = client.patch("/fee-types/not-an-integer", json={"name": "Tên mới"}, headers=admin_headers)
    assert res.status_code in [400, 404, 422]


def test_patch_fee_type_due_day_zero(client, admin_headers):
    """PATCH /fee-types/{id} with due_day=0 (< minimum 1) must return 400 VALIDATION_ERROR."""
    # Create a fee type first
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_DUE_0",
            "name": "Fee test due day 0",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"due_day": 0}, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_patch_fee_type_due_day_negative(client, admin_headers):
    """PATCH /fee-types/{id} with due_day=-1 must return 400 VALIDATION_ERROR."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_DUE_NEG",
            "name": "Fee test due day negative",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"due_day": -1}, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_patch_fee_type_due_day_above_31(client, admin_headers):
    """PATCH /fee-types/{id} with due_day=32 (> maximum 31) must return 400 VALIDATION_ERROR."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_DUE_32",
            "name": "Fee test due day 32",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"due_day": 32}, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


def test_patch_fee_type_invalid_cycle(client, admin_headers):
    """PATCH /fee-types/{id} with invalid cycle must return 400 VALIDATION_ERROR."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_BAD_CYCLE",
            "name": "Fee test bad cycle",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"cycle": "BIWEEKLY"}, headers=admin_headers)
    assert res.status_code == 400
    assert res.json().get("code") == "VALIDATION_ERROR"


# ==============================================================================
# 6. PATCH /fee-types/{id} - Happy Path Updates & Edge Cases
# ==============================================================================

def test_patch_fee_type_update_name_admin(client, admin_headers):
    """PATCH /fee-types/{id} updates 'name' successfully by ADMIN."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_NAME_01",
            "name": "Tên ban đầu",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"name": "Tên đã cập nhật"}, headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == fee_id
    assert data["name"] == "Tên đã cập nhật"


def test_patch_fee_type_update_name_accountant(client, admin_headers, accountant_headers):
    """PATCH /fee-types/{id} updates 'name' successfully by ACCOUNTANT."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_NAME_ACC",
            "name": "Tên cũ kế toán",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"name": "Tên mới kế toán"}, headers=accountant_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "Tên mới kế toán"


def test_patch_fee_type_update_unit_label(client, admin_headers):
    """PATCH /fee-types/{id} updates 'unit_label' successfully."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_UNIT_01",
            "name": "Phí đổi đơn vị",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"unit_label": "mét vuông"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["unit_label"] == "mét vuông"


def test_patch_fee_type_update_cycle(client, admin_headers):
    """PATCH /fee-types/{id} updates 'cycle' to QUARTERLY and YEARLY."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_CYCLE_01",
            "name": "Phí đổi chu kỳ",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2",
            "cycle": "MONTHLY"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    # Update to QUARTERLY
    res_q = client.patch(f"/fee-types/{fee_id}", json={"cycle": "QUARTERLY"}, headers=admin_headers)
    assert res_q.status_code == 200
    assert res_q.json()["cycle"] == "QUARTERLY"

    # Update to YEARLY
    res_y = client.patch(f"/fee-types/{fee_id}", json={"cycle": "YEARLY"}, headers=admin_headers)
    assert res_y.status_code == 200
    assert res_y.json()["cycle"] == "YEARLY"


def test_patch_fee_type_update_due_day_boundary_1(client, admin_headers):
    """PATCH /fee-types/{id} updates 'due_day' to minimum boundary 1."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_DUE_B1",
            "name": "Phí cập nhật due day 1",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2",
            "due_day": 15
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"due_day": 1}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["due_day"] == 1


def test_patch_fee_type_update_due_day_boundary_31(client, admin_headers):
    """PATCH /fee-types/{id} updates 'due_day' to maximum boundary 31."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_DUE_B31",
            "name": "Phí cập nhật due day 31",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2",
            "due_day": 15
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={"due_day": 31}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["due_day"] == 31


def test_patch_fee_type_update_description(client, admin_headers):
    """PATCH /fee-types/{id} updates 'description' successfully."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_DESC_01",
            "name": "Phí đổi mô tả",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(
        f"/fee-types/{fee_id}",
        json={"description": "Mô tả mới được cập nhật chi tiết."},
        headers=admin_headers
    )
    assert res.status_code == 200
    assert res.json()["description"] == "Mô tả mới được cập nhật chi tiết."


def test_patch_fee_type_update_multiple_fields(client, admin_headers):
    """PATCH /fee-types/{id} updates multiple fields simultaneously."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_MULTI_01",
            "name": "Phí ban đầu multi",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2",
            "cycle": "MONTHLY",
            "due_day": 10
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    patch_payload = {
        "name": "Phí dịch vụ tổng hợp",
        "unit_label": "m2 thông thủy",
        "cycle": "QUARTERLY",
        "due_day": 25,
        "description": "Cập nhật đồng thời nhiều trường"
    }
    res = client.patch(f"/fee-types/{fee_id}", json=patch_payload, headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Phí dịch vụ tổng hợp"
    assert data["unit_label"] == "m2 thông thủy"
    assert data["cycle"] == "QUARTERLY"
    assert data["due_day"] == 25
    assert data["description"] == "Cập nhật đồng thời nhiều trường"


def test_patch_fee_type_empty_body_retains_values(client, admin_headers):
    """PATCH /fee-types/{id} with empty object {} retains existing values and returns 200."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "PATCH_EMPTY_01",
            "name": "Phí giữ nguyên",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2",
            "cycle": "MONTHLY",
            "due_day": 12
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    res = client.patch(f"/fee-types/{fee_id}", json={}, headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == fee_id
    assert data["name"] == "Phí giữ nguyên"
    assert data["code"] == "PATCH_EMPTY_01"
    assert data["due_day"] == 12


def test_patch_fee_type_immutable_code_ignored_or_preserved(client, admin_headers):
    """PATCH /fee-types/{id} ignores attempt to mutate 'code' according to FeeTypeUpdate schema."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "IMMUTABLE_CODE_01",
            "name": "Phí bất biến mã",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    # Attempt to change code via PATCH
    res = client.patch(
        f"/fee-types/{fee_id}",
        json={"code": "MUTATED_CODE", "name": "Tên mới"},
        headers=admin_headers
    )
    # The code must remain the original one
    assert res.status_code == 200
    assert res.json()["code"] == "IMMUTABLE_CODE_01"
    assert res.json()["name"] == "Tên mới"


def test_patch_fee_type_immutable_calc_method_ignored_or_preserved(client, admin_headers):
    """PATCH /fee-types/{id} ignores attempt to mutate 'calc_method' according to FeeTypeUpdate schema."""
    create_res = client.post(
        "/fee-types",
        json={
            "code": "IMMUTABLE_CALC_01",
            "name": "Phí bất biến cách tính",
            "fee_group": "MANAGEMENT",
            "calc_method": "PER_M2",
            "unit_label": "m2"
        },
        headers=admin_headers
    )
    fee_id = create_res.json()["id"]

    # Attempt to change calc_method via PATCH
    res = client.patch(
        f"/fee-types/{fee_id}",
        json={"calc_method": "METERED", "name": "Tên mới calc"},
        headers=admin_headers
    )
    # calc_method must remain the original one
    assert res.status_code == 200
    assert res.json()["calc_method"] == "PER_M2"
    assert res.json()["name"] == "Tên mới calc"
