# ĐẶC TẢ CHI TIẾT USER STORY: US-03 (CHUYỂN NHƯỢNG CĂN HỘ)
> **Mã Story:** `US-03` | **Feature:** `F-01.1` Chuyển nhượng căn hộ | **WBS:** `2.2.1`  
> **Story Points:** `3 SP` | **Độ ưu tiên:** `Should (S)`  
> **Tác giả (Author):** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Reviewer):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-03-backend-apartment-transfer`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.2.1), `docs/API_CONTRACT.md` (Chương 3.5.6), `docs/openapi.yaml` (path `/households/{id}/transfer`), `database/01_schema.sql` (bảng `apartments`, `households`, `apartment_occupancies`, `residents`, `invoices`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As a** Ban Quản Trị (ADMIN),  
> **I want** thực hiện chuyển nhượng quyền cư trú căn hộ sang hộ gia đình mới mà vẫn giữ nguyên lịch sử thu phí và công nợ của hộ cũ,  
> **So that** không làm sai lệch báo cáo tài chính lịch sử, bảo toàn trách nhiệm pháp lý và cập nhật chính xác quyền sở hữu/cư trú của tòa nhà.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-03.1` (Chuyển nhượng căn hộ: đóng hồ sơ cư trú hộ cũ, gắn hộ mới vào căn hộ, bảo toàn 100% lịch sử hóa đơn):**
  - **Kiểm tra công nợ (`DEBT_NOT_SETTLED`):** Hộ cũ phải hoàn tất tất toán toàn bộ công nợ trước khi chuyển nhượng. Nếu hộ cũ còn nợ (`status IN ('UNPAID', 'PARTIALLY_PAID', 'OVERDUE')` hoặc `total_due > paid_amount`), hệ thống từ chối và trả về HTTP `409 DEBT_NOT_SETTLED`.
  - **Kiểm tra căn hộ hộ cũ (`HOUSEHOLD_HAS_NO_APARTMENT`):** Hộ cũ `{id}` bắt buộc phải đang cư trú tại một căn hộ (`end_date IS NULL` trong `apartment_occupancies`). Nếu không có căn hộ, trả về HTTP `409 HOUSEHOLD_HAS_NO_APARTMENT`.
  - **Kiểm tra căn hộ hộ mới (`APARTMENT_OCCUPIED`):** Hộ mới `new_household_id` chưa được gắn với bất kỳ căn hộ nào khác (`end_date IS NULL`). Nếu hộ mới đang có căn hộ khác, hoặc căn hộ chuyển nhượng đang có tranh chấp cư trú khác, trả về HTTP `409 APARTMENT_OCCUPIED`.
  - **Giao dịch ACID nguyên tử duy nhất:**
    + Đóng hồ sơ cư trú cũ: Ghi nhận `end_date = effective_date` và `end_reason` trong `apartment_occupancies` của hộ cũ.
    + Mở hồ sơ cư trú mới: Tạo bản ghi mới trong `apartment_occupancies` với `apartment_id` tương ứng, `household_id = new_household_id`, `start_date = effective_date`, `end_date = NULL`.
  - **Bảo toàn 100% dữ liệu lịch sử:**
    + Toàn bộ hóa đơn (`invoices`), khoản thu, biên lai (`payments`), sổ cái tín dụng (`household_credit_ledger`) của hộ cũ gắn với `household_id` nên được giữ nguyên vẹn 100% thuộc về hộ cũ, không bị dịch chuyển hay sửa đổi.
    + Nhân khẩu (`residents`) của hộ cũ và hộ mới được giữ nguyên liên kết độc lập với từng hộ gia đình tương ứng.
    + Tuyệt đối cấm xóa vật lý (No hard delete). Căn hộ vật lý (`apartments`) giữ nguyên trạng thái `ACTIVE`.
  - **Nhật ký kiểm toán (`AuditLog`):** Ghi nhận hành động `TRANSFER_APARTMENT`, `entity_type = 'HOUSEHOLD'`, lưu vết ID hộ cũ, mã hộ cũ, căn hộ chuyển nhượng trong `old_value`; ID hộ mới, mã hộ mới, căn hộ và ngày hiệu lực trong `new_value`.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── schemas/
│   ├── __init__.py                  # Export HouseholdTransferRequest
│   └── household.py                 # Pydantic v2 schema HouseholdTransferRequest
├── routers/
│   └── households.py                # Endpoint POST /households/{id}/transfer
backend/tests/
└── test_us03_apartment_transfer.py # Bộ 84 test cases Black-box độc lập kiểm thử toàn diện US-03
```

---

## 3. CHI TIẾT HTTP REST ENDPOINT (STRICT API CONTRACT)

### `POST /api/v1/households/{id}/transfer` (Chuyển nhượng căn hộ từ hộ này sang hộ mới)
* **Operation ID:** `transferHousehold`
* **Quyền gọi (Roles):** `ADMIN`
* **Path Parameter:**
  - `id`: int (ID hộ gia đình đang giữ căn hộ cần chuyển nhượng)
* **Request Body:** Schema `HouseholdTransferRequest`
  - `new_household_id`: int (Bắt buộc, ID hộ gia đình mới nhận căn hộ)
  - `effective_date`: date (Bắt buộc, định dạng ISO `YYYY-MM-DD`)
  - `reason`: Optional[str] (Lý do chuyển nhượng)
* **Mã phản hồi HTTP & Xử lý nghiệp vụ:**
  - `200 OK`: Trả về schema `Household` đại diện cho hộ gia đình mới đã nhận căn hộ thành công.
  - `400 VALIDATION_ERROR`:
    + Dữ liệu đầu vào thiếu hoặc sai kiểu dữ liệu (ngày sai định dạng, ID không phải số).
    + Chuyển nhượng cho chính mình (`new_household_id == id`).
    + Ngày hiệu lực `effective_date` trước ngày bắt đầu cư trú của hộ cũ (`old_occupancy.start_date`).
    + Hộ cũ hoặc hộ mới đã ngưng hoạt động (`status == 'INACTIVE'`).
  - `401 UNAUTHENTICATED`: Thiếu header Authorization, token sai, không đúng Bearer, hoặc token đã hết hạn.
  - `403 FORBIDDEN`: Gọi bởi tài khoản không có quyền ADMIN (`RESIDENT`, `ACCOUNTANT`, `TREASURER`).
  - `403 PASSWORD_CHANGE_REQUIRED`: Tài khoản ADMIN chưa đổi mật khẩu lần đầu (`must_change_password = True`).
  - `404 NOT_FOUND`: Không tìm thấy hộ cũ `{id}` hoặc hộ nhận `new_household_id`.
  - `409 DEBT_NOT_SETTLED`: Hộ cũ còn công nợ chưa tất toán (`UNPAID`, `PARTIALLY_PAID`, `OVERDUE`).
  - `409 HOUSEHOLD_HAS_NO_APARTMENT`: Hộ cũ hiện không cư trú tại căn hộ nào.
  - `409 APARTMENT_OCCUPIED`: Hộ nhận hiện đang cư trú tại một căn hộ khác, hoặc căn hộ có tranh chấp cư trú đang mở.
  - `500 INTERNAL_SERVER_ERROR`: Lỗi hệ thống hoặc lỗi giao dịch CSDL không mong muốn.

---

## 4. QUẢN LÝ DỮ LIỆU & TÍNH TOÀN VẸN GIAO DỊCH (ACID & INVARIANTS)

1. **Phân tách thực thể vật lý & đơn vị cư trú (T-01 & T-02):**
   - Căn hộ vật lý (`apartments`) độc lập hoàn toàn với hộ gia đình (`households`).
   - Mối quan hệ cư trú theo thời gian được quản lý qua bảng trung gian `apartment_occupancies`.
   - Chuyển nhượng căn hộ không sửa đổi bảng `apartments` mà kết thúc dòng cư trú cũ (`end_date = effective_date`) và mở dòng cư trú mới (`start_date = effective_date`, `end_date = NULL`).
2. **Bảo toàn dữ liệu lịch sử hóa đơn:**
   - Hệ thống hóa đơn thu phí (`invoices`, `invoice_items`) tham chiếu trực tiếp đến `household_id`.
   - Do đó, khi căn hộ được chuyển nhượng, toàn bộ biên lai, hóa đơn, lịch sử thanh toán của hộ cũ được bảo toàn 100%, không bị chuyển giao hay sửa đổi sai lệch.
3. **Tính nguyên tử ACID:**
   - Toàn bộ thao tác: kiểm tra điều kiện, đóng occupancy cũ, mở occupancy mới, ghi nhận audit log được thực hiện trong một giao dịch DB duy nhất (`db.commit()`), tự động rollback nếu xảy ra bất kỳ ngoại lệ nào.

---

## 5. BÁO CÁO KẾT QUẢ KIỂM THỬ BLACK-BOX (QA AGENT)

- **Tệp test:** `backend/tests/test_us03_apartment_transfer.py`
- **Tổng số test cases:** **84** test cases
- **Kết quả:** **84/84 PASSED (100% PASS)**
- **Thời gian thực thi:** **2.61s**
- **Phân bổ kịch bản kiểm thử:**
  1. *Xác thực & Phân quyền RBAC (11 test cases):* Kiểm tra token hợp lệ, thiếu token, token hết hạn, chặn vai trò RESIDENT, ACCOUNTANT, TREASURER, chặn bắt buộc đổi mật khẩu lần đầu, ghi log ACCESS_DENIED.
  2. *Phương thức HTTP không được phép (4 test cases):* Chặn GET, PUT, PATCH, DELETE trên path chuyển nhượng (HTTP 405).
  3. *Kiểm tra Path Parameter (5 test cases):* ID chuỗi, số thực, số 0, số âm, SQL injection.
  4. *Kiểm tra Schema Request Body & Kiểu dữ liệu (21 test cases):* Thiếu trường, null, sai kiểu dữ liệu, ngày sai định dạng, ngày không hợp lệ (tháng 13, 30/02), lý do không đúng kiểu, raw text non-JSON.
  5. *Lỗi Không tìm thấy (4 test cases):* Hộ nguồn không tồn tại, hộ đích không tồn tại, cả hai không tồn tại, đối chiếu chuẩn schema Error.
  6. *Xung đột nghiệp vụ & Ràng buộc miền (11 test cases):* `HOUSEHOLD_HAS_NO_APARTMENT`, `APARTMENT_OCCUPIED`, `DEBT_NOT_SETTLED` (nợ 1 phần, chưa trả, nợ đọng), hộ INACTIVE, tự chuyển nhượng cho chính mình, ngày hiệu lực trước ngày bắt đầu.
  7. *Kịch bản thành công & Chuyển dịch trạng thái (15 test cases):* Happy path, schema phản hồi, đóng occupancy cũ, mở occupancy mới, kiểm tra lại trạng thái hộ cũ và mới qua GET, không có lý do, lý do tiếng Việt Unicode, lý do dài, ngày trùng boundary, chuyển nhượng liên tiếp theo chuỗi (A $\rightarrow$ B $\rightarrow$ C).
  8. *Nhật ký kiểm toán Audit Log (5 test cases):* Sinh bản ghi `TRANSFER_APARTMENT`, khớp admin user_id, khớp entity_id, lưu đúng reason, ghi nhận old_value và new_value.
  9. *Bảo toàn dữ liệu & Tính toàn vẹn ACID (8 test cases):* Bảo toàn 100% hóa đơn hộ cũ (`AC-03.1`), bảo toàn nhân khẩu hộ cũ, bảo toàn nhân khẩu hộ mới, ngăn chuyển nhượng lần 2 khi không còn căn hộ, rollback khi lỗi hộ đích, rollback khi lỗi công nợ, rollback khi hộ nhận đã có căn hộ, giữ nguyên trạng thái ACTIVE của căn hộ vật lý.

