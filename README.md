# 🏢 Hệ Thống Quản Lý Cư Dân và Thu Phí Chung Cư BlueMoon

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg) ![Course](https://img.shields.io/badge/SoICT%2F_HUST-Intro_to_SE-red.svg) ![Team](https://img.shields.io/badge/Team-Nh%C3%B3m_18-success.svg)

> **Dự án môn học:** Nhập môn Công nghệ Phần mềm (Introduction to Software Engineering) - Trường CNTT&TT, Đại học Bách Khoa Hà Nội.  
> **Khách hàng mục tiêu:** Ban Quản Trị (BQT), Kế toán, Thủ quỹ và Cư dân tòa nhà chung cư BlueMoon (Quy mô ~1.000 căn hộ, ~5.000 nhân khẩu).

---

## 📖 1. Giới thiệu bài toán

Hiện tại, Ban quản trị chung cư BlueMoon đang quản lý thông tin hộ khẩu, biến động nhân khẩu và thu phí hàng tháng bằng nhiều file Excel rời rạc và biên lai giấy. Việc này dẫn đến:

- Tốn nhiều thời gian nhân công thức tính phí theo diện tích ($\text{m}^2$) và tổng hợp công nợ.  
- Dễ xảy ra sai sót khi thu một phần, nộp thừa, hoặc đổi chủ căn hộ.  
- Khó tra cứu tức thì khi cư dân đến nộp phí hoặc khi Công an phường yêu cầu báo cáo cư trú.

**Phần mềm Quản lý Chung cư BlueMoon** được xây dựng nhằm số hóa 100% quy trình quản lý nhân khẩu, tự động hóa tính phí định kỳ, quản lý biên lai điện tử và cung cấp cổng tra cứu minh bạch cho cư dân.

---

## ✨ 2. Các phân hệ chức năng chính (Phạm vi v1.0)

Hệ thống bao gồm **3 Module cốt lõi** (ánh xạ từ 8 Epics, 27 Features và 43 User Stories):

1. **🔐 Module Quản lý người dùng & Nền tảng (`EP-05`, `EP-08`):**  
   - Đăng nhập, bắt buộc đổi mật khẩu lần đầu, tự động khóa tạm thời 15 phút khi nhập sai 5 lần.  
   - Phân quyền theo vai trò (RBAC): `Trưởng BQT (Admin)`, `Kế toán`, `Thủ quỹ`, `Cư dân`.  
   - Ghi nhận nhật ký thao tác nhạy cảm (`Audit Log`) và tự động sao lưu CSDL hằng ngày lúc 02:00 sáng.  
2. **👨‍👩‍👧‍👦 Module Quản lý hộ gia đình & Cổng cư dân (`EP-01`, `EP-09`):**  
   - Quản lý tách biệt thực thể **Căn hộ** (diện tích, tầng) và **Hộ gia đình** (nhóm nhân khẩu đang cư trú) hỗ trợ nghiệp vụ chuyển nhượng căn hộ.  
   - Quản lý nhân khẩu, biến động (thêm mới sinh, chuyển đi, tách hộ) và cảnh báo Tạm trú/Tạm vắng sắp hết hạn trước 15 ngày.  
   - Import danh sách hộ từ Excel và xuất báo cáo cư trú theo mẫu Công an (`DOC-03`).  
   - Cổng thông tin cho Cư dân tự tra cứu thông tin hộ, lịch sử nộp phí và gửi đề nghị chỉnh sửa.  
3. **💰 Module Quản lý thu phí, Thống kê & Quỹ tự nguyện (`EP-02`, `EP-03`, `EP-04`, `EP-10`):**  
   - Cấu hình danh mục khoản thu (bắt buộc theo $\text{m}^2$, cố định theo hộ) và lưu vết lịch sử đơn giá.  
   - Khởi tạo kỳ thu tự động cho 1.000 hộ trong $\le 10$ giây (tự động cộng nợ cũ và bù trừ số dư có).  
   - Ghi nhận thu tiền (tiền mặt/chuyển khoản), xử lý nộp một phần hoặc nộp dư, in biên lai điện tử (đóng dấu "BẢN SAO" khi in lại).  
   - Quản lý các đợt vận động đóng góp quỹ tự nguyện riêng biệt với công nợ bắt buộc.  
   - Tìm kiếm đa tiêu chí $\le 1$ giây, Dashboard biểu đồ trực quan và xuất báo cáo Excel/PDF.

---

## 👥 3. Đội ngũ phát triển (Nhóm 18 - Mô hình Hợp tác Peer-to-Peer)

Dự án áp dụng mô hình cộng tác **Peer-to-Peer (Bình đẳng / Không có nhóm trưởng)**: Mọi thành viên có vị thế ngang hàng, tự chủ kỹ thuật, đồng sở hữu sản phẩm (Shared Product Ownership) và cùng chịu trách nhiệm về chất lượng chung:

| Mã TV | Thành viên | Vai trò |
| :---: | :--- | :--- |
| **TV1** | **Lê Trường Giang** | Backend Developer |
| **TV2** | **Nguyễn Việt Tùng** | Backend Developer |
| **TV3** | **Nguyễn Thanh Hải** | Frontend Developer |
| **TV4** | **Lê Nguyễn Nhật Huy** | Frontend Developer |
| **TV5** | **Vũ Trung Kiên** | Database & API Contract Specialist |

---

## 📂 4. Tài liệu dự án & Cấu trúc kho mã nguồn (Repository Structure)

### 4.1. Cấu trúc thư mục dự án
```text
bluemoon-management-system/
├── backend/                         # Mã nguồn ứng dụng FastAPI (TV1 & TV2 phụ trách)
│   ├── app/                         # Logic ứng dụng, Routers, Models, Schemas
│   ├── tests/                       # Unit test & Integration test
│   ├── requirements.txt             # Gói phụ thuộc Python
│   └── README.md                    # Hướng dẫn chi tiết phân hệ Backend
├── frontend/                        # Mã nguồn ứng dụng React Web UI (TV3 & TV4 phụ trách)
├── database/                        # Lược đồ CSDL PostgreSQL 28 bảng (TV5 quản lý)
│   ├── 01_schema.sql                # DDL 28 bảng, views, triggers, constraints
│   ├── 02_seed_initial_data.sql     # Dữ liệu mẫu khởi tạo
│   ├── 03_seed_1000_households.py   # Script sinh dữ liệu thử tải
│   └── 04_backup_restore.sh         # Script sao lưu CSDL
├── docs/                            # Tài liệu chuẩn hóa kỹ thuật & SSOT
│   ├── Plan.pdf                     # Master Project Plan (Nhóm 18)
│   ├── Nhóm_18_Epic_User_story.xlsx # Bảng gốc INVEST User Story & AC
│   ├── openapi.yaml                 # Master OpenAPI 3.0.3 API Contract (TV5)
│   ├── API_CONTRACT.md              # Đặc tả Hợp đồng API chi tiết Markdown
│   ├── ARCHITECTURE.md              # Kiến trúc hệ thống & Domain rules
│   ├── DATABASE_DESIGN.md           # Thiết kế CSDL 28 bảng chi tiết
│   ├── PRODUCT_BACKLOG.md           # Product Backlog & Phân bổ 4 Sprints
│   ├── WBS_DICTIONARY.xlsx          # Từ điển WBS
│   └── WBS_TREE_DIAGRAM.svg         # Sơ đồ WBS Tree
├── CONTRIBUTING.md                  # Quy định Git workflow & commit format
├── AGENTS.md                        # Hiến chương phân định quyền hạn workspace
└── README.md                        # Tài liệu tổng quan dự án
```

### 4.2. Danh mục tài liệu kỹ thuật chuẩn (SSOT)
Toàn bộ tài liệu kỹ thuật và kế hoạch thống nhất cho giai đoạn Sprint 1 được lưu trữ trong thư mục [`docs/`](./docs/):

* 📑 **[Kế hoạch dự án BlueMoon (Plan.pdf)](./docs/Plan.pdf):** **Single Source of Truth (SSOT)** - Tuyên ngôn dự án, phạm vi 3 module, ngân sách, rủi ro, WBS, 47 User Stories và kế hoạch 4 Sprints (150 SP).
* 📋 **[Product Backlog & Kế hoạch 4 Sprints](./docs/PRODUCT_BACKLOG.md):** Trích xuất chi tiết 47 User Stories, tiêu chí AC và phân bổ 4 Sprint (150 SP) từ Plan.pdf.
* 📜 **[Hợp đồng API chuẩn OpenAPI 3.0.3 (openapi.yaml)](./docs/openapi.yaml):** Master API Contract 6.034 dòng do TV5 thiết kế cho toàn bộ 97 endpoints hệ thống.
* 📖 **[Đặc tả Hợp đồng API chi tiết (API_CONTRACT.md)](./docs/API_CONTRACT.md):** Tài liệu Hợp đồng API định dạng Markdown trực quan cho Backend và Frontend.
* 🏗️ **[Kiến trúc hệ thống & Quy tắc nghiệp vụ](./docs/ARCHITECTURE.md):** Mô hình Modular Monolith và các Domain Rules cốt lõi.
* 🗄️ **[Đặc tả Thiết kế Cơ sở Dữ liệu (28 bảng)](./docs/DATABASE_DESIGN.md):** Chuẩn CSDL PostgreSQL từ `feat/database-schema-design`, mô tả 28 bảng và DDL tại [database/01_schema.sql](./database/01_schema.sql).
* 📊 **[Kế hoạch Phân cấp Công việc (WBS)](./docs/WBS_DICTIONARY.xlsx):** Từ điển WBS chuẩn và sơ đồ cây [WBS_TREE_DIAGRAM.svg](./docs/WBS_TREE_DIAGRAM.svg).
* 🤝 **[Quy tắc làm việc nhóm & Quy trình Git](./CONTRIBUTING.md):** Quy ước commit, branching strategy và Pull Request.

---

## 🚀 5. Hướng dẫn cài đặt và chạy dự án (Quick Start)

### Yêu cầu môi trường
* **Python:** $\ge 3.10$ (cho Backend FastAPI)
* **Node.js:** $\ge 18.\text{x}$ (cho Frontend React Vite)
* **PostgreSQL:** $\ge 15+$ (Database Engine)
* **Git**

### Các bước khởi chạy

```bash
# 1. Khởi tạo Cơ sở dữ liệu PostgreSQL
# Chạy file DDL tạo 28 bảng:
psql -U postgres -d bluemoon_db -f database/01_schema.sql

# 2. Khởi chạy Backend API Server (Python FastAPI)
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Truy cập Swagger UI: http://localhost:8000/docs

# 3. Khởi chạy Frontend Web UI (React + Vite)
cd ../frontend
npm install
npm run dev
# Truy cập Web App: http://localhost:3000
```

---

### Tài khoản thử nghiệm mặc định (Theo Seed Data CSDL)

| Vai trò | Tên đăng nhập | Mật khẩu mặc định | Quyền hạn chính |
| :---- | :---- | :---- | :---- |
| **Trưởng BQT (Admin)** | `admin_bqt` | `BlueMoon@2026` | Toàn quyền hệ thống, duyệt nhân khẩu, xem Dashboard |
| **Kế toán** | `ketoan_01` | `BlueMoon@2026` | Cấu hình khoản thu, tạo kỳ thu, nhập CK, xuất báo cáo |
| **Thủ quỹ** | `thuquy_01` | `BlueMoon@2026` | Thu tiền mặt tại quầy, in biên lai, thu quỹ tự nguyện |
| **Cư dân (Căn B1204)** | `cudan_B1204` | `BlueMoon@2026` | Xem thông tin hộ B1204, lịch sử đóng phí, gửi đề nghị sửa |
