# ĐẶC TẢ CHI TIẾT USER STORY: US-30 (QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG)
> **Mã Story:** `US-30` | **Feature:** `F-08.2` Quản lý tài khoản & Phân quyền | **WBS:** `2.1.3`  
> **Story Points:** `4 SP` | **Độ ưu tiên:** `Must (M)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-30-backend-user-management`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.3), `docs/API_CONTRACT.md` (Chương 2.2), `docs/openapi.yaml` (các path `/users*`), `database/01_schema.sql` (bảng `users`, `roles`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As an** Quản trị viên hệ thống (Admin),  
> **I want** xem danh sách, tạo mới, xem chi tiết, cập nhật thông tin, khóa, mở khóa tài khoản và cấp lại mật khẩu tạm cho nhân sự tòa nhà,  
> **So that** tôi chủ động điều hành quyền truy cập hệ thống, quản lý vòng đời tài khoản và đảm bảo an ninh vận hành tòa nhà BlueMoon.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-30.1` (Tạo mới, khóa, mở khóa tài khoản nhân sự có hiệu lực tức thì):**
  - **Phân quyền bắt buộc:** Toàn bộ 7 endpoint thuộc phân hệ quản lý người dùng yêu cầu quyền `ADMIN` thông qua RBAC middleware (`require_roles("ADMIN")`). Các vai trò khác (`ACCOUNTANT`, `TREASURER`, `RESIDENT`) bị chặn với HTTP `403 FORBIDDEN` và tự động ghi nhận nhật ký kiểm toán `ACCESS_DENIED`.
  - **Tạo tài khoản nhân sự (`POST /api/v1/users`):**
    * Chỉ tạo tài khoản cho các vai trò nhân sự (`ADMIN`, `ACCOUNTANT`, `TREASURER`). Nghiêm cấm tạo thủ công tài khoản vai trò `RESIDENT` (trả về HTTP `400 VALIDATION_ERROR` vì tài khoản cư dân được hệ thống tự sinh khi tạo hộ gia đình theo nguyên tắc `D-12`).
    * Kiểm tra trùng lặp `username` không phân biệt hoa thường (`lower(username)`). Nếu đã tồn tại $\rightarrow$ Trả về HTTP `409 Conflict` với mã lỗi `DUPLICATE_USERNAME`.
    * Tự động sinh mật khẩu tạm ngẫu nhiên an toàn (`secrets`) đạt chuẩn `AC-29.1` (độ dài $\ge 12$, chứa ít nhất 1 chữ hoa, 1 chữ thường, 1 số, 1 ký tự đặc biệt).
    * Băm mật khẩu bằng `bcrypt` rounds $\ge 12$ (`AC-44.1`).
    * Đặt cờ `must_change_password = True`, `is_active = True`.
    * Trả về HTTP `201 Created` kèm mật khẩu tạm dạng plaintext (`temporary_password` và alias `temp_password`) để Admin bàn giao.
  - **Khóa tài khoản (`POST /api/v1/users/{userId}/lock`):**
    * Khóa tài khoản tức thì (`is_active = False`).
    * Ràng buộc bất biến: Cấm Admin tự khóa chính mình $\rightarrow$ Trả về HTTP `409 Conflict` với mã lỗi `CANNOT_LOCK_SELF`.
    * Tự động ghi nhận `AuditLog` với `action="LOCK_USER"`.
  - **Mở khóa tài khoản (`POST /api/v1/users/{userId}/unlock`):**
    * Mở khóa tài khoản tức thì (`is_active = True`).
    * Reset số lần đăng nhập sai `failed_login_count = 0` và xóa hạn khóa tạm `locked_until = None`.
    * Tự động ghi nhận `AuditLog` với `action="UNLOCK_USER"`.
  - **Cấp lại mật khẩu tạm (`POST /api/v1/users/{userId}/reset-password`):**
    * Sinh mật khẩu tạm mới đạt chuẩn `AC-29.1`, băm `bcrypt` rounds $\ge 12$.
    * Đặt cờ `must_change_password = True`, reset `failed_login_count = 0`, `locked_until = None`.
    * Tự động ghi nhận `AuditLog` với `action="RESET_PASSWORD"`.
    * Trả về HTTP `200 OK` kèm mật khẩu tạm plaintext (`temporary_password`).
  - **Xem chi tiết & Cập nhật (`GET`, `PATCH /api/v1/users/{userId}`):**
    * Trả về thông tin chi tiết hoặc cập nhật `full_name`, `email`, `phone`, `is_active`.
    * Nếu không tìm thấy người dùng $\rightarrow$ Trả về HTTP `404 Not Found` với mã lỗi `USER_NOT_FOUND`.
  - **Danh sách người dùng (`GET /api/v1/users`):**
    * Phân trang chuẩn `PageMeta`: `page` (default 1, $\ge 1$), `page_size` (default 20, $1 \dots 100$).
    * Hỗ trợ tìm kiếm từ khóa `q` (tìm kiếm partial, case-insensitive trên `username` hoặc `full_name`).
    * Hỗ trợ lọc theo mã vai trò `role` (`ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`) và trạng thái `is_active`.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── routers/
│   ├── __init__.py              # Export users_router
│   └── users.py                 # Hiện thực 7 endpoints quản lý tài khoản người dùng
├── schemas/
│   ├── __init__.py              # Export UserCreate, UserUpdate, UserWithTempPassword, TempPassword, UserPage
│   └── user.py                  # DTO Schemas theo docs/openapi.yaml
└── main.py                      # Đăng ký users_router vào /api/v1/users
backend/tests/
└── test_us30_users.py           # Bộ kiểm thử tự động black-box (>= 50 test cases)
docs/backend_spec/sprint_1/
├── README.md                    # Cập nhật mục lục tài liệu Sprint 1
├── SPRINT_1_BACKEND_SPEC.md     # Đánh dấu checklist DoD AC-30.1
└── US-30_USER_MANAGEMENT_SPEC.md# Tài liệu này
```

---

## 3. CHI TIẾT 7 ENDPOINTS & LOGIC NGHIỆP VỤ

### 3.1. `GET /api/v1/users` — Danh sách tài khoản người dùng
* **Quyền gọi (RBAC):** `ADMIN`
* **Query Parameters:**
  - `page` (integer, default 1, min 1)
  - `page_size` (integer, default 20, min 1, max 100)
  - `q` (string, optional): Từ khóa tìm kiếm họ tên hoặc username.
  - `role` (string, optional): Mã vai trò cần lọc.
  - `is_active` (boolean, optional): Trạng thái hoạt động.
* **Phản hồi:** `200 OK` (`UserPage`).

### 3.2. `POST /api/v1/users` — Tạo tài khoản nhân sự mới
* **Quyền gọi (RBAC):** `ADMIN`
* **Request Body (`UserCreate`):**
  ```json
  {
    "username": "accountant_ha",
    "full_name": "Nguyễn Hoàng Hà",
    "email": "ha.nh@bluemoon.vn",
    "phone": "0987654321",
    "role_id": 2
  }
  ```
* **Xử lý nghiệp vụ:**
  1. Kiểm tra tồn tại username (case-insensitive): trùng $\rightarrow$ ném `409 DUPLICATE_USERNAME`.
  2. Kiểm tra `role_id`: không tồn tại $\rightarrow$ `400 VALIDATION_ERROR`; nếu là role `RESIDENT` $\rightarrow$ `400 VALIDATION_ERROR`.
  3. Tự sinh `temp_password` an toàn $\ge 12$ ký tự (hoa, thường, số, ký tự đặc biệt).
  4. Băm bcrypt `get_password_hash(temp_password)`.
  5. Tạo mới bản ghi `User` với `is_active=True`, `must_change_password=True`.
  6. Phản hồi `201 Created` (`UserWithTempPassword`).

### 3.3. `GET /api/v1/users/{userId}` — Chi tiết tài khoản
* **Quyền gọi (RBAC):** `ADMIN`
* **Path Parameter:** `userId: int` (min 1)
* **Xử lý nghiệp vụ:** Truy vấn theo `User.id == userId`. Không thấy $\rightarrow$ `404 USER_NOT_FOUND`.
* **Phản hồi:** `200 OK` (`UserResponse`).

### 3.4. `PATCH /api/v1/users/{userId}` — Cập nhật thông tin tài khoản
* **Quyền gọi (RBAC):** `ADMIN`
* **Path Parameter:** `userId: int` (min 1)
* **Request Body (`UserUpdate`):**
  ```json
  {
    "full_name": "Nguyễn Hoàng Hà (Trưởng nhóm)",
    "email": "ha.truongnhom@bluemoon.vn",
    "phone": "0912345678",
    "is_active": true
  }
  ```
* **Xử lý nghiệp vụ:** Cập nhật các trường không `None`. Lưu vào CSDL.
* **Phản hồi:** `200 OK` (`UserResponse`).

### 3.5. `POST /api/v1/users/{userId}/lock` — Khóa tài khoản tức thì
* **Quyền gọi (RBAC):** `ADMIN`
* **Path Parameter:** `userId: int` (min 1)
* **Xử lý nghiệp vụ:**
  1. Kiểm tra tự khóa: `current_user.id == userId` $\rightarrow$ Ném `409 CANNOT_LOCK_SELF`.
  2. Tìm kiếm user: không thấy $\rightarrow$ `404 USER_NOT_FOUND`.
  3. Gán `user.is_active = False`.
  4. Ghi nhận `AuditLog` hành động `LOCK_USER`.
  5. Commit transaction và trả về `200 OK` (`UserResponse`).

### 3.6. `POST /api/v1/users/{userId}/unlock` — Mở khóa tài khoản tức thì
* **Quyền gọi (RBAC):** `ADMIN`
* **Path Parameter:** `userId: int` (min 1)
* **Xử lý nghiệp vụ:**
  1. Tìm kiếm user: không thấy $\rightarrow$ `404 USER_NOT_FOUND`.
  2. Gán `user.is_active = True`, `user.failed_login_count = 0`, `user.locked_until = None`.
  3. Ghi nhận `AuditLog` hành động `UNLOCK_USER`.
  4. Commit transaction và trả về `200 OK` (`UserResponse`).

### 3.7. `POST /api/v1/users/{userId}/reset-password` — Cấp lại mật khẩu tạm
* **Quyền gọi (RBAC):** `ADMIN`
* **Path Parameter:** `userId: int` (min 1)
* **Xử lý nghiệp vụ:**
  1. Tìm kiếm user: không thấy $\rightarrow$ `404 USER_NOT_FOUND`.
  2. Sinh mật khẩu tạm mới đạt chuẩn an toàn `AC-29.1`.
  3. Băm bcrypt `get_password_hash(temp_password)`.
  4. Gán `user.password_hash = hash`, `user.must_change_password = True`, `user.failed_login_count = 0`, `user.locked_until = None`.
  5. Ghi nhận `AuditLog` hành động `RESET_PASSWORD`.
  6. Commit transaction và trả về `200 OK` (`TempPassword`).

---

## 4. MA TRẬN PHẢN HỒI LỖI (ERROR CODE SPECIFICATION)

| HTTP Status | Mã lỗi (`code`) | Tình huống áp dụng | Schema chi tiết |
| :---: | :--- | :--- | :--- |
| **200** | *(None)* | Thao tác truy vấn, cập nhật, khóa, mở khóa, reset mật khẩu thành công. | `UserPage` / `UserResponse` / `TempPassword` |
| **201** | *(None)* | Tạo tài khoản nhân sự thành công. | `UserWithTempPassword` |
| **400** | `VALIDATION_ERROR` | Lỗi tham số phân trang (`page < 1`, `page_size > 100`), email sai format, username ngắn $< 3$, hoặc cố tình gán role `RESIDENT`. | `Error` (kèm `details`) |
| **401** | `UNAUTHENTICATED` | Thiếu Bearer token, token sai format, hoặc token hết hạn. | `Error` |
| **403** | `FORBIDDEN` | Người dùng không mang vai trò `ADMIN` (Kế toán, Thủ quỹ, Cư dân) cố gắng truy cập. | `Error` |
| **404** | `USER_NOT_FOUND` | Không tìm thấy tài khoản với `userId` được yêu cầu. | `Error` |
| **409** | `DUPLICATE_USERNAME` | Tên đăng nhập bị trùng lặp (so khớp case-insensitive). | `Error` |
| **409** | `CANNOT_LOCK_SELF` | Quản trị viên cố gắng tự khóa tài khoản của chính mình. | `Error` |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi máy chủ hoặc giao dịch CSDL không mong muốn. | `Error` |

---

## 5. MA TRẬN BỘ KIỂM THỬ TỰ ĐỘNG (TEST SUITE MATRIX)

Tệp kiểm thử `backend/tests/test_us30_users.py` bao phủ toàn diện $\ge 50$ test cases:
1. **Happy Paths:**
   - Lấy danh sách phân trang mặc định và tùy chỉnh (`page`, `page_size`).
   - Lọc theo từ khóa `q` (username, full_name, case-insensitive, ký tự tiếng Việt).
   - Lọc theo `role` (`ADMIN`, `ACCOUNTANT`, `RESIDENT`) và `is_active` (`True`, `False`).
   - Tạo user mới với các role nhân sự (`ADMIN`, `ACCOUNTANT`, `TREASURER`), kiểm tra mật khẩu tạm đăng nhập thành công.
   - Lấy chi tiết user, cập nhật thông tin user.
   - Khóa user và mở khóa user, kiểm tra trạng thái đăng nhập tương ứng.
   - Reset mật khẩu và đăng nhập lại bằng mật khẩu tạm mới.
2. **Edge Cases & Validation:**
   - Trùng lặp username (chính xác và khác biệt chữ hoa/thường).
   - Role không tồn tại hoặc role `RESIDENT`.
   - Username quá ngắn hoặc chứa ký tự đặc biệt không cho phép.
   - Admin tự khóa chính mình.
   - ID người dùng không tồn tại (404).
   - Phân trang bất thường (`page=0`, `page_size=101`).
   - Payload SQL Injection và chuỗi Unicode đặc biệt trong query param `q`.
3. **Security & RBAC Guard:**
   - Cả 7 endpoints khi không có token (401).
   - Cả 7 endpoints khi gọi bởi vai trò không phải Admin (403 cho Resident, Accountant, Treasurer).
   - Kiểm tra ghi nhận `AuditLog` đối với `ACCESS_DENIED`, `LOCK_USER`, `UNLOCK_USER`, `RESET_PASSWORD`.

