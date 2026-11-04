"""
User Story US-32: Nhật ký thao tác (Audit Log)
Black-box Integration Test Suite for `GET /api/v1/audit-logs`

Strict Isolation Rules:
- Black-box testing purely against docs/API_CONTRACT.md and docs/openapi.yaml.
- Zero inspection or modifications of backend/app/** source files.
- Testing RBAC Guard, Input Validation, Filters, Pagination, Sorting, Schema Integrity, Immutability.
"""

from datetime import datetime, timedelta
import jwt
import pytest
from app.core.security import create_access_token
from app.models.user import AuditLog, User


# ---------------------------------------------------------------------------
# Helper functions for test tokens & headers
# ---------------------------------------------------------------------------

def make_token(sub="1", username="admin_test", role="ADMIN", must_change_password=False, **extra):
    """Generate JWT access token with custom payload claims."""
    payload = {
        "sub": str(sub),
        "username": username,
        "role": role,
        "must_change_password": must_change_password,
        **extra,
    }
    return create_access_token(payload)


def auth_headers(token: str):
    """Wrap JWT into HTTP Bearer Authorization header."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixture: Seed diverse audit logs for filter, pagination, and sorting tests
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_audit_logs(db_session):
    """
    Seed 15 distinct audit log records spanning different dates, users,
    actions, entity types, and nullable combinations.
    """
    logs = [
        # Day 1: 2026-11-01
        AuditLog(
            user_id=1,
            action="LOGIN_SUCCESS",
            entity_type="AUTH",
            entity_id="1",
            old_value=None,
            new_value=None,
            reason="Đăng nhập thành công",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Chrome/118",
            created_at=datetime(2026, 11, 1, 8, 30, 0),
        ),
        AuditLog(
            user_id=1,
            action="UPDATE_ROLE",
            entity_type="USER",
            entity_id="2",
            old_value={"role": "RESIDENT"},
            new_value={"role": "ACCOUNTANT"},
            reason="Phân quyền kế toán viên",
            ip_address="192.168.1.10",
            user_agent="Mozilla/5.0 Firefox/119",
            created_at=datetime(2026, 11, 1, 14, 0, 0),
        ),
        # Day 2: 2026-11-02
        AuditLog(
            user_id=2,
            action="CREATE_APARTMENT",
            entity_type="APARTMENT",
            entity_id="A-101",
            old_value=None,
            new_value={"code": "A-101", "floor": 1, "area": 85.5},
            reason="Khởi tạo căn hộ mới",
            ip_address="192.168.1.20",
            user_agent="Mozilla/5.0 Chrome/118",
            created_at=datetime(2026, 11, 2, 9, 15, 0),
        ),
        AuditLog(
            user_id=2,
            action="UPDATE_APARTMENT",
            entity_type="APARTMENT",
            entity_id="A-101",
            old_value={"status": "VACANT"},
            new_value={"status": "OCCUPIED"},
            reason="Bàn giao căn hộ cho cư dân",
            ip_address="192.168.1.20",
            user_agent="Mozilla/5.0 Chrome/118",
            created_at=datetime(2026, 11, 2, 16, 45, 0),
        ),
        # Day 3: 2026-11-03
        AuditLog(
            user_id=1,
            action="LOCK_USER",
            entity_type="USER",
            entity_id="4",
            old_value={"is_active": True},
            new_value={"is_active": False},
            reason="Khóa tài khoản do vi phạm",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Safari/16",
            created_at=datetime(2026, 11, 3, 10, 0, 0),
        ),
        AuditLog(
            user_id=None,  # Nullable user_id (system action / anonymous)
            action="ACCESS_DENIED",
            entity_type="AUTH",
            entity_id=None,
            old_value=None,
            new_value=None,
            reason="Truy cập trái phép",
            ip_address="10.0.0.99",
            user_agent=None,
            created_at=datetime(2026, 11, 3, 11, 30, 0),
        ),
        AuditLog(
            user_id=1,
            action="UNLOCK_USER",
            entity_type="USER",
            entity_id="4",
            old_value={"is_active": False},
            new_value={"is_active": True},
            reason="Mở khóa tài khoản sau xác minh",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Safari/16",
            created_at=datetime(2026, 11, 3, 15, 0, 0),
        ),
        # Day 4: 2026-11-04
        AuditLog(
            user_id=2,
            action="CREATE_FEE",
            entity_type="FEE",
            entity_id="F-01",
            old_value=None,
            new_value={"name": "Phí quản lý", "amount": 10000},
            reason="Thêm danh mục phí mới",
            ip_address="192.168.1.20",
            user_agent="Mozilla/5.0 Chrome/118",
            created_at=datetime(2026, 11, 4, 8, 45, 0),
        ),
        AuditLog(
            user_id=2,
            action="UPDATE_FEE",
            entity_type="FEE",
            entity_id="F-01",
            old_value={"amount": 10000},
            new_value={"amount": 12000},
            reason="Điều chỉnh đơn giá dịch vụ",
            ip_address="192.168.1.20",
            user_agent="Mozilla/5.0 Chrome/118",
            created_at=datetime(2026, 11, 4, 13, 20, 0),
        ),
        AuditLog(
            user_id=1,
            action="RESET_PASSWORD",
            entity_type="USER",
            entity_id="3",
            old_value=None,
            new_value={"must_change_password": True},
            reason="Cấp lại mật khẩu tạm thời",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Safari/16",
            created_at=datetime(2026, 11, 4, 17, 10, 0),
        ),
        # Day 5: 2026-11-05
        AuditLog(
            user_id=None,
            action="SYSTEM_BACKUP",
            entity_type="SYSTEM",
            entity_id="backup-101",
            old_value=None,
            new_value={"file": "bluemoon_backup_20261105.tar.gz"},
            reason="Sao lưu hệ thống định kỳ",
            ip_address=None,
            user_agent=None,
            created_at=datetime(2026, 11, 5, 2, 0, 0),
        ),
        AuditLog(
            user_id=1,
            action="LOGIN_SUCCESS",
            entity_type="AUTH",
            entity_id="1",
            old_value=None,
            new_value=None,
            reason="Đăng nhập phiên làm việc mới",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Chrome/118",
            created_at=datetime(2026, 11, 5, 8, 0, 0),
        ),
        AuditLog(
            user_id=2,
            action="CREATE_INVOICE",
            entity_type="INVOICE",
            entity_id="INV-2026-001",
            old_value=None,
            new_value={"household_id": 101, "total_amount": 500000},
            reason="Lập hóa đơn kỳ 11/2026",
            ip_address="192.168.1.20",
            user_agent="Mozilla/5.0 Chrome/118",
            created_at=datetime(2026, 11, 5, 11, 30, 0),
        ),
        # Day 6: 2026-11-06
        AuditLog(
            user_id=1,
            action="EXPORT_REPORT",
            entity_type="REPORT",
            entity_id="REP-DEBT-01",
            old_value=None,
            new_value={"format": "xlsx", "period": "2026-10"},
            reason="Xuất báo cáo công nợ",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Safari/16",
            created_at=datetime(2026, 11, 6, 9, 0, 0),
        ),
        # Record with all nulls possible
        AuditLog(
            user_id=None,
            action="ANONYMOUS_PROBE",
            entity_type="SYSTEM",
            entity_id=None,
            old_value=None,
            new_value=None,
            reason=None,
            ip_address=None,
            user_agent=None,
            created_at=datetime(2026, 11, 6, 23, 59, 59),
        ),
    ]
    db_session.add_all(logs)
    db_session.commit()
    return logs


# ===========================================================================
# Group 1: Authentication & RBAC Guard
# ===========================================================================

class TestAuditLogAuthenticationAndRBAC:
    """Validate 401 UNAUTHENTICATED, 403 FORBIDDEN, 403 PASSWORD_CHANGE_REQUIRED, and 200 OK."""

    def test_01_audit_logs_no_token_returns_401(self, client):
        """Request without Authorization header must return 401 UNAUTHENTICATED."""
        res = client.get("/api/v1/audit-logs")
        assert res.status_code == 401
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]

    def test_02_audit_logs_empty_token_returns_401(self, client):
        """Authorization header with empty Bearer token must return 401."""
        res = client.get("/api/v1/audit-logs", headers={"Authorization": "Bearer "})
        assert res.status_code == 401
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]

    def test_03_audit_logs_malformed_token_returns_401(self, client):
        """Malformed JWT string must return 401 UNAUTHENTICATED."""
        res = client.get("/api/v1/audit-logs", headers={"Authorization": "Bearer not.a.valid.jwt"})
        assert res.status_code == 401
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]

    def test_04_audit_logs_invalid_bearer_scheme_returns_401(self, client):
        """Non-Bearer scheme (e.g. Basic auth) must return 401."""
        res = client.get("/api/v1/audit-logs", headers={"Authorization": "Basic dXNlcjpwYXNz"})
        assert res.status_code == 401
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]

    def test_05_audit_logs_expired_token_returns_401(self, client):
        """Expired JWT token must return 401 UNAUTHENTICATED."""
        token = create_access_token(
            {"sub": "1", "username": "admin_test", "role": "ADMIN", "must_change_password": False},
            expires_delta=timedelta(seconds=-60),
        )
        res = client.get("/api/v1/audit-logs", headers=auth_headers(token))
        assert res.status_code == 401
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]

    def test_06_audit_logs_invalid_signature_token_returns_401(self, client):
        """JWT signed with an untrusted secret key must return 401 UNAUTHENTICATED."""
        bogus_token = jwt.encode(
            {"sub": "1", "username": "admin_test", "role": "ADMIN", "exp": 9999999999},
            "completely_untrusted_secret_key_67890",
            algorithm="HS256",
        )
        res = client.get("/api/v1/audit-logs", headers=auth_headers(bogus_token))
        assert res.status_code == 401
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]

    def test_07_audit_logs_resident_101_returns_403(self, client, auth_headers_resident_101):
        """Role RESIDENT is forbidden from viewing audit logs (403 FORBIDDEN)."""
        res = client.get("/api/v1/audit-logs", headers=auth_headers_resident_101)
        assert res.status_code == 403
        data = res.json()
        assert data.get("code") == "FORBIDDEN"

    def test_08_audit_logs_resident_102_returns_403(self, client, auth_headers_resident_102):
        """Role RESIDENT (household 102) is forbidden from viewing audit logs (403 FORBIDDEN)."""
        res = client.get("/api/v1/audit-logs", headers=auth_headers_resident_102)
        assert res.status_code == 403
        data = res.json()
        assert data.get("code") == "FORBIDDEN"

    def test_09_audit_logs_accountant_returns_403(self, client):
        """Role ACCOUNTANT is forbidden from viewing audit logs (403 FORBIDDEN)."""
        token = make_token(sub="2", username="accountant_test", role="ACCOUNTANT")
        res = client.get("/api/v1/audit-logs", headers=auth_headers(token))
        assert res.status_code == 403
        data = res.json()
        assert data.get("code") == "FORBIDDEN"

    def test_10_audit_logs_treasurer_returns_403(self, client, db_session):
        """Role TREASURER (role_id=3) is forbidden from viewing audit logs (403 FORBIDDEN)."""
        treasurer = User(
            id=5,
            username="treasurer_test",
            password_hash="dummy_hash_treasurer",
            full_name="Thủ Quỹ Test",
            email="treasurer@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(treasurer)
        db_session.commit()

        token = make_token(sub="5", username="treasurer_test", role="TREASURER")
        res = client.get("/api/v1/audit-logs", headers=auth_headers(token))
        assert res.status_code == 403
        data = res.json()
        assert data.get("code") == "FORBIDDEN"

    def test_11_audit_logs_token_user_not_found_returns_401(self, client):
        """Token referencing a non-existent user_id in DB must return 401 UNAUTHENTICATED."""
        token = make_token(sub="9999", username="ghost_user", role="ADMIN")
        res = client.get("/api/v1/audit-logs", headers=auth_headers(token))
        assert res.status_code == 401
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]

    def test_12_audit_logs_inactive_user_returns_401_or_403(self, client, db_session):
        """Inactive user account (is_active=False) must be denied access."""
        inactive_admin = User(
            id=7,
            username="admin_inactive",
            password_hash="dummy_hash_inactive",
            full_name="Admin Inactive Test",
            email="inactive_admin@bluemoon.local",
            role_id=1,
            is_active=False,
            must_change_password=False,
        )
        db_session.add(inactive_admin)
        db_session.commit()

        token = make_token(sub="7", username="admin_inactive", role="ADMIN")
        res = client.get("/api/v1/audit-logs", headers=auth_headers(token))
        assert res.status_code in [401, 403]
        data = res.json()
        assert data.get("code") in ["UNAUTHENTICATED", "INVALID_CREDENTIALS", "FORBIDDEN"]

    def test_13_audit_logs_admin_must_change_password_returns_403_password_change_required(self, client, db_session):
        """Admin with must_change_password=True must receive 403 PASSWORD_CHANGE_REQUIRED."""
        admin_must_change = User(
            id=6,
            username="admin_must_change",
            password_hash="dummy_hash_must_change",
            full_name="Admin Cần Đổi Mật Khẩu",
            email="admin_mc@bluemoon.local",
            role_id=1,
            is_active=True,
            must_change_password=True,
        )
        db_session.add(admin_must_change)
        db_session.commit()

        token = make_token(sub="6", username="admin_must_change", role="ADMIN", must_change_password=True)
        res = client.get("/api/v1/audit-logs", headers=auth_headers(token))
        assert res.status_code == 403
        data = res.json()
        assert data.get("code") == "PASSWORD_CHANGE_REQUIRED"

    def test_14_audit_logs_valid_admin_returns_200(self, client, auth_headers_admin):
        """Valid admin user with must_change_password=False must receive 200 OK."""
        res = client.get("/api/v1/audit-logs", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "page" in data
        assert "page_size" in data
        assert "total" in data


# ===========================================================================
# Group 2: Validation & Boundary Conditions
# ===========================================================================

class TestAuditLogValidationAndBoundaries:
    """Validate 400 VALIDATION_ERROR on boundary violations and invalid data types."""

    def test_15_page_zero_returns_400(self, client, auth_headers_admin):
        """page=0 violates minimum: 1 constraint -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page=0", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_16_page_negative_returns_400(self, client, auth_headers_admin):
        """page=-1 violates minimum: 1 constraint -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page=-1", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_17_page_non_numeric_returns_400(self, client, auth_headers_admin):
        """page='abc' is not an integer -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page=abc", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_18_page_float_returns_400(self, client, auth_headers_admin):
        """page='1.5' is not an integer -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page=1.5", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_19_page_size_zero_returns_400(self, client, auth_headers_admin):
        """page_size=0 violates minimum: 1 constraint -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page_size=0", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_20_page_size_negative_returns_400(self, client, auth_headers_admin):
        """page_size=-5 violates minimum: 1 constraint -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page_size=-5", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_21_page_size_exceeds_100_returns_400(self, client, auth_headers_admin):
        """page_size=101 violates maximum: 100 constraint -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page_size=101", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_22_page_size_huge_returns_400(self, client, auth_headers_admin):
        """page_size=10000 violates maximum: 100 constraint -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page_size=10000", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_23_page_size_non_numeric_returns_400(self, client, auth_headers_admin):
        """page_size='fifty' is not an integer -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page_size=fifty", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_24_page_size_float_returns_400(self, client, auth_headers_admin):
        """page_size='20.5' is not an integer -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?page_size=20.5", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_25_from_date_slash_format_returns_400(self, client, auth_headers_admin):
        """from='2026/11/04' is not ISO YYYY-MM-DD -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?from=2026/11/04", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_26_from_date_day_month_year_returns_400(self, client, auth_headers_admin):
        """from='04-11-2026' is reversed -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?from=04-11-2026", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_27_from_date_random_string_returns_400(self, client, auth_headers_admin):
        """from='invalid-date' is not a date -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?from=invalid-date", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_28_from_date_nonexistent_day_feb31_returns_400(self, client, auth_headers_admin):
        """from='2026-02-31' does not exist -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?from=2026-02-31", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_29_from_date_nonexistent_month_13_returns_400(self, client, auth_headers_admin):
        """from='2026-13-01' has invalid month -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?from=2026-13-01", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_30_to_date_random_string_returns_400(self, client, auth_headers_admin):
        """to='abc' is not a date -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?to=abc", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_31_to_date_nonexistent_day_apr31_returns_400(self, client, auth_headers_admin):
        """to='2026-04-31' does not exist (April has 30 days) -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?to=2026-04-31", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_32_to_date_nonexistent_feb29_nonleap_returns_400(self, client, auth_headers_admin):
        """to='2025-02-29' does not exist (2025 is not a leap year) -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?to=2025-02-29", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_33_from_date_greater_than_to_date_returns_400(self, client, auth_headers_admin):
        """from > to (2026-11-10 > 2026-11-01) violates temporal logic -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?from=2026-11-10&to=2026-11-01", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_34_user_id_non_numeric_string_returns_400(self, client, auth_headers_admin):
        """user_id='abc' is not an integer -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?user_id=abc", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"

    def test_35_user_id_float_returns_400(self, client, auth_headers_admin):
        """user_id='1.5' is not an integer -> 400 VALIDATION_ERROR."""
        res = client.get("/api/v1/audit-logs?user_id=1.5", headers=auth_headers_admin)
        assert res.status_code == 400
        data = res.json()
        assert data.get("code") == "VALIDATION_ERROR"


# ===========================================================================
# Group 3: Valid Requests & Filter Matrix
# ===========================================================================

class TestAuditLogFilters:
    """Validate filtering by user_id, action, entity_type, from, to, and combinations."""

    def test_36_filter_user_id_existing_returns_only_matching_logs(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by existing user_id=1 returns only logs where user_id=1."""
        res = client.get("/api/v1/audit-logs?user_id=1", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["user_id"] == 1

    def test_37_filter_user_id_different_user_returns_only_matching_logs(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by user_id=2 returns only logs where user_id=2."""
        res = client.get("/api/v1/audit-logs?user_id=2", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["user_id"] == 2

    def test_38_filter_user_id_nonexistent_returns_empty_items_total_zero(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by non-existent user_id=99999 returns empty items array and total=0."""
        res = client.get("/api/v1/audit-logs?user_id=99999", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_39_filter_user_id_negative_returns_empty_items_total_zero(self, client, auth_headers_admin, seeded_audit_logs):
        """Negative user_id (not existing) returns empty items array and total=0."""
        res = client.get("/api/v1/audit-logs?user_id=-10", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_40_filter_action_exact_match(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by action='LOGIN_SUCCESS' returns only matching logs."""
        res = client.get("/api/v1/audit-logs?action=LOGIN_SUCCESS", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2
        for item in data["items"]:
            assert item["action"] == "LOGIN_SUCCESS"

    def test_41_filter_action_different_action(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by action='UPDATE_ROLE' returns only matching logs."""
        res = client.get("/api/v1/audit-logs?action=UPDATE_ROLE", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "UPDATE_ROLE"

    def test_42_filter_action_nonexistent_returns_empty_items_total_zero(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by unknown action returns empty items array and total=0."""
        res = client.get("/api/v1/audit-logs?action=UNKNOWN_NONEXISTENT_ACTION", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_43_filter_entity_type_user(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by entity_type='USER' returns only records affecting USER."""
        res = client.get("/api/v1/audit-logs?entity_type=USER", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["entity_type"] == "USER"

    def test_44_filter_entity_type_apartment(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by entity_type='APARTMENT' returns only records affecting APARTMENT."""
        res = client.get("/api/v1/audit-logs?entity_type=APARTMENT", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["entity_type"] == "APARTMENT"

    def test_45_filter_entity_type_fee(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by entity_type='FEE' returns only records affecting FEE."""
        res = client.get("/api/v1/audit-logs?entity_type=FEE", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["entity_type"] == "FEE"

    def test_46_filter_entity_type_nonexistent_returns_empty_items_total_zero(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter by unknown entity_type returns empty items array and total=0."""
        res = client.get("/api/v1/audit-logs?entity_type=NONEXISTENT_ENTITY", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_47_filter_from_date_inclusive(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter from='2026-11-04' includes logs from 2026-11-04 00:00:00 onwards."""
        res = client.get("/api/v1/audit-logs?from=2026-11-04", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for item in data["items"]:
            created_date = item["created_at"][:10]
            assert created_date >= "2026-11-04"

    def test_48_filter_to_date_inclusive(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter to='2026-11-02' includes logs up to 2026-11-02 23:59:59."""
        res = client.get("/api/v1/audit-logs?to=2026-11-02", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for item in data["items"]:
            created_date = item["created_at"][:10]
            assert created_date <= "2026-11-02"

    def test_49_filter_date_range_from_to(self, client, auth_headers_admin, seeded_audit_logs):
        """Filter from='2026-11-02' and to='2026-11-04' returns only logs within that range."""
        res = client.get("/api/v1/audit-logs?from=2026-11-02&to=2026-11-04", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] > 0
        for item in data["items"]:
            created_date = item["created_at"][:10]
            assert "2026-11-02" <= created_date <= "2026-11-04"

    def test_50_filter_single_day_from_equals_to(self, client, auth_headers_admin, seeded_audit_logs):
        """When from == to (e.g. 2026-11-03), returns all logs on that entire single day."""
        res = client.get("/api/v1/audit-logs?from=2026-11-03&to=2026-11-03", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3  # 3 logs seeded on 2026-11-03
        for item in data["items"]:
            assert item["created_at"][:10] == "2026-11-03"

    def test_51_filter_date_range_no_matching_logs_in_future(self, client, auth_headers_admin, seeded_audit_logs):
        """Date range in the far future returns empty items array and total=0."""
        res = client.get("/api/v1/audit-logs?from=2099-01-01&to=2099-12-31", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_52_filter_date_range_no_matching_logs_in_past(self, client, auth_headers_admin, seeded_audit_logs):
        """Date range in the past before any logs returns empty items array and total=0."""
        res = client.get("/api/v1/audit-logs?from=2020-01-01&to=2020-12-31", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_53_filter_combined_user_id_and_action(self, client, auth_headers_admin, seeded_audit_logs):
        """Combined user_id=1 and action='LOGIN_SUCCESS' matches both conditions."""
        res = client.get("/api/v1/audit-logs?user_id=1&action=LOGIN_SUCCESS", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 2
        for item in data["items"]:
            assert item["user_id"] == 1
            assert item["action"] == "LOGIN_SUCCESS"

    def test_54_filter_combined_action_and_entity_type(self, client, auth_headers_admin, seeded_audit_logs):
        """Combined action='CREATE_APARTMENT' and entity_type='APARTMENT'."""
        res = client.get("/api/v1/audit-logs?action=CREATE_APARTMENT&entity_type=APARTMENT", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "CREATE_APARTMENT"
        assert data["items"][0]["entity_type"] == "APARTMENT"

    def test_55_filter_combined_entity_type_and_date_range(self, client, auth_headers_admin, seeded_audit_logs):
        """Combined entity_type='USER' and date range 2026-11-03 to 2026-11-04."""
        res = client.get(
            "/api/v1/audit-logs?entity_type=USER&from=2026-11-03&to=2026-11-04",
            headers=auth_headers_admin,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3  # LOCK_USER, UNLOCK_USER on 11-03, RESET_PASSWORD on 11-04
        for item in data["items"]:
            assert item["entity_type"] == "USER"
            assert "2026-11-03" <= item["created_at"][:10] <= "2026-11-04"

    def test_56_filter_combined_all_five_filters(self, client, auth_headers_admin, seeded_audit_logs):
        """Simultaneous combination of user_id, action, entity_type, from, and to."""
        res = client.get(
            "/api/v1/audit-logs?user_id=1&action=UPDATE_ROLE&entity_type=USER&from=2026-11-01&to=2026-11-02",
            headers=auth_headers_admin,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["user_id"] == 1
        assert item["action"] == "UPDATE_ROLE"
        assert item["entity_type"] == "USER"
        assert item["created_at"][:10] == "2026-11-01"

    def test_57_filter_mutually_exclusive_filters_returns_empty(self, client, auth_headers_admin, seeded_audit_logs):
        """Mutually exclusive filters (user_id=1 with action performed only by user_id=2) returns total=0."""
        res = client.get("/api/v1/audit-logs?user_id=1&action=CREATE_INVOICE", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0


# ===========================================================================
# Group 4: Pagination & Ordering
# ===========================================================================

class TestAuditLogPaginationAndOrdering:
    """Validate page, page_size boundaries, default pagination, and created_at DESC / id DESC order."""

    def test_58_default_pagination_params_page_1_size_20(self, client, auth_headers_admin, seeded_audit_logs):
        """Default query without page & page_size returns page=1, page_size=20."""
        res = client.get("/api/v1/audit-logs", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] == len(seeded_audit_logs)
        assert len(data["items"]) == len(seeded_audit_logs)

    def test_59_pagination_first_page_custom_size(self, client, auth_headers_admin, seeded_audit_logs):
        """page=1, page_size=4 returns exactly 4 items with total=15."""
        res = client.get("/api/v1/audit-logs?page=1&page_size=4", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 1
        assert data["page_size"] == 4
        assert data["total"] == 15
        assert len(data["items"]) == 4

    def test_60_pagination_second_page_no_overlap_with_first_page(self, client, auth_headers_admin, seeded_audit_logs):
        """Page 2 with page_size=4 must return the next 4 items without overlap with page 1."""
        res1 = client.get("/api/v1/audit-logs?page=1&page_size=4", headers=auth_headers_admin)
        res2 = client.get("/api/v1/audit-logs?page=2&page_size=4", headers=auth_headers_admin)
        assert res1.status_code == 200
        assert res2.status_code == 200
        data1 = res1.json()
        data2 = res2.json()

        page1_ids = {item["id"] for item in data1["items"]}
        page2_ids = {item["id"] for item in data2["items"]}
        assert len(page1_ids) == 4
        assert len(page2_ids) == 4
        assert page1_ids.isdisjoint(page2_ids), "Page 1 and Page 2 must not have overlapping record IDs"

    def test_61_pagination_min_boundary_page_size_1(self, client, auth_headers_admin, seeded_audit_logs):
        """page_size=1 is the valid lower boundary."""
        res = client.get("/api/v1/audit-logs?page=1&page_size=1", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["page_size"] == 1
        assert len(data["items"]) == 1

    def test_62_pagination_max_boundary_page_size_100(self, client, auth_headers_admin, seeded_audit_logs):
        """page_size=100 is the valid upper boundary."""
        res = client.get("/api/v1/audit-logs?page=1&page_size=100", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["page_size"] == 100
        assert len(data["items"]) == len(seeded_audit_logs)

    def test_63_sorting_created_at_desc_and_id_desc(self, client, auth_headers_admin, seeded_audit_logs):
        """
        Verify sort order is strictly descending by created_at DESC (and id DESC as tie-breaker).
        """
        res = client.get("/api/v1/audit-logs?page=1&page_size=100", headers=auth_headers_admin)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) >= 2

        for i in range(len(items) - 1):
            curr_dt = items[i]["created_at"]
            next_dt = items[i + 1]["created_at"]
            curr_id = items[i]["id"]
            next_id = items[i + 1]["id"]

            # Sort criterion: created_at DESC, then id DESC
            assert curr_dt >= next_dt, f"Item {i} ({curr_dt}) must be >= item {i+1} ({next_dt})"
            if curr_dt == next_dt:
                assert curr_id >= next_id, f"When timestamps equal, id {curr_id} must be >= {next_id}"

    def test_64_empty_database_returns_empty_page(self, client, auth_headers_admin):
        """When no audit logs exist in database, returns items=[], total=0, page=1, page_size=20."""
        res = client.get("/api/v1/audit-logs", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_65_page_beyond_total_pages_returns_empty_items(self, client, auth_headers_admin, seeded_audit_logs):
        """Requesting page=999 when total=15 returns items=[], total=15, page=999."""
        res = client.get("/api/v1/audit-logs?page=999&page_size=10", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 15
        assert data["page"] == 999
        assert data["page_size"] == 10

    def test_66_total_count_remains_unaffected_by_page_or_page_size(self, client, auth_headers_admin, seeded_audit_logs):
        """Total count reflects all matching records regardless of page number or page_size."""
        res_p1 = client.get("/api/v1/audit-logs?page=1&page_size=2", headers=auth_headers_admin)
        res_p2 = client.get("/api/v1/audit-logs?page=3&page_size=2", headers=auth_headers_admin)
        assert res_p1.json()["total"] == res_p2.json()["total"] == 15


# ===========================================================================
# Group 5: Schema Structure & Field Integrity
# ===========================================================================

class TestAuditLogSchemaAndIntegrity:
    """Validate OpenAPI 3.0.3 schema conformance, field types, nullability, and JSON preservation."""

    def test_67_response_envelope_keys_and_types(self, client, auth_headers_admin, seeded_audit_logs):
        """Response envelope must strictly match AuditLogPage schema (items, page, page_size, total)."""
        res = client.get("/api/v1/audit-logs", headers=auth_headers_admin)
        assert res.status_code == 200
        data = res.json()
        assert set(data.keys()) == {"items", "page", "page_size", "total"}
        assert isinstance(data["items"], list)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        assert isinstance(data["total"], int)

    def test_68_item_all_eleven_schema_fields_present(self, client, auth_headers_admin, seeded_audit_logs):
        """Every audit log item must contain all 11 fields defined in OpenAPI AuditLog schema."""
        expected_fields = {
            "id",
            "user_id",
            "action",
            "entity_type",
            "entity_id",
            "old_value",
            "new_value",
            "reason",
            "ip_address",
            "user_agent",
            "created_at",
        }
        res = client.get("/api/v1/audit-logs?page=1&page_size=10", headers=auth_headers_admin)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) > 0
        for item in items:
            assert set(item.keys()) == expected_fields
            assert isinstance(item["id"], int)
            assert isinstance(item["action"], str)
            assert isinstance(item["entity_type"], str)

    def test_69_item_created_at_is_iso8601_format(self, client, auth_headers_admin, seeded_audit_logs):
        """created_at must be formatted as ISO-8601 datetime string."""
        res = client.get("/api/v1/audit-logs?page=1&page_size=5", headers=auth_headers_admin)
        assert res.status_code == 200
        for item in res.json()["items"]:
            iso_str = item["created_at"]
            assert "T" in iso_str or " " in iso_str
            # Parse datetime using fromisoformat without error
            parsed = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            assert isinstance(parsed, datetime)

    def test_70_item_nullable_fields_return_null(self, client, auth_headers_admin, seeded_audit_logs):
        """A record seeded with nulls must return null (None in Python) for all nullable fields."""
        res = client.get("/api/v1/audit-logs?action=ANONYMOUS_PROBE", headers=auth_headers_admin)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        item = items[0]
        assert item["user_id"] is None
        assert item["entity_id"] is None
        assert item["old_value"] is None
        assert item["new_value"] is None
        assert item["reason"] is None
        assert item["ip_address"] is None
        assert item["user_agent"] is None

    def test_71_item_json_object_fields_old_and_new_value(self, client, auth_headers_admin, seeded_audit_logs):
        """old_value and new_value with JSON dictionary must be parsed and returned as objects."""
        res = client.get("/api/v1/audit-logs?action=UPDATE_ROLE", headers=auth_headers_admin)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        item = items[0]
        assert isinstance(item["old_value"], dict)
        assert item["old_value"] == {"role": "RESIDENT"}
        assert isinstance(item["new_value"], dict)
        assert item["new_value"] == {"role": "ACCOUNTANT"}

    def test_72_item_entity_id_is_string(self, client, auth_headers_admin, seeded_audit_logs):
        """entity_id must be a string representation when present."""
        res = client.get("/api/v1/audit-logs?action=CREATE_APARTMENT", headers=auth_headers_admin)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["entity_id"] == "A-101"
        assert isinstance(items[0]["entity_id"], str)

    def test_73_access_denied_audit_log_created_automatically_on_403(self, client, auth_headers_resident_101, auth_headers_admin):
        """
        API Contract Section 1.2: When a request receives 403 FORBIDDEN,
        the backend automatically logs an ACCESS_DENIED audit entry.
        """
        # Call forbidden endpoint as resident
        res_forbidden = client.get("/api/v1/audit-logs", headers=auth_headers_resident_101)
        assert res_forbidden.status_code == 403

        # Admin checks if an ACCESS_DENIED audit log was recorded
        res_admin = client.get("/api/v1/audit-logs?action=ACCESS_DENIED", headers=auth_headers_admin)
        assert res_admin.status_code == 200
        data = res_admin.json()
        assert data["total"] >= 1
        assert any(item["action"] == "ACCESS_DENIED" for item in data["items"])


# ===========================================================================
# Group 6: Immutability & Method Not Allowed
# ===========================================================================

class TestAuditLogImmutability:
    """Validate that audit logs are strictly read-only (405 Method Not Allowed on mutation methods)."""

    def test_74_post_audit_logs_returns_405(self, client, auth_headers_admin):
        """POST /api/v1/audit-logs must return 405 Method Not Allowed."""
        res = client.post("/api/v1/audit-logs", json={"action": "HACK"}, headers=auth_headers_admin)
        assert res.status_code == 405

    def test_75_put_audit_logs_returns_405(self, client, auth_headers_admin):
        """PUT /api/v1/audit-logs must return 405 Method Not Allowed."""
        res = client.put("/api/v1/audit-logs", json={"action": "HACK"}, headers=auth_headers_admin)
        assert res.status_code == 405

    def test_76_patch_audit_logs_returns_405(self, client, auth_headers_admin):
        """PATCH /api/v1/audit-logs must return 405 Method Not Allowed."""
        res = client.patch("/api/v1/audit-logs", json={"action": "HACK"}, headers=auth_headers_admin)
        assert res.status_code == 405

    def test_77_delete_audit_logs_returns_405(self, client, auth_headers_admin):
        """DELETE /api/v1/audit-logs must return 405 Method Not Allowed."""
        res = client.delete("/api/v1/audit-logs", headers=auth_headers_admin)
        assert res.status_code == 405

    def test_78_post_audit_log_item_returns_405_or_404(self, client, auth_headers_admin):
        """POST /api/v1/audit-logs/1 must return 405 Method Not Allowed or 404 Not Found."""
        res = client.post("/api/v1/audit-logs/1", json={"action": "HACK"}, headers=auth_headers_admin)
        assert res.status_code in [404, 405]

    def test_79_put_audit_log_item_returns_405_or_404(self, client, auth_headers_admin):
        """PUT /api/v1/audit-logs/1 must return 405 Method Not Allowed or 404 Not Found."""
        res = client.put("/api/v1/audit-logs/1", json={"action": "HACK"}, headers=auth_headers_admin)
        assert res.status_code in [404, 405]

    def test_80_patch_audit_log_item_returns_405_or_404(self, client, auth_headers_admin):
        """PATCH /api/v1/audit-logs/1 must return 405 Method Not Allowed or 404 Not Found."""
        res = client.patch("/api/v1/audit-logs/1", json={"action": "HACK"}, headers=auth_headers_admin)
        assert res.status_code in [404, 405]

    def test_81_delete_audit_log_item_returns_405_or_404(self, client, auth_headers_admin):
        """DELETE /api/v1/audit-logs/1 must return 405 Method Not Allowed or 404 Not Found."""
        res = client.delete("/api/v1/audit-logs/1", headers=auth_headers_admin)
        assert res.status_code in [404, 405]

    def test_82_get_audit_log_detail_endpoint_returns_404_or_405(self, client, auth_headers_admin):
        """GET /api/v1/audit-logs/1 is not in API Contract (only collection is exposed) -> 404 or 405."""
        res = client.get("/api/v1/audit-logs/1", headers=auth_headers_admin)
        assert res.status_code in [404, 405]
