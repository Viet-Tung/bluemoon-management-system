# Bản đồ Tri thức Backend (`docs/backend_spec/`)

## 1. Kiến trúc tri thức 3 tầng & Kiểm kê tài liệu
- **Tầng 1 — *Cái gì* (Code & Test tự kiểm chứng):** Router FastAPI (`/docs`) đối chiếu tự động với [openapi.yaml](../openapi.yaml) qua [test_contract_drift.py](../../backend/tests/test_contract_drift.py); chi tiết luồng & edge case nằm ở docstring router và tên/docstring `pytest`.
- **Tầng 2 — *Tại sao* (Append-only ADR):** [DECISIONS.md](./DECISIONS.md) (chỉ nối thêm quyết định mới, không sửa mục cũ).
- **Tầng 3 — *Điều hướng*:** File này (`< 80` dòng).
- **SSOT Read-only:** [Plan.pdf](../Plan.pdf) | [01_schema.sql](../../database/01_schema.sql) | [openapi.yaml](../openapi.yaml) | [DATABASE_DESIGN.md](../DATABASE_DESIGN.md) | [ARCHITECTURE.md](../ARCHITECTURE.md) | [PRODUCT_BACKLOG.md](../PRODUCT_BACKLOG.md).
- **Lưu trữ lịch sử:** 15 file spec chi tiết Sprint 1 trước đây (`docs/backend_spec/sprint_1/`) đã được dọn khỏi working tree (lưu trong Git history) để tránh trùng lặp với OpenAPI và code hiện hành.

## 2. Trạng thái User Stories Backend (Sprint 1 & 2)

| User Stories | Module Router (`backend/app/routers/`) | Test Suite (`backend/tests/`) | Trạng thái |
|---|---|---|---|
| `US-28`, `US-29`, `US-44` | `auth.py`, `rbac_middleware.py`, `security.py` | `test_us28_auth.py`, `test_us29_change_password.py`, `test_us44_security.py` | Done |
| `US-30`, `US-31`, `US-32`, `US-45` | `users.py`, `roles.py`, `audit_logs.py`, `system.py` | `test_us30_users.py`, `test_us31_role_management.py`, `test_us32_audit_log.py`, `test_us45_system_backups.py` | Done |
| `US-01`, `US-02`, `US-03` | `apartments.py`, `households.py` | `test_us01_apartments_households.py`, `test_us02_household_management.py`, `test_us03_apartment_transfer.py` | Done |
| `US-04`, `US-05`, `US-06`, `US-23` | `import_data.py`, `residents.py`, `search.py` | `test_us04_import_excel.py`, `test_us05_residents.py`, `test_us23_omnibox_search.py` | Done |
| `US-12`, `US-13`, `US-14` | `fee_types.py` | `test_us12_fee_catalog.py`, `test_us13_deactivate_fee.py`, `test_us14_fee_rates.py` | Done |
| `US-15`, `US-16`, `US-36` | `fee_exemptions.py`, `vehicles.py` | `test_us15_fee_exemptions.py`, `test_us36_vehicles.py` | Done |
| `US-17`, `US-37`, `US-38`, `US-47` | `billing.py` | `test_us17_billing_engine.py`, `test_us37_parking_fee.py`, `test_us38_utility_readings.py`, `test_us47_invoices.py` | Done |
| Kiểm tra tổng hợp & Drift | Toàn bộ `/api/v1/*` | `test_contract_drift.py`, `test_advanced_testing_sprint1.py` | Done |

## 3. Lệnh vận hành nhanh
- **Test toàn bộ (`pytest`):** `cd backend; .\venv\Scripts\pytest.exe -c pytest.ini tests -q --tb=short`
- **Kiểm tra lệch OpenAPI:** `cd backend; .\venv\Scripts\pytest.exe -c pytest.ini tests/test_contract_drift.py -v`
- **Chạy server dev:** `cd backend; .\venv\Scripts\uvicorn.exe app.main:app --reload --port 8000`
- **Seed DB PostgreSQL mẫu:** nạp [seed_sprint1_test.sql](../../backend/sql/seed_sprint1_test.sql) rồi [seed_sprint2_test.sql](../../backend/sql/seed_sprint2_test.sql) vào container `bluemoon-postgres`.

## 4. Quy ước cốt lõi
- **DB & Tài khoản mẫu:** `DATABASE_URL` trỏ `bluemoon_db`; mật khẩu chung tài khoản seed: `BlueMoon@2026` (`admin_bqt`, `ketoan_01`, `thuquy_01`, `cudan_b1204`).
- **Bất biến nghiệp vụ:** 4 vai trò (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`), không xóa vật lý (`DELETE FROM` bị cấm), mọi mutation nhạy cảm ghi `audit_logs`, endpoint mutation trọng yếu hỗ trợ `Idempotency-Key`.
