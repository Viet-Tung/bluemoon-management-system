# ĐẶC TẢ KỸ THUẬT BACKEND SPRINT 1 (BACKEND SPECIFICATION - SPRINT 1)
> **Dự án:** Quản lý & Thu phí Chung Cư BlueMoon  
> **Phạm vi:** 12 User Stories — 40 Story Points (Tuần 3 – Tuần 5)  
> **Căn cứ gốc (SSOT):** `docs/Plan.pdf`, `database/01_schema.sql`, `docs/API_CONTRACT.md`  
> **Mục đích:** Tệp đặc tả kỹ thuật cô đọng, truy cập siêu nhanh cho Backend Developers (TV1: Lê Trường Giang, TV2: Nguyễn Việt Tùng) khi phát triển Sprint 1 mà không phải tra cứu các file tài liệu lớn (>100KB).

---

## 1. TIÊU CHUẨN KỸ THUẬT & CẤU HÌNH (TECH STACK BASELINE)

* **Runtime:** Python 3.10+ (Môi trường phát triển TV1: Python 3.14.2 tại `backend/venv`).
* **Web Framework:** FastAPI 0.162+ (hỗ trợ ASGI async, tự động sinh OpenAPI schema tại `/docs`).
* **ORM & Database Driver:** SQLAlchemy 2.0 (Declarative Base) + `psycopg` (version 3.3+ binary).
* **Bảo mật:** `bcrypt 5.0+` (rounds $\ge 12$), `PyJWT 2.15+` (thuật toán HS256, access token hết hạn 8 giờ).
* **Kiểm thử tự động:** `pytest`, `pytest-asyncio`, `httpx` (SQLite in-memory with `StaticPool`).
* **Định dạng dữ liệu:** JSON UTF-8, toàn bộ key định dạng **`snake_case`**. Tiền tệ luôn là số nguyên **`int64`** (VNĐ).

---

## 2. CHUẨN XỬ LÝ LỖI DÙNG CHUNG (ERROR HANDLING SPEC)

Mọi HTTP Error response từ hệ thống bắt buộc tuân theo Schema chuẩn `Error` (tham chiếu `docs/API_CONTRACT.md` mục 1.2):
```json
{
  "code": "ERROR_CODE_STRING",
  "message": "Mô tả chi tiết nguyên nhân lỗi cho client",
  "details": [
    {
      "field": "tên_trường_lỗi",
      "message": "Lý do không hợp lệ"
    }
  ]
}
```

### Bảng mã lỗi Sprint 1 (Strict snake_case):
| HTTP Status | Mã `code` | Trường hợp áp dụng trong Sprint 1 |
| :---: | :--- | :--- |
| **400** | `VALIDATION_ERROR` | Dữ liệu gửi lên sai kiểu, thiếu trường bắt buộc, diện tích $\le 0$. |
| **400** | `WRONG_OLD_PASSWORD` | Sai mật khẩu cũ khi gọi `POST /auth/change-password` (`US-29`). |
| **401** | `UNAUTHENTICATED` | Thiếu token, token không hợp lệ hoặc đã hết hạn. |
| **401** | `INVALID_CREDENTIALS` | Sai username hoặc password khi đăng nhập (`US-28`). |
| **403** | `FORBIDDEN` | Sai vai trò theo ma trận RBAC Guard (`US-31`). |
| **403** | `PASSWORD_CHANGE_REQUIRED` | Tài khoản có `must_change_password = true` gọi API khác ngoài đổi mật khẩu. |
| **404** | `NOT_FOUND` | Không tìm thấy ID bản ghi; hoặc Cư dân gọi sang hộ khác (Chống IDOR - `AC-44.2`). |
| **409** | `DUPLICATE_USERNAME` | Trùng username khi tạo tài khoản nhân sự (`US-30`). |
| **409** | `DUPLICATE_APARTMENT_CODE` | Trùng mã căn hộ khi tạo căn hộ (`US-01`). |
| **409** | `DUPLICATE_HOUSEHOLD_CODE` | Trùng mã hộ khi tạo hộ mới (`US-01`). |
| **409** | `DUPLICATE_FEE_CODE` | Trùng mã khoản thu khi tạo mới (`US-12`). |
| **409** | `APARTMENT_OCCUPIED` | Căn hộ đang có hộ gia đình khác cư trú (`US-01`, `US-03`). |
| **409** | `HOUSEHOLD_HAS_NO_APARTMENT`| Hộ không giữ căn hộ nào nên không thể chuyển nhượng (`US-03`). |
| **409** | `DEBT_NOT_SETTLED` | Hộ còn nợ đọng, không cho phép đổi chủ hộ, chuyển nhượng hoặc đóng hộ (`US-02`, `US-03`). |
| **409** | `CANNOT_LOCK_SELF` | Admin không được tự khóa tài khoản của chính mình (`US-30`). |
| **409** | `CANNOT_CHANGE_OWN_ROLE` | Admin không được tự đổi vai trò của chính mình (`US-31`). |
| **409** | `FEE_TYPE_IN_USE` | Khoản thu đã phát sinh dữ liệu, cấm sửa code hoặc cách tính (`US-12`). |
| **423** | `ACCOUNT_LOCKED` | Nhập sai mật khẩu 5 lần liên tiếp, tài khoản bị tạm khóa 15 phút (`AC-28.2`). |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi máy chủ hoặc lỗi giao dịch CSDL không mong muốn. |

---

## 3. CẤU TRÚC DỮ LIỆU CỤM TỐI THIỂU (9 BẢNG SPRINT 1)

Khớp 100% định nghĩa tại `database/01_schema.sql`:

### 3.1. Cụm Identity & System (4 bảng)
1. **`roles`**:
   - `id`: smallint (Identity PK)
   - `code`: text UNIQUE (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`)
   - `name`: text
   - `description`: text (Nullable)
2. **`users`**:
   - `id`: bigint (Identity PK)
   - `username`: text (Unique index trên `lower(username)`)
   - `password_hash`: text (Bcrypt hash)
   - `full_name`: text
   - `email`: text (Nullable)
   - `phone`: text (Nullable)
   - `role_id`: smallint (FK -> `roles.id`)
   - `household_id`: bigint (Nullable, FK -> `households.id`, Unique index where not null: mỗi hộ chỉ 1 tài khoản cư dân - `D-12`)
   - `is_active`: boolean (Default: `true`)
   - `must_change_password`: boolean (Default: `true`)
   - `failed_login_count`: smallint (Default: `0`)
   - `locked_until`: timestamptz (Nullable)
   - `last_login_at`: timestamptz (Nullable)
   - `password_changed_at`: timestamptz (Nullable)
   - `created_at`, `updated_at`: timestamptz
3. **`audit_logs`** *(Bất biến, cấm sửa/xóa)*:
   - `id`: bigint (Identity PK)
   - `user_id`: bigint (Nullable, FK -> `users.id`)
   - `action`: text (`CHANGE_HEAD`, `TRANSFER_APARTMENT`, `DEACTIVATE_FEE`, `LOCK_USER`, `ACCESS_DENIED`,...)
   - `entity_type`: text (`USER`, `HOUSEHOLD`, `APARTMENT`, `FEE_TYPE`)
   - `entity_id`: text (Nullable)
   - `old_value`: jsonb (Nullable)
   - `new_value`: jsonb (Nullable)
   - `reason`: text (Nullable)
   - `ip_address`: inet (Nullable)
   - `user_agent`: text (Nullable)
   - `created_at`: timestamptz
4. **`backup_jobs`**:
   - `id`: bigint (Identity PK)
   - `status`: text (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`)
   - `requested_by`: bigint (Nullable, FK -> `users.id`)
   - `requested_at`: timestamptz
   - `finished_at`: timestamptz (Nullable)
   - `size_bytes`: bigint (Nullable)
   - `file_path`: text (Nullable)
   - `error_message`: text (Nullable)

### 3.2. Cụm Property & Occupancy (4 bảng)
5. **`apartments`** (Căn hộ vật lý - `T-01`):
   - `id`: bigint (Identity PK)
   - `code`: text UNIQUE (VD: `P.1002`)
   - `floor`: smallint (CHECK: `floor >= 0`)
   - `area_m2`: numeric(8,2) (CHECK: `area_m2 > 0`)
   - `status`: text (CHECK: `status IN ('ACTIVE','INACTIVE')`, Default: `ACTIVE`)
   - `note`: text (Nullable)
6. **`households`** (Hộ gia đình - `T-02`):
   - `id`: bigint (Identity PK)
   - `household_code`: text UNIQUE (VD: `HO-1002`)
   - `status`: text (CHECK: `status IN ('ACTIVE','INACTIVE')`, Default: `ACTIVE`)
   - `contact_phone`: text (Nullable)
   - `contact_email`: text (Nullable)
   - `note`: text (Nullable)
7. **`apartment_occupancies`** (Liên kết Căn hộ $\leftrightarrow$ Hộ theo thời gian):
   - `id`: bigint (Identity PK)
   - `apartment_id`: bigint (FK -> `apartments.id`)
   - `household_id`: bigint (FK -> `households.id`)
   - `start_date`: date
   - `end_date`: date (Nullable: `NULL` = đang cư trú)
   - `end_reason`: text (Nullable)
   - Ràng buộc: `CHECK (end_date IS NULL OR end_date >= start_date)`
   - Chỉ mục loại trừ: `EXCLUDE USING gist (apartment_id WITH =, daterange(start_date, end_date, '[]') WITH &&)`
8. **`residents`** (Nhân khẩu thường trú trong hộ):
   - `id`: bigint (Identity PK)
   - `household_id`: bigint (FK -> `households.id`)
   - `full_name`: text
   - `date_of_birth`: date
   - `gender`: text (CHECK: `gender IN ('NAM','NU','KHAC')`)
   - `cccd`: text (Nullable nếu $< 14$ tuổi, regex `^[0-9]{9,12}$`)
   - `is_head`: boolean (Default: `false`)
   - `residence_status`: text (`THUONG_TRU`, `TAM_VANG`, `DA_CHUYEN_DI`, `DA_QUA_DOI`)
   - `is_deleted`: boolean (Default: `false` - No hard delete)
   - Unique Index: Mỗi hộ chỉ có 1 chủ hộ đang hoạt động (`ux_residents_one_head`).

### 3.3. Cụm Fee Catalog (1 bảng)
9. **`fee_types`** (Khoản thu bắt buộc):
   - `id`: bigint (Identity PK)
   - `code`: text UNIQUE (VD: `PQL`, `P_XE_MAY`)
   - `name`: text
   - `fee_group`: text (`MANAGEMENT`, `PARKING`, `UTILITY`, `OTHER`)
   - `calc_method`: text (`PER_M2`, `PER_HOUSEHOLD`, `PER_PERSON`, `PER_VEHICLE`, `METERED`)
   - `unit_label`: text (`m2`, `hộ`, `người`, `xe`, `kWh`, `m3`)
   - `cycle`: text (`MONTHLY`, `QUARTERLY`, `YEARLY`, Default: `MONTHLY`)
   - `due_day`: smallint (Nullable: 1 - 31)
   - `status`: text (`ACTIVE`, `INACTIVE`, Default: `ACTIVE` - AC-13.1 cấm hard delete)

---

## 4. MA TRẬN 32 ENDPOINTS SPRINT 1 THEO API CONTRACT

Trích xuất trực tiếp từ `docs/API_CONTRACT.md`:

### 4.1. Phân hệ Auth (4 endpoints)
* `POST /auth/login` | Roles: **public** | Status: `200`, `400`, `401`, `423` (`ACCOUNT_LOCKED`) | US-28
* `POST /auth/logout` | Roles: **all** | Status: `204`, `401`, `403` | US-28
* `GET /auth/me` | Roles: **all** | Status: `200`, `401`, `403` | US-28
* `POST /auth/change-password` | Roles: **all** (kể cả khi `PASSWORD_CHANGE_REQUIRED`) | Status: `204`, `400` (`WRONG_OLD_PASSWORD`), `401` | US-29

### 4.2. Phân hệ Users (9 endpoints)
* `GET /roles` | Roles: **ADMIN** | Status: `200` (List roles) | US-31
* `GET /users` | Roles: **ADMIN** | Query: `page`, `page_size`, `q`, `role`, `is_active` | Status: `200` (`UserPage`) | US-30
* `POST /users` | Roles: **ADMIN** | Body: `UserCreate` | Status: `201` (`UserWithTempPassword`), `409` (`DUPLICATE_USERNAME`) | US-30
* `GET /users/{userId}` | Roles: **ADMIN** | Status: `200`, `404` | US-30
* `PATCH /users/{userId}` | Roles: **ADMIN** | Body: `UserUpdate` | Status: `200`, `404` | US-30
* `PUT /users/{userId}/role` | Roles: **ADMIN** | Body: `UserRoleUpdate` | Status: `200`, `409` (`CANNOT_CHANGE_OWN_ROLE`) | US-31
* `POST /users/{userId}/lock` | Roles: **ADMIN** | Status: `200`, `409` (`CANNOT_LOCK_SELF`) | US-30
* `POST /users/{userId}/unlock` | Roles: **ADMIN** | Status: `200`, `404` | US-30
* `POST /users/{userId}/reset-password` | Roles: **ADMIN** | Status: `200` (`TempPassword`) | US-30, US-29

### 4.3. Phân hệ System (3 endpoints)
* `GET /audit-logs` | Roles: **ADMIN** | Query: `page`, `page_size`, `user_id`, `action`, `entity_type`, `from`, `to` | Status: `200` (`AuditLogPage`) | US-32
* `POST /system/backups` | Roles: **ADMIN** | Status: `202` Accepted (`BackupJob`) | US-45
* `GET /system/backups` | Roles: **ADMIN** | Query: `page`, `page_size` | Status: `200` (`BackupJobPage`) | US-45

### 4.4. Phân hệ Apartments (4 endpoints)
* `GET /apartments` | Roles: **ADMIN, ACCOUNTANT** | Query: `page`, `page_size`, `floor`, `status`, `q` | Status: `200` (`ApartmentPage`) | US-01
* `POST /apartments` | Roles: **ADMIN** | Body: `ApartmentCreate` (`code`, `floor`, `area_m2 > 0`) | Status: `201`, `409` (`DUPLICATE_APARTMENT_CODE`) | US-01
* `GET /apartments/{id}` | Roles: **ADMIN, ACCOUNTANT** | Status: `200`, `404` | US-01
* `PATCH /apartments/{id}` | Roles: **ADMIN** | Body: `ApartmentUpdate` | Status: `200`, `404` | US-01

### 4.5. Phân hệ Households (8 endpoints)
* `GET /households` | Roles: **ADMIN, ACCOUNTANT** | Query: `page`, `page_size`, `status`, `q` | Status: `200` (`HouseholdPage`) | US-01
* `POST /households` | Roles: **ADMIN** | Body: `HouseholdCreate` (kèm auto tạo tài khoản cư dân `D-12`) | Status: `201` (`HouseholdCreated`), `409` (`DUPLICATE_HOUSEHOLD_CODE`, `APARTMENT_OCCUPIED`) | US-01, US-30
* `GET /households/{id}` | Roles: **ADMIN, ACCOUNTANT** | Status: `200` (`Household`), `404` | US-01
* `PATCH /households/{id}` | Roles: **ADMIN** | Body: `HouseholdUpdate` | Status: `200`, `404` | US-02
* `POST /households/{id}/deactivate` | Roles: **ADMIN** | Body: `HouseholdDeactivate` (`reason`) | Status: `200`, `409` (`DEBT_NOT_SETTLED`) | US-02
* `POST /households/{id}/transfer` | Roles: **ADMIN** | Body: `HouseholdTransferRequest` | Status: `200`, `409` (`DEBT_NOT_SETTLED`, `APARTMENT_OCCUPIED`, `HOUSEHOLD_HAS_NO_APARTMENT`) | US-03
* `PUT /households/{id}/head` | Roles: **ADMIN** | Body: `HouseholdChangeHead` (Ghi Audit Log `CHANGE_HEAD`) | Status: `200`, `409` (`DEBT_NOT_SETTLED`) | US-02
* `GET /households/{id}/credit` | Roles: **ADMIN, ACCOUNTANT, TREASURER** | Status: `200` (`HouseholdCredit`) | US-19

### 4.6. Phân hệ Fee Catalog (4 endpoints)
* `GET /fee-types` | Roles: **ADMIN, ACCOUNTANT** | Query: `page`, `page_size`, `fee_group`, `status` | Status: `200` (`FeeTypePage`) | US-12
* `POST /fee-types` | Roles: **ADMIN, ACCOUNTANT** | Body: `FeeTypeCreate` | Status: `201`, `409` (`DUPLICATE_FEE_CODE`) | US-12
* `PATCH /fee-types/{id}` | Roles: **ADMIN, ACCOUNTANT** | Body: `FeeTypeUpdate` | Status: `200`, `409` (`FEE_TYPE_IN_USE`) | US-12
* `POST /fee-types/{id}/deactivate` | Roles: **ADMIN, ACCOUNTANT** | Status: `200` (Đổi `INACTIVE`, cấm DELETE) | US-13

---

## 5. BẢNG CHECKLIST ACCEPTANCE CRITERIA (DOD SPRINT 1)

* [x] `AC-44.1`: Mật khẩu lưu dạng băm `bcrypt` rounds $\ge 12$.
* [x] `AC-44.2`: Chặn lỗi IDOR khi Cư dân truy cập chéo ID hộ (trả về `404 NOT_FOUND`).
* [ ] `AC-45.1`: Lập lịch tự động sao lưu CSDL lúc 02:00 sáng, RTO $\le 2\text{h}$, lưu 30 ngày.
* [x] `AC-46.1`: Đảm bảo tính nguyên tử ACID, tự động rollback khi gặp lỗi giữa chừng.
* [x] `AC-28.1`: Đăng nhập đúng trả về JWT token và thông tin user khớp vai trò.
* [x] `AC-28.2`: Nhập sai mật khẩu 5 lần liên tiếp tự động khóa tài khoản 15 phút.
* [x] `AC-29.1`: Đổi mật khẩu mới độ dài $\ge 8$ ký tự, bắt buộc đổi trong lần đầu đăng nhập.
* [x] `AC-30.1`: Tạo mới, khóa, mở khóa tài khoản nhân sự có hiệu lực tức thì.
* [x] `AC-30.2`: Tự động sinh tài khoản Cư dân mặc định khi tạo Hộ gia đình mới.
* [x] `AC-31.1`: Middleware RBAC Guard kiểm tra quyền trên mọi API endpoint; gán/thu hồi role có hiệu lực ngay.
* [x] `AC-32.1`: Lưu rõ User thực hiện, Thời gian, Hành động, Giá trị cũ $\rightarrow$ Giá trị mới; Tuyệt đối chặn xóa/sửa bảng `audit_logs`.
* [x] `AC-01.1`: Căn hộ có mã không trùng lặp, diện tích $> 0\text{ m}^2$.
* [x] `AC-01.2`: Tách biệt độc lập 2 thực thể Căn hộ và Hộ gia đình (`T-01`, `T-02`).
* [ ] `AC-02.1`: Kiểm tra tất toán công nợ trước khi đổi chủ hộ; ghi Audit Log `CHANGE_HEAD`.
* [ ] `AC-03.1`: Chuyển nhượng căn hộ: đóng hồ sơ hộ cũ, gắn hộ mới, bảo toàn 100% lịch sử hóa đơn.
* [ ] `AC-12.1`: Khai báo mã, tên, fee_group, calc_method, đơn vị tính của khoản thu.
* [ ] `AC-13.1`: Cấm xóa vật lý khoản thu (No hard delete); chỉ chuyển trạng thái sang `INACTIVE`.

---

## 6. NGUYÊN TẮC KIẾN TRÚC & PHÁT TRIỂN (ENGINEERING GUARDRAILS)

1. **Nguyên lý Cụm tối thiểu (Minimal Cluster Principle - 9 bảng):**
   * Trong phạm vi Sprint 1, Backend chỉ khởi tạo và tương tác với đúng 9 bảng CSDL cốt lõi (`roles`, `users`, `audit_logs`, `backup_jobs`, `apartments`, `households`, `apartment_occupancies`, `residents`, `fee_types`).
   * 19 bảng thuộc các sprint tiếp theo (kỳ thu, hóa đơn, thanh toán, xe cộ,...) không được khai báo vội vàng để tránh nợ kỹ thuật (technical debt) và dependency chéo.
2. **Phân rã liên kết lỏng (Loose Coupling):**
   * Các quan hệ hướng tới các bảng tương lai (ví dụ: `apartments` $\rightarrow$ `vehicles`, `households` $\rightarrow$ `invoices`) tuyệt đối không khai báo Foreign Key cứng tại tầng SQLAlchemy models trong Sprint 1. Sẽ mở rộng JIT (Just-In-Time) khi bước vào các Sprint tương ứng.
3. **Môi trường Test độc lập & ACID Snapshot:**
   * Bộ kiểm thử `pytest` thực thi trên SQLite in-memory (`StaticPool`), cô lập hoàn toàn với PostgreSQL production.
   * Mỗi test case được bao bọc bởi transaction rollback (`SAVEPOINT`), đảm bảo tính idempotent, không để lại dữ liệu rác và thời gian thực thi $< 2\text{s}$.
