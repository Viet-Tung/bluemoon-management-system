# THƯ MỤC ĐẶC TẢ KỸ THUẬT BACKEND SPRINT 1

Thư mục này chứa các tài liệu kỹ thuật thu gọn, cô đọng được trích xuất từ các tệp master SSOT (`Plan.pdf`, `01_schema.sql`, `API_CONTRACT.md`) nhằm phục vụ tra cứu nhanh và chuyển giao ngữ cảnh giữa các phiên làm việc (AI Conversations) cho các kỹ sư Backend.

---

## 📑 Danh mục tài liệu kỹ thuật Sprint 1

| Tên tệp | Mô tả nội dung | Phạm vi |
| :--- | :--- | :--- |
| `SPRINT_1_BACKEND_SPEC.md` | Toàn bộ 12 User Stories Sprint 1: Chuẩn lỗi, 9 bảng CSDL cụm tối thiểu, 32 Endpoints, Ma trận phân quyền RBAC và DoD Checklist. | Toàn bộ Sprint 1 (40 SP) |
| `US-01_APARTMENTS_HOUSEHOLDS_SPEC.md` | Đặc tả chi tiết cấp code cho US-01: Quản lý 7 endpoints Căn hộ & Hộ gia đình, tách biệt thực thể T-01/T-02, tự sinh tài khoản cư dân D-12, giao dịch ACID và 122 test cases black-box. | User Story US-01 (5 SP) |
| `US-02_HOUSEHOLD_MANAGEMENT_SPEC.md` | Đặc tả chi tiết cấp code cho US-02: Quản lý thông tin liên hệ hộ, ngừng quản lý (No hard delete), đổi chủ hộ đại diện (AC-02.1), kiểm tra công nợ (DEBT_NOT_SETTLED), ghi nhận AuditLog và 98 test cases black-box. | User Story US-02 (3 SP) |
| `US-03_APARTMENT_TRANSFER_SPEC.md` | Đặc tả chi tiết cấp code cho US-03: Chuyển nhượng căn hộ giữa các hộ, đóng/mở occupancy, kiểm tra công nợ (DEBT_NOT_SETTLED, APARTMENT_OCCUPIED, HOUSEHOLD_HAS_NO_APARTMENT), bảo toàn 100% lịch sử hóa đơn (AC-03.1), ghi nhận AuditLog và 84 test cases black-box. | User Story US-03 (3 SP) |
| `US-44_AUTH_SECURITY_SPEC.md` | Đặc tả chi tiết cấp code cho US-44: Bcrypt $\ge 12$ rounds, JWT token, chống IDOR, cấu trúc thư mục `core/`, `models/`, `schemas/`, `main.py` và 238 test cases. | User Story US-44 (4 SP) |
| `US-28_AUTH_LOGIN_SPEC.md` | Đặc tả chi tiết cấp code cho US-28: Đăng nhập cấp JWT 8h, khóa tài khoản 15m khi sai 5 lần (`AC-28.2`), đăng xuất, thông tin tài khoản và 114 test cases. | User Story US-28 (4 SP) |
| `US-29_CHANGE_PASSWORD_SPEC.md` | Đặc tả chi tiết cấp code cho US-29: Đổi mật khẩu cá nhân, bắt buộc đổi lần đầu, mã lỗi `WRONG_OLD_PASSWORD`, kiểm tra độ mạnh AC-29.1 và 81 test cases. | User Story US-29 (2 SP) |
| `US-30_USER_MANAGEMENT_SPEC.md` | Đặc tả chi tiết cấp code cho US-30: Quản lý 7 endpoints tài khoản người dùng, sinh mật khẩu tạm an toàn, cấm tự khóa chính mình, AuditLog và bộ test black-box. | User Story US-30 (4 SP) |
| `US-31_ROLE_MANAGEMENT_SPEC.md` | Đặc tả chi tiết cấp code cho US-31: Phân quyền & Quản lý vai trò (2 endpoints `GET /roles`, `PUT /users/{userId}/role`), hiệu lực ngay `AC-31.1`, cấm đổi vai trò chính mình, cô lập nhân sự/cư dân và 65 test cases. | User Story US-31 (3 SP) |
| `US-32_AUDIT_LOG_SPEC.md` | Đặc tả chi tiết cấp code cho US-32: Nhật ký thao tác (Audit Log) (`GET /audit-logs`), phân quyền `ADMIN`, bộ lọc đa tiêu chí, tính bất biến và 82 test cases black-box. | User Story US-32 (3 SP) |
| `US-12_FEE_CATALOG_SPEC.md` | Đặc tả chi tiết cấp code cho US-12: Quản lý danh mục khoản thu bắt buộc (`GET /fee-types`, `POST /fee-types`, `PATCH /fee-types/{id}`), kiểm tra trùng mã `DUPLICATE_FEE_CODE`, bất biến mã và cách tính, ghi nhận AuditLog và 79 test cases black-box. | User Story US-12 (3 SP) |
| `US-13_DEACTIVATE_FEE_SPEC.md` | Đặc tả chi tiết cấp code cho US-13: Ngừng áp dụng khoản thu (`POST /fee-types/{id}/deactivate`), cấm xóa vật lý No hard delete (`AC-13.1`), bất biến thuộc tính cấu hình, ghi nhận AuditLog và 70 test cases black-box. | User Story US-13 (2 SP) |

---

## 🚀 Hướng dẫn nạp ngữ cảnh cho các phiên làm việc AI tiếp theo
Khi bắt đầu một Conversation mới cho một User Story, chỉ cần nhắc AI:
> *"Đọc docs/backend_spec/sprint_1/SPRINT_1_BACKEND_SPEC.md và bắt đầu code User Story US-xx trên nhánh feat/US-xx..."*
