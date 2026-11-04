# ĐẶC TẢ CHI TIẾT USER STORY: US-02 (QUẢN LÝ THÔNG TIN HỘ & THAY ĐỔI CHỦ HỘ)
> **Mã Story:** `US-02` | **Feature:** `F-01.1` Đổi chủ hộ / Quản lý thông tin hộ | **WBS:** `2.2.1`  
> **Story Points:** `3 SP` | **Độ ưu tiên:** `Should (S)`  
> **Tác giả (Author):** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Reviewer):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-02-backend-household-management`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.2.1), `docs/API_CONTRACT.md` (Chương 3.5), `docs/openapi.yaml` (các path `/households/{id}`, `/households/{id}/deactivate`, `/households/{id}/head`), `database/01_schema.sql` (bảng `households`, `apartment_occupancies`, `residents`, `users`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As a** Ban Quản Trị (ADMIN),  
> **I want** cập nhật thông tin liên hệ hộ gia đình, ngừng quản lý hộ và thực hiện nghiệp vụ thay đổi chủ hộ đại diện kèm điều kiện kiểm tra công nợ,  
> **So that** đảm bảo tính chính xác của dữ liệu cư trú, trách nhiệm pháp lý và bảo toàn lịch sử tài chính của tòa nhà.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-02.1` (Kiểm tra tất toán công nợ trước khi đổi chủ hộ; ghi Audit Log `CHANGE_HEAD`):**
  - Kiểm tra và bắt buộc tất toán công nợ cũ trước khi cho phép thay đổi chủ hộ đại diện (`D-06`). Nếu hộ còn nợ chưa tất toán, trả về lỗi xung đột `409 DEBT_NOT_SETTLED`.
  - Thực hiện trong **duy nhất 1 giao dịch ACID nguyên tử**: hạ chủ hộ cũ (`is_head = False`, quan hệ chuyển sang "THÀNH VIÊN") và nâng nhân khẩu mới (`is_head = True`, quan hệ là "CHỦ HỘ").
  - Đảm bảo tính bất biến toàn vẹn: mỗi hộ gia đình tại một thời điểm chỉ có **duy nhất 1 chủ hộ đang hoạt động** (`ux_residents_one_head`).
  - Ghi nhận nhật ký kiểm toán bất biến `AuditLog` với `action = 'CHANGE_HEAD'`, `entity_type = 'HOUSEHOLD'`, lưu vết chính xác ID chủ hộ cũ trong `old_value` và ID chủ hộ mới trong `new_value`.
* **Cập nhật thông tin liên hệ hộ gia đình (`PATCH /api/v1/households/{id}`):**
  - Cho phép Admin cập nhật số điện thoại liên hệ, email liên hệ và ghi chú của hộ gia đình.
  - Kiểm tra validation email đúng định dạng RFC chuẩn (`VALIDATION_ERROR` 400).
  - Không cho phép can thiệp hoặc sửa đổi các trường bất biến (`id`, `household_code`, `status`) qua PATCH.
* **Ngừng quản lý hộ gia đình (`POST /api/v1/households/{id}/deactivate`):**
  - Chỉ cho phép ngừng quản lý khi hộ gia đình không còn công nợ (`409 DEBT_NOT_SETTLED`).
  - Chuyển trạng thái hộ sang `INACTIVE`. **Tuyệt đối cấm xóa vật lý (No hard delete)** nhằm bảo toàn 100% dữ liệu lịch sử.
  - Tự động đóng thời gian cư trú hiện tại trong `apartment_occupancies` (`end_date = CURRENT_DATE`), ghi nhận `end_reason`.
  - Vô hiệu hóa tài khoản cư dân của hộ nếu đang hoạt động (`is_active = False`).
  - Ghi nhận `AuditLog` với `action = 'DEACTIVATE_HOUSEHOLD'`.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── schemas/
│   ├── __init__.py              # Export HouseholdDeactivate, HouseholdChangeHead, HouseholdUpdate
│   └── household.py             # Schemas Pydantic v2: HouseholdUpdate, HouseholdDeactivate, HouseholdChangeHead
├── routers/
│   └── households.py            # Hiện thực 3 endpoints: PATCH /households/{id}, POST /households/{id}/deactivate, PUT /households/{id}/head
backend/tests/
└── test_us02_household_management.py # Bộ 98 test cases Black-box độc lập kiểm thử toàn diện US-02
```

---

## 3. CHI TIẾT 3 HTTP REST ENDPOINTS (STRICT API CONTRACT)

### 3.1. `PATCH /api/v1/households/{id}` (Cập nhật thông tin liên hệ hộ)
* **Quyền gọi (Roles):** `ADMIN`
* **Path Parameter:** `id`: int (ID hộ gia đình)
* **Request Body:** `HouseholdUpdate`
  - `contact_phone`: Optional[str] (Số điện thoại)
  - `contact_email`: Optional[str] (Email chuẩn)
  - `note`: Optional[str] (Ghi chú)
* **Mã phản hồi HTTP:**
  - `200 OK`: Trả về schema `Household` đã cập nhật.
  - `400 VALIDATION_ERROR`: Email sai định dạng hoặc kiểu dữ liệu không hợp lệ.
  - `401 UNAUTHENTICATED`: Thiếu hoặc sai JWT token.
  - `403 FORBIDDEN`: Sai quyền (`ACCOUNTANT`, `TREASURER`, `RESIDENT` bị chặn).
  - `403 PASSWORD_CHANGE_REQUIRED`: Admin chưa đổi mật khẩu lần đầu.
  - `404 NOT_FOUND`: Không tìm thấy ID hộ gia đình.

### 3.2. `POST /api/v1/households/{id}/deactivate` (Ngừng quản lý hộ gia đình)
* **Quyền gọi (Roles):** `ADMIN`
* **Path Parameter:** `id`: int
* **Request Body:** `HouseholdDeactivate`
  - `reason`: str (Bắt buộc, tối thiểu 1 ký tự)
* **Xử lý nghiệp vụ:**
  - Kiểm tra hộ tồn tại -> `404 NOT_FOUND`.
  - Kiểm tra công nợ chưa tất toán -> `409 DEBT_NOT_SETTLED`.
  - Cập nhật `status = 'INACTIVE'`, kết thúc lưu trú `apartment_occupancies`, khóa tài khoản cư dân.
  - Ghi nhận `AuditLog` (`action = 'DEACTIVATE_HOUSEHOLD'`).
* **Mã phản hồi HTTP:**
  - `200 OK`: Trả về schema `Household` với `status: "INACTIVE"`.
  - `400 VALIDATION_ERROR`: Thiếu `reason` hoặc `reason` rỗng.
  - `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `403 PASSWORD_CHANGE_REQUIRED`.
  - `404 NOT_FOUND`: Không tìm thấy hộ.
  - `409 DEBT_NOT_SETTLED`: Hộ còn nợ đọng chưa thanh toán hết.

### 3.3. `PUT /api/v1/households/{id}/head` (Đổi chủ hộ đại diện)
* **Quyền gọi (Roles):** `ADMIN`
* **Path Parameter:** `id`: int
* **Request Body:** `HouseholdChangeHead`
  - `new_head_resident_id`: int (ID nhân khẩu chỉ định làm chủ hộ mới)
  - `effective_date`: date (Ngày có hiệu lực chuyển giao)
  - `reason`: Optional[str] (Lý do đổi chủ hộ)
* **Xử lý nghiệp vụ:**
  - Kiểm tra hộ tồn tại -> `404 NOT_FOUND`.
  - Kiểm tra hộ đang hoạt động (`status == 'ACTIVE'`), nếu `INACTIVE` -> `400 VALIDATION_ERROR`.
  - Kiểm tra công nợ -> `409 DEBT_NOT_SETTLED` (AC-02.1).
  - Kiểm tra nhân khẩu tồn tại thuộc hộ và không bị xóa -> `404 NOT_FOUND`.
  - Kiểm tra trạng thái nhân khẩu phải là `THUONG_TRU` hoặc `TAM_VANG` (từ chối `DA_CHUYEN_DI`, `DA_QUA_DOI`) -> `400 VALIDATION_ERROR`.
  - Trong 1 giao dịch ACID:
    + Hạ chủ hộ cũ (`is_head = False`, `relationship_to_head = 'THÀNH VIÊN'`).
    + Nâng chủ hộ mới (`is_head = True`, `relationship_to_head = 'CHỦ HỘ'`).
    + Đồng bộ tên đại diện tài khoản cư dân nếu có.
    + Ghi `AuditLog` (`action = 'CHANGE_HEAD'`, `entity_type = 'HOUSEHOLD'`).
* **Mã phản hồi HTTP:**
  - `200 OK`: Trả về schema `Household` với thông tin chủ hộ mới (`head_resident_id`, `head_name`, `head_phone`).
  - `400 VALIDATION_ERROR`: Sai định dạng ngày, nhân khẩu không đủ tư cách (đã qua đời/chuyển đi), hộ đã đóng.
  - `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `403 PASSWORD_CHANGE_REQUIRED`.
  - `404 NOT_FOUND`: Hộ hoặc nhân khẩu không tồn tại / không thuộc hộ.
  - `409 DEBT_NOT_SETTLED`: Hộ còn công nợ chưa tất toán.

---

## 4. MA TRẬN MÃ LỖI NGHIỆP VỤ (ERROR CODES)

| HTTP Status | Mã `code` | Tình huống áp dụng | Schema phản hồi |
| :---: | :--- | :--- | :--- |
| **400** | `VALIDATION_ERROR` | Email sai định dạng, thiếu `reason`, `reason` rỗng, sai định dạng ngày `effective_date`, nhân khẩu đã chuyển đi/qua đời, hộ đã `INACTIVE`. | `Error` |
| **401** | `UNAUTHENTICATED` | Thiếu Authorization Bearer header, token sai hoặc đã hết hạn. | `Error` |
| **403** | `FORBIDDEN` | Sai vai trò theo ma trận RBAC (`ACCOUNTANT`, `TREASURER`, `RESIDENT`). | `Error` |
| **403** | `PASSWORD_CHANGE_REQUIRED` | Tài khoản có `must_change_password = True` gọi API ngoài đổi mật khẩu. | `Error` |
| **404** | `NOT_FOUND` | Không tìm thấy ID hộ gia đình hoặc ID nhân khẩu trong hộ. | `Error` |
| **409** | `DEBT_NOT_SETTLED` | Hộ còn nợ đọng, không cho phép đổi chủ hộ hoặc ngừng quản lý hộ (`AC-02.1`, `D-06`). | `Error` |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi máy chủ hoặc lỗi giao dịch CSDL không mong muốn. | `Error` |

---

## 5. KẾT QUẢ KIỂM THỬ BLACK-BOX ĐỘC LẬP

* **Tệp test:** `backend/tests/test_us02_household_management.py`
* **Người thực hiện:** QA Subagent (Black-Box Tester độc lập)
* **Số lượng test cases:** **102 test cases** (vượt 204% chỉ tiêu tối thiểu $\ge 50$ tests), **100% Pass rate**.
* **Phân bổ chi tiết:**
  - **29 test cases** cho `PATCH /api/v1/households/{id}`: cập nhật từng trường, cập nhật đồng thời, null payload, unicode tiếng Việt, ký tự đặc biệt, chuỗi dài 1,000 ký tự, bảo vệ các trường bất biến (`id`, `household_code`, `status`), validation email sai format, boundaries ID âm/0/999999, RBAC Guard (401/403/must_change_password).
  - **25 test cases** cho `POST /api/v1/households/{id}/deactivate`: ngừng quản lý hộ, kiểm tra trạng thái `INACTIVE`, đóng lịch sử lưu trú `apartment_occupancies`, vô hiệu hóa tài khoản cư dân, **kiểm tra bất biến No hard delete trực tiếp trên CSDL**, kiểm tra ghi nhận `AuditLog`, validation `reason` thiếu/rỗng/whitespace/null/sai type, boundaries 404, RBAC Guard (401/403).
  - **39 test cases** cho `PUT /api/v1/households/{id}/head`: đổi chủ hộ thành công, hạ chủ hộ cũ, nâng chủ hộ mới, **đảm bảo duy nhất 1 chủ hộ hoạt động (`ux_residents_one_head`)**, kiểm tra ghi nhận `AuditLog` bắt buộc (`CHANGE_HEAD`), chặn đổi chủ hộ khi hộ `INACTIVE`, chặn nhân khẩu `DA_CHUYEN_DI` và `DA_QUA_DOI`, chặn nhân khẩu hộ khác, validation ngày ISO, boundaries 404, RBAC Guard (401/403).
  - **5 test cases** kiểm tra phong bì lỗi chuẩn (`Error` envelope: `code`, `message`, `details`) và tự động ghi `AuditLog` hành động `ACCESS_DENIED` khi vi phạm RBAC Guard.
  - **4 test cases** kiểm thử chuyên sâu ràng buộc nợ (`TestDebtNotSettledEnforcement`): giả lập bảng `invoices` trong SQLite để kích hoạt và xác thực nhánh lỗi `409 DEBT_NOT_SETTLED` khi có nợ chưa thanh toán (`UNPAID`), nợ quá hạn (`OVERDUE`), nợ thanh toán một phần (`PARTIALLY_PAID`), và xác thực nghiệp vụ thành công ngay sau khi tất toán (`PAID`).
* **Tổng test suite toàn dự án:** **952 passed** (850 tests cũ + 102 tests US-02), không có bất kỳ regression hay xung đột nào.

