# HỢP ĐỒNG API HỆ THỐNG BLUEMOON (API CONTRACT SPECIFICATION)

> **THÔNG TIN PHÁP LÝ & QUYỀN SỞ HỮU:**
> - **Tác giả thiết kế & Quản trị:** `TV5: Vũ Trung Kiên` (Database & API Contract Specialist).
> - **Tệp nguồn máy đọc (OpenAPI 3.0.3):** [docs/openapi.yaml](file:///z:/Desktop/bluemoon-management-system/docs/openapi.yaml) (6.034 dòng).
> - **Đơn vị hiện thực Backend:** `TV1: Lê Trường Giang` & `TV2: Nguyễn Việt Tùng` (FastAPI app, routers, models, schemas).
> - **Đơn vị tiêu thụ Frontend:** `TV3: Nguyễn Thanh Hải` & `TV4: Lê Nguyễn Nhật Huy` (React/TypeScript UI components).
> - **Phiên bản:** `1.1.0` | **Tổng số Endpoint:** `97 endpoints` | **Phạm vi:** 47 User Stories v1.0.

---

## MỤC LỤC

1. [Chương 1: Quy ước chung & Tiêu chuẩn kỹ thuật](#chương-1-quy-ước-chung--tiêu-chuẩn-kỹ-thuật)
   - [1.1. Giao thức & Định dạng dữ liệu](#11-giao-thức--định-dạng-dữ-liệu)
   - [1.2. Chuẩn xử lý lỗi (Error Handling)](#12-chuẩn-xử-lý-lỗi-error-handling)
   - [1.3. Ma trận phân quyền vai trò (RBAC Matrix)](#13-ma-trận-phân-quyền-vai-trò-rbac-matrix)
2. [Chương 2: Danh mục 17 Phân hệ chức năng](#chương-2-danh-mục-17-phân-hệ-chức-năng)
3. [Chương 3: Đặc tả chi tiết 97 Endpoint theo phân hệ](#chương-3-đặc-tả-chi-tiết-97-endpoint-theo-phân-hệ)
   - [3.1. Phân hệ Auth (4 endpoints)](#31-phân-hệ-auth)
   - [3.2. Phân hệ Users (9 endpoints)](#32-phân-hệ-users)
   - [3.3. Phân hệ System (3 endpoints)](#33-phân-hệ-system)
   - [3.4. Phân hệ Apartments (4 endpoints)](#34-phân-hệ-apartments)
   - [3.5. Phân hệ Households (8 endpoints)](#35-phân-hệ-households)
   - [3.6. Phân hệ Residents (7 endpoints)](#36-phân-hệ-residents)
   - [3.7. Phân hệ Temporary stays (7 endpoints)](#37-phân-hệ-temporary-stays)
   - [3.8. Phân hệ Import (1 endpoints)](#38-phân-hệ-import)
   - [3.9. Phân hệ Portal (7 endpoints)](#39-phân-hệ-portal)
   - [3.10. Phân hệ Change requests (3 endpoints)](#310-phân-hệ-change-requests)
   - [3.11. Phân hệ Fee catalog (9 endpoints)](#311-phân-hệ-fee-catalog)
   - [3.12. Phân hệ Service providers (4 endpoints)](#312-phân-hệ-service-providers)
   - [3.13. Phân hệ Vehicles (4 endpoints)](#313-phân-hệ-vehicles)
   - [3.14. Phân hệ Billing (10 endpoints)](#314-phân-hệ-billing)
   - [3.15. Phân hệ Cashier (6 endpoints)](#315-phân-hệ-cashier)
   - [3.16. Phân hệ Donations (6 endpoints)](#316-phân-hệ-donations)
   - [3.17. Phân hệ Search & Reports (5 endpoints)](#317-phân-hệ-search--reports)
4. [Chương 4: Ma trận đối soát User Story $\leftrightarrow$ Endpoints (RTM)](#chương-4-ma-trận-đối-soát-user-story-\leftrightarrow-endpoints-rtm)
5. [Chương 5: Phụ lục các Schema dữ liệu cốt lõi (DTO Models)](#chương-5-phụ-lục-các-schema-dữ-liệu-cốt-lõi-dto-models)

---

## CHƯƠNG 1: QUY ƯỚC CHUNG & TIÊU CHUẨN KỸ THUẬT

### 1.1. Giao thức & Định dạng dữ liệu

- **Base URL:** `/api/v1`.
  * Development (FastAPI trực tiếp): `http://localhost:8000/api/v1`
  * Gateway / Docker Proxy: `http://localhost:8080/api/v1`
- **Định dạng dữ liệu:** JSON UTF-8 cho toàn bộ request/response body. Tên trường sử dụng định dạng **`snake_case`**.
- **Xác thực:** Bearer Token qua header `Authorization: Bearer <JWT_TOKEN>`. Mọi endpoint đều bắt buộc có token, ngoại trừ `POST /auth/login`.
- **Tiền tệ:** Luôn là số nguyên **`int64`** (đơn vị: VNĐ). CSDL lưu `numeric(14,2)` nhưng trong nghiệp vụ v1.0 luôn là số chẵn đồng. Backend tự động làm tròn đến hàng đơn vị khi tính phí. Ngoại lệ: `discount_value` của miễn giảm dạng `PERCENT` (0–100, cho phép số thập phân).
- **Thời gian:**
  * Định dạng ngày: `YYYY-MM-DD` (ví dụ: `2026-11-05`).
  * Định dạng thời điểm: ISO 8601 kèm múi giờ (ví dụ: `2026-11-05T09:30:00+07:00`).
- **Phân trang chuẩn:** Mọi API trả về danh sách đều hỗ trợ query parameters `page` (tối thiểu 1, mặc định 1) và `page_size` (mặc định 20, tối đa 100). Cấu trúc phản hồi luôn gồm:
  ```json
  {
    "items": [...],
    "page": 1,
    "page_size": 20,
    "total": 100
  }
  ```
- **Xuất file báo cáo:** Hỗ trợ query parameter `format` (`json` mặc định, `xlsx`, `pdf`). Khi xuất file nhị phân, server trả về kèm header `Content-Disposition: attachment; filename="..."`.
- **Nguyên tắc No Hard Delete:** Thao tác xóa bản ghi luôn là xóa logic, hủy hoặc chuyển trạng thái sang `INACTIVE` / `CANCELLED`.
- **Danh tính người thao tác:** Các trường kiểm toán như `created_by`, `collected_by`, `approved_by`, `recorded_by` luôn được Backend trích xuất trực tiếp từ payload của JWT Token, tuyệt đối không nhận từ tham số client gửi lên.
- **Tính Idempotent (Chống gửi trùng):** Endpoint thanh toán `POST /payments` bắt buộc truyền header `Idempotency-Key` (UUID v4) để ngăn ngừa việc bấm đúp tạo trùng biên lai thu tiền.

### 1.2. Chuẩn xử lý lỗi (Error Handling)

Mọi lỗi từ hệ thống đều trả về cấu trúc JSON đồng nhất `Error`:
```json
{
  "code": "ERROR_CODE_STRING",
  "message": "Mô tả chi tiết nguyên nhân lỗi cho người dùng",
  "details": {}
}
```

| Mã HTTP | Tên mã (`code`) | Ý nghĩa và trường hợp áp dụng |
| :---: | :--- | :--- |
| **400** | `VALIDATION_ERROR`, `WRONG_OLD_PASSWORD` | Dữ liệu đầu vào không hợp lệ; trường `details` chỉ rõ lỗi tại từng field. |
| **401** | `UNAUTHENTICATED`, `INVALID_CREDENTIALS` | Chưa đăng nhập, token hết hạn hoặc sai tên đăng nhập/mật khẩu. |
| **403** | `FORBIDDEN`, `PASSWORD_CHANGE_REQUIRED` | Không đủ quyền theo RBAC; hoặc bắt buộc phải đổi mật khẩu lần đầu. Backend tự động ghi Audit Log `ACCESS_DENIED`. |
| **404** | `NOT_FOUND` | Không tìm thấy bản ghi (khi Cư dân gọi dữ liệu hộ khác cũng nhận 404 để chống IDOR). |
| **409** | Nghiệp vụ cụ thể: `DUPLICATE_CCCD`, `DUPLICATE_APARTMENT_CODE`, `HEAD_ALREADY_EXISTS`, `DEBT_NOT_SETTLED`, `PERIOD_HAS_PAYMENTS`, `PERIOD_CLOSED`, `RATE_OVERLAP`, `IDEMPOTENCY_KEY_REUSED`, `ALREADY_CANCELLED` | Vi phạm các ràng buộc nghiệp vụ bất biến của hệ thống. |
| **422** | `IMPORT_FAILED` | File import Excel có dòng dữ liệu sai, toàn bộ transaction đã được rollback. |
| **423** | `ACCOUNT_LOCKED` | Nhập sai mật khẩu 5 lần liên tiếp, tài khoản bị tạm khóa 15 phút (`AC-28.2`). |
| **500** | `INTERNAL_SERVER_ERROR` | Lỗi phía máy chủ hoặc kết nối cơ sở dữ liệu. |

### 1.3. Ma trận phân quyền vai trò (RBAC Matrix)

Hệ thống có 4 vai trò chính: `ADMIN` (Ban quản trị kiêm Quản trị hệ thống), `ACCOUNTANT` (Kế toán), `TREASURER` (Thủ quỹ), và `RESIDENT` (Cư dân).

| Nhóm chức năng nghiệp vụ | ADMIN | ACCOUNTANT | TREASURER | RESIDENT |
| :--- | :---: | :---: | :---: | :---: |
| Quản lý người dùng, phân quyền vai trò, audit log, sao lưu | ✔ | | | |
| Quản lý căn hộ, hộ gia đình, nhân khẩu, biến động, tạm trú/vắng, xe | ✔ | Chỉ xem | | |
| Import dữ liệu Excel, duyệt đề nghị chỉnh sửa của cư dân | ✔ | | | |
| Danh mục khoản thu, đơn giá, chính sách miễn giảm, kỳ thu, chỉ số điện nước | ✔ | ✔ | | |
| Thu tiền tại quầy, xuất và in biên lai điện tử | | ✔ | ✔ | |
| Hủy biên lai thu sai (kèm lý do bắt buộc) | ✔ | ✔ | | |
| Quản lý các đợt vận động và thu đóng góp quỹ tự nguyện | ✔ | ✔ | ✔ | |
| Báo cáo công nợ, tổng hợp doanh thu theo kỳ/tháng | ✔ | ✔ | | |
| Báo cáo cư trú Công an, thống kê nhân khẩu, Dashboard BQT | ✔ | | | |
| Cổng cư dân (`/portal/*` tra cứu hộ, công nợ, gửi đề nghị) | | | | ✔ |

---

## CHƯƠNG 2: DANH MỤC 17 PHÂN HỆ CHỨC NĂNG

| STT | Tên Phân hệ (Tag) | Số lượng Endpoint | Mô tả nghiệp vụ tóm tắt |
| :---: | :--- | :---: | :--- |
| 1 | **Auth** | **4** | Đăng nhập, đăng xuất, đổi mật khẩu |
| 2 | **Users** | **9** | Tài khoản và phân quyền |
| 3 | **System** | **3** | Nhật ký thao tác, sao lưu |
| 4 | **Apartments** | **4** | Căn hộ |
| 5 | **Households** | **8** | Hộ gia đình |
| 6 | **Residents** | **7** | Nhân khẩu và biến động |
| 7 | **Temporary stays** | **7** | Tạm trú, tạm vắng |
| 8 | **Import** | **1** | Nhập dữ liệu từ Excel |
| 9 | **Portal** | **7** | Cổng cư dân (chỉ RESIDENT) |
| 10 | **Change requests** | **3** | Duyệt đề nghị chỉnh sửa từ cư dân |
| 11 | **Fee catalog** | **9** | Khoản thu, đơn giá, miễn giảm |
| 12 | **Service providers** | **4** | Thu hộ và đối soát nhà cung cấp |
| 13 | **Vehicles** | **4** | Phương tiện |
| 14 | **Billing** | **10** | Kỳ thu, giấy báo, chỉ số điện nước |
| 15 | **Cashier** | **6** | Thu ngân, biên lai |
| 16 | **Donations** | **6** | Quỹ vận động tự nguyện |
| 17 | **Search & Reports** | **5** | Tìm kiếm, báo cáo, dashboard |
| | **TỔNG CỘNG** | **97** | **Toàn bộ 47 User Stories của hệ thống** |

---

## CHƯƠNG 3: ĐẶC TẢ CHI TIẾT 97 ENDPOINT THEO PHÂN HỆ

### 3.1. Phân hệ Auth
*Đăng nhập, đăng xuất, đổi mật khẩu* (Gồm 4 endpoints)

#### 3.1.1. `POST /auth/login` — Đăng nhập
- **Operation ID:** `login`
- **User Stories:** `US-28`
- **Quyền gọi (Roles):** **`public`**
- **Mô tả nghiệp vụ:** Sai mật khẩu 5 lần liên tiếp thì khóa 15 phút (AC-28.2). Nếu `user.must_change_password = true`, client phải đổi mật khẩu trước khi dùng các endpoint khác.
- **Request Body:** Schema [`LoginRequest`](#schema-loginrequest)
  * *Các trường:* `username**\***` (string); `password**\***` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: Đăng nhập thành công (Trả về `LoginResponse`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`423`**: Tài khoản đang bị khóa tạm thời (`ACCOUNT_LOCKED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.1.2. `POST /auth/logout` — Đăng xuất
- **Operation ID:** `logout`
- **User Stories:** `US-28`
- **Quyền gọi (Roles):** **`all`**
- **Mô tả nghiệp vụ:** Server đưa token vào danh sách thu hồi (blacklist) đến khi token hết hạn.
- **Mã phản hồi HTTP:**
  * **`204`**: Đã đăng xuất
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.1.3. `GET /auth/me` — Thông tin tài khoản đang đăng nhập
- **Operation ID:** `getMe`
- **User Stories:** `US-28`
- **Quyền gọi (Roles):** **`all`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `User`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.1.4. `POST /auth/change-password` — Đổi mật khẩu cá nhân
- **Operation ID:** `changePassword`
- **User Stories:** `US-29`
- **Quyền gọi (Roles):** **`all`**
- **Mô tả nghiệp vụ:** Cho phép cả khi đang ở trạng thái `PASSWORD_CHANGE_REQUIRED`. Sai mật khẩu cũ trả `400 WRONG_OLD_PASSWORD` (không dùng 401 để tránh client tự đăng xuất).
- **Request Body:** Schema [`ChangePasswordRequest`](#schema-changepasswordrequest)
  * *Các trường:* `old_password**\***` (string); `new_password**\***` (string)
- **Mã phản hồi HTTP:**
  * **`204`**: Đã đổi mật khẩu
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.2. Phân hệ Users
*Tài khoản và phân quyền* (Gồm 9 endpoints)

#### 3.2.1. `GET /roles` — Danh sách vai trò
- **Operation ID:** `listRoles`
- **User Stories:** `US-31`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Role`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.2. `GET /users` — Danh sách tài khoản
- **Operation ID:** `listUsers`
- **User Stories:** `US-30`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `UserPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.3. `POST /users` — Tạo tài khoản nhân sự
- **Operation ID:** `createUser`
- **User Stories:** `US-30`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Chỉ tạo tài khoản nhân sự (ADMIN, ACCOUNTANT, TREASURER). Tài khoản `RESIDENT` do hệ thống tự sinh khi tạo hộ (D-12).
- **Request Body:** Schema [`UserCreate`](#schema-usercreate)
  * *Các trường:* `username**\***` (string); `full_name**\***` (string); `email` (string); `phone` (string); `role_id**\***` (integer): Id vai trò nhân sự (không phải RESIDENT)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `UserWithTempPassword`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_USERNAME` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.4. `GET /users/{userId}` — Chi tiết tài khoản
- **Operation ID:** `getUser`
- **User Stories:** `US-30`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `User`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.5. `PATCH /users/{userId}` — Cập nhật thông tin tài khoản
- **Operation ID:** `updateUser`
- **User Stories:** `US-30`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`UserUpdate`](#schema-userupdate)
  * *Các trường:* `full_name` (string); `email` (string); `phone` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `User`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.6. `PUT /users/{userId}/role` — Gán hoặc thu hồi vai trò
- **Operation ID:** `setUserRole`
- **User Stories:** `US-31`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Không được gán vai trò `RESIDENT` cho tài khoản nhân sự và ngược lại. Ghi audit log.
- **Request Body:** Schema [`UserRoleUpdate`](#schema-userroleupdate)
  * *Các trường:* `role_id**\***` (integer)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `User`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `CANNOT_CHANGE_OWN_ROLE` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.7. `POST /users/{userId}/lock` — Khóa tài khoản
- **Operation ID:** `lockUser`
- **User Stories:** `US-30`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `User`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `CANNOT_LOCK_SELF` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.8. `POST /users/{userId}/unlock` — Mở khóa tài khoản
- **Operation ID:** `unlockUser`
- **User Stories:** `US-30`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `User`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.2.9. `POST /users/{userId}/reset-password` — Cấp lại mật khẩu tạm
- **Operation ID:** `resetUserPassword`
- **User Stories:** `US-30`, `US-29`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Mật khẩu tạm chỉ hiển thị một lần; tài khoản bị buộc đổi mật khẩu ở lần đăng nhập kế tiếp.
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `TempPassword`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.3. Phân hệ System
*Nhật ký thao tác, sao lưu* (Gồm 3 endpoints)

#### 3.3.1. `GET /audit-logs` — Xem và lọc nhật ký thao tác
- **Operation ID:** `listAuditLogs`
- **User Stories:** `US-32`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `AuditLogPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.3.2. `POST /system/backups` — Chạy sao lưu thủ công
- **Operation ID:** `createBackup`
- **User Stories:** `US-45`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`202`**: Đã nhận yêu cầu, sao lưu chạy nền (Trả về `BackupJob`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.3.3. `GET /system/backups` — Lịch sử sao lưu
- **Operation ID:** `listBackups`
- **User Stories:** `US-45`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `BackupJobPage`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.4. Phân hệ Apartments
*Căn hộ* (Gồm 4 endpoints)

#### 3.4.1. `GET /apartments` — Danh sách căn hộ
- **Operation ID:** `listApartments`
- **User Stories:** `US-01`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ApartmentPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.4.2. `POST /apartments` — Tạo căn hộ mới
- **Operation ID:** `createApartment`
- **User Stories:** `US-01`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`ApartmentCreate`](#schema-apartmentcreate)
  * *Các trường:* `code**\***` (string); `floor**\***` (integer); `area_m2**\***` (number): Diện tích > 0 (AC-01.1); `note` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `Apartment`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_APARTMENT_CODE` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.4.3. `GET /apartments/{id}` — Chi tiết căn hộ
- **Operation ID:** `getApartment`
- **User Stories:** `US-01`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Apartment`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.4.4. `PATCH /apartments/{id}` — Cập nhật căn hộ
- **Operation ID:** `updateApartment`
- **User Stories:** `US-01`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Đổi diện tích không làm thay đổi giấy báo của các kỳ đã tạo (đã snapshot).
- **Request Body:** Schema [`ApartmentUpdate`](#schema-apartmentupdate)
  * *Các trường:* `floor` (integer); `area_m2` (number); `status` (string); `note` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Apartment`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.5. Phân hệ Households
*Hộ gia đình* (Gồm 8 endpoints)

#### 3.5.1. `GET /households` — Danh sách hộ gia đình
- **Operation ID:** `listHouseholds`
- **User Stories:** `US-01`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `HouseholdPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.5.2. `POST /households` — Tạo hộ gia đình mới (tự động sinh tài khoản cư dân - D-12)
- **Operation ID:** `createHousehold`
- **User Stories:** `US-01`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** `apartment_id` có thể bỏ trống nếu hộ sẽ nhận căn hộ qua `POST /households/{id}/transfer`. Có thể gửi kèm `head` để tạo luôn chủ hộ.'
- **Request Body:** Schema [`HouseholdCreate`](#schema-householdcreate)
  * *Các trường:* `household_code**\***` (string); `apartment_id` (integer): Bỏ trống nếu nhận căn hộ qua chuyển nhượng; `occupancy_start_date` (string): Mặc định là ngày tạo; `contact_phone` (string); `contact_email` (string); `note` (string)...
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo, trả về thông tin hộ và tài khoản cư dân (Trả về `HouseholdCreated`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_HOUSEHOLD_CODE`, `APARTMENT_OCCUPIED`, (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.5.3. `GET /households/{id}` — Chi tiết hộ gia đình
- **Operation ID:** `getHousehold`
- **User Stories:** `US-01`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Household`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.5.4. `PATCH /households/{id}` — Cập nhật thông tin liên hệ của hộ
- **Operation ID:** `updateHousehold`
- **User Stories:** `US-02`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`HouseholdUpdate`](#schema-householdupdate)
  * *Các trường:* `contact_phone` (string); `contact_email` (string); `note` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Household`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.5.5. `POST /households/{id}/deactivate` — Ngừng quản lý hộ
- **Operation ID:** `deactivateHousehold`
- **User Stories:** `US-02`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Chỉ được ngừng khi hộ không còn công nợ. Hộ chuyển sang `INACTIVE`, không xóa dữ liệu.
- **Request Body:** Schema [`HouseholdDeactivate`](#schema-householddeactivate)
  * *Các trường:* `reason**\***` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Household`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DEBT_NOT_SETTLED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.5.6. `POST /households/{id}/transfer` — Chuyển nhượng căn hộ từ hộ này sang hộ mới
- **Operation ID:** `transferHousehold`
- **User Stories:** `US-03`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** `{id}` là hộ đang giữ căn hộ. Kết thúc `apartment_occupancies` của hộ cũ và mở bản ghi mới cho `new_household_id` tại `effective_date`. Hộ cũ phải hết công nợ.'
- **Request Body:** Schema [`HouseholdTransferRequest`](#schema-householdtransferrequest)
  * *Các trường:* `new_household_id**\***` (integer); `effective_date**\***` (string); `reason` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Household`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DEBT_NOT_SETTLED`, `APARTMENT_OCCUPIED`, `HOUSEHOLD_HAS_NO_APARTMENT` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.5.7. `PUT /households/{id}/head` — Đổi chủ hộ
- **Operation ID:** `changeHouseholdHead`
- **User Stories:** `US-05`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Hạ chủ hộ cũ và nâng nhân khẩu mới trong cùng một giao dịch. Ghi audit `CHANGE_HEAD`.
- **Request Body:** Schema [`HouseholdChangeHead`](#schema-householdchangehead)
  * *Các trường:* `new_head_resident_id**\***` (integer); `effective_date**\***` (string); `reason` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Household`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.5.8. `GET /households/{id}/credit` — Số dư có (nộp thừa) của hộ
- **Operation ID:** `getHouseholdCredit`
- **User Stories:** `US-19`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `HouseholdCredit`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.6. Phân hệ Residents
*Nhân khẩu và biến động* (Gồm 7 endpoints)

#### 3.6.1. `GET /households/{id}/residents` — Danh sách nhân khẩu trong hộ
- **Operation ID:** `listResidents`
- **User Stories:** `US-06`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ResidentPage`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.6.2. `POST /households/{id}/residents` — Thêm nhân khẩu mới
- **Operation ID:** `createResident`
- **User Stories:** `US-05`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** `cccd` được phép trống nếu nhân khẩu dưới 14 tuổi (AC-05.3), ngược lại bắt buộc.
- **Request Body:** Schema [`ResidentCreate`](#schema-residentcreate)
  * *Các trường:* `full_name**\***` (string); `date_of_birth**\***` (string); `gender**\***` (string); `cccd` (string): CCCD/CMND 9-12 chữ số; `phone` (string); `email` (string)...
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `Resident`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_CCCD`, `HEAD_ALREADY_EXISTS` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.6.3. `GET /residents/{id}` — Chi tiết nhân khẩu
- **Operation ID:** `getResident`
- **User Stories:** `US-06`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Resident`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.6.4. `PATCH /residents/{id}` — Cập nhật nhân khẩu
- **Operation ID:** `updateResident`
- **User Stories:** `US-06`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`ResidentUpdate`](#schema-residentupdate)
  * *Các trường:* `full_name` (string); `date_of_birth` (string); `gender` (string); `cccd` (string): CCCD/CMND 9-12 chữ số; `phone` (string); `email` (string)...
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Resident`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_CCCD` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.6.5. `DELETE /residents/{id}` — Xóa logic nhân khẩu
- **Operation ID:** `deleteResident`
- **User Stories:** `US-06`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`204`**: Đã xóa logic
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `CANNOT_DELETE_HEAD` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.6.6. `GET /residents/{id}/events` — Lịch sử biến động của nhân khẩu
- **Operation ID:** `listResidencyEvents`
- **User Stories:** `US-11`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ResidencyEvent`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.6.7. `POST /residents/{id}/events` — Ghi nhận biến động nhân khẩu (đến, đi, sinh, mất, trở về)
- **Operation ID:** `createResidencyEvent`
- **User Stories:** `US-07`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Biến động `TAM_TRU` và `TAM_VANG` được sinh tự động khi gọi các endpoint tạm trú, tạm vắng nên không gửi ở đây.
- **Request Body:** Schema [`ResidencyEventCreate`](#schema-residencyeventcreate)
  * *Các trường:* `event_type**\***` (string); `effective_date**\***` (string); `reason` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã ghi nhận (Trả về `ResidencyEvent`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.7. Phân hệ Temporary stays
*Tạm trú, tạm vắng* (Gồm 7 endpoints)

#### 3.7.1. `GET /temporary-stays` — Danh sách tạm trú
- **Operation ID:** `listTemporaryStays`
- **User Stories:** `US-08`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `TemporaryStayPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.7.2. `POST /temporary-stays` — Đăng ký tạm trú mới
- **Operation ID:** `createTemporaryStay`
- **User Stories:** `US-08`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`TemporaryStayCreate`](#schema-temporarystaycreate)
  * *Các trường:* `household_id**\***` (integer); `apartment_id**\***` (integer); `full_name**\***` (string); `date_of_birth` (string); `gender` (string); `cccd**\***` (string): CCCD/CMND 9-12 chữ số...
- **Mã phản hồi HTTP:**
  * **`201`**: Đã đăng ký tạm trú thành công (Trả về `TemporaryStay`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.7.3. `GET /temporary-stays/expiring` — Cảnh báo tạm trú và tạm vắng sắp hết hạn (<= 15 ngày)
- **Operation ID:** `listExpiringStays`
- **User Stories:** `US-09`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ExpiringStay`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.7.4. `POST /temporary-stays/{id}/end` — Kết thúc tạm trú
- **Operation ID:** `endTemporaryStay`
- **User Stories:** `US-08`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `TemporaryStay`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_ENDED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.7.5. `GET /temporary-absences` — Danh sách tạm vắng
- **Operation ID:** `listTemporaryAbsences`
- **User Stories:** `US-10`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `TemporaryAbsencePage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.7.6. `POST /temporary-absences` — Đăng ký tạm vắng cho nhân khẩu
- **Operation ID:** `createTemporaryAbsence`
- **User Stories:** `US-10`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`TemporaryAbsenceCreate`](#schema-temporaryabsencecreate)
  * *Các trường:* `resident_id**\***` (integer); `start_date**\***` (string); `end_date**\***` (string): Phải lớn hơn hoặc bằng start_date; `destination` (string); `reason` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã ghi nhận tạm vắng thành công (Trả về `TemporaryAbsence`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.7.7. `POST /temporary-absences/{id}/return` — Ghi nhận cư dân báo về sớm
- **Operation ID:** `returnTemporaryAbsence`
- **User Stories:** `US-10`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`TemporaryAbsenceReturn`](#schema-temporaryabsencereturn)
  * *Các trường:* `returned_date**\***` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `TemporaryAbsence`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_ENDED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.8. Phân hệ Import
*Nhập dữ liệu từ Excel* (Gồm 1 endpoints)

#### 3.8.1. `POST /import/excel` — Import dữ liệu từ Excel
- **Operation ID:** `importExcel`
- **User Stories:** `US-04`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Chạy trong một giao dịch: có bất kỳ dòng lỗi nào thì rollback toàn bộ và trả `422 IMPORT_FAILED` kèm danh sách lỗi theo dòng trong `details`.'
- **Mã phản hồi HTTP:**
  * **`200`**: Import thành công (Trả về `ImportResult`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`422`**: File import có lỗi, đã rollback (`IMPORT_FAILED`); `details` liệt kê lỗi theo dòng (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.9. Phân hệ Portal
*Cổng cư dân (chỉ RESIDENT)* (Gồm 7 endpoints)

#### 3.9.1. `GET /portal/household` — Xem thông tin hộ và nhân khẩu của mình
- **Operation ID:** `getPortalHousehold`
- **User Stories:** `US-33`
- **Quyền gọi (Roles):** **`RESIDENT`**
- **Mô tả nghiệp vụ:** Hộ được xác định từ token, không nhận `household_id` từ client.
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `PortalHousehold`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.9.2. `GET /portal/invoices` — Xem công nợ và các giấy báo của hộ mình
- **Operation ID:** `getPortalInvoices`
- **User Stories:** `US-35`
- **Quyền gọi (Roles):** **`RESIDENT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `PortalInvoicePage`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.9.3. `GET /portal/payments` — Lịch sử nộp tiền của hộ mình
- **Operation ID:** `getPortalPayments`
- **User Stories:** `US-35`
- **Quyền gọi (Roles):** **`RESIDENT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `PaymentPage`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.9.4. `GET /portal/payments/{id}/receipt` — Tải biên lai PDF của hộ mình
- **Operation ID:** `getPortalPaymentReceipt`
- **User Stories:** `US-20`
- **Quyền gọi (Roles):** **`RESIDENT`**
- **Mô tả nghiệp vụ:** Biên lai không thuộc hộ của token trả `404`.
- **Mã phản hồi HTTP:**
  * **`200`**: Tên file tải về
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.9.5. `GET /portal/donation-campaigns` — Xem các đợt vận động (chỉ tổng hợp)
- **Operation ID:** `listPortalCampaigns`
- **User Stories:** `US-40`
- **Quyền gọi (Roles):** **`RESIDENT`**
- **Mô tả nghiệp vụ:** Chỉ trả tổng số tiền của đợt, không trả số tiền hay danh tính hộ khác (WL-026).
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `DonationCampaignPage`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.9.6. `GET /portal/change-requests` — Các đề nghị chỉnh sửa đã gửi
- **Operation ID:** `listPortalChangeRequests`
- **User Stories:** `US-34`
- **Quyền gọi (Roles):** **`RESIDENT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ChangeRequestPage`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.9.7. `POST /portal/change-requests` — Gửi đề nghị chỉnh sửa thông tin
- **Operation ID:** `createChangeRequest`
- **User Stories:** `US-34`
- **Quyền gọi (Roles):** **`RESIDENT`**
- **Request Body:** Schema [`ChangeRequestCreate`](#schema-changerequestcreate)
  * *Các trường:* `request_type**\***` (string); `resident_id` (integer): Bắt buộc khi `request_type = UPDATE_RESIDENT`; `proposed_data**\***` (object); `evidence_files` (string): Danh sách file minh chứng đã tải lên
- **Mã phản hồi HTTP:**
  * **`201`**: Đã gửi (Trả về `ChangeRequest`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.10. Phân hệ Change requests
*Duyệt đề nghị chỉnh sửa từ cư dân* (Gồm 3 endpoints)

#### 3.10.1. `GET /change-requests` — Danh sách đề nghị chỉnh sửa
- **Operation ID:** `listChangeRequests`
- **User Stories:** `US-34`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ChangeRequestPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.10.2. `PUT /change-requests/{id}/approve` — Duyệt đề nghị chỉnh sửa
- **Operation ID:** `approveChangeRequest`
- **User Stories:** `US-34`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mô tả nghiệp vụ:** Duyệt thì áp dụng `proposed_data` vào dữ liệu gốc trong cùng giao dịch.
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ChangeRequest`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `REQUEST_ALREADY_PROCESSED`, `DUPLICATE_CCCD` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.10.3. `PUT /change-requests/{id}/reject` — Từ chối đề nghị chỉnh sửa
- **Operation ID:** `rejectChangeRequest`
- **User Stories:** `US-34`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`ChangeRequestReject`](#schema-changerequestreject)
  * *Các trường:* `reject_reason**\***` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ChangeRequest`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `REQUEST_ALREADY_PROCESSED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.11. Phân hệ Fee catalog
*Khoản thu, đơn giá, miễn giảm* (Gồm 9 endpoints)

#### 3.11.1. `GET /fee-types` — Danh sách khoản thu
- **Operation ID:** `listFeeTypes`
- **User Stories:** `US-12`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `FeeTypePage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.2. `POST /fee-types` — Tạo khoản thu mới
- **Operation ID:** `createFeeType`
- **User Stories:** `US-12`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Request Body:** Schema [`FeeTypeCreate`](#schema-feetypecreate)
  * *Các trường:* `code**\***` (string); `name**\***` (string); `fee_group**\***` ('FeeGroup'); `calc_method**\***` ('CalcMethod'); `unit_label**\***` (string); `vehicle_type` (string): Bắt buộc khi `calc_method = PER_VEHICLE`...
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `FeeType`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_FEE_CODE` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.3. `PATCH /fee-types/{id}` — Cập nhật khoản thu
- **Operation ID:** `updateFeeType`
- **User Stories:** `US-12`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Không cho đổi `code`, `calc_method` khi khoản thu đã phát sinh giấy báo.
- **Request Body:** Schema [`FeeTypeUpdate`](#schema-feetypeupdate)
  * *Các trường:* `name` (string); `unit_label` (string); `provider_id` (integer); `cycle` (string); `due_day` (integer); `description` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `FeeType`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `FEE_TYPE_IN_USE` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.4. `POST /fee-types/{id}/deactivate` — Ngừng áp dụng khoản thu
- **Operation ID:** `deactivateFeeType`
- **User Stories:** `US-13`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Không xóa; chỉ chuyển `INACTIVE` (AC-13.1).
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `FeeType`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.5. `GET /fee-types/{id}/rates` — Lịch sử đơn giá của khoản thu
- **Operation ID:** `listFeeRates`
- **User Stories:** `US-14`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `FeeRate`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.6. `POST /fee-types/{id}/rates` — Cập nhật đơn giá mới
- **Operation ID:** `createFeeRate`
- **User Stories:** `US-14`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Đơn giá đang áp dụng (không có ngày kết thúc) được server tự khép lại vào ngày trước `effective_from`.
- **Request Body:** Schema [`FeeRateCreate`](#schema-feeratecreate)
  * *Các trường:* `unit_price**\***` (integer): Đơn giá (VNĐ); `effective_from**\***` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `FeeRate`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `RATE_OVERLAP` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.7. `GET /fee-exemptions` — Danh sách chính sách miễn giảm
- **Operation ID:** `listExemptions`
- **User Stories:** `US-15`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `FeeExemptionPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.8. `POST /fee-exemptions` — Tạo chính sách miễn giảm
- **Operation ID:** `createExemption`
- **User Stories:** `US-15`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** `approved_by` lấy từ token của người tạo.
- **Request Body:** Schema [`ExemptionCreate`](#schema-exemptioncreate)
  * *Các trường:* `household_id**\***` (integer); `fee_type_id**\***` (integer); `discount_type**\***` (string); `discount_value**\***` (number): PERCENT: 0-100 (có thể lẻ). AMOUNT: số tiền VNĐ nguyên; `reason**\***` (string); `decision_no` (string)...
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `FeeExemption`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.11.9. `POST /fee-exemptions/{id}/revoke` — Thu hồi chính sách miễn giảm
- **Operation ID:** `revokeExemption`
- **User Stories:** `US-16`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `FeeExemption`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_REVOKED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.12. Phân hệ Service providers
*Thu hộ và đối soát nhà cung cấp* (Gồm 4 endpoints)

#### 3.12.1. `GET /service-providers` — Danh sách nhà cung cấp (điện, nước, internet)
- **Operation ID:** `listServiceProviders`
- **User Stories:** `US-39`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ServiceProviderPage`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.12.2. `POST /service-providers` — Thêm nhà cung cấp
- **Operation ID:** `createServiceProvider`
- **User Stories:** `US-39`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Request Body:** Schema [`ServiceProviderCreate`](#schema-serviceprovidercreate)
  * *Các trường:* `name**\***` (string); `service_type**\***` (string); `contact` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `ServiceProvider`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.12.3. `GET /provider-settlements` — Đối soát thu hộ theo kỳ
- **Operation ID:** `listProviderSettlements`
- **User Stories:** `US-39`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ProviderSettlementPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.12.4. `POST /provider-settlements/{id}/reconcile` — Ghi nhận đã nộp lại nhà cung cấp
- **Operation ID:** `reconcileProviderSettlement`
- **User Stories:** `US-39`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Request Body:** Schema [`ProviderSettlementReconcile`](#schema-providersettlementreconcile)
  * *Các trường:* `amount_remitted**\***` (integer); `remitted_date**\***` (string); `note` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `ProviderSettlement`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_RECONCILED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.13. Phân hệ Vehicles
*Phương tiện* (Gồm 4 endpoints)

#### 3.13.1. `GET /vehicles` — Danh sách phương tiện
- **Operation ID:** `listVehicles`
- **User Stories:** `US-36`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `VehiclePage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.13.2. `POST /vehicles` — Đăng ký phương tiện
- **Operation ID:** `createVehicle`
- **User Stories:** `US-36`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`VehicleCreate`](#schema-vehiclecreate)
  * *Các trường:* `household_id**\***` (integer); `plate_number**\***` (string); `vehicle_type**\***` ('VehicleType'); `brand` (string); `color` (string); `registered_date` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `Vehicle`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_PLATE` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.13.3. `PATCH /vehicles/{id}` — Cập nhật phương tiện
- **Operation ID:** `updateVehicle`
- **User Stories:** `US-36`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`VehicleUpdate`](#schema-vehicleupdate)
  * *Các trường:* `plate_number` (string); `vehicle_type` ('VehicleType'); `brand` (string); `color` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Vehicle`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.13.4. `POST /vehicles/{id}/unregister` — Hủy đăng ký phương tiện
- **Operation ID:** `unregisterVehicle`
- **User Stories:** `US-36`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Request Body:** Schema [`VehicleUnregister`](#schema-vehicleunregister)
  * *Các trường:* `unregistered_date` (string): Mặc định là ngày hiện tại
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Vehicle`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_INACTIVE` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.14. Phân hệ Billing
*Kỳ thu, giấy báo, chỉ số điện nước* (Gồm 10 endpoints)

#### 3.14.1. `GET /billing-periods` — Danh sách kỳ thu
- **Operation ID:** `listBillingPeriods`
- **User Stories:** `US-17`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `BillingPeriodPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.2. `POST /billing-periods` — Tạo kỳ thu mới
- **Operation ID:** `createBillingPeriod`
- **User Stories:** `US-17`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Request Body:** Schema [`BillingPeriodCreate`](#schema-billingperiodcreate)
  * *Các trường:* `period_month**\***` (string): Ngày 1 của tháng; `name**\***` (string); `due_date` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `BillingPeriod`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_PERIOD` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.3. `GET /billing-periods/{id}` — Chi tiết kỳ thu
- **Operation ID:** `getBillingPeriod`
- **User Stories:** `US-17`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `BillingPeriod`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.4. `POST /billing-periods/{id}/generate` — Chạy động cơ tính phí tự động cho toàn bộ hộ
- **Operation ID:** `generateInvoices`
- **User Stories:** `US-17`, `US-37`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Snapshot đơn giá và diện tích vào giấy báo. Chạy lại khi kỳ đã có biên lai trả `409 PERIOD_HAS_PAYMENTS`.
- **Mã phản hồi HTTP:**
  * **`200`**: Tính toán thành công (Trả về `GenerateResult`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `PERIOD_HAS_PAYMENTS`, `PERIOD_CLOSED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.5. `POST /billing-periods/{id}/close` — Chốt kỳ thu
- **Operation ID:** `closeBillingPeriod`
- **User Stories:** `US-17`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Sau khi chốt, không sửa chỉ số điện nước hay chạy lại tính phí của kỳ này.
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `BillingPeriod`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `PERIOD_CLOSED`, `PERIOD_NOT_GENERATED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.6. `GET /invoices` — Danh sách giấy báo nộp phí
- **Operation ID:** `listInvoices`
- **User Stories:** `US-17`, `US-47`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `InvoicePage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.7. `GET /invoices/{id}` — Chi tiết giấy báo (kèm từng khoản)
- **Operation ID:** `getInvoice`
- **User Stories:** `US-47`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `InvoiceDetail`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.8. `GET /utility-readings` — Danh sách chỉ số điện/nước
- **Operation ID:** `listUtilityReadings`
- **User Stories:** `US-38`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `UtilityReadingPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.9. `POST /utility-readings` — Nhập chỉ số điện/nước
- **Operation ID:** `createUtilityReading`
- **User Stories:** `US-38`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** `current_index` phải >= `previous_index`. Bỏ trống `unit_price` thì server lấy đơn giá hiệu lực của khoản thu.'
- **Request Body:** Schema [`UtilityReadingCreate`](#schema-utilityreadingcreate)
  * *Các trường:* `household_id**\***` (integer); `fee_type_id**\***` (integer); `billing_period_id**\***` (integer); `previous_index**\***` (number); `current_index**\***` (number); `unit_price` (integer): Tùy chọn; mặc định lấy đơn giá hiệu lực của khoản thu
- **Mã phản hồi HTTP:**
  * **`201`**: Đã lưu chỉ số (Trả về `UtilityReading`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_READING`, `PERIOD_CLOSED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.14.10. `PATCH /utility-readings/{id}` — Sửa chỉ số điện/nước
- **Operation ID:** `updateUtilityReading`
- **User Stories:** `US-38`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Request Body:** Schema [`UtilityReadingUpdate`](#schema-utilityreadingupdate)
  * *Các trường:* `previous_index` (number); `current_index` (number); `unit_price` (integer)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `UtilityReading`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `PERIOD_CLOSED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.15. Phân hệ Cashier
*Thu ngân, biên lai* (Gồm 6 endpoints)

#### 3.15.1. `GET /cashier/search` — Tìm kiếm nhanh hộ tại quầy thu ngân
- **Operation ID:** `cashierSearch`
- **User Stories:** `US-18`
- **Quyền gọi (Roles):** **`TREASURER`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK, trả về thông tin hộ và công nợ (Trả về `CashierHousehold`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.15.2. `GET /payments` — Danh sách biên lai
- **Operation ID:** `listPayments`
- **User Stories:** `US-19`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `PaymentPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.15.3. `POST /payments` — Ghi nhận thu tiền và gạch nợ
- **Operation ID:** `createPayment`
- **User Stories:** `US-19`
- **Quyền gọi (Roles):** **`TREASURER`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Người thu (`collected_by`) lấy từ token. Nếu bỏ `allocations`, server gạch nợ theo thứ tự kỳ cũ nhất trước; phần còn lại ghi vào số dư có của hộ (AC-19.5). Cùng `Idempotency-Key` và cùng nội dung sẽ trả lại biên lai đã tạo (`200`), khác nội dung trả `409 IDEMPOTENCY_KEY_REUSED`.
- **Request Body:** Schema [`PaymentCreate`](#schema-paymentcreate)
  * *Các trường:* `household_id**\***` (integer); `amount**\***` (integer): Tổng tiền khách nộp (VNĐ); `method**\***` (string); `reference_no` (string): Mã giao dịch ngân hàng, nên bắt buộc khi `BANK_TRANSFER`; `note` (string); `allocations` ('PaymentAllocation'): Gạch nợ chỉ định. Bỏ trống thì tự gạch theo kỳ cũ nhất. Tổng <= amount; phần dư vào số dư
- **Mã phản hồi HTTP:**
  * **`200`**: Yêu cầu trùng `Idempotency-Key`, trả lại biên lai đã tạo trước đó (Trả về `Payment`)
  * **`201`**: Đã tạo biên lai (Trả về `Payment`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `IDEMPOTENCY_KEY_REUSED`, `ALLOCATION_EXCEEDS_DEBT`, (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.15.4. `GET /payments/{id}` — Chi tiết biên lai (kèm gạch nợ)
- **Operation ID:** `getPayment`
- **User Stories:** `US-19`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Payment`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.15.5. `POST /payments/{id}/cancel` — Hủy biên lai thu sai
- **Operation ID:** `cancelPayment`
- **User Stories:** `US-22`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Hoàn lại công nợ và số dư có, giữ nguyên số biên lai (không nhảy số). Ghi audit `CANCEL_RECEIPT`.
- **Request Body:** Schema [`PaymentCancel`](#schema-paymentcancel)
  * *Các trường:* `cancel_reason**\***` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: Đã hủy biên lai và hoàn lại công nợ (Trả về `Payment`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_CANCELLED`, `PERIOD_CLOSED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.15.6. `GET /payments/{id}/receipt` — Xuất biên lai PDF
- **Operation ID:** `getPaymentReceipt`
- **User Stories:** `US-20`
- **Quyền gọi (Roles):** **`TREASURER`**, **`ACCOUNTANT`**
- **Mô tả nghiệp vụ:** Từ lần in thứ 2 trở đi, biên lai được đóng dấu BẢN SAO (AC-20.2). Cư dân dùng `/portal/payments/{id}/receipt`.
- **Mã phản hồi HTTP:**
  * **`200`**: Tên file tải về
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.16. Phân hệ Donations
*Quỹ vận động tự nguyện* (Gồm 6 endpoints)

#### 3.16.1. `GET /donation-campaigns` — Danh sách đợt vận động
- **Operation ID:** `listCampaigns`
- **User Stories:** `US-40`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `DonationCampaignPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.16.2. `POST /donation-campaigns` — Tạo đợt vận động mới
- **Operation ID:** `createCampaign`
- **User Stories:** `US-40`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Request Body:** Schema [`DonationCampaignCreate`](#schema-donationcampaigncreate)
  * *Các trường:* `code**\***` (string); `name**\***` (string); `description` (string); `start_date**\***` (string); `end_date` (string): Phải >= start_date
- **Mã phản hồi HTTP:**
  * **`201`**: Đã tạo (Trả về `DonationCampaign`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `DUPLICATE_CAMPAIGN_CODE` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.16.3. `POST /donation-campaigns/{id}/close` — Kết thúc đợt vận động
- **Operation ID:** `closeCampaign`
- **User Stories:** `US-40`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `DonationCampaign`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_CLOSED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.16.4. `GET /donations` — Danh sách đóng góp
- **Operation ID:** `listDonations`
- **User Stories:** `US-41`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `DonationPage`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.16.5. `POST /donations` — Ghi nhận đóng góp tự nguyện
- **Operation ID:** `createDonation`
- **User Stories:** `US-41`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mô tả nghiệp vụ:** Người thu lấy từ token. Khoản đóng góp tách hẳn khỏi công nợ (AC-40.1).
- **Request Body:** Schema [`DonationCreate`](#schema-donationcreate)
  * *Các trường:* `campaign_id**\***` (integer); `household_id**\***` (integer); `amount**\***` (integer); `method**\***` (string); `note` (string)
- **Mã phản hồi HTTP:**
  * **`201`**: Đã ghi nhận, sinh phiếu xác nhận (Trả về `Donation`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `CAMPAIGN_CLOSED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.16.6. `POST /donations/{id}/cancel` — Hủy phiếu đóng góp
- **Operation ID:** `cancelDonation`
- **User Stories:** `US-41`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Request Body:** Schema [`DonationCancel`](#schema-donationcancel)
  * *Các trường:* `cancel_reason**\***` (string)
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Donation`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`404`**: Không tìm thấy (`NOT_FOUND`) (Trả về `Error`)
  * **`409`**: Xung đột nghiệp vụ. Mã `code` có thể gặp: `ALREADY_CANCELLED` (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

### 3.17. Phân hệ Search & Reports
*Tìm kiếm, báo cáo, dashboard* (Gồm 5 endpoints)

#### 3.17.1. `GET /search` — Tìm kiếm đa tiêu chí (Omnibox)
- **Operation ID:** `globalSearch`
- **User Stories:** `US-23`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**, **`TREASURER`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK, trả về kết quả gộp từ nhiều thực thể (Trả về `SearchResult`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.17.2. `GET /reports/revenue` — Báo cáo tổng thu theo tháng/khoản thu
- **Operation ID:** `getRevenueReport`
- **User Stories:** `US-24`, `US-25`, `US-26`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: Có khi format là xlsx hoặc pdf (Trả về `RevenueReport`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.17.3. `GET /reports/debt` — Báo cáo danh sách hộ nợ đọng
- **Operation ID:** `getDebtReport`
- **User Stories:** `US-21`, `US-26`
- **Quyền gọi (Roles):** **`ADMIN`**, **`ACCOUNTANT`**
- **Mã phản hồi HTTP:**
  * **`200`**: Có khi format là xlsx hoặc pdf (Trả về `DebtReport`)
  * **`400`**: Lỗi dữ liệu đầu vào (`VALIDATION_ERROR`) (Trả về `Error`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.17.4. `GET /reports/demographics` — Báo cáo thống kê cơ cấu nhân khẩu
- **Operation ID:** `getDemographicsReport`
- **User Stories:** `US-27`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: Có khi format là xlsx hoặc pdf (Trả về `DemographicsReport`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

#### 3.17.5. `GET /dashboard` — Dashboard điều hành tổng quan
- **Operation ID:** `getDashboard`
- **User Stories:** `US-43`
- **Quyền gọi (Roles):** **`ADMIN`**
- **Mã phản hồi HTTP:**
  * **`200`**: OK (Trả về `Dashboard`)
  * **`401`**: Chưa xác thực hoặc token hết hạn (`UNAUTHENTICATED`, `INVALID_CREDENTIALS`) (Trả về `Error`)
  * **`403`**: Sai vai trò (`FORBIDDEN`) hoặc phải đổi mật khẩu (`PASSWORD_CHANGE_REQUIRED`) (Trả về `Error`)
  * **`500`**: Lỗi hệ thống (Trả về `Error`)

---

## CHƯƠNG 4: MA TRẬN ĐỐI SOÁT USER STORY $\leftrightarrow$ ENDPOINTS (RTM)

Bảng đối soát trực tiếp từ 47 User Stories sang các Endpoint API phụ trách trong hệ thống:

| Mã US | Tên tóm tắt User Story | Các HTTP API Endpoints phụ trách |
| :---: | :--- | :--- |
| **US-01** | Quản lý theo chuẩn `Plan.pdf` | `GET /apartments`, `POST /apartments`, `GET /apartments/{id}`, `PATCH /apartments/{id}`, `GET /households`, `POST /households`, `GET /households/{id}` |
| **US-02** | Quản lý theo chuẩn `Plan.pdf` | `PATCH /households/{id}`, `POST /households/{id}/deactivate` |
| **US-03** | Quản lý theo chuẩn `Plan.pdf` | `POST /households/{id}/transfer` |
| **US-04** | Quản lý theo chuẩn `Plan.pdf` | `POST /import/excel` |
| **US-05** | Quản lý theo chuẩn `Plan.pdf` | `PUT /households/{id}/head`, `POST /households/{id}/residents` |
| **US-06** | Quản lý theo chuẩn `Plan.pdf` | `GET /households/{id}/residents`, `GET /residents/{id}`, `PATCH /residents/{id}`, `DELETE /residents/{id}` |
| **US-07** | Quản lý theo chuẩn `Plan.pdf` | `POST /residents/{id}/events` |
| **US-08** | Quản lý theo chuẩn `Plan.pdf` | `GET /temporary-stays`, `POST /temporary-stays`, `POST /temporary-stays/{id}/end` |
| **US-09** | Quản lý theo chuẩn `Plan.pdf` | `GET /temporary-stays/expiring` |
| **US-10** | Quản lý theo chuẩn `Plan.pdf` | `GET /temporary-absences`, `POST /temporary-absences`, `POST /temporary-absences/{id}/return` |
| **US-11** | Quản lý theo chuẩn `Plan.pdf` | `GET /residents/{id}/events` |
| **US-12** | Quản lý theo chuẩn `Plan.pdf` | `GET /fee-types`, `POST /fee-types`, `PATCH /fee-types/{id}` |
| **US-13** | Quản lý theo chuẩn `Plan.pdf` | `POST /fee-types/{id}/deactivate` |
| **US-14** | Quản lý theo chuẩn `Plan.pdf` | `GET /fee-types/{id}/rates`, `POST /fee-types/{id}/rates` |
| **US-15** | Quản lý theo chuẩn `Plan.pdf` | `GET /fee-exemptions`, `POST /fee-exemptions` |
| **US-16** | Quản lý theo chuẩn `Plan.pdf` | `POST /fee-exemptions/{id}/revoke` |
| **US-17** | Quản lý theo chuẩn `Plan.pdf` | `GET /billing-periods`, `POST /billing-periods`, `GET /billing-periods/{id}`, `POST /billing-periods/{id}/generate`, `POST /billing-periods/{id}/close`, `GET /invoices` |
| **US-18** | Quản lý theo chuẩn `Plan.pdf` | `GET /cashier/search` |
| **US-19** | Quản lý theo chuẩn `Plan.pdf` | `GET /households/{id}/credit`, `GET /payments`, `POST /payments`, `GET /payments/{id}` |
| **US-20** | Quản lý theo chuẩn `Plan.pdf` | `GET /portal/payments/{id}/receipt`, `GET /payments/{id}/receipt` |
| **US-21** | Quản lý theo chuẩn `Plan.pdf` | `GET /reports/debt` |
| **US-22** | Quản lý theo chuẩn `Plan.pdf` | `POST /payments/{id}/cancel` |
| **US-23** | Quản lý theo chuẩn `Plan.pdf` | `GET /search` |
| **US-24** | Quản lý theo chuẩn `Plan.pdf` | `GET /reports/revenue` |
| **US-25** | Quản lý theo chuẩn `Plan.pdf` | `GET /reports/revenue` |
| **US-26** | Quản lý theo chuẩn `Plan.pdf` | `GET /reports/revenue`, `GET /reports/debt` |
| **US-27** | Quản lý theo chuẩn `Plan.pdf` | `GET /reports/demographics` |
| **US-28** | Quản lý theo chuẩn `Plan.pdf` | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| **US-29** | Quản lý theo chuẩn `Plan.pdf` | `POST /auth/change-password`, `POST /users/{userId}/reset-password` |
| **US-30** | Quản lý theo chuẩn `Plan.pdf` | `GET /users`, `POST /users`, `GET /users/{userId}`, `PATCH /users/{userId}`, `POST /users/{userId}/lock`, `POST /users/{userId}/unlock`, `POST /users/{userId}/reset-password` |
| **US-31** | Quản lý theo chuẩn `Plan.pdf` | `GET /roles`, `PUT /users/{userId}/role` |
| **US-32** | Quản lý theo chuẩn `Plan.pdf` | `GET /audit-logs` |
| **US-33** | Quản lý theo chuẩn `Plan.pdf` | `GET /portal/household` |
| **US-34** | Quản lý theo chuẩn `Plan.pdf` | `GET /portal/change-requests`, `POST /portal/change-requests`, `GET /change-requests`, `PUT /change-requests/{id}/approve`, `PUT /change-requests/{id}/reject` |
| **US-35** | Quản lý theo chuẩn `Plan.pdf` | `GET /portal/invoices`, `GET /portal/payments` |
| **US-36** | Quản lý theo chuẩn `Plan.pdf` | `GET /vehicles`, `POST /vehicles`, `PATCH /vehicles/{id}`, `POST /vehicles/{id}/unregister` |
| **US-37** | Quản lý theo chuẩn `Plan.pdf` | `POST /billing-periods/{id}/generate` |
| **US-38** | Quản lý theo chuẩn `Plan.pdf` | `GET /utility-readings`, `POST /utility-readings`, `PATCH /utility-readings/{id}` |
| **US-39** | Quản lý theo chuẩn `Plan.pdf` | `GET /service-providers`, `POST /service-providers`, `GET /provider-settlements`, `POST /provider-settlements/{id}/reconcile` |
| **US-40** | Quản lý theo chuẩn `Plan.pdf` | `GET /portal/donation-campaigns`, `GET /donation-campaigns`, `POST /donation-campaigns`, `POST /donation-campaigns/{id}/close` |
| **US-41** | Quản lý theo chuẩn `Plan.pdf` | `GET /donations`, `POST /donations`, `POST /donations/{id}/cancel` |
| **US-42** | Nghiệp vụ logic / Nền tảng | *(Được đảm bảo qua Middleware RBAC / Transaction / Logging)* |
| **US-43** | Quản lý theo chuẩn `Plan.pdf` | `GET /dashboard` |
| **US-44** | Nghiệp vụ logic / Nền tảng | *(Được đảm bảo qua Middleware RBAC / Transaction / Logging)* |
| **US-45** | Quản lý theo chuẩn `Plan.pdf` | `POST /system/backups`, `GET /system/backups` |
| **US-46** | Nghiệp vụ logic / Nền tảng | *(Được đảm bảo qua Middleware RBAC / Transaction / Logging)* |
| **US-47** | Quản lý theo chuẩn `Plan.pdf` | `GET /invoices`, `GET /invoices/{id}` |

---

## CHƯƠNG 5: PHỤ LỤC CÁC SCHEMA DỮ LIỆU CỐT LÕI (DTO MODELS)

Dưới đây là định nghĩa chi tiết các đối tượng dữ liệu cốt lõi được sử dụng xuyên suốt hệ thống:

### Schema: `User`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `username` | `string` |  |  |
| `full_name` | `string` |  |  |
| `email` | `string (email)` |  |  |
| `phone` | `string` |  |  |
| `role` | `'Role'` |  |  |
| `household_id` | `integer (int64)` |  |  |
| `is_active` | `boolean` |  |  |
| `must_change_password` | `boolean` |  |  |
| `locked_until` | `string (date-time)` |  |  |
| `last_login_at` | `string (date-time)` |  |  |

### Schema: `Apartment`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `code` | `string` |  |  |
| `floor` | `integer` |  |  |
| `area_m2` | `number` |  |  |
| `status` | `string` |  |  |
| `note` | `string` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `Household`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `household_code` | `string` |  |  |
| `status` | `string` |  |  |
| `contact_phone` | `string` |  |  |
| `contact_email` | `string` |  |  |
| `note` | `string` |  |  |
| `apartment_id` | `integer (int64)` |  |  |
| `apartment_code` | `string` |  |  |
| `floor` | `integer` |  |  |
| `area_m2` | `number` |  |  |
| `head_resident_id` | `integer (int64)` |  |  |
| `head_name` | `string` |  |  |
| `head_phone` | `string` |  |  |
| `member_count` | `integer` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `Resident`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `household_id` | `integer (int64)` |  |  |
| `full_name` | `string` |  |  |
| `date_of_birth` | `string (date)` |  |  |
| `gender` | `string` |  |  |
| `cccd` | `string` |  | CCCD/CMND 9-12 chữ số |
| `phone` | `string` |  |  |
| `email` | `string` |  |  |
| `relationship_to_head` | `string` |  |  |
| `is_head` | `boolean` |  |  |
| `residence_status` | `string` |  |  |
| `status_effective_date` | `string (date)` |  |  |
| `status_reason` | `string` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `TemporaryStay`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `household_id` | `integer (int64)` |  |  |
| `apartment_id` | `integer (int64)` |  |  |
| `full_name` | `string` |  |  |
| `date_of_birth` | `string (date)` |  |  |
| `gender` | `string` |  |  |
| `cccd` | `string` |  | CCCD/CMND 9-12 chữ số |
| `phone` | `string` |  |  |
| `permanent_address` | `string` |  |  |
| `start_date` | `string (date)` |  |  |
| `end_date` | `string (date)` |  |  |
| `status` | `string` |  |  |
| `note` | `string` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `TemporaryAbsence`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `resident_id` | `integer (int64)` |  |  |
| `start_date` | `string (date)` |  |  |
| `end_date` | `string (date)` |  |  |
| `destination` | `string` |  |  |
| `reason` | `string` |  |  |
| `status` | `string` |  |  |
| `returned_date` | `string (date)` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `FeeType`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `code` | `string` |  |  |
| `name` | `string` |  |  |
| `fee_group` | `'FeeGroup'` |  |  |
| `calc_method` | `'CalcMethod'` |  |  |
| `unit_label` | `string` |  |  |
| `vehicle_type` | `string` |  |  |
| `is_pass_through` | `boolean` |  |  |
| `provider_id` | `integer (int64)` |  |  |
| `cycle` | `string` |  |  |
| `due_day` | `integer` |  |  |
| `status` | `string` |  |  |
| `description` | `string` |  |  |
| `current_unit_price` | `integer (int64)` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `BillingPeriod`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `period_month` | `string (date)` |  |  |
| `name` | `string` |  |  |
| `due_date` | `string (date)` |  |  |
| `status` | `string` |  |  |
| `generated_at` | `string (date-time)` |  |  |
| `closed_at` | `string (date-time)` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `Invoice`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `billing_period_id` | `integer (int64)` |  |  |
| `household_id` | `integer (int64)` |  |  |
| `household_code` | `string` |  |  |
| `apartment_id` | `integer (int64)` |  |  |
| `apartment_area` | `number` |  |  |
| `fee_amount` | `integer (int64)` |  |  |
| `discount_amount` | `integer (int64)` |  |  |
| `previous_debt` | `integer (int64)` |  |  |
| `credit_applied` | `integer (int64)` |  |  |
| `total_due` | `integer (int64)` |  | = fee_amount - discount_amount + previous_debt - credit_applied (AC-17.1) |
| `paid_amount` | `integer (int64)` |  |  |
| `status` | `string` |  |  |
| `created_at` | `string (date-time)` |  |  |
| `updated_at` | `string (date-time)` |  |  |

### Schema: `InvoiceItem`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `invoice_id` | `integer (int64)` |  |  |
| `fee_type_id` | `integer (int64)` |  |  |
| `fee_name` | `string` |  |  |
| `quantity` | `number` |  |  |
| `unit_price` | `integer (int64)` |  |  |
| `gross_amount` | `integer (int64)` |  |  |
| `discount_amount` | `integer (int64)` |  |  |
| `net_amount` | `integer (int64)` |  |  |
| `paid_amount` | `integer (int64)` |  |  |
| `description` | `string` |  |  |

### Schema: `Payment`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `receipt_no` | `string` |  |  |
| `household_id` | `integer (int64)` |  |  |
| `paid_at` | `string (date-time)` |  |  |
| `amount` | `integer (int64)` |  |  |
| `allocated_amount` | `integer (int64)` |  |  |
| `credit_amount` | `integer (int64)` |  |  |
| `method` | `string` |  |  |
| `reference_no` | `string` |  |  |
| `collected_by` | `integer (int64)` |  |  |
| `status` | `string` |  |  |
| `cancel_reason` | `string` |  |  |
| `cancelled_by` | `integer (int64)` |  |  |
| `cancelled_at` | `string (date-time)` |  |  |
| `print_count` | `integer` |  |  |
| `note` | `string` |  |  |
| `allocations` | `'PaymentAllocation'` |  |  |
| `created_at` | `string (date-time)` |  |  |

### Schema: `DonationCampaign`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `code` | `string` |  |  |
| `name` | `string` |  |  |
| `description` | `string` |  |  |
| `start_date` | `string (date)` |  |  |
| `end_date` | `string (date)` |  |  |
| `status` | `string` |  |  |
| `total_collected` | `integer (int64)` |  | Tổng đã vận động (chỉ biên hợp lệ) |
| `donation_count` | `integer` |  |  |
| `created_at` | `string (date-time)` |  |  |

### Schema: `Vehicle`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `household_id` | `integer (int64)` |  |  |
| `plate_number` | `string` |  |  |
| `vehicle_type` | `'VehicleType'` |  |  |
| `brand` | `string` |  |  |
| `color` | `string` |  |  |
| `status` | `string` |  |  |
| `registered_date` | `string (date)` |  |  |
| `unregistered_date` | `string (date)` |  |  |

### Schema: `AuditLog`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `id` | `integer (int64)` |  |  |
| `user_id` | `integer (int64)` |  |  |
| `action` | `string` |  |  |
| `entity_type` | `string` |  |  |
| `entity_id` | `string` |  |  |
| `old_value` | `object` |  |  |
| `new_value` | `object` |  |  |
| `reason` | `string` |  |  |
| `ip_address` | `string` |  |  |
| `user_agent` | `string` |  |  |
| `created_at` | `string (date-time)` |  |  |

### Schema: `Error`
| Tên trường (`snake_case`) | Kiểu dữ liệu | Bắt buộc | Mô tả trường |
| :--- | :---: | :---: | :--- |
| `code` | `string` | ✔ |  |
| `message` | `string` | ✔ |  |
| `details` | `'ErrorDetail'` |  |  |
