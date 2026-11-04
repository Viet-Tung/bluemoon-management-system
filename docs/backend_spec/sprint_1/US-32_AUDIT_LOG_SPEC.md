# ĐẶC TẢ CHI TIẾT USER STORY: US-32 (NHẬT KÝ THAO TÁC / AUDIT LOG)
> **Mã Story:** `US-32` | **Feature:** `F-05.4` Nhật ký thao tác (Audit Log) | **WBS:** `2.1.4`  
> **Story Points:** `3 SP` | **Độ ưu tiên:** `Should (S)`  
> **Người thực hiện:** `TV1: Lê Trường Giang` | **Người kiểm thử ngang hàng (Peer Review):** `TV2: Nguyễn Việt Tùng`  
> **Nhánh Git:** `feat/US-32-backend-audit-log`  
> **Tài liệu tham chiếu:** `docs/Plan.pdf` (mục II.3), `docs/API_CONTRACT.md` (Chương 3.3.1), `docs/openapi.yaml` (path `/audit-logs`), `database/01_schema.sql` (bảng `audit_logs`, `users`).

---

## 1. NỘI DUNG USER STORY & TIÊU CHÍ NGHIỆM THU (DOD)

### 1.1. Yêu cầu nghiệp vụ (User Story Statement)
> **As an** Quản trị viên hệ thống (Admin / Ban Quản Trị),  
> **I want** xem và lọc lịch sử các thao tác nhạy cảm (sửa đơn giá, hủy biên lai, đổi chủ hộ, khóa/mở khóa tài khoản, cấp lại mật khẩu tạm, thay đổi vai trò...),  
> **So that** truy vết trách nhiệm minh bạch, giải trình kiểm toán chính xác và bảo vệ toàn vẹn dữ liệu hệ thống.

### 1.2. Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria)
* **`AC-32.1` (Lưu rõ User thực hiện, Thời gian, Hành động, Giá trị cũ $\rightarrow$ Giá trị mới; Tuyệt đối chặn xóa/sửa bảng `audit_logs`):**
  - **Phân quyền bắt buộc:** Endpoint `GET /api/v1/audit-logs` chỉ cho phép vai trò `ADMIN` truy cập thông qua middleware RBAC Guard (`require_roles("ADMIN")`). Các vai trò khác (`ACCOUNTANT`, `TREASURER`, `RESIDENT`) bị chặn với HTTP `403 FORBIDDEN` và tự động ghi nhận nhật ký kiểm toán `ACCESS_DENIED`.
  - **Bắt buộc đổi mật khẩu lần đầu:** Quản trị viên chưa hoàn thành đổi mật khẩu ban đầu (`must_change_password = True`) bị chặn với HTTP `403 FORBIDDEN` kèm mã lỗi `PASSWORD_CHANGE_REQUIRED`.
  - **Truy xuất và lọc lịch sử:**
    * Hỗ trợ phân trang chuẩn: `page` (bắt đầu từ 1, mặc định 1) và `page_size` ($1 \le \text{page\_size} \le 100$, mặc định 20).
    * Hỗ trợ lọc theo `user_id`: trả về các thao tác do người dùng cụ thể thực hiện (hoặc trả về `items = []`, `total = 0` nếu ID không tồn tại).
    * Hỗ trợ lọc theo `action`: lọc chính xác mã hành động (ví dụ: `CHANGE_ROLE`, `LOCK_USER`, `UNLOCK_USER`, `RESET_PASSWORD`, `ACCESS_DENIED`...).
    * Hỗ trợ lọc theo `entity_type`: lọc theo đối tượng tác động (ví dụ: `USER`, `HOUSEHOLD`, `APARTMENT`, `FEE_RATE`...).
    * Hỗ trợ lọc khoảng thời gian theo định dạng ngày `date` (`YYYY-MM-DD`):
      - `from`: Lọc bản ghi phát sinh từ `00:00:00.000000` của ngày bắt đầu.
      - `to`: Lọc bản ghi phát sinh đến hết `23:59:59.999999` của ngày kết thúc.
      - Chặn lỗi nếu `from > to` $\rightarrow$ Trả về HTTP `400 Bad Request` kèm mã lỗi `VALIDATION_ERROR`.
      - Chặn lỗi nếu định dạng ngày sai hoặc ngày không hợp lệ trên lịch (ví dụ: `2026/11/04`, `2026-02-31`, `invalid-date`) $\rightarrow$ Trả về HTTP `400 Bad Request` kèm mã lỗi `VALIDATION_ERROR`.
    * Cho phép kết hợp đồng thời nhiều bộ lọc (`user_id` + `action` + `entity_type` + `from` + `to`).
  - **Thứ tự sắp xếp:** Sắp xếp mặc định giảm dần theo thời gian phát sinh: `created_at DESC, id DESC` (bản ghi mới nhất luôn hiển thị trước).
  - **Tính bất biến & Toàn vẹn (Immutability):**
    * Bảng `audit_logs` là bảng ghi nhận nhật ký kiểm toán bất biến (Write-Once-Read-Many - WORM).
    * Hệ thống tuyệt đối không cung cấp bất kỳ API nào để cập nhật (`PUT`, `PATCH`), tạo thủ công (`POST`) hay xóa (`DELETE`) trên đường dẫn `/api/v1/audit-logs`. Các yêu cầu này đều nhận phản hồi HTTP `405 Method Not Allowed`.
    * Ở tầng CSDL, trigger `trg_audit_logs_immutable` và `trg_audit_logs_no_truncate` chặn đứng mọi thao tác UPDATE/DELETE/TRUNCATE.

---

## 2. BẢN THIẾT KẾ CẤU TRÚC KỸ THUẬT (TECHNICAL BLUEPRINT)

```text
backend/app/
├── core/
│   └── rbac_middleware.py       # RBAC Guard kiểm tra role ADMIN & PASSWORD_CHANGE_REQUIRED
├── routers/
│   ├── __init__.py              # Export audit_logs_router, auth_router, roles_router, users_router
│   └── audit_logs.py            # Endpoint GET /api/v1/audit-logs (listAuditLogs)
├── schemas/
│   ├── __init__.py              # Export AuditLogResponse, AuditLogPage
│   ├── audit_log.py             # Schema Pydantic v2: AuditLogResponse, AuditLogPage
│   └── common.py                # PageMeta, Error, ErrorDetail
└── main.py                      # Đăng ký audit_logs_router tại prefix /api/v1/audit-logs
backend/tests/
└── test_us32_audit_log.py       # Bộ kiểm thử tự động Black-box độc lập (82 test cases)
docs/backend_spec/sprint_1/
├── README.md                    # Cập nhật danh mục tài liệu kỹ thuật Sprint 1
├── SPRINT_1_BACKEND_SPEC.md     # Đánh dấu checklist DoD AC-32.1
└── US-32_AUDIT_LOG_SPEC.md      # Tài liệu này
```

---

## 3. CHI TIẾT ENDPOINT & LOGIC NGHIỆP VỤ

### 3.1. `GET /api/v1/audit-logs` — Xem và lọc nhật ký thao tác
* **Operation ID:** `listAuditLogs`
* **Quyền gọi (RBAC):** `ADMIN`
* **Tags:** `System`
* **Tham số Query:**
  * `page` (integer, $\ge 1$, mặc định `1`): Số trang cần lấy.
  * `page_size` (integer, $1 \le \text{page\_size} \le 100$, mặc định `20`): Số lượng bản ghi trên một trang.
  * `user_id` (integer, int64, optional): Lọc theo ID tài khoản thực hiện hành động.
  * `action` (string, optional): Lọc chính xác mã hành động nghiệp vụ.
  * `entity_type` (string, optional): Lọc chính xác loại thực thể bị tác động.
  * `from` (string, định dạng `date` `YYYY-MM-DD`, optional): Lọc từ thời điểm `00:00:00` của ngày.
  * `to` (string, định dạng `date` `YYYY-MM-DD`, optional): Lọc đến thời điểm `23:59:59` của ngày.
* **Quy trình xử lý:**
  1. Middleware `require_roles("ADMIN")` xác thực JWT token, lấy thông tin `current_user`.
  2. Kiểm tra `current_user.must_change_password`: nếu `True` $\rightarrow$ Ném ngoại lệ `403 FORBIDDEN` với mã lỗi `PASSWORD_CHANGE_REQUIRED`.
  3. Kiểm tra tính hợp lệ của tham số:
     - Nếu cả `from` và `to` đều được truyền vào và `from > to` $\rightarrow$ Ném ngoại lệ `400 Bad Request` kèm mã lỗi `VALIDATION_ERROR`.
  4. Xây dựng truy vấn SQLAlchemy 2.0 động:
     - Thêm điều kiện `AuditLog.user_id == user_id` nếu `user_id` có giá trị.
     - Thêm điều kiện `AuditLog.action == action.strip()` nếu `action` có giá trị chuỗi không rỗng.
     - Thêm điều kiện `AuditLog.entity_type == entity_type.strip()` nếu `entity_type` có giá trị chuỗi không rỗng.
     - Thêm điều kiện `AuditLog.created_at >= datetime.combine(from_date, time.min)` nếu `from` có giá trị.
     - Thêm điều kiện `AuditLog.created_at <= datetime.combine(to_date, time.max)` nếu `to` có giá trị.
  5. Đếm tổng số bản ghi thỏa mãn điều kiện lọc thông qua `select(func.count(AuditLog.id))`.
  6. Áp dụng sắp xếp `order_by(AuditLog.created_at.desc(), AuditLog.id.desc())`, phân trang với `offset((page - 1) * page_size)` và `limit(page_size)`.
  7. Trả về `AuditLogPage` chứa danh sách `items`, `page`, `page_size`, `total`.

* **Phản hồi thành công (`200 OK` - `AuditLogPage`):**
  ```json
  {
    "page": 1,
    "page_size": 20,
    "total": 1,
    "items": [
      {
        "id": 105,
        "user_id": 1,
        "action": "CHANGE_ROLE",
        "entity_type": "USER",
        "entity_id": "2",
        "old_value": {
          "role_id": 2,
          "role_code": "ACCOUNTANT"
        },
        "new_value": {
          "role_id": 1,
          "role_code": "ADMIN"
        },
        "reason": "Admin 'admin_test' đã đổi vai trò của người dùng 'accountant_test' từ 'ACCOUNTANT' sang 'ADMIN'.",
        "ip_address": "127.0.0.1",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "created_at": "2026-11-04T12:00:00+00:00"
      }
    ]
  }
  ```

---

## 4. MA TRẬN MÃ LỖI & RÀNG BUỘC BẤT BIẾN (ERROR MATRIX)

| HTTP Status | Mã `code` | Nguyên nhân áp dụng |
| :---: | :--- | :--- |
| **400** | `VALIDATION_ERROR` | `page < 1`; `page_size < 1` hoặc `page_size > 100`; tham số kiểu số bị truyền chuỗi chữ; định dạng ngày không khớp `YYYY-MM-DD`; ngày tháng không tồn tại trên lịch; `from > to`. |
| **401** | `UNAUTHENTICATED` | Thiếu header `Authorization`, token rỗng, định dạng scheme sai (không phải `Bearer`), token hết hạn, chữ ký JWT không hợp lệ, hoặc `user_id` trong token không tồn tại. |
| **403** | `FORBIDDEN` | Người dùng không có vai trò `ADMIN` (`ACCOUNTANT`, `TREASURER`, `RESIDENT` gọi vào) $\rightarrow$ Tự động ghi audit log `ACCESS_DENIED`. |
| **403** | `PASSWORD_CHANGE_REQUIRED` | Tài khoản Admin chưa đổi mật khẩu ban đầu (`must_change_password=True`) $\rightarrow$ Tự động ghi audit log `ACCESS_DENIED`. |
| **405** | `METHOD_NOT_ALLOWED` | Thao tác bằng phương thức HTTP không được hỗ trợ (`POST`, `PUT`, `PATCH`, `DELETE` trên `/api/v1/audit-logs`). |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi máy chủ hoặc ngoại lệ CSDL không xử lý được. |

---

## 5. KẾT QUẢ KIỂM THỬ THUẦN BLACK-BOX CỦA SUBAGENT QA (82 TEST CASES)

Bộ kiểm thử độc lập tại `backend/tests/test_us32_audit_log.py` đạt **82/82 PASSED (100%)**, bao phủ 6 nhóm kịch bản:

1. **Group 1: Authentication & RBAC Guard (14 test cases):**
   - Chặn các trường hợp thiếu token, token rỗng, malformed token, sai scheme Basic, token hết hạn, chữ ký giả mạo (`401 UNAUTHENTICATED`).
   - Chặn các vai trò không hợp lệ: `RESIDENT` (hộ 101, hộ 102), `ACCOUNTANT`, `TREASURER` (`403 FORBIDDEN`).
   - Chặn tài khoản Admin bị vô hiệu hóa (`is_active=False`) và Admin chưa đổi mật khẩu lần đầu (`403 PASSWORD_CHANGE_REQUIRED`).
   - Cho phép tài khoản Admin hợp lệ truy cập (`200 OK`).
2. **Group 2: Input Validation & Boundary Conditions (21 test cases):**
   - Kiểm tra ràng buộc phân trang: `page=0`, `page=-1`, `page='abc'`, `page='1.5'` (`400 VALIDATION_ERROR`).
   - Kiểm tra biên kích thước trang: `page_size=0`, `page_size=-5`, `page_size=101`, `page_size=10000`, `page_size='fifty'` (`400 VALIDATION_ERROR`).
   - Kiểm tra định dạng ngày: `from='2026/11/04'`, `from='04-11-2026'`, `from='invalid-date'` (`400 VALIDATION_ERROR`).
   - Kiểm tra tính hợp lệ lịch ngày: ngày 31 tháng 2 (`2026-02-31`), tháng 13 (`2026-13-01`), ngày 31 tháng 4 (`2026-04-31`), ngày 29 tháng 2 năm không nhuận (`2025-02-29`) (`400 VALIDATION_ERROR`).
   - Kiểm tra ràng buộc logic thời gian: `from > to` (`400 VALIDATION_ERROR`).
   - Kiểm tra `user_id='abc'`, `user_id='1.5'` (`400 VALIDATION_ERROR`).
3. **Group 3: Valid Requests & Filter Matrix (22 test cases):**
   - Lọc theo `user_id`: trả về đúng log của user; `user_id` không tồn tại trả về `items=[]`, `total=0`.
   - Lọc theo `action`: khớp chính xác mã hành động (`LOGIN_SUCCESS`, `UPDATE_ROLE`...); action không tồn tại trả về rỗng.
   - Lọc theo `entity_type`: khớp chính xác (`USER`, `APARTMENT`, `FEE`...).
   - Lọc theo thời gian: `from` đơn lẻ (tính từ `00:00:00`), `to` đơn lẻ (tính đến `23:59:59`), khoảng ngày `from <= to`, ngày đơn `from == to`, khoảng ngày tương lai/quá khứ không có dữ liệu.
   - Tổ hợp đa bộ lọc: `user_id` + `action`, `action` + `entity_type`, `entity_type` + khoảng ngày, kết hợp toàn bộ 5 bộ lọc cùng lúc, và kiểm tra điều kiện loại trừ lẫn nhau.
4. **Group 4: Pagination & Ordering (9 test cases):**
   - Giá trị mặc định `page=1`, `page_size=20`.
   - Phân trang trang 1, trang 2 với kích thước tùy biến, kiểm tra không bị trùng lặp ID giữa các trang.
   - Biên hợp lệ: `page_size=1` và `page_size=100`.
   - Kiểm tra thứ tự sắp xếp nghiêm ngặt: `created_at DESC, id DESC`.
   - Kiểm tra cơ sở dữ liệu rỗng và trang `page=999` vượt quá tổng số trang.
   - Kiểm tra `total` không bị biến động bởi `page` hay `page_size`.
5. **Group 5: Schema Structure & Field Integrity (7 test cases):**
   - Cấu trúc envelope khớp chuẩn `AuditLogPage` (`items`, `page`, `page_size`, `total`).
   - Kiểm tra đầy đủ 11 trường dữ liệu của từng bản ghi `AuditLog`.
   - Định dạng `created_at` tuân thủ chuẩn ISO-8601.
   - Các trường nullable (`user_id`, `entity_id`, `old_value`, `new_value`, `reason`, `ip_address`, `user_agent`) nhận `null` an toàn.
   - Lưu trữ và đọc cấu trúc JSON object của `old_value` và `new_value`.
   - Xác minh tính năng tự động sinh audit log `ACCESS_DENIED` khi phát sinh phản hồi 403.
6. **Group 6: Immutability & Method Not Allowed (9 test cases):**
   - Kiểm tra từ chối phương thức `POST`, `PUT`, `PATCH`, `DELETE` trên `/api/v1/audit-logs` (`405 Method Not Allowed`).
   - Kiểm tra từ chối các phương thức biến đổi trên endpoint item `/api/v1/audit-logs/{id}` (`404` hoặc `405`).

---

## 6. HƯỚNG DẪN BÀN GIAO & PEER REVIEW DOD

* **Tự kiểm tra (Self-Check DoD):**
  - Chạy `pytest backend/tests/test_us32_audit_log.py` $\rightarrow$ **82/82 tests PASSED (100%)**.
  - Chạy toàn bộ test suite `pytest` $\rightarrow$ **728/728 tests PASSED (100%)**, zero regression.
  - Zero hard delete, bảo toàn 100% tính bất biến (WORM) của audit log.
  - Không chứa bất kỳ đường dẫn tuyệt đối nào của máy cá nhân.
* **Người thực hiện:** Lê Trường Giang (`TV1`)
* **Chuyển giao cho:** Nguyễn Việt Tùng (`TV2`) xác nhận hoàn thành và mở PR tích hợp vào nhánh `develop`.

