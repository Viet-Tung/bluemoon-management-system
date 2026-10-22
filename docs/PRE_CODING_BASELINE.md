# HỢP ĐỒNG KỸ THUẬT NỀN TẢNG (PRE-CODING BASELINE)
## HỆ THỐNG QUẢN LÝ VÀ THU PHÍ CHUNG CƯ BLUEMOON (BLUEMOON RMS)

| THÔNG TIN QUẢN TRỊ CẤU HÌNH | CHI TIẾT ĐẶC TẢ |
| :--- | :--- |
| **Mã tài liệu (Document ID)** | `BM-BASE-01` |
| **Phiên bản (Version)** | `v2.0-APPROVED` |
| **Ngày ban hành (Effective Date)** | 2026-10-22 |
| **Tác giả (System Architect)** | Lê Trường Giang (Thành viên số 3 - System Architect & Backend Lead) |
| **Hội đồng ký duyệt (Sign-off)** | Toàn thể 5 thành viên Nhóm 18 (HUST / SoICT) |
| **Tiêu chuẩn tham chiếu** | IEEE Std 1016-2009, RFC 2119, ISO/IEC/IEEE 29148:2018 |

---

### BẢNG LỊCH SỬ THAY ĐỔI (REVISION HISTORY)

| Phiên bản | Ngày | Tác giả | Tóm tắt nội dung thay đổi | Trạng thái |
| :---: | :---: | :--- | :--- | :---: |
| `v0.1-DRAFT` | 2026-10-22 | Lê Trường Giang | Khởi tạo khung quy ước kỹ thuật sơ bộ. | `REJECTED` |
| `v1.0-DRAFT` | 2026-10-22 | Lê Trường Giang | Tái cấu trúc chuẩn hóa 9 trụ cột theo đặc tả `SPEC-PRE-CODING-BASELINE`. | `SUPERSEDED` |
| `v1.2-APPROVED` | 2026-10-22 | Lê Trường Giang | Bổ sung sơ đồ ACID chuyên biệt, phân định DATE vs TIMESTAMPTZ, ranh giới Quỹ tự nguyện. | `SUPERSEDED` |
| `v2.0-APPROVED` | 2026-10-22 | Lê Trường Giang | **Chuyển đổi toàn diện sang Tech Stack thân thiện với sinh viên: Python FastAPI + Pydantic v2 + SQLAlchemy 2.0 (đồng bộ 100% với `backend/README.md`)**, tự sinh Swagger UI `/docs`, cấu hình `venv`, Dependency Injection chuẩn Python. | `APPROVED` |

---

### MỤC LỤC ĐIỀU HƯỚNG (TABLE OF CONTENTS)
- [1. NGUYÊN TẮC CỐT LÕI & CHUẨN TẮC TỪ KHÓA](#1-nguyên-tắc-cốt-lõi--chuẩn-tắc-từ-khóa)
- [2. MA TRẬN CÔNG NGHỆ THÂN THIỆN VỚI SINH VIÊN (TECH STACK)](#2-ma-trận-công-nghệ-thân-thiện-với-sinh-viên-tech-stack)
- [3. CẤU TRÚC THƯ MỤC DỰ ÁN CHUẨN (PROJECT DIRECTORY LAYOUT)](#3-cấu-trúc-thư-mục-dự-án-chuẩn-project-directory-layout)
- [4. HỢP ĐỒNG CƠ SỞ DỮ LIỆU & KIỂU DỮ LIỆU CHUẨN (DATABASE CONTRACT)](#4-hợp-đồng-cơ-sở-dữ-liệu--kiểu-dữ-liệu-chuẩn-database-contract)
  - [4.1. Quy ước Kiểu Dữ liệu & Ràng buộc Khóa ngoại](#41-quy-ước-kiểu-dữ-liệu--ràng-buộc-khóa-ngoại)
  - [4.2. Năm Quy tắc Nghiệp vụ Cốt lõi & Kiểm soát Giao dịch ACID](#42-năm-quy-tắc-nghiệp-vụ-cốt-lõi--kiểm-soát-giao-dịch-acid)
  - [4.3. Giao thức Đóng băng Lược đồ & Kỷ luật Alembic Migration](#43-giao-thức-đóng-băng-lược-đồ--kỷ-luật-alembic-migration)
- [5. BỘ TỪ ĐIỂN ENUM DÙNG CHUNG HỆ THỐNG (PYTHON ENUMS CATALOG)](#5-bộ-từ-điển-enum-dùng-chung-hệ-thống-python-enums-catalog)
- [6. HỢP ĐỒNG GIAO DIỆN API & RESPONSE ENVELOPE (API CONTRACT)](#6-hợp-đồng-giao-diện-api--response-envelope-api-contract)
  - [6.1. Quy chuẩn Response Envelope (Pydantic Generic)](#61-quy-chuẩn-response-envelope-pydantic-generic)
  - [6.2. Bảng Danh mục Mã lỗi Hệ thống (Error Code Registry)](#62-bảng-danh-mục-mã-lỗi-hệ-thống-error-code-registry)
  - [6.3. Chuẩn hóa Tham số Truy vấn & Headers](#63-chuẩn-hóa-tham-số-truy-vấn--headers)
- [7. HỢP ĐỒNG GIAO TIẾP DTO GIỮA 5 PHÂN HỆ (PYDANTIC SCHEMAS)](#7-hợp-đồng-giao-tiếp-dto-giữa-5-phân-hệ-pydantic-schemas)
  - [7.1. Phân hệ Căn hộ & Cư dân (residents)](#71-phân-hệ-căn-hộ--cư-dân-residents)
  - [7.2. Phân hệ Phương tiện (vehicles)](#72-phân-hệ-phương-tiện-vehicles)
  - [7.3. Phân hệ Kế toán & Đợt thu (billing)](#73-phân-hệ-kế-toán--đợt-thu-billing)
  - [7.4. Phân hệ Thực thu & Quỹ (cashier)](#74-phân-hệ-thực-thu--quỹ-cashier)
  - [7.5. Phân hệ Cổng cư dân (portal)](#75-phân-hệ-cổng-cư-dân-portal)
- [8. KIẾN TRÚC BẢO MẬT & NGỮ CẢNH PHIÊN (SECURITY & FASTAPI DEPENDENCIES)](#8-kiến-trúc-bảo-mật--ngữ-cảnh-phiên-security--fastapi-dependencies)
  - [8.1. Sơ đồ Luồng Xác thực & Phân quyền RBAC](#81-sơ-đồ-luồng-xác-thực--phân-quyền-rbac)
  - [8.2. Cấu trúc JWT Payload & Thuật toán Ký HS256](#82-cấu-trúc-jwt-payload--thuật-toán-ký-hs256)
  - [8.3. Quy chuẩn Trích xuất Ngữ cảnh bằng FastAPI Depends](#83-quy-chuẩn-trích-xuất-ngữ-cảnh-bằng-fastapi-depends)
  - [8.4. Cơ chế Ghi vết & Xử lý Ngoại lệ Xuyên suốt (Cross-Cutting Concerns)](#84-cơ-chế-ghi-vết--xử-lý-ngoại-lệ-xuyên-suốt-cross-cutting-concerns)
- [9. MÔI TRƯỜNG CỤC BỘ & BỘ DỮ LIỆU HẠT GIỐNG (GOLDEN SEED DATA)](#9-môi-trường-cục-bộ--bộ-dữ-liệu-hạt-giống-golden-seed-data)
  - [9.1. Tệp Biến Môi trường Mẫu (.env.example)](#91-tệp-biến-môi-trường-mẫu-envexample)
  - [9.2. Kịch bản Cài đặt & Chạy Server Cục bộ (Virtualenv)](#92-kịch-bản-cài-đặt--chạy-server-cục-bộ-virtualenv)
  - [9.3. Danh mục Dữ liệu Hạt giống Vàng bao phủ Ca Biên (Golden Seed Records)](#93-danh-mục-dữ-liệu-hạt-giống-vàng-bao-phủ-ca-biên-golden-seed-records)
- [10. KỶ LUẬT GIT FLOW & TIÊU CHUẨN XONG (DEFINITION OF DONE)](#10-kỷ-luật-git-flow--tiêu-chuẩn-xong-definition-of-done)
- [11. KHUNG PHÂN ĐỊNH TRÁCH NHIỆM & MA TRẬN CAM KẾT KỸ THUẬT](#11-khung-phân-định-trách-nhiệm--ma-trận-cam-kết-kỹ-thuật)

---

## 1. NGUYÊN TẮC CỐT LÕI & CHUẨN TẮC TỪ KHÓA

### 1.1. Ba Nguyên tắc Bất biến
1. **Thiết kế theo Hợp đồng (Contract-First Design):** Toàn bộ Schema Pydantic, mã lỗi nghiệp vụ, và Response Envelope BẮT BUỘC phải được định nghĩa trước khi viết logic nội bộ. Logic bên trong có thể tái cấu trúc, nhưng ranh giới giao tiếp ngoại vi BẮT BUỘC giữ tính tương thích ngược.
2. **Một nguồn Chân lý Duy nhất (Single Source of Truth):** Toàn bộ Enum, Pydantic DTOs dùng chung BẮT BUỘC nằm tập trung tại `app/common/`. KHÔNG ĐƯỢC PHÉP tái định nghĩa hoặc khai báo cục bộ tại các router riêng lẻ.
3. **Độc lập Tích hợp qua Dữ liệu Vàng (Decoupled Integration via Golden Seed):** Mỗi thành viên phát triển và kiểm thử độc lập dựa trên bộ dữ liệu hạt giống định danh cố định, loại bỏ hoàn toàn sự phụ thuộc thời gian vào tiến độ của thành viên khác.

### 1.2. Chuẩn tắc Từ khóa Ràng buộc (RFC 2119)
- **BẮT BUỘC (MUST / SHALL / REQUIRED):** Ràng buộc kỹ thuật tuyệt đối. Vi phạm tiêu chí này sẽ bị từ chối phê duyệt Pull Request (Reject PR).
- **KHÔNG ĐƯỢC PHÉP (MUST NOT / SHALL NOT):** Hành vi cấm kỵ tuyệt đối trong thiết kế và mã nguồn.
- **NÊN (SHOULD / RECOMMENDED):** Chuẩn mực kỹ thuật công nghiệp tối ưu; nếu làm khác phải có văn bản giải trình kiến trúc được Lead chấp thuận.
- **TÙY CHỌN (MAY / OPTIONAL):** Khả năng mở rộng không ảnh hưởng tới các phân hệ khác.

---

## 2. MA TRẬN CÔNG NGHỆ THÂN THIỆN VỚI SINH VIÊN (TECH STACK)

Để phù hợp với trình độ thực tế của nhóm 5 sinh viên Công nghệ Thông tin (HUST / SoICT), loại bỏ các rào cản phức tạp của NestJS/TypeScript (như RxJS, Decorator reflection, Dependency Injection rối rắm), hệ thống thống nhất sử dụng **Python FastAPI Ecosystem** (đồng bộ 100% với tài liệu kiến trúc tại `backend/README.md`):

| Thành phần | Công nghệ / Thư viện | Phiên bản cố định | Lý do & Lợi ích thân thiện với sinh viên |
| :--- | :--- | :--- | :--- |
| **Ngôn ngữ lập trình** | Python | `3.10+` hoặc `3.11.x` | Ngôn ngữ quen thuộc nhất với sinh viên ĐHBK Hà Nội, cú pháp rõ ràng, dễ viết. |
| **Web Framework** | FastAPI | `v0.110.x` | Tốc độ cao, cú pháp async/await tự nhiên, **tự động sinh Swagger UI tại `/docs`** giúp test ngay trên trình duyệt mà không cần cài Postman. |
| **Kiểm tra dữ liệu (DTO)** | Pydantic v2 | `v2.6.x` | Tự động validate kiểu dữ liệu đầu vào/ra, báo lỗi tiếng Việt dễ hiểu, sinh schema OpenAPI tự động. |
| **ORM & Truy vấn CSDL** | SQLAlchemy 2.0 | `v2.0.x` | ORM chuẩn mực của Python, hỗ trợ Typed Mapping, cú pháp `select()` trực quan, kiểm soát ACID Transaction chặt chẽ. |
| **Quản lý Migration** | Alembic | `v1.13.x` | Tự động sinh file migration theo lịch sử thay đổi của model (`alembic revision --autogenerate`). |
| **Hệ quản trị CSDL** | PostgreSQL (hoặc SQLite) | `PostgreSQL 15+` / `SQLite 3` | Linh hoạt: Máy cấu hình tốt chạy PostgreSQL (qua Docker hoặc installer); máy yếu có thể test nhanh trên SQLite file mà không bị nghẽn máy. |
| **Bảo mật & Auth** | `passlib[bcrypt]`, `python-jose` | Chuẩn mã hóa `HS256` | Băm mật khẩu an toàn với `bcrypt`, cấp phát và kiểm tra JWT token đơn giản. |
| **Xử lý Excel & Báo cáo** | `pandas`, `openpyxl`, `reportlab` | Bản mới nhất | Đọc/xuất Excel danh sách cư dân (`DOC-03`) và in ấn Biên lai PDF chuẩn tiếng Việt (`DOC-02`) cực mạnh. |
| **Môi trường & Gói** | Python `venv` + `pip` | `requirements.txt` | Cài đặt cực nhanh trong 1 phút bằng lệnh `pip install -r requirements.txt`, không lo lỗi phiên bản Node/npm cache. |
| **Kiểm thử tự động** | `pytest` + `httpx` | `pytest 8.x` | Cú pháp viết test đơn giản với hàm `assert`, dễ học hơn Jest/Supertest nhiều lần. |

> [!TIP]
> **Lợi thế lớn nhất của FastAPI đối với sinh viên:** Sau khi chạy server (`uvicorn app.main:app --reload`), bạn chỉ cần mở trình duyệt vào địa chỉ `http://localhost:8000/docs`. Toàn bộ danh sách API của cả 5 phân hệ sẽ hiện ra với giao diện trực quan, có nút **"Try it out"** để nhập dữ liệu và test ngay lập tức mà không cần phụ thuộc vào Frontend hay Postman.

---

## 3. CẤU TRÚC THƯ MỤC DỰ ÁN CHUẨN (PROJECT DIRECTORY LAYOUT)

Cấu trúc mã nguồn tại thư mục `backend/` được tổ chức dạng **Modular Layered Architecture** chuẩn Python, phân định rõ ràng giữa lõi dùng chung (`app/core/`, `app/common/`) và 5 phân hệ nghiệp vụ (`app/routers/`):

```text
backend/
├── alembic/                      # Lịch sử Schema Migrations tự động của SQLAlchemy
│   ├── versions/                 # Các file migration được đánh số thứ tự (V001, V002...)
│   └── env.py                    # Cấu hình kết nối DB cho Alembic
├── app/
│   ├── core/                     # VÙNG LÕI HỆ THỐNG (SYSTEM KERNEL)
│   │   ├── config.py             # Đọc biến môi trường từ .env bằng Pydantic BaseSettings
│   │   ├── database.py           # Khởi tạo SQLAlchemy Engine, SessionLocal & get_db Dependency
│   │   ├── security.py           # Hàm hash bcrypt, hàm tạo/giải mã JWT token HS256
│   │   └── dependencies.py       # FastAPI Dependencies: get_current_user, require_role
│   │
│   ├── common/                   # VÙNG DÙNG CHUNG BẤT BIẾN (SHARED COMMON)
│   │   ├── enums.py              # 100% Shared Enums của toàn bộ hệ thống
│   │   ├── response.py           # Pydantic ResponseEnvelope chuẩn hóa đầu ra JSON
│   │   └── audit_logger.py       # Hàm ghi lịch sử thao tác vào bảng audit_logs
│   │
│   ├── models/                   # ĐỊNH NGHĨA CÁC BẢNG CSDL (SQLALCHEMY ORM MODELS)
│   │   ├── base.py               # DeclarativeBase chung
│   │   ├── user.py               # Bảng users, roles, audit_logs
│   │   ├── household.py          # Bảng apartments, households, residents, temp_residencies
│   │   ├── vehicle.py            # Bảng vehicles, parking_tickets
│   │   ├── billing.py            # Bảng fee_categories, billing_periods, household_bills, receipts
│   │   └── portal.py             # Bảng edit_requests, complaints, voluntary_campaigns
│   │
│   ├── schemas/                  # KIỂM TRA DỮ LIỆU ĐẦU VÀO/ĐẦU RA & DTOS (PYDANTIC SCHEMAS)
│   │   ├── auth.py               # Schemas đăng nhập, đổi mật khẩu, token payload
│   │   ├── resident.py           # Schemas căn hộ, nhân khẩu, biến động tạm trú
│   │   ├── vehicle.py            # Schemas phương tiện, đếm xe cross-module
│   │   ├── billing.py            # Schemas lập đợt, tính công nợ, chi tiết dòng phí
│   │   ├── cashier.py            # Schemas thực thu tiền, gạch nợ, biên lai, quyên góp
│   │   └── portal.py             # Schemas cổng cư dân, gửi yêu cầu/khiếu nại
│   │
│   ├── routers/                  # NƠI VIẾT API ENDPOINTS (5 PHÂN HỆ ĐỘC LẬP)
│   │   ├── auth.py               # Phân hệ Auth: Đăng nhập, Quản lý tài khoản, Audit Log (US-36..43)
│   │   ├── residents.py          # Phân hệ Căn hộ & Cư dân: Quản lý căn hộ, hộ dân, nhân khẩu (US-01..08)
│   │   ├── vehicles.py           # Phân hệ Phương tiện: Quản lý phương tiện, vé gửi xe (US-09..14)
│   │   ├── billing.py            # Phân hệ Kế toán: Biểu phí, Lập đợt thu, Tính công nợ (US-15..20)
│   │   ├── cashier.py            # Phân hệ Thủ quỹ: Thu tiền, In/Hủy biên lai, Quỹ tự nguyện (US-21..28)
│   │   └── portal.py             # Phân hệ Cổng cư dân: Tra cứu công nợ, Gửi đề xuất/khiếu nại (US-29..35)
│   │
│   ├── main.py                   # Điểm khởi chạy FastAPI, cấu hình CORS, gắn các router
│   └── seed.py                   # Script Python nạp dữ liệu hạt giống vàng kiểm thử
│
├── tests/                        # Thư mục kiểm thử tự động với pytest
├── .env.example                  # File biến môi trường mẫu
├── alembic.ini                   # File cấu hình Alembic
└── requirements.txt              # Danh mục các thư viện Python cố định phiên bản
```

### Sơ đồ 1: Kiến trúc Phân tầng FastAPI & Ranh giới Thư mục
```mermaid
flowchart TD
    Client["Client: Trình duyệt Web / Swagger UI (/docs)"] -->|"HTTP / REST API"| FastAPIMain["FastAPI App (app/main.py)"]

    subgraph CoreKernel["app/core/ & app/common/ (Vùng dùng chung)"]
        DepAuth["FastAPI Dependencies: get_current_user, require_role"]
        Envelope["ResponseEnvelope (JSON Wrapper)"]
        Audit["AuditLoggerService"]
        Enums["Shared Enums & Config (.env)"]
    end

    FastAPIMain --> DepAuth
    DepAuth --> Envelope

    subgraph ModularRouters["app/routers/ (5 Phân hệ nghiệp vụ độc lập)"]
        R1["Router 1: residents.py (Căn hộ & Cư dân)"]
        R2["Router 2: vehicles.py (Phương tiện & Vé xe)"]
        R3["Router 3: billing.py (Kế toán & Đợt thu)"]
        R4["Router 4: cashier.py (Thủ quỹ & Biên lai)"]
        R5["Router 5: portal.py (Cổng cư dân & Tra cứu)"]
    end

    Envelope --> ModularRouters
    ModularRouters --> Audit
    ModularRouters -->|"SQLAlchemy Session"| DBLayer[("PostgreSQL 15+ / SQLite CSDL")]
```

---

## 4. HỢP ĐỒNG CƠ SỞ DỮ LIỆU & KIỂU DỮ LIỆU CHUẨN (DATABASE CONTRACT)

### 4.1. Quy ước Kiểu Dữ liệu & Ràng buộc Khóa ngoại

| Hạng mục | Quy định chuẩn trong SQLAlchemy | Điều cấm kỵ (Negative Constraints) |
| :--- | :--- | :--- |
| **Khóa chính nội bộ (Internal PK)** | `Integer` / `BigInteger`, `primary_key=True, autoincrement=True` | KHÔNG dùng chuỗi ngẫu nhiên làm PK cho các bảng nghiệp vụ có tần suất JOIN cao. |
| **Định danh công khai (Public ID)** | `UUID` (chuỗi 36 ký tự) cho `users.id`; Mã chứng từ có tiền tố: `receipt_number`, `bill_code`. | KHÔNG để lộ số thứ tự tự tăng (Auto-increment ID) ra URL công khai. |
| **Dữ liệu Tiền tệ (Currency)** | `Numeric(15, 2)` trong CSDL; Kiểu số nguyên VNĐ (`int`) trong Python. | **TUYỆT ĐỐI CẤM SỬ DỤNG `FLOAT` HOẶC `DOUBLE`** cho bất kỳ trường dữ liệu tài chính nào. |
| **Dữ liệu Sự kiện (Timestamp)** | `DateTime(timezone=True)` (UTC ISO-8601) cho `created_at`, `paid_at`, `deleted_at`. | KHÔNG lưu giờ máy tính cục bộ (Local time) vào cơ sở dữ liệu. |
| **Dữ liệu Ngày thuần túy (Date-only)** | `Date` (Định dạng: `YYYY-MM-DD`, không kèm giờ) cho: Ngày sinh (`dob`), Ngày dọn vào/ra (`move_in_date`), Ngày hiệu lực (`effective_from`). | **CẤM LƯU DATETIME CHO NGÀY SINH** để tránh lỗi lệch lùi 1 ngày do chuyển đổi múi giờ GMT+7 sang UTC. |
| **Xóa mềm (Soft Delete)** | BẮT BUỘC có 2 trường: `status: Enum` và `deleted_at: DateTime, nullable=True`. | **TUYỆT ĐỐI CẤM LỆNH `DELETE FROM`** trên các bảng thực thể nghiệp vụ. |
| **Ràng buộc Khóa ngoại (FK Constraint)**| `ForeignKey("table.id", ondelete="RESTRICT")` trên tất cả quan hệ tài chính, căn hộ, hộ dân. | **TUYỆT ĐỐI CẤM `ondelete="CASCADE"`** hoặc `SET NULL` trên các bảng tài chính. |
| **Quy chuẩn đặt tên (Naming)** | Database: `snake_case` (ví dụ: `apartment_id`, `created_at`).<br>Pydantic / API: Tự động hỗ trợ cả `snake_case` và `camelCase` qua alias generator. | KHÔNG dùng lẫn lộn giữa camelCase và snake_case trong cùng một bảng. |

### 4.2. Năm Quy tắc Nghiệp vụ Cốt lõi & Kiểm soát Giao dịch ACID
1. **Tách biệt Căn hộ vật lý (`apartments`) và Hộ gia đình (`households`) (`T-01, T-02`):**
   * Bảng `apartments`: Đại diện cho diện tích sàn xây dựng cố định (`room_number`, `area_m2`, `floor`).
   * Bảng `households`: Đại diện cho quan hệ cư trú biến động theo thời gian (`household_code`, `status`, `credit_balance`).
   * *Ràng buộc:* Khi hộ gia đình chuyển nhượng (`US-02`), cập nhật `households.status = 'MOVED_OUT'`. Khởi tạo bản ghi `households` mới trỏ vào `apartment_id`. **KHÔNG ĐƯỢC PHÉP ghi đè thông tin chủ hộ mới lên bản ghi hộ cũ**.
2. **Công thức Tính phí Kỳ thu Chuẩn tắc (`US-17`, `AC-17.1`, `AC-19.5`):**
   $$\text{Tổng phải nộp kỳ này} = \sum (\text{Đơn giá} \times \text{Số lượng} - \text{Miễn giảm}) + \text{Nợ cũ lũy kế} - \text{Số dư có (Credit Balance)}$$
3. **Bảo tồn Lịch sử Nghiệp vụ:** Mọi thay đổi trạng thái cư dân chuyển đi (`US-07`), biểu phí hết hạn (`AC-13.2`), hoặc biên lai bị hủy (`US-22`) BẮT BUỘC chỉ cập nhật cột `status` và ghi vết vào `audit_logs`.
4. **Kiểm soát Giao dịch Đồng thời & Mức cô lập (Concurrency & ACID Isolation Level - `NFR-008`):**
   Tác vụ thu phí (`US-19`) BẮT BUỘC thực thi trong một SQLAlchemy Transaction kèm Khóa bi quan (`with_for_update()`) trên bản ghi hộ và hóa đơn:
   ```python
   # Cú pháp giao dịch an toàn tuyệt đối trong SQLAlchemy:
   with db.begin():
       # Khóa bản ghi chống Race Condition khi có 2 luồng nộp tiền cùng lúc:
       household = db.query(Household).filter(Household.id == household_id).with_for_update().one()
       bills = db.query(HouseholdBill).filter(HouseholdBill.household_id == household_id, HouseholdBill.status != BillStatus.PAID).with_for_update().all()
       # 1. Tạo receipt
       # 2. Gạch nợ từng khoản theo AC-19.2
       # 3. Khấu trừ hoặc cộng thừa vào credit_balance
   ```
5. **Khoản thu Tự nguyện (`voluntary_donations`) ĐỘC LẬP HOÀN TOÀN với Hóa đơn Tiền phí (`household_bills`):**
   Tiền đóng góp tự nguyện KHÔNG ghi nhận vào công nợ căn hộ, KHÔNG làm thay đổi `credit_balance` của hộ gia đình, KHÔNG được cấn trừ tự động từ số dư có, và KHÔNG được gộp chung vào biên lai thu phí sinh hoạt định kỳ.

#### Sơ đồ 2: Luồng Giao dịch Toàn vẹn khi Thu phí (ACID Transaction Flow)
```mermaid
sequenceDiagram
    autonumber
    actor Cashier as Thủ quỹ / WebHook VietQR
    participant Service as CashierService (Python)
    participant DB as Database Engine (ACID)

    Cashier->>Service: execute_payment_transaction(cmd)
    activate Service
    Service->>DB: with db.begin() (Mở Transaction)
    Service->>DB: SELECT * FROM households WHERE id = ? WITH FOR UPDATE
    Service->>DB: SELECT * FROM household_bills WHERE household_id = ? WITH FOR UPDATE
    Service->>DB: (1) INSERT INTO receipts (receipt_number, amount_received)
    loop Gạch nợ theo thứ tự ưu tiên (AC-19.2)
        Service->>DB: (2) Phân bổ tiền gạch nợ: Phí dịch vụ -> Quản lý -> Gửi xe
        Service->>DB: UPDATE household_bills SET paid_amount = paid_amount + alloc
    end
    alt Số tiền nộp > Tổng công nợ còn lại
        Service->>DB: (3) UPDATE households SET credit_balance = credit_balance + excess
    else Có sử dụng credit_balance có sẵn để cấn trừ
        Service->>DB: (3) UPDATE households SET credit_balance = credit_balance - used
    end
    alt Không phát sinh lỗi
        Service->>DB: COMMIT TRANSACTION (Tự động khi thoát khối with)
        Service-->>Cashier: PaymentExecutionResultDTO (Thành công)
    else Phát sinh lỗi (Validation, Concurrency Conflict, DB Timeout)
        Service->>DB: ROLLBACK TRANSACTION (Tự động Rollback)
        Service-->>Cashier: Ném HTTPException (409 hoặc 422)
    end
    deactivate Service
```

### 4.3. Giao thức Đóng băng Lược đồ & Kỷ luật Alembic Migration
1. **Đóng băng Lược đồ (Schema Freeze):** TV3 (System Architect) BẮT BUỘC thiết kế 100% Khung Model trong thư mục `app/models/` và sinh file migration gốc đầu tiên (`alembic/versions/V001_init_baseline.py`) ngay trên nhánh `develop` trước khi các thành viên tách nhánh.
2. **Kỷ luật Nhánh tính năng:** Các thành viên phát triển tính năng **KHÔNG ĐƯỢC PHÉP tự ý chỉnh sửa cấu trúc bảng trong `app/models/` trên nhánh cá nhân**.
3. **Lệnh Migration Chuẩn:**
   * Tạo migration mới (chỉ dành cho Lead TV3 trên `develop`): `alembic revision --autogenerate -m "ten_thay_doi"`
   * Áp dụng migration sẵn có (cho các thành viên kéo code về local): `alembic upgrade head`
4. **Quy trình Thay đổi Schema (RFC Schema Change):** Nếu phát sinh nhu cầu thêm cột hoặc quan hệ mới, thành viên BẮT BUỘC phải gửi yêu cầu (RFC Issue) cho TV3. TV3 sẽ phê duyệt, cập nhật tập trung trên `develop`, tạo migration `V00X...` và thông báo cho cả nhóm kéo (pull) về.

---

## 5. BỘ TỪ ĐIỂN ENUM DÙNG CHUNG HỆ THỐNG (PYTHON ENUMS CATALOG)

Toàn bộ Enum BẮT BUỘC đặt tập trung tại `app/common/enums.py`. Khai báo đầy đủ 100% mã nguồn Python chuẩn (`str, Enum`):

```python
from enum import Enum

# 1. Phân quyền người dùng hệ thống (RBAC)
class UserRole(str, Enum):
    ADMIN = "ADMIN"           # Quản trị viên hệ thống (US-36..43)
    ACCOUNTANT = "ACCOUNTANT" # Kế toán: Lập đợt thu, biểu phí, chốt số liệu (US-15..20)
    CASHIER = "CASHIER"       # Thủ quỹ: Thu tiền, xuất biên lai, chốt ca (US-21..28)
    RESIDENT = "RESIDENT"     # Cư dân: Tra cứu công nợ, gửi kiến nghị (US-29..35)

# 2. Trạng thái Hộ gia đình & Cư dân (US-01..08)
class HouseholdStatus(str, Enum):
    ACTIVE = "ACTIVE"                     # Đang sinh sống thực tế tại chung cư
    TEMPORARY_ABSENT = "TEMPORARY_ABSENT" # Hộ đang tạm vắng
    MOVED_OUT = "MOVED_OUT"               # Đã chuyển hẳn khỏi chung cư

class ResidentRelation(str, Enum):
    OWNER = "OWNER"         # Chủ hộ đứng tên
    SPOUSE = "SPOUSE"       # Vợ / Chồng
    CHILD = "CHILD"         # Con đẻ / Con nuôi hợp pháp
    PARENT = "PARENT"       # Bố / Mẹ
    OTHER = "OTHER"         # Quan hệ nhân khẩu khác

class ResidenceType(str, Enum):
    PERMANENT = "PERMANENT" # Thường trú
    TEMPORARY = "TEMPORARY" # Tạm trú

class ResidentStatus(str, Enum):
    ACTIVE = "ACTIVE"                     # Cư dân đang sinh sống
    TEMPORARY_ABSENT = "TEMPORARY_ABSENT" # Tạm vắng
    MOVED_OUT = "MOVED_OUT"               # Đã chuyển khẩu đi
    DECEASED = "DECEASED"                 # Đã qua đời (Bảo tồn dữ liệu - US-07)

# 3. Phân loại & Trạng thái Phương tiện (US-09..14)
class VehicleType(str, Enum):
    CAR = "CAR"                               # Ô tô
    MOTORBIKE = "MOTORBIKE"                   # Xe máy xăng / xe máy điện
    BICYCLE = "BICYCLE"                       # Xe đạp truyền thống
    ELECTRIC_SCOOTER = "ELECTRIC_SCOOTER"     # Xe đạp điện

class VehicleStatus(str, Enum):
    ACTIVE = "ACTIVE"             # Đang sử dụng vé tháng gửi xe
    UNREGISTERED = "UNREGISTERED" # Đã chấm dứt hợp đồng gửi xe

# 4. Quản lý Đợt thu & Hóa đơn căn hộ (US-15..20)
class FeePeriodStatus(str, Enum):
    DRAFT = "DRAFT"         # Bản nháp kế toán đang rà soát
    PUBLISHED = "PUBLISHED" # Đã phát hành chính thức, mở cổng thanh toán
    CLOSED = "CLOSED"       # Đã khóa sổ kỳ thu, chuyển nợ tồn sang kỳ sau

class FeeCalculationMethod(str, Enum):
    PER_M2 = "PER_M2"                             # Nhân theo diện tích căn hộ (Phí dịch vụ, quản lý)
    FIXED_PER_HOUSEHOLD = "FIXED_PER_HOUSEHOLD"   # Thu cố định trên một hộ gia đình
    PER_VEHICLE = "PER_VEHICLE"                   # Nhân theo số lượng phương tiện của hộ
    VOLUNTARY = "VOLUNTARY"                       # Tự nguyện đóng góp (Quỹ từ thiện, khuyến học)

class BillStatus(str, Enum):
    UNPAID = "UNPAID"                 # Chưa thanh toán
    PARTIALLY_PAID = "PARTIALLY_PAID" # Đã nộp một phần tiền
    PAID = "PAID"                     # Đã nộp đủ 100% nghĩa vụ
    OVERDUE = "OVERDUE"               # Nợ quá thời hạn quy định

# 5. Thanh toán, Biên lai & Quỹ tự nguyện (US-21..28)
class PaymentMethod(str, Enum):
    CASH = "CASH"                     # Nộp tiền mặt trực tiếp tại quầy
    BANK_TRANSFER = "BANK_TRANSFER"   # Chuyển khoản ngân hàng / VietQR

class ReceiptStatus(str, Enum):
    VALID = "VALID"         # Biên lai có hiệu lực pháp lý
    CANCELLED = "CANCELLED" # Biên lai đã bị hủy do thu sai / lập nhầm

class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"   # Đợt vận động đang lên kế hoạch
    ACTIVE = "ACTIVE" # Đang tiếp nhận đóng góp tự nguyện
    CLOSED = "CLOSED" # Đã kết thúc đợt vận động và công khai quyết toán

# 6. Cổng dịch vụ Cư dân (US-29..35)
class EditRequestStatus(str, Enum):
    PENDING = "PENDING"   # Chờ Ban quản trị xem xét
    APPROVED = "APPROVED" # Đã phê duyệt và đồng bộ dữ liệu nhân khẩu
    REJECTED = "REJECTED" # Bị từ chối (có lý do kèm theo)

class ComplaintStatus(str, Enum):
    SUBMITTED = "SUBMITTED" # Cư dân đã gửi khiếu nại hóa đơn
    IN_REVIEW = "IN_REVIEW" # Kế toán đang đối soát số liệu
    RESOLVED = "RESOLVED"   # Đã giải quyết / Điều chỉnh hóa đơn
    REJECTED = "REJECTED"   # Bác bỏ khiếu nại
```

---

## 6. HỢP ĐỒNG GIAO DIỆN API & RESPONSE ENVELOPE (API CONTRACT)

### 6.1. Quy chuẩn Response Envelope (Pydantic Generic)
Mọi API trả về BẮT BUỘC tuân theo cấu trúc bao gói chuẩn tại `app/common/response.py`:

```python
from typing import Generic, TypeVar, Optional, Any, List
from pydantic import BaseModel

T = TypeVar("T")

class ResponseMeta(BaseModel):
    page: int = 1
    page_size: int = 10
    total_items: int = 0
    total_pages: int = 0

class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = "Thao tác thành công"
    meta: Optional[ResponseMeta] = None
```

#### Phản hồi Thành công (HTTP 200 / 201):
```json
{
  "success": true,
  "data": { ... },
  "message": "Thực hiện tác vụ thành công",
  "meta": {
    "page": 1,
    "pageSize": 10,
    "totalItems": 45,
    "totalPages": 5
  }
}
```

#### Phản hồi Thất bại (HTTP 4xx / 5xx):
```json
{
  "success": false,
  "error": {
    "code": "HOUSEHOLD_STILL_HAS_UNPAID_DEBT",
    "message": "Không thể đóng hồ sơ hộ gia đình do vẫn còn nợ phí chưa hoàn thành nghĩa vụ tài chính",
    "details": [
      {
        "field": "household_id",
        "issue": "Còn tồn đọng 1.450.000 VNĐ tại kỳ thu 2026-10"
      }
    ]
  }
}
```

### 6.2. Bảng Danh mục Mã lỗi Hệ thống (Error Code Registry)

| Mã lỗi Nghiệp vụ (`error.code`) | HTTP Status | Định nghĩa & Ngữ cảnh phát sinh theo AC |
| :--- | :---: | :--- |
| `VALIDATION_FAILED` | `400` | Dữ liệu đầu vào sai định dạng hoặc vi phạm ràng buộc Schema Pydantic. |
| `INVALID_PAYMENT_AMOUNT` | `400` | Số tiền thanh toán phải lớn hơn 0 (`AC-19.1`). |
| `UNAUTHORIZED` | `401` | Thiếu Bearer Token, Token hết hạn hoặc chữ ký không hợp lệ. |
| `FORBIDDEN_RESOURCE` | `403` | Tài khoản đăng nhập không có quyền truy cập Endpoint này. |
| `ENTITY_NOT_FOUND` | `404` | Không tìm thấy Căn hộ, Hộ gia đình, hoặc Hóa đơn theo ID. |
| `DUPLICATE_RESOURCE` | `409` | Trùng khóa duy nhất: Số CCCD, Biển số xe, hoặc Mã căn hộ. |
| `CONCURRENCY_CONFLICT` | `409` | Xung đột giao dịch đồng thời (Thử lại sau 1-2 giây). |
| `HOUSEHOLD_STILL_HAS_DEBT` | `422` | Vi phạm nghiệp vụ: Hộ còn nợ tiền không được phép chuyển đi. |
| `CANNOT_REMOVE_HOUSEHOLD_HEAD` | `422` | Không thể xóa/chuyển chủ hộ nếu hộ còn thành viên mà chưa đổi chủ (`AC-07.2`). |
| `RECEIPT_ALREADY_CANCELLED`| `422` | Biên lai đã hủy không được phép hủy lại lần thứ hai. |
| `RECEIPT_CANCELLATION_WINDOW_EXPIRED` | `422` | Quá thời hạn 24 giờ kể từ khi xuất; thủ quỹ không được tự hủy biên lai (`AC-22.1`). |
| `FEE_PERIOD_ALREADY_CLOSED`| `422` | Không thể gạch nợ hoặc sửa hóa đơn của kỳ thu đã khóa sổ. |
| `CAMPAIGN_NOT_ACTIVE` | `422` | Đợt vận động đã đóng hoặc chưa mở, không tiếp nhận đóng góp. |
| `INTERNAL_SERVER_ERROR` | `500` | Lỗi ngoại lệ hệ thống ngoài tầm kiểm soát. |

### 6.3. Chuẩn hóa Tham số Truy vấn & Headers
- **Headers bắt buộc:**
  * `Authorization: Bearer <jwt_token>` (áp dụng cho mọi API ngoại trừ `/api/v1/auth/login`).
  * `Content-Type: application/json`.
  * `X-Request-Id`: Chuỗi UUID định danh yêu cầu phục vụ truy vết log.
- **Tham số phân trang và lọc chuẩn trên URL:**
  * Mặc định: `page=1`, `page_size=10` (BẮT BUỘC khống chế: `1 <= page_size <= 100` để chống DoS).
  * URL chuẩn: `/api/v1/{resources}?page=1&page_size=10&sort_by=created_at&sort_order=desc`

---

## 7. HỢP ĐỒNG GIAO TIẾP DTO GIỮA 5 PHÂN HỆ (PYDANTIC SCHEMAS)

### Sơ đồ 3: Luồng Giao tiếp DTO Toàn diện giữa 5 Module
```mermaid
sequenceDiagram
    autonumber
    actor Resident as Cư dân (Portal)
    actor Cashier as Thủ quỹ / Thu ngân
    participant PortalMod as portal (Cổng cư dân)
    participant CashierMod as cashier (Thực thu & Quỹ)
    participant BillingMod as billing (Kế toán & Đợt thu)
    participant VehicleMod as vehicles (Phương tiện & Vé xe)
    participant ResidentMod as residents (Căn hộ & Cư dân)
    participant DB as Database (ACID)

    Note over ResidentMod,VehicleMod: 1. Lập đợt thu & Tính công nợ
    BillingMod->>ResidentMod: get_apartment_detail(apartment_id)
    ResidentMod-->>BillingMod: ApartmentDetailDTO (Diện tích m2)
    BillingMod->>VehicleMod: get_vehicle_summary(household_id)
    VehicleMod-->>BillingMod: VehicleCountDTO (Số xe ô tô, xe máy)
    BillingMod->>DB: Khởi tạo HouseholdBills & BillDetails

    Note over CashierMod,BillingMod: 2. Thực thu & Gạch nợ (ACID Transaction)
    Cashier->>CashierMod: Nhập số tiền thu tại quầy
    CashierMod->>BillingMod: execute_payment_transaction(cmd)
    BillingMod->>DB: Thực thi ACID Transaction (Chi tiết tại Sơ đồ 2)
    BillingMod-->>CashierMod: PaymentExecutionResultDTO

    Note over Resident,ResidentMod: 3. Cư dân gửi Yêu cầu chỉnh sửa & Khiếu nại
    Resident->>PortalMod: Gửi yêu cầu cập nhật nhân khẩu
    PortalMod->>ResidentMod: submit_edit_request(cmd)
    ResidentMod-->>PortalMod: EditRequestSummaryDTO (PENDING)
    Resident->>PortalMod: Gửi khiếu nại sai lệch hóa đơn
    PortalMod->>BillingMod: submit_fee_complaint(cmd)
    BillingMod-->>PortalMod: ComplaintSummaryDTO (SUBMITTED)
```

Toàn bộ DTO giao tiếp liên phân hệ được định nghĩa bằng **Pydantic v2 Schemas**:

### 7.1. Phân hệ Căn hộ & Cư dân (residents)
Định nghĩa tại: `app/schemas/resident.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from app.common.enums import HouseholdStatus, EditRequestStatus

class ApartmentDetailDTO(BaseModel):
    apartment_id: int
    room_number: str       # Ví dụ: "P.101"
    floor: int
    area_m2: float         # Ví dụ: 75.50
    status: str

class HouseholdSummaryDTO(BaseModel):
    household_id: int
    apartment_id: int
    household_code: str
    owner_name: str
    resident_count: int
    credit_balance: int = 0 # Số dư có hiện tại (VNĐ)
    status: HouseholdStatus

class SubmitEditRequestCommandDTO(BaseModel):
    household_id: int
    resident_id: int
    request_type: str       # ADD_MEMBER | REMOVE_MEMBER | UPDATE_INFO
    proposed_data: Dict[str, Any]
    document_proof_url: Optional[str] = None

class EditRequestSummaryDTO(BaseModel):
    request_id: int
    household_id: int
    status: EditRequestStatus
    submitted_at: str
```

### 7.2. Phân hệ Phương tiện (vehicles)
Định nghĩa tại: `app/schemas/vehicle.py`

```python
from pydantic import BaseModel

class VehicleCountDTO(BaseModel):
    household_id: int
    car_count: int = 0              # Số lượng ô tô
    motorbike_count: int = 0        # Số lượng xe máy
    bicycle_count: int = 0          # Số lượng xe đạp
    electric_scooter_count: int = 0  # Số lượng xe máy điện
```

### 7.3. Phân hệ Kế toán & Đợt thu (billing)
Định nghĩa tại: `app/schemas/billing.py`

```python
from pydantic import BaseModel
from typing import List, Optional
from app.common.enums import BillStatus, ComplaintStatus

class BillLineItemDTO(BaseModel):
    fee_code: str
    fee_name: str
    unit_price: int
    quantity: float
    discount_amount: int = 0
    total_amount: int
    paid_amount: int = 0

class BillCalculationResultDTO(BaseModel):
    bill_id: int
    household_id: int
    period_code: str              # Ví dụ: "2026-10"
    current_period_total: int     # Phí phát sinh kỳ này (VNĐ)
    previous_debt: int            # Nợ cũ lũy kế dồn về (VNĐ)
    credit_balance_applied: int   # Số dư có đã trừ (VNĐ)
    total_payable: int            # Tổng thực nộp cuối cùng (VNĐ)
    status: BillStatus
    items: List[BillLineItemDTO]

class SubmitFeeComplaintCommandDTO(BaseModel):
    household_id: int
    bill_id: int
    fee_code: str
    reason: str
    claimed_amount: Optional[int] = None

class ComplaintSummaryDTO(BaseModel):
    complaint_id: int
    bill_id: int
    status: ComplaintStatus
    created_at: str
```

### 7.4. Phân hệ Thực thu & Quỹ (cashier)
Định nghĩa tại: `app/schemas/cashier.py`

```python
from pydantic import BaseModel
from typing import Optional
from app.common.enums import PaymentMethod

class RecordPaymentCommandDTO(BaseModel):
    household_id: int
    billing_period_id: int
    cashier_id: str               # UUID của thủ quỹ thực hiện
    amount_received: int          # Số tiền khách nộp thực tế (VNĐ)
    payment_method: PaymentMethod # Tiền mặt / Chuyển khoản
    payer_name: str               # Tên người nộp
    notes: Optional[str] = None

class PaymentExecutionResultDTO(BaseModel):
    receipt_id: int
    receipt_number: str           # Ví dụ: "BL-202610-0012"
    amount_received: int
    allocated_to_debt: int        # Số tiền dùng gạch nợ các khoản
    excess_to_credit_balance: int # Tiền thừa cộng vào số dư có
    remaining_household_debt: int # Nợ còn tồn lại sau thanh toán
    paid_at: str                  # ISO-8601 UTC

class RecordDonationCommandDTO(BaseModel):
    campaign_id: int
    household_id: Optional[int] = None
    donor_name: str
    amount: int
    payment_method: PaymentMethod
    notes: Optional[str] = None
    cashier_id: str

class DonationReceiptDTO(BaseModel):
    donation_id: int
    receipt_number: str
    campaign_name: str
    donor_name: str
    amount: int
    paid_at: str
```

### 7.5. Phân hệ Cổng cư dân (portal)
Định nghĩa tại: `app/schemas/portal.py`

```python
from pydantic import BaseModel
from typing import List, Optional
from app.schemas.resident import HouseholdSummaryDTO, EditRequestSummaryDTO
from app.schemas.billing import BillCalculationResultDTO
from app.schemas.cashier import PaymentExecutionResultDTO

class ResidentDashboardOverviewDTO(BaseModel):
    household: HouseholdSummaryDTO
    current_bill: Optional[BillCalculationResultDTO] = None
    payment_history: List[PaymentExecutionResultDTO] = []
    pending_requests: List[EditRequestSummaryDTO] = []
    active_campaigns: List[dict] = []
```

---

## 8. KIẾN TRÚC BẢO MẬT & NGỮ CẢNH PHIÊN (SECURITY & FASTAPI DEPENDENCIES)

### 8.1. Sơ đồ 4: Luồng Xác thực & Phân quyền RBAC (Security Sequence)
```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng (Browser / Swagger)
    participant FastAPI as FastAPI Router Endpoint
    participant DepToken as oauth2_scheme (Bearer Token)
    participant DepAuth as get_current_user Dependency
    participant DepRole as require_role Dependency
    participant Service as Business Service (Python)

    User->>FastAPI: Gửi Request + Header `Authorization: Bearer <Token>`
    FastAPI->>DepToken: Trích xuất chuỗi Token từ Header
    alt Token thiếu hoặc không đúng định dạng
        DepToken-->>User: Trả về HTTP 401 Unauthorized
    else Token hợp lệ
        DepToken->>DepAuth: Chuyển token để giải mã
        DepAuth->>DepAuth: jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        DepAuth->>DepRole: Trả về đối tượng AuthenticatedUser
        alt User không sở hữu Role được yêu cầu
            DepRole-->>User: Ném HTTPException(status_code=403, detail="FORBIDDEN_RESOURCE")
        else Role hợp lệ
            DepRole->>FastAPI: Tiêm current_user vào hàm xử lý endpoint
            FastAPI->>Service: Thực thi nghiệp vụ với current_user.user_id
            Service-->>User: Trả về kết quả ResponseEnvelope (HTTP 200/201)
        end
    end
```

### 8.2. Cấu trúc JWT Payload & Thuật toán Ký HS256
- **Thuật toán ký BẮT BUỘC:** **`HS256`** (HMAC-SHA256), ký bằng khóa bí mật `SECRET_KEY` từ file `.env`.
- Cấu trúc Claims định danh trong Token:

```python
from pydantic import BaseModel
from typing import Optional
from app.common.enums import UserRole

class JwtPayload(BaseModel):
    sub: str                    # UUID của user trong bảng `users`
    username: str               # Tên đăng nhập (ví dụ: "admin", "ketoan")
    role: UserRole              # ADMIN | ACCOUNTANT | CASHIER | RESIDENT
    household_id: Optional[int] = None # None đối với cán bộ; Có ID nếu là Cư dân
    exp: int                    # Thời điểm hết hạn (Unix timestamp)

class AuthenticatedUser(BaseModel):
    user_id: str
    username: str
    role: UserRole
    household_id: Optional[int] = None
```

### 8.3. Quy chuẩn Trích xuất Ngữ cảnh bằng FastAPI Depends
Mọi Endpoint phân quyền BẮT BUỘC sử dụng cú pháp Dependency Injection cực kỳ trực quan của FastAPI:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, require_role
from app.common.enums import UserRole
from app.schemas.auth import AuthenticatedUser
from app.schemas.cashier import RecordPaymentCommandDTO

router = APIRouter(prefix="/api/v1/bills", tags=["Billing & Cashier"])

@router.post("/{bill_id}/pay")
def pay_bill(
    bill_id: int,
    cmd: RecordPaymentCommandDTO,
    current_user: AuthenticatedUser = Depends(require_role([UserRole.CASHIER, UserRole.ADMIN]))
):
    # current_user tự động được tiêm vào, không cần query lại CSDL
    return cashier_service.process_payment(bill_id, cmd, current_user.user_id)
```

### 8.4. Cơ chế Ghi vết & Xử lý Ngoại lệ Xuyên suốt (Cross-Cutting Concerns)
- **Hàm Ghi vết Kiểm toán (`app/common/audit_logger.py`):** Bắt buộc gọi hàm ghi vết khi thực hiện các hành động nhạy cảm (`US-02` đổi chủ hộ, `US-16` đổi giá phí, `US-22` hủy biên lai):
  ```python
  def log_audit_action(
      db: Session,
      user_id: str,
      action: str,          # CREATE | UPDATE | DELETE | CANCEL
      entity_name: str,     # households, fee_rates, receipts
      entity_id: str,
      old_value: dict = None,
      new_value: dict = None
  ):
      # Tự động ghi bản ghi bất biến vào bảng audit_logs
      ...
  ```
- **Xử lý Ngoại lệ Toàn cục (Global Exception Handler):** Bắt `HTTPException` và `RequestValidationError` tại `app/main.py` để tự động trả về định dạng JSON Error Envelope chuẩn.

---

## 9. MÔI TRƯỜNG CỤC BỘ & BỘ DỮ LIỆU HẠT GIỐNG (GOLDEN SEED DATA)

### 9.1. Tệp Biến Môi trường Mẫu (`.env.example`)
Tạo file `.env` tại thư mục `backend/`:

```env
# Cấu hình Ứng dụng Backend FastAPI
APP_NAME="BlueMoon RMS API"
DEBUG=True
PORT=8000

# Cơ sở dữ liệu (Mặc định dùng PostgreSQL, máy yếu có thể đổi sang SQLite để test)
# Option 1 - PostgreSQL:
DATABASE_URL="postgresql://bluemoon_admin:BlueMoonPass2026@localhost:5432/bluemoon_db"
# Option 2 - SQLite (Dành cho máy sinh viên không cài được PostgreSQL/Docker):
# DATABASE_URL="sqlite:///./bluemoon_dev.db"

# Khóa bí mật JWT
SECRET_KEY="bluemoon_super_secret_jwt_key_2026_hust_soict"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440 # 24 giờ

# Danh sách Frontend Origins được phép gọi API (CORS)
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### 9.2. Kịch bản Cài đặt & Chạy Server Cục bộ (Virtualenv)
Mỗi thành viên chỉ cần mở Terminal tại thư mục `backend/` và gõ 4 lệnh cơ bản:

```bash
# 1. Tạo môi trường ảo Python
python -m venv venv

# 2. Kích hoạt môi trường ảo:
# Trên Windows:
venv\Scripts\activate
# Trên macOS / Linux:
source venv/bin/activate

# 3. Cài đặt toàn bộ thư viện:
pip install -r requirements.txt

# 4. Chạy nạp dữ liệu mẫu và khởi động server:
python app/seed.py
uvicorn app.main:app --reload --port 8000
```
*Sau khi chạy xong, mở ngay trình duyệt vào `http://localhost:8000/docs` để kiểm thử toàn bộ API trên giao diện Swagger.*

### 9.3. Danh mục Dữ liệu Hạt giống Vàng bao phủ Ca Biên (Golden Seed Records)
Script `app/seed.py` tự động nạp sẵn dữ liệu kiểm thử đầy đủ:

#### 1. Bốn Tài khoản Đăng nhập Mặc định (Mật khẩu chung: `BlueMoon@2026`):
| Username | Role | Household gắn kết | Mục đích kiểm thử tính năng |
| :--- | :--- | :---: | :--- |
| `admin` | `ADMIN` | `None` | Phân quyền, quản lý tài khoản, xem Audit Log (`US-36..43`). |
| `ketoan` | `ACCOUNTANT` | `None` | Lập đợt thu, cấu hình biểu phí, xuất báo cáo (`US-15..20`). |
| `thuquy` | `CASHIER` | `None` | Thu tiền mặt/chuyển khoản, gạch nợ, in biên lai (`US-21..28`). |
| `cudan101` | `RESIDENT` | `Hộ P.101` | Tra cứu hóa đơn, lịch sử nộp, gửi kiến nghị (`US-29..35`). |

#### 2. Dữ liệu Căn hộ & Hộ gia đình Mẫu (Bao phủ đủ 3 kịch bản tài chính):
* **Căn hộ `P.101` (ID: 1) - [Kịch bản 1: Hộ chuẩn, không nợ, không dư]:**
  * Diện tích: $75.0\text{ m}^2$, tầng 1, trạng thái `ACTIVE`.
  * Hộ cư ngụ: Hộ ông **Nguyễn Văn An** (CCCD: `001099012345`).
  * Nhân khẩu: 3 người (Chủ hộ, Vợ, 1 Con).
  * Xe cộ: 1 Ô tô (`30A-999.88`), 2 Xe máy (`29B1-123.45`, `29B1-678.90`).
  * Tình trạng tài chính: Nợ cũ = $0\text{ VNĐ}$, Số dư có (`credit_balance`) = $0\text{ VNĐ}$.
* **Căn hộ `P.102` (ID: 2) - [Kịch bản 2: Hộ nợ cũ dồn về & Kiểm thử nộp thiếu]:**
  * Diện tích: $90.5\text{ m}^2$, tầng 1, trạng thái `ACTIVE`.
  * Hộ cư ngụ: Hộ bà **Trần Thị Bích** (CCCD: `001088054321`).
  * Tình trạng tài chính: **Đang nợ tồn $1.250.000\text{ VNĐ}$** từ kỳ `2026-09`.
  * *Mục đích kiểm thử:* Kiểm tra công thức dồn nợ cũ của Phân hệ Đợt thu và quy tắc gạch nợ từng phần theo `AC-19.2` của Phân hệ Thực thu.
* **Căn hộ `P.201` (ID: 3) - [Kịch bản 3: Hộ có sẵn Số dư có (Credit Balance)]:**
  * Diện tích: $120.0\text{ m}^2$, tầng 2, trạng thái `ACTIVE`.
  * Hộ cư ngụ: Hộ ông **Lê Hoàng Long** (CCCD: `001077098765`).
  * Tình trạng tài chính: Nợ cũ = $0\text{ VNĐ}$, **Đang có sẵn Số dư có = $500.000\text{ VNĐ}$**.
  * *Mục đích kiểm thử:* Kiểm tra tính năng tự động cấn trừ số dư có vào hóa đơn kỳ mới phát hành.

#### 3. Biểu giá Phí Chuẩn (Kỳ mẫu: `2026-10`):
* Phí dịch vụ chung cư (`FEE_SERVICE`): $16.500\text{ VNĐ/m}^2/\text{tháng}$ (Tính theo diện tích).
* Phí quản lý chung cư (`FEE_MANAGEMENT`): $7.000\text{ VNĐ/m}^2/\text{tháng}$ (Tính theo diện tích).
* Vé gửi ô tô (`VEHICLE_CAR`): $1.200.000\text{ VNĐ/xe/tháng}$.
* Vé gửi xe máy (`VEHICLE_MOTO`): $120.000\text{ VNĐ/xe/tháng}$.

---

## 10. KỶ LUẬT GIT FLOW & TIÊU CHUẨN XONG (DEFINITION OF DONE)

### 10.1. Quy chuẩn Nhánh & Commit
- **Quy ước đặt tên nhánh:**
  * Tính năng mới: `feat/US-{mã}-{tên-ngắn}` (Ví dụ: `feat/US-17-tinh-phi-thang`).
  * Sửa lỗi: `fix/US-{mã}-{tên-ngắn}` (Ví dụ: `fix/US-19-sai-cong-don-so-du-co`).
- **Quy ước Commit Message (Conventional Commits):**
  * `feat(billing): them cong thuc tru mien giam theo AC-17.1`
  * `fix(residents): chan xoa chu ho khi con du no phi theo AC-02.3`
  * `test(cashier): them unit test pytest cho quy trinh gach no acid`

### 10.2. Ma trận Cặp Review Chéo Bắt buộc (Peer Review Matrix)
Để triệt tiêu lỗi cục bộ và chia sẻ ngữ cảnh kiến trúc, quy định cặp review chéo:

```
[Phân hệ Căn hộ & Cư dân] <── Peer Review ──> [Phân hệ Phương tiện & Gửi xe]
[Phân hệ Thực thu & Quỹ] <── Peer Review ──> [Phân hệ Cổng Cư dân & Tra cứu]
                     ▲                               ▲
                     └── Gatekeeper: System Architect (Lead) ─────┘
```

- **Quy tắc Phê duyệt (Approval Policy):**
  * Mỗi PR BẮT BUỘC có tối thiểu **1 chữ ký Approve** từ thành viên cặp chéo.
  * Mọi PR có chỉnh sửa vào `alembic/`, `app/common/`, hoặc tầng Auth BẮT BUỘC phải có thêm chữ ký của **TV3 (Lead Architect)**.
  * **KHÔNG ĐƯỢC PHÉP tự merge PR của chính mình**.

### 10.3. Bảng Tiêu chuẩn Xong (Definition of Done - DoD Checklist)
Một Pull Request chỉ được phép merge vào nhánh `develop` khi thỏa mãn trọn vẹn 5 tiêu chí:
- [ ] **Linter sạch:** Chạy `flake8 app` hoặc `ruff check app` không phát sinh lỗi cú pháp.
- [ ] **Bảo toàn Core Schemas:** Không tự ý sửa đổi file trong `app/common/` hoặc `app/models/` nếu chưa có thông báo kiến trúc.
- [ ] **Bằng chứng Kiểm thử (Test Evidence):** Đính kèm ảnh chụp màn hình Swagger UI test thành công hoặc lệnh `pytest` chạy xanh.
- [ ] **Không làm hỏng Seed Data:** Chạy lại `python app/seed.py` thành công không phát sinh lỗi khóa ngoại.
- [ ] **Đúng chuẩn Envelope:** Mọi API mới viết đều trả về đúng format `ResponseEnvelope` và chuẩn mã lỗi HTTP.

---

## 11. KHUNG PHÂN ĐỊNH TRÁCH NHIỆM & MA TRẬN CAM KẾT KỸ THUẬT

Tài liệu này xác lập khung trách nhiệm kỹ thuật và ranh giới theo từng Module chức năng. Danh sách phân công nhân sự cụ thể cho từng thành viên sẽ được thảo luận, thống nhất và biểu quyết chính thức tại phiên họp Sprint Planning trước khi mở nhánh lập trình.

Mọi thành viên khi được giao quyền sở hữu phân hệ (Module Owner) BẮT BUỘC phải ký cam kết tuân thủ toàn bộ các quy chuẩn kiến trúc đã được đặc tả trong tài liệu này:

| STT | Phân hệ / Khối chức năng | Phạm vi User Stories | Vai trò Kỹ thuật | Nhân sự phụ trách | Trạng thái Cam kết |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **1** | Phân hệ Căn hộ & Cư dân (`app/routers/residents.py`) | Quản lý Căn hộ, Cư dân, Hộ khẩu (`US-01..08`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
| **2** | Phân hệ Phương tiện & Vé xe (`app/routers/vehicles.py`) | Quản lý Phương tiện, Vé xe tháng/lượt (`US-09..14`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
| **3** | Kiến trúc lõi, Quản trị Auth & Đợt thu (`app/core`, `billing.py`) | Hệ thống Core, Auth/RBAC, Biểu phí, Lập đợt thu (`US-15..20`, `US-36..43`) | System Architect / Backend Lead | Lê Trường Giang (Chủ trì kỹ thuật) | Đã phê duyệt khung |
| **4** | Phân hệ Thực thu & Quỹ (`app/routers/cashier.py`) | Thu phí tại quầy/chuyển khoản, Quỹ tự nguyện, Biên lai (`US-21..28`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
| **5** | Phân hệ Cổng cư dân & Tra cứu (`app/routers/portal.py`) | Portal Cư dân, Tra cứu hóa đơn, Gửi yêu cầu/khiếu nại (`US-29..35`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
