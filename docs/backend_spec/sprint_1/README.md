# THƯ MỤC ĐẶC TẢ KỸ THUẬT BACKEND SPRINT 1

Thư mục này chứa các tài liệu kỹ thuật thu gọn, cô đọng được trích xuất từ các tệp master SSOT (`Plan.pdf`, `01_schema.sql`, `API_CONTRACT.md`) nhằm phục vụ tra cứu nhanh và chuyển giao ngữ cảnh giữa các phiên làm việc (AI Conversations) cho 2 kỹ sư Backend: `TV1: Lê Trường Giang` và `TV2: Nguyễn Việt Tùng`.

---

## 📑 Danh mục tài liệu

| Tên tệp | Mô tả nội dung | Phạm vi |
| :--- | :--- | :--- |
| **[SPRINT_1_BACKEND_SPEC.md](file:///z:/Desktop/bluemoon-management-system/docs/backend_spec/sprint_1/SPRINT_1_BACKEND_SPEC.md)** | Toàn bộ 12 User Stories Sprint 1: Chuẩn lỗi, 9 bảng CSDL cụm tối thiểu, 32 Endpoints, Ma trận phân quyền RBAC và DoD Checklist. | Toàn bộ Sprint 1 (40 SP) |
| **[US-44_AUTH_SECURITY_SPEC.md](file:///z:/Desktop/bluemoon-management-system/docs/backend_spec/sprint_1/US-44_AUTH_SECURITY_SPEC.md)** | Đặc tả chi tiết cấp code cho User Story đầu tiên: Bcrypt $\ge 12$ rounds, JWT token, chống IDOR, cấu trúc thư mục `core/`, `models/`, `schemas/`, `main.py` và kịch bản test. | User Story US-44 (5 SP) |

---

## 🚀 Hướng dẫn nạp ngữ cảnh cho các phiên làm việc AI tiếp theo
Khi bắt đầu một Conversation mới cho một User Story, chỉ cần nhắc AI:
> *"Đọc @[docs/backend_spec/sprint_1/SPRINT_1_BACKEND_SPEC.md] và bắt đầu code User Story US-xx trên nhánh feat/US-xx..."*
