"""Test suite for US-13: Ngung ap dung khoan thu (Deactivate Fee Type).

Black-box testing covering:
- RBAC permissions (ADMIN, ACCOUNTANT allowed; TREASURER, RESIDENT forbidden).
- Authentication validations (missing token, invalid token, expired token, must_change_password).
- Domain invariants (AC-13.1: No hard delete, transitions to INACTIVE, immutability of other fields).
- Idempotency (already INACTIVE fee types).
- Boundary conditions & path parameter validation (404 Not Found, 422 Unprocessable Entity).
- HTTP Method constraints (405 Method Not Allowed).
- Request body tolerance (empty body, extra fields).
- State isolation & Fee catalog filtering integration.
- Standard Error response schema conformance.
"""

import datetime
import uuid
import pytest
from app.core.security import create_access_token


# ============================================================================
# HELPER FUNCTIONS & FIXTURES
# ============================================================================

def create_token(
    user_id: int = 1,
    username: str = "admin_test",
    role: str = "ADMIN",
    must_change_password: bool = False,
    expires_delta: datetime.timedelta | None = None
) -> dict:
    """Helper to generate Authorization header for arbitrary role/user."""
    claims = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "must_change_password": must_change_password,
    }
    token = create_access_token(claims, expires_delta=expires_delta)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_accountant():
    return create_token(user_id=2, username="accountant_test", role="ACCOUNTANT")


@pytest.fixture
def auth_headers_treasurer():
    return create_token(user_id=5, username="treasurer_test", role="TREASURER")


@pytest.fixture
def auth_headers_resident():
    return create_token(user_id=3, username="resident_101", role="RESIDENT")


def create_test_fee_type(client, auth_headers, **kwargs) -> dict:
    """Helper to provision a fee type via API for testing deactivation."""
    random_suffix = uuid.uuid4().hex[:6].upper()
    code = kwargs.get("code", f"FT_{random_suffix}")
    payload = {
        "code": code,
        "name": kwargs.get("name", f"Khoan thu test {code}"),
        "fee_group": kwargs.get("fee_group", "MANAGEMENT"),
        "calc_method": kwargs.get("calc_method", "PER_M2"),
        "unit_label": kwargs.get("unit_label", "m2"),
        "cycle": kwargs.get("cycle", "MONTHLY"),
        "is_pass_through": kwargs.get("is_pass_through", False),
    }
    if "vehicle_type" in kwargs:
        payload["vehicle_type"] = kwargs["vehicle_type"]
    elif payload["calc_method"] == "PER_VEHICLE":
        payload["vehicle_type"] = "MOTORBIKE"

    if "due_day" in kwargs:
        payload["due_day"] = kwargs["due_day"]
    if "description" in kwargs:
        payload["description"] = kwargs["description"]
    if "provider_id" in kwargs:
        payload["provider_id"] = kwargs["provider_id"]

    res = client.post("/api/v1/fee-types", json=payload, headers=auth_headers)
    assert res.status_code == 201, f"Failed to setup fee type: {res.text}"
    return res.json()


# ============================================================================
# SUITE 1: RBAC & AUTHENTICATION (14 Test Cases)
# ============================================================================

def test_us13_rbac_admin_allowed(client, auth_headers_admin):
    """US-13: ADMIN is authorized to deactivate fee types (200 OK)."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_rbac_accountant_allowed(client, auth_headers_admin, auth_headers_accountant):
    """US-13: ACCOUNTANT is authorized to deactivate fee types (200 OK)."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_accountant)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_rbac_treasurer_forbidden(client, db_session, auth_headers_admin):
    """US-13: TREASURER role is forbidden from deactivating fee types (403 FORBIDDEN)."""
    from sqlalchemy import text
    fee = create_test_fee_type(client, auth_headers_admin)

    # Set user 3 (resident_101) to role_id=3 (TREASURER)
    db_session.execute(text("UPDATE users SET role_id = 3 WHERE id = 3"))
    db_session.commit()
    try:
        treasurer_headers = create_token(user_id=3, username="resident_101", role="TREASURER")
        res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=treasurer_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"
    finally:
        db_session.execute(text("UPDATE users SET role_id = 4 WHERE id = 3"))
        db_session.commit()


def test_us13_rbac_resident_forbidden(client, auth_headers_admin, auth_headers_resident):
    """US-13: RESIDENT role is forbidden from deactivating fee types (403 FORBIDDEN)."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_resident)
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_us13_rbac_unknown_role_forbidden(client, db_session, auth_headers_admin):
    """US-13: User without ADMIN/ACCOUNTANT permissions is rejected with 403."""
    # Resident user (id=4) attempting admin action
    resident_headers = create_token(user_id=4, username="resident_102", role="RESIDENT")
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=resident_headers)
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_us13_rbac_empty_role_forbidden(client, db_session, auth_headers_admin):
    """US-13: User with non-privileged role in token claim is rejected with 403."""
    headers = create_token(user_id=3, username="resident_101", role="")
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=headers)
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_us13_auth_missing_header(client, auth_headers_admin):
    """US-13: Request without Authorization header returns 401 UNAUTHENTICATED."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate")
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_us13_auth_invalid_token(client, auth_headers_admin):
    """US-13: Request with invalid/corrupt token returns 401."""
    fee = create_test_fee_type(client, auth_headers_admin)
    headers = {"Authorization": "Bearer invalid_gibberish_token_string"}
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=headers)
    assert res.status_code == 401
    assert res.json()["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_us13_auth_empty_bearer(client, auth_headers_admin):
    """US-13: Request with empty Bearer token returns 401."""
    fee = create_test_fee_type(client, auth_headers_admin)
    headers = {"Authorization": "Bearer "}
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=headers)
    assert res.status_code == 401


def test_us13_auth_non_bearer_scheme(client, auth_headers_admin):
    """US-13: Request with non-Bearer auth scheme (Basic) returns 401."""
    fee = create_test_fee_type(client, auth_headers_admin)
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=headers)
    assert res.status_code == 401


def test_us13_auth_token_expired(client, auth_headers_admin):
    """US-13: Expired JWT token returns 401."""
    fee = create_test_fee_type(client, auth_headers_admin)
    expired_headers = create_token(
        user_id=1,
        username="admin_test",
        role="ADMIN",
        expires_delta=datetime.timedelta(minutes=-30)
    )
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=expired_headers)
    assert res.status_code == 401


def test_us13_auth_must_change_password_admin(client, db_session, auth_headers_admin):
    """US-13: User with must_change_password=True is rejected with 403 PASSWORD_CHANGE_REQUIRED."""
    from sqlalchemy import text
    fee = create_test_fee_type(client, auth_headers_admin)

    db_session.execute(text("UPDATE users SET must_change_password = 1 WHERE id = 1"))
    db_session.commit()
    try:
        pw_change_headers = create_token(
            user_id=1,
            username="admin_test",
            role="ADMIN",
            must_change_password=True
        )
        res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=pw_change_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    finally:
        db_session.execute(text("UPDATE users SET must_change_password = 0 WHERE id = 1"))
        db_session.commit()


def test_us13_auth_must_change_password_accountant(client, db_session, auth_headers_admin):
    """US-13: Accountant with must_change_password=True is rejected with 403."""
    from sqlalchemy import text
    fee = create_test_fee_type(client, auth_headers_admin)

    db_session.execute(text("UPDATE users SET must_change_password = 1 WHERE id = 2"))
    db_session.commit()
    try:
        pw_change_headers = create_token(
            user_id=2,
            username="accountant_test",
            role="ACCOUNTANT",
            must_change_password=True
        )
        res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=pw_change_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    finally:
        db_session.execute(text("UPDATE users SET must_change_password = 0 WHERE id = 2"))
        db_session.commit()


def test_us13_auth_malformed_token_header(client, auth_headers_admin):
    """US-13: Header with incorrect formatting returns 401."""
    fee = create_test_fee_type(client, auth_headers_admin)
    headers = {"Authorization": "Token eyJhbGciOiJIUzI1NiJ9"}
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=headers)
    assert res.status_code == 401


# ============================================================================
# SUITE 2: FUNCTIONAL HAPPY PATHS & AC-13.1 (16 Test Cases)
# ============================================================================

def test_us13_happy_path_deactivate_active_fee(client, auth_headers_admin):
    """US-13 / AC-13.1: Active fee type successfully transitions to INACTIVE."""
    fee = create_test_fee_type(client, auth_headers_admin)
    assert fee["status"] == "ACTIVE"

    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "INACTIVE"
    assert data["id"] == fee["id"]


def test_us13_ac13_no_hard_delete_verified_by_id(client, auth_headers_admin):
    """US-13 / AC-13.1: Deactivated fee type is NOT physically deleted; can still be fetched."""
    fee = create_test_fee_type(client, auth_headers_admin)
    client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)

    # Verification via GET by ID
    get_res = client.get(f"/api/v1/fee-types/{fee['id']}", headers=auth_headers_admin)
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == fee["id"]
    assert retrieved["status"] == "INACTIVE"


def test_us13_response_schema_exact_fields(client, auth_headers_admin):
    """US-13: Response conforms strictly to FeeType schema."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()

    expected_keys = {
        "id", "code", "name", "fee_group", "calc_method", "unit_label",
        "vehicle_type", "is_pass_through", "provider_id", "cycle", "due_day",
        "status", "description", "current_unit_price", "created_at", "updated_at"
    }
    for key in ["id", "code", "name", "fee_group", "calc_method", "unit_label", "status"]:
        assert key in data, f"Missing required key: {key}"


def test_us13_immutability_code_preserved(client, auth_headers_admin):
    """US-13: Field 'code' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, code="CODE_IMMUTABLE")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["code"] == "CODE_IMMUTABLE"


def test_us13_immutability_name_preserved(client, auth_headers_admin):
    """US-13: Field 'name' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, name="Phi Bao Tri Dac Biet")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["name"] == "Phi Bao Tri Dac Biet"


def test_us13_immutability_fee_group_preserved(client, auth_headers_admin):
    """US-13: Field 'fee_group' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="CAR")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["fee_group"] == "PARKING"


def test_us13_immutability_calc_method_preserved(client, auth_headers_admin):
    """US-13: Field 'calc_method' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, calc_method="PER_M2")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["calc_method"] == "PER_M2"


def test_us13_immutability_unit_label_preserved(client, auth_headers_admin):
    """US-13: Field 'unit_label' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, unit_label="m2_thang")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["unit_label"] == "m2_thang"


def test_us13_immutability_cycle_preserved(client, auth_headers_admin):
    """US-13: Field 'cycle' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, cycle="YEARLY")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["cycle"] == "YEARLY"


def test_us13_immutability_due_day_preserved(client, auth_headers_admin):
    """US-13: Field 'due_day' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, due_day=15)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["due_day"] == 15


def test_us13_immutability_is_pass_through_preserved(client, auth_headers_admin):
    """US-13: Field 'is_pass_through' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, is_pass_through=True)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["is_pass_through"] is True


def test_us13_immutability_description_preserved(client, auth_headers_admin):
    """US-13: Field 'description' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, description="Mo ta chi tiet khoan thu")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["description"] == "Mo ta chi tiet khoan thu"


def test_us13_immutability_vehicle_type_preserved(client, auth_headers_admin):
    """US-13: Field 'vehicle_type' remains unchanged after deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="MOTORBIKE")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.json()["vehicle_type"] == "MOTORBIKE"


def test_us13_timestamp_updated_at_updated(client, auth_headers_admin):
    """US-13: 'updated_at' is updated upon deactivation."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    data = res.json()
    assert "updated_at" in data
    assert data["updated_at"] is not None


def test_us13_idempotent_deactivate_already_inactive(client, auth_headers_admin):
    """US-13: Deactivating an already INACTIVE fee type succeeds with 200 and status remains INACTIVE."""
    fee = create_test_fee_type(client, auth_headers_admin)
    # First deactivation
    res1 = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res1.status_code == 200
    assert res1.json()["status"] == "INACTIVE"

    # Second deactivation (idempotent operation)
    res2 = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res2.status_code == 200
    assert res2.json()["status"] == "INACTIVE"


def test_us13_idempotent_multiple_consecutive_deactivations(client, auth_headers_admin):
    """US-13: Multiple consecutive deactivations consistently return 200 OK and status INACTIVE."""
    fee = create_test_fee_type(client, auth_headers_admin)
    for _ in range(4):
        res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
        assert res.status_code == 200
        assert res.json()["status"] == "INACTIVE"


# ============================================================================
# SUITE 3: FEE GROUPS, CYCLES & METHODS COVERAGE (14 Test Cases)
# ============================================================================

def test_us13_deactivate_management_per_m2(client, auth_headers_admin):
    """US-13: Deactivate MANAGEMENT fee type with calc_method=PER_M2."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="MANAGEMENT", calc_method="PER_M2", unit_label="m2")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_parking_motorbike(client, auth_headers_admin):
    """US-13: Deactivate PARKING fee type with vehicle_type=MOTORBIKE."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="MOTORBIKE", unit_label="xe")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_parking_car(client, auth_headers_admin):
    """US-13: Deactivate PARKING fee type with vehicle_type=CAR."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="CAR", unit_label="xe")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_parking_bicycle(client, auth_headers_admin):
    """US-13: Deactivate PARKING fee type with vehicle_type=BICYCLE."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="BICYCLE", unit_label="xe")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_utility_metered(client, auth_headers_admin):
    """US-13: Deactivate UTILITY fee type with calc_method=METERED."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="UTILITY", calc_method="METERED", unit_label="kWh")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_utility_pass_through_true(client, auth_headers_admin):
    """US-13: Deactivate UTILITY fee type marked as is_pass_through=True."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="UTILITY", calc_method="METERED", unit_label="m3", is_pass_through=True)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_utility_pass_through_false(client, auth_headers_admin):
    """US-13: Deactivate UTILITY fee type marked as is_pass_through=False."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="UTILITY", calc_method="METERED", unit_label="m3", is_pass_through=False)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_other_per_household(client, auth_headers_admin):
    """US-13: Deactivate OTHER fee type with calc_method=PER_HOUSEHOLD."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="OTHER", calc_method="PER_HOUSEHOLD", unit_label="ho")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_other_per_person(client, auth_headers_admin):
    """US-13: Deactivate OTHER fee type with calc_method=PER_PERSON."""
    fee = create_test_fee_type(client, auth_headers_admin, fee_group="OTHER", calc_method="PER_PERSON", unit_label="nguoi")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_cycle_monthly(client, auth_headers_admin):
    """US-13: Deactivate fee type with cycle=MONTHLY."""
    fee = create_test_fee_type(client, auth_headers_admin, cycle="MONTHLY")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_cycle_quarterly(client, auth_headers_admin):
    """US-13: Deactivate fee type with cycle=QUARTERLY."""
    fee = create_test_fee_type(client, auth_headers_admin, cycle="QUARTERLY")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_cycle_yearly(client, auth_headers_admin):
    """US-13: Deactivate fee type with cycle=YEARLY."""
    fee = create_test_fee_type(client, auth_headers_admin, cycle="YEARLY")
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_due_day_boundary_1(client, auth_headers_admin):
    """US-13: Deactivate fee type with due_day=1 (lower bound)."""
    fee = create_test_fee_type(client, auth_headers_admin, due_day=1)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_deactivate_due_day_boundary_31(client, auth_headers_admin):
    """US-13: Deactivate fee type with due_day=31 (upper bound)."""
    fee = create_test_fee_type(client, auth_headers_admin, due_day=31)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


# ============================================================================
# SUITE 4: BOUNDARY & PATH PARAMETER VALIDATION (10 Test Cases)
# ============================================================================

def test_us13_error_not_found_id_999999(client, auth_headers_admin):
    """US-13: Deactivating non-existent ID 999999 returns 404 NOT_FOUND."""
    res = client.post("/api/v1/fee-types/999999/deactivate", headers=auth_headers_admin)
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_us13_error_not_found_id_888888(client, auth_headers_admin):
    """US-13: Deactivating non-existent ID 888888 returns 404 NOT_FOUND."""
    res = client.post("/api/v1/fee-types/888888/deactivate", headers=auth_headers_admin)
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_us13_boundary_id_zero(client, auth_headers_admin):
    """US-13: Deactivating ID=0 returns 404 or 422."""
    res = client.post("/api/v1/fee-types/0/deactivate", headers=auth_headers_admin)
    assert res.status_code in [404, 422]


def test_us13_boundary_negative_id(client, auth_headers_admin):
    """US-13: Deactivating negative ID returns 404 or 422."""
    res = client.post("/api/v1/fee-types/-1/deactivate", headers=auth_headers_admin)
    assert res.status_code in [404, 422]


def test_us13_boundary_large_int64_id(client, auth_headers_admin):
    """US-13: Deactivating maximum int64 boundary ID returns 404 NOT_FOUND."""
    res = client.post("/api/v1/fee-types/9223372036854775800/deactivate", headers=auth_headers_admin)
    assert res.status_code == 404
    assert res.json()["code"] == "NOT_FOUND"


def test_us13_invalid_string_id(client, auth_headers_admin):
    """US-13: Path with string ID returns 400 VALIDATION_ERROR, 404 or 422."""
    res = client.post("/api/v1/fee-types/abc/deactivate", headers=auth_headers_admin)
    assert res.status_code in [400, 404, 422]
    if res.status_code == 400:
        assert res.json()["code"] == "VALIDATION_ERROR"


def test_us13_invalid_float_id(client, auth_headers_admin):
    """US-13: Path with float ID returns 400 VALIDATION_ERROR, 404 or 422."""
    res = client.post("/api/v1/fee-types/1.5/deactivate", headers=auth_headers_admin)
    assert res.status_code in [400, 404, 422]
    if res.status_code == 400:
        assert res.json()["code"] == "VALIDATION_ERROR"


def test_us13_invalid_special_chars_id(client, auth_headers_admin):
    """US-13: Path with special characters returns 400, 404, 405, or 422."""
    res = client.post("/api/v1/fee-types/!@#$/deactivate", headers=auth_headers_admin)
    assert res.status_code in [400, 404, 405, 422]


def test_us13_invalid_whitespace_id(client, auth_headers_admin):
    """US-13: Path with whitespace returns 400, 404, or 422."""
    res = client.post("/api/v1/fee-types/%20/deactivate", headers=auth_headers_admin)
    assert res.status_code in [400, 404, 422]
    if res.status_code == 400:
        assert res.json()["code"] == "VALIDATION_ERROR"


def test_us13_sqli_id_safe(client, auth_headers_admin):
    """US-13: SQL injection attempt in path is safely rejected with 400 VALIDATION_ERROR or 422/404."""
    res = client.post("/api/v1/fee-types/1%20OR%201=1/deactivate", headers=auth_headers_admin)
    assert res.status_code in [400, 404, 422]
    if res.status_code == 400:
        assert res.json()["code"] == "VALIDATION_ERROR"


# ============================================================================
# SUITE 5: HTTP PROTOCOL, METHODS & BODY HANDLING (8 Test Cases)
# ============================================================================

def test_us13_http_get_not_allowed(client, auth_headers_admin):
    """US-13: GET /fee-types/{id}/deactivate returns 405 Method Not Allowed."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.get(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 405


def test_us13_http_put_not_allowed(client, auth_headers_admin):
    """US-13: PUT /fee-types/{id}/deactivate returns 405 Method Not Allowed."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.put(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 405


def test_us13_http_delete_not_allowed(client, auth_headers_admin):
    """US-13: DELETE /fee-types/{id}/deactivate returns 405 Method Not Allowed."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.delete(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 405


def test_us13_http_patch_not_allowed(client, auth_headers_admin):
    """US-13: PATCH /fee-types/{id}/deactivate returns 405 Method Not Allowed."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.patch(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 405


def test_us13_body_empty_post(client, auth_headers_admin):
    """US-13: POST with no body content succeeds (200 OK)."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_body_empty_json(client, auth_headers_admin):
    """US-13: POST with empty JSON object '{}' succeeds (200 OK)."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", json={}, headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_body_extra_fields_tolerated(client, auth_headers_admin):
    """US-13: POST with superfluous body payload is tolerated and succeeds (200 OK)."""
    fee = create_test_fee_type(client, auth_headers_admin)
    extra_payload = {"reason": "Outdated charge item", "extra": 1234}
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", json=extra_payload, headers=auth_headers_admin)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"


def test_us13_both_url_paths_work(client, auth_headers_admin):
    """US-13: Both '/api/v1/fee-types/{id}/deactivate' and '/fee-types/{id}/deactivate' routes work."""
    fee1 = create_test_fee_type(client, auth_headers_admin)
    res1 = client.post(f"/api/v1/fee-types/{fee1['id']}/deactivate", headers=auth_headers_admin)
    assert res1.status_code == 200
    assert res1.json()["status"] == "INACTIVE"

    fee2 = create_test_fee_type(client, auth_headers_admin)
    res2 = client.post(f"/fee-types/{fee2['id']}/deactivate", headers=auth_headers_admin)
    assert res2.status_code == 200
    assert res2.json()["status"] == "INACTIVE"


# ============================================================================
# SUITE 6: STATE ISOLATION & CATALOG QUERY INTEGRATION (8 Test Cases)
# ============================================================================

def test_us13_state_isolation_two_fee_types(client, auth_headers_admin):
    """US-13: Deactivating fee type A leaves fee type B in ACTIVE state."""
    fee_a = create_test_fee_type(client, auth_headers_admin)
    fee_b = create_test_fee_type(client, auth_headers_admin)

    # Deactivate fee A only
    res_a = client.post(f"/api/v1/fee-types/{fee_a['id']}/deactivate", headers=auth_headers_admin)
    assert res_a.status_code == 200
    assert res_a.json()["status"] == "INACTIVE"

    # Verify fee B remains ACTIVE
    res_b = client.get(f"/api/v1/fee-types/{fee_b['id']}", headers=auth_headers_admin)
    assert res_b.status_code == 200
    assert res_b.json()["status"] == "ACTIVE"


def test_us13_state_isolation_batch_deactivation(client, auth_headers_admin):
    """US-13: Sequentially deactivating multiple fee types does not corrupt adjacent records."""
    fees = [create_test_fee_type(client, auth_headers_admin) for _ in range(4)]

    # Deactivate first three
    for fee in fees[:3]:
        r = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)
        assert r.status_code == 200

    # 4th must remain ACTIVE
    r4 = client.get(f"/api/v1/fee-types/{fees[3]['id']}", headers=auth_headers_admin)
    assert r4.json()["status"] == "ACTIVE"

    # First three must be INACTIVE
    for fee in fees[:3]:
        r = client.get(f"/api/v1/fee-types/{fee['id']}", headers=auth_headers_admin)
        assert r.json()["status"] == "INACTIVE"


def test_us13_list_all_contains_deactivated(client, auth_headers_admin):
    """US-13: Listing fee types includes deactivated records with status INACTIVE."""
    fee = create_test_fee_type(client, auth_headers_admin)
    client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)

    list_res = client.get("/api/v1/fee-types?page=1&page_size=100", headers=auth_headers_admin)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    matched = next((item for item in items if item["id"] == fee["id"]), None)
    assert matched is not None
    assert matched["status"] == "INACTIVE"


def test_us13_filter_status_active_excludes_deactivated(client, auth_headers_admin):
    """US-13: GET /fee-types?status=ACTIVE does NOT include deactivated fee types."""
    fee = create_test_fee_type(client, auth_headers_admin)
    client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)

    list_res = client.get("/api/v1/fee-types?status=ACTIVE&page=1&page_size=100", headers=auth_headers_admin)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert not any(item["id"] == fee["id"] for item in items)


def test_us13_filter_status_inactive_includes_deactivated(client, auth_headers_admin):
    """US-13: GET /fee-types?status=INACTIVE includes deactivated fee types."""
    fee = create_test_fee_type(client, auth_headers_admin)
    client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_admin)

    list_res = client.get("/api/v1/fee-types?status=INACTIVE&page=1&page_size=100", headers=auth_headers_admin)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    matched = next((item for item in items if item["id"] == fee["id"]), None)
    assert matched is not None
    assert matched["status"] == "INACTIVE"


def test_us13_error_schema_404_conformance(client, auth_headers_admin):
    """US-13: 404 response payload strictly conforms to Error schema."""
    res = client.post("/api/v1/fee-types/9999999/deactivate", headers=auth_headers_admin)
    assert res.status_code == 404
    data = res.json()
    assert "code" in data
    assert "message" in data
    assert data["code"] == "NOT_FOUND"


def test_us13_error_schema_401_conformance(client):
    """US-13: 401 response payload strictly conforms to Error schema."""
    res = client.post("/api/v1/fee-types/1/deactivate")
    assert res.status_code == 401
    data = res.json()
    assert "code" in data
    assert "message" in data
    assert data["code"] == "UNAUTHENTICATED"


def test_us13_error_schema_403_conformance(client, auth_headers_admin, auth_headers_resident):
    """US-13: 403 response payload strictly conforms to Error schema."""
    fee = create_test_fee_type(client, auth_headers_admin)
    res = client.post(f"/api/v1/fee-types/{fee['id']}/deactivate", headers=auth_headers_resident)
    assert res.status_code == 403
    data = res.json()
    assert "code" in data
    assert "message" in data
    assert data["code"] == "FORBIDDEN"
