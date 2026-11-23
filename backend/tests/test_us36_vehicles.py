"""
Test Suite for User Story US-36: Quản lý phương tiện gửi tại chung cư (Vehicles).

Standards:
- docs/openapi.yaml:
  - GET /vehicles (listVehicles, US-36)
  - POST /vehicles (createVehicle, US-36)
  - PATCH /vehicles/{id} (updateVehicle, US-36)
  - POST /vehicles/{id}/unregister (unregisterVehicle, US-36)
- docs/API_CONTRACT.md (Section 3.13)
- docs/PRODUCT_BACKLOG.md (AC-36.1: Nhập biển số xe, loại xe, chọn hộ; chặn trùng biển số active; hủy đăng ký)
"""

# [SỬA] Xóa import thừa `timedelta`
from datetime import date
import pytest
from sqlalchemy import select

from app.core.security import create_access_token, get_password_hash
from app.models.property import Household
from app.models.user import AuditLog, User
from app.models.vehicle import Vehicle

# [THÊM] Danh sách mã hộ gia đình riêng của suite US-36 để dọn dẹp an toàn khi chạy hồi quy
US36_HOUSEHOLD_CODES = ("H_US36_01", "H_US36_02", "H_INACTIVE_36")


# ==============================================================================
# Helper Functions & Fixtures for Authentication & Roles
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
def admin_headers():
    return make_headers(role="ADMIN", sub="1", username="admin_test")


@pytest.fixture
def accountant_headers():
    return make_headers(role="ACCOUNTANT", sub="2", username="accountant_test")


@pytest.fixture
def treasurer_headers(db_session):
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us36"))
    if not user:
        user = User(
            id=536,
            username="treasurer_test_us36",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US36",
            email="treasurer_36@bluemoon.local",
            role_id=3,
            is_active=True,
            must_change_password=False,
        )
        db_session.add(user)
        db_session.commit()
    return make_headers(role="TREASURER", sub=str(user.id), username=user.username)


@pytest.fixture
def resident_headers():
    return make_headers(role="RESIDENT", sub="3", username="resident_101")


@pytest.fixture(autouse=True)
def clean_vehicle_tables(db_session):
    """Đảm bảo các bảng liên quan sạch sẽ trước và sau mỗi test."""
    def _cleanup():
        # [SỬA] Chỉ xóa AuditLog của VEHICLE và Household thuộc phạm vi US-36
        # để tránh lỗi khóa ngoại (IntegrityError) với dữ liệu tồn dư của các suite test khác
        db_session.query(AuditLog).filter(AuditLog.entity_type == "VEHICLE").delete(
            synchronize_session=False
        )
        db_session.query(Vehicle).delete(synchronize_session=False)
        db_session.query(Household).filter(
            Household.household_code.in_(US36_HOUSEHOLD_CODES)
        ).delete(synchronize_session=False)
        db_session.commit()

    _cleanup()
    yield
    _cleanup()


# ==============================================================================
# Data Fixtures
# ==============================================================================

@pytest.fixture
def sample_household(db_session):
    """Tạo 1 hộ gia đình đang hoạt động."""
    # [SỬA] Bỏ hardcode id=1 để tránh đụng Primary Key với các test khác trong bộ hồi quy
    hh = Household(
        household_code="H_US36_01",
        status="ACTIVE",
        contact_phone="0911223344",
        note="Hộ gia đình mẫu test xe",
    )
    db_session.add(hh)
    db_session.commit()
    db_session.refresh(hh)
    return hh


@pytest.fixture
def sample_household_2(db_session):
    """Tạo hộ gia đình thứ hai."""
    # [SỬA] Bỏ hardcode id=2
    hh = Household(
        household_code="H_US36_02",
        status="ACTIVE",
        contact_phone="0988776655",
        note="Hộ gia đình thứ hai",
    )
    db_session.add(hh)
    db_session.commit()
    db_session.refresh(hh)
    return hh


@pytest.fixture
def inactive_household(db_session):
    """Tạo hộ gia đình đã ngừng quản lý."""
    # [SỬA] Bỏ hardcode id=3
    hh = Household(
        household_code="H_INACTIVE_36",
        status="INACTIVE",
        contact_phone="0900000000",
        note="Hộ đã dọn đi",
    )
    db_session.add(hh)
    db_session.commit()
    db_session.refresh(hh)
    return hh


# ==============================================================================
# 1. Test Suite: Phân quyền RBAC (US-36)
# ==============================================================================

class TestVehiclesRBAC:
    """Kiểm tra phân quyền nghiêm ngặt theo docs/openapi.yaml và docs/API_CONTRACT.md."""

    def test_list_vehicles_unauthenticated_fails_401(self, client):
        res = client.get("/api/v1/vehicles")
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_list_vehicles_forbidden_treasurer_fails_403(self, client, treasurer_headers):
        res = client.get("/api/v1/vehicles", headers=treasurer_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_list_vehicles_forbidden_resident_fails_403(self, client, resident_headers):
        res = client.get("/api/v1/vehicles", headers=resident_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_list_vehicles_allowed_admin_200(self, client, admin_headers):
        res = client.get("/api/v1/vehicles", headers=admin_headers)
        assert res.status_code == 200

    def test_list_vehicles_allowed_accountant_200(self, client, accountant_headers):
        res = client.get("/api/v1/vehicles", headers=accountant_headers)
        assert res.status_code == 200

    # [THÊM] Smoke test đảm bảo prefix legacy /vehicles đã được mount trong main.py
    def test_legacy_prefix_vehicles_route_works_200(self, client, admin_headers):
        res = client.get("/vehicles", headers=admin_headers)
        assert res.status_code == 200
        assert "items" in res.json()

    def test_create_vehicle_unauthenticated_fails_401(self, client):
        res = client.post("/api/v1/vehicles", json={})
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_create_vehicle_forbidden_accountant_fails_403(
        self, client, accountant_headers, sample_household
    ):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "MOTORBIKE",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=accountant_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_create_vehicle_forbidden_treasurer_fails_403(
        self, client, treasurer_headers, sample_household
    ):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "MOTORBIKE",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=treasurer_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_create_vehicle_forbidden_resident_fails_403(
        self, client, resident_headers, sample_household
    ):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "MOTORBIKE",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=resident_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_create_vehicle_allowed_admin_201(self, client, admin_headers, sample_household):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "CAR",
            "brand": "Toyota",
            "color": "Trắng",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 201

    def test_update_vehicle_unauthenticated_fails_401(self, client):
        res = client.patch("/api/v1/vehicles/1", json={"color": "Đỏ"})
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_update_vehicle_forbidden_accountant_fails_403(self, client, accountant_headers):
        res = client.patch("/api/v1/vehicles/1", json={"color": "Đỏ"}, headers=accountant_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"

    def test_unregister_vehicle_unauthenticated_fails_401(self, client):
        res = client.post("/api/v1/vehicles/1/unregister")
        assert res.status_code == 401
        assert res.json()["code"] == "UNAUTHENTICATED"

    def test_unregister_vehicle_forbidden_accountant_fails_403(self, client, accountant_headers):
        res = client.post("/api/v1/vehicles/1/unregister", headers=accountant_headers)
        assert res.status_code == 403
        assert res.json()["code"] == "FORBIDDEN"


# ==============================================================================
# 2. Test Suite: Tra cứu và phân trang phương tiện (US-36)
# ==============================================================================

class TestListVehicles:
    """Kiểm tra danh sách, bộ lọc và phân trang VehiclePage."""

    def test_list_empty_when_no_vehicles(self, client, admin_headers):
        res = client.get("/api/v1/vehicles", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_pagination(self, client, admin_headers, sample_household, db_session):
        for i in range(1, 6):
            v = Vehicle(
                household_id=sample_household.id,
                plate_number=f"29A-{i:03d}.99",
                vehicle_type="MOTORBIKE",
                brand="Honda",
                color="Đen",
                status="ACTIVE",
                registered_date=date(2026, 1, i),
            )
            db_session.add(v)
        db_session.commit()

        # Trang 1 lấy 2 xe
        res1 = client.get("/api/v1/vehicles?page=1&page_size=2", headers=admin_headers)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["total"] == 5
        assert len(data1["items"]) == 2
        assert data1["page"] == 1
        assert data1["page_size"] == 2

        # Trang 3 lấy xe thứ 5
        res3 = client.get("/api/v1/vehicles?page=3&page_size=2", headers=admin_headers)
        assert res3.status_code == 200
        data3 = res3.json()
        assert len(data3["items"]) == 1

    def test_filter_by_household_id(
        self, client, admin_headers, sample_household, sample_household_2, db_session
    ):
        v1 = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-111.11",
            vehicle_type="CAR",
            status="ACTIVE",
        )
        v2 = Vehicle(
            household_id=sample_household_2.id,
            plate_number="29A-222.22",
            vehicle_type="CAR",
            status="ACTIVE",
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        res = client.get(f"/api/v1/vehicles?household_id={sample_household.id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["household_id"] == sample_household.id
        assert data["items"][0]["plate_number"] == "29A-111.11"

    def test_filter_by_status(self, client, admin_headers, sample_household, db_session):
        v_act = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-ACTIVE",
            vehicle_type="MOTORBIKE",
            status="ACTIVE",
        )
        v_inact = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-INACTIVE",
            vehicle_type="MOTORBIKE",
            status="INACTIVE",
            unregistered_date=date(2026, 2, 1),
        )
        db_session.add_all([v_act, v_inact])
        db_session.commit()

        # Lọc ACTIVE
        res_a = client.get("/api/v1/vehicles?status=ACTIVE", headers=admin_headers)
        assert res_a.status_code == 200
        assert res_a.json()["total"] == 1
        assert res_a.json()["items"][0]["status"] == "ACTIVE"

        # Lọc INACTIVE
        res_i = client.get("/api/v1/vehicles?status=INACTIVE", headers=admin_headers)
        assert res_i.status_code == 200
        assert res_i.json()["total"] == 1
        assert res_i.json()["items"][0]["status"] == "INACTIVE"

    def test_filter_by_vehicle_type(self, client, admin_headers, sample_household, db_session):
        v_car = Vehicle(
            household_id=sample_household.id,
            plate_number="30E-CAR",
            vehicle_type="CAR",
            status="ACTIVE",
        )
        v_bike = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-BIKE",
            vehicle_type="BICYCLE",
            status="ACTIVE",
        )
        db_session.add_all([v_car, v_bike])
        db_session.commit()

        res = client.get("/api/v1/vehicles?vehicle_type=CAR", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["vehicle_type"] == "CAR"

    def test_filter_by_plate_number_search(self, client, admin_headers, sample_household, db_session):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-999.88",
            vehicle_type="MOTORBIKE",
            status="ACTIVE",
        )
        db_session.add(v)
        db_session.commit()

        # [SỬA] Truyền chuỗi có chữ thường và khoảng trắng để thực sự kiểm tra logic chuẩn hóa khi search
        res = client.get(
            "/api/v1/vehicles",
            params={"plate_number": "  29a - 999.88  "},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["plate_number"] == "29A-999.88"

    # [THÊM] Kiểm tra chống SQL wildcard injection ('%' và '_') khi tìm theo biển số
    def test_filter_plate_number_escapes_sql_wildcards(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-777.66",
            vehicle_type="CAR",
            status="ACTIVE",
        )
        db_session.add(v)
        db_session.commit()

        res_percent = client.get("/api/v1/vehicles", params={"plate_number": "%"}, headers=admin_headers)
        assert res_percent.status_code == 200
        assert res_percent.json()["total"] == 0

        res_underscore = client.get("/api/v1/vehicles", params={"plate_number": "_"}, headers=admin_headers)
        assert res_underscore.status_code == 200
        assert res_underscore.json()["total"] == 0

    # [THÊM] Kiểm tra lọc kết hợp nhiều điều kiện (tổ hợp phục vụ tính phí gửi xe ở US-17)
    def test_filter_combined_household_status_and_type(
        self, client, admin_headers, sample_household, sample_household_2, db_session
    ):
        vehicles = [
            Vehicle(household_id=sample_household.id, plate_number="29A-001", vehicle_type="CAR", status="ACTIVE"),
            Vehicle(household_id=sample_household.id, plate_number="29A-002", vehicle_type="CAR", status="INACTIVE"),
            Vehicle(household_id=sample_household.id, plate_number="29A-003", vehicle_type="MOTORBIKE", status="ACTIVE"),
            Vehicle(household_id=sample_household_2.id, plate_number="29A-004", vehicle_type="CAR", status="ACTIVE"),
        ]
        db_session.add_all(vehicles)
        db_session.commit()

        res = client.get(
            "/api/v1/vehicles",
            params={
                "household_id": sample_household.id,
                "status": "ACTIVE",
                "vehicle_type": "CAR",
            },
            headers=admin_headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["plate_number"] == "29A-001"

    def test_sorted_by_id_desc(self, client, admin_headers, sample_household, db_session):
        v1 = Vehicle(id=10, household_id=sample_household.id, plate_number="29A-10", vehicle_type="CAR")
        v2 = Vehicle(id=20, household_id=sample_household.id, plate_number="29A-20", vehicle_type="CAR")
        db_session.add_all([v1, v2])
        db_session.commit()

        res = client.get("/api/v1/vehicles", headers=admin_headers)
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 2
        assert items[0]["id"] == 20
        assert items[1]["id"] == 10


# ==============================================================================
# 3. Test Suite: Đăng ký phương tiện thành công (US-36)
# ==============================================================================

class TestCreateVehicleSuccess:
    """Kiểm tra đăng ký xe các loại và Audit Log."""

    def test_create_motorbike_success_201(self, client, admin_headers, sample_household):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "29B1-123.45",
            "vehicle_type": "MOTORBIKE",
            "brand": "Honda SH 150i",
            "color": "Trắng",
            "registered_date": "2026-01-15",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["household_id"] == sample_household.id
        assert data["plate_number"] == "29B1-123.45"
        assert data["vehicle_type"] == "MOTORBIKE"
        assert data["brand"] == "Honda SH 150i"
        assert data["color"] == "Trắng"
        assert data["registered_date"] == "2026-01-15"
        assert data["status"] == "ACTIVE"
        assert data["unregistered_date"] is None

    def test_create_car_success_201(self, client, admin_headers, sample_household):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "30H-888.88",
            "vehicle_type": "CAR",
            "brand": "Mercedes GLC 300",
            "color": "Đen",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["plate_number"] == "30H-888.88"
        assert data["vehicle_type"] == "CAR"
        assert data["registered_date"] == str(date.today())

    def test_create_bicycle_success_201(self, client, admin_headers, sample_household):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "XE-DAP-001",
            "vehicle_type": "BICYCLE",
            "brand": "Giant Escape 3",
            "color": "Xanh dương",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 201
        assert res.json()["vehicle_type"] == "BICYCLE"

    def test_create_vehicle_normalizes_plate_number(self, client, admin_headers, sample_household):
        # Biển số chứa khoảng trắng và chữ thường
        payload = {
            "household_id": sample_household.id,
            "plate_number": "  29a - 999.99  ",
            "vehicle_type": "MOTORBIKE",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 201
        assert res.json()["plate_number"] == "29A-999.99"

    def test_create_vehicle_records_audit_log(
        self, client, admin_headers, sample_household, db_session
    ):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "29C-555.55",
            "vehicle_type": "CAR",
            "brand": "VinFast VF8",
            "color": "Đỏ",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 201
        created_id = res.json()["id"]

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "VEHICLE",
                AuditLog.action == "CREATE_VEHICLE",
                AuditLog.entity_id == str(created_id),
            )
        )
        assert audit is not None
        assert audit.user_id == 1
        assert audit.new_value["plate_number"] == "29C-555.55"
        assert audit.new_value["vehicle_type"] == "CAR"
        assert "Đăng ký phương tiện" in audit.reason


# ==============================================================================
# 4. Test Suite: Ràng buộc Validation & Nghiệp vụ (US-36)
# ==============================================================================

class TestCreateVehicleValidationAndErrors:
    """Kiểm tra xử lý lỗi đầu vào và xung đột trùng biển số."""

    def test_create_household_not_found_fails_404(self, client, admin_headers):
        payload = {
            "household_id": 999999,
            "plate_number": "29A-123.45",
            "vehicle_type": "MOTORBIKE",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_create_household_inactive_fails_400(
        self, client, admin_headers, inactive_household
    ):
        payload = {
            "household_id": inactive_household.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "MOTORBIKE",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"
        assert "đã ngừng hoạt động" in res.json()["message"]

    def test_create_empty_plate_number_rejected_400(self, client, admin_headers, sample_household):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "    ",
            "vehicle_type": "MOTORBIKE",
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_invalid_vehicle_type_rejected_400(self, client, admin_headers, sample_household):
        payload = {
            "household_id": sample_household.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "TRUCK",  # Không nằm trong MOTORBIKE, CAR, BICYCLE
        }
        res = client.post("/api/v1/vehicles", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_create_duplicate_active_plate_conflict_409(
        self, client, admin_headers, sample_household, sample_household_2
    ):
        # Đăng ký xe 1
        payload1 = {
            "household_id": sample_household.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "CAR",
        }
        res1 = client.post("/api/v1/vehicles", json=payload1, headers=admin_headers)
        assert res1.status_code == 201

        # Đăng ký xe 2 trùng biển số (kể cả khác hộ gia đình)
        payload2 = {
            "household_id": sample_household_2.id,
            "plate_number": "29A-123.45",
            "vehicle_type": "CAR",
        }
        res2 = client.post("/api/v1/vehicles", json=payload2, headers=admin_headers)
        assert res2.status_code == 409
        assert res2.json()["code"] == "DUPLICATE_PLATE"
        assert "đã được đăng ký" in res2.json()["message"]

    def test_create_duplicate_active_plate_case_and_spaces_insensitive_409(
        self, client, admin_headers, sample_household, sample_household_2
    ):
        # Đăng ký xe 1 với biển "29A-888.88"
        payload1 = {
            "household_id": sample_household.id,
            "plate_number": "29A-888.88",
            "vehicle_type": "CAR",
        }
        res1 = client.post("/api/v1/vehicles", json=payload1, headers=admin_headers)
        assert res1.status_code == 201

        # Đăng ký xe 2 với biển "  29a - 888.88  "
        payload2 = {
            "household_id": sample_household_2.id,
            "plate_number": "  29a - 888.88  ",
            "vehicle_type": "CAR",
        }
        res2 = client.post("/api/v1/vehicles", json=payload2, headers=admin_headers)
        assert res2.status_code == 409
        assert res2.json()["code"] == "DUPLICATE_PLATE"

    def test_create_same_plate_allowed_when_previous_vehicle_is_inactive_201(
        self, client, admin_headers, sample_household, sample_household_2
    ):
        # 1. Đăng ký xe
        payload1 = {
            "household_id": sample_household.id,
            "plate_number": "29A-999.00",
            "vehicle_type": "MOTORBIKE",
        }
        res1 = client.post("/api/v1/vehicles", json=payload1, headers=admin_headers)
        assert res1.status_code == 201
        v_id = res1.json()["id"]

        # 2. Hủy đăng ký (chuyển sang INACTIVE)
        res_un = client.post(f"/api/v1/vehicles/{v_id}/unregister", headers=admin_headers)
        assert res_un.status_code == 200

        # 3. Đăng ký lại biển số đó cho hộ khác -> Thành công vì xe cũ đã INACTIVE
        payload2 = {
            "household_id": sample_household_2.id,
            "plate_number": "29A-999.00",
            "vehicle_type": "MOTORBIKE",
        }
        res2 = client.post("/api/v1/vehicles", json=payload2, headers=admin_headers)
        assert res2.status_code == 201
        assert res2.json()["status"] == "ACTIVE"


# ==============================================================================
# 5. Test Suite: Cập nhật thông tin phương tiện (US-36)
# ==============================================================================

class TestUpdateVehicle:
    """Kiểm tra cập nhật thông tin phương tiện (PATCH /vehicles/{id})."""

    def test_update_vehicle_not_found_fails_404(self, client, admin_headers):
        res = client.patch("/api/v1/vehicles/999999", json={"color": "Đỏ"}, headers=admin_headers)
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_update_brand_and_color_success_200(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-UPDATE-1",
            vehicle_type="CAR",
            brand="Mazda 3",
            color="Đỏ",
            status="ACTIVE",
        )
        db_session.add(v)
        db_session.commit()

        payload = {"brand": "Mazda 6", "color": "Xám"}
        res = client.patch(f"/api/v1/vehicles/{v.id}", json=payload, headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["brand"] == "Mazda 6"
        assert data["color"] == "Xám"
        assert data["plate_number"] == "29A-UPDATE-1"

    def test_update_plate_number_success_200(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-OLD-PLATE",
            vehicle_type="MOTORBIKE",
            status="ACTIVE",
        )
        db_session.add(v)
        db_session.commit()

        payload = {"plate_number": "29A-NEW-PLATE"}
        res = client.patch(f"/api/v1/vehicles/{v.id}", json=payload, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["plate_number"] == "29A-NEW-PLATE"

    # [THÊM] Kiểm tra chuẩn hóa biển số và xóa trường optional (brand: null) khi PATCH
    def test_update_normalizes_plate_and_clears_optional_brand_200(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-OLD-01",
            vehicle_type="CAR",
            brand="Toyota",
            color="Đen",
            status="ACTIVE",
        )
        db_session.add(v)
        db_session.commit()

        payload = {"plate_number": "  30h - 111.22  ", "brand": None}
        res = client.patch(f"/api/v1/vehicles/{v.id}", json=payload, headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["plate_number"] == "30H-111.22"
        assert data["brand"] is None
        assert data["color"] == "Đen"

    def test_update_same_plate_number_does_not_conflict_with_self_200(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-SELF-CHECK",
            vehicle_type="CAR",
            color="Trắng",
            status="ACTIVE",
        )
        db_session.add(v)
        db_session.commit()

        # Gửi lại đúng biển số cũ kèm đổi màu
        payload = {"plate_number": "29A-SELF-CHECK", "color": "Đen"}
        res = client.patch(f"/api/v1/vehicles/{v.id}", json=payload, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["color"] == "Đen"

    def test_update_plate_number_conflict_with_another_active_vehicle_409(
        self, client, admin_headers, sample_household, db_session
    ):
        v1 = Vehicle(household_id=sample_household.id, plate_number="29A-EXISTS", vehicle_type="CAR", status="ACTIVE")
        v2 = Vehicle(household_id=sample_household.id, plate_number="29A-TARGET", vehicle_type="CAR", status="ACTIVE")
        db_session.add_all([v1, v2])
        db_session.commit()

        # Cố tình đổi v2 thành biển số của v1
        payload = {"plate_number": "29A-EXISTS"}
        res = client.patch(f"/api/v1/vehicles/{v2.id}", json=payload, headers=admin_headers)
        assert res.status_code == 409
        assert res.json()["code"] == "DUPLICATE_PLATE"

    def test_update_explicit_null_plate_number_rejected_400(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(household_id=sample_household.id, plate_number="29A-VALID", vehicle_type="CAR")
        db_session.add(v)
        db_session.commit()

        res = client.patch(f"/api/v1/vehicles/{v.id}", json={"plate_number": None}, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_update_explicit_null_vehicle_type_rejected_400(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(household_id=sample_household.id, plate_number="29A-VALID", vehicle_type="CAR")
        db_session.add(v)
        db_session.commit()

        res = client.patch(f"/api/v1/vehicles/{v.id}", json={"vehicle_type": None}, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"

    def test_update_records_audit_log(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-LOG-ME",
            vehicle_type="CAR",
            color="Bạc",
            status="ACTIVE",
        )
        db_session.add(v)
        db_session.commit()

        res = client.patch(f"/api/v1/vehicles/{v.id}", json={"color": "Vàng cát"}, headers=admin_headers)
        assert res.status_code == 200

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "VEHICLE",
                AuditLog.action == "UPDATE_VEHICLE",
                AuditLog.entity_id == str(v.id),
            )
        )
        assert audit is not None
        assert audit.user_id == 1
        assert audit.old_value["color"] == "Bạc"
        assert audit.new_value["color"] == "Vàng cát"


# ==============================================================================
# 6. Test Suite: Hủy đăng ký phương tiện (US-36)
# ==============================================================================

class TestUnregisterVehicle:
    """Kiểm tra hủy đăng ký phương tiện (POST /vehicles/{id}/unregister)."""

    def test_unregister_vehicle_not_found_fails_404(self, client, admin_headers):
        res = client.post("/api/v1/vehicles/999999/unregister", headers=admin_headers)
        assert res.status_code == 404
        assert res.json()["code"] == "NOT_FOUND"

    def test_unregister_active_vehicle_success_200(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-UNREG-1",
            vehicle_type="MOTORBIKE",
            status="ACTIVE",
            registered_date=date(2026, 1, 1),
        )
        db_session.add(v)
        db_session.commit()

        res = client.post(f"/api/v1/vehicles/{v.id}/unregister", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == v.id
        assert data["status"] == "INACTIVE"
        assert data["unregistered_date"] == str(date.today())

        # Kiểm tra database đã cập nhật
        db_session.expire_all()
        reloaded = db_session.get(Vehicle, v.id)
        assert reloaded.status == "INACTIVE"
        assert reloaded.unregistered_date == date.today()

    def test_unregister_with_explicit_date_success_200(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-UNREG-DATE",
            vehicle_type="CAR",
            status="ACTIVE",
            registered_date=date(2026, 1, 1),
        )
        db_session.add(v)
        db_session.commit()

        payload = {"unregistered_date": "2026-06-30"}
        res = client.post(f"/api/v1/vehicles/{v.id}/unregister", json=payload, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["unregistered_date"] == "2026-06-30"

    def test_unregister_with_empty_body_success_200(
        self, client, admin_headers, sample_household, db_session
    ):
        """Gọi POST /unregister không truyền request body (hoặc {}) vẫn thành công."""
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-EMPTY-BODY",
            vehicle_type="CAR",
            status="ACTIVE",
            registered_date=date(2026, 1, 1),
        )
        db_session.add(v)
        db_session.commit()

        res = client.post(f"/api/v1/vehicles/{v.id}/unregister", json={}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "INACTIVE"

    def test_unregister_date_before_registered_date_fails_400(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-DATE-ORDER",
            vehicle_type="CAR",
            status="ACTIVE",
            registered_date=date(2026, 5, 1),
        )
        db_session.add(v)
        db_session.commit()

        payload = {"unregistered_date": "2026-04-30"}  # Trước ngày đăng ký
        res = client.post(f"/api/v1/vehicles/{v.id}/unregister", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert res.json()["code"] == "VALIDATION_ERROR"
        assert "không được nhỏ hơn ngày đăng ký" in res.json()["message"]

    def test_unregister_already_inactive_fails_409(
        self, client, admin_headers, sample_household, db_session
    ):
        """Mã lỗi 409 ALREADY_INACTIVE theo docs/openapi.yaml."""
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-INACTIVE-ALREADY",
            vehicle_type="MOTORBIKE",
            status="INACTIVE",
            registered_date=date(2026, 1, 1),
            unregistered_date=date(2026, 2, 1),
        )
        db_session.add(v)
        db_session.commit()

        res = client.post(f"/api/v1/vehicles/{v.id}/unregister", headers=admin_headers)
        assert res.status_code == 409
        assert res.json()["code"] == "ALREADY_INACTIVE"
        assert "đã ở trạng thái ngừng gửi" in res.json()["message"]

    def test_unregister_records_audit_log(
        self, client, admin_headers, sample_household, db_session
    ):
        v = Vehicle(
            household_id=sample_household.id,
            plate_number="29A-AUDIT-UNREG",
            vehicle_type="CAR",
            status="ACTIVE",
            registered_date=date(2026, 1, 1),
        )
        db_session.add(v)
        db_session.commit()

        res = client.post(f"/api/v1/vehicles/{v.id}/unregister", headers=admin_headers)
        assert res.status_code == 200

        audit = db_session.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "VEHICLE",
                AuditLog.action == "UNREGISTER_VEHICLE",
                AuditLog.entity_id == str(v.id),
            )
        )
        assert audit is not None
        assert audit.user_id == 1
        assert audit.old_value["status"] == "ACTIVE"
        assert audit.new_value["status"] == "INACTIVE"
        assert f"Hủy đăng ký phương tiện ID {v.id}" in audit.reason