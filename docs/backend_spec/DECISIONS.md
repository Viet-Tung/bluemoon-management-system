# Nhật ký Quyết định Kiến trúc & Nghiệp vụ Backend (ADR — Append-Only)

> **Quy tắc bất biến:** Chỉ **nối thêm** mục `ADR-xxx` mới ở cuối file; tuyệt đối không sửa nội dung các quyết định cũ đã chốt. Khi thay đổi quyết định, ghi một mục mới ghi rõ `Thay thế: ADR-xxx`.

---

## ADR-001 — Ràng buộc CCCD khi cư dân bước qua tuổi 14 (`PATCH /residents/{id}`)
- **Ngữ cảnh:** Quy định yêu cầu cư dân $\ge 14$ tuổi phải có số CCCD. DB không đặt `CHECK` động theo thời gian (`CURRENT_DATE - date_of_birth`), nên cư dân tạo lúc $\le 13$ tuổi (`cccd = NULL`) đến sinh nhật 14 tuổi sẽ trở thành "chờ bổ sung CCCD".
- **Quyết định:** Tầng ứng dụng chỉ bắt buộc CCCD khi tạo mới (`POST`) hoặc khi `PATCH /residents/{id}` có truyền trường `date_of_birth` hoặc `cccd` ([residents.py](../../backend/app/routers/residents.py)). Sửa SĐT/quan hệ không bị chặn.
- **Hệ quả:** Giữ tuân thủ quy định lúc nhập/sửa nhân thân mà không khóa thao tác vận hành thường ngày.

## ADR-002 — Mốc hiệu lực đơn giá & miễn giảm theo đầu tháng (`period_month`)
- **Ngữ cảnh:** `fee_rates` và `fee_exemptions` lưu khoảng ngày `effective_from`/`to` và `valid_from`/`to`, nhưng hóa đơn v1.0 phát hành theo kỳ tháng (`YYYY-MM-01`).
- **Quyết định:** `generate_invoices` ([billing.py](../../backend/app/routers/billing.py)) tra cứu đơn giá và miễn giảm tại đúng mốc `period.period_month` (`YYYY-MM-01`). Không hỗ trợ tách tỷ lệ giữa tháng (pro-rata) trong v1.0.
- **Quy ước vận hành:** Biểu giá và chính sách miễn giảm mới nên đặt hiệu lực từ ngày `01` của tháng áp dụng.

## ADR-003 — Hỗ trợ nhiều khoản thu `PER_VEHICLE` cùng `vehicle_type`
- **Ngữ cảnh:** `fee_types` cho phép tạo nhiều khoản phí `ACTIVE` cùng `calc_method = 'PER_VEHICLE'` và cùng `vehicle_type`.
- **Quyết định:** Đổi cấu trúc gom trong `generate_invoices` từ 1-1 sang `Dict[str, List[FeeType]]` để tính đầy đủ mọi khoản phí gửi xe `ACTIVE` có đơn giá hiệu lực, không ghi đè ngầm.

## ADR-004 — Giới hạn mô hình biểu giá phẳng của v1.0
- **Ngữ cảnh:** Bảng `fee_rates` chỉ có 1 cột scalar `unit_price` theo `(fee_type_id, effective_from, effective_to)`.
- **Quyết định:** Chấp nhận giới hạn v1.0: không hỗ trợ đơn giá bậc thang, đơn giá theo hạng căn hộ/tầng, hoặc đơn giá lũy tiến theo số lượng xe (xe thứ 1 vs xe thứ 2).

## ADR-005 — Phân tách quyền `RESIDENT` qua cụm `/portal/*`
- **Ngữ cảnh:** Toàn bộ API Sprint 1–2 (`/households`, `/apartments`, `/residents`, `/vehicles`, `/fee-types`, `/billing-periods`) thuộc phạm vi quản trị back-office (`ADMIN`, `ACCOUNTANT`, `TREASURER`) nhằm tránh lộ dữ liệu giữa các hộ (IDOR).
- **Quyết định:** Giữ back-office routes chặn `RESIDENT` (`403`). Quyền đọc của cư dân triển khai riêng ở cụm `/portal/*` (Sprint 3–4).
- **Đề xuất chờ chốt với team trước Sprint 3–4:** Bổ sung mảng `vehicles` vào `GET /portal/household` và mở quyền `RESIDENT` đọc `GET /fee-types` để lấp 2 khoảng trống trong OpenAPI v1.0.

## ADR-006 — Cơ chế tri thức 3 tầng (Code-first + ADR + Index ngắn)
- **Ngữ cảnh:** Spec `.md` chi tiết cho từng US dễ bị lệch sau mỗi vòng fix bug và tốn công bảo trì.
- **Quyết định:** Áp dụng tri thức 3 tầng: (1) *Cái gì* giữ trong FastAPI/OpenAPI + `pytest` (`test_contract_drift.py`, docstring hàm & test); (2) *Tại sao* lưu append-only tại `DECISIONS.md`; (3) Điều hướng lưu gọn tại `README.md` (`< 80` dòng). Đóng băng [sprint_1/](./sprint_1/README.md) làm tài liệu tham khảo lịch sử.

## ADR-007 — Loại bỏ thư mục spec cũ `docs/backend_spec/sprint_1/` khỏi working tree
- **Thay thế một phần:** `ADR-006` (phần giữ `sprint_1/` làm archive tại chỗ).
- **Ngữ cảnh:** 15 file spec chi tiết Sprint 1 (~194 KB) trùng lặp với [openapi.yaml](../openapi.yaml) và gây nhiễu tìm kiếm cho cả dev lẫn AI sau các đợt sửa lỗi.
- **Quyết định:** Xóa `docs/backend_spec/sprint_1/` khỏi working tree (lưu toàn vẹn trong Git history); thư mục `docs/backend_spec/` chỉ giữ lại [README.md](./README.md) và [DECISIONS.md](./DECISIONS.md).
