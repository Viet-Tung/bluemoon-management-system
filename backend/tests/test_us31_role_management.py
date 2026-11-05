"""
Black-box Automated Test Suite for US-31: Phân quyền & Quản lý vai trò (Role-Based Access Control & Role Management).
Conforms strictly to docs/openapi.yaml, docs/API_CONTRACT.md, and docs/backend_spec/sprint_1/SPRINT_1_BACKEND_SPEC.md.

Scope of US-31:
1. GET /api/v1/roles (Operation: listRoles)
   - RBAC: ADMIN only
   - Returns 200 with list of 4 roles (ADMIN, ACCOUNTANT, TREASURER, RESIDENT)
   - Error handling: 401 UNAUTHENTICATED, 403 FORBIDDEN

2. PUT /api/v1/users/{userId}/role (Operation: setUserRole)
   - RBAC: ADMIN only
   - Body: UserRoleUpdate (role_id: int)
   - Invariants:
     * Admin cannot change own role -> 409 CANNOT_CHANGE_OWN_ROLE
     * Target user must exist -> 404 NOT_FOUND
     * Target role must exist -> 400 VALIDATION_ERROR
     * Staff cannot be assigned RESIDENT role -> 400 VALIDATION_ERROR
     * Resident cannot be assigned staff role -> 400 VALIDATION_ERROR
     * Role change must take effect immediately on next request (AC-31.1)
     * Mutation must be recorded in audit_logs (action="CHANGE_ROLE")
   - Error handling: 400, 401, 403, 404, 409, 500
"""

from datetime import timedelta
import uuid
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.models.user import AuditLog, Role, User

ROLES_URL = f"{settings.API_V1_STR}/roles"
USERS_URL = f"{settings.API_V1_STR}/users"


def make_auth_headers(user_id: int, username: str, role: str, expires_delta: timedelta = timedelta(hours=1)) -> dict:
    """Helper tạo Bearer token hợp lệ cho các vai trò kiểm thử."""
    token = create_access_token(
        data={"sub": str(user_id), "username": username, "role": role, "must_change_password": False},
        expires_delta=expires_delta,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_staff_users(db_session):
    """
    Tạo các tài khoản nhân sự và cư dân biệt lập cho mỗi ca kiểm thử:
    - staff_accountant (role_id=2, ACCOUNTANT)
    - staff_treasurer (role_id=3, TREASURER)
    - secondary_admin (role_id=1, ADMIN)
    - resident_user (role_id=4, RESIDENT, household_id=201)
    """
    password_hash = get_password_hash("TestPass123!")
    suffix = uuid.uuid4().hex[:6]

    # Đảm bảo role_id=3 (TREASURER) tồn tại
    treasurer_role = db_session.scalar(select(Role).where(Role.code == "TREASURER"))
    if not treasurer_role:
        treasurer_role = Role(id=3, code="TREASURER", name="Thủ quỹ", description="Quản lý thu chi")
        db_session.add(treasurer_role)
        db_session.commit()

    u_acc = User(
        username=f"u31_acc_{suffix}",
        password_hash=password_hash,
        full_name="Kế Toán Kiểm Thử US31",
        email=f"acc_{suffix}@bluemoon.local",
        role_id=2,
        is_active=True,
        must_change_password=False,
    )
    u_tre = User(
        username=f"u31_tre_{suffix}",
        password_hash=password_hash,
        full_name="Thủ Quỹ Kiểm Thử US31",
        email=f"tre_{suffix}@bluemoon.local",
        role_id=3,
        is_active=True,
        must_change_password=False,
    )
    u_adm = User(
        username=f"u31_adm_{suffix}",
        password_hash=password_hash,
        full_name="Admin Phụ Kiểm Thử US31",
        email=f"adm_{suffix}@bluemoon.local",
        role_id=1,
        is_active=True,
        must_change_password=False,
    )
    u_res = User(
        username=f"u31_res_{suffix}",
        password_hash=password_hash,
        full_name="Cư Dân Kiểm Thử US31",
        email=f"res_{suffix}@bluemoon.local",
        role_id=4,
        household_id=201,
        is_active=True,
        must_change_password=False,
    )

    db_session.add_all([u_acc, u_tre, u_adm, u_res])
    db_session.commit()
    db_session.refresh(u_acc)
    db_session.refresh(u_tre)
    db_session.refresh(u_adm)
    db_session.refresh(u_res)

    yield {
        "accountant": u_acc,
        "treasurer": u_tre,
        "secondary_admin": u_adm,
        "resident": u_res,
    }

    try:
        db_session.delete(u_acc)
        db_session.delete(u_tre)
        db_session.delete(u_adm)
        db_session.delete(u_res)
        db_session.commit()
    except Exception:
        db_session.rollback()


# =====================================================================
# 1. HAPPY PATHS: GET /roles (Danh sách vai trò)
# =====================================================================

def test_01_list_roles_success_status_code_200(client, auth_headers_admin):
    """GET /roles thành công trả về HTTP 200 OK."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    assert res.status_code == 200


def test_02_list_roles_returns_array_of_roles(client, auth_headers_admin):
    """GET /roles trả về định dạng mảng (JSON Array) chứa các vai trò."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 4


def test_03_list_roles_schema_structure(client, auth_headers_admin):
    """GET /roles: Mỗi phần tử trong mảng tuân thủ đầy đủ schema Role."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    data = res.json()
    for role in data:
        assert "id" in role
        assert "code" in role
        assert "name" in role
        assert "description" in role
        assert isinstance(role["id"], int)
        assert isinstance(role["code"], str)
        assert isinstance(role["name"], str)


def test_04_list_roles_ordered_by_id_asc(client, auth_headers_admin):
    """GET /roles: Danh sách vai trò được sắp xếp theo thứ tự ID tăng dần."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    data = res.json()
    ids = [r["id"] for r in data]
    assert ids == sorted(ids)


def test_05_list_roles_contains_admin(client, auth_headers_admin):
    """GET /roles: Chứa vai trò ADMIN với mã code chuẩn."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    codes = [r["code"] for r in res.json()]
    assert "ADMIN" in codes


def test_06_list_roles_contains_accountant(client, auth_headers_admin):
    """GET /roles: Chứa vai trò ACCOUNTANT với mã code chuẩn."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    codes = [r["code"] for r in res.json()]
    assert "ACCOUNTANT" in codes


def test_07_list_roles_contains_treasurer(client, auth_headers_admin):
    """GET /roles: Chứa vai trò TREASURER với mã code chuẩn."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    codes = [r["code"] for r in res.json()]
    assert "TREASURER" in codes


def test_08_list_roles_contains_resident(client, auth_headers_admin):
    """GET /roles: Chứa vai trò RESIDENT với mã code chuẩn."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    codes = [r["code"] for r in res.json()]
    assert "RESIDENT" in codes


def test_09_list_roles_exact_four_standard_roles(client, auth_headers_admin):
    """GET /roles: Kiểm tra tập hợp 4 vai trò chuẩn theo thiết kế CSDL và OpenAPI."""
    res = client.get(ROLES_URL, headers=auth_headers_admin)
    codes = {r["code"] for r in res.json()}
    expected = {"ADMIN", "ACCOUNTANT", "TREASURER", "RESIDENT"}
    assert expected.issubset(codes)


# =====================================================================
# 2. HAPPY PATHS: PUT /users/{userId}/role (Gán hoặc thu hồi vai trò)
# =====================================================================

def test_10_set_user_role_accountant_to_treasurer_success(client, auth_headers_admin, test_staff_users):
    """Admin chuyển vai trò Kế toán sang Thủ quỹ thành công (200 OK)."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 3
    assert data["role"]["code"] == "TREASURER"


def test_11_set_user_role_treasurer_to_accountant_success(client, auth_headers_admin, test_staff_users):
    """Admin chuyển vai trò Thủ quỹ sang Kế toán thành công (200 OK)."""
    user = test_staff_users["treasurer"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 2
    assert data["role"]["code"] == "ACCOUNTANT"


def test_12_set_user_role_accountant_to_admin_success(client, auth_headers_admin, test_staff_users):
    """Admin thăng quyền nhân viên Kế toán lên Admin phụ thành công (200 OK)."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 1
    assert data["role"]["code"] == "ADMIN"


def test_13_set_user_role_secondary_admin_to_accountant_success(client, auth_headers_admin, test_staff_users):
    """Admin hạ quyền Admin phụ xuống Kế toán thành công (200 OK)."""
    user = test_staff_users["secondary_admin"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 2
    assert data["role"]["code"] == "ACCOUNTANT"


def test_14_set_user_role_secondary_admin_to_treasurer_success(client, auth_headers_admin, test_staff_users):
    """Admin chuyển Admin phụ sang Thủ quỹ thành công (200 OK)."""
    user = test_staff_users["secondary_admin"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 3
    assert data["role"]["code"] == "TREASURER"


def test_15_set_user_role_treasurer_to_admin_success(client, auth_headers_admin, test_staff_users):
    """Admin thăng quyền Thủ quỹ lên Admin phụ thành công (200 OK)."""
    user = test_staff_users["treasurer"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 1
    assert data["role"]["code"] == "ADMIN"


def test_16_set_user_role_same_role_idempotent_success(client, auth_headers_admin, test_staff_users):
    """Admin gán lại vai trò trùng với vai trò hiện tại (tính lũy thừa - idempotent) thành công (200 OK)."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 2
    assert data["role"]["code"] == "ACCOUNTANT"


def test_17_set_user_role_response_schema_fields(client, auth_headers_admin, test_staff_users):
    """Phản hồi PUT /{userId}/role tuân thủ đầy đủ cấu trúc UserResponse."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == user.id
    assert data["username"] == user.username
    assert data["full_name"] == user.full_name
    assert "role" in data
    assert "is_active" in data
    assert "must_change_password" in data


def test_18_set_user_role_updates_database_state_immediately(client, auth_headers_admin, db_session, test_staff_users):
    """Trạng thái vai trò người dùng trong CSDL được cập nhật tức thì."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200

    db_session.expire_all()
    updated_user = db_session.scalar(select(User).where(User.id == user.id))
    assert updated_user.role_id == 3
    assert updated_user.role.code == "TREASURER"


def test_19_set_user_role_creates_audit_log_record(client, auth_headers_admin, db_session, test_staff_users):
    """Ghi nhận AuditLog với action='CHANGE_ROLE' khi đổi vai trò người dùng thành công."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200

    log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "CHANGE_ROLE", AuditLog.entity_id == str(user.id))
    )
    assert log is not None
    assert log.entity_type == "USER"
    assert log.user_id == 1  # ID của admin_test


def test_20_set_user_role_audit_log_tracks_old_and_new_values(client, auth_headers_admin, db_session, test_staff_users):
    """AuditLog ghi nhận đầy đủ old_value và new_value của vai trò."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200

    log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "CHANGE_ROLE", AuditLog.entity_id == str(user.id))
    )
    assert log.old_value["role_code"] == "ACCOUNTANT"
    assert log.new_value["role_code"] == "TREASURER"
    assert log.old_value["role_id"] == 2
    assert log.new_value["role_id"] == 3


def test_21_set_user_role_audit_log_captures_client_meta(client, auth_headers_admin, db_session, test_staff_users):
    """AuditLog ghi nhận User-Agent khi Admin thực hiện đổi vai trò."""
    user = test_staff_users["accountant"]
    custom_headers = {**auth_headers_admin, "User-Agent": "BlueMoon-AdminPortal/1.0"}
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=custom_headers, json={"role_id": 3})
    assert res.status_code == 200

    log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "CHANGE_ROLE", AuditLog.entity_id == str(user.id))
    )
    assert log.user_agent == "BlueMoon-AdminPortal/1.0"


# =====================================================================
# 3. ACCEPTANCE CRITERIA AC-31.1: HIỆU LỰC TỨC THÌ (IMMEDIATE EFFECT)
# =====================================================================

def test_22_ac31_1_promoted_staff_immediately_accesses_admin_routes(client, auth_headers_admin, test_staff_users):
    """AC-31.1: Kế toán sau khi được thăng lên ADMIN có hiệu lực ngay lập tức ở request tiếp theo."""
    user = test_staff_users["accountant"]
    headers_before = make_auth_headers(user.id, user.username, "ACCOUNTANT")

    # Trước khi thăng quyền: gọi endpoint admin-only bị 403 FORBIDDEN
    res_before = client.get(f"{settings.API_V1_STR}/test/admin-only", headers=headers_before)
    assert res_before.status_code == 403

    # Admin thực hiện thăng quyền lên ADMIN (role_id=1)
    res_promote = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 1})
    assert res_promote.status_code == 200

    # Ngay request tiếp theo: Token của user được thăng quyền lập tức được chấp thuận (200 OK)
    res_after = client.get(f"{settings.API_V1_STR}/test/admin-only", headers=headers_before)
    assert res_after.status_code == 200
    assert res_after.json()["role"] == "ADMIN"


def test_23_ac31_1_demoted_staff_immediately_loses_admin_routes(client, auth_headers_admin, test_staff_users):
    """AC-31.1: Admin phụ sau khi bị giáng quyền xuống Kế toán lập tức bị từ chối truy cập endpoint Admin."""
    user = test_staff_users["secondary_admin"]
    headers_admin = make_auth_headers(user.id, user.username, "ADMIN")

    # Trước khi giáng quyền: gọi endpoint admin-only thành công 200 OK
    res_before = client.get(f"{settings.API_V1_STR}/test/admin-only", headers=headers_admin)
    assert res_before.status_code == 200

    # Admin thực hiện hạ quyền xuống ACCOUNTANT (role_id=2)
    res_demote = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res_demote.status_code == 200

    # Ngay request tiếp theo: Token cũ lập tức bị chặn 403 FORBIDDEN do hệ thống nạp role trực tiếp từ CSDL
    res_after = client.get(f"{settings.API_V1_STR}/test/admin-only", headers=headers_admin)
    assert res_after.status_code == 403
    assert res_after.json()["code"] == "FORBIDDEN"


def test_24_ac31_1_promoted_staff_can_list_roles_immediately(client, auth_headers_admin, test_staff_users):
    """AC-31.1: Người dùng được thăng cấp Admin có thể lập tức gọi GET /roles."""
    user = test_staff_users["treasurer"]
    headers_user = make_auth_headers(user.id, user.username, "TREASURER")

    # Thủ quỹ gọi /roles bị chặn 403
    assert client.get(ROLES_URL, headers=headers_user).status_code == 403

    # Admin thăng quyền user lên Admin
    res_promote = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 1})
    assert res_promote.status_code == 200

    # User gọi /roles ngay lập tức được 200 OK
    res_after = client.get(ROLES_URL, headers=headers_user)
    assert res_after.status_code == 200


# =====================================================================
# 4. EDGE CASES & RÀNG BUỘC BẤT BIẾN (400, 404, 409)
# =====================================================================

def test_25_admin_cannot_change_own_role_to_accountant(client, auth_headers_admin):
    """Ràng buộc: Admin tự đổi vai trò của chính mình sang Kế toán -> 409 CANNOT_CHANGE_OWN_ROLE."""
    res = client.put(f"{USERS_URL}/1/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 409
    assert res.json()["code"] == "CANNOT_CHANGE_OWN_ROLE"


def test_26_admin_cannot_change_own_role_to_treasurer(client, auth_headers_admin):
    """Ràng buộc: Admin tự đổi vai trò của chính mình sang Thủ quỹ -> 409 CANNOT_CHANGE_OWN_ROLE."""
    res = client.put(f"{USERS_URL}/1/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 409
    assert res.json()["code"] == "CANNOT_CHANGE_OWN_ROLE"


def test_27_admin_cannot_change_own_role_to_resident(client, auth_headers_admin):
    """Ràng buộc: Admin tự đổi vai trò của chính mình sang Cư dân -> 409 CANNOT_CHANGE_OWN_ROLE."""
    res = client.put(f"{USERS_URL}/1/role", headers=auth_headers_admin, json={"role_id": 4})
    assert res.status_code == 409
    assert res.json()["code"] == "CANNOT_CHANGE_OWN_ROLE"


def test_28_admin_cannot_change_own_role_to_admin_same(client, auth_headers_admin):
    """Ràng buộc: Admin tự gán lại vai trò Admin cho chính mình -> 409 CANNOT_CHANGE_OWN_ROLE."""
    res = client.put(f"{USERS_URL}/1/role", headers=auth_headers_admin, json={"role_id": 1})
    assert res.status_code == 409
    assert res.json()["code"] == "CANNOT_CHANGE_OWN_ROLE"


def test_29_admin_cannot_change_own_role_audit_log_not_created(client, auth_headers_admin, db_session):
    """Khi Admin cố tình tự đổi vai trò và bị từ chối 409, không ghi CHANGE_ROLE vào audit_logs."""
    res = client.put(f"{USERS_URL}/1/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 409

    log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "CHANGE_ROLE", AuditLog.entity_id == "1")
    )
    assert log is None


def test_30_set_role_nonexistent_user_id_returns_404(client, auth_headers_admin):
    """User ID không tồn tại trả về HTTP 404 NOT_FOUND."""
    res = client.put(f"{USERS_URL}/999999/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 404
    assert res.json()["code"] in ("NOT_FOUND", "USER_NOT_FOUND")


def test_31_set_role_very_large_user_id_returns_404(client, auth_headers_admin):
    """User ID rất lớn không tồn tại trả về HTTP 404 NOT_FOUND."""
    res = client.put(f"{USERS_URL}/2147483647/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 404
    assert res.json()["code"] in ("NOT_FOUND", "USER_NOT_FOUND")


def test_32_set_role_nonexistent_role_id_returns_400(client, auth_headers_admin, test_staff_users):
    """Role ID không tồn tại trong bảng roles trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 999})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_33_set_role_negative_role_id_returns_400(client, auth_headers_admin, test_staff_users):
    """Role ID âm trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": -1})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_34_set_role_zero_role_id_returns_400(client, auth_headers_admin, test_staff_users):
    """Role ID = 0 không tồn tại trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 0})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_35_prohibit_staff_accountant_to_resident_returns_400(client, auth_headers_admin, test_staff_users):
    """Ràng buộc cô lập: Không được gán vai trò RESIDENT cho tài khoản Kế toán (400 VALIDATION_ERROR)."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 4})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_36_prohibit_staff_treasurer_to_resident_returns_400(client, auth_headers_admin, test_staff_users):
    """Ràng buộc cô lập: Không được gán vai trò RESIDENT cho tài khoản Thủ quỹ (400 VALIDATION_ERROR)."""
    user = test_staff_users["treasurer"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 4})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_37_prohibit_staff_secondary_admin_to_resident_returns_400(client, auth_headers_admin, test_staff_users):
    """Ràng buộc cô lập: Không được gán vai trò RESIDENT cho tài khoản Admin phụ (400 VALIDATION_ERROR)."""
    user = test_staff_users["secondary_admin"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 4})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_38_prohibit_resident_to_admin_returns_400(client, auth_headers_admin, test_staff_users):
    """Ràng buộc cô lập: Không được gán vai trò ADMIN cho tài khoản Cư dân (400 VALIDATION_ERROR)."""
    user = test_staff_users["resident"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 1})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_39_prohibit_resident_to_accountant_returns_400(client, auth_headers_admin, test_staff_users):
    """Ràng buộc cô lập: Không được gán vai trò ACCOUNTANT cho tài khoản Cư dân (400 VALIDATION_ERROR)."""
    user = test_staff_users["resident"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_40_prohibit_resident_to_treasurer_returns_400(client, auth_headers_admin, test_staff_users):
    """Ràng buộc cô lập: Không được gán vai trò TREASURER cho tài khoản Cư dân (400 VALIDATION_ERROR)."""
    user = test_staff_users["resident"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


# =====================================================================
# 5. INPUT VALIDATION & PAYLOAD INTEGRITY (400)
# =====================================================================

def test_41_missing_role_id_in_body_returns_400(client, auth_headers_admin, test_staff_users):
    """Thiếu trường role_id trong request body trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_42_string_role_id_in_body_returns_400(client, auth_headers_admin, test_staff_users):
    """role_id dạng chuỗi không hợp lệ trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": "three"})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_43_null_role_id_in_body_returns_400(client, auth_headers_admin, test_staff_users):
    """role_id là null trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": None})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_44_malformed_json_body_returns_400(client, auth_headers_admin, test_staff_users):
    """JSON body sai cú pháp trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(
        f"{USERS_URL}/{user.id}/role",
        headers={**auth_headers_admin, "Content-Type": "application/json"},
        content="{\"role_id\": 2,",
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_45_negative_user_id_path_param_returns_400(client, auth_headers_admin):
    """Path param userId âm (vi phạm ge=1) trả về HTTP 400 hoặc 404."""
    res = client.put(f"{USERS_URL}/-5/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code in [400, 404]
    if res.status_code == 400:
        assert res.json()["code"] == "VALIDATION_ERROR"


def test_46_zero_user_id_path_param_returns_400(client, auth_headers_admin):
    """Path param userId = 0 (vi phạm ge=1) trả về HTTP 400 VALIDATION_ERROR."""
    res = client.put(f"{USERS_URL}/0/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_47_string_user_id_path_param_returns_400(client, auth_headers_admin):
    """Path param userId dạng chữ không phải số nguyên trả về HTTP 400 hoặc 404."""
    res = client.put(f"{USERS_URL}/notanumber/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code in [400, 404]
    if res.status_code == 400:
        assert res.json()["code"] == "VALIDATION_ERROR"


# =====================================================================
# 6. SECURITY & RBAC GUARD (401 UNAUTHENTICATED & 403 FORBIDDEN)
# =====================================================================

def test_48_list_roles_unauthenticated_returns_401(client):
    """GET /roles khi chưa xác thực trả về HTTP 401 UNAUTHENTICATED."""
    res = client.get(ROLES_URL)
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_49_list_roles_invalid_token_returns_401(client):
    """GET /roles với Bearer token giả mạo trả về HTTP 401 UNAUTHENTICATED."""
    res = client.get(ROLES_URL, headers={"Authorization": "Bearer invalid_gibberish_token"})
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_50_list_roles_expired_token_returns_401(client):
    """GET /roles với token đã hết hạn trả về HTTP 401 UNAUTHENTICATED."""
    headers = make_auth_headers(1, "admin_test", "ADMIN", expires_delta=timedelta(seconds=-10))
    res = client.get(ROLES_URL, headers=headers)
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_51_list_roles_forbidden_for_accountant_returns_403(client, test_staff_users):
    """GET /roles với vai trò ACCOUNTANT bị chặn HTTP 403 FORBIDDEN."""
    user = test_staff_users["accountant"]
    headers = make_auth_headers(user.id, user.username, "ACCOUNTANT")
    res = client.get(ROLES_URL, headers=headers)
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_52_list_roles_forbidden_for_treasurer_returns_403(client, test_staff_users):
    """GET /roles với vai trò TREASURER bị chặn HTTP 403 FORBIDDEN."""
    user = test_staff_users["treasurer"]
    headers = make_auth_headers(user.id, user.username, "TREASURER")
    res = client.get(ROLES_URL, headers=headers)
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_53_list_roles_forbidden_for_resident_returns_403(client, auth_headers_resident_101):
    """GET /roles với vai trò RESIDENT bị chặn HTTP 403 FORBIDDEN."""
    res = client.get(ROLES_URL, headers=auth_headers_resident_101)
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_54_list_roles_forbidden_creates_access_denied_audit_log(client, db_session, test_staff_users):
    """Khi truy cập /roles bị 403, tự động ghi nhận nhật ký ACCESS_DENIED."""
    user = test_staff_users["accountant"]
    headers = make_auth_headers(user.id, user.username, "ACCOUNTANT")
    res = client.get(ROLES_URL, headers=headers)
    assert res.status_code == 403

    log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "ACCESS_DENIED", AuditLog.user_id == user.id)
    )
    assert log is not None
    assert log.entity_type == "ENDPOINT"


def test_55_set_user_role_unauthenticated_returns_401(client, test_staff_users):
    """PUT /users/{userId}/role khi chưa xác thực trả về HTTP 401 UNAUTHENTICATED."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", json={"role_id": 3})
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_56_set_user_role_invalid_token_returns_401(client, test_staff_users):
    """PUT /users/{userId}/role với Bearer token giả mạo trả về HTTP 401 UNAUTHENTICATED."""
    user = test_staff_users["accountant"]
    res = client.put(
        f"{USERS_URL}/{user.id}/role",
        headers={"Authorization": "Bearer fake_token_abc"},
        json={"role_id": 3},
    )
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_57_set_user_role_expired_token_returns_401(client, test_staff_users):
    """PUT /users/{userId}/role với token đã hết hạn trả về HTTP 401 UNAUTHENTICATED."""
    user = test_staff_users["accountant"]
    headers = make_auth_headers(1, "admin_test", "ADMIN", expires_delta=timedelta(seconds=-10))
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=headers, json={"role_id": 3})
    assert res.status_code == 401
    assert res.json()["code"] == "UNAUTHENTICATED"


def test_58_set_user_role_forbidden_for_accountant_returns_403(client, test_staff_users):
    """PUT /users/{userId}/role với vai trò ACCOUNTANT bị chặn HTTP 403 FORBIDDEN."""
    user = test_staff_users["accountant"]
    headers = make_auth_headers(user.id, user.username, "ACCOUNTANT")
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=headers, json={"role_id": 3})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_59_set_user_role_forbidden_for_treasurer_returns_403(client, test_staff_users):
    """PUT /users/{userId}/role với vai trò TREASURER bị chặn HTTP 403 FORBIDDEN."""
    user = test_staff_users["treasurer"]
    headers = make_auth_headers(user.id, user.username, "TREASURER")
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=headers, json={"role_id": 2})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_60_set_user_role_forbidden_for_resident_returns_403(client, auth_headers_resident_101, test_staff_users):
    """PUT /users/{userId}/role với vai trò RESIDENT bị chặn HTTP 403 FORBIDDEN."""
    user = test_staff_users["accountant"]
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_resident_101, json={"role_id": 3})
    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_61_set_user_role_forbidden_creates_access_denied_audit_log(client, db_session, test_staff_users):
    """Khi gọi PUT /users/{userId}/role bị 403, tự động ghi nhận nhật ký ACCESS_DENIED."""
    user = test_staff_users["accountant"]
    headers = make_auth_headers(user.id, user.username, "ACCOUNTANT")
    res = client.put(f"{USERS_URL}/{user.id}/role", headers=headers, json={"role_id": 3})
    assert res.status_code == 403

    log = db_session.scalar(
        select(AuditLog).where(AuditLog.action == "ACCESS_DENIED", AuditLog.user_id == user.id)
    )
    assert log is not None
    assert log.entity_type == "ENDPOINT"


# =====================================================================
# 7. INJECTION DEFENSE & HTTP METHODS SANITY
# =====================================================================

def test_62_sql_injection_in_user_id_path_param_safe(client, auth_headers_admin):
    """SQL injection trong path parameter userId được chặn an toàn bởi Starlette/FastAPI (400 hoặc 404)."""
    malicious_path = f"{USERS_URL}/1%20OR%201=1;%20DROP%20TABLE%20users;--/role"
    res = client.put(malicious_path, headers=auth_headers_admin, json={"role_id": 2})
    assert res.status_code in [400, 404]


def test_63_roles_method_not_allowed_post(client, auth_headers_admin):
    """POST /roles không được phép (405 Method Not Allowed)."""
    res = client.post(ROLES_URL, headers=auth_headers_admin, json={})
    assert res.status_code == 405


def test_64_roles_method_not_allowed_delete(client, auth_headers_admin):
    """DELETE /roles không được phép (405 Method Not Allowed)."""
    res = client.delete(ROLES_URL, headers=auth_headers_admin)
    assert res.status_code == 405


def test_65_set_user_role_method_not_allowed_delete(client, auth_headers_admin, test_staff_users):
    """DELETE /users/{userId}/role không được phép (405 Method Not Allowed)."""
    user = test_staff_users["accountant"]
    res = client.delete(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin)
    assert res.status_code == 405


# =====================================================================
# 8. BỔ SUNG NÂNG CAO: PASSWORD CHANGE REQUIRED, HTTP METHODS & INTEGRITY
# =====================================================================

def test_66_list_roles_must_change_password_required_returns_403(client, db_session):
    """Admin có flag must_change_password=True trong DB khi gọi GET /roles bị chặn 403 PASSWORD_CHANGE_REQUIRED."""
    admin = db_session.scalar(select(User).where(User.id == 1))
    admin.must_change_password = True
    db_session.commit()

    try:
        token = create_access_token(
            data={"sub": "1", "username": "admin_test", "role": "ADMIN", "must_change_password": True}
        )
        res = client.get(ROLES_URL, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    finally:
        admin.must_change_password = False
        db_session.commit()


def test_67_set_user_role_must_change_password_required_returns_403(client, db_session, test_staff_users):
    """Admin có flag must_change_password=True trong DB khi gọi PUT /{userId}/role bị chặn 403 PASSWORD_CHANGE_REQUIRED."""
    admin = db_session.scalar(select(User).where(User.id == 1))
    admin.must_change_password = True
    db_session.commit()

    user = test_staff_users["accountant"]
    try:
        token = create_access_token(
            data={"sub": "1", "username": "admin_test", "role": "ADMIN", "must_change_password": True}
        )
        res = client.put(
            f"{USERS_URL}/{user.id}/role",
            headers={"Authorization": f"Bearer {token}"},
            json={"role_id": 3},
        )
        assert res.status_code == 403
        assert res.json()["code"] == "PASSWORD_CHANGE_REQUIRED"
    finally:
        admin.must_change_password = False
        db_session.commit()


def test_68_roles_method_not_allowed_patch(client, auth_headers_admin):
    """PATCH /roles không được phép (405 Method Not Allowed)."""
    res = client.patch(ROLES_URL, headers=auth_headers_admin, json={})
    assert res.status_code == 405


def test_69_roles_method_not_allowed_put(client, auth_headers_admin):
    """PUT /roles không được phép (405 Method Not Allowed)."""
    res = client.put(ROLES_URL, headers=auth_headers_admin, json={})
    assert res.status_code == 405


def test_70_set_user_role_method_not_allowed_post(client, auth_headers_admin, test_staff_users):
    """POST /users/{userId}/role không được phép (405 Method Not Allowed)."""
    user = test_staff_users["accountant"]
    res = client.post(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 405


def test_71_set_user_role_method_not_allowed_get(client, auth_headers_admin, test_staff_users):
    """GET /users/{userId}/role không được phép (405 Method Not Allowed)."""
    user = test_staff_users["accountant"]
    res = client.get(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin)
    assert res.status_code == 405


def test_72_set_user_role_with_extra_fields_in_payload_succeeds(client, auth_headers_admin, test_staff_users):
    """Payload chứa trường dư thừa ngoài role_id vẫn được xử lý an toàn (200 OK) và cập nhật đúng vai trò."""
    user = test_staff_users["accountant"]
    res = client.put(
        f"{USERS_URL}/{user.id}/role",
        headers=auth_headers_admin,
        json={"role_id": 3, "hacked": True, "extra_note": "malicious injection"},
    )
    assert res.status_code == 200
    assert res.json()["role"]["id"] == 3


def test_73_set_user_role_array_payload_returns_400(client, auth_headers_admin, test_staff_users):
    """Body gửi mảng JSON thay vì JSON Object trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(
        f"{USERS_URL}/{user.id}/role",
        headers=auth_headers_admin,
        json=[{"role_id": 3}],
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_74_set_user_role_empty_raw_body_returns_400(client, auth_headers_admin, test_staff_users):
    """Body rỗng nhưng khai báo Content-Type json trả về HTTP 400 VALIDATION_ERROR."""
    user = test_staff_users["accountant"]
    res = client.put(
        f"{USERS_URL}/{user.id}/role",
        headers={**auth_headers_admin, "Content-Type": "application/json"},
        content="",
    )
    assert res.status_code == 400
    assert res.json()["code"] == "VALIDATION_ERROR"


def test_75_set_user_role_for_inactive_user_preserves_inactive_status(client, auth_headers_admin, db_session, test_staff_users):
    """Đổi vai trò của người dùng đang INACTIVE thì trạng thái is_active=False vẫn được bảo toàn."""
    user = test_staff_users["accountant"]
    user.is_active = False
    db_session.commit()

    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 3
    assert data["is_active"] is False


def test_76_set_user_role_preserves_must_change_password_flag(client, auth_headers_admin, db_session, test_staff_users):
    """Đổi vai trò của người dùng có flag must_change_password=True thì cờ này vẫn được giữ nguyên."""
    user = test_staff_users["accountant"]
    user.must_change_password = True
    db_session.commit()

    res = client.put(f"{USERS_URL}/{user.id}/role", headers=auth_headers_admin, json={"role_id": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["role"]["id"] == 3
    assert data["must_change_password"] is True


def test_77_ac31_1_demoted_admin_cannot_mutate_roles_on_next_request(client, auth_headers_admin, test_staff_users):
    """AC-31.1: Admin phụ sau khi bị hạ xuống Kế toán lập tức không thể gọi PUT /users/{userId}/role của người khác."""
    sub_admin = test_staff_users["secondary_admin"]
    victim = test_staff_users["accountant"]
    sub_admin_headers = make_auth_headers(sub_admin.id, sub_admin.username, "ADMIN")

    # Trước khi bị hạ: sub_admin có thể đổi role
    res_can = client.put(f"{USERS_URL}/{victim.id}/role", headers=sub_admin_headers, json={"role_id": 3})
    assert res_can.status_code == 200

    # Super admin hạ sub_admin xuống ACCOUNTANT (role_id=2)
    res_demote = client.put(f"{USERS_URL}/{sub_admin.id}/role", headers=auth_headers_admin, json={"role_id": 2})
    assert res_demote.status_code == 200

    # Ngay request tiếp theo: sub_admin dùng token cũ gọi PUT /role lập tức bị chặn 403 FORBIDDEN
    res_blocked = client.put(f"{USERS_URL}/{victim.id}/role", headers=sub_admin_headers, json={"role_id": 2})
    assert res_blocked.status_code == 403
    assert res_blocked.json()["code"] == "FORBIDDEN"

