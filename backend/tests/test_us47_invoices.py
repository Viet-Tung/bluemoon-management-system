"""
Test Suite for User Story US-47: In giấy báo nộp phí hàng loạt / Chi tiết giấy báo nộp phí (Invoices & Details).

Specification & Standards:
- docs/openapi.yaml:
  - GET /invoices (listInvoices, US-17, US-47)
  - GET /invoices/{id} (getInvoice, US-47)
- docs/API_CONTRACT.md (Sections 3.14.6, 3.14.7)
- docs/PRODUCT_BACKLOG.md (F-03.1, WBS 2.3.2, AC-47.1):
  - Kế toán kết xuất / in giấy báo nộp phí hàng loạt cho các hộ gia đình.
  - Chi tiết từng khoản thu (xe, m², điện, nước, an ninh), nợ cũ, số dư có và tổng số tiền cần thanh toán của từng hộ.
  - Tốc độ phản hồi <= 1 giây cho danh sách và chi tiết giấy báo.
"""

import time
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select, text

from app.core.security import create_access_token, get_password_hash
from app.models.billing import BillingPeriod, Invoice, InvoiceItem, UtilityReading
from app.models.fee import FeeExemption, FeeRate, FeeType
from app.models.property import Apartment, ApartmentOccupancy, Household
from app.models.user import AuditLog, User
from app.models.vehicle import Vehicle

US47_HOUSEHOLD_CODES = (
    "HH_US47_FULL",
    "HH_US47_AREA_ONLY",
    "HH_US47_PARKING_ONLY",
    "HH_US47_UTILITY_ONLY",
    "HH_US47_EXEMPTION",
    "HH_US47_DEBT",
    "HH_US47_PAID",
)
US47_FEE_CODES = (
    "FEE_US47_MGT",
    "FEE_US47_MOTO",
    "FEE_US47_CAR",
    "FEE_US47_ELEC",
    "FEE_US47_WATER",
    "FEE_US47_FIXED",
)
US47_APT_CODES = ("APT_US47_101", "APT_US47_102", "APT_US47_103")


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
    user = db_session.scalar(select(User).where(User.username == "treasurer_test_us47"))
    if not user:
        user = User(
            id=547,
            username="treasurer_test_us47",
            password_hash=get_password_hash("TreasurerPass123!"),
            full_name="Thủ Quỹ Test US47",
            email="treasurer_47@bluemoon.local",
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
def clean_us47_tables(db_session):
    """Dọn dẹp sạch sẽ dữ liệu của suite test US-47 trước và sau mỗi test."""
    def _cleanup():
        db_session.query(AuditLog).filter(
            AuditLog.entity_type.in_(("BILLING_PERIOD", "INVOICE", "UTILITY_READING"))
        ).delete(synchronize_session=False)

        # Xóa các hóa đơn, chỉ số và kỳ thu
        db_session.query(InvoiceItem).delete(synchronize_session=False)
        db_session.query(Invoice).delete(synchronize_session=False)
        db_session.query(UtilityReading).delete(synchronize_session=False)
        db_session.query(BillingPeriod).delete(synchronize_session=False)

        # Xóa miễn giảm, đơn giá và loại phí
        db_session.query(FeeExemption).delete(synchronize_session=False)
        db_session.query(FeeRate).delete(synchronize_session=False)
        db_session.query(FeeType).filter(FeeType.code.in_(US47_FEE_CODES)).delete(synchronize_session=False)

        # Xóa phương tiện, hợp đồng ở và căn hộ
        db_session.query(Vehicle).delete(synchronize_session=False)
        for tbl in ["apartment_occupancies", "resident_members", "residents", "households", "apartments"]:
            try:
                db_session.execute(text(f"DELETE FROM {tbl}"))
            except Exception:
                pass
        db_session.commit()

    _cleanup()
    yield
    _cleanup()


@pytest.fixture
def setup_us47_environment(client, accountant_headers, db_session):
    """
    Thiết lập môi trường chuẩn cho US-47:
    - 3 Căn hộ
    - 7 Hộ gia đình với các tình huống đa dạng
    - 6 Khoản thu & Đơn giá
    - Chạy tạo kỳ thu và tự động tính phí (US-17) để sinh dữ liệu giấy báo thực tế cho US-47 kiểm thử.
    """
    # 1. Căn hộ
    apt1 = Apartment(code="APT_US47_101", floor=1, area_m2=Decimal("85.50"), status="ACTIVE")
    apt2 = Apartment(code="APT_US47_102", floor=1, area_m2=Decimal("110.00"), status="ACTIVE")
    apt3 = Apartment(code="APT_US47_103", floor=2, area_m2=Decimal("70.00"), status="ACTIVE")
    db_session.add_all([apt1, apt2, apt3])
    db_session.flush()

    # 2. Hộ gia đình
    households = {
        code: Household(household_code=code, status="ACTIVE")
        for code in US47_HOUSEHOLD_CODES
    }
    db_session.add_all(households.values())
    db_session.flush()

    # 3. Gán căn hộ
    occ1 = ApartmentOccupancy(apartment_id=apt1.id, household_id=households["HH_US47_FULL"].id, start_date=date(2025, 1, 1))
    occ2 = ApartmentOccupancy(apartment_id=apt2.id, household_id=households["HH_US47_AREA_ONLY"].id, start_date=date(2025, 1, 1))
    occ3 = ApartmentOccupancy(apartment_id=apt3.id, household_id=households["HH_US47_EXEMPTION"].id, start_date=date(2025, 1, 1))
    db_session.add_all([occ1, occ2, occ3])
    db_session.flush()

    # 4. Khoản thu
    ft_mgt = FeeType(code="FEE_US47_MGT", name="Phí quản lý", fee_group="MANAGEMENT", calc_method="PER_M2", unit_label="m²", status="ACTIVE")
    ft_moto = FeeType(code="FEE_US47_MOTO", name="Phí gửi xe máy", fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="MOTORBIKE", unit_label="xe", status="ACTIVE")
    ft_car = FeeType(code="FEE_US47_CAR", name="Phí gửi ô tô", fee_group="PARKING", calc_method="PER_VEHICLE", vehicle_type="CAR", unit_label="xe", status="ACTIVE")
    ft_elec = FeeType(code="FEE_US47_ELEC", name="Tiền điện", fee_group="ELECTRICITY", calc_method="PER_INDEX", unit_label="kWh", status="ACTIVE")
    ft_water = FeeType(code="FEE_US47_WATER", name="Tiền nước", fee_group="WATER", calc_method="PER_INDEX", unit_label="m³", status="ACTIVE")
    ft_fixed = FeeType(code="FEE_US47_FIXED", name="Phí an ninh", fee_group="OTHER", calc_method="PER_HOUSEHOLD", unit_label="hộ", status="ACTIVE")
    db_session.add_all([ft_mgt, ft_moto, ft_car, ft_elec, ft_water, ft_fixed])
    db_session.flush()

    # 5. Biểu giá
    rates = [
        FeeRate(fee_type_id=ft_mgt.id, unit_price=Decimal("8000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_moto.id, unit_price=Decimal("70000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_car.id, unit_price=Decimal("1200000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_elec.id, unit_price=Decimal("2500.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_water.id, unit_price=Decimal("15000.00"), effective_from=date(2026, 1, 1)),
        FeeRate(fee_type_id=ft_fixed.id, unit_price=Decimal("50000.00"), effective_from=date(2026, 1, 1)),
    ]
    db_session.add_all(rates)
    db_session.flush()

    # 6. Phương tiện
    # HH_US47_FULL: 2 xe máy, 1 ô tô
    # HH_US47_PARKING_ONLY: 1 xe máy
    v1 = Vehicle(household_id=households["HH_US47_FULL"].id, plate_number="29A-11111", vehicle_type="MOTORBIKE", status="ACTIVE")
    v2 = Vehicle(household_id=households["HH_US47_FULL"].id, plate_number="29A-22222", vehicle_type="MOTORBIKE", status="ACTIVE")
    v3 = Vehicle(household_id=households["HH_US47_FULL"].id, plate_number="30F-99999", vehicle_type="CAR", status="ACTIVE")
    v4 = Vehicle(household_id=households["HH_US47_PARKING_ONLY"].id, plate_number="29B-33333", vehicle_type="MOTORBIKE", status="ACTIVE")
    db_session.add_all([v1, v2, v3, v4])
    db_session.flush()

    # 7. Miễn giảm: Giảm 20% phí quản lý cho HH_US47_EXEMPTION
    ex = FeeExemption(
        household_id=households["HH_US47_EXEMPTION"].id,
        fee_type_id=ft_mgt.id,
        discount_type="PERCENT",
        discount_value=Decimal("20.00"),
        valid_from=date(2026, 1, 1),
        status="ACTIVE",
        reason="Giảm 20% phí quản lý cư dân cao tuổi",
    )
    db_session.add(ex)
    db_session.commit()

    # 8. Tạo kỳ thu và generate hóa đơn
    res_period = client.post(
        "/api/v1/billing-periods",
        json={"period_month": "2026-11-01", "name": "Kỳ thu tháng 11/2026 US-47"},
        headers=accountant_headers,
    )
    assert res_period.status_code == 201
    period_id = res_period.json()["id"]

    # Nhập chỉ số điện nước cho hộ HH_US47_UTILITY_ONLY
    ur_elec = UtilityReading(
        household_id=households["HH_US47_UTILITY_ONLY"].id,
        fee_type_id=ft_elec.id,
        billing_period_id=period_id,
        previous_index=Decimal("100.000"),
        current_index=Decimal("220.000"),
        unit_price=Decimal("2500.00"),
        amount=Decimal("300000.00"),
    )
    db_session.add(ur_elec)
    db_session.commit()

    # Chạy động cơ tính phí sinh hóa đơn cho toàn bộ hộ
    res_gen = client.post(f"/api/v1/billing-periods/{period_id}/generate", headers=accountant_headers)
    assert res_gen.status_code == 200

    return {
        "period_id": period_id,
        "households": households,
        "apartments": {"apt1": apt1, "apt2": apt2, "apt3": apt3},
        "fee_types": {
            "mgt": ft_mgt,
            "moto": ft_moto,
            "car": ft_car,
            "elec": ft_elec,
            "water": ft_water,
            "fixed": ft_fixed,
        },
    }


# ==============================================================================
# 1. TEST PHÂN QUYỀN RBAC & BẢO MẬT (US-47)
# ==============================================================================

def test_rbac_admin_and_accountant_can_access_invoices(client, admin_headers, accountant_headers, setup_us47_environment):
    """ADMIN và ACCOUNTANT được phép tra cứu danh sách và chi tiết giấy báo nộp phí (US-47)."""
    period_id = setup_us47_environment["period_id"]

    for headers in (admin_headers, accountant_headers):
        # 1. GET /invoices
        res_list = client.get(f"/api/v1/invoices?billing_period_id={period_id}", headers=headers)
        assert res_list.status_code == 200
        invoices = res_list.json()["items"]
        assert len(invoices) >= 1

        # 2. GET /invoices/{id}
        first_id = invoices[0]["id"]
        res_detail = client.get(f"/api/v1/invoices/{first_id}", headers=headers)
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == first_id


def test_rbac_treasurer_and_resident_forbidden_on_invoices(client, treasurer_headers, resident_headers, setup_us47_environment):
    """TREASURER và RESIDENT bị chặn 403 FORBIDDEN trên GET /invoices và GET /invoices/{id} (US-47)."""
    period_id = setup_us47_environment["period_id"]

    for headers in (treasurer_headers, resident_headers):
        assert client.get("/api/v1/invoices", headers=headers).status_code == 403
        assert client.get(f"/api/v1/invoices?billing_period_id={period_id}", headers=headers).status_code == 403
        assert client.get("/api/v1/invoices/1", headers=headers).status_code == 403


def test_rbac_unauthenticated_request_rejected(client):
    """Yêu cầu không kèm token xác thực bị trả về 401 UNAUTHENTICATED (US-47)."""
    assert client.get("/api/v1/invoices").status_code == 401
    assert client.get("/api/v1/invoices/1").status_code == 401


def test_rbac_password_change_required_blocked(client, db_session):
    """Tài khoản có cờ must_change_password=True bị chặn 403 PASSWORD_CHANGE_REQUIRED (US-47)."""
    user = db_session.get(User, 2)
    assert user is not None
    orig_flag = user.must_change_password
    user.must_change_password = True
    db_session.commit()

    try:
        headers = make_headers(role="ACCOUNTANT", sub=str(user.id), username=user.username, must_change_password=True)
        res = client.get("/api/v1/invoices", headers=headers)
        assert res.status_code == 403
        assert res.json().get("code") == "PASSWORD_CHANGE_REQUIRED"
    finally:
        user.must_change_password = orig_flag
        db_session.commit()


# ==============================================================================
# 2. TEST DANH SÁCH GIẤY BÁO NỘP PHÍ (GET /invoices)
# ==============================================================================

def test_list_invoices_pagination(client, accountant_headers, setup_us47_environment):
    """Kiểm tra phân trang danh sách giấy báo (page, page_size, total, total_pages) (US-47)."""
    period_id = setup_us47_environment["period_id"]

    # Trang 1, kích thước 3
    res1 = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&page=1&page_size=3",
        headers=accountant_headers,
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["page"] == 1
    assert data1["page_size"] == 3
    assert len(data1["items"]) == 3
    assert data1["total"] >= 7
    assert data1["total_pages"] >= 3

    # Trang 2, kích thước 3
    res2 = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&page=2&page_size=3",
        headers=accountant_headers,
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["page"] == 2
    assert len(data2["items"]) == 3

    # ID các trang không được trùng nhau
    ids_page1 = [inv["id"] for inv in data1["items"]]
    ids_page2 = [inv["id"] for inv in data2["items"]]
    assert set(ids_page1).isdisjoint(set(ids_page2))


def test_list_invoices_filter_by_billing_period_id(client, accountant_headers, setup_us47_environment, db_session):
    """Lọc danh sách giấy báo theo ID kỳ thu (billing_period_id) (US-47)."""
    period_id = setup_us47_environment["period_id"]

    # 1. Lọc kỳ hiện tại
    res = client.get(f"/api/v1/invoices?billing_period_id={period_id}", headers=accountant_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 7
    assert all(inv["billing_period_id"] == period_id for inv in items)

    # 2. Lọc kỳ không tồn tại
    res_empty = client.get("/api/v1/invoices?billing_period_id=99999", headers=accountant_headers)
    assert res_empty.status_code == 200
    assert len(res_empty.json()["items"]) == 0
    assert res_empty.json()["total"] == 0


def test_list_invoices_filter_by_household_id(client, accountant_headers, setup_us47_environment):
    """Lọc danh sách giấy báo theo ID hộ gia đình (household_id) (US-47)."""
    hh_full = setup_us47_environment["households"]["HH_US47_FULL"]
    res = client.get(f"/api/v1/invoices?household_id={hh_full.id}", headers=accountant_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["household_id"] == hh_full.id
    assert items[0]["household_code"] == "HH_US47_FULL"


def test_list_invoices_filter_by_status(client, accountant_headers, setup_us47_environment, db_session):
    """Lọc danh sách giấy báo theo trạng thái (status: UNPAID, PARTIAL, PAID) (US-47)."""
    period_id = setup_us47_environment["period_id"]

    # Cập nhật 1 hóa đơn sang PAID
    inv_to_pay = db_session.execute(
        select(Invoice).where(Invoice.billing_period_id == period_id)
    ).scalars().first()
    assert inv_to_pay is not None
    inv_to_pay.status = "PAID"
    inv_to_pay.paid_amount = inv_to_pay.total_due
    db_session.commit()

    # 1. Lọc UNPAID
    res_unpaid = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&status=UNPAID",
        headers=accountant_headers,
    )
    assert res_unpaid.status_code == 200
    items_unpaid = res_unpaid.json()["items"]
    assert len(items_unpaid) >= 1
    assert all(inv["status"] == "UNPAID" for inv in items_unpaid)

    # 2. Lọc PAID
    res_paid = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&status=PAID",
        headers=accountant_headers,
    )
    assert res_paid.status_code == 200
    items_paid = res_paid.json()["items"]
    assert len(items_paid) >= 1
    assert any(inv["id"] == inv_to_pay.id for inv in items_paid)


def test_list_invoices_combined_filters(client, accountant_headers, setup_us47_environment):
    """Lọc kết hợp đồng thời billing_period_id + household_id + status (US-47)."""
    period_id = setup_us47_environment["period_id"]
    hh_area = setup_us47_environment["households"]["HH_US47_AREA_ONLY"]

    res = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_area.id}&status=UNPAID",
        headers=accountant_headers,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["household_id"] == hh_area.id
    assert items[0]["billing_period_id"] == period_id
    assert items[0]["status"] == "UNPAID"


def test_list_invoices_includes_household_and_apartment_codes(client, accountant_headers, setup_us47_environment):
    """Kiểm tra danh sách hóa đơn chứa đầy đủ household_code và apartment_code (US-47)."""
    period_id = setup_us47_environment["period_id"]
    hh_full = setup_us47_environment["households"]["HH_US47_FULL"]

    res = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_full.id}",
        headers=accountant_headers,
    )
    assert res.status_code == 200
    inv = res.json()["items"][0]
    assert inv["household_code"] == "HH_US47_FULL"
    assert inv["apartment_code"] == "APT_US47_101"
    assert inv["apartment_area"] == 85.5


def test_list_invoices_default_sorting_id_desc(client, accountant_headers, setup_us47_environment):
    """Danh sách giấy báo mặc định sắp xếp ID giảm dần (mới nhất lên đầu) (US-47)."""
    res = client.get("/api/v1/invoices?page=1&page_size=10", headers=accountant_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    ids = [inv["id"] for inv in items]
    assert ids == sorted(ids, reverse=True)


# ==============================================================================
# 3. TEST CHI TIẾT GIẤY BÁO NỘP PHÍ (GET /invoices/{id})
# ==============================================================================

def test_get_invoice_detail_success(client, accountant_headers, setup_us47_environment):
    """Tra cứu chi tiết một giấy báo nộp phí kèm danh sách toàn bộ các dòng phí chi tiết (US-47)."""
    period_id = setup_us47_environment["period_id"]
    hh_full = setup_us47_environment["households"]["HH_US47_FULL"]

    # 1. Tìm ID hóa đơn
    res_list = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_full.id}",
        headers=accountant_headers,
    )
    inv_id = res_list.json()["items"][0]["id"]

    # 2. Lấy chi tiết
    res_detail = client.get(f"/api/v1/invoices/{inv_id}", headers=accountant_headers)
    assert res_detail.status_code == 200
    data = res_detail.json()

    # Kiểm tra các trường tổng hợp
    assert data["id"] == inv_id
    assert data["billing_period_id"] == period_id
    assert data["household_id"] == hh_full.id
    assert data["household_code"] == "HH_US47_FULL"
    assert data["apartment_code"] == "APT_US47_101"
    assert data["apartment_area"] == 85.5
    assert data["status"] == "UNPAID"
    assert data["total_due"] > 0
    assert data["total_due"] == data["fee_amount"] - data["discount_amount"] + data["previous_debt"] - data["credit_applied"]

    # Kiểm tra danh sách dòng chi tiết items
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 4  # Quản lý, 2 xe máy, 1 ô tô, an ninh


def test_get_invoice_detail_not_found_returns_404(client, accountant_headers):
    """Tra cứu giấy báo không tồn tại trả về 404 NOT_FOUND với details rõ ràng (US-47)."""
    res = client.get("/api/v1/invoices/99999", headers=accountant_headers)
    assert res.status_code == 404
    data = res.json()
    assert data.get("code") == "NOT_FOUND"
    assert "details" in data
    assert data["details"][0]["field"] == "id"


def test_get_invoice_detail_item_fields_and_formulas(client, accountant_headers, setup_us47_environment):
    """Kiểm tra từng dòng InvoiceItem có đầy đủ các trường và công thức net_amount = gross - discount (US-47)."""
    period_id = setup_us47_environment["period_id"]
    hh_full = setup_us47_environment["households"]["HH_US47_FULL"]

    res_list = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_full.id}",
        headers=accountant_headers,
    )
    inv_id = res_list.json()["items"][0]["id"]

    res_detail = client.get(f"/api/v1/invoices/{inv_id}", headers=accountant_headers)
    items = res_detail.json()["items"]

    for item in items:
        assert "id" in item
        assert item["invoice_id"] == inv_id
        assert "fee_type_id" in item
        assert "fee_name" in item and len(item["fee_name"]) > 0
        assert item["quantity"] > 0
        assert item["unit_price"] > 0
        assert item["gross_amount"] >= 0
        assert item["discount_amount"] >= 0
        assert item["net_amount"] >= 0
        assert item["paid_amount"] >= 0
        # AC-47.1 / schema: net_amount = gross_amount - discount_amount
        assert item["net_amount"] == item["gross_amount"] - item["discount_amount"]
        assert item["description"] is not None


# ==============================================================================
# 4. TEST CHI TIẾT TỪNG KHOẢN PHÍ & TỔ HỢP NGHIỆP VỤ (AC-47.1)
# ==============================================================================

def test_invoice_detail_parking_fee_breakdown(client, accountant_headers, setup_us47_environment):
    """Chi tiết giấy báo thể hiện rõ từng loại xe: số lượng, đơn giá, diễn giải (AC-47.1, US-37)."""
    period_id = setup_us47_environment["period_id"]
    hh_full = setup_us47_environment["households"]["HH_US47_FULL"]

    res_list = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_full.id}",
        headers=accountant_headers,
    )
    inv_id = res_list.json()["items"][0]["id"]

    res_detail = client.get(f"/api/v1/invoices/{inv_id}", headers=accountant_headers)
    items = res_detail.json()["items"]
    items_by_fee = {it["fee_type_id"]: it for it in items}

    ft_moto = setup_us47_environment["fee_types"]["moto"]
    ft_car = setup_us47_environment["fee_types"]["car"]

    # 1. Xe máy: 2 xe x 70.000 đ = 140.000 đ
    moto_item = items_by_fee[ft_moto.id]
    assert moto_item["fee_name"] == "Phí gửi xe máy"
    assert moto_item["quantity"] == 2.0
    assert moto_item["unit_price"] == 70000
    assert moto_item["gross_amount"] == 140000
    assert moto_item["net_amount"] == 140000
    assert "2 Phí gửi xe máy" in moto_item["description"]

    # 2. Ô tô: 1 xe x 1.200.000 đ = 1.200.000 đ
    car_item = items_by_fee[ft_car.id]
    assert car_item["fee_name"] == "Phí gửi ô tô"
    assert car_item["quantity"] == 1.0
    assert car_item["unit_price"] == 1200000
    assert car_item["gross_amount"] == 1200000
    assert car_item["net_amount"] == 1200000


def test_invoice_detail_management_fee_breakdown(client, accountant_headers, setup_us47_environment):
    """Chi tiết giấy báo thể hiện rõ diện tích x đơn giá và thành tiền (AC-47.1)."""
    period_id = setup_us47_environment["period_id"]
    hh_full = setup_us47_environment["households"]["HH_US47_FULL"]

    res_list = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_full.id}",
        headers=accountant_headers,
    )
    inv_id = res_list.json()["items"][0]["id"]

    res_detail = client.get(f"/api/v1/invoices/{inv_id}", headers=accountant_headers)
    items_by_fee = {it["fee_type_id"]: it for it in res_detail.json()["items"]}
    ft_mgt = setup_us47_environment["fee_types"]["mgt"]

    # 85.5 m2 x 8.000 đ = 684.000 đ
    mgt_item = items_by_fee[ft_mgt.id]
    assert mgt_item["fee_name"] == "Phí quản lý"
    assert mgt_item["quantity"] == 85.5
    assert mgt_item["unit_price"] == 8000
    assert mgt_item["gross_amount"] == 684000
    assert mgt_item["net_amount"] == 684000
    assert "m²" in mgt_item["description"] and "8,000 đ" in mgt_item["description"]


def test_invoice_detail_utility_reading_breakdown(client, accountant_headers, setup_us47_environment):
    """Chi tiết giấy báo thể hiện rõ chỉ số điện/nước tiêu thụ và đơn giá (AC-47.1, US-38)."""
    period_id = setup_us47_environment["period_id"]
    hh_util = setup_us47_environment["households"]["HH_US47_UTILITY_ONLY"]

    res_list = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_util.id}",
        headers=accountant_headers,
    )
    inv_id = res_list.json()["items"][0]["id"]

    res_detail = client.get(f"/api/v1/invoices/{inv_id}", headers=accountant_headers)
    items_by_fee = {it["fee_type_id"]: it for it in res_detail.json()["items"]}
    ft_elec = setup_us47_environment["fee_types"]["elec"]

    # Tiền điện: tiêu thụ 120 kWh (220 - 100) x 2.500 đ = 300.000 đ
    elec_item = items_by_fee[ft_elec.id]
    assert elec_item["fee_name"] == "Tiền điện"
    assert elec_item["quantity"] == 120.0
    assert elec_item["unit_price"] == 2500
    assert elec_item["gross_amount"] == 300000
    assert elec_item["net_amount"] == 300000
    assert "Tiền điện:" in elec_item["description"] and "2,500 đ" in elec_item["description"]


def test_invoice_detail_with_discount_and_exemption(client, accountant_headers, setup_us47_environment):
    """Chi tiết giấy báo ghi nhận rõ khoản tiền miễn giảm và số tiền thực nộp (AC-47.1, US-15)."""
    period_id = setup_us47_environment["period_id"]
    hh_ex = setup_us47_environment["households"]["HH_US47_EXEMPTION"]

    res_list = client.get(
        f"/api/v1/invoices?billing_period_id={period_id}&household_id={hh_ex.id}",
        headers=accountant_headers,
    )
    inv = res_list.json()["items"][0]

    # Căn hộ 70 m2 x 8.000 đ = 560.000 đ. Giảm 20% = 112.000 đ. Thực nộp = 448.000 đ.
    # Phí an ninh = 50.000 đ. Tổng gốc = 610.000 đ. Giảm = 112.000 đ. Tổng nộp = 498.000 đ.
    assert inv["fee_amount"] == 610000
    assert inv["discount_amount"] == 112000
    assert inv["total_due"] == 498000

    # Kiểm tra dòng chi tiết phí quản lý
    res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=accountant_headers)
    items_by_fee = {it["fee_type_id"]: it for it in res_detail.json()["items"]}
    ft_mgt = setup_us47_environment["fee_types"]["mgt"]

    mgt_item = items_by_fee[ft_mgt.id]
    assert mgt_item["gross_amount"] == 560000
    assert mgt_item["discount_amount"] == 112000
    assert mgt_item["net_amount"] == 448000


def test_invoice_detail_reflects_previous_debt_and_credit_applied(client, accountant_headers, db_session, setup_us47_environment):
    """Giấy báo phản ánh đúng nợ cũ và số dư có theo AC-47.1."""
    period_id = setup_us47_environment["period_id"]
    hh_debt = setup_us47_environment["households"]["HH_US47_DEBT"]

    # Cập nhật thủ công nợ cũ và số dư có cho hóa đơn để kiểm tra hiển thị
    inv = db_session.execute(
        select(Invoice).where(
            Invoice.billing_period_id == period_id,
            Invoice.household_id == hh_debt.id,
        )
    ).scalar_one()
    inv.previous_debt = Decimal("500000")
    inv.credit_applied = Decimal("100000")
    inv.total_due = inv.fee_amount - inv.discount_amount + inv.previous_debt - inv.credit_applied
    db_session.commit()

    res_detail = client.get(f"/api/v1/invoices/{inv.id}", headers=accountant_headers)
    assert res_detail.status_code == 200
    data = res_detail.json()

    assert data["previous_debt"] == 500000
    assert data["credit_applied"] == 100000
    assert data["total_due"] == int(inv.total_due)


# ==============================================================================
# 5. TEST HIỆU NĂNG & KẾT XUẤT HÀNG LOẠT (NFR: <= 1 GIÂY)
# ==============================================================================

def test_list_invoices_performance_under_1_second(client, accountant_headers, setup_us47_environment):
    """Tốc độ phản hồi tra cứu danh sách giấy báo <= 1 giây (NFR)."""
    period_id = setup_us47_environment["period_id"]

    start = time.perf_counter()
    res = client.get(f"/api/v1/invoices?billing_period_id={period_id}&page_size=100", headers=accountant_headers)
    duration = time.perf_counter() - start

    assert res.status_code == 200
    assert duration < 1.0, f"Thời gian phản hồi {duration:.3f}s vượt quá 1 giây"


def test_get_invoice_detail_performance_under_1_second(client, accountant_headers, setup_us47_environment):
    """Tốc độ phản hồi tra cứu chi tiết một giấy báo nộp phí <= 1 giây (NFR)."""
    period_id = setup_us47_environment["period_id"]
    res_list = client.get(f"/api/v1/invoices?billing_period_id={period_id}", headers=accountant_headers)
    first_id = res_list.json()["items"][0]["id"]

    start = time.perf_counter()
    res = client.get(f"/api/v1/invoices/{first_id}", headers=accountant_headers)
    duration = time.perf_counter() - start

    assert res.status_code == 200
    assert duration < 1.0, f"Thời gian phản hồi {duration:.3f}s vượt quá 1 giây"


def test_simulate_batch_print_export_for_all_households(client, accountant_headers, setup_us47_environment):
    """
    Mô phỏng quy trình kết xuất / in giấy báo hàng loạt (AC-47.1):
    Kế toán lấy danh sách giấy báo của kỳ thu và duyệt qua từng hóa đơn để in chi tiết.
    Toàn bộ quá trình cho các hộ hoàn tất mượt mà dưới 2 giây.
    """
    period_id = setup_us47_environment["period_id"]

    start = time.perf_counter()
    # 1. Kế toán lấy toàn bộ danh sách giấy báo của kỳ
    res_list = client.get(f"/api/v1/invoices?billing_period_id={period_id}&page_size=100", headers=accountant_headers)
    assert res_list.status_code == 200
    invoices = res_list.json()["items"]
    assert len(invoices) >= 7

    # 2. Duyệt qua từng giấy báo để lấy chi tiết chuẩn bị in ấn
    for inv in invoices:
        res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=accountant_headers)
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert "items" in detail
        assert detail["household_code"] != ""

    total_duration = time.perf_counter() - start
    assert total_duration < 2.0, f"Tổng thời gian kết xuất hàng loạt {total_duration:.3f}s vượt quá 2 giây"


def test_list_invoices_page_size_boundary_validation(client, accountant_headers):
    """Kiểm tra giới hạn page_size (tối đa 100, page >= 1) trả về 400 nếu vi phạm (US-47)."""
    # page_size=101 vượt quá le=100
    res_large = client.get("/api/v1/invoices?page=1&page_size=101", headers=accountant_headers)
    assert res_large.status_code == 400

    # page=0 vi phạm ge=1
    res_zero = client.get("/api/v1/invoices?page=0&page_size=20", headers=accountant_headers)
    assert res_zero.status_code == 400


def test_list_invoices_empty_result_when_no_match(client, accountant_headers):
    """Bộ lọc không khớp bản ghi nào trả về mảng rỗng và total=0 (US-47)."""
    res = client.get("/api/v1/invoices?household_id=99999", headers=accountant_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["total_pages"] == 0


def test_invoice_detail_status_partial_when_partially_paid(client, accountant_headers, db_session, setup_us47_environment):
    """Giấy báo thanh toán một phần hiển thị trạng thái PARTIAL và đúng paid_amount (US-47)."""
    period_id = setup_us47_environment["period_id"]
    inv = db_session.execute(
        select(Invoice).where(Invoice.billing_period_id == period_id)
    ).scalars().first()
    assert inv is not None

    inv.paid_amount = Decimal("100000")
    inv.status = "PARTIAL"
    db_session.commit()

    res = client.get(f"/api/v1/invoices/{inv.id}", headers=accountant_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PARTIAL"
    assert data["paid_amount"] == 100000


def test_invoice_items_net_amount_formula_integrity(client, accountant_headers, setup_us47_environment):
    """Tất cả các dòng phí trên tất cả hóa đơn đều phải thỏa mãn net_amount = gross_amount - discount_amount (US-47)."""
    period_id = setup_us47_environment["period_id"]
    res_list = client.get(f"/api/v1/invoices?billing_period_id={period_id}&page_size=100", headers=accountant_headers)
    assert res_list.status_code == 200
    invoices = res_list.json()["items"]

    for inv in invoices:
        res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=accountant_headers)
        assert res_detail.status_code == 200
        for item in res_detail.json()["items"]:
            assert item["net_amount"] == item["gross_amount"] - item["discount_amount"]
            assert item["gross_amount"] >= item["discount_amount"]
            assert item["net_amount"] >= 0


def test_invoice_total_due_formula_integrity(client, accountant_headers, setup_us47_environment):
    """Tất cả hóa đơn đều phải thỏa mãn: total_due = fee_amount - discount_amount + previous_debt - credit_applied (AC-17.1, AC-47.1)."""
    period_id = setup_us47_environment["period_id"]
    res_list = client.get(f"/api/v1/invoices?billing_period_id={period_id}&page_size=100", headers=accountant_headers)
    assert res_list.status_code == 200
    invoices = res_list.json()["items"]

    for inv in invoices:
        expected_total = inv["fee_amount"] - inv["discount_amount"] + inv["previous_debt"] - inv["credit_applied"]
        assert inv["total_due"] == max(0, expected_total)


def test_invoice_items_all_have_non_empty_fee_name(client, accountant_headers, setup_us47_environment):
    """Mọi dòng InvoiceItem đều có fee_name hiển thị tường minh cho người dùng in ấn (AC-47.1)."""
    period_id = setup_us47_environment["period_id"]
    res_list = client.get(f"/api/v1/invoices?billing_period_id={period_id}&page_size=100", headers=accountant_headers)
    invoices = res_list.json()["items"]

    for inv in invoices:
        res_detail = client.get(f"/api/v1/invoices/{inv['id']}", headers=accountant_headers)
        for it in res_detail.json()["items"]:
            assert it["fee_name"] is not None
            assert len(it["fee_name"].strip()) > 0

