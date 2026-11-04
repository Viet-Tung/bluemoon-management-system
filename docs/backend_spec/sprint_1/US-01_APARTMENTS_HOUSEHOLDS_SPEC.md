# ĐẶC TẢ CHI TIẾT USER STORY: US-01 (QUẢN LÝ CĂN HỘ & HỘ GIA ĐÌNH)
> **Mã Story:** `US-01` | **Feature:** `F-01.1` Hồ sơ căn hộ & `F-01.2` Hồ sơ hộ gia đình | **WBS:** `2.2.1`, `2.2.2`  
> **Story Points:** `5 SP` | **Độ ưu tiên:** `Must (M)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-01-backend-apartments-households`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.1, II.2), `docs/API_CONTRACT.md` (Chương 3.4, 3.5), `docs/openapi.yaml` (các path `/apartments*`, `/households*`), `database/01_schema.sql` (bảng `apartments`, `households`, `apartment_occupancies`, `residents`, `users`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As an** Quản trị viên hệ thống (Admin) hoặc Kế toán (Accountant),  
> **I want** khai báo, quản lý danh sách căn hộ vật lý và hồ sơ hộ gia đình cư trú,  
> **So that** tòa nhà BlueMoon có cơ sở dữ liệu nền tảng chuẩn xác về mặt bằng và cư dân phục vụ thu phí và quản trị vận hành.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-01.1` (Căn hộ có mã không trùng lặp, diện tích > 0 m2):**
  - Mã căn hộ `code` là duy nhất trên toàn hệ thống (`UNIQUE`, kiểm tra case-insensitive).
  - Tầng `floor >= 0` (hỗ trợ tầng trệt và các tầng cao).
  - Diện tích `area_m2 > 0` (ràng buộc `exclusiveMinimum: true` và `CHECK (area_m2 > 0)`).
  - Cấm xóa vật lý căn hộ (No hard delete); khi căn hộ ngưng sử dụng chỉ chuyển trạng thái sang `INACTIVE` (`PATCH /api/v1/apartments/{id}`).
* **`AC-01.2` (Tách biệt độc lập 2 thực thể Căn hộ và Hộ gia đình - `T-01`, `T-02`):**
  - Căn hộ vật lý (`apartments`) độc lập với Hộ gia đình (`households`). Một căn hộ có thể chưa có hộ nào cư trú; một hộ gia đình mới tạo có thể chưa nhận căn hộ ngay (`apartment_id` nullable).
  - Mối quan hệ cư trú theo thời gian được quản lý qua bảng trung gian `apartment_occupancies`.
* **`AC-30.2` (Tự động cấp tài khoản cư dân mặc định khi tạo hộ mới - `D-12`):**
  - Khi tạo hộ mới (`POST /api/v1/households`), hệ thống tự động sinh 1 tài khoản cư dân duy nhất cho hộ (`Role = RESIDENT`, `is_active = True`, `must_change_password = True`).
  - Mật khẩu tạm ngẫu nhiên an toàn đạt chuẩn `AC-29.1` (độ dài $\ge 12$, gồm chữ hoa, chữ thường, số, ký tự đặc biệt), băm `bcrypt` rounds $\ge 12$ (`AC-44.1`).
  - Phản hồi HTTP `201 Created` trả về schema `HouseholdCreated` chứa thông tin hộ và `resident_account` (`username`, `temporary_password`).
* **`AC-46.1` (Tính nguyên tử ACID):**
  - Toàn bộ thao tác tạo hộ gia đình, liên kết căn hộ (nếu có), tạo nhân khẩu chủ hộ (nếu có), và cấp tài khoản cư dân phải nằm trong **duy nhất 1 transaction CSDL**, tự động rollback 100% nếu xảy ra bất kỳ lỗi xung đột hoặc vi phạm nào.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── models/
│   ├── __init__.py              # Export Apartment, Household, ApartmentOccupancy, Resident
│   └── property.py              # 4 thực thể CSDL (apartments, households, apartment_occupancies, residents)
├── schemas/
│   ├── __init__.py              # Export DTOs cho apartments và households
│   ├── apartment.py             # ApartmentCreate, ApartmentUpdate, Apartment, ApartmentPage
│   └── household.py             # ResidentAccount, ResidentCreate, HouseholdCreate, HouseholdUpdate, Household, HouseholdCreated, HouseholdPage
├── routers/
│   ├── __init__.py              # Export apartments_router, households_router
│   ├── apartments.py            # 4 endpoints: GET/POST /apartments, GET/PATCH /apartments/{id}
│   └── households.py            # 3 endpoints: GET/POST /households, GET /households/{id}
└── main.py                      # Đăng ký /api/v1/apartments và /api/v1/households
```

---

## 3. CHI TIẾT 7 HTTP REST ENDPOINTS (STRICT API CONTRACT)

### 3.1. Phân hệ Căn hộ (Apartments - 4 Endpoints)

#### 1. `GET /api/v1/apartments` (Danh sách căn hộ)
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Query Parameters:**
  - `page`: int (default: 1, $\ge 1$)
  - `page_size`: int (default: 20, $1 \dots 100$)
  - `floor`: Optional[int] (Lọc theo tầng)
  - `status`: Optional[str] (`ACTIVE`, `INACTIVE`)
* **Phản hồi:** `200 OK` (`ApartmentPage`), `400 VALIDATION_ERROR`, `401 UNAUTHENTICATED`, `403 FORBIDDEN`

#### 2. `POST /api/v1/apartments` (Tạo căn hộ mới)
* **Quyền gọi (Roles):** `ADMIN`
* **Request Body:** `ApartmentCreate` (`code`, `floor >= 0`, `area_m2 > 0`, `note`)
* **Phản hồi:** `201 Created` (`Apartment`), `400 VALIDATION_ERROR`, `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `409 DUPLICATE_APARTMENT_CODE`

#### 3. `GET /api/v1/apartments/{id}` (Chi tiết căn hộ)
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Path Parameter:** `id`: int
* **Phản hồi:** `200 OK` (`Apartment`), `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `404 NOT_FOUND`

#### 4. `PATCH /api/v1/apartments/{id}` (Cập nhật căn hộ)
* **Quyền gọi (Roles):** `ADMIN`
* **Path Parameter:** `id`: int
* **Request Body:** `ApartmentUpdate` (`floor`, `area_m2`, `status`, `note`)
* **Phản hồi:** `200 OK` (`Apartment`), `400 VALIDATION_ERROR`, `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `404 NOT_FOUND`

---

### 3.2. Phân hệ Hộ gia đình (Households - 3 Endpoints)

#### 5. `GET /api/v1/households` (Danh sách hộ gia đình)
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Query Parameters:**
  - `page`: int (default: 1, $\ge 1$)
  - `page_size`: int (default: 20, $1 \dots 100$)
  - `q`: Optional[str] (Tìm kiếm theo mã hộ, tên chủ hộ, SĐT)
  - `status`: Optional[str] (`ACTIVE`, `INACTIVE`)
* **Phản hồi:** `200 OK` (`HouseholdPage`), `400 VALIDATION_ERROR`, `401 UNAUTHENTICATED`, `403 FORBIDDEN`

#### 6. `POST /api/v1/households` (Tạo hộ gia đình mới & Tự sinh tài khoản cư dân)
* **Quyền gọi (Roles):** `ADMIN`
* **Request Body:** `HouseholdCreate` (`household_code`, `apartment_id`, `occupancy_start_date`, `contact_phone`, `contact_email`, `note`, `head`)
* **Xử lý nghiệp vụ:**
  - Kiểm tra trùng lặp mã hộ $\rightarrow$ `409 DUPLICATE_HOUSEHOLD_CODE`.
  - Nếu có `apartment_id`: kiểm tra căn hộ tồn tại $\rightarrow$ `404 NOT_FOUND`; kiểm tra đang có người ở $\rightarrow$ `409 APARTMENT_OCCUPIED`.
  - Nếu có `head.cccd`: kiểm tra trùng CCCD toàn hệ thống $\rightarrow$ `409 DUPLICATE_CCCD`.
  - Tạo `Household`, gắn `ApartmentOccupancy` (nếu có), tạo `Resident` chủ hộ (nếu có).
  - Tự động sinh `User` cư dân với vai trò `RESIDENT`, gắn `household_id`, mật khẩu tạm an toàn $\ge 12$ ký tự băm `bcrypt`.
* **Phản hồi:** `201 Created` (`HouseholdCreated` kèm `resident_account`), `400 VALIDATION_ERROR`, `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `404 NOT_FOUND`, `409` (conflict code)

#### 7. `GET /api/v1/households/{id}` (Chi tiết hộ gia đình)
* **Quyền gọi (Roles):** `ADMIN`, `ACCOUNTANT`
* **Path Parameter:** `id`: int
* **Phản hồi:** `200 OK` (`Household`), `401 UNAUTHENTICATED`, `403 FORBIDDEN`, `404 NOT_FOUND`

---

## 4. MA TRẬN MÃ LỖI NGHIỆP VỤ (ERROR CODES)

| HTTP Status | Mã `code` | Tình huống áp dụng | Schema phản hồi |
| :---: | :--- | :--- | :--- |
| **400** | `VALIDATION_ERROR` | Thiếu trường bắt buộc, diện tích $\le 0$, tầng $< 0$, status không hợp lệ, email sai format, cccd sai format. | `Error` |
| **401** | `UNAUTHENTICATED` | Thiếu Authorization Bearer header, token sai hoặc đã hết hạn. | `Error` |
| **403** | `FORBIDDEN` | Sai vai trò (ví dụ: `ACCOUNTANT` cố gọi POST/PATCH căn hộ hoặc POST hộ; `TREASURER`, `RESIDENT` bị chặn). | `Error` |
| **403** | `PASSWORD_CHANGE_REQUIRED` | Tài khoản có cờ `must_change_password = True` gọi API ngoài đổi mật khẩu. | `Error` |
| **404** | `NOT_FOUND` | Không tìm thấy ID căn hộ hoặc hộ gia đình. | `Error` |
| **409** | `DUPLICATE_APARTMENT_CODE` | Trùng mã căn hộ khi tạo mới. | `Error` |
| **409** | `DUPLICATE_HOUSEHOLD_CODE` | Trùng mã hộ gia đình khi tạo mới. | `Error` |
| **409** | `APARTMENT_OCCUPIED` | Căn hộ được gán đang có hộ gia đình khác cư trú (`end_date IS NULL`). | `Error` |
| **409** | `DUPLICATE_CCCD` | Số CCCD/CMND của chủ hộ đã tồn tại trên hệ thống. | `Error` |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi máy chủ hoặc lỗi giao dịch CSDL không mong muốn. | `Error` |

---

## 5. KẾT QUẢ KIỂM THỬ BLACK-BOX ĐỘC LẬP (TV2 - NGUYỄN VIỆT TÙNG)

* **Tệp test:** `backend/tests/test_us01_apartments_households.py`
* **Số lượng test cases:** **122 test cases** (100% Pass rate)
* **Phạm vi bao phủ:**
  - 24 tests cho `POST /api/v1/apartments` (Happy paths, floor=0, area thập phân, validation, duplicate code, RBAC).
  - 17 tests cho `GET /api/v1/apartments` (Phân trang, lọc tầng, lọc status, page_size boundaries, RBAC).
  - 8 tests cho `GET /api/v1/apartments/{id}` (Chi tiết, 404 ID không tồn tại, path routing, RBAC).
  - 15 tests cho `PATCH /api/v1/apartments/{id}` (Sửa diện tích, tầng, status INACTIVE - soft delete, 404, validation, RBAC).
  - 28 tests cho `POST /api/v1/households` (Tạo hộ độc lập, gán căn hộ, gán chủ hộ, tự sinh tài khoản cư dân D-12, trùng mã hộ, căn hộ đã có người ở, trùng CCCD, validation email/date/gender/cccd, RBAC).
  - 18 tests cho `GET /api/v1/households` (Phân trang, tìm kiếm q theo mã hộ, SĐT, lọc status, RBAC).
  - 10 tests cho `GET /api/v1/households/{id}` (Chi tiết hộ, thông tin chủ hộ, thông tin căn hộ liên kết, 404, RBAC).
  - 2 tests miền nghiệp vụ bất biến: Tách biệt thực thể (`AC-01.2`) và Không xóa vật lý (`No hard delete`).
* **Tổng test suite toàn dự án:** **850 passed** (728 tests cũ + 122 tests US-01).
