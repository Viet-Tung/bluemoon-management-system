"""
Test suite for US-45: Sao lưu & Phục hồi CSDL (Database Backup & Restore - History and Manual Trigger).
Endpoints:
- POST /api/v1/system/backups: Chạy sao lưu thủ công (202 Accepted)
- GET /api/v1/system/backups: Lịch sử sao lưu (200 OK, BackupJobPage)

Specifications & Invariants (SSOT):
- docs/openapi.yaml
- docs/API_CONTRACT.md
- docs/backend_spec/sprint_1/SPRINT_1_BACKEND_SPEC.md (US-45, AC-45.1)
- Minimal cluster: backup_jobs, audit_logs, users, roles
- RBAC: ADMIN only. ACCOUNTANT, TREASURER, RESIDENT get 403 FORBIDDEN.
- Unauthenticated / Invalid token gets 401 UNAUTHENTICATED.
- must_change_password=True gets 403 PASSWORD_CHANGE_REQUIRED.
- Pagination: page >= 1 (default 1), page_size between 1 and 100 (default 20).
"""

from datetime import datetime, timezone
import pytest
from app.core.security import create_access_token
from app.models.user import AuditLog, BackupJob, User


# ============================================================================
# HELPER FUNCTIONS & AUTH FIXTURES
# ============================================================================

def make_auth_headers(
    sub: str = "1",
    username: str = "admin_test",
    role: str = "ADMIN",
    must_change_password: bool = False,
    extra_claims: dict = None
) -> dict:
    """Generate authorization header with valid JWT token."""
    payload = {
        "sub": str(sub),
        "username": username,
        "role": role,
        "must_change_password": must_change_password,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = create_access_token(payload)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers():
    return make_auth_headers(sub="1", username="admin_test", role="ADMIN")


@pytest.fixture
def accountant_headers():
    return make_auth_headers(sub="2", username="accountant_test", role="ACCOUNTANT")


@pytest.fixture
def treasurer_headers(db_session):
    """Seed treasurer user in db and generate auth headers."""
    treasurer = db_session.query(User).filter(User.id == 5).first()
    if not treasurer:
        treasurer = User(
            id=5,
            username="treasurer_test",
            password_hash="hashed_pw_treasurer",
            full_name="Thủ Quỹ Test",
            email="treasurer@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False
        )
        db_session.add(treasurer)
        db_session.commit()
    return make_auth_headers(sub="5", username="treasurer_test", role="TREASURER")


@pytest.fixture
def resident_headers():
    return make_auth_headers(sub="3", username="resident_101", role="RESIDENT")


@pytest.fixture
def admin_must_change_pwd_headers(db_session):
    """Set must_change_password=True for admin in DB, yield headers, then restore."""
    admin = db_session.query(User).filter(User.id == 1).first()
    original = admin.must_change_password if admin else False
    if admin:
        admin.must_change_password = True
        db_session.commit()
    try:
        yield make_auth_headers(
            sub="1",
            username="admin_test",
            role="ADMIN",
            must_change_password=True
        )
    finally:
        if admin:
            admin.must_change_password = original
            db_session.commit()


# ============================================================================
# 1. POST /api/v1/system/backups: HAPPY PATH & FUNCTIONAL SPECIFICATION
# ============================================================================

def test_post_backup_returns_status_202(client, admin_headers):
    """AC-45.1: Admin kích hoạt sao lưu thủ công thành công trả về HTTP 202 Accepted."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}: {response.text}"


def test_post_backup_returns_json_content_type(client, admin_headers):
    """Response trả về phải có Content-Type là application/json."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    assert "application/json" in response.headers.get("content-type", "")


def test_post_backup_schema_contains_required_fields(client, admin_headers):
    """Response schema BackupJob phải chứa các trường bắt buộc theo SSOT openapi.yaml."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    data = response.json()
    assert "id" in data, "BackupJob must contain 'id'"
    assert "status" in data, "BackupJob must contain 'status'"
    assert "requested_at" in data, "BackupJob must contain 'requested_at'"
    assert "requested_by" in data, "BackupJob must contain 'requested_by'"
    assert "finished_at" in data, "BackupJob must contain 'finished_at'"
    assert "size_bytes" in data, "BackupJob must contain 'size_bytes'"


def test_post_backup_id_is_positive_integer(client, admin_headers):
    """ID của BackupJob phải là số nguyên dương."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    data = response.json()
    assert isinstance(data["id"], int)
    assert data["id"] > 0


def test_post_backup_status_is_valid_enum(client, admin_headers):
    """Trường status phải thuộc enum: ['QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED']."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    data = response.json()
    valid_statuses = {"QUEUED", "RUNNING", "SUCCEEDED", "FAILED"}
    assert data["status"] in valid_statuses, f"Invalid status: {data['status']}"


def test_post_backup_requested_by_matches_admin_id(client, admin_headers):
    """requested_by phải trích xuất chính xác từ sub của JWT token (Admin ID = 1)."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    data = response.json()
    assert data["requested_by"] == 1


def test_post_backup_requested_at_is_valid_iso_datetime(client, admin_headers):
    """requested_at phải là chuỗi định dạng ISO 8601 date-time hợp lệ."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    data = response.json()
    dt_str = data["requested_at"]
    assert dt_str is not None
    # Parse ISO format - must not raise error
    parsed_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    assert parsed_dt is not None


def test_post_backup_nullable_fields_allowed_to_be_null(client, admin_headers):
    """finished_at và size_bytes có thể là null khi job mới được tạo (QUEUED/RUNNING)."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    data = response.json()
    if data["status"] in ["QUEUED", "RUNNING"]:
        assert data["finished_at"] is None or isinstance(data["finished_at"], str)
        assert data["size_bytes"] is None or isinstance(data["size_bytes"], int)


def test_post_backup_persists_to_database(client, admin_headers, db_session):
    """Sau khi POST thành công, một bản ghi mới phải tồn tại trong bảng backup_jobs."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    job_id = response.json()["id"]

    db_job = db_session.query(BackupJob).filter(BackupJob.id == job_id).first()
    assert db_job is not None, f"BackupJob with id {job_id} not found in DB"
    assert db_job.requested_by == 1


def test_post_backup_multiple_consecutive_triggers(client, admin_headers, db_session):
    """Kích hoạt nhiều backup liên tiếp phải sinh ra các ID khác nhau tăng dần."""
    r1 = client.post("/api/v1/system/backups", headers=admin_headers)
    r2 = client.post("/api/v1/system/backups", headers=admin_headers)
    r3 = client.post("/api/v1/system/backups", headers=admin_headers)

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r3.status_code == 202

    id1 = r1.json()["id"]
    id2 = r2.json()["id"]
    id3 = r3.json()["id"]

    assert id1 < id2 < id3
    count = db_session.query(BackupJob).count()
    assert count == 3


def test_post_backup_with_empty_json_body_accepted(client, admin_headers):
    """POST /system/backups không yêu cầu request body; gửi json rỗng '{}' vẫn chấp nhận 202."""
    response = client.post("/api/v1/system/backups", headers=admin_headers, json={})
    assert response.status_code == 202


# ============================================================================
# 2. POST /api/v1/system/backups: RBAC & AUTHENTICATION SECURITY
# ============================================================================

def test_post_backup_unauthenticated_no_token(client):
    """Gọi POST /system/backups không có header Authorization -> 401 UNAUTHENTICATED."""
    response = client.post("/api/v1/system/backups")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_post_backup_unauthenticated_empty_bearer(client):
    """Header Authorization: Bearer rỗng -> 401 UNAUTHENTICATED."""
    response = client.post("/api/v1/system/backups", headers={"Authorization": "Bearer "})
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_post_backup_unauthenticated_malformed_token(client):
    """Token rác / không đúng định dạng JWT -> 401 UNAUTHENTICATED."""
    response = client.post("/api/v1/system/backups", headers={"Authorization": "Bearer not-a-valid-token"})
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_post_backup_unauthenticated_wrong_auth_scheme(client):
    """Gửi Basic auth thay vì Bearer -> 401 UNAUTHENTICATED."""
    response = client.post("/api/v1/system/backups", headers={"Authorization": "Basic YWRtaW46MTIz"})
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_post_backup_forbidden_for_accountant(client, accountant_headers):
    """Kế toán (ACCOUNTANT) không có quyền sao lưu CSDL -> 403 FORBIDDEN."""
    response = client.post("/api/v1/system/backups", headers=accountant_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"


def test_post_backup_forbidden_for_treasurer(client, treasurer_headers):
    """Thủ quỹ (TREASURER) không có quyền sao lưu CSDL -> 403 FORBIDDEN."""
    response = client.post("/api/v1/system/backups", headers=treasurer_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"


def test_post_backup_forbidden_for_resident(client, resident_headers):
    """Cư dân (RESIDENT) không có quyền sao lưu CSDL -> 403 FORBIDDEN."""
    response = client.post("/api/v1/system/backups", headers=resident_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"


def test_post_backup_forbidden_when_must_change_password(client, admin_must_change_pwd_headers):
    """Tài khoản Admin có must_change_password=True bị chặn mọi thao tác -> 403 PASSWORD_CHANGE_REQUIRED."""
    response = client.post("/api/v1/system/backups", headers=admin_must_change_pwd_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_post_backup_forbidden_records_audit_log_access_denied(client, resident_headers, db_session):
    """Theo SSOT (Chương 1.2 & 1.3), mọi vi phạm 403 phải tự động ghi nhận Audit Log ACCESS_DENIED."""
    db_session.query(AuditLog).delete()
    db_session.commit()

    response = client.post("/api/v1/system/backups", headers=resident_headers)
    assert response.status_code == 403

    denied_logs = db_session.query(AuditLog).filter(AuditLog.action == "ACCESS_DENIED").all()
    assert len(denied_logs) >= 1, "Expected at least 1 ACCESS_DENIED audit log entry upon 403"


def test_post_backup_error_response_conforms_to_error_schema(client, resident_headers):
    """Response lỗi 403 phải tuân thủ Schema Error (code, message)."""
    response = client.post("/api/v1/system/backups", headers=resident_headers)
    assert response.status_code == 403
    data = response.json()
    assert "code" in data
    assert "message" in data
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str)


# ============================================================================
# 3. GET /api/v1/system/backups: HAPPY PATH & DATA RETRIEVAL
# ============================================================================

def test_get_backups_empty_list_returns_200(client, admin_headers):
    """Khi DB chưa có bản ghi backup nào, GET /system/backups trả về 200 OK."""
    response = client.get("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 200


def test_get_backups_empty_list_schema_page_meta(client, admin_headers):
    """Response trả về đầy đủ các trường phân trang: items, page, page_size, total."""
    response = client.get("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "page" in data
    assert "page_size" in data
    assert "total" in data


def test_get_backups_empty_list_default_values(client, admin_headers):
    """Khi DB trống: items=[], total=0, page=1, page_size=20."""
    response = client.get("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_get_backups_default_pagination_params(client, admin_headers):
    """Không truyền query params, mặc định page=1, page_size=20."""
    response = client.get("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_get_backups_reflects_newly_created_job(client, admin_headers):
    """Sau khi gọi POST tạo backup, gọi GET phải thấy job vừa tạo trong danh sách."""
    post_res = client.post("/api/v1/system/backups", headers=admin_headers)
    assert post_res.status_code == 202
    created_id = post_res.json()["id"]

    get_res = client.get("/api/v1/system/backups", headers=admin_headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == created_id


def test_get_backups_item_schema_conformance(client, admin_headers):
    """Mỗi phần tử trong danh sách items phải chứa đầy đủ các trường của BackupJob."""
    client.post("/api/v1/system/backups", headers=admin_headers)
    response = client.get("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 200
    item = response.json()["items"][0]
    for field in ["id", "status", "requested_by", "requested_at", "finished_at", "size_bytes"]:
        assert field in item, f"Missing field '{field}' in BackupJob item"


def test_get_backups_total_matches_count_of_created_jobs(client, admin_headers):
    """Tạo 4 jobs, total phải bằng 4 và items có 4 phần tử."""
    for _ in range(4):
        client.post("/api/v1/system/backups", headers=admin_headers)

    response = client.get("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4


def test_get_backups_ordered_descending_by_time(client, admin_headers):
    """Lịch sử sao lưu phải được sắp xếp mới nhất lên trước (ID hoặc requested_at giảm dần)."""
    r1 = client.post("/api/v1/system/backups", headers=admin_headers)
    r2 = client.post("/api/v1/system/backups", headers=admin_headers)
    r3 = client.post("/api/v1/system/backups", headers=admin_headers)

    id1, id2, id3 = r1.json()["id"], r2.json()["id"], r3.json()["id"]

    response = client.get("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 200
    items = response.json()["items"]
    assert items[0]["id"] == id3
    assert items[1]["id"] == id2
    assert items[2]["id"] == id1


def test_get_backups_custom_page_size(client, admin_headers):
    """Truyền page_size=2 thì items chỉ trả về tối đa 2 phần tử."""
    for _ in range(5):
        client.post("/api/v1/system/backups", headers=admin_headers)

    response = client.get("/api/v1/system/backups?page_size=2", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["page_size"] == 2
    assert data["total"] == 5


def test_get_backups_pagination_navigation_offset(client, admin_headers):
    """Trang 1 và Trang 2 không được trùng lặp bản ghi."""
    for _ in range(4):
        client.post("/api/v1/system/backups", headers=admin_headers)

    page1 = client.get("/api/v1/system/backups?page=1&page_size=2", headers=admin_headers).json()
    page2 = client.get("/api/v1/system/backups?page=2&page_size=2", headers=admin_headers).json()

    ids_page1 = [x["id"] for x in page1["items"]]
    ids_page2 = [x["id"] for x in page2["items"]]

    assert len(ids_page1) == 2
    assert len(ids_page2) == 2
    assert set(ids_page1).isdisjoint(set(ids_page2)), "Pages must not contain overlapping items"


def test_get_backups_pagination_last_partial_page(client, admin_headers):
    """Với 5 bản ghi và page_size=2, trang 3 chỉ trả về đúng 1 bản ghi còn lại."""
    for _ in range(5):
        client.post("/api/v1/system/backups", headers=admin_headers)

    response = client.get("/api/v1/system/backups?page=3&page_size=2", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["page"] == 3
    assert data["total"] == 5


def test_get_backups_page_out_of_bounds_returns_empty_items(client, admin_headers):
    """Truy vấn page=99 khi chỉ có 2 jobs -> items rỗng, total=2, status 200 OK."""
    for _ in range(2):
        client.post("/api/v1/system/backups", headers=admin_headers)

    response = client.get("/api/v1/system/backups?page=99&page_size=10", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 2
    assert data["page"] == 99


# ============================================================================
# 4. GET /api/v1/system/backups: RBAC & AUTHENTICATION SECURITY
# ============================================================================

def test_get_backups_unauthenticated_no_token(client):
    """Gọi GET /system/backups không có header Authorization -> 401 UNAUTHENTICATED."""
    response = client.get("/api/v1/system/backups")
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_get_backups_unauthenticated_empty_bearer(client):
    """Header Authorization: Bearer rỗng -> 401 UNAUTHENTICATED."""
    response = client.get("/api/v1/system/backups", headers={"Authorization": "Bearer "})
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_get_backups_unauthenticated_malformed_token(client):
    """Token rác / hỏng định dạng -> 401 UNAUTHENTICATED."""
    response = client.get("/api/v1/system/backups", headers={"Authorization": "Bearer bad-jwt-token"})
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_get_backups_unauthenticated_wrong_auth_scheme(client):
    """Dùng Token scheme thay vì Bearer -> 401 UNAUTHENTICATED."""
    response = client.get("/api/v1/system/backups", headers={"Authorization": "Token mytoken123"})
    assert response.status_code == 401
    data = response.json()
    assert data["code"] in ["UNAUTHENTICATED", "INVALID_CREDENTIALS"]


def test_get_backups_forbidden_for_accountant(client, accountant_headers):
    """Kế toán (ACCOUNTANT) không có quyền xem lịch sử sao lưu -> 403 FORBIDDEN."""
    response = client.get("/api/v1/system/backups", headers=accountant_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"


def test_get_backups_forbidden_for_treasurer(client, treasurer_headers):
    """Thủ quỹ (TREASURER) không có quyền xem lịch sử sao lưu -> 403 FORBIDDEN."""
    response = client.get("/api/v1/system/backups", headers=treasurer_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"


def test_get_backups_forbidden_for_resident(client, resident_headers):
    """Cư dân (RESIDENT) không có quyền xem lịch sử sao lưu -> 403 FORBIDDEN."""
    response = client.get("/api/v1/system/backups", headers=resident_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "FORBIDDEN"


def test_get_backups_forbidden_when_must_change_password(client, admin_must_change_pwd_headers):
    """Admin có must_change_password=True bị chặn -> 403 PASSWORD_CHANGE_REQUIRED."""
    response = client.get("/api/v1/system/backups", headers=admin_must_change_pwd_headers)
    assert response.status_code == 403
    data = response.json()
    assert data["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_get_backups_forbidden_records_audit_log_access_denied(client, resident_headers, db_session):
    """GET bị 403 phải tự động ghi nhận Audit Log ACCESS_DENIED."""
    db_session.query(AuditLog).delete()
    db_session.commit()

    response = client.get("/api/v1/system/backups", headers=resident_headers)
    assert response.status_code == 403

    denied_logs = db_session.query(AuditLog).filter(AuditLog.action == "ACCESS_DENIED").all()
    assert len(denied_logs) >= 1


# ============================================================================
# 5. GET /api/v1/system/backups: INPUT VALIDATION & BOUNDARY TESTING
# ============================================================================

def test_get_backups_invalid_page_zero(client, admin_headers):
    """page=0 vi phạm minimum=1 -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page=0", headers=admin_headers)
    assert response.status_code in [400, 422]
    data = response.json()
    if response.status_code == 400:
        assert data["code"] == "VALIDATION_ERROR"


def test_get_backups_invalid_page_negative(client, admin_headers):
    """page=-1 vi phạm minimum=1 -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page=-1", headers=admin_headers)
    assert response.status_code in [400, 422]
    data = response.json()
    if response.status_code == 400:
        assert data["code"] == "VALIDATION_ERROR"


def test_get_backups_invalid_page_negative_large(client, admin_headers):
    """page=-999 vi phạm minimum=1 -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page=-999", headers=admin_headers)
    assert response.status_code in [400, 422]


def test_get_backups_invalid_page_string(client, admin_headers):
    """page='invalid' không phải số nguyên -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page=invalid", headers=admin_headers)
    assert response.status_code in [400, 422]


def test_get_backups_invalid_page_float(client, admin_headers):
    """page=1.5 số thực không hợp lệ -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page=1.5", headers=admin_headers)
    assert response.status_code in [400, 422]


def test_get_backups_invalid_page_size_zero(client, admin_headers):
    """page_size=0 vi phạm minimum=1 -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page_size=0", headers=admin_headers)
    assert response.status_code in [400, 422]
    data = response.json()
    if response.status_code == 400:
        assert data["code"] == "VALIDATION_ERROR"


def test_get_backups_invalid_page_size_negative(client, admin_headers):
    """page_size=-5 vi phạm minimum=1 -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page_size=-5", headers=admin_headers)
    assert response.status_code in [400, 422]


def test_get_backups_invalid_page_size_exceed_max_100(client, admin_headers):
    """page_size=101 vượt quá maximum=100 -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page_size=101", headers=admin_headers)
    assert response.status_code in [400, 422]
    data = response.json()
    if response.status_code == 400:
        assert data["code"] == "VALIDATION_ERROR"


def test_get_backups_invalid_page_size_huge_number(client, admin_headers):
    """page_size=99999 vượt quá maximum=100 -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page_size=99999", headers=admin_headers)
    assert response.status_code in [400, 422]


def test_get_backups_invalid_page_size_string(client, admin_headers):
    """page_size='xyz' không phải số nguyên -> 400 VALIDATION_ERROR (hoặc 422)."""
    response = client.get("/api/v1/system/backups?page_size=xyz", headers=admin_headers)
    assert response.status_code in [400, 422]


def test_get_backups_boundary_page_min_1_valid(client, admin_headers):
    """Biên dưới hợp lệ: page=1 phải được chấp nhận bình thường (200 OK)."""
    response = client.get("/api/v1/system/backups?page=1", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["page"] == 1


def test_get_backups_boundary_page_size_min_1_valid(client, admin_headers):
    """Biên dưới hợp lệ: page_size=1 phải được chấp nhận bình thường (200 OK)."""
    response = client.get("/api/v1/system/backups?page_size=1", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["page_size"] == 1


def test_get_backups_boundary_page_size_max_100_valid(client, admin_headers):
    """Biên trên hợp lệ: page_size=100 phải được chấp nhận bình thường (200 OK)."""
    response = client.get("/api/v1/system/backups?page_size=100", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["page_size"] == 100


def test_get_backups_validation_error_structure(client, admin_headers):
    """Khi lỗi validation, cấu trúc response phải có code=VALIDATION_ERROR hoặc details chỉ rõ."""
    response = client.get("/api/v1/system/backups?page=-1", headers=admin_headers)
    assert response.status_code in [400, 422]
    data = response.json()
    if response.status_code == 400:
        assert data.get("code") == "VALIDATION_ERROR"
        assert "message" in data


# ============================================================================
# 6. HTTP METHODS & INVARIANTS & INTEGRITY TESTING
# ============================================================================

def test_backups_disallowed_method_put(client, admin_headers):
    """PUT /system/backups không được hỗ trợ -> 405 Method Not Allowed."""
    response = client.put("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 405


def test_backups_disallowed_method_delete(client, admin_headers):
    """DELETE /system/backups không được hỗ trợ -> 405 Method Not Allowed."""
    response = client.delete("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 405


def test_backups_disallowed_method_patch(client, admin_headers):
    """PATCH /system/backups không được hỗ trợ -> 405 Method Not Allowed."""
    response = client.patch("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 405


def test_backup_jobs_no_hard_delete_invariant(client, admin_headers, db_session):
    """Nguyên tắc No Hard Delete: các bản ghi backup_jobs tồn tại bất biến trong DB."""
    client.post("/api/v1/system/backups", headers=admin_headers)
    client.post("/api/v1/system/backups", headers=admin_headers)

    records = db_session.query(BackupJob).all()
    assert len(records) == 2
    for r in records:
        assert r.id is not None
        assert r.requested_at is not None


def test_inactive_admin_user_cannot_create_backup(client, db_session):
    """Tài khoản Admin đã bị vô hiệu hoá (is_active=False) bị từ chối truy cập."""
    admin_user = db_session.query(User).filter(User.id == 1).first()
    admin_user.is_active = False
    db_session.commit()

    headers = make_auth_headers(sub="1", username="admin_test", role="ADMIN")
    response = client.post("/api/v1/system/backups", headers=headers)
    assert response.status_code in [401, 403]


def test_inactive_admin_user_cannot_list_backups(client, db_session):
    """Tài khoản Admin đã bị vô hiệu hoá (is_active=False) không thể xem lịch sử sao lưu."""
    admin_user = db_session.query(User).filter(User.id == 1).first()
    admin_user.is_active = False
    db_session.commit()

    headers = make_auth_headers(sub="1", username="admin_test", role="ADMIN")
    response = client.get("/api/v1/system/backups", headers=headers)
    assert response.status_code in [401, 403]


def test_get_backups_pagination_total_accurate_with_many_items(client, admin_headers):
    """Tạo 25 jobs, kiểm tra total luôn là 25 và items lấy đúng 10 bản ghi mỗi trang."""
    for _ in range(25):
        client.post("/api/v1/system/backups", headers=admin_headers)

    p1 = client.get("/api/v1/system/backups?page=1&page_size=10", headers=admin_headers).json()
    assert p1["total"] == 25
    assert len(p1["items"]) == 10

    p2 = client.get("/api/v1/system/backups?page=2&page_size=10", headers=admin_headers).json()
    assert p2["total"] == 25
    assert len(p2["items"]) == 10

    p3 = client.get("/api/v1/system/backups?page=3&page_size=10", headers=admin_headers).json()
    assert p3["total"] == 25
    assert len(p3["items"]) == 5


def test_backup_job_size_bytes_non_negative_if_present(client, admin_headers):
    """Nếu size_bytes có giá trị thì phải >= 0."""
    response = client.post("/api/v1/system/backups", headers=admin_headers)
    assert response.status_code == 202
    data = response.json()
    if data["size_bytes"] is not None:
        assert data["size_bytes"] >= 0


def test_post_backup_does_not_mutate_existing_jobs(client, admin_headers, db_session):
    """Tạo mới một backup job không làm thay đổi dữ liệu của các backup job trước đó."""
    r1 = client.post("/api/v1/system/backups", headers=admin_headers)
    job1_data = r1.json()

    r2 = client.post("/api/v1/system/backups", headers=admin_headers)
    job2_data = r2.json()

    db_job1 = db_session.query(BackupJob).filter(BackupJob.id == job1_data["id"]).first()
    assert db_job1 is not None
    assert db_job1.id == job1_data["id"]
    assert db_job1.requested_by == job1_data["requested_by"]
