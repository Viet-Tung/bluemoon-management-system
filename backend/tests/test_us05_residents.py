import itertools
from datetime import date, timedelta
import pytest
from sqlalchemy import text

from app.core.security import create_access_token
from app.models.property import Apartment, Household, Resident
from app.models.user import AuditLog

_id_gen = itertools.count(10000)
_cccd_gen = itertools.count(100000000)


def gen_cccd(digits: int = 12) -> str:
    """Sinh chuỗi CCCD hợp lệ duy nhất."""
    val = next(_cccd_gen)
    return str(val).zfill(digits)


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================

@pytest.fixture
def auth_headers_accountant():
    token = create_access_token({
        "sub": "2",
        "username": "accountant_test",
        "role": "ACCOUNTANT",
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_resident_custom():
    token = create_access_token({
        "sub": "3",
        "username": "resident_101",
        "role": "RESIDENT",
        "household_id": 101,
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def household_factory(db_session):
    """Tạo nhanh hộ gia đình trong test CSDL sử dụng ORM để tránh xung đột khóa chính."""
    def _create(status="ACTIVE", with_head=True):
        idx = next(_id_gen)
        apt = Apartment(
            code=f"P.TEST.{idx}",
            floor=5,
            area_m2=65.0,
            status="ACTIVE",
            note="Test Apartment"
        )
        db_session.add(apt)
        db_session.flush()

        hh = Household(
            household_code=f"HO-TEST-{idx}",
            status=status,
            contact_phone="0912345678",
            contact_email="test@bluemoon.local"
        )
        db_session.add(hh)
        db_session.flush()

        head_id = None
        if with_head:
            res = Resident(
                household_id=hh.id,
                full_name="Chủ Hộ Mẫu",
                date_of_birth=date(1985, 5, 15),
                gender="NAM",
                cccd=gen_cccd(12),
                is_head=True,
                residence_status="THUONG_TRU",
                is_deleted=False
            )
            db_session.add(res)
            db_session.flush()
            head_id = res.id

        db_session.commit()
        return {"household_id": hh.id, "apartment_id": apt.id, "head_id": head_id}

    return _create


# ==============================================================================
# 1. TEST POST /households/{id}/residents (US-05)
# ==============================================================================

class TestCreateResident:
    """Kiểm thử thêm nhân khẩu vào hộ gia đình (US-05)."""

    def test_create_adult_resident_with_12_digits_cccd_success(self, client, auth_headers_admin, household_factory):
        """Thêm nhân khẩu người lớn (>= 14 tuổi) có CCCD 12 số -> 201 Created."""
        h = household_factory()
        payload = {
            "full_name": "Nguyễn Văn An",
            "date_of_birth": "1995-10-20",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "phone": "0987654321",
            "email": "an.nguyen@example.com",
            "relationship_to_head": "CON",
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["full_name"] == "Nguyễn Văn An"
        assert data["cccd"] == payload["cccd"]
        assert data["relationship_to_head"] == "CON"
        assert data["is_head"] is False
        assert data["residence_status"] == "THUONG_TRU"
        assert data["is_deleted"] is False

    def test_create_adult_resident_with_9_digits_cccd_success(self, client, auth_headers_admin, household_factory):
        """Thêm nhân khẩu có CMND 9 số -> 201 Created."""
        h = household_factory()
        payload = {
            "full_name": "Trần Thị Mai",
            "date_of_birth": "1990-01-01",
            "gender": "NU",
            "cccd": gen_cccd(9),
            "relationship_to_head": "VỢ",
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["cccd"] == payload["cccd"]

    def test_create_child_resident_without_cccd_success(self, client, auth_headers_admin, household_factory):
        """AC-05.3: Trẻ em dưới 14 tuổi cho phép để trống CCCD -> 201 Created."""
        h = household_factory()
        payload = {
            "full_name": "Nguyễn Bé Con",
            "date_of_birth": str(date.today() - timedelta(days=365 * 5)),  # 5 tuổi
            "gender": "NAM",
            "cccd": None,
            "relationship_to_head": "CON",
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["cccd"] is None

    def test_create_child_resident_with_cccd_success(self, client, auth_headers_admin, household_factory):
        """Trẻ em dưới 14 tuổi nếu có CCCD định danh vẫn được phép nhập -> 201 Created."""
        h = household_factory()
        cccd_val = gen_cccd(12)
        payload = {
            "full_name": "Nguyễn Bé Lớn",
            "date_of_birth": str(date.today() - timedelta(days=365 * 10)),  # 10 tuổi
            "gender": "NU",
            "cccd": cccd_val,
            "relationship_to_head": "CON",
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        assert resp.json()["cccd"] == cccd_val

    def test_create_head_when_no_head_exists_success(self, client, auth_headers_admin, household_factory):
        """Tạo nhân khẩu chủ hộ khi hộ chưa có chủ hộ -> 201 Created."""
        h = household_factory(with_head=False)
        payload = {
            "full_name": "Lê Văn Chủ Hộ",
            "date_of_birth": "1980-04-12",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": True,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_head"] is True
        assert data["relationship_to_head"] == "CHỦ HỘ"

    def test_create_adult_missing_cccd_fails_400(self, client, auth_headers_admin, household_factory):
        """AC-05.3: Nhân khẩu >= 14 tuổi bắt buộc có CCCD, nếu thiếu trả về 400 VALIDATION_ERROR."""
        h = household_factory()
        payload = {
            "full_name": "Lê Trưởng Thành",
            "date_of_birth": "2000-01-01",  # 26 tuổi
            "gender": "NAM",
            "cccd": None,
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "14 tuổi" in data["message"]

    def test_create_resident_future_dob_fails_400(self, client, auth_headers_admin, household_factory):
        """Ngày sinh ở tương lai trả về 400 VALIDATION_ERROR."""
        h = household_factory()
        payload = {
            "full_name": "Người Tương Lai",
            "date_of_birth": str(date.today() + timedelta(days=10)),
            "gender": "NAM",
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        data = resp.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "ngày hiện tại" in data["message"]

    def test_create_resident_whitespace_name_fails_400(self, client, auth_headers_admin, household_factory):
        """Họ và tên rỗng hoặc chỉ có dấu cách trả về 400 VALIDATION_ERROR."""
        h = household_factory()
        payload = {
            "full_name": "     ",
            "date_of_birth": "1998-05-05",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_resident_invalid_cccd_format_fails_400(self, client, auth_headers_admin, household_factory):
        """CCCD sai định dạng (chứa chữ hoặc độ dài không phải 9/12) bị từ chối 400."""
        h = household_factory()
        payload = {
            "full_name": "Phạm Văn Sai",
            "date_of_birth": "1999-09-09",
            "gender": "NAM",
            "cccd": "12345ABCDE",
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 400
        assert resp.json()["code"] == "VALIDATION_ERROR"

    def test_create_resident_nonexistent_household_fails_404(self, client, auth_headers_admin):
        """Hộ gia đình không tồn tại trả về 404 NOT_FOUND."""
        payload = {
            "full_name": "Ai Đó",
            "date_of_birth": "1990-01-01",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }
        resp = client.post("/api/v1/households/999999/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_create_head_already_exists_fails_409(self, client, auth_headers_admin, household_factory):
        """AC-05.1: Không thể tạo thêm chủ hộ khi hộ đã có chủ hộ -> 409 HEAD_ALREADY_EXISTS."""
        h = household_factory(with_head=True)
        payload = {
            "full_name": "Chủ Hộ Thứ Hai",
            "date_of_birth": "1988-08-08",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": True,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 409
        assert resp.json()["code"] == "HEAD_ALREADY_EXISTS"

    def test_create_resident_duplicate_cccd_fails_409(self, client, auth_headers_admin, household_factory):
        """AC-05.2: Trùng CCCD trên toàn hệ thống trả về 409 DUPLICATE_CCCD."""
        h1 = household_factory()
        h2 = household_factory()
        same_cccd = gen_cccd(12)

        # Thêm vào hộ 1 thành công
        payload1 = {
            "full_name": "Người Thứ Nhất",
            "date_of_birth": "1992-02-02",
            "gender": "NAM",
            "cccd": same_cccd,
            "is_head": False,
        }
        resp1 = client.post(f"/api/v1/households/{h1['household_id']}/residents", json=payload1, headers=auth_headers_admin)
        assert resp1.status_code == 201

        # Thêm cùng số CCCD đó vào hộ 2 phải bị 409
        payload2 = {
            "full_name": "Người Thứ Hai",
            "date_of_birth": "1993-03-03",
            "gender": "NU",
            "cccd": same_cccd,
            "is_head": False,
        }
        resp2 = client.post(f"/api/v1/households/{h2['household_id']}/residents", json=payload2, headers=auth_headers_admin)
        assert resp2.status_code == 409
        assert resp2.json()["code"] == "DUPLICATE_CCCD"

    def test_create_resident_records_audit_log(self, client, auth_headers_admin, household_factory, db_session):
        """US-32: Thao tác tạo nhân khẩu được ghi lại vào bảng audit_logs."""
        h = household_factory()
        payload = {
            "full_name": "Kiểm Tra Audit",
            "date_of_birth": "1994-04-04",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_admin)
        assert resp.status_code == 201
        created_id = resp.json()["id"]

        audit = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "RESIDENT",
            AuditLog.entity_id == str(created_id),
            AuditLog.action == "CREATE_RESIDENT"
        ).first()
        assert audit is not None
        assert audit.new_value["full_name"] == "Kiểm Tra Audit"

    def test_create_resident_rbac_forbidden_for_non_admin(self, client, auth_headers_accountant, auth_headers_resident_custom, household_factory):
        """RBAC: Kế toán và Cư dân không có quyền tạo nhân khẩu -> 403 FORBIDDEN."""
        h = household_factory()
        payload = {
            "full_name": "Test Quyền",
            "date_of_birth": "1991-01-01",
            "gender": "NAM",
            "cccd": gen_cccd(12),
        }
        # Accountant
        r1 = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_accountant)
        assert r1.status_code == 403

        # Resident
        r2 = client.post(f"/api/v1/households/{h['household_id']}/residents", json=payload, headers=auth_headers_resident_custom)
        assert r2.status_code == 403


# ==============================================================================
# 2. TEST GET /households/{id}/residents (US-06)
# ==============================================================================

class TestListResidents:
    """Kiểm thử danh sách nhân khẩu trong hộ (US-06)."""

    def test_list_residents_admin_and_accountant_success(self, client, auth_headers_admin, auth_headers_accountant, household_factory):
        """Cả ADMIN và ACCOUNTANT đều có quyền xem danh sách nhân khẩu của hộ."""
        h = household_factory()
        # Admin
        resp_admin = client.get(f"/api/v1/households/{h['household_id']}/residents", headers=auth_headers_admin)
        assert resp_admin.status_code == 200
        assert resp_admin.json()["total"] >= 1

        # Accountant
        resp_acc = client.get(f"/api/v1/households/{h['household_id']}/residents", headers=auth_headers_accountant)
        assert resp_acc.status_code == 200
        assert resp_acc.json()["total"] == resp_admin.json()["total"]

    def test_list_residents_head_is_first(self, client, auth_headers_admin, household_factory):
        """Chủ hộ luôn được sắp xếp ở vị trí đầu tiên trong danh sách."""
        h = household_factory(with_head=True)
        # Thêm 2 thành viên
        for name in ["Thành Viên 1", "Thành Viên 2"]:
            client.post(f"/api/v1/households/{h['household_id']}/residents", json={
                "full_name": name,
                "date_of_birth": "2001-01-01",
                "gender": "NAM",
                "cccd": gen_cccd(12),
                "is_head": False,
            }, headers=auth_headers_admin)

        resp = client.get(f"/api/v1/households/{h['household_id']}/residents", headers=auth_headers_admin)
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 3
        assert items[0]["is_head"] is True
        assert items[1]["is_head"] is False
        assert items[2]["is_head"] is False

    def test_list_residents_pagination(self, client, auth_headers_admin, household_factory):
        """Kiểm thử phân trang danh sách nhân khẩu."""
        h = household_factory(with_head=True)
        for i in range(3):
            client.post(f"/api/v1/households/{h['household_id']}/residents", json={
                "full_name": f"Người Số {i}",
                "date_of_birth": "2002-02-02",
                "gender": "NU",
                "cccd": gen_cccd(12),
                "is_head": False,
            }, headers=auth_headers_admin)

        resp = client.get(f"/api/v1/households/{h['household_id']}/residents?page=1&page_size=2", headers=auth_headers_admin)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 4
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_list_residents_excludes_deleted_by_default(self, client, auth_headers_admin, household_factory):
        """Mặc định nhân khẩu đã xóa mềm sẽ không xuất hiện trong danh sách."""
        h = household_factory(with_head=True)
        resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Sắp Bị Xóa",
            "date_of_birth": "1996-06-06",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }, headers=auth_headers_admin)
        mem_id = resp.json()["id"]

        # Xóa nhân khẩu
        client.delete(f"/api/v1/residents/{mem_id}", headers=auth_headers_admin)

        # Danh sách mặc định không có nhân khẩu này
        r_list = client.get(f"/api/v1/households/{h['household_id']}/residents", headers=auth_headers_admin)
        item_ids = [item["id"] for item in r_list.json()["items"]]
        assert mem_id not in item_ids

        # Nếu admin truyền include_deleted=true sẽ thấy lại
        r_inc = client.get(f"/api/v1/households/{h['household_id']}/residents?include_deleted=true", headers=auth_headers_admin)
        inc_ids = [item["id"] for item in r_inc.json()["items"]]
        assert mem_id in inc_ids

    def test_list_residents_nonexistent_household_fails_404(self, client, auth_headers_admin):
        """Hộ không tồn tại trả về 404 NOT_FOUND."""
        resp = client.get("/api/v1/households/888888/residents", headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"


# ==============================================================================
# 3. TEST GET /residents/{id} (US-06)
# ==============================================================================

class TestGetResidentDetail:
    """Kiểm thử xem chi tiết nhân khẩu (US-06)."""

    def test_get_resident_detail_admin_and_accountant_success(self, client, auth_headers_admin, auth_headers_accountant, household_factory):
        """Lấy chi tiết nhân khẩu thành công."""
        h = household_factory(with_head=True)
        head_id = h["head_id"]

        r_admin = client.get(f"/api/v1/residents/{head_id}", headers=auth_headers_admin)
        assert r_admin.status_code == 200
        assert r_admin.json()["id"] == head_id

        r_acc = client.get(f"/api/v1/residents/{head_id}", headers=auth_headers_accountant)
        assert r_acc.status_code == 200
        assert r_acc.json()["id"] == head_id

    def test_get_resident_detail_not_found_fails_404(self, client, auth_headers_admin):
        """Không tìm thấy nhân khẩu -> 404 NOT_FOUND."""
        resp = client.get("/api/v1/residents/777777", headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"

    def test_get_deleted_resident_detail_fails_404(self, client, auth_headers_admin, household_factory):
        """Nhân khẩu đã bị xóa mềm gọi chi tiết cũng trả về 404 NOT_FOUND."""
        h = household_factory()
        post_resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Tạm Thời",
            "date_of_birth": "1997-07-07",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }, headers=auth_headers_admin)
        rid = post_resp.json()["id"]

        client.delete(f"/api/v1/residents/{rid}", headers=auth_headers_admin)

        resp = client.get(f"/api/v1/residents/{rid}", headers=auth_headers_admin)
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"


# ==============================================================================
# 4. TEST PATCH /residents/{id} (US-06)
# ==============================================================================

class TestUpdateResident:
    """Kiểm thử cập nhật nhân khẩu (US-06)."""

    def test_update_resident_basic_info_success(self, client, auth_headers_admin, household_factory, db_session):
        """Cập nhật họ tên, số điện thoại, email thành công."""
        h = household_factory()
        post_resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Tên Cũ",
            "date_of_birth": "1993-03-03",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "phone": "0911111111",
            "email": "old@example.com",
            "is_head": False,
        }, headers=auth_headers_admin)
        rid = post_resp.json()["id"]

        patch_payload = {
            "full_name": "Tên Đã Đổi Mới",
            "phone": "0999999999",
            "email": "new@example.com",
        }
        patch_resp = client.patch(f"/api/v1/residents/{rid}", json=patch_payload, headers=auth_headers_admin)
        assert patch_resp.status_code == 200
        data = patch_resp.json()
        assert data["full_name"] == "Tên Đã Đổi Mới"
        assert data["phone"] == "0999999999"
        assert data["email"] == "new@example.com"

        # Kiểm tra AuditLog
        audit = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "RESIDENT",
            AuditLog.entity_id == str(rid),
            AuditLog.action == "UPDATE_RESIDENT"
        ).first()
        assert audit is not None
        assert audit.old_value["full_name"] == "Tên Cũ"
        assert audit.new_value["full_name"] == "Tên Đã Đổi Mới"

    def test_update_resident_new_valid_cccd_success(self, client, auth_headers_admin, household_factory):
        """Cập nhật sang số CCCD hợp lệ mới không trùng lặp -> 200 OK."""
        h = household_factory()
        post_resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Đổi CCCD",
            "date_of_birth": "1995-05-05",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }, headers=auth_headers_admin)
        rid = post_resp.json()["id"]

        new_cccd = gen_cccd(12)
        patch_resp = client.patch(f"/api/v1/residents/{rid}", json={"cccd": new_cccd}, headers=auth_headers_admin)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["cccd"] == new_cccd

    def test_update_resident_same_cccd_does_not_conflict(self, client, auth_headers_admin, household_factory):
        """Gửi lại chính số CCCD hiện tại của nhân khẩu không bị báo 409 DUPLICATE_CCCD."""
        h = household_factory()
        my_cccd = gen_cccd(12)
        post_resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Giữ CCCD",
            "date_of_birth": "1992-02-02",
            "gender": "NAM",
            "cccd": my_cccd,
            "is_head": False,
        }, headers=auth_headers_admin)
        rid = post_resp.json()["id"]

        patch_resp = client.patch(f"/api/v1/residents/{rid}", json={"cccd": my_cccd, "full_name": "Tên Mới"}, headers=auth_headers_admin)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["cccd"] == my_cccd

    def test_update_resident_duplicate_cccd_fails_409(self, client, auth_headers_admin, household_factory):
        """Đổi sang CCCD đang thuộc về một nhân khẩu khác -> 409 DUPLICATE_CCCD."""
        h = household_factory()
        other_cccd = gen_cccd(12)
        # Người 1 có other_cccd
        client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Người 1",
            "date_of_birth": "1990-01-01",
            "gender": "NAM",
            "cccd": other_cccd,
            "is_head": False,
        }, headers=auth_headers_admin)

        # Người 2
        r2 = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Người 2",
            "date_of_birth": "1991-01-01",
            "gender": "NU",
            "cccd": gen_cccd(12),
            "is_head": False,
        }, headers=auth_headers_admin).json()

        # Người 2 đổi CCCD sang other_cccd
        patch_resp = client.patch(f"/api/v1/residents/{r2['id']}", json={"cccd": other_cccd}, headers=auth_headers_admin)
        assert patch_resp.status_code == 409
        assert patch_resp.json()["code"] == "DUPLICATE_CCCD"

    def test_update_child_to_adult_without_cccd_fails_400(self, client, auth_headers_admin, household_factory):
        """Cập nhật ngày sinh khiến trẻ em thành người lớn mà không có CCCD -> 400 VALIDATION_ERROR."""
        h = household_factory()
        # Tạo trẻ em 5 tuổi không CCCD
        child = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Bé Năm Tuổi",
            "date_of_birth": str(date.today() - timedelta(days=365 * 5)),
            "gender": "NAM",
            "cccd": None,
            "is_head": False,
        }, headers=auth_headers_admin).json()

        # Sửa ngày sinh thành 20 năm trước (20 tuổi) nhưng không cung cấp CCCD
        patch_resp = client.patch(f"/api/v1/residents/{child['id']}", json={
            "date_of_birth": "2004-01-01"
        }, headers=auth_headers_admin)
        assert patch_resp.status_code == 400
        assert patch_resp.json()["code"] == "VALIDATION_ERROR"
        assert "14 tuổi" in patch_resp.json()["message"]

    def test_update_adult_clearing_cccd_fails_400(self, client, auth_headers_admin, household_factory):
        """Người lớn cố tình xóa bỏ CCCD -> 400 VALIDATION_ERROR."""
        h = household_factory()
        adult = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Người Lớn",
            "date_of_birth": "1990-01-01",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }, headers=auth_headers_admin).json()

        patch_resp = client.patch(f"/api/v1/residents/{adult['id']}", json={
            "cccd": None
        }, headers=auth_headers_admin)
        assert patch_resp.status_code == 400
        assert patch_resp.json()["code"] == "VALIDATION_ERROR"

    def test_update_resident_rbac_forbidden_for_accountant(self, client, auth_headers_accountant, household_factory):
        """Kế toán không có quyền sửa thông tin nhân khẩu -> 403 FORBIDDEN."""
        h = household_factory()
        resp = client.patch(f"/api/v1/residents/{h['head_id']}", json={"full_name": "Đổi Lén"}, headers=auth_headers_accountant)
        assert resp.status_code == 403


# ==============================================================================
# 5. TEST DELETE /residents/{id} (US-06)
# ==============================================================================

class TestDeleteResident:
    """Kiểm thử xóa logic nhân khẩu (US-06)."""

    def test_delete_member_resident_success(self, client, auth_headers_admin, household_factory, db_session):
        """Xóa mềm thành viên bình thường thành công -> 204 No Content."""
        h = household_factory()
        post_resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Thành Viên Thường",
            "date_of_birth": "1999-12-12",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }, headers=auth_headers_admin)
        rid = post_resp.json()["id"]

        del_resp = client.delete(f"/api/v1/residents/{rid}", headers=auth_headers_admin)
        assert del_resp.status_code == 204

        # Kiểm tra trong DB: is_deleted = True
        res = db_session.query(Resident).filter(Resident.id == rid).first()
        assert res.is_deleted is True
        assert res.deleted_at is not None

        # Kiểm tra AuditLog
        audit = db_session.query(AuditLog).filter(
            AuditLog.entity_type == "RESIDENT",
            AuditLog.entity_id == str(rid),
            AuditLog.action == "DELETE_RESIDENT"
        ).first()
        assert audit is not None
        assert audit.new_value == {"is_deleted": True}

    def test_delete_head_resident_in_active_household_fails_409(self, client, auth_headers_admin, household_factory):
        """AC-06.1: Chặn xóa Chủ hộ khi hộ vẫn đang hoạt động -> 409 CANNOT_DELETE_HEAD."""
        h = household_factory(status="ACTIVE", with_head=True)
        head_id = h["head_id"]

        del_resp = client.delete(f"/api/v1/residents/{head_id}", headers=auth_headers_admin)
        assert del_resp.status_code == 409
        data = del_resp.json()
        assert data["code"] == "CANNOT_DELETE_HEAD"
        assert "Chủ hộ" in data["message"]

    def test_delete_resident_already_deleted_fails_404(self, client, auth_headers_admin, household_factory):
        """Xóa nhân khẩu đã bị xóa trước đó trả về 404 NOT_FOUND."""
        h = household_factory()
        post_resp = client.post(f"/api/v1/households/{h['household_id']}/residents", json={
            "full_name": "Xóa Hai Lần",
            "date_of_birth": "1998-01-01",
            "gender": "NAM",
            "cccd": gen_cccd(12),
            "is_head": False,
        }, headers=auth_headers_admin)
        rid = post_resp.json()["id"]

        # Xóa lần 1
        assert client.delete(f"/api/v1/residents/{rid}", headers=auth_headers_admin).status_code == 204

        # Xóa lần 2
        r2 = client.delete(f"/api/v1/residents/{rid}", headers=auth_headers_admin)
        assert r2.status_code == 404
        assert r2.json()["code"] == "NOT_FOUND"

    def test_delete_resident_rbac_forbidden_for_accountant(self, client, auth_headers_accountant, household_factory):
        """Kế toán không có quyền xóa nhân khẩu -> 403 FORBIDDEN."""
        h = household_factory()
        resp = client.delete(f"/api/v1/residents/{h['head_id']}", headers=auth_headers_accountant)
        assert resp.status_code == 403
