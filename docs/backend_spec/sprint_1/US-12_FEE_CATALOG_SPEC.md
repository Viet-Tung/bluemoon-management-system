# ĐẶC TẢ CHI TIẾT USER STORY: US-12 (QUẢN LÝ DANH MỤC KHOẢN THU BẮT BUỘC)
> **Mã Story:** `US-12` | **Feature:** `F-03.1` Danh mục khoản thu | **WBS:** `2.3.1`  
> **Story Points:** `3 SP` | **Độ ưu tiên:** `Must (M)`  
> **Tác giả (Author):** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Reviewer):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-12-backend-fee-catalog`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.2.3), `docs/API_CONTRACT.md` (mục 3.11.1 – 3.11.3), `docs/openapi.yaml` (paths `/fee-types`, `/fee-types/{id}`, `/fee-types/{id}/deactivate`), `database/01_schema.sql` (bảng `fee_types`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As an** Kế toán (ACCOUNTANT) hoặc Ban Quản Trị (ADMIN),  
> **I want** khai báo, xem danh sách và cập nhật danh mục các khoản thu bắt buộc (như phí quản lý, phí gửi xe máy/ô tô, tiền nước, dịch vụ khác) kèm quy tắc tính toán và chu kỳ thu,  
> **So that** hệ thống có căn cứ chuẩn hóa để áp biểu giá, tính tiền và phát hành thông báo thu phí hàng tháng một cách minh bạch, chính xác.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-12.1` (Khai báo mã, tên, fee_group, calc_method, đơn vị tính của khoản thu):**
  - **Khai báo khoản thu mới (`POST /fee-types`):**
    + Bắt buộc cung cấp: `code` (mã định danh duy nhất), `name` (tên khoản thu), `fee_group` (nhóm phí), `calc_method` (phương pháp tính phí), `unit_label` (đơn vị tính).
    + Nhóm phí `fee_group` hợp lệ thuộc danh mục enum: `MANAGEMENT`, `PARKING`, `UTILITY`, `OTHER`.
    + Phương pháp tính `calc_method` thuộc danh mục enum: `PER_M2`, `PER_HOUSEHOLD`, `PER_PERSON`, `PER_VEHICLE`, `METERED`.
    + Ràng buộc loại phương tiện: Khi `calc_method = PER_VEHICLE`, bắt buộc phải truyền `vehicle_type` thuộc danh mục: `MOTORBIKE`, `CAR`, `BICYCLE`.
    + Chu kỳ thu `cycle`: Mặc định là `MONTHLY`, hỗ trợ `QUARTERLY`, `YEARLY`.
    + Hạn nộp `due_day`: Nếu khai báo, giá trị số nguyên phải nằm trong phạm vi từ 1 đến 31.
    + Kiểm tra trùng lặp mã (`DUPLICATE_FEE_CODE`): Mã `code` là duy nhất trên toàn hệ thống (không phân biệt hoa/thường). Nếu trùng, từ chối và trả về HTTP `409 DUPLICATE_FEE_CODE`.
    + Trạng thái ban đầu mặc định là `ACTIVE`.
  - **Danh sách danh mục khoản thu (`GET /fee-types`):**
    + Hỗ trợ phân trang: `page` (mặc định 1), `page_size` (mặc định 20, tối đa 100).
    + Hỗ trợ lọc theo `status` (`ACTIVE`, `INACTIVE`) và theo nhóm phí `fee_group`.
    + Tự động gắn kèm đơn giá hiện hành `current_unit_price` nếu đã có bảng `fee_rates` đang có hiệu lực.
  - **Cập nhật khoản thu (`PATCH /fee-types/{id}`):**
    + Cho phép cập nhật các thuộc tính linh hoạt: `name`, `unit_label`, `provider_id`, `cycle`, `due_day`, `description`.
    + Tuân thủ nghiêm ngặt Schema Contract `FeeTypeUpdate`: Bất biến trường `code` và `calc_method` sau khi khởi tạo, mọi yêu cầu cố tình thay đổi mã hoặc cách tính đều bị bỏ qua (ignore) để bảo toàn tính toàn vẹn dữ liệu kế toán và lịch sử giao dịch.
    + Không tìm thấy ID bản ghi trả về HTTP `404 NOT_FOUND`.
  - **Ngừng áp dụng khoản thu (`POST /fee-types/{id}/deactivate` - US-13, AC-13.1):**
    + Chuyển trạng thái sang `INACTIVE`, tuyệt đối cấm xóa vật lý (No hard delete).
  - **Nhật ký kiểm toán (`AuditLog` - AC-32.1):**
    + Mọi thao tác thêm mới (`CREATE_FEE_TYPE`), cập nhật (`UPDATE_FEE_TYPE`), ngừng áp dụng (`DEACTIVATE_FEE`) đều được ghi vết tự động vào bảng `audit_logs` với đầy đủ `old_value`, `new_value`, `user_id`, `ip_address`, `user_agent`.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── models/
│   ├── __init__.py                  # Export FeeType model
│   └── fee.py                       # SQLAlchemy model FeeType (bảng fee_types)
├── schemas/
│   ├── __init__.py                  # Export Pydantic v2 schemas cho Fee Catalog
│   └── fee.py                       # FeeType, FeeTypeCreate, FeeTypeUpdate, FeeTypePage, Enums
├── routers/
│   ├── __init__.py                  # Export fee_types_router
│   └── fee_types.py                 # FastAPI Router: GET /fee-types, POST /fee-types, PATCH /fee-types/{id}, POST /fee-types/{id}/deactivate
backend/tests/
└── test_us12_fee_catalog.py        # Bộ 79 test cases Black-box độc lập kiểm thử toàn diện US-12
```

---

## 3. CHI TIẾT HTTP REST ENDPOINTS (STRICT API CONTRACT CONFORMANCE)

### 3.1. `GET /api/v1/fee-types` (Danh sách khoản thu bắt buộc)
* **Operation ID:** `listFeeTypes`
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Query Parameters:**
  - `page`: int (Mặc định 1, $\ge 1$)
  - `page_size`: int (Mặc định 20, $1 \le \text{page\_size} \le 100$)
  - `status`: Optional[str] (`ACTIVE`, `INACTIVE`)
  - `fee_group`: Optional[str] (`MANAGEMENT`, `PARKING`, `UTILITY`, `OTHER`)
* **Mã phản hồi HTTP:**
  - `200 OK`: Trả về `FeeTypePage` (`items`, `page`, `page_size`, `total`).
  - `400 VALIDATION_ERROR`: `page < 1`, `page_size < 1` hoặc `> 100`, `status` sai enum, `fee_group` sai enum.
  - `401 UNAUTHENTICATED`: Thiếu hoặc sai JWT token.
  - `403 FORBIDDEN`: Gọi bởi tài khoản `RESIDENT`, `TREASURER`.
  - `403 PASSWORD_CHANGE_REQUIRED`: Tài khoản chưa đổi mật khẩu lần đầu.
  - `500 INTERNAL_SERVER_ERROR`: Lỗi hệ thống.

### 3.2. `POST /api/v1/fee-types` (Tạo khoản thu mới)
* **Operation ID:** `createFeeType`
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Request Body:** Schema `FeeTypeCreate`
  - `code`: str (Bắt buộc, không rỗng, $\le 50$ ký tự)
  - `name`: str (Bắt buộc, không rỗng, $\le 255$ ký tự)
  - `fee_group`: FeeGroup (Bắt buộc: `MANAGEMENT`, `PARKING`, `UTILITY`, `OTHER`)
  - `calc_method`: CalcMethod (Bắt buộc: `PER_M2`, `PER_HOUSEHOLD`, `PER_PERSON`, `PER_VEHICLE`, `METERED`)
  - `unit_label`: str (Bắt buộc, không rỗng: `m2`, `hộ`, `người`, `xe`, `kWh`, `m3`)
  - `vehicle_type`: Optional[VehicleType] (Bắt buộc khi `calc_method = PER_VEHICLE`: `MOTORBIKE`, `CAR`, `BICYCLE`)
  - `is_pass_through`: bool (Mặc định `false`, thu hộ không cộng dồn công nợ ban quản lý)
  - `provider_id`: Optional[int] (ID nhà cung cấp nếu là khoản thu hộ)
  - `cycle`: FeeCycle (Mặc định `MONTHLY`, hỗ trợ `QUARTERLY`, `YEARLY`)
  - `due_day`: Optional[int] (Hạn nộp từ 1 đến 31)
  - `description`: Optional[str] (Mô tả chi tiết)
* **Mã phản hồi HTTP:**
  - `201 Created`: Trả về schema `FeeType` của bản ghi vừa tạo.
  - `400 VALIDATION_ERROR`: Thiếu trường bắt buộc, sai kiểu, `due_day` ngoài phạm vi 1–31, thiếu `vehicle_type` khi tính theo xe.
  - `401 UNAUTHENTICATED`: Thiếu hoặc sai token.
  - `403 FORBIDDEN`: Không đúng vai trò `ADMIN` hoặc `ACCOUNTANT`.
  - `403 PASSWORD_CHANGE_REQUIRED`: Phải đổi mật khẩu lần đầu.
  - `409 DUPLICATE_FEE_CODE`: Trùng lặp mã khoản thu trên hệ thống.
  - `500 INTERNAL_SERVER_ERROR`: Lỗi hệ thống.

### 3.3. `PATCH /api/v1/fee-types/{id}` (Cập nhật thông tin khoản thu)
* **Operation ID:** `updateFeeType`
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Path Parameter:** `id`: int (ID khoản thu)
* **Request Body:** Schema `FeeTypeUpdate`
  - `name`: Optional[str]
  - `unit_label`: Optional[str]
  - `provider_id`: Optional[int]
  - `cycle`: Optional[FeeCycle]
  - `due_day`: Optional[int] (1–31)
  - `description`: Optional[str]
* **Mã phản hồi HTTP:**
  - `200 OK`: Trả về schema `FeeType` sau khi cập nhật.
  - `400 VALIDATION_ERROR`: Dữ liệu gửi lên sai định dạng, `due_day` sai miền giá trị.
  - `401 UNAUTHENTICATED`: Chưa xác thực hoặc token hết hạn.
  - `403 FORBIDDEN`: Sai vai trò.
  - `403 PASSWORD_CHANGE_REQUIRED`: Phải đổi mật khẩu lần đầu.
  - `404 NOT_FOUND`: Không tìm thấy khoản thu với ID tương ứng.
  - `500 INTERNAL_SERVER_ERROR`: Lỗi hệ thống.

---

## 4. QUẢN LÝ DỮ LIỆU & TÍNH TOÀN VẸN GIAO DỊCH (ACID & INVARIANTS)

1. **Nguyên tắc Cụm tối thiểu (Minimal Cluster Principle):**
   - Bảng `fee_types` là bảng thứ 9 thuộc cụm CSDL tối thiểu của Sprint 1 (`roles`, `users`, `audit_logs`, `backup_jobs`, `apartments`, `households`, `apartment_occupancies`, `residents`, `fee_types`).
   - Tách rời liên kết cứng với các bảng Sprint sau: `fee_rates`, `service_providers` được tham chiếu lỏng, tự động xử lý an toàn bằng fallback runtime nếu các bảng này chưa xuất hiện trong schema.
2. **Tính bất biến & Toàn vẹn tham chiếu:**
   - Cấm xóa vật lý (No hard delete): Danh mục khoản thu đã phát sinh dữ liệu không được xóa; chỉ chuyển trạng thái sang `INACTIVE`.
   - Bất biến phương pháp tính và mã định danh nhằm bảo đảm các kỳ hóa đơn lịch sử không bị sai lệch cách quy đổi.
3. **Nhật ký kiểm toán minh bạch (Audit Trail):**
   - Mọi thay đổi về cấu hình danh mục phí đều được tự động lưu vết tại bảng `audit_logs` với `action IN ('CREATE_FEE_TYPE', 'UPDATE_FEE_TYPE', 'DEACTIVATE_FEE')`.

---

## 5. MA TRẬN KẾT QUẢ KIỂM THỬ BLACK-BOX ĐỘC LẬP (TEST MATRIX)

Bộ kiểm thử được thiết kế độc lập bởi QA Engineer tại `backend/tests/test_us12_fee_catalog.py`:

| Nhóm kịch bản kiểm thử | Số lượng test cases | Trạng thái thực thi |
| :--- | :---: | :---: |
| **Xác thực & RBAC Guard** (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`, Token hết hạn, `PASSWORD_CHANGE_REQUIRED`) | **15** | **PASSED (15/15)** |
| **Kiểm tra dữ liệu đầu vào `POST /fee-types`** (Trường bắt buộc, sai Enum, `due_day` biên, `calc_method = PER_VEHICLE`) | **16** | **PASSED (16/16)** |
| **Luồng thành công & Xung đột mã `POST /fee-types`** (5 cách tính, các chu kỳ, `DUPLICATE_FEE_CODE`) | **14** | **PASSED (14/14)** |
| **Phân trang & Bộ lọc `GET /fee-types`** (Phân trang mặc định, nhiều trang, lọc `status`, lọc `fee_group`, lọc kết hợp, biên) | **16** | **PASSED (16/16)** |
| **Cập nhật & Bất biến `PATCH /fee-types/{id}`** (`404 NOT_FOUND`, cập nhật từng trường, biên `due_day`, bảo toàn `code` & `calc_method`) | **18** | **PASSED (18/18)** |
| **TỔNG CỘNG** | **79** | **100% PASSED (79/79)** |

* Toàn bộ test suite của toàn hệ thống (bao gồm các User Story trước đó: US-01, US-02, US-03, US-28, US-29, US-30, US-31, US-32, US-44 và US-12) đạt **1115 passed**, **0 failed**, **0 errors** trong thời gian $\le 75\text{s}$.
