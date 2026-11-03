# ⚙️ Backend API Server - Chung Cư BlueMoon (Python FastAPI)

Thư mục này chứa toàn bộ mã nguồn xử lý nghiệp vụ (Business Logic), kết nối Cơ sở dữ liệu, phân quyền RBAC và cung cấp RESTful API cho giao diện Frontend.

---

## 🛠️ 1. Ngôn ngữ & Công nghệ sử dụng (Tech Stack)

* **Ngôn ngữ lập trình:** **Python 3.10+** (Môi trường phát triển TV1: Python 3.14.2)
* **Web Framework:** **FastAPI** (Tốc độ cao, hỗ trợ async, tự động sinh tài liệu Swagger UI tại `/docs`).
* **ORM & Quản lý CSDL:** **SQLAlchemy 2.0** + **Alembic** (Quản lý phiên bản cấu trúc bảng).
* **Database Engine:** **PostgreSQL 15+** (28 bảng khớp [database/01_schema.sql](../database/01_schema.sql)).
* **Bảo mật & Xác thực (`NFR-001`, `EP-05`, `US-44`, `US-28`):**
  * `bcrypt`: Băm và xác thực mật khẩu an toàn theo thuật toán `bcrypt` chuẩn (rounds $\ge 12$).
  * `pyjwt[crypto]`: Tạo và giải mã `JWT Token` (thuật toán HS256, access token hết hạn sau 8 giờ).
* **Kiểm thử tự động (Automated Testing):**
  * `pytest`, `pytest-asyncio`, `httpx`: Bộ test suite tự động kiểm thử toàn bộ API endpoints, RBAC middleware, và IDOR defense trên môi trường SQLite in-memory (StaticPool), gồm 352 test cases tự động.
* **Xử lý Excel & In ấn PDF (`US-04`, `US-11`, `US-20`, `US-26`):**
  * `pandas` & `openpyxl`: Đọc file Excel khi Import danh sách hộ và xuất báo cáo thu phí/cư trú.
  * `reportlab` hoặc `weasyprint`: Xuất biên lai điện tử (`DOC-02`) và giấy báo phí ra định dạng PDF chuẩn tiếng Việt.

---

## 👥 2. Phân công & Cấu trúc thư mục `backend/`

Phân hệ Backend do **2 thành viên** phụ trách: `TV1: Lê Trường Giang` & `TV2: Nguyễn Việt Tùng`.  
Cấu trúc mã nguồn bám sát 100% lược đồ CSDL [database/01_schema.sql](../database/01_schema.sql) (28 bảng) và Hợp đồng API [docs/openapi.yaml](../docs/openapi.yaml):

```text
backend/
├── app/
│   ├── main.py                      # File khởi chạy ứng dụng FastAPI, cấu hình CORS & Exception handlers
│   ├── core/                        # Cấu hình hệ thống cốt lõi
│   │   ├── config.py                # Đọc biến môi trường (.env: DATABASE_URL, JWT_SECRET, ALGORITHM)
│   │   ├── database.py              # Kết nối PostgreSQL (SQLAlchemy 2.0 Engine & SessionLocal ACID)
│   │   ├── security.py              # Hàm băm bcrypt, xác thực password, tạo JWT Token
│   │   └── rbac_middleware.py       # RBAC Guard kiểm tra quyền ADMIN/ACCOUNTANT/TREASURER/RESIDENT (US-31)
│   │
│   ├── models/                      # Định nghĩa 28 bảng CSDL (SQLAlchemy ORM Models khớp 01_schema.sql)
│   │   ├── user.py                  # Bảng users, roles, audit_logs, backup_jobs, document_counters
│   │   ├── apartment.py             # Bảng apartments, households, apartment_occupancies, residents, vehicles
│   │   ├── residency.py             # Bảng temporary_residences, temporary_absences, residency_events
│   │   ├── fee.py                   # Bảng service_providers, fee_types, fee_rates, fee_exemptions
│   │   ├── billing.py               # Bảng billing_periods, utility_readings, invoices, invoice_items
│   │   ├── payment.py               # Bảng payments, payment_allocations, household_credit_ledger, provider_settlements
│   │   ├── donation.py              # Bảng donation_campaigns, donations
│   │   └── portal.py                # Bảng profile_change_requests
│   │
│   ├── schemas/                     # Pydantic v2 Models (Khớp 100% docs/openapi.yaml)
│   │   ├── auth.py                  # LoginRequest, LoginResponse, ChangePasswordRequest
│   │   ├── user.py                  # UserCreate, UserUpdate, UserRoleUpdate, UserPage
│   │   ├── apartment.py             # ApartmentCreate, ApartmentUpdate, ApartmentPage
│   │   ├── household.py             # HouseholdCreate, HouseholdUpdate, HouseholdTransferRequest
│   │   ├── resident.py              # ResidentCreate, ResidentUpdate, TemporaryStayCreate
│   │   ├── fee.py                   # FeeTypeCreate, FeeTypeUpdate, FeeRateCreate
│   │   ├── billing.py               # BillingPeriodCreate, InvoicePage, UtilityReadingCreate
│   │   ├── payment.py               # PaymentCreate (kèm Idempotency-Key), ReceiptResponse
│   │   ├── donation.py              # DonationCampaignCreate, DonationRecordCreate
│   │   └── common.py                # Error, PageMeta
│   │
│   ├── routers/                     # 17 Router Modules (Hiện thực 97 endpoints theo openapi.yaml)
│   │   ├── auth.py                  # POST /auth/login, POST /auth/logout, GET /auth/me, POST /auth/change-password
│   │   ├── users.py                 # Quản lý tài khoản, phân quyền vai trò, khóa/mở khóa
│   │   ├── system.py                # Sao lưu CSDL, xem lịch sử sao lưu, Audit Log
│   │   ├── apartments.py            # Quản lý căn hộ vật lý (diện tích, tầng)
│   │   ├── households.py            # Hộ gia đình, đổi chủ hộ, chuyển nhượng căn hộ
│   │   ├── residents.py             # Nhân khẩu, biến động dân cư
│   │   ├── temporary_stays.py       # Đăng ký tạm trú, tạm vắng, cảnh báo hết hạn
│   │   ├── import_data.py           # Import danh sách từ Excel (DOC-01)
│   │   ├── portal.py                # Cổng cư dân tra cứu thông tin hộ, công nợ
│   │   ├── change_requests.py       # Duyệt đề nghị chỉnh sửa thông tin từ cư dân
│   │   ├── fee_types.py             # Danh mục khoản thu, đơn giá, miễn giảm phí
│   │   ├── service_providers.py     # Thu hộ & đối soát nhà cung cấp điện nước
│   │   ├── vehicles.py              # Phương tiện, đăng ký gửi xe
│   │   ├── billing.py               # Tạo kỳ thu, chốt phí, nhập chỉ số điện nước
│   │   ├── cashier.py               # Quầy thu tiền, gạch nợ tự động, in biên lai
│   │   ├── donations.py             # Vận động quỹ tự nguyện, in phiếu thu
│   │   └── reports.py               # Omnibox tìm kiếm, báo cáo tài chính, báo cáo Công an, Dashboard
│   │
│   └── utils/                       # Hàm tiện ích dùng chung
│       ├── audit_logger.py          # Ghi log nhạy cảm vào bảng audit_logs
│       ├── excel_handler.py         # Xử lý import Excel và export báo cáo biểu mẫu
│       ├── pdf_generator.py         # Xuất hóa đơn/biên lai PDF có đóng dấu "BẢN SAO"
│       └── backup_service.py        # Dịch vụ gọi pg_dump sao lưu CSDL tự động 02:00 sáng
│
├── tests/                           # Unit test & Integration test (352 test cases: US-44, US-28)
├── .env.example                     # Mẫu biến môi trường
├── pytest.ini                       # Cấu hình pytest (asyncio loop scope)
├── requirements.txt                 # Danh sách gói phụ thuộc Python
└── README.md                        # Tài liệu hướng dẫn này
```

---

## 🚀 3. Hướng dẫn cài đặt và chạy Backend (Cho Backend Developers)

Mở Terminal tại thư mục `backend/` và chạy lần lượt các lệnh sau:

```bash
# 1. Tạo môi trường ảo Python (Virtual Environment)
python -m venv venv

# 2. Kích hoạt môi trường ảo
# - Trên Windows:
venv\Scripts\activate
# - Trên macOS / Linux:
source venv/bin/activate

# 3. Cài đặt các thư viện cần thiết từ requirements.txt
pip install -r requirements.txt

# 4. Tạo file cấu hình môi trường .env từ mẫu .env.example
copy .env.example .env     # Trên Windows
# cp .env.example .env     # Trên Linux/macOS

# 5. Chạy bộ kiểm thử tự động (Unit & Integration tests)
pytest -c pytest.ini tests -v

# 6. Chạy Server phát triển (Development Server)
uvicorn app.main:app --reload --port 8000
```

* Sau khi chạy thành công, mở trình duyệt truy cập:
  * **Trang API Docs tự động (Swagger UI):** `http://localhost:8000/docs`
  * **Trang Redoc:** `http://localhost:8000/redoc`
