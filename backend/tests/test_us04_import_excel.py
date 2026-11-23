from datetime import date, timedelta
import io
import os
import openpyxl
import pytest
from sqlalchemy import func, select

from app.core.security import create_access_token, get_password_hash
from app.models.property import Apartment, ApartmentOccupancy, Household, Resident
from app.models.user import AuditLog, Role, User

# ==============================================================================
# HELPERS & FIXTURES
# ==============================================================================

DEFAULT_HEADERS = [
    "Mã căn hộ",
    "Tầng",
    "Diện tích (m2)",
    "Mã hộ gia đình",
    "SĐT liên hệ",
    "Email liên hệ",
    "Họ và tên",
    "Ngày sinh",
    "Giới tính",
    "Số CCCD",
    "Quan hệ với chủ hộ",
    "Là chủ hộ",
]


def create_excel_bytes(rows: list, headers: list = None) -> bytes:
    """Tạo file Excel .xlsx trong bộ nhớ dạng bytes."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Import_Cu_Dan"

    header_cols = headers if headers is not None else DEFAULT_HEADERS
    ws.append(header_cols)

    for r in rows:
        ws.append(r)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def clean_import_tables(db_session):
    """Đảm bảo CSDL sạch sẽ trước và sau mỗi test case."""
    def _cleanup():
        try:
            db_session.query(Resident).delete()
            db_session.query(ApartmentOccupancy).delete()
            db_session.query(Household).delete()
            db_session.query(Apartment).delete()
            db_session.query(User).filter(User.id > 4, User.id != 99).delete()
            db_session.query(AuditLog).delete()
            db_session.commit()
        except Exception:
            db_session.rollback()

    _cleanup()
    yield
    _cleanup()


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
def auth_headers_treasurer(db_session):
    # Đảm bảo có user role TREASURER trong CSDL test
    user = db_session.scalar(select(User).where(User.id == 99))
    if not user:
        user = User(
            id=99,
            username="treasurer_test",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test",
            role_id=3,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        db_session.commit()

    token = create_access_token({
        "sub": "99",
        "username": "treasurer_test",
        "role": "TREASURER",
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_resident():
    token = create_access_token({
        "sub": "3",
        "username": "resident_101",
        "role": "RESIDENT",
        "household_id": 101,
        "must_change_password": False,
    })
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. SUCCESS / HAPPY PATH TESTS
# ==============================================================================

class TestImportExcelSuccess:
    """Kiểm tra kịch bản import thành công toàn bộ dữ liệu hợp lệ."""

    def test_import_valid_file_creates_all_entities(self, client, auth_headers_admin, db_session):
        """
        Import file hợp lệ gồm 2 căn hộ, 2 hộ gia đình, 3 nhân khẩu:
        - Căn hộ A101 (Tầng 1, 75.5m2) -> Hộ H101 (2 nhân khẩu: 1 chủ hộ CCCD 12 số, 1 con dưới 14 tuổi không CCCD)
        - Căn hộ B202 (Tầng 2, 90.0m2) -> Hộ H202 (1 nhân khẩu: chủ hộ CCCD 9 số)
        Kì vọng:
        - HTTP 200 OK, total_rows=3, imported_rows=3
        - CSDL được tạo đầy đủ Apartment, Household, ApartmentOccupancy, Resident, User và AuditLog
        """
        rows = [
            # Căn A101 - Hộ H101
            ["A101", 1, 75.5, "H101", "0901234567", "h101@gmail.com", "Nguyễn Văn A", "1985-05-15", "NAM", "001085001234", "CHỦ HỘ", "CÓ"],
            ["A101", 1, 75.5, "H101", "0901234567", "h101@gmail.com", "Nguyễn Văn B", "2015-08-20", "NAM", None, "CON", "KHÔNG"],
            # Căn B202 - Hộ H202
            ["B202", 2, 90.0, "H202", "0912345678", "h202@gmail.com", "Trần Thị C", "1990-10-10", "NU", "123456789", "CHỦ HỘ", "X"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("residents.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 3
        assert data["imported_rows"] == 3

        # Kiểm tra Căn hộ trong CSDL
        apts = db_session.scalars(select(Apartment).order_by(Apartment.code)).all()
        assert len(apts) == 2
        assert apts[0].code == "A101"
        assert apts[0].floor == 1
        assert apts[0].area_m2 == 75.5
        assert apts[0].status == "ACTIVE"

        assert apts[1].code == "B202"
        assert apts[1].floor == 2
        assert apts[1].area_m2 == 90.0

        # Kiểm tra Hộ gia đình trong CSDL
        hhs = db_session.scalars(select(Household).order_by(Household.household_code)).all()
        assert len(hhs) == 2
        assert hhs[0].household_code == "H101"
        assert hhs[0].contact_phone == "0901234567"
        assert hhs[0].contact_email == "h101@gmail.com"
        assert hhs[0].status == "ACTIVE"

        # Kiểm tra Lịch sử cư trú (ApartmentOccupancy)
        occs = db_session.scalars(select(ApartmentOccupancy)).all()
        assert len(occs) == 2
        for occ in occs:
            assert occ.start_date == date.today()
            assert occ.end_date is None

        # Kiểm tra Nhân khẩu (Resident)
        residents = db_session.scalars(select(Resident).order_by(Resident.full_name)).all()
        assert len(residents) == 3
        # Nguyễn Văn A (Chủ hộ)
        r_a = next(r for r in residents if r.full_name == "Nguyễn Văn A")
        assert r_a.cccd == "001085001234"
        assert r_a.is_head is True
        assert r_a.residence_status == "THUONG_TRU"
        assert r_a.is_deleted is False

        # Nguyễn Văn B (Con, dưới 14 tuổi, không CCCD)
        r_b = next(r for r in residents if r.full_name == "Nguyễn Văn B")
        assert r_b.cccd is None
        assert r_b.is_head is False

        # Kiểm tra Tài khoản Cư dân sinh tự động (D-12, AC-30.2)
        users = db_session.scalars(select(User).where(User.id > 4, User.id != 99)).all()
        assert len(users) == 2
        usernames = [u.username for u in users]
        assert "res_h101" in usernames
        assert "res_h202" in usernames
        for u in users:
            assert u.must_change_password is True
            assert u.is_active is True
            assert u.failed_login_count == 0

        # Kiểm tra Audit Log (US-32)
        audits = db_session.scalars(select(AuditLog).where(AuditLog.action == "IMPORT_EXCEL")).all()
        assert len(audits) == 1
        assert audits[0].entity_type == "SYSTEM"
        assert audits[0].new_value["total_rows"] == 3
        assert audits[0].new_value["imported_rows"] == 3
        assert audits[0].new_value["apartments_count"] == 2
        assert audits[0].new_value["households_count"] == 2

    def test_import_official_template_file(self, client, auth_headers_admin, db_session):
        """Import trực tiếp file mẫu DOC-01_MAU_IMPORT_CU_DAN.xlsx của dự án."""
        template_path = os.path.join("docs", "DOC-01_MAU_IMPORT_CU_DAN.xlsx")
        assert os.path.exists(template_path), "File mẫu docs/DOC-01_MAU_IMPORT_CU_DAN.xlsx không tồn tại."

        with open(template_path, "rb") as f:
            template_bytes = f.read()

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("DOC-01_MAU_IMPORT_CU_DAN.xlsx", template_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 5
        assert data["imported_rows"] == 5

        # CSDL phải có 5 nhân khẩu, 2 hộ gia đình, 2 căn hộ
        res_count = db_session.scalar(select(func.count(Resident.id)))
        assert res_count == 5
        hh_count = db_session.scalar(select(func.count(Household.id)))
        assert hh_count == 2
        apt_count = db_session.scalar(select(func.count(Apartment.id)))
        assert apt_count == 2

    def test_import_reuses_existing_vacant_apartment(self, client, auth_headers_admin, db_session):
        """Căn hộ đã tồn tại trong DB nhưng đang trống (chưa có người ở) thì tái sử dụng bình thường."""
        existing_apt = Apartment(code="A303", floor=3, area_m2=80.0, status="ACTIVE")
        db_session.add(existing_apt)
        db_session.commit()

        rows = [
            ["A303", 3, 80.0, "H303", "0933333333", "h303@gmail.com", "Lê Văn C", "1992-03-03", "NAM", "001092003333", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("reuse.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 200
        # Số căn hộ trong DB vẫn chỉ là 1 căn A303
        apts = db_session.scalars(select(Apartment).where(Apartment.code == "A303")).all()
        assert len(apts) == 1


# ==============================================================================
# 2. ACID TRANSACTION ROLLBACK TESTS (AC-04.2)
# ==============================================================================

class TestImportExcelACIDRollback:
    """Kiểm tra nguyên tắc ACID: Có bất kỳ lỗi nào -> Rollback 100%, không lưu bản ghi nào."""

    def test_rollback_negative_area(self, client, auth_headers_admin, db_session):
        """Dòng 1 hợp lệ, Dòng 2 có diện tích âm -> Rollback toàn bộ, 0 bản ghi nào được lưu."""
        rows = [
            ["A101", 1, 75.0, "H101", "0901234567", "h101@gmail.com", "Nguyễn Văn A", "1985-01-01", "NAM", "001085001111", "CHỦ HỘ", "CÓ"],
            ["A102", 1, -50.0, "H102", "0901234568", "h102@gmail.com", "Trần Văn B", "1988-02-02", "NAM", "001088002222", "CHỦ HỘ", "CÓ"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("invalid_area.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "area_m2" for d in data.get("details", []))

        # Kiểm tra ACID: Không một bản ghi nào được tạo
        assert db_session.scalar(select(func.count(Apartment.id))) == 0
        assert db_session.scalar(select(func.count(Household.id))) == 0
        assert db_session.scalar(select(func.count(Resident.id))) == 0
        assert db_session.scalar(select(func.count(User.id)).where(User.id > 4, User.id != 99)) == 0
        assert db_session.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == "IMPORT_EXCEL")) == 0

    def test_rollback_invalid_floor(self, client, auth_headers_admin, db_session):
        """Số tầng là số thập phân (5.5) hoặc <= 0 -> Rollback."""
        rows = [
            ["A101", 5.5, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("invalid_floor.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "floor" for d in data.get("details", []))
        assert db_session.scalar(select(func.count(Apartment.id))) == 0

    def test_rollback_duplicate_cccd_in_file(self, client, auth_headers_admin, db_session):
        """Hai dòng trong file có cùng số CCCD -> Rollback."""
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"],
            ["A102", 1, 80.0, "H102", "0902222222", "h2@test.com", "Trần Văn B", "1992-02-02", "NAM", "001090001111", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("dup_cccd.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "cccd" and "trùng lặp" in d["message"].lower() for d in data.get("details", []))
        assert db_session.scalar(select(func.count(Resident.id))) == 0

    def test_rollback_duplicate_cccd_in_database(self, client, auth_headers_admin, db_session):
        """Số CCCD trong file đã tồn tại trong CSDL -> Rollback."""
        # Tạo sẵn 1 resident trong DB
        h = Household(household_code="EXISTING_H", status="ACTIVE")
        db_session.add(h)
        db_session.flush()
        existing_res = Resident(
            household_id=h.id,
            full_name="Người Đã Tồn Tại",
            date_of_birth=date(1980, 1, 1),
            gender="NAM",
            cccd="001080009999",
            residence_status="THUONG_TRU",
            status_effective_date=date.today(),
            is_head=True,
            is_deleted=False,
        )
        db_session.add(existing_res)
        db_session.commit()

        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001080009999", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("db_dup_cccd.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "cccd" and "đã tồn tại trên hệ thống" in d["message"].lower() for d in data.get("details", []))
        # Không có căn hộ hoặc hộ mới nào được tạo
        assert db_session.scalar(select(func.count(Apartment.id))) == 0

    def test_rollback_duplicate_household_code_in_database(self, client, auth_headers_admin, db_session):
        """Mã hộ gia đình trong file đã tồn tại trong CSDL -> Rollback."""
        existing_hh = Household(household_code="H101", status="ACTIVE")
        db_session.add(existing_hh)
        db_session.commit()

        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("dup_hcode.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "household_code" and "đã tồn tại trên hệ thống" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_apartment_already_occupied(self, client, auth_headers_admin, db_session):
        """Căn hộ đã có hộ đang cư trú (ApartmentOccupancy end_date is None) -> Rollback."""
        apt = Apartment(code="A101", floor=1, area_m2=70.0, status="ACTIVE")
        db_session.add(apt)
        db_session.flush()
        hh = Household(household_code="H_OLD", status="ACTIVE")
        db_session.add(hh)
        db_session.flush()
        occ = ApartmentOccupancy(apartment_id=apt.id, household_id=hh.id, start_date=date(2025, 1, 1), end_date=None)
        db_session.add(occ)
        db_session.commit()

        rows = [
            ["A101", 1, 70.0, "H_NEW", "0901111111", "h@new.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("apt_occupied.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "apartment_code" and "đang có người cư trú" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_household_without_head(self, client, auth_headers_admin, db_session):
        """Hộ không có ai là chủ hộ -> Rollback."""
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "THÀNH VIÊN", "KHÔNG"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("no_head.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "is_head" and "đúng 1 chủ hộ" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_household_with_multiple_heads(self, client, auth_headers_admin, db_session):
        """Hộ có nhiều hơn 1 chủ hộ -> Rollback."""
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "CÓ"],
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Trần Thị B", "1992-02-02", "NU", "001092002222", "CHỦ HỘ", "CÓ"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("multi_heads.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "is_head" and "đúng 1 chủ hộ" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_apartment_assigned_to_two_households_in_file(self, client, auth_headers_admin, db_session):
        """1 căn hộ bị gán cho 2 hộ gia đình khác nhau trong cùng 1 file -> Rollback."""
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"],
            ["A101", 1, 70.0, "H102", "0902222222", "h2@test.com", "Trần Văn B", "1992-02-02", "NAM", "001092002222", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("same_apt_multi_hh.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any("không thể gán thêm cho hộ" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_inconsistent_apartment_info_in_file(self, client, auth_headers_admin, db_session):
        """Cùng 1 căn hộ nhưng diện tích hoặc tầng không đồng nhất giữa các dòng -> Rollback."""
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"],
            ["A101", 2, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn B", "2018-05-05", "NAM", None, "CON", "0"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("inconsistent_apt.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any("không đồng nhất" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_resident_above_14_without_cccd(self, client, auth_headers_admin, db_session):
        """Nhân khẩu từ 14 tuổi trở lên bắt buộc phải có số CCCD/CMND -> Rollback."""
        dob_15_years_ago = (date.today() - timedelta(days=15 * 365 + 30)).strftime("%Y-%m-%d")
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1980-01-01", "NAM", "001080001111", "CHỦ HỘ", "1"],
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn Con", dob_15_years_ago, "NAM", None, "CON", "0"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("no_cccd_14plus.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any("từ 14 tuổi trở lên bắt buộc" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_resident_dob_in_future(self, client, auth_headers_admin, db_session):
        """Ngày sinh ở tương lai -> Rollback."""
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", tomorrow, "NAM", "001090001111", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("future_dob.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any("tương lai" in d["message"].lower() for d in data.get("details", []))

    def test_rollback_invalid_gender(self, client, auth_headers_admin, db_session):
        """Giới tính không hợp lệ -> Rollback."""
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "h1@test.com", "Nguyễn Văn A", "1990-01-01", "INVALID_GENDER", "001090001111", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("invalid_gender.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "gender" for d in data.get("details", []))

    def test_rollback_invalid_email_format(self, client, auth_headers_admin, db_session):
        """Email liên hệ sai định dạng -> Rollback."""
        rows = [
            ["A101", 1, 70.0, "H101", "0901111111", "not-an-email", "Nguyễn Văn A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"],
        ]
        excel_bytes = create_excel_bytes(rows)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("invalid_email.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )

        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "IMPORT_FAILED"
        assert any(d["field"] == "contact_email" for d in data.get("details", []))


# ==============================================================================
# 3. FILE FORMAT & INTEGRITY VALIDATION TESTS
# ==============================================================================

class TestImportExcelValidation:
    """Kiểm tra tính hợp lệ của định dạng tệp, kích thước và cấu trúc bảng tính."""

    def test_invalid_extension_rejected_400(self, client, auth_headers_admin):
        """Tải file không phải .xlsx (vd: .csv, .txt) -> HTTP 400 VALIDATION_ERROR."""
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("data.csv", b"col1,col2\nval1,val2", "text/csv")},
            headers=auth_headers_admin,
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert ".xlsx" in data["message"].lower()

    def test_empty_file_rejected_400(self, client, auth_headers_admin):
        """Tải file 0 bytes -> HTTP 400 VALIDATION_ERROR."""
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("empty.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "rỗng" in data["message"].lower()

    def test_oversized_file_rejected_400(self, client, auth_headers_admin):
        """Tải file vượt quá giới hạn 10MB -> HTTP 400 VALIDATION_ERROR."""
        oversized_bytes = b"x" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("large.xlsx", oversized_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "10mb" in data["message"].lower()

    def test_corrupted_file_rejected_400(self, client, auth_headers_admin):
        """Tải file có đuôi .xlsx nhưng nội dung không phải cấu trúc zip/excel -> HTTP 400."""
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("corrupt.xlsx", b"not-a-valid-excel-file", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "bị hỏng" in data["message"].lower() or "không phải là file excel" in data["message"].lower()

    def test_missing_required_headers_rejected_400(self, client, auth_headers_admin):
        """File thiếu các cột bắt buộc (vd thiếu cột 'Mã căn hộ') -> HTTP 400."""
        headers = ["Tầng", "Diện tích", "Họ tên"]
        excel_bytes = create_excel_bytes([["1", "70", "Nguyễn Văn A"]], headers=headers)

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("missing_cols.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "thiếu các cột bắt buộc" in data["message"].lower()

    def test_file_with_no_data_rows_rejected_400(self, client, auth_headers_admin):
        """File chỉ có dòng tiêu đề, không có bất kỳ dòng dữ liệu nào -> HTTP 400."""
        excel_bytes = create_excel_bytes([])

        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("no_data.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_admin,
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "không có dòng dữ liệu nào" in data["message"].lower()


# ==============================================================================
# 4. RBAC (ROLE-BASED ACCESS CONTROL) TESTS
# ==============================================================================

class TestImportExcelRBAC:
    """Kiểm tra phân quyền nghiêm ngặt: Chỉ duy nhất ADMIN được phép thực thi import Excel."""

    def test_unauthenticated_rejected_401(self, client):
        """Chưa đăng nhập (thiếu Authorization header) -> HTTP 401 UNAUTHENTICATED."""
        excel_bytes = create_excel_bytes([["A101", 1, 70.0, "H101", "0901", "a@a.com", "A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"]])
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("test.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 401

    def test_accountant_forbidden_403(self, client, auth_headers_accountant):
        """Kế toán (ACCOUNTANT) không có quyền -> HTTP 403 FORBIDDEN."""
        excel_bytes = create_excel_bytes([["A101", 1, 70.0, "H101", "0901", "a@a.com", "A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"]])
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("test.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_accountant,
        )
        assert response.status_code == 403

    def test_treasurer_forbidden_403(self, client, auth_headers_treasurer):
        """Thủ quỹ (TREASURER) không có quyền -> HTTP 403 FORBIDDEN."""
        excel_bytes = create_excel_bytes([["A101", 1, 70.0, "H101", "0901", "a@a.com", "A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"]])
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("test.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_treasurer,
        )
        assert response.status_code == 403

    def test_resident_forbidden_403(self, client, auth_headers_resident):
        """Cư dân (RESIDENT) không có quyền -> HTTP 403 FORBIDDEN."""
        excel_bytes = create_excel_bytes([["A101", 1, 70.0, "H101", "0901", "a@a.com", "A", "1990-01-01", "NAM", "001090001111", "CHỦ HỘ", "1"]])
        response = client.post(
            "/api/v1/import/excel",
            files={"file": ("test.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers_resident,
        )
        assert response.status_code == 403
