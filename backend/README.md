# ⚙️ Backend API Server - Chung Cư BlueMoon (Python FastAPI)

Thư mục này chứa toàn bộ mã nguồn xử lý nghiệp vụ (Business Logic), kết nối Cơ sở dữ liệu, phân quyền RBAC, bảo mật an ninh và cung cấp hệ thống RESTful API chuẩn OpenAPI 3.0.3 cho dự án **Quản lý & Thu phí Chung Cư BlueMoon**.

---

## 🛠️ 1. Ngôn ngữ & Công nghệ sử dụng (Tech Stack)

* **Ngôn ngữ lập trình:** **Python 3.10+** (Môi trường phát triển TV1: Python 3.14.2 tại `backend/venv`).
* **Web Framework:** **FastAPI 0.162+** (ASGI async, hỗ trợ OpenAPI 3.0.3 tự động tại `/docs` và `/redoc`).
* **ORM & Quản lý CSDL:** **SQLAlchemy 2.0** (Declarative 2.0 Style) + **Alembic**.
* **Database Engine:** **PostgreSQL 15+** (Hỗ trợ 28 bảng theo [database/01_schema.sql](../database/01_schema.sql)).
* **Bảo mật & Xác thực (`NFR-001`, `EP-05`, `US-44`, `US-28`, `US-29`):**
  * `bcrypt 5.0+`: Băm mật khẩu an toàn với work factor rounds $\ge 12$ chống tấn công brute-force (`AC-44.1`).
  * `PyJWT 2.15+`: Sinh và xác thực JWT Access Token (HS256, hạn 8 giờ / 28.800 giây).
  * `RBAC Guard Middleware`: Kiểm soát quyền truy cập theo vai trò trên từng endpoint (`US-31`).
  * `IDOR Defense`: Kiểm soát chống truy cập chéo dữ liệu giữa các hộ gia đình cư dân (`AC-44.2`).
* **Kiểm thử tự động (Automated Testing):**
  * `pytest 9.0+`, `pytest-asyncio`, `httpx`: Môi trường kiểm thử độc lập SQLite in-memory (`StaticPool`), cô lập hoàn toàn giữa các test case, đạt **433 test cases tự động** (100% PASS).
* **Xử lý Excel & Báo cáo PDF (`US-04`, `US-11`, `US-20`, `US-26`):**
  * `pandas` & `openpyxl`: Import danh sách căn hộ/nhân khẩu từ Excel (`DOC-01`) và trích xuất báo cáo.
  * `reportlab` / `weasyprint`: Xuất hóa đơn, biên lai thu phí (`DOC-02`) có đóng dấu `BẢN SAO`.

---

## 👥 2. Phân công & Cấu trúc thư mục `backend/`

Phân hệ Backend do **2 thành viên** phụ trách theo mô hình Peer-to-Peer:  
* `TV1: Lê Trường Giang` | Backend Developer
* `TV2: Nguyễn Việt Tùng` | Backend Developer

```text
backend/
├── app/
│   ├── main.py                      # Khởi chạy FastAPI, cấu hình CORS & Error Handlers chuẩn
│   ├── core/                        # Cấu hình hệ thống cốt lõi
│   │   ├── config.py                # Đọc biến môi trường (.env: DATABASE_URL, JWT_SECRET,...)
│   │   ├── database.py              # Kết nối PostgreSQL (SQLAlchemy 2.0 Engine & SessionLocal ACID)
│   │   ├── security.py              # Hàm băm bcrypt, verify password, JWT token, validate độ mạnh
│   │   └── rbac_middleware.py       # Middleware RBAC Guard, IDOR defense & Bearer authentication
│   │
│   ├── models/                      # Định nghĩa ORM Models (SQLAlchemy 2.0)
│   │   ├── base.py                  # Base class & TimestampMixin (created_at, updated_at)
│   │   ├── user.py                  # Bảng users, roles, audit_logs (Cụm tối thiểu Sprint 1)
│   │   ├── apartment.py             # Bảng apartments, households, occupancies, residents
│   │   └── fee.py                   # Bảng fee_types (Danh mục khoản thu)
│   │
│   ├── schemas/                     # Pydantic v2 Models (Khớp 100% docs/openapi.yaml)
│   │   ├── auth.py                  # LoginRequest, LoginResponse, ChangePasswordRequest, UserResponse
│   │   ├── common.py                # Schema Error, ErrorDetail, PageMeta dùng chung
│   │   └── ...
│   │
│   ├── routers/                     # Router API Modules theo tiền tố /api/v1
│   │   └── auth.py                  # POST /login, POST /logout, GET /me, POST /change-password
│   │
│   └── utils/                       # Tiện ích dùng chung
│       └── audit_logger.py          # Helper ghi nhật ký kiểm toán bất biến
│
├── tests/                           # Bộ kiểm thử tự động (433 test cases: 100% Pass)
│   ├── conftest.py                  # Fixtures SQLite in-memory (StaticPool), Seed test users
│   ├── test_us44_security.py        # 238 test cases: Bcrypt rounds >= 12, RBAC, IDOR Defense
│   ├── test_us28_auth.py            # 114 test cases: Login, Logout, Me, Brute-force Lockout 15m
│   └── test_us29_change_password.py # 81 test cases: Đổi mật khẩu, bắt buộc đổi lần đầu, AC-29.1
│
├── .env.example                     # Mẫu biến môi trường
├── pytest.ini                       # Cấu hình pytest (asyncio loop scope)
├── requirements.txt                 # Danh sách gói phụ thuộc Python
└── README.md                        # Tài liệu hướng dẫn này
```

---

## 📊 3. Tiến độ thực hiện User Stories (Sprint 1)

| Mã US | Tên User Story | SP | Người thực hiện | Người Review | Số Test Cases | Trạng thái |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **US-44** | Kiến trúc An ninh, Băm mật khẩu Bcrypt & Chống IDOR | 4 | TV2: Nguyễn Việt Tùng | TV1: Lê Trường Giang | 238 tests | **HOÀN THÀNH** |
| **US-28** | Đăng nhập hệ thống & Khóa tài khoản Brute-force | 4 | TV1: Lê Trường Giang | TV2: Nguyễn Việt Tùng | 114 tests | **HOÀN THÀNH** |
| **US-29** | Đổi mật khẩu cá nhân & Buộc đổi lần đầu | 2 | TV1: Lê Trường Giang | TV2: Nguyễn Việt Tùng | 81 tests | **HOÀN THÀNH** |
| **US-30** | Quản lý tài khoản người dùng & Tự tạo tài khoản Hộ | 4 | TV1 / TV2 | Chéo TV | - | *Sprint 1 Tiếp theo* |
| **US-31** | Phân quyền vai trò RBAC Guard | 2 | TV1 / TV2 | Chéo TV | - | *Sprint 1 Tiếp theo* |
| **US-32** | Xem nhật ký kiểm toán (Audit Logs) | 2 | TV1 / TV2 | Chéo TV | - | *Sprint 1 Tiếp theo* |

---

## 📡 4. Danh sách API Endpoints Phân hệ Auth (`/api/v1/auth`)

Toàn bộ các endpoint tuân thủ 100% hợp đồng API tại [docs/openapi.yaml](../docs/openapi.yaml):

| Phương thức | Đường dẫn | Quyền truy cập | Mã phản hồi | Mô tả nghiệp vụ |
| :---: | :--- | :---: | :---: | :--- |
| **POST** | `/api/v1/auth/login` | Public | `200`, `400`, `401`, `423` | Đăng nhập hệ thống. Cấp JWT token 8h. Nhập sai 5 lần liên tiếp tự khóa 15 phút (`ACCOUNT_LOCKED`). |
| **POST** | `/api/v1/auth/logout` | Authenticated | `204`, `401` | Thu hồi phiên làm việc hiện tại của người dùng. |
| **GET** | `/api/v1/auth/me` | Authenticated | `200`, `401` | Lấy thông tin hồ sơ (Profile) của người dùng hiện tại kèm vai trò. |
| **POST** | `/api/v1/auth/change-password` | Authenticated | `204`, `400`, `401` | Đổi mật khẩu cá nhân (hỗ trợ cả khi `must_change_password=True`). Sai mật khẩu cũ trả `400 WRONG_OLD_PASSWORD`. Mật khẩu mới bám chuẩn `AC-29.1`. |

---

## 🚀 5. Hướng dẫn Cài đặt & Chạy ứng dụng

### 5.1. Khởi tạo môi trường ảo Python
Mở Terminal tại thư mục gốc `backend/`:

```bash
# 1. Tạo môi trường ảo (Virtual Environment)
python -m venv venv

# 2. Kích hoạt môi trường ảo
# Trên Windows (PowerShell):
venv\Scripts\Activate.ps1
# Trên macOS / Linux:
source venv/bin/activate

# 3. Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 4. Sao chép cấu hình môi trường
copy .env.example .env     # Trên Windows
# cp .env.example .env     # Trên Linux/macOS
```

### 5.2. Chạy bộ kiểm thử tự động (Automated Test Suite)
Môi trường test chạy trên SQLite in-memory độc lập với CSDL PostgreSQL:

```bash
# Chạy toàn bộ 433 test cases hệ thống
pytest -c pytest.ini tests -v

# Chạy riêng bộ test US-29 (Đổi mật khẩu cá nhân - 81 tests)
pytest tests/test_us29_change_password.py -v

# Chạy riêng bộ test US-28 (Đăng nhập & Khóa brute-force - 114 tests)
pytest tests/test_us28_auth.py -v

# Chạy riêng bộ test US-44 (An ninh & Chống IDOR - 238 tests)
pytest tests/test_us44_security.py -v
```

### 5.3. Khởi chạy Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Sau khi server khởi động thành công, truy cập:
* **Swagger UI API Explorer:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
