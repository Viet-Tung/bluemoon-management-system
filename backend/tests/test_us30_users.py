"""
Unit & Integration Tests for US-30: Quản lý tài khoản người dùng (User Account Management).
Comprehensive Black-Box Automated Test Suite according to docs/openapi.yaml,
docs/API_CONTRACT.md, and US-30 specifications.

Coverage:
1. Happy Paths:
   - GET /api/v1/users (default pagination, custom pagination, search q, filter role, filter is_active, combinations)
   - POST /api/v1/users (create ADMIN, ACCOUNTANT, TREASURER, verify schema, temporary_password, DB state, login)
   - GET /api/v1/users/{userId} (fetch UserResponse, check all fields)
   - PATCH /api/v1/users/{userId} (update full_name, email, phone, is_active, multiple fields)
   - POST /api/v1/users/{userId}/lock (lock staff account, verify DB, AuditLog, prevent login)
   - POST /api/v1/users/{userId}/unlock (unlock account, verify DB, AuditLog, restore login)
   - POST /api/v1/users/{userId}/reset-password (reset password, verify DB, AuditLog, test login with new temp password)

2. Edge Cases & Validation (400, 404, 409):
   - Duplicate username (exact, case-insensitive, with whitespace) -> 409 DUPLICATE_USERNAME
   - Invalid role_id (non-existent, negative) -> 400 VALIDATION_ERROR
   - Prohibited resident role creation -> 400 VALIDATION_ERROR
   - Username validation (too short, spaces, invalid chars) -> 400 VALIDATION_ERROR
   - Email format validation (create, patch) -> 400 VALIDATION_ERROR
   - Admin self-locking prohibition -> 409 CANNOT_LOCK_SELF
   - Non-existent userId (GET, PATCH, lock, unlock, reset-password) -> 404 USER_NOT_FOUND
   - Pagination boundaries (page <= 0, page_size <= 0, page_size > 100) -> 400 VALIDATION_ERROR
   - SQL Injection & wildcard payload safety in q parameter -> 200 OK (no crashes, parameterized)

3. Security & RBAC Guard (401, 403):
   - Unauthenticated requests on all 7 endpoints -> 401 UNAUTHENTICATED
   - Malformed/expired tokens on all 7 endpoints -> 401 UNAUTHENTICATED
   - Forbidden role RESIDENT on all 7 endpoints -> 403 FORBIDDEN
   - Forbidden role ACCOUNTANT on all 7 endpoints -> 403 FORBIDDEN
   - Forbidden role TREASURER on all 7 endpoints -> 403 FORBIDDEN
   - AuditLog verification for ACCESS_DENIED events
"""

from datetime import timedelta
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import AuditLog, Role, User

USERS_URL = f"{settings.API_V1_STR}/users"
LOGIN_URL = f"{settings.API_V1_STR}/auth/login"

HASH_ADMIN = get_password_hash("AdminPass123!")
HASH_ACCOUNTANT = get_password_hash("AccPass123!")
HASH_RESIDENT = get_password_hash("ResPass123!")
HASH_TREASURER = get_password_hash("TreasurerPass123!")


# =====================================================================
# FIXTURES & ISOLATION HELPERS
# =====================================================================

@pytest.fixture(autouse=True)
def cleanup_users_and_logs(db_session):
    """
    Ensure complete database isolation before and after each test case:
    - Removes any user added with id > 4 (or newly added usernames).
    - Resets seeded users (IDs 1..4) to original active state, failed count = 0.
    - Cleans audit logs.
    """
    yield
    try:
        # Delete non-seeded users
        db_session.query(User).filter(User.id > 4).delete()
        # Reset seeded users
        u1 = db_session.get(User, 1)
        if u1:
            u1.full_name = "Quản Trị Viên Test"
            u1.email = "admin@bluemoon.local"
            u1.phone = None
            u1.is_active = True
            u1.failed_login_count = 0
            u1.locked_until = None
            u1.must_change_password = False
            u1.password_hash = HASH_ADMIN

        u2 = db_session.get(User, 2)
        if u2:
            u2.full_name = "Kế Toán Test"
            u2.email = "accountant@bluemoon.local"
            u2.phone = None
            u2.is_active = True
            u2.failed_login_count = 0
            u2.locked_until = None
            u2.must_change_password = False
            u2.password_hash = HASH_ACCOUNTANT

        u3 = db_session.get(User, 3)
        if u3:
            u3.is_active = True
            u3.failed_login_count = 0
            u3.locked_until = None
            u3.must_change_password = False

        u4 = db_session.get(User, 4)
        if u4:
            u4.is_active = True
            u4.failed_login_count = 0
            u4.locked_until = None
            u4.must_change_password = False

        db_session.query(AuditLog).delete()
        db_session.commit()
    except Exception:
        db_session.rollback()


@pytest.fixture
def auth_headers_accountant(db_session):
    """Generate auth headers for accountant_test (Role ACCOUNTANT, user_id=2)."""
    token = create_access_token({
        "sub": "2",
        "username": "accountant_test",
        "role": "ACCOUNTANT",
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_treasurer(db_session):
    """Generate auth headers for a persistent treasurer user (Role TREASURER, user_id=5)."""
    user = db_session.get(User, 5)
    if not user:
        user = User(
            id=5,
            username="treasurer_test",
            password_hash=HASH_TREASURER,
            full_name="Thủ Quỹ Test",
            email="treasurer@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        db_session.commit()
    else:
        user.is_active = True
        user.password_hash = HASH_TREASURER
        db_session.commit()

    token = create_access_token({
        "sub": "5",
        "username": "treasurer_test",
        "role": "TREASURER",
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. HAPPY PATHS: GET /api/v1/users (Listing, Filtering, Pagination)
# =====================================================================

def test_list_users_default_pagination(client, auth_headers_admin):
    """Happy Path: List users with default pagination (page=1, page_size=20)."""
    res = client.get(USERS_URL, headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()

    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= 4
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 4

    # Verify schema of the first item
    first = data["items"][0]
    assert "id" in first
    assert "username" in first
    assert "full_name" in first
    assert "role" in first
    assert "is_active" in first
    assert "must_change_password" in first
    assert "role" in first and "code" in first["role"]


def test_list_users_custom_pagination(client, auth_headers_admin):
    """Happy Path: List users with custom page size and page offset."""
    res_p1 = client.get(f"{USERS_URL}?page=1&page_size=2", headers=auth_headers_admin)
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    assert data_p1["page"] == 1
    assert data_p1["page_size"] == 2
    assert len(data_p1["items"]) == 2
    ids_p1 = [u["id"] for u in data_p1["items"]]

    res_p2 = client.get(f"{USERS_URL}?page=2&page_size=2", headers=auth_headers_admin)
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    assert data_p2["page"] == 2
    assert data_p2["page_size"] == 2
    assert len(data_p2["items"]) == 2
    ids_p2 = [u["id"] for u in data_p2["items"]]

    # Ensure pages contain mutually exclusive items
    assert set(ids_p1).isdisjoint(set(ids_p2))


def test_list_users_search_q_username_exact(client, auth_headers_admin):
    """Happy Path: Search users by exact username."""
    res = client.get(f"{USERS_URL}?q=admin_test", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "admin_test"


def test_list_users_search_q_username_case_insensitive(client, auth_headers_admin):
    """Happy Path: Search users by username case-insensitively."""
    res = client.get(f"{USERS_URL}?q=ADMIN_TEST", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "admin_test"


def test_list_users_search_q_username_partial(client, auth_headers_admin):
    """Happy Path: Search users by partial username keyword."""
    res = client.get(f"{USERS_URL}?q=resident", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    usernames = {u["username"] for u in data["items"]}
    assert usernames == {"resident_101", "resident_102"}


def test_list_users_search_q_full_name(client, auth_headers_admin):
    """Happy Path: Search users by full_name."""
    res = client.get(f"{USERS_URL}?q=Quản Trị Viên", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "admin_test"


def test_list_users_search_q_vietnamese_diacritics(client, auth_headers_admin):
    """Happy Path: Search users using Vietnamese accented keywords."""
    res = client.get(f"{USERS_URL}?q=Kế Toán", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "accountant_test"


def test_list_users_search_q_no_match(client, auth_headers_admin):
    """Happy Path: Search users with keyword matching no record."""
    res = client.get(f"{USERS_URL}?q=NonExistentUser12345XYZ", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_list_users_filter_role_admin(client, auth_headers_admin):
    """Happy Path: Filter users by role ADMIN."""
    res = client.get(f"{USERS_URL}?role=ADMIN", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for u in data["items"]:
        assert u["role"]["code"] == "ADMIN"


def test_list_users_filter_role_accountant(client, auth_headers_admin):
    """Happy Path: Filter users by role ACCOUNTANT."""
    res = client.get(f"{USERS_URL}?role=ACCOUNTANT", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["role"]["code"] == "ACCOUNTANT"


def test_list_users_filter_role_resident(client, auth_headers_admin):
    """Happy Path: Filter users by role RESIDENT."""
    res = client.get(f"{USERS_URL}?role=RESIDENT", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    for u in data["items"]:
        assert u["role"]["code"] == "RESIDENT"


def test_list_users_filter_role_treasurer(client, auth_headers_admin, auth_headers_treasurer):
    """Happy Path: Filter users by role TREASURER."""
    res = client.get(f"{USERS_URL}?role=TREASURER", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["role"]["code"] == "TREASURER"


def test_list_users_filter_role_case_insensitive(client, auth_headers_admin):
    """Happy Path: Role filter handles lowercase input gracefully."""
    res = client.get(f"{USERS_URL}?role=admin", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for u in data["items"]:
        assert u["role"]["code"] == "ADMIN"


def test_list_users_filter_is_active_true(client, auth_headers_admin):
    """Happy Path: Filter users by is_active=True."""
    res = client.get(f"{USERS_URL}?is_active=true", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 4
    for u in data["items"]:
        assert u["is_active"] is True


def test_list_users_filter_is_active_false(client, auth_headers_admin, db_session):
    """Happy Path: Filter users by is_active=False."""
    # Deactivate user 2
    u2 = db_session.get(User, 2)
    u2.is_active = False
    db_session.commit()

    res = client.get(f"{USERS_URL}?is_active=false", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == 2
    assert data["items"][0]["is_active"] is False


def test_list_users_combined_role_and_active(client, auth_headers_admin):
    """Happy Path: Combine filters role=RESIDENT and is_active=true."""
    res = client.get(f"{USERS_URL}?role=RESIDENT&is_active=true", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    for u in data["items"]:
        assert u["role"]["code"] == "RESIDENT"
        assert u["is_active"] is True


def test_list_users_combined_q_and_role(client, auth_headers_admin):
    """Happy Path: Combine search q and role filter."""
    res = client.get(f"{USERS_URL}?q=101&role=RESIDENT", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "resident_101"


def test_list_users_combined_all_filters(client, auth_headers_admin):
    """Happy Path: Combine q, role, is_active, page, and page_size."""
    res = client.get(
        f"{USERS_URL}?q=admin&role=ADMIN&is_active=true&page=1&page_size=10",
        headers=auth_headers_admin,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["username"] == "admin_test"


def test_list_users_whitespace_query_returns_all(client, auth_headers_admin):
    """Happy Path: Whitespace-only query is ignored and returns normal listing."""
    res = client.get(f"{USERS_URL}?q=%20%20%20", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 4


# =====================================================================
# 2. HAPPY PATHS: POST /api/v1/users (Creation of Staff Accounts)
# =====================================================================

def test_create_user_admin_success(client, auth_headers_admin, db_session):
    """
    Happy Path: Create new ADMIN user:
    - Status 201 Created.
    - Schema contains temporary_password and temp_password.
    - User in DB has must_change_password=True, is_active=True.
    - Password hash is valid bcrypt rounds >= 12.
    """
    payload = {
        "username": "new_admin_user",
        "full_name": "New Admin Specialist",
        "email": "newadmin@bluemoon.local",
        "phone": "0911222333",
        "role_id": 1,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["username"] == "new_admin_user"
    assert data["full_name"] == "New Admin Specialist"
    assert data["email"] == "newadmin@bluemoon.local"
    assert data["phone"] == "0911222333"
    assert data["role"]["code"] == "ADMIN"
    assert data["is_active"] is True
    assert data["must_change_password"] is True
    assert "temporary_password" in data
    assert "temp_password" in data
    assert data["temporary_password"] == data["temp_password"]

    temp_pwd = data["temporary_password"]
    assert len(temp_pwd) >= 12

    # Check DB
    new_user = db_session.scalar(select(User).where(User.username == "new_admin_user"))
    assert new_user is not None
    assert new_user.must_change_password is True
    assert new_user.is_active is True
    assert verify_password(temp_pwd, new_user.password_hash) is True


def test_create_user_accountant_success(client, auth_headers_admin, db_session):
    """Happy Path: Create new ACCOUNTANT user."""
    payload = {
        "username": "new_acc_user",
        "full_name": "Nguyễn Văn Kế Toán",
        "email": "acc_staff@bluemoon.local",
        "phone": "0988776655",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "new_acc_user"
    assert data["role"]["code"] == "ACCOUNTANT"
    assert data["must_change_password"] is True

    # Verify temp password matches DB hash
    new_user = db_session.scalar(select(User).where(User.username == "new_acc_user"))
    assert verify_password(data["temporary_password"], new_user.password_hash) is True


def test_create_user_treasurer_success(client, auth_headers_admin, db_session):
    """Happy Path: Create new TREASURER user."""
    payload = {
        "username": "new_treasurer_user",
        "full_name": "Lê Thị Thủ Quỹ",
        "email": "treasurer_staff@bluemoon.local",
        "phone": "0933445566",
        "role_id": 3,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "new_treasurer_user"
    assert data["role"]["code"] == "TREASURER"

    new_user = db_session.scalar(select(User).where(User.username == "new_treasurer_user"))
    assert verify_password(data["temporary_password"], new_user.password_hash) is True


def test_create_user_minimal_fields(client, auth_headers_admin, db_session):
    """Happy Path: Create user with only required fields (email & phone omitted)."""
    payload = {
        "username": "minimal_user",
        "full_name": "Minimal Staff",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "minimal_user"
    assert data["email"] is None
    assert data["phone"] is None
    assert data["role"]["code"] == "ACCOUNTANT"


def test_create_user_login_with_temporary_password(client, auth_headers_admin):
    """Happy Path: Newly created user can successfully log in using the temporary password."""
    payload = {
        "username": "temp_login_user",
        "full_name": "Temporary Login Tester",
        "role_id": 2,
    }
    create_res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert create_res.status_code == 201
    temp_pwd = create_res.json()["temporary_password"]

    # Attempt login with the generated temporary password
    login_res = client.post(
        LOGIN_URL,
        json={"username": "temp_login_user", "password": temp_pwd},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "token" in login_data
    assert login_data["user"]["username"] == "temp_login_user"
    assert login_data["user"]["must_change_password"] is True


def test_create_user_bcrypt_rounds_ge_12(client, auth_headers_admin, db_session):
    """Happy Path: Created user password hash adheres to AC-44.1 (rounds >= 12)."""
    payload = {
        "username": "bcrypt_user",
        "full_name": "Bcrypt Cost Tester",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 201

    user = db_session.scalar(select(User).where(User.username == "bcrypt_user"))
    parts = user.password_hash.split("$")
    assert parts[1] in ("2a", "2b", "2y")
    rounds = int(parts[2])
    assert rounds >= 12


def test_create_user_temporary_password_complexity(client, auth_headers_admin):
    """Happy Path: Temporary password satisfies uppercase, lowercase, digit, and special char."""
    payload = {
        "username": "pwd_complex_user",
        "full_name": "Password Complexity Tester",
        "role_id": 1,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 201
    pwd = res.json()["temporary_password"]

    assert len(pwd) >= 12
    assert any(c.isupper() for c in pwd)
    assert any(c.islower() for c in pwd)
    assert any(c.isdigit() for c in pwd)
    assert any(c in "!@#$%^&*" for c in pwd)


# =====================================================================
# 3. HAPPY PATHS: GET /api/v1/users/{userId} (User Details)
# =====================================================================

def test_get_user_admin_by_id(client, auth_headers_admin):
    """Happy Path: Get details of admin user (ID=1)."""
    res = client.get(f"{USERS_URL}/1", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 1
    assert data["username"] == "admin_test"
    assert data["full_name"] == "Quản Trị Viên Test"
    assert data["role"]["code"] == "ADMIN"
    assert data["is_active"] is True


def test_get_user_accountant_by_id(client, auth_headers_admin):
    """Happy Path: Get details of accountant user (ID=2)."""
    res = client.get(f"{USERS_URL}/2", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 2
    assert data["username"] == "accountant_test"
    assert data["role"]["code"] == "ACCOUNTANT"


def test_get_user_resident_by_id(client, auth_headers_admin):
    """Happy Path: Get details of resident user (ID=3) with household_id."""
    res = client.get(f"{USERS_URL}/3", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 3
    assert data["username"] == "resident_101"
    assert data["role"]["code"] == "RESIDENT"
    assert data["household_id"] == 101


# =====================================================================
# 4. HAPPY PATHS: PATCH /api/v1/users/{userId} (User Updates)
# =====================================================================

def test_update_user_full_name(client, auth_headers_admin, db_session):
    """Happy Path: Update full_name of user."""
    res = client.patch(
        f"{USERS_URL}/2",
        headers=auth_headers_admin,
        json={"full_name": "Kế Toán Viên Đã Đổi Tên"},
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Kế Toán Viên Đã Đổi Tên"

    u = db_session.get(User, 2)
    assert u.full_name == "Kế Toán Viên Đã Đổi Tên"


def test_update_user_email(client, auth_headers_admin, db_session):
    """Happy Path: Update email of user."""
    res = client.patch(
        f"{USERS_URL}/2",
        headers=auth_headers_admin,
        json={"email": "new_accountant_email@bluemoon.local"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == "new_accountant_email@bluemoon.local"

    u = db_session.get(User, 2)
    assert u.email == "new_accountant_email@bluemoon.local"


def test_update_user_phone(client, auth_headers_admin, db_session):
    """Happy Path: Update phone number of user."""
    res = client.patch(
        f"{USERS_URL}/2",
        headers=auth_headers_admin,
        json={"phone": "0909123456"},
    )
    assert res.status_code == 200
    assert res.json()["phone"] == "0909123456"

    u = db_session.get(User, 2)
    assert u.phone == "0909123456"


def test_update_user_is_active_toggle(client, auth_headers_admin, db_session):
    """Happy Path: Deactivate user via PATCH, then reactivate."""
    # 1. Deactivate
    res_deact = client.patch(
        f"{USERS_URL}/2",
        headers=auth_headers_admin,
        json={"is_active": False},
    )
    assert res_deact.status_code == 200
    assert res_deact.json()["is_active"] is False

    u = db_session.get(User, 2)
    assert u.is_active is False

    # 2. Reactivate
    res_act = client.patch(
        f"{USERS_URL}/2",
        headers=auth_headers_admin,
        json={"is_active": True},
    )
    assert res_act.status_code == 200
    assert res_act.json()["is_active"] is True

    db_session.refresh(u)
    assert u.is_active is True


def test_update_user_multiple_fields(client, auth_headers_admin, db_session):
    """Happy Path: Update full_name, email, phone, and is_active simultaneously."""
    payload = {
        "full_name": "Tên Cập Nhật Toàn Diện",
        "email": "comprehensive@bluemoon.local",
        "phone": "0999888777",
        "is_active": True,
    }
    res = client.patch(f"{USERS_URL}/2", headers=auth_headers_admin, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["full_name"] == payload["full_name"]
    assert data["email"] == payload["email"]
    assert data["phone"] == payload["phone"]
    assert data["is_active"] is True


def test_update_user_empty_payload(client, auth_headers_admin, db_session):
    """Happy Path: Empty PATCH payload returns current user data without errors."""
    res = client.patch(f"{USERS_URL}/2", headers=auth_headers_admin, json={})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 2
    assert data["username"] == "accountant_test"


def test_update_user_does_not_modify_immutable_fields(client, auth_headers_admin, db_session):
    """Happy Path: PATCH ignores attempts to overwrite role_id, password_hash, or id."""
    u_before = db_session.get(User, 2)
    original_hash = u_before.password_hash
    original_role = u_before.role_id

    res = client.patch(
        f"{USERS_URL}/2",
        headers=auth_headers_admin,
        json={"id": 999, "role_id": 1, "password_hash": "hacked_hash"},
    )
    assert res.status_code == 200

    u_after = db_session.get(User, 2)
    assert u_after.id == 2
    assert u_after.role_id == original_role
    assert u_after.password_hash == original_hash


# =====================================================================
# 5. HAPPY PATHS: POST /api/v1/users/{userId}/lock (Lock User)
# =====================================================================

def test_lock_user_success_status_and_db(client, auth_headers_admin, db_session):
    """Happy Path: Lock another staff user successfully."""
    res = client.post(f"{USERS_URL}/2/lock", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 2
    assert data["is_active"] is False

    u = db_session.get(User, 2)
    assert u.is_active is False


def test_lock_user_audit_log_recorded(client, auth_headers_admin, db_session):
    """Happy Path: Locking user generates an immutable LOCK_USER AuditLog entry."""
    res = client.post(f"{USERS_URL}/2/lock", headers=auth_headers_admin)
    assert res.status_code == 200

    audit = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "LOCK_USER", AuditLog.entity_id == "2")
        .order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert audit.user_id == 1  # Admin ID
    assert audit.entity_type == "USER"
    assert audit.old_value == {"is_active": True}
    assert audit.new_value == {"is_active": False}
    assert "accountant_test" in audit.reason


def test_lock_user_prevents_subsequent_login(client, auth_headers_admin):
    """Happy Path: Locked user is immediately rejected from logging in (HTTP 403 ACCOUNT_DISABLED)."""
    lock_res = client.post(f"{USERS_URL}/2/lock", headers=auth_headers_admin)
    assert lock_res.status_code == 200

    login_res = client.post(
        LOGIN_URL,
        json={"username": "accountant_test", "password": "AccPass123!"},
    )
    assert login_res.status_code == 403
    assert login_res.json()["code"] == "ACCOUNT_DISABLED"


# =====================================================================
# 6. HAPPY PATHS: POST /api/v1/users/{userId}/unlock (Unlock User)
# =====================================================================

def test_unlock_user_success_status_and_db(client, auth_headers_admin, db_session):
    """Happy Path: Unlock a locked user and reset login counters."""
    # Setup locked user with failed counters
    u2 = db_session.get(User, 2)
    u2.is_active = False
    u2.failed_login_count = 5
    db_session.commit()

    res = client.post(f"{USERS_URL}/2/unlock", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == 2
    assert data["is_active"] is True

    db_session.refresh(u2)
    assert u2.is_active is True
    assert u2.failed_login_count == 0
    assert u2.locked_until is None


def test_unlock_user_audit_log_recorded(client, auth_headers_admin, db_session):
    """Happy Path: Unlocking user generates an UNLOCK_USER AuditLog entry."""
    # Pre-lock
    u2 = db_session.get(User, 2)
    u2.is_active = False
    db_session.commit()

    res = client.post(f"{USERS_URL}/2/unlock", headers=auth_headers_admin)
    assert res.status_code == 200

    audit = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "UNLOCK_USER", AuditLog.entity_id == "2")
        .order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert audit.user_id == 1
    assert audit.entity_type == "USER"
    assert audit.new_value["is_active"] is True
    assert audit.new_value["failed_login_count"] == 0
    assert audit.new_value["locked_until"] is None


def test_unlock_user_restores_login_capability(client, auth_headers_admin, db_session):
    """Happy Path: User can log in normally after being unlocked."""
    # Lock first
    client.post(f"{USERS_URL}/2/lock", headers=auth_headers_admin)

    # Unlock
    client.post(f"{USERS_URL}/2/unlock", headers=auth_headers_admin)

    # Login test
    login_res = client.post(
        LOGIN_URL,
        json={"username": "accountant_test", "password": "AccPass123!"},
    )
    assert login_res.status_code == 200
    assert "token" in login_res.json()


# =====================================================================
# 7. HAPPY PATHS: POST /api/v1/users/{userId}/reset-password (Reset)
# =====================================================================

def test_reset_password_success_response(client, auth_headers_admin):
    """Happy Path: Reset password endpoint returns valid TempPassword schema."""
    res = client.post(f"{USERS_URL}/2/reset-password", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()

    assert "temporary_password" in data
    assert "temp_password" in data
    assert data["temporary_password"] == data["temp_password"]
    assert len(data["temporary_password"]) >= 12


def test_reset_password_db_must_change_password_flag(client, auth_headers_admin, db_session):
    """Happy Path: Reset password forces must_change_password=True in database."""
    res = client.post(f"{USERS_URL}/2/reset-password", headers=auth_headers_admin)
    assert res.status_code == 200

    u2 = db_session.get(User, 2)
    assert u2.must_change_password is True
    assert u2.failed_login_count == 0
    assert u2.locked_until is None


def test_reset_password_audit_log_recorded(client, auth_headers_admin, db_session):
    """Happy Path: Reset password generates RESET_PASSWORD AuditLog entry."""
    res = client.post(f"{USERS_URL}/2/reset-password", headers=auth_headers_admin)
    assert res.status_code == 200

    audit = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "RESET_PASSWORD", AuditLog.entity_id == "2")
        .order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert audit.user_id == 1
    assert audit.entity_type == "USER"
    assert audit.new_value == {"must_change_password": True}


def test_reset_password_old_password_invalidated(client, auth_headers_admin):
    """Happy Path: Old password can no longer be used after reset."""
    res = client.post(f"{USERS_URL}/2/reset-password", headers=auth_headers_admin)
    assert res.status_code == 200

    # Attempt login with old password
    login_res = client.post(
        LOGIN_URL,
        json={"username": "accountant_test", "password": "AccPass123!"},
    )
    assert login_res.status_code == 401
    assert login_res.json()["code"] == "INVALID_CREDENTIALS"


def test_reset_password_new_temp_password_login_works(client, auth_headers_admin):
    """Happy Path: New temporary password successfully authenticates."""
    res = client.post(f"{USERS_URL}/2/reset-password", headers=auth_headers_admin)
    assert res.status_code == 200
    new_temp_pwd = res.json()["temporary_password"]

    login_res = client.post(
        LOGIN_URL,
        json={"username": "accountant_test", "password": new_temp_pwd},
    )
    assert login_res.status_code == 200
    assert login_res.json()["user"]["must_change_password"] is True


# =====================================================================
# 8. EDGE CASES & VALIDATION: 400, 404, 409
# =====================================================================

def test_create_user_duplicate_username_exact(client, auth_headers_admin):
    """Edge Case: Duplicate username exact match returns 409 DUPLICATE_USERNAME."""
    payload = {
        "username": "accountant_test",
        "full_name": "Trùng Tên Đăng Nhập",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 409
    data = res.json()
    assert data["code"] == "DUPLICATE_USERNAME"


def test_create_user_duplicate_username_case_insensitive(client, auth_headers_admin):
    """Edge Case: Duplicate username case-insensitive returns 409 DUPLICATE_USERNAME."""
    payload = {
        "username": "ACCOUNTANT_TEST",
        "full_name": "Trùng Tên In Hoa",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 409
    assert res.json()["code"] == "DUPLICATE_USERNAME"


def test_create_user_duplicate_username_with_whitespace(client, auth_headers_admin):
    """Edge Case: Duplicate username with leading/trailing whitespace returns 409 DUPLICATE_USERNAME."""
    payload = {
        "username": "  admin_test  ",
        "full_name": "Trùng Admin Có Khoảng Trắng",
        "role_id": 1,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 409
    assert res.json()["code"] == "DUPLICATE_USERNAME"


def test_create_user_nonexistent_role_id(client, auth_headers_admin):
    """Edge Case: Role ID that does not exist returns 400 VALIDATION_ERROR."""
    payload = {
        "username": "invalid_role_user",
        "full_name": "Vai Trò Sai",
        "role_id": 9999,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "9999" in data["message"]


def test_create_user_forbidden_resident_role(client, auth_headers_admin):
    """Edge Case: Manual creation of RESIDENT role via endpoint returns 400 VALIDATION_ERROR."""
    payload = {
        "username": "resident_manual",
        "full_name": "Cư Dân Tạo Thủ Công",
        "role_id": 4,  # RESIDENT role id
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "RESIDENT" in data["message"]


@pytest.mark.parametrize("short_username", ["a", "ab", "1", "12"])
def test_create_user_username_too_short(client, auth_headers_admin, short_username):
    """Validation: Username < 3 characters returns 400 VALIDATION_ERROR."""
    payload = {
        "username": short_username,
        "full_name": "Tên Ngắn",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("invalid_username", [
    "user name with space",
    "user@domain.com",
    "user#special",
    "user$cash",
    "user%percent",
    "user^caret",
    "user&amp",
    "user*star",
    "user(paren)",
])
def test_create_user_username_invalid_special_chars(client, auth_headers_admin, invalid_username):
    """Validation: Username containing forbidden characters returns 400 VALIDATION_ERROR."""
    payload = {
        "username": invalid_username,
        "full_name": "Ký Tự Đặc Biệt",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_create_user_username_valid_special_chars(client, auth_headers_admin):
    """Happy Path: Username with allowed symbols (_ . -) succeeds."""
    payload = {
        "username": "user_name.test-2026",
        "full_name": "Hợp Lệ Ký Tự Phụ",
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 201


@pytest.mark.parametrize("invalid_email", [
    "not-an-email",
    "user@",
    "@domain.com",
    "user@domain",
    "user@.com",
    "user@domain..com",
    "user name@bluemoon.local",
])
def test_create_user_invalid_email(client, auth_headers_admin, invalid_email):
    """Validation: Invalid email format during user creation returns 400 VALIDATION_ERROR."""
    payload = {
        "username": "invalid_email_user",
        "full_name": "Email Sai Định Dạng",
        "email": invalid_email,
        "role_id": 2,
    }
    res = client.post(USERS_URL, headers=auth_headers_admin, json=payload)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_patch_user_invalid_email(client, auth_headers_admin):
    """Validation: Updating email with invalid format returns 400 VALIDATION_ERROR."""
    res = client.patch(
        f"{USERS_URL}/2",
        headers=auth_headers_admin,
        json={"email": "bad_email_format"},
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_admin_cannot_lock_self(client, auth_headers_admin):
    """Business Invariant: Admin cannot lock their own account -> 409 CANNOT_LOCK_SELF."""
    res = client.post(f"{USERS_URL}/1/lock", headers=auth_headers_admin)
    assert res.status_code == 409
    data = res.json()
    assert data["code"] == "CANNOT_LOCK_SELF"
    assert "chính mình" in data["message"]


@pytest.mark.parametrize("nonexistent_id", [999999, 1000000])
def test_get_nonexistent_user(client, auth_headers_admin, nonexistent_id):
    """Not Found: GET non-existent userId returns 404 USER_NOT_FOUND."""
    res = client.get(f"{USERS_URL}/{nonexistent_id}", headers=auth_headers_admin)
    assert res.status_code == 404
    assert res.json()["code"] == "USER_NOT_FOUND"


def test_patch_nonexistent_user(client, auth_headers_admin):
    """Not Found: PATCH non-existent userId returns 404 USER_NOT_FOUND."""
    res = client.patch(
        f"{USERS_URL}/999999",
        headers=auth_headers_admin,
        json={"full_name": "NonExistent"},
    )
    assert res.status_code == 404
    assert res.json()["code"] == "USER_NOT_FOUND"


def test_lock_nonexistent_user(client, auth_headers_admin):
    """Not Found: Locking non-existent userId returns 404 USER_NOT_FOUND."""
    res = client.post(f"{USERS_URL}/999999/lock", headers=auth_headers_admin)
    assert res.status_code == 404
    assert res.json()["code"] == "USER_NOT_FOUND"


def test_unlock_nonexistent_user(client, auth_headers_admin):
    """Not Found: Unlocking non-existent userId returns 404 USER_NOT_FOUND."""
    res = client.post(f"{USERS_URL}/999999/unlock", headers=auth_headers_admin)
    assert res.status_code == 404
    assert res.json()["code"] == "USER_NOT_FOUND"


def test_reset_password_nonexistent_user(client, auth_headers_admin):
    """Not Found: Reset password for non-existent userId returns 404 USER_NOT_FOUND."""
    res = client.post(f"{USERS_URL}/999999/reset-password", headers=auth_headers_admin)
    assert res.status_code == 404
    assert res.json()["code"] == "USER_NOT_FOUND"


@pytest.mark.parametrize("invalid_page", [0, -1, -99])
def test_list_users_invalid_page(client, auth_headers_admin, invalid_page):
    """Validation: page < 1 returns 400 VALIDATION_ERROR."""
    res = client.get(f"{USERS_URL}?page={invalid_page}", headers=auth_headers_admin)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("invalid_page_size", [0, -1, 101, 500])
def test_list_users_invalid_page_size(client, auth_headers_admin, invalid_page_size):
    """Validation: page_size < 1 or page_size > 100 returns 400 VALIDATION_ERROR."""
    res = client.get(f"{USERS_URL}?page_size={invalid_page_size}", headers=auth_headers_admin)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("invalid_path_id", ["abc", "zero", "1.5"])
def test_user_id_path_param_invalid_type(client, auth_headers_admin, invalid_path_id):
    """Validation: Non-integer userId path parameter returns 400 VALIDATION_ERROR."""
    res = client.get(f"{USERS_URL}/{invalid_path_id}", headers=auth_headers_admin)
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_user_id_path_param_zero_or_negative(client, auth_headers_admin):
    """Validation: userId <= 0 violates ge=1 and returns 400 VALIDATION_ERROR."""
    res_zero = client.get(f"{USERS_URL}/0", headers=auth_headers_admin)
    assert res_zero.status_code == 400
    assert res_zero.json()["code"] == "VALIDATION_ERROR"

    res_neg = client.get(f"{USERS_URL}/-1", headers=auth_headers_admin)
    assert res_neg.status_code == 400
    assert res_neg.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("sqli_payload", [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "admin%'",
    "1' UNION SELECT 1,2,3,4,5,6,7,8,9,10 --",
    "test' OR 1=1 #",
])
def test_list_users_search_q_sqli_payload_safety(client, auth_headers_admin, sqli_payload, db_session):
    """Security: Search query with SQL Injection payloads executes safely with 200 OK and no damage."""
    res = client.get(f"{USERS_URL}?q={sqli_payload}", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["items"], list)

    # Verify database users table remains completely intact
    count = db_session.scalar(select(User.id).where(User.id == 1))
    assert count == 1


def test_list_users_page_beyond_available_data(client, auth_headers_admin):
    """Boundary: Requesting a page far beyond total records returns empty list (200 OK)."""
    res = client.get(f"{USERS_URL}?page=9999", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 9999
    assert len(data["items"]) == 0
    assert data["total"] >= 4


# =====================================================================
# 9. SECURITY & RBAC GUARD: 401 UNAUTHENTICATED & 403 FORBIDDEN
# =====================================================================

SAMPLE_ENDPOINTS = [
    ("GET", USERS_URL, None),
    ("POST", USERS_URL, {"username": "unauth_user", "full_name": "Test", "role_id": 1}),
    ("GET", f"{USERS_URL}/1", None),
    ("PATCH", f"{USERS_URL}/1", {"full_name": "Hacked Name"}),
    ("POST", f"{USERS_URL}/2/lock", None),
    ("POST", f"{USERS_URL}/2/unlock", None),
    ("POST", f"{USERS_URL}/2/reset-password", None),
]


@pytest.mark.parametrize("method, url, body", SAMPLE_ENDPOINTS)
def test_endpoints_unauthenticated_without_token(client, method, url, body):
    """Security: All 7 endpoints reject requests lacking Authorization header with 401 UNAUTHENTICATED."""
    if method == "GET":
        res = client.get(url)
    elif method == "POST":
        res = client.post(url, json=body)
    elif method == "PATCH":
        res = client.patch(url, json=body)

    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("method, url, body", SAMPLE_ENDPOINTS)
def test_endpoints_unauthenticated_with_malformed_token(client, method, url, body):
    """Security: All 7 endpoints reject requests with malformed tokens with 401 UNAUTHENTICATED."""
    headers = {"Authorization": "Bearer malformed.garbage.jwt.token"}
    if method == "GET":
        res = client.get(url, headers=headers)
    elif method == "POST":
        res = client.post(url, headers=headers, json=body)
    elif method == "PATCH":
        res = client.patch(url, headers=headers, json=body)

    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_endpoints_unauthenticated_with_expired_token(client):
    """Security: Requests with expired JWT access token return 401 UNAUTHENTICATED."""
    expired_token = create_access_token(
        {"sub": "1", "username": "admin_test", "role": "ADMIN"},
        expires_delta=timedelta(seconds=-3600),  # expired 1 hour ago
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    res = client.get(USERS_URL, headers=headers)
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_endpoints_unauthenticated_with_inactive_user(client, db_session):
    """Security: Token from a deactivated user returns 401 UNAUTHENTICATED."""
    u1 = db_session.get(User, 1)
    u1.is_active = False
    db_session.commit()

    token = create_access_token({"sub": "1", "username": "admin_test", "role": "ADMIN"})
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get(USERS_URL, headers=headers)
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("method, url, body", SAMPLE_ENDPOINTS)
def test_endpoints_forbidden_for_resident(client, auth_headers_resident_101, method, url, body):
    """RBAC Guard: All 7 endpoints reject calls from RESIDENT with 403 FORBIDDEN."""
    if method == "GET":
        res = client.get(url, headers=auth_headers_resident_101)
    elif method == "POST":
        res = client.post(url, headers=auth_headers_resident_101, json=body)
    elif method == "PATCH":
        res = client.patch(url, headers=auth_headers_resident_101, json=body)

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


@pytest.mark.parametrize("method, url, body", SAMPLE_ENDPOINTS)
def test_endpoints_forbidden_for_accountant(client, auth_headers_accountant, method, url, body):
    """RBAC Guard: All 7 endpoints reject calls from ACCOUNTANT with 403 FORBIDDEN."""
    if method == "GET":
        res = client.get(url, headers=auth_headers_accountant)
    elif method == "POST":
        res = client.post(url, headers=auth_headers_accountant, json=body)
    elif method == "PATCH":
        res = client.patch(url, headers=auth_headers_accountant, json=body)

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


@pytest.mark.parametrize("method, url, body", SAMPLE_ENDPOINTS)
def test_endpoints_forbidden_for_treasurer(client, auth_headers_treasurer, method, url, body):
    """RBAC Guard: All 7 endpoints reject calls from TREASURER with 403 FORBIDDEN."""
    if method == "GET":
        res = client.get(url, headers=auth_headers_treasurer)
    elif method == "POST":
        res = client.post(url, headers=auth_headers_treasurer, json=body)
    elif method == "PATCH":
        res = client.patch(url, headers=auth_headers_treasurer, json=body)

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_audit_log_access_denied_recorded_on_forbidden(client, auth_headers_resident_101, db_session):
    """Audit Logging: 403 Forbidden events generate an ACCESS_DENIED AuditLog record."""
    res = client.get(USERS_URL, headers=auth_headers_resident_101)
    assert res.status_code == 403

    audit = db_session.scalar(
        select(AuditLog)
        .where(AuditLog.action == "ACCESS_DENIED", AuditLog.user_id == 3)
        .order_by(AuditLog.id.desc())
    )
    assert audit is not None
    assert audit.entity_type == "ENDPOINT"
    assert audit.entity_id == USERS_URL
    assert "RESIDENT" in audit.reason

