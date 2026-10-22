# HỢP ĐỒNG KỸ THUẬT NỀN TẢNG (PRE-CODING BASELINE)
## HỆ THỐNG QUẢN LÝ VÀ THU PHÍ CHUNG CƯ BLUEMOON (BLUEMOON RMS)

| THÔNG TIN QUẢN TRỊ CẤU HÌNH | CHI TIẾT ĐẶC TẢ |
| :--- | :--- |
| **Mã tài liệu (Document ID)** | `BM-BASE-01` |
| **Phiên bản (Version)** | `v1.2-APPROVED` |
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
| `v1.1-APPROVED` | 2026-10-22 | Lê Trường Giang | Bổ sung DTO hai chiều TV5, Quỹ đóng góp TV4, Mức cô lập Serializable, Giao thức Schema Freeze, `onDelete: Restrict`, và Edge Cases Seed Data. | `SUPERSEDED` |
| `v1.2-APPROVED` | 2026-10-22 | Lê Trường Giang | Bổ sung Sơ đồ chuyên biệt ACID Transaction, phân định chuẩn `DATE` vs `TIMESTAMPTZ`, cấm lệnh `prisma db push`, mở rộng Error Code Registry, và tách biệt độc lập Quỹ tự nguyện. | `APPROVED` |

---

### MỤC LỤC ĐIỀU HƯỚNG (TABLE OF CONTENTS)
- [1. NGUYÊN TẮC CỐT LÕI & CHUẨN TẮC TỪ KHÓA](#1-nguyên-tắc-cốt-lõi--chuẩn-tắc-từ-khóa)
- [2. MA TRẬN CÔNG NGHỆ & MÔI TRƯỜNG THỰC THI (TECH STACK)](#2-ma-trận-công-nghệ--môi-trường-thực-thi-tech-stack)
- [3. CẤU TRÚC THƯ MỤC DỰ ÁN CHUẨN (PROJECT DIRECTORY LAYOUT)](#3-cấu-trúc-thư-mục-dự-án-chuẩn-project-directory-layout)
- [4. HỢP ĐỒNG CƠ SỞ DỮ LIỆU & KIỂU DỮ LIỆU CHUẨN (DATABASE CONTRACT)](#4-hợp-đồng-cơ-sở-dữ-liệu--kiểu-dữ-liệu-chuẩn-database-contract)
  - [4.1. Quy ước Kiểu Dữ liệu & Ràng buộc Khóa ngoại](#41-quy-ước-kiểu-dữ-liệu--ràng-buộc-khóa-ngoại)
  - [4.2. Năm Quy tắc Nghiệp vụ Cốt lõi & Kiểm soát Giao dịch ACID](#42-năm-quy-tắc-nghiệp-vụ-cốt-lõi--kiểm-soát-giao-dịch-acid)
  - [4.3. Giao thức Đóng băng Lược đồ & Kỷ luật Migration (Schema Freeze Protocol)](#43-giao-thức-đóng-băng-lược-đồ--kỷ-luật-migration-schema-freeze-protocol)
- [5. BỘ TỪ ĐIỂN ENUM DÙNG CHUNG HỆ THỐNG (SHARED ENUMS CATALOG)](#5-bộ-từ-điển-enum-dùng-chung-hệ-thống-shared-enums-catalog)
- [6. HỢP ĐỒNG GIAO DIỆN API & RESPONSE ENVELOPE (API CONTRACT)](#6-hợp-đồng-giao-diện-api--response-envelope-api-contract)
  - [6.1. Quy chuẩn Response Envelope](#61-quy-chuẩn-response-envelope)
  - [6.2. Bảng Danh mục Mã lỗi Hệ thống (Error Code Registry)](#62-bảng-danh-mục-mã-lỗi-hệ-thống-error-code-registry)
  - [6.3. Chuẩn hóa Tham số Truy vấn & Headers](#63-chuẩn-hóa-tham-số-truy-vấn--headers)
- [7. HỢP ĐỒNG GIAO TIẾP DTO GIỮA 5 MODULE (CROSS-MODULE CONTRACTS)](#7-hợp-đồng-giao-tiếp-dto-giữa-5-module-cross-module-contracts)
  - [7.1. Phân hệ Căn hộ & Cư dân (residents) cung cấp cho vehicles, billing và tiếp nhận từ portal](#71-phân-hệ-căn-hộ--cư-dân-residents-cung-cấp-cho-vehicles-billing-và-tiếp-nhận-từ-portal)
  - [7.2. Phân hệ Phương tiện (vehicles) cung cấp cho billing](#72-phân-hệ-phương-tiện-vehicles-cung-cấp-cho-billing)
  - [7.3. Phân hệ Kế toán & Đợt thu (billing) cung cấp cho cashier, portal và tiếp nhận khiếu nại](#73-phân-hệ-kế-toán--đợt-thu-billing-cung-cấp-cho-cashier-portal-và-tiếp-nhận-khiếu-nại)
  - [7.4. Phân hệ Thực thu & Quỹ (cashier) giao tiếp với billing (Transaction ACID) và Báo cáo](#74-phân-hệ-thực-thu--quỹ-cashier-giao-tiếp-với-billing-transaction-acid-và-báo-cáo)
  - [7.5. Phân hệ Cổng cư dân (portal) gửi yêu cầu và tra cứu thông tin](#75-phân-hệ-cổng-cư-dân-portal-gửi-yêu-cầu-và-tra-cứu-thông-tin)
- [8. KIẾN TRÚC BẢO MẬT & NGỮ CẢNH PHIÊN (SECURITY & AUTH CONTEXT)](#8-kiến-trúc-bảo-mật--ngữ-cảnh-phiên-security--auth-context)
  - [8.1. Sơ đồ Luồng Xác thực & Phân quyền RBAC](#81-sơ-đồ-luồng-xác-thực--phân-quyền-rbac)
  - [8.2. Cấu trúc JWT Payload & Thuật toán Ký chuẩn](#82-cấu-trúc-jwt-payload--thuật-toán-ký-chuẩn)
  - [8.3. Quy chuẩn Trích xuất Ngữ cảnh Người dùng](#83-quy-chuẩn-trích-xuất-ngữ-cảnh-người-dùng)
  - [8.4. Cơ chế Ghi vết & Xử lý Ngoại lệ Xuyên suốt (Cross-Cutting Concerns)](#84-cơ-chế-ghi-vết--xử-lý-ngoại-lệ-xuyên-suốt-cross-cutting-concerns)
- [9. MÔI TRƯỜNG CỤC BỘ & BỘ DỮ LIỆU HẠT GIỐNG (GOLDEN SEED DATA)](#9-môi-trường-cục-bộ--bộ-dữ-liệu-hạt-giống-golden-seed-data)
  - [9.1. Tệp Biến Môi trường Mẫu (.env.example)](#91-tệp-biến-môi-trường-mẫu-envexample)
  - [9.2. Kịch bản Dựng CSDL Cục bộ (docker-compose.yml)](#92-kịch-bản-dựng-csdl-cục-bộ-docker-composeyml)
  - [9.3. Danh mục Dữ liệu Hạt giống Vàng bao phủ Ca Biên (Golden Seed Records)](#93-danh-mục-dữ-liệu-hạt-giống-vàng-bao-phủ-ca-biên-golden-seed-records)
- [10. KỶ LUẬT GIT FLOW & TIÊU CHUẨN XONG (DEFINITION OF DONE)](#10-kỷ-luật-git-flow--tiêu-chuẩn-xong-definition-of-done)
- [11. KHUNG PHÂN ĐỊNH TRÁCH NHIỆM & MA TRẬN CAM KẾT KỸ THUẬT](#11-khung-phân-định-trách-nhiệm--ma-trận-cam-kết-kỹ-thuật)

---

## 1. NGUYÊN TẮC CỐT LÕI & CHUẨN TẮC TỪ KHÓA

### 1.1. Ba Nguyên tắc Bất biến
1. **Thiết kế theo Hợp đồng (Contract-First Design):** Toàn bộ Interface, DTO, mã lỗi, và Response Envelope BẮT BUỘC phải được định nghĩa trước khi viết logic nội bộ. Logic bên trong có thể tái cấu trúc, nhưng ranh giới giao tiếp ngoại vi BẮT BUỘC giữ tính tương thích ngược.
2. **Một nguồn Chân lý Duy nhất (Single Source of Truth):** Toàn bộ Type, Enum, mã lỗi nghiệp vụ dùng chung BẮT BUỘC nằm tập trung tại thư mục `src/common/`. KHÔNG ĐƯỢC PHÉP tái định nghĩa hoặc khai báo cục bộ tại các phân hệ riêng lẻ.
3. **Độc lập Tích hợp qua Dữ liệu Vàng (Decoupled Integration via Golden Seed):** Mỗi thành viên phát triển và kiểm thử độc lập dựa trên bộ dữ liệu hạt giống định danh cố định, loại bỏ hoàn toàn sự phụ thuộc thời gian vào tiến độ của thành viên khác.

### 1.2. Chuẩn tắc Từ khóa Ràng buộc (RFC 2119)
- **BẮT BUỘC (MUST / SHALL / REQUIRED):** Ràng buộc kỹ thuật tuyệt đối. Vi phạm tiêu chí này sẽ bị từ chối phê duyệt Pull Request (Reject PR).
- **KHÔNG ĐƯỢC PHÉP (MUST NOT / SHALL NOT):** Hành vi cấm kỵ tuyệt đối trong thiết kế và mã nguồn.
- **NÊN (SHOULD / RECOMMENDED):** Chuẩn mực kỹ thuật công nghiệp tối ưu; nếu làm khác phải có văn bản giải trình kiến trúc được Lead chấp thuận.
- **TÙY CHỌN (MAY / OPTIONAL):** Khả năng mở rộng không ảnh hưởng tới các phân hệ khác.

---

## 2. MA TRẬN CÔNG NGHỆ & MÔI TRƯỜNG THỰC THI (TECH STACK)

Toàn bộ 5 thành viên BẮT BUỘC đồng bộ môi trường thực thi theo bảng thông số kỹ thuật cố định sau:

| Thành phần | Công nghệ / Thư viện | Phiên bản cố định | Ràng buộc kỹ thuật |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Node.js (LTS) | `v20.12.x LTS` | Kiểm tra bằng lệnh: `node -v` |
| **Ngôn ngữ lập trình** | TypeScript | `v5.4.x` | `strict: true` trong `tsconfig.json` |
| **Backend Framework** | NestJS | `v10.3.x` | Cấu trúc Modular Monolith |
| **Hệ quản trị CSDL** | PostgreSQL (Docker) | `16.2-alpine` | Encoding: `UTF-8`, Timezone: `UTC` |
| **ORM / Data Access** | Prisma ORM | `v5.12.x` | Schema đồng bộ qua file migration |
| **Quản lý gói (Package)** | npm | `v10.5.x` | **BẮT BUỘC commit `package-lock.json`** |
| **Kiểm thử tự động** | Jest / Supertest | `v29.7.x` | Tối thiểu 70% Unit Test cho service lõi |
| **Code Formatter** | Prettier + ESLint | Prettier 3.x / ESLint 8.x | Tự động format qua Git Pre-commit Hook |

> [!CAUTION]
> **KHÔNG ĐƯỢC PHÉP** tự ý xóa file `package-lock.json` để chạy `npm install` lại từ đầu, hoặc cài đặt các package không nằm trong danh mục đã được phê duyệt.

---

## 3. CẤU TRÚC THƯ MỤC DỰ ÁN CHUẨN (PROJECT DIRECTORY LAYOUT)

Hệ thống triển khai theo mô hình **Modular Layered Architecture**. Mã nguồn BẮT BUỘC tuân thủ cấu trúc phân cấp thư mục sau:

```text
bluemoon-backend/
├── prisma/
│   ├── migrations/               # Lịch sử Schema Migrations được đánh số thứ tự
│   ├── schema.prisma             # Định nghĩa CSDL tập trung (Đã đóng băng)
│   └── seed.ts                   # Kịch bản nạp dữ liệu hạt giống chuẩn
├── src/
│   ├── common/                   # VÙNG DÙNG CHUNG TẬP TRUNG (SHARED KERNEL)
│   │   ├── constants/            # Hằng số toàn hệ thống
│   │   ├── decorators/           # Custom Decorators (@CurrentUser, @Roles)
│   │   ├── dto/                  # Base DTO, Pagination DTO, Error Response DTO
│   │   ├── enums/                # 100% Shared Enums của toàn hệ thống
│   │   ├── filters/              # Global Exception Filter xử lý mã lỗi HTTP
│   │   ├── guards/               # JwtAuthGuard, RolesGuard (RBAC)
│   │   ├── interceptors/         # TransformResponseInterceptor (Envelope)
│   │   └── services/             # AuditLoggerService (Ghi vết kiểm toán tập trung)
│   ├── config/                   # Cấu hình môi trường (.env validation)
│   ├── modules/                  # 5 PHÂN HỆ NGHIỆP VỤ ĐỘC LẬP
│   │   ├── auth/                 # Quản trị User, Auth & Audit Log (US-36..43)
│   │   ├── residents/            # Phân hệ Căn hộ, Cư dân, Hộ khẩu (US-01..08)
│   │   ├── vehicles/             # Phân hệ Phương tiện & Vé xe (US-09..14)
│   │   ├── billing/              # Phân hệ Biểu phí, Lập đợt, Tính công nợ (US-15..20)
│   │   ├── cashier/              # Phân hệ Thu phí, Quỹ tự nguyện, Biên lai (US-21..28)
│   │   └── portal/               # Phân hệ Cổng cư dân, Tra cứu, Báo cáo (US-29..35)
│   ├── app.module.ts             # Root Module gom 5 phân hệ
│   └── main.ts                   # Điểm khởi chạy hệ thống (Bootstrap)
├── .editorconfig                 # Chuẩn hóa format code đa nền tảng
├── .env.example                  # File biến môi trường mẫu
├── docker-compose.yml            # Khởi chạy PostgreSQL môi trường cục bộ
└── tsconfig.json                 # Cấu hình TypeScript nghiêm ngặt (Strict mode)
```

### Sơ đồ 1: Kiến trúc Phân tầng & Ranh giới Thư mục (Modular Architecture)
```mermaid
flowchart TD
    Client["Client: Trình duyệt Web / Mobile App"] -->|"HTTPS / REST API"| ControllerLayer["Tầng Controller (HTTP Handlers)"]

    subgraph CoreBoundary["src/common/ (Vùng dùng chung bất biến)"]
        Guard["JwtAuthGuard & RolesGuard"]
        Interceptor["TransformResponseInterceptor (Envelope)"]
        Filter["GlobalExceptionFilter"]
        Audit["AuditLoggerService"]
        Enums["Shared Enums & Constants"]
    end

    ControllerLayer --> Guard
    Guard --> Interceptor

    subgraph ModularContexts["src/modules/ (5 Phân hệ nghiệp vụ)"]
        M1["Phân hệ 1: residents (Căn hộ & Cư dân)"]
        M2["Phân hệ 2: vehicles (Phương tiện & Vé xe)"]
        M3["Phân hệ 3: auth & billing (Core, Biểu phí & Đợt thu)"]
        M4["Phân hệ 4: cashier (Thực thu, Quỹ & Biên lai)"]
        M5["Phân hệ 5: portal (Cổng cư dân & Tra cứu)"]
    end

    Interceptor --> ModularContexts
    ModularContexts --> Filter
    ModularContexts --> Audit
    ModularContexts -->|"Prisma Client"| DBLayer[("PostgreSQL 16.2 Database")]
```

> [!IMPORTANT]
> **Quy tắc Đóng gói Module (Module Encapsulation):** Module A KHÔNG ĐƯỢC PHÉP import trực tiếp Repository hoặc Service nội bộ của Module B. Mọi trao đổi dữ liệu BẮT BUỘC phải thông qua file `index.ts` công khai (Public API) của từng module bằng các DTO chuẩn.

---

## 4. HỢP ĐỒNG CƠ SỞ DỮ LIỆU & KIỂU DỮ LIỆU CHUẨN (DATABASE CONTRACT)

### 4.1. Quy ước Kiểu Dữ liệu & Ràng buộc Khóa ngoại

| Hạng mục | Quy định chuẩn | Điều cấm kỵ (Negative Constraints) |
| :--- | :--- | :--- |
| **Khóa chính nội bộ (Internal PK)** | `BIGSERIAL` / `BIGINT AUTO_INCREMENT` | KHÔNG dùng chuỗi ngẫu nhiên làm PK cho các bảng nghiệp vụ có tần suất JOIN cao. |
| **Định danh công khai (Public ID)** | `UUID v4` cho bảng `users`; Mã định dạng cho chứng từ: `receipt_number`, `bill_code`. | KHÔNG để lộ số thứ tự tự tăng (Auto-increment ID) ra URL công khai. |
| **Dữ liệu Tiền tệ (Currency)** | Database: `DECIMAL(15, 2)` hoặc `BIGINT` (lưu tròn số tiền VNĐ).<br>Code: Kiểu số nguyên VNĐ (`number` an toàn hoặc `BigInt`). | **TUYỆT ĐỐI CẤM SỬ DỤNG `FLOAT` HOẶC `DOUBLE`** cho bất kỳ trường dữ liệu tài chính nào. |
| **Dữ liệu Sự kiện (Timestamp)** | `TIMESTAMPTZ` (UTC ISO-8601: `YYYY-MM-DDTHH:mm:ss.sssZ`) cho `created_at`, `paid_at`, `deleted_at`. | KHÔNG lưu giờ máy tính cục bộ (Local time) vào cơ sở dữ liệu. |
| **Dữ liệu Ngày thuần túy (Date-only)** | Kiểu **`DATE`** chuẩn (`YYYY-MM-DD`, không kèm giờ) cho: Ngày sinh (`dob`), Ngày dọn vào/ra (`move_in_date`), Ngày hiệu lực biểu phí (`effective_from`). | **CẤM LƯU TIMESTAMPTZ CHO NGÀY SINH** để tránh lỗi lệch lùi 1 ngày do chuyển đổi múi giờ GMT+7 sang UTC. |
| **Xóa mềm (Soft Delete)** | BẮT BUỘC có 2 trường: `status` (Enum) và `deleted_at: TIMESTAMPTZ NULL`. | **TUYỆT ĐỐI CẤM LỆNH `DELETE FROM`** trên các bảng thực thể nghiệp vụ. |
| **Ràng buộc Khóa ngoại (FK Constraint)**| BẮT BUỘC cấu hình **`onDelete: Restrict`** trên tất cả các khóa ngoại quan hệ nghiệp vụ. | **TUYỆT ĐỐI CẤM `onDelete: Cascade`** hoặc `SetNull` trên các bảng tài chính, căn hộ, hộ dân. |
| **Quy chuẩn đặt tên (Naming)** | Database: `snake_case` (ví dụ: `apartment_id`, `created_at`).<br>Code / API: `camelCase` (ví dụ: `apartmentId`, `createdAt`). | KHÔNG dùng lẫn lộn giữa camelCase và snake_case trong cùng một tầng. |

### 4.2. Năm Quy tắc Nghiệp vụ Cốt lõi & Kiểm soát Giao dịch ACID
1. **Tách biệt Căn hộ vật lý (`apartments`) và Hộ gia đình (`households`) (`T-01, T-02`):**
   * Bảng `apartments`: Đại diện cho diện tích sàn xây dựng cố định (`room_number`, `area_m2`, `floor`).
   * Bảng `households`: Đại diện cho quan hệ cư trú biến động theo thời gian (`household_code`, `status`, `credit_balance`).
   * *Ràng buộc:* Khi hộ gia đình chuyển nhượng (`US-02`), cập nhật `households.status = 'MOVED_OUT'`. Khởi tạo bản ghi `households` mới trỏ vào `apartment_id`. **KHÔNG ĐƯỢC PHÉP ghi đè thông tin chủ hộ mới lên bản ghi hộ cũ**.
2. **Công thức Tính phí Kỳ thu Chuẩn tắc (`US-17`, `AC-17.1`, `AC-19.5`):**
   $$\text{Tổng phải nộp kỳ này} = \sum (\text{Đơn giá} \times \text{Số lượng} - \text{Miễn giảm}) + \text{Nợ cũ lũy kế} - \text{Số dư có (Credit Balance)}$$
3. **Bảo tồn Lịch sử Nghiệp vụ:** Mọi thay đổi trạng thái cư dân chuyển đi (`US-07`), biểu phí hết hạn (`AC-13.2`), hoặc biên lai bị hủy (`US-22`) BẮT BUỘC chỉ cập nhật cột `status` và ghi vết vào `audit_logs`.
4. **Kiểm soát Giao dịch Đồng thời & Mức cô lập (Concurrency & ACID Isolation Level - `NFR-008`):**
   Tác vụ thu phí (`US-19`) BẮT BUỘC phải thực thi trong một Transaction với mức cô lập **`Serializable`** (hoặc Khóa bi quan `Pessimistic Locking: SELECT ... FOR UPDATE` trên bản ghi hộ và hóa đơn) để chống triệt để lỗi Lost Update khi xảy ra thanh toán đồng thời (quầy và Webhook quét mã VietQR).
5. **Khoản thu Tự nguyện (`voluntary_donations`) ĐỘC LẬP HOÀN TOÀN với Hóa đơn Tiền phí (`household_bills`):**
   Tiền đóng góp tự nguyện KHÔNG ghi nhận vào công nợ căn hộ, KHÔNG làm thay đổi `credit_balance` của hộ gia đình, KHÔNG được cấn trừ tự động từ số dư có, và KHÔNG được gộp chung vào biên lai thu phí sinh hoạt định kỳ.

#### Sơ đồ 2: Luồng Giao dịch Toàn vẹn khi Thu phí (ACID Transaction Flow)
```mermaid
sequenceDiagram
    autonumber
    actor Cashier as Thủ quỹ / WebHook VietQR
    participant Service as PaymentTransactionService
    participant DB as PostgreSQL (ACID Engine)

    Cashier->>Service: executePaymentTransaction(cmd)
    activate Service
    Service->>DB: BEGIN TRANSACTION (isolationLevel: Serializable)
    Service->>DB: SELECT * FROM households WHERE id = ? FOR UPDATE
    Service->>DB: SELECT * FROM household_bills WHERE household_id = ? AND status != 'PAID' FOR UPDATE
    Service->>DB: (1) INSERT INTO receipts (receipt_number, amount_received, cashier_id)
    loop Gạch nợ theo thứ tự ưu tiên (AC-19.2)
        Service->>DB: (2) Phân bổ tiền nộp gạch nợ: Phí dịch vụ -> Quản lý -> Gửi xe
        Service->>DB: UPDATE household_bills SET paid_amount = paid_amount + alloc, status = ?
    end
    alt Số tiền nộp > Tổng công nợ còn lại
        Service->>DB: (3) UPDATE households SET credit_balance = credit_balance + excess
    else Có sử dụng credit_balance có sẵn để cấn trừ
        Service->>DB: (3) UPDATE households SET credit_balance = credit_balance - used
    end
    alt Không phát sinh lỗi
        Service->>DB: COMMIT TRANSACTION
        Service-->>Cashier: PaymentExecutionResultDTO (Thành công)
    else Phát sinh lỗi (Validation, Concurrency Conflict, DB Timeout)
        Service->>DB: ROLLBACK TRANSACTION
        Service-->>Cashier: Ném lỗi HTTP 409 / 422 (Rollback sạch 100%)
    end
    deactivate Service
```

### 4.3. Giao thức Đóng băng Lược đồ & Kỷ luật Migration (Schema Freeze Protocol)
Để triệt tiêu nguy cơ Merge Conflict trên file tập trung `prisma/schema.prisma` khi 5 người cùng mở nhánh:
1. **Đóng băng Lược đồ (Schema Freeze):** TV3 (System Architect) BẮT BUỘC thiết kế 100% Khung thực thể (Entity Models & Relations) của toàn bộ 10 Epics vào file `prisma/schema.prisma` và khởi tạo bản migration gốc `V001__init_baseline.sql` ngay trên nhánh `develop` trước khi các thành viên tách nhánh.
2. **Kỷ luật Nhánh tính năng:** Các thành viên phát triển tính năng **KHÔNG ĐƯỢC PHÉP tự ý chỉnh sửa `prisma/schema.prisma` trên nhánh cá nhân**.
3. **Cấm câu lệnh `prisma db push`:** **TUYỆT ĐỐI CẤM SỬ DỤNG LỆNH `prisma db push`** trên toàn bộ các nhánh. Bắt buộc 100% sử dụng lệnh chuẩn:
   * Tạo migration mới (chỉ dành cho Lead TV3 trên `develop`): `npx prisma migrate dev --name <ten_thay_doi>`
   * Áp dụng migration sẵn có (cho các thành viên trên local): `npx prisma migrate deploy`
4. **Quy trình Thay đổi Schema (RFC Schema Change):** Nếu phát sinh nhu cầu thêm cột hoặc quan hệ mới, thành viên BẮT BUỘC phải gửi yêu cầu (RFC Issue) cho TV3. TV3 sẽ phê duyệt, cập nhật tập trung trên `develop`, tạo migration `V00X...` và thông báo cho cả nhóm kéo (pull) về.

---

## 5. BỘ TỪ ĐIỂN ENUM DÙNG CHUNG HỆ THỐNG (SHARED ENUMS CATALOG)

Toàn bộ Enum BẮT BUỘC đặt tập trung tại `src/common/enums/index.ts`. Khai báo đầy đủ 100% mã nguồn chuẩn:

```typescript
// 1. Phân quyền người dùng hệ thống (RBAC)
export enum UserRole {
  ADMIN = 'ADMIN',           // Quản trị viên hệ thống (US-36..43)
  ACCOUNTANT = 'ACCOUNTANT', // Kế toán: Lập đợt thu, biểu phí, chốt số liệu (US-15..20)
  CASHIER = 'CASHIER',       // Thủ quỹ: Thu tiền, xuất biên lai, chốt ca (US-21..28)
  RESIDENT = 'RESIDENT',     // Cư dân: Tra cứu công nợ, gửi kiến nghị (US-29..35)
}

// 2. Trạng thái Hộ gia đình & Cư dân (US-01..08)
export enum HouseholdStatus {
  ACTIVE = 'ACTIVE',                 // Đang sinh sống thực tế tại chung cư
  TEMPORARY_ABSENT = 'TEMPORARY_ABSENT', // Hộ đang tạm vắng
  MOVED_OUT = 'MOVED_OUT',           // Đã chuyển hẳn khỏi chung cư
}

export enum ResidentRelation {
  OWNER = 'OWNER',         // Chủ hộ đứng tên
  SPOUSE = 'SPOUSE',       // Vợ / Chồng
  CHILD = 'CHILD',         // Con đẻ / Con nuôi hợp pháp
  PARENT = 'PARENT',       // Bố / Mẹ
  OTHER = 'OTHER',         // Quan hệ nhân khẩu khác
}

export enum ResidenceType {
  PERMANENT = 'PERMANENT', // Thường trú
  TEMPORARY = 'TEMPORARY', // Tạm trú
}

export enum ResidentStatus {
  ACTIVE = 'ACTIVE',       // Cư dân đang sinh sống
  TEMPORARY_ABSENT = 'TEMPORARY_ABSENT', // Tạm vắng
  MOVED_OUT = 'MOVED_OUT', // Đã chuyển khẩu đi
  DECEASED = 'DECEASED',   // Đã qua đời (Bảo tồn dữ liệu - US-07)
}

// 3. Phân loại & Trạng thái Phương tiện (US-09..14)
export enum VehicleType {
  CAR = 'CAR',                       // Ô tô
  MOTORBIKE = 'MOTORBIKE',           // Xe máy xăng / xe máy điện
  BICYCLE = 'BICYCLE',               // Xe đạp truyền thống
  ELECTRIC_SCOOTER = 'ELECTRIC_SCOOTER', // Xe đạp điện
}

export enum VehicleStatus {
  ACTIVE = 'ACTIVE',                 // Đang sử dụng vé tháng gửi xe
  UNREGISTERED = 'UNREGISTERED',     // Đã chấm dứt hợp đồng gửi xe
}

// 4. Quản lý Đợt thu & Hóa đơn căn hộ (US-15..20)
export enum FeePeriodStatus {
  DRAFT = 'DRAFT',         // Bản nháp kế toán đang rà soát
  PUBLISHED = 'PUBLISHED', // Đã phát hành chính thức, mở cổng thanh toán
  CLOSED = 'CLOSED',       // Đã khóa sổ kỳ thu, chuyển nợ tồn sang kỳ sau
}

export enum FeeCalculationMethod {
  PER_M2 = 'PER_M2',                   // Nhân theo diện tích căn hộ (Phí dịch vụ, quản lý)
  FIXED_PER_HOUSEHOLD = 'FIXED_PER_HOUSEHOLD', // Thu cố định trên một hộ gia đình
  PER_VEHICLE = 'PER_VEHICLE',         // Nhân theo số lượng phương tiện của hộ
  VOLUNTARY = 'VOLUNTARY',             // Tự nguyện đóng góp (Quỹ từ thiện, khuyến học)
}

export enum BillStatus {
  UNPAID = 'UNPAID',                 // Chưa thanh toán
  PARTIALLY_PAID = 'PARTIALLY_PAID', // Đã nộp một phần tiền
  PAID = 'PAID',                     // Đã nộp đủ 100% nghĩa vụ
  OVERDUE = 'OVERDUE',               // Nợ quá thời hạn quy định
}

// 5. Thanh toán, Biên lai & Quỹ tự nguyện (US-21..28)
export enum PaymentMethod {
  CASH = 'CASH',                     // Nộp tiền mặt trực tiếp tại quầy
  BANK_TRANSFER = 'BANK_TRANSFER',   // Chuyển khoản ngân hàng / VietQR
}

export enum ReceiptStatus {
  VALID = 'VALID',         // Biên lai có hiệu lực pháp lý
  CANCELLED = 'CANCELLED', // Biên lai đã bị hủy do thu sai / lập nhầm
}

export enum CampaignStatus {
  DRAFT = 'DRAFT',         // Đợt vận động đang lên kế hoạch
  ACTIVE = 'ACTIVE',       // Đang tiếp nhận đóng góp tự nguyện
  CLOSED = 'CLOSED',       // Đã kết thúc đợt vận động và công khai quyết toán
}

// 6. Cổng dịch vụ Cư dân (US-29..35)
export enum EditRequestStatus {
  PENDING = 'PENDING',     // Chờ Ban quản trị xem xét
  APPROVED = 'APPROVED',   // Đã phê duyệt và đồng bộ dữ liệu nhân khẩu
  REJECTED = 'REJECTED',   // Bị từ chối (có lý do kèm theo)
}

export enum ComplaintStatus {
  SUBMITTED = 'SUBMITTED', // Cư dân đã gửi khiếu nại hóa đơn
  IN_REVIEW = 'IN_REVIEW', // Kế toán đang đối soát số liệu
  RESOLVED = 'RESOLVED',   // Đã giải quyết / Điều chỉnh hóa đơn
  REJECTED = 'REJECTED',   // Bác bỏ khiếu nại
}
```

---

## 6. HỢP ĐỒNG GIAO DIỆN API & RESPONSE ENVELOPE (API CONTRACT)

### 6.1. Quy chuẩn Response Envelope
Mọi Controller BẮT BUỘC phải trả về dữ liệu tuân theo cấu trúc bao gói chuẩn thông qua `TransformResponseInterceptor`:

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
*(Trường `meta` là BẮT BUỘC đối với các API trả về danh sách phân trang; các API thao tác đơn lẻ hoặc chi tiết bản ghi được phép bỏ qua `meta`).*

#### Phản hồi Thất bại (HTTP 4xx / 5xx):
```json
{
  "success": false,
  "error": {
    "code": "HOUSEHOLD_STILL_HAS_UNPAID_DEBT",
    "message": "Không thể đóng hồ sơ hộ gia đình do vẫn còn nợ phí chưa hoàn thành nghĩa vụ tài chính",
    "details": [
      {
        "field": "householdId",
        "issue": "Còn tồn đọng 1.450.000 VNĐ tại kỳ thu 2026-10"
      }
    ]
  }
}
```

### 6.2. Bảng Danh mục Mã lỗi Hệ thống (Error Code Registry)

| Mã lỗi Nghiệp vụ (`error.code`) | HTTP Status | Định nghĩa & Ngữ cảnh phát sinh theo AC |
| :--- | :---: | :--- |
| `VALIDATION_FAILED` | `400` | Dữ liệu đầu vào sai định dạng hoặc vi phạm ràng buộc DTO. |
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
  * Mặc định: `page=1`, `pageSize=10` (BẮT BUỘC khống chế: `1 <= pageSize <= 100` để chống DoS).
  * URL chuẩn: `/api/v1/{resources}?page=1&pageSize=10&sortBy=createdAt&sortOrder=DESC`
  * Lọc điều kiện: `/api/v1/households?status=ACTIVE&floor=5`

---

## 7. HỢP ĐỒNG GIAO TIẾP DTO GIỮA 5 MODULE (CROSS-MODULE CONTRACTS)

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
    participant DB as PostgreSQL 16.2 (ACID)

    Note over ResidentMod,VehicleMod: 1. Lập đợt thu & Tính công nợ
    BillingMod->>ResidentMod: getApartmentDetail(apartmentId)
    ResidentMod-->>BillingMod: ApartmentDetailDTO (Diện tích m2)
    BillingMod->>VehicleMod: getVehicleSummaryByHousehold(householdId)
    VehicleMod-->>BillingMod: VehicleCountDTO (Số xe ô tô, xe máy)
    BillingMod->>DB: Khởi tạo HouseholdBills & BillDetails

    Note over CashierMod,BillingMod: 2. Thực thu & Gạch nợ (Serializable Transaction)
    Cashier->>CashierMod: Nhập số tiền thu tại quầy
    CashierMod->>BillingMod: executePaymentTransaction(cmd)
    BillingMod->>DB: Thực thi ACID Transaction (Chi tiết tại Sơ đồ 2)
    BillingMod-->>CashierMod: PaymentExecutionResultDTO

    Note over Resident,ResidentMod: 3. Cư dân gửi Yêu cầu chỉnh sửa & Khiếu nại
    Resident->>PortalMod: Gửi yêu cầu cập nhật nhân khẩu
    PortalMod->>ResidentMod: submitEditRequest(cmd)
    ResidentMod-->>PortalMod: EditRequestSummaryDTO (PENDING)
    Resident->>PortalMod: Gửi khiếu nại sai lệch hóa đơn
    PortalMod->>BillingMod: submitFeeComplaint(cmd)
    BillingMod-->>PortalMod: ComplaintSummaryDTO (SUBMITTED)
```

### 7.1. Phân hệ Căn hộ & Cư dân (residents) cung cấp cho vehicles, billing và tiếp nhận từ portal
Định nghĩa tại: `src/modules/residents/dto/cross-module.dto.ts`

```typescript
export interface ApartmentDetailDTO {
  apartmentId: number;
  roomNumber: string; // Ví dụ: "P.101"
  floor: number;
  areaM2: number;     // Ví dụ: 75.50 m2
  status: string;
}

export interface HouseholdSummaryDTO {
  householdId: number;
  apartmentId: number;
  householdCode: string;
  ownerName: string;
  residentCount: number;
  creditBalance: number; // Số dư có hiện tại (VNĐ)
  status: HouseholdStatus;
}

export interface SubmitEditRequestCommandDTO {
  householdId: number;
  residentId: number;
  requestType: 'ADD_MEMBER' | 'REMOVE_MEMBER' | 'UPDATE_INFO';
  proposedData: Record<string, any>; // Dữ liệu đề xuất (JSON)
  documentProofUrl?: string;         // Ảnh CCCD / Giấy tạm vắng đính kèm
}

export interface EditRequestSummaryDTO {
  requestId: number;
  householdId: number;
  status: EditRequestStatus;
  submittedAt: string;
}

// Chữ ký hàm Service công khai (Exported Service):
export interface IResidentsPublicService {
  getApartmentById(apartmentId: number): Promise<ApartmentDetailDTO>;
  getActiveHouseholdByApartment(apartmentId: number): Promise<HouseholdSummaryDTO>;
  submitEditRequest(cmd: SubmitEditRequestCommandDTO): Promise<EditRequestSummaryDTO>;
}
```

### 7.2. Phân hệ Phương tiện (vehicles) cung cấp cho billing
Định nghĩa tại: `src/modules/vehicles/dto/cross-module.dto.ts`

```typescript
export interface VehicleCountDTO {
  householdId: number;
  carCount: number;              // Số lượng ô tô
  motorbikeCount: number;        // Số lượng xe máy
  bicycleCount: number;          // Số lượng xe đạp
  electricScooterCount: number;  // Số lượng xe máy điện
}

// Chữ ký hàm Service công khai:
export interface IVehiclesPublicService {
  getVehicleCountByHousehold(householdId: number): Promise<VehicleCountDTO>;
}
```

### 7.3. Phân hệ Kế toán & Đợt thu (billing) cung cấp cho cashier, portal và tiếp nhận khiếu nại
Định nghĩa tại: `src/modules/billing/dto/cross-module.dto.ts`

```typescript
export interface BillLineItemDTO {
  feeCode: string;
  feeName: string;
  unitPrice: number;
  quantity: number;
  discountAmount: number;
  totalAmount: number;
  paidAmount: number;
}

export interface BillCalculationResultDTO {
  billId: number;
  householdId: number;
  periodCode: string;           // Ví dụ: "2026-10"
  currentPeriodTotal: number;   // Phí phát sinh kỳ này (VNĐ)
  previousDebt: number;         // Nợ cũ lũy kế dồn về (VNĐ)
  creditBalanceApplied: number; // Số dư có đã trừ (VNĐ)
  totalPayable: number;         // Tổng thực nộp cuối cùng (VNĐ)
  status: BillStatus;
  items: BillLineItemDTO[];
}

export interface SubmitFeeComplaintCommandDTO {
  householdId: number;
  billId: number;
  feeCode: string;
  reason: string;
  claimedAmount?: number;
}

export interface ComplaintSummaryDTO {
  complaintId: number;
  billId: number;
  status: ComplaintStatus;
  createdAt: string;
}

// Chữ ký hàm Service công khai:
export interface IBillingPublicService {
  getBillCalculationDetails(householdId: number, periodId: number): Promise<BillCalculationResultDTO>;
  submitFeeComplaint(cmd: SubmitFeeComplaintCommandDTO): Promise<ComplaintSummaryDTO>;
}
```

### 7.4. Phân hệ Thực thu & Quỹ (cashier) giao tiếp với billing (Transaction ACID) và Báo cáo
Định nghĩa tại: `src/modules/cashier/dto/cross-module.dto.ts`

```typescript
export interface RecordPaymentCommandDTO {
  householdId: number;
  billingPeriodId: number;
  cashierId: string;            // UUID của thủ quỹ thực hiện
  amountReceived: number;       // Số tiền khách nộp thực tế (VNĐ)
  paymentMethod: PaymentMethod; // Tiền mặt / Chuyển khoản
  payerName: string;            // Tên người nộp
  notes?: string;               // Ghi chú giao dịch
}

export interface PaymentExecutionResultDTO {
  receiptId: number;
  receiptNumber: string;        // Ví dụ: "BL-202610-0012"
  amountReceived: number;
  allocatedToDebt: number;      // Số tiền dùng gạch nợ các khoản
  excessToCreditBalance: number;// Tiền thừa cộng vào số dư có
  remainingHouseholdDebt: number; // Nợ còn tồn lại sau thanh toán
  paidAt: string;               // ISO-8601 UTC
}

export interface RecordDonationCommandDTO {
  campaignId: number;
  householdId?: number;         // Có thể đóng góp ẩn danh hoặc không theo hộ
  donorName: string;
  amount: number;
  paymentMethod: PaymentMethod;
  notes?: string;
  cashierId: string;
}

export interface DonationReceiptDTO {
  donationId: number;
  receiptNumber: string;
  campaignName: string;
  donorName: string;
  amount: number;
  paidAt: string;
}

// Chữ ký hàm Service công khai:
export interface IPaymentTransactionService {
  executePaymentTransaction(cmd: RecordPaymentCommandDTO): Promise<PaymentExecutionResultDTO>;
  recordDonation(cmd: RecordDonationCommandDTO): Promise<DonationReceiptDTO>;
}
```

### 7.5. Phân hệ Cổng cư dân (portal) gửi yêu cầu và tra cứu thông tin
Định nghĩa tại: `src/modules/portal/dto/cross-module.dto.ts`

```typescript
export interface ResidentDashboardOverviewDTO {
  household: HouseholdSummaryDTO;
  currentBill: BillCalculationResultDTO | null;
  paymentHistory: PaymentExecutionResultDTO[];
  pendingRequests: EditRequestSummaryDTO[];
  activeCampaigns: { campaignId: number; campaignName: string; targetAmount: number }[];
}

export interface IPortalPublicService {
  getResidentDashboard(householdId: number): Promise<ResidentDashboardOverviewDTO>;
}
```

---

## 8. KIẾN TRÚC BẢO MẬT & NGỮ CẢNH PHIÊN (SECURITY & AUTH CONTEXT)

### 8.1. Sơ đồ 4: Luồng Xác thực & Phân quyền RBAC (Security Sequence)
```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng (Browser)
    participant Gateway as NestJS Main Gateway
    participant JwtGuard as JwtAuthGuard
    participant RolesGuard as RolesGuard (@Roles)
    participant Controller as Feature Controller
    participant Service as Business Service

    User->>Gateway: Gửi Request + Header `Authorization: Bearer <Token>`
    Gateway->>JwtGuard: CanActivate(context)?
    alt Token thiếu hoặc không hợp lệ
        JwtGuard-->>User: Trả về HTTP 401 Unauthorized (UNAUTHORIZED)
    else Token hợp lệ
        JwtGuard->>JwtGuard: Giải mã JWT (Thuật toán HS256)
        JwtGuard->>Gateway: Gắn req.user = AuthenticatedUser
        Gateway->>RolesGuard: CanActivate(context)?
        alt User không sở hữu Role được yêu cầu
            RolesGuard-->>User: Trả về HTTP 403 Forbidden (FORBIDDEN_RESOURCE)
        else Role hợp lệ
            RolesGuard->>Controller: Chuyển giao tiếp nhận (@CurrentUser() user)
            Controller->>Service: Thực thi nghiệp vụ với định danh user
            Service-->>User: Trả về kết quả HTTP 200/201 (Envelope)
        end
    end
```

### 8.2. Cấu trúc JWT Payload & Thuật toán Ký chuẩn
- **Thuật toán ký BẮT BUỘC:** **`HS256`** (HMAC sử dụng SHA-256), ký bằng khóa bí mật `JWT_SECRET` từ `.env`.
- Token trả về sau khi đăng nhập thành công BẮT BUỘC chỉ chứa các Claims định danh tối thiểu sau:

```typescript
export interface JwtPayload {
  sub: string;             // UUID của user trong bảng `users`
  username: string;        // Tên đăng nhập (ví dụ: "admin", "ketoan")
  role: UserRole;          // ADMIN | ACCOUNTANT | CASHIER | RESIDENT
  householdId: number | null; // NULL đối với cán bộ BQT; Có giá trị nếu là Cư dân
  iat?: number;            // Thời điểm phát hành token (Unix timestamp)
  exp?: number;            // Thời điểm hết hạn (Mặc định: 1 ngày)
}

export interface AuthenticatedUser {
  userId: string;
  username: string;
  role: UserRole;
  householdId: number | null;
}
```

### 8.3. Quy chuẩn Trích xuất Ngữ cảnh Người dùng
- Mọi Controller BẮT BUỘC sử dụng Parameter Decorator `@CurrentUser()` để lấy thông tin phiên làm việc.
- **KHÔNG ĐƯỢC PHÉP** query lại cơ sở dữ liệu để lấy lại `role` hay `username` của người thực hiện tác vụ.

```typescript
@Controller('api/v1/bills')
@UseGuards(JwtAuthGuard, RolesGuard)
export class BillingController {
  @Post(':id/pay')
  @Roles(UserRole.CASHIER, UserRole.ADMIN)
  async payBill(
    @Param('id', ParseIntPipe) billId: number,
    @Body() dto: PaymentRequestDto,
    @CurrentUser() user: AuthenticatedUser,
  ) {
    return this.billingService.processPayment(billId, dto, user.userId);
  }
}
```

### 8.4. Cơ chế Ghi vết & Xử lý Ngoại lệ Xuyên suốt (Cross-Cutting Concerns)
- **Ghi vết Kiểm toán (Audit Logging Service):** BẮT BUỘC tiêm (inject) `AuditLoggerService` tại `src/common/services/audit-logger.service.ts` để ghi vết các hành vi thay đổi dữ liệu nhạy cảm (`US-02` đổi chủ hộ, `US-16` đổi giá phí, `US-22` hủy biên lai):
  ```typescript
  export interface IAuditLogger {
    logAction(
      userId: string,
      action: 'CREATE' | 'UPDATE' | 'DELETE' | 'CANCEL',
      entityName: string,
      entityId: string,
      oldValue?: Record<string, any>,
      newValue?: Record<string, any>,
    ): Promise<void>;
  }
  ```
- **Bộ lọc Ngoại lệ Toàn cục (Global Exception Filter):** Tự động bắt mọi lỗi `HttpException` và định dạng chuẩn thành Error Response Envelope đã định nghĩa tại Mục 6.1.

---

## 9. MÔI TRƯỜNG CỤC BỘ & BỘ DỮ LIỆU HẠT GIỐNG (GOLDEN SEED DATA)

### 9.1. Tệp Biến Môi trường Mẫu (`.env.example`)
Toàn bộ thành viên BẮT BUỘC tạo file `.env` cục bộ với các khóa chuẩn:

```env
# Ứng dụng Backend
PORT=3000
NODE_ENV=development
API_PREFIX=/api/v1

# Cơ sở dữ liệu PostgreSQL (Khởi chạy qua Docker)
DATABASE_URL="postgresql://bluemoon_admin:BlueMoonPass2026@localhost:5432/bluemoon_db?schema=public"

# Bảo mật JWT (Thuật toán HS256)
JWT_SECRET="bluemoon_super_secret_jwt_key_2026_hust_soict"
JWT_EXPIRES_IN="24h"

# CORS Origin Whitelist (Ngăn cách Frontend)
CORS_ORIGIN="http://localhost:5173,http://localhost:3000"
```

### 9.2. Kịch bản Dựng CSDL Cục bộ (`docker-compose.yml`)
Khởi động hệ quản trị CSDL chuẩn hóa bằng lệnh: `docker compose up -d`

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16.2-alpine
    container_name: bluemoon_postgres
    restart: always
    environment:
      POSTGRES_USER: bluemoon_admin
      POSTGRES_PASSWORD: BlueMoonPass2026
      POSTGRES_DB: bluemoon_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bluemoon_admin -d bluemoon_db"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### 9.3. Danh mục Dữ liệu Hạt giống Vàng bao phủ Ca Biên (Golden Seed Records)
Sau khi chạy migration, BẮT BUỘC thực thi lệnh `npm run db:seed` để tạo bộ dữ liệu cố định bao phủ toàn bộ các ca kiểm thử:

#### 1. Bốn Tài khoản Đăng nhập Mặc định (Mật khẩu chung: `BlueMoon@2026`):
| Username | Role | Household gắn kết | Mục đích kiểm thử tính năng |
| :--- | :--- | :---: | :--- |
| `admin` | `ADMIN` | `NULL` | Phân quyền, quản lý tài khoản, xem Audit Log (`US-36..43`). |
| `ketoan` | `ACCOUNTANT` | `NULL` | Lập đợt thu, cấu hình biểu phí, xuất báo cáo (`US-15..20`). |
| `thuquy` | `CASHIER` | `NULL` | Thu tiền mặt/chuyển khoản, gạch nợ, in biên lai (`US-21..28`). |
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
  * `test(cashier): them unit test cho quy trinh gach no acid`

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
  * Mọi PR có chỉnh sửa vào `prisma/migrations/`, `src/common/`, hoặc tầng Auth BẮT BUỘC phải có thêm chữ ký của **TV3 (Lead Architect)**.
  * **KHÔNG ĐƯỢC PHÉP tự merge PR của chính mình**.

### 10.3. Bảng Tiêu chuẩn Xong (Definition of Done - DoD Checklist)
Một Pull Request chỉ được phép merge vào nhánh `develop` khi thỏa mãn trọn vẹn 5 tiêu chí:
- [ ] **Linter & Format sạch:** Chạy `npm run lint` không phát sinh lỗi (0 Error, 0 Warning).
- [ ] **Bảo toàn Core Types:** Không tự ý sửa đổi file trong `src/common/` hoặc `schema.prisma` nếu chưa có thông báo kiến trúc.
- [ ] **Bằng chứng Kiểm thử (Test Evidence):** Đính kèm ảnh chụp màn hình Postman request hoặc Unit Test chạy xanh (`npm run test`).
- [ ] **Không làm hỏng Seed Data:** Chạy lại `npm run db:seed` thành công không phát sinh lỗi khóa ngoại.
- [ ] **Đúng chuẩn Envelope:** Mọi API mới viết đều trả về đúng format Envelope và chuẩn mã lỗi HTTP.

---

## 11. KHUNG PHÂN ĐỊNH TRÁCH NHIỆM & MA TRẬN CAM KẾT KỸ THUẬT

Tài liệu này xác lập khung trách nhiệm kỹ thuật và ranh giới theo từng Module chức năng. Danh sách phân công nhân sự cụ thể cho từng thành viên sẽ được thảo luận, thống nhất và biểu quyết chính thức tại phiên họp Sprint Planning trước khi mở nhánh lập trình.

Mọi thành viên khi được giao quyền sở hữu phân hệ (Module Owner) BẮT BUỘC phải ký cam kết tuân thủ toàn bộ các quy chuẩn kiến trúc đã được đặc tả trong tài liệu này:

| STT | Phân hệ / Khối chức năng | Phạm vi User Stories | Vai trò Kỹ thuật | Nhân sự phụ trách | Trạng thái Cam kết |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **1** | Phân hệ Căn hộ & Cư dân (`src/modules/residents`) | Quản lý Căn hộ, Cư dân, Hộ khẩu (`US-01..08`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
| **2** | Phân hệ Phương tiện & Vé xe (`src/modules/vehicles`) | Quản lý Phương tiện, Vé xe tháng/lượt (`US-09..14`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
| **3** | Kiến trúc lõi, Quản trị Auth & Đợt thu (`src/common`, `billing`) | Hệ thống Core, Auth/RBAC, Biểu phí, Lập đợt thu (`US-15..20`, `US-36..43`) | System Architect / Backend Lead | Lê Trường Giang (Chủ trì kỹ thuật) | Đã phê duyệt khung |
| **4** | Phân hệ Thủ quỹ & Thực thu (`src/modules/cashier`) | Thu phí tại quầy/chuyển khoản, Quỹ tự nguyện, Biên lai (`US-21..28`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
| **5** | Phân hệ Cổng cư dân & Tra cứu (`src/modules/portal`) | Portal Cư dân, Tra cứu hóa đơn, Gửi yêu cầu/khiếu nại (`US-29..35`) | Module Owner / Developer | *[Chờ phân công chính thức]* | Chờ ký duyệt |
