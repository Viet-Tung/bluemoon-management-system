# THƯ MỤC ĐẶC TẢ KỸ THUẬT BACKEND SPRINT 1

Thư mục này chứa các tài liệu kỹ thuật thu gọn, cô đọng được trích xuất từ các tệp master SSOT (`Plan.pdf`, `01_schema.sql`, `API_CONTRACT.md`) nhằm phục vụ tra cứu nhanh và chuyển giao ngữ cảnh giữa các phiên làm việc (AI Conversations) cho 2 kỹ sư Backend: `TV1: Lê Trường Giang` và `TV2: Nguyễn Việt Tùng`.

---

## 📑 Danh mục tài liệu kỹ thuật Sprint 1

| Tên tệp | Mô tả nội dung | Phạm vi |
| :--- | :--- | :--- |
| `SPRINT_1_BACKEND_SPEC.md` | Toàn bộ 12 User Stories Sprint 1: Chuẩn lỗi, 9 bảng CSDL cụm tối thiểu, 32 Endpoints, Ma trận phân quyền RBAC và DoD Checklist. | Toàn bộ Sprint 1 (40 SP) |
| `US-44_AUTH_SECURITY_SPEC.md` | Đặc tả chi tiết cấp code cho US-44: Bcrypt $\ge 12$ rounds, JWT token, chống IDOR, cấu trúc thư mục `core/`, `models/`, `schemas/`, `main.py` và 238 test cases. | User Story US-44 (4 SP) |
| `US-28_AUTH_LOGIN_SPEC.md` | Đặc tả chi tiết cấp code cho US-28: Đăng nhập cấp JWT 8h, khóa tài khoản 15m khi sai 5 lần (`AC-28.2`), đăng xuất, thông tin tài khoản và 114 test cases. | User Story US-28 (4 SP) |
| `US-29_CHANGE_PASSWORD_SPEC.md` | Đặc tả chi tiết cấp code cho US-29: Đổi mật khẩu cá nhân, bắt buộc đổi lần đầu, mã lỗi `WRONG_OLD_PASSWORD`, kiểm tra độ mạnh AC-29.1 và 81 test cases. | User Story US-29 (2 SP) |

---

## 🚀 Hướng dẫn nạp ngữ cảnh cho các phiên làm việc AI tiếp theo
Khi bắt đầu một Conversation mới cho một User Story, chỉ cần nhắc AI:
> *"Đọc docs/backend_spec/sprint_1/SPRINT_1_BACKEND_SPEC.md và bắt đầu code User Story US-xx trên nhánh feat/US-xx..."*
