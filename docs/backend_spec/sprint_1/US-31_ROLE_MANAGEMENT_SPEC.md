# ĐẶC TẢ CHI TIẾT USER STORY: US-31 (PHÂN QUYỀN & QUẢN LÝ VAI TRÒ)
> **Mã Story:** `US-31` | **Feature:** `F-05.3` Phân quyền theo vai trò (RBAC) | **WBS:** `2.1.3`  
> **Story Points:** `3 SP` | **Độ ưu tiên:** `Must (M)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-31-backend-role-management`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.3), `docs/API_CONTRACT.md` (Chương 3.2), `docs/openapi.yaml` (các path `/roles`, `/users/{userId}/role`), `database/01_schema.sql` (bảng `roles`, `users`, `audit_logs`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As an** Quản trị viên hệ thống (Admin),  
> **I want** xem danh sách các vai trò chuẩn của hệ thống và gán/thu hồi vai trò cho tài khoản người dùng,  
> **So that** mỗi cá nhân và bộ phận trong ban quản lý tòa nhà chỉ thao tác đúng phạm vi chức trách được ủy nhiệm, đảm bảo an toàn vận hành và bảo mật dữ liệu.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-31.1` (Middleware RBAC Guard kiểm tra quyền trên mọi API endpoint; gán/thu hồi role có hiệu lực ngay):**
  - **Phân quyền bắt buộc:** Cả 2 endpoint (`GET /api/v1/roles` và `PUT /api/v1/users/{userId}/role`) yêu cầu vai trò `ADMIN` thông qua RBAC middleware (`require_roles("ADMIN")`). Các vai trò khác (`ACCOUNTANT`, `TREASURER`, `RESIDENT`) bị chặn với HTTP `403 FORBIDDEN` và tự động ghi nhận nhật ký kiểm toán `ACCESS_DENIED`.
  - **Bắt buộc đổi mật khẩu lần đầu:** Nếu tài khoản Admin có cờ `must_change_password = True` gọi vào các endpoint này, hệ thống lập tức chặn với HTTP `403 FORBIDDEN` kèm mã lỗi `PASSWORD_CHANGE_REQUIRED` và ghi log `ACCESS_DENIED`.
  - **Danh sách vai trò (`GET /api/v1/roles`):**
    * Trả về danh sách đầy đủ 4 vai trò chuẩn trong hệ thống: `ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`.
    * Dữ liệu sắp xếp tăng dần theo `Role.id`.
    * Phản hồi HTTP `200 OK` với mảng các đối tượng schema `Role` (`id`, `code`, `name`, `description`).
  - **Gán hoặc thu hồi vai trò (`PUT /api/v1/users/{userId}/role`):**
    * **Chống tự giáng quyền (Self-demotion prevention):** Quản trị viên không được phép tự thay đổi vai trò của chính mình (`userId == current_user.id`) $\rightarrow$ Trả về HTTP `409 Conflict` với mã lỗi `CANNOT_CHANGE_OWN_ROLE`.
    * **Kiểm tra tồn tại:**
      - Nếu `userId` không tồn tại trong hệ thống $\rightarrow$ Trả về HTTP `404 Not Found` với mã lỗi `NOT_FOUND`.
      - Nếu `role_id` không tồn tại trong danh mục `roles` $\rightarrow$ Trả về HTTP `400 Bad Request` với mã lỗi `VALIDATION_ERROR`.
    * **Ràng buộc phân tách Nhân sự $\leftrightarrow$ Cư dân (Separation of Concerns):**
      - Tài khoản nhân sự (`ADMIN`, `ACCOUNTANT`, `TREASURER`) không được gán vai trò `RESIDENT` $\rightarrow$ Trả về HTTP `400 Bad Request` với mã lỗi `VALIDATION_ERROR`.
      - Tài khoản cư dân (`RESIDENT` / có `household_id`) không được gán các vai trò nhân sự $\rightarrow$ Trả về HTTP `400 Bad Request` với mã lỗi `VALIDATION_ERROR`.
    * **Hiệu lực tức thì:** Hàm `get_current_user` nạp vai trò trực tiếp từ CSDL theo từng request nên khi cập nhật `user.role_id` và commit giao dịch, request tiếp theo của người dùng đó lập tức áp dụng quyền hạn mới (nhận quyền truy cập mới hoặc lập tức bị chặn `403 FORBIDDEN` nếu mất quyền).
    * **Nhật ký kiểm toán (`AuditLog`):** Ghi nhận bản ghi kiểm toán nhạy cảm với `action="CHANGE_ROLE"`, `entity_type="USER"`, `entity_id=str(user.id)`, lưu trữ `old_value` và `new_value` (gồm `role_id` và `role_code`), kèm IP address và User-Agent.
    * **Toàn vẹn giao dịch ACID & Cấm xóa vật lý:** Thực thi trong giao dịch duy nhất, không sử dụng xóa vật lý.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── core/
│   └── rbac_middleware.py       # RBAC Guard kiểm tra role & PASSWORD_CHANGE_REQUIRED
├── routers/
│   ├── __init__.py              # Export roles_router, users_router
│   ├── roles.py                 # Endpoint GET /api/v1/roles (listRoles)
│   └── users.py                 # Endpoint PUT /api/v1/users/{userId}/role (setUserRole)
├── schemas/
│   ├── __init__.py              # Export UserRoleUpdate, RoleResponse
│   ├── auth.py                  # RoleResponse (id, code, name, description)
│   └── user.py                  # UserRoleUpdate (role_id: int)
└── main.py                      # Đăng ký roles_router prefix /api/v1/roles
backend/tests/
└── test_us31_role_management.py # Bộ kiểm thử tự động black-box (77 test cases)
docs/backend_spec/sprint_1/
├── README.md                    # Cập nhật danh mục tài liệu Sprint 1
├── SPRINT_1_BACKEND_SPEC.md     # Đánh dấu checklist DoD AC-31.1
└── US-31_ROLE_MANAGEMENT_SPEC.md# Tài liệu này
```

---

## 3. CHI TIẾT 2 ENDPOINTS & LOGIC NGHIỆP VỤ

### 3.1. `GET /api/v1/roles` — Danh sách vai trò hệ thống
* **Operation ID:** `listRoles`
* **Quyền gọi (RBAC):** `ADMIN`
* **Tham số Query:** Không có.
* **Phản hồi thành công:** `200 OK` (`List[RoleResponse]`).
  ```json
  [
    {
      "id": 1,
      "code": "ADMIN",
      "name": "Ban Quản Trị / Quản Trị Viên",
      "description": "Toàn quyền quản trị hệ thống, phê duyệt nhân khẩu, xem dashboard"
    },
    {
      "id": 2,
      "code": "ACCOUNTANT",
      "name": "Kế toán",
      "description": "Cấu hình danh mục phí, đơn giá, tạo kỳ thu, đối soát dịch vụ, báo cáo"
    },
    {
      "id": 3,
      "code": "TREASURER",
      "name": "Thủ quỹ",
      "description": "Thu tiền mặt/chuyển khoản tại quầy, in biên lai, quản lý đợt vận động tự nguyện"
    },
    {
      "id": 4,
      "code": "RESIDENT",
      "name": "Cư dân",
      "description": "Xem thông tin hộ, lịch sử hóa đơn/thanh toán, gửi đề nghị sửa đổi thông tin"
    }
  ]
  ```
* **Mã lỗi:**
  - `401 UNAUTHENTICATED`: Thiếu token hoặc token không hợp lệ.
  - `403 FORBIDDEN`: Không phải vai trò ADMIN.
  - `403 PASSWORD_CHANGE_REQUIRED`: Admin chưa đổi mật khẩu lần đầu.

---

### 3.2. `PUT /api/v1/users/{userId}/role` — Gán hoặc thu hồi vai trò
* **Operation ID:** `setUserRole`
* **Quyền gọi (RBAC):** `ADMIN`
* **Path Parameter:** `userId` (integer, $\ge 1$).
* **Request Body (`UserRoleUpdate`):**
  ```json
  {
    "role_id": 3
  }
  ```
* **Xử lý nghiệp vụ:**
  1. Kiểm tra `current_user.must_change_password`: Nếu `True` $\rightarrow$ Trả về `403 PASSWORD_CHANGE_REQUIRED`.
  2. Kiểm tra `current_user.id == userId`: Nếu trùng $\rightarrow$ Trả về `409 CANNOT_CHANGE_OWN_ROLE`.
  3. Truy vấn người dùng mục tiêu theo `userId`: Nếu không tìm thấy $\rightarrow$ Trả về `404 NOT_FOUND`.
  4. Truy vấn vai trò mục tiêu theo `req.role_id`: Nếu không tìm thấy $\rightarrow$ Trả về `400 VALIDATION_ERROR`.
  5. Kiểm tra ràng buộc phân tách:
     - Nếu tài khoản là nhân sự và `target_role.code == "RESIDENT"` $\rightarrow$ Trả về `400 VALIDATION_ERROR`.
     - Nếu tài khoản là cư dân và `target_role.code != "RESIDENT"` $\rightarrow$ Trả về `400 VALIDATION_ERROR`.
  6. Cập nhật `user.role_id = target_role.id`.
  7. Ghi nhật ký `AuditLog` với `action="CHANGE_ROLE"`, lưu snapshot `old_value` và `new_value`.
  8. Commit giao dịch và trả về `UserResponse`.
* **Phản hồi thành công:** `200 OK` (`UserResponse`).

---

## 4. MA TRẬN MÃ LỖI & RÀNG BUỘC BẤT BIẾN (ERROR MATRIX)

| HTTP Status | Mã `code` | Nguyên nhân áp dụng |
| :---: | :--- | :--- |
| **400** | `VALIDATION_ERROR` | `role_id` không tồn tại; gán RESIDENT cho nhân sự; gán vai trò nhân sự cho cư dân; thiếu `role_id` hoặc sai định dạng. |
| **401** | `UNAUTHENTICATED` | Thiếu token, token hết hạn hoặc chữ ký JWT không hợp lệ. |
| **403** | `FORBIDDEN` | Tài khoản gọi endpoint không có vai trò `ADMIN` (tự động ghi log `ACCESS_DENIED`). |
| **403** | `PASSWORD_CHANGE_REQUIRED` | Tài khoản có `must_change_password=True` gọi API trước khi đổi mật khẩu (tự động ghi log `ACCESS_DENIED`). |
| **404** | `NOT_FOUND` | Không tìm thấy người dùng mục tiêu theo `userId`. |
| **409** | `CANNOT_CHANGE_OWN_ROLE` | Quản trị viên tự đổi vai trò của chính mình. |
| **405** | `METHOD_NOT_ALLOWED` | Gọi sai phương thức HTTP (VD: `POST /roles`, `DELETE /users/{id}/role`). |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi máy chủ hoặc xung đột giao dịch bất khả kháng. |

---

## 5. CHIẾN LƯỢC KIỂM THỬ THUẦN BLACK-BOX (77 TEST CASES)

Toàn bộ 77 ca kiểm thử tự động tại `backend/tests/test_us31_role_management.py` được thiết kế 100% dựa trên API Contract và OpenAPI specification bởi QA Subagent độc lập:

1. **Happy Paths `GET /roles` (9 test cases):**
   - HTTP 200 OK, trả về danh sách mảng JSON.
   - Kiểm tra cấu trúc Schema đầy đủ (`id`, `code`, `name`, `description`).
   - Sắp xếp tăng dần theo ID.
   - Bao phủ đủ 4 vai trò chuẩn: `ADMIN`, `ACCOUNTANT`, `TREASURER`, `RESIDENT`.
2. **Happy Paths `PUT /users/{userId}/role` (12 test cases):**
   - Đổi qua lại giữa các vai trò nhân sự: `ACCOUNTANT` $\leftrightarrow$ `TREASURER`, `ACCOUNTANT` $\rightarrow$ `ADMIN`, `ADMIN` $\rightarrow$ `ACCOUNTANT`, `TREASURER` $\rightarrow$ `ADMIN`.
   - Tính lũy thừa (Idempotent): gán lại vai trò trùng vai trò hiện tại trả về 200 OK.
   - Kiểm tra cấu trúc phản hồi `UserResponse`.
   - Kiểm tra cập nhật CSDL tức thì.
   - Kiểm tra bản ghi `AuditLog` với `action="CHANGE_ROLE"`, lưu đúng `old_value`, `new_value`, User-Agent.
3. **Hiệu lực tức thì theo tiêu chí `AC-31.1` (4 test cases):**
   - Kế toán sau khi được thăng lên `ADMIN` lập tức có quyền truy cập endpoint admin-only ở request kế tiếp.
   - Admin phụ sau khi bị giáng xuống `ACCOUNTANT` lập tức bị chặn `403 FORBIDDEN` ở request kế tiếp.
   - Người dùng được thăng Admin lập tức gọi được `GET /roles`.
   - Admin phụ bị giáng cấp lập tức không thể gọi `PUT /users/{userId}/role` để sửa vai trò người khác.
4. **Edge Cases & Ràng buộc bất biến (16 test cases):**
   - Cấm Admin tự đổi vai trò của chính mình sang bất kỳ role nào (`409 CANNOT_CHANGE_OWN_ROLE`), không ghi audit log khi bị từ chối.
   - User ID không tồn tại hoặc cực lớn (`404 NOT_FOUND`).
   - Role ID không tồn tại, âm hoặc bằng 0 (`400 VALIDATION_ERROR`).
   - Cấm gán vai trò `RESIDENT` cho nhân sự (`400 VALIDATION_ERROR`).
   - Cấm gán vai trò nhân sự cho cư dân (`400 VALIDATION_ERROR`).
5. **Validation & Dữ liệu đầu vào (10 test cases):**
   - Thiếu `role_id`, `role_id` là chuỗi, null, JSON sai cú pháp (`400 VALIDATION_ERROR`).
   - Path param `userId` âm, bằng 0 hoặc chữ (`400 VALIDATION_ERROR`).
   - Payload chứa trường dư thừa, mảng JSON thay vì object, body trống hoàn toàn (`400 VALIDATION_ERROR`).
6. **Bảo mật & Phân quyền RBAC (14 test cases):**
   - Chưa xác thực, token giả mạo, token hết hạn (`401 UNAUTHENTICATED`).
   - Gọi bằng `ACCOUNTANT`, `TREASURER`, `RESIDENT` (`403 FORBIDDEN`).
   - Xác minh tự động ghi nhận `ACCESS_DENIED` vào `audit_logs`.
7. **HTTP Methods Sanity & An toàn Injection (8 test cases):**
   - Chặn an toàn SQL injection trong path param `userId`.
   - Kiểm tra `405 Method Not Allowed` cho các HTTP methods không hỗ trợ (`POST /roles`, `PUT /roles`, `DELETE /roles`, `PATCH /roles`, v.v.).
8. **Trạng thái tài khoản đặc biệt (4 test cases):**
   - Đổi vai trò cho user `is_active=False` bảo toàn trạng thái vô hiệu hóa.
   - Đổi vai trò cho user `must_change_password=True` bảo toàn cờ đổi mật khẩu.
   - Chặn `GET /roles` khi `must_change_password=True` (`403 PASSWORD_CHANGE_REQUIRED`).
   - Chặn `PUT /users/{userId}/role` khi `must_change_password=True` (`403 PASSWORD_CHANGE_REQUIRED`).

---

## 6. HƯỚNG DẪN BÀN GIAO & PEER REVIEW DOD

* **Tự kiểm tra (Self-Check):**
  - Chạy `pytest backend/tests/test_us31_role_management.py` $\rightarrow$ 77/77 tests PASSED (100%).
  - Chạy toàn bộ test suite `pytest` $\rightarrow$ 646/646 tests PASSED (100%).
  - Zero hard delete, giao dịch ACID toàn vẹn.
  - Tuân thủ tuyệt đối quy tắc không chèn đường dẫn tuyệt đối máy cá nhân vào tài liệu.
* **Người thực hiện:** Lê Trường Giang (`TV1`)
* **Chuyển giao cho:** Nguyễn Việt Tùng (`TV2`) kiểm thử chéo và xác nhận PR hợp nhất vào `develop`.
