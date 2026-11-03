# PRODUCT BACKLOG & SPRINT PLAN \- DỰ ÁN CHUNG CƯ BLUEMOON

**Nhóm thực hiện:** Nhóm 18 (5 thành viên)  
**Đơn vị:** Trường Công nghệ Thông tin và Truyền thông \- ĐHBK Hà Nội (SoICT/HUST)  
**Phiên bản:** 1.0 (Đã chuẩn hóa truy vết & Acceptance Criteria)

---

## 1\. DANH SÁCH THÀNH VIÊN & VAI TRÒ TRONG ĐỘI SCRUM

| STT | Họ và tên | Vai trò Scrum / Kỹ thuật | Module phụ trách chính |
| :---- | :---- | :---- | :---- |
| 1 |  | Product Owner / Scrum Master / Fullstack | Quản lý người dùng, Phân quyền RBAC, Audit Log (`EP-05`, `EP-08`) |
| 2 |  | Business Analyst / Backend Developer | Quản lý hộ gia đình, Nhân khẩu, Tạm trú/Tạm vắng (`EP-01`) |
| 3 |  | System Architect / Backend Lead | Quản lý danh mục khoản thu, Kỳ thu, Ghi nhận thu phí (`EP-02`, `EP-03`) |
| 4 |  | Frontend Lead / UI-UX Designer | Giao diện Quầy thu phí, Biên lai điện tử, Quỹ tự nguyện (`EP-03`, `EP-10`) |
| 5 |  | QA/Tester Lead / Fullstack Developer | Tra cứu đa tiêu chí, Báo cáo thống kê, Cổng cư dân (`EP-04`, `EP-09`) |

&nbsp;

---

## 2\. TỔNG HỢP PRODUCT BACKLOG THEO 3 MODULE CHÍNH (V1.0)

Dưới đây là bảng phân rã Product Backlog đã được ánh xạ từ 8 Epics (thuộc phạm vi v1.0), 31 Features và 47 User Stories vào 3 Module cốt lõi theo chuẩn đề bài:

### MODULE 1: QUẢN LÝ NGƯỜI DÙNG & NỀN TẢNG HỆ THỐNG (`EP-05`, `EP-08`)

| Mã US | Tính năng (Feature) | Nội dung User Story (As a... I want... So that...) | Độ ưu tiên (MoSCoW) | Điểm (Story Points) | Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria) |
| :---- | :---- | :---- | :---: | :---: | :---- |
| **US-28** | `F-05.1` Đăng nhập & Phiên làm việc | **As a** người dùng hệ thống, **I want** đăng nhập bằng tài khoản được cấp, **so that** truy cập đúng chức năng theo vai trò. | Must (M) | 3 | `AC-28.1`: Đăng nhập đúng chuyển tới trang chủ theo role.<br>`AC-28.2`: Sai mật khẩu 5 lần liên tiếp khóa tài khoản 15 phút (`D-05`). |
| **US-29** | `F-05.2` Bảo mật mật khẩu | **As a** người dùng, **I want** đổi mật khẩu cá nhân và bắt buộc đổi trong lần đầu đăng nhập, **so that** bảo mật tài khoản. | Must (M) | 2 | `AC-29.1`: Mật khẩu mới $\geq 8$ ký tự, gồm chữ hoa, thường, số.<br>`AC-29.2`: Lần đầu đăng nhập bắt buộc đổi mật khẩu trước khi thao tác. |
| **US-30** | `F-05.3` Quản lý tài khoản & RBAC | **As a** BQT (Admin), **I want** tạo, khóa tài khoản và gán vai trò (Admin, Kế toán, Thủ quỹ, Cư dân), **so that** kiểm soát truy cập. | Must (M) | 5 | `AC-30.1`: Gán/thu hồi role có hiệu lực ngay ở request tiếp theo.<br>`AC-30.2`: Tự động sinh tài khoản Cư dân mặc định khi tạo Hộ mới (`D-12`). |
| **US-31** | `F-05.4` Nhật ký thao tác (Audit Log) | **As a** BQT (Admin), **I want** xem lịch sử các thao tác nhạy cảm (sửa đơn giá, hủy biên lai, đổi chủ hộ), **so that** truy vết trách nhiệm. | Should (S) | 3 | `AC-31.1`: Lưu rõ Người thực hiện, Thời gian, Hành động, Giá trị cũ $\rightarrow$ Giá trị mới. Không cho phép xóa/sửa Audit Log. |
| **US-44** | `F-08.1` Kiến trúc & Bảo mật | **As a** BQT (Admin), **I want** mật khẩu được băm (bcrypt) và phân quyền chặn truy cập trái phép ở tầng API, **so that** an toàn dữ liệu. | Must (M) | 5 | `AC-44.1`: Mật khẩu lưu dạng bcrypt.<br>`AC-44.2`: Chặn lỗi IDOR khi cư dân đổi ID hộ trên URL (`AC-33.2`). |
| **US-45** | `F-08.2` Sao lưu & Phục hồi | **As a** BQT (Admin), **I want** hệ thống tự động sao lưu CSDL hằng ngày lúc 02:00 sáng, **so that** tránh mất dữ liệu tài chính. | Should (S) | 3 | `AC-45.1`: Lưu bản backup trong 30 ngày, thời gian phục hồi (RTO) $\leq 2$ giờ (`NFR-002`). |

&nbsp;

---

### MODULE 2: QUẢN LÝ HỘ GIA ĐÌNH & NHÂN KHẨU (`EP-01`, `EP-09`)

| Mã US | Tính năng (Feature) | Nội dung User Story | Độ ưu tiên | Story Points | Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria) |
| :---- | :---- | :---- | :---: | :---: | :---- |
| **US-01** | `F-01.1` Hồ sơ Căn hộ & Hộ | **As a** BQT, **I want** thêm mới và cập nhật thông tin căn hộ (Mã căn, Tầng, Diện tích $\text{m}^2$) và Hộ gia đình, **so that** làm cơ sở tính phí. | Must (M) | 5 | `AC-01.1`: Không trùng mã căn hộ; diện tích $> 0\text{ m}^2$.<br>`AC-01.2`: Tách biệt thực thể `Căn hộ` và `Hộ` (`T-01`, `T-02`). |
| **US-02** | `F-01.1` Đổi chủ / Chuyển nhượng | **As a** BQT, **I want** thực hiện nghiệp vụ chuyển nhượng/đổi hộ cư trú tại căn hộ, **so that** giữ nguyên lịch sử thu phí của hộ cũ. | Should (S) | 5 | `AC-02.1`: Bắt buộc tất toán công nợ hộ cũ trước khi gán hộ mới vào căn hộ (`D-06`). |
| **US-04** | `F-01.1` Import dữ liệu Excel | **As a** BQT, **I want** nhập danh sách hộ và nhân khẩu từ file Excel mẫu, **so that** khởi tạo nhanh dữ liệu ban đầu. | Should (S) | 5 | `AC-04.1`: Báo lỗi chi tiết từng dòng sai định dạng (trùng CCCD, diện tích âm) và không lưu nửa vời (Transaction). |
| **US-05** | `F-01.2` Quản lý Nhân khẩu | **As a** BQT, **I want** thêm, sửa thông tin nhân khẩu trong hộ (Họ tên, Ngày sinh, CCCD, Quan hệ với chủ hộ), **so that** quản lý cư trú. | Must (M) | 5 | `AC-05.1`: Mỗi hộ chỉ có duy nhất 1 Chủ hộ đang hoạt động.<br>`AC-05.3`: Cho phép để trống CCCD với trẻ em dưới 14 tuổi. |
| **US-07** | `F-01.3` Biến động nhân khẩu | **As a** BQT, **I want** ghi nhận nhân khẩu chuyển đi, qua đời hoặc tách hộ, **so that** danh sách nhân khẩu luôn chính xác. | Must (M) | 3 | `AC-07.1`: Chuyển trạng thái nhân khẩu sang "Đã chuyển đi" kèm ngày biến động, không xóa vật lý. |
| **US-08** | `F-01.3` Tạm trú & Tạm vắng | **As a** BQT, **I want** đăng ký tạm trú/tạm vắng có thời hạn (từ ngày \- đến ngày), **so that** theo dõi nhân khẩu vãng lai. | Must (M) | 5 | `AC-08.1`: Cảnh báo các trường hợp tạm trú sắp hết hạn trước 15 ngày (`D-04`). |
| **US-10** | `F-01.4` Báo cáo cư trú Công an | **As a** BQT, **I want** xuất báo cáo nhân khẩu, tạm trú/tạm vắng theo mẫu Công an phường (`DOC-03`), **so that** nộp định kỳ. | Should (S) | 3 | `AC-10.1`: Xuất đúng biểu mẫu Excel/PDF trong thời gian $\leq 5$ giây (`NFR-011`). |
| **US-33** | `F-09.1` Cổng tra cứu Cư dân | **As a** Cư dân, **I want** xem thông tin nhân khẩu của hộ mình và lịch sử đóng phí, **so that** tự kiểm tra minh bạch. | Should (S) | 3 | `AC-33.1`: Chỉ xem được dữ liệu của chính hộ mình (`RAW-011`, `WL-028`). |
| **US-34** | `F-09.2` Đề nghị chỉnh sửa thông tin | **As a** Cư dân, **I want** gửi yêu cầu chỉnh sửa thông tin nhân khẩu kèm minh chứng, **so that** BQT phê duyệt cập nhật. | Could (C) | 3 | `AC-34.1`: Trạng thái "Chờ duyệt".<br>`AC-34.2`: BQT Duyệt $\rightarrow$ Cập nhật & ghi Audit Log.<br>`AC-34.3`: BQT Từ chối $\rightarrow$ Bắt buộc nhập lý do. |

&nbsp;

---

### MODULE 3: QUẢN LÝ THU PHÍ, THỐNG KÊ & QUỸ TỰ NGUYỆN (`EP-02`, `EP-03`, `EP-04`, `EP-10`)

| Mã US | Tính năng (Feature) | Nội dung User Story | Độ ưu tiên | Story Points | Tiêu chí nghiệm thu cốt lõi (Acceptance Criteria) |
| :---- | :---- | :---- | :---: | :---: | :---- |
| **US-11** | `F-02.1` Danh mục khoản thu | **As a** Kế toán, **I want** tạo và cấu hình các khoản thu (Bắt buộc theo $\text{m}^2$, cố định theo hộ, hoặc tự nguyện), **so that** áp dụng tính phí. | Must (M) | 5 | `AC-11.1`: Phân loại rõ cách tính; không cho phép xóa vật lý khoản thu đã phát sinh giao dịch (`AC-13.2`). |
| **US-14** | `F-02.2` Lịch sử đơn giá | **As a** Kế toán, **I want** cập nhật đơn giá mới theo ngày hiệu lực, **so that** các kỳ thu cũ không bị nhảy lại số tiền. | Must (M) | 3 | `AC-14.1`: Kỳ thu đã chốt giữ nguyên đơn giá tại thời điểm tạo kỳ. |
| **US-17** | `F-03.1` Tạo kỳ thu tự động | **As a** Kế toán, **I want** khởi tạo kỳ thu hàng tháng và hệ thống tự động tính phí cho toàn bộ 1.000 hộ, **so that** không phải nhân Excel. | Must (M) | 8 | `AC-17.1`: Tổng phải nộp \= $\sum(\text{Phí kỳ này} - \text{Miễn giảm}) + \text{Nợ cũ} - \text{Số dư có}$. Hoàn tất $\leq 10$ giây (`NFR-005`). |
| **US-19** | `F-03.2` Ghi nhận thu phí | **As a** Thủ quỹ / Kế toán, **I want** ghi nhận hộ dân nộp tiền (đủ, một phần, hoặc nộp dư) bằng tiền mặt/chuyển khoản, **so that** gạch nợ. | Must (M) | 8 | `AC-19.1`: Nộp đủ $\rightarrow$ "Đã nộp đủ".<br>`AC-19.2`: Nộp 1 phần $\rightarrow$ Cho phép tích chọn khoản thu gạch nợ.<br>`AC-19.5`: Nộp dư $\rightarrow$ Chuyển phần dư vào "Số dư có" kỳ sau. |
| **US-20** | `F-03.3` In biên lai điện tử | **As a** Thủ quỹ, **I want** xuất và in biên lai thu tiền có mã biên lai tự tăng duy nhất, **so that** giao cho cư dân. | Must (M) | 5 | `AC-20.1`: Đúng mẫu `DOC-02`.<br>`AC-20.2`: In từ lần thứ 2 trở đi tự động đóng dấu chữ **"BẢN SAO"**. |
| **US-22** | `F-03.5` Hủy giao dịch thu sai | **As a** Kế toán trưởng/BQT, **I want** hủy biên lai thu nhầm và nhập lý do bắt buộc, **so that** khôi phục lại công nợ đúng cho hộ. | Should (S) | 3 | `AC-22.1`: Không xóa bản ghi giao dịch, chuyển trạng thái "Đã hủy", cộng trả lại công nợ và ghi Audit Log. |
| **US-23** | `F-04.1` Tìm kiếm đa tiêu chí | **As a** BQT/Kế toán/Thủ quỹ, **I want** tìm kiếm nhanh hộ, nhân khẩu, khoản thu theo tên, mã căn, CCCD, SĐT, **so that** tra cứu tức thì. | Must (M) | 3 | `AC-23.1`: Thời gian phản hồi kết quả tìm kiếm $\leq 1$ giây trên tập 1.000 hộ / 5.000 nhân khẩu (`RAW-009`, `RAW-032`). |
| **US-24** | `F-04.2` Báo cáo thu & Công nợ | **As a** Kế toán, **I want** xem và xuất báo cáo tổng hợp thu phí, danh sách hộ còn nợ theo kỳ ra Excel/PDF, **so that** báo cáo BQT. | Must (M) | 5 | `AC-24.1`: Số liệu khớp 100% với tổng các biên lai hợp lệ trong kỳ. |
| **US-27** | `F-04.5` Dashboard tổng quan | **As a** Trưởng BQT, **I want** xem biểu đồ tỷ lệ hoàn thành thu phí tháng, tổng số hộ nợ, tổng nhân khẩu, **so that** nắm bắt nhanh tình hình. | Should (S) | 3 | `AC-27.1`: Hiển thị trực quan trên màn hình chính của BQT. |
| **US-35** | `F-10.1` Quỹ vận động tự nguyện | **As a** Thủ quỹ, **I want** tạo đợt vận động đóng góp tự nguyện (Quỹ vì người nghèo, Khuyến học...) và ghi nhận số tiền tùy tâm, **so that** quản lý riêng biệt với phí bắt buộc. | Should (S) | 5 | `AC-35.1`: Không tính vào công nợ bắt buộc của hộ; báo cáo công khai tổng quỹ nhưng giữ riêng tư mức đóng chi tiết giữa các cư dân (`WL-026`, `WL-034`). |

&nbsp;

---

## 3\. KẾ HOẠCH PHÂN BỔ 4 SPRINTS (LỘ TRÌNH PHÁT TRIỂN)

* **Sprint 1 (Tuần 4 – Tuần 5): Nền tảng, Phân quyền & Hồ sơ Hộ/Nhân khẩu cơ bản**  
  * **Mục tiêu:** Dựng xong khung dự án (Backend \+ Frontend \+ DB), đăng nhập phân quyền RBAC và CRUD Căn hộ, Hộ gia đình, Nhân khẩu.  
  * **User Stories:** `US-28`, `US-29`, `US-30`, `US-44`, `US-01`, `US-05`.  
* **Sprint 2 (Tuần 6 – Tuần 7): Biến động cư trú & Cấu hình Danh mục khoản thu**  
  * **Mục tiêu:** Hoàn thiện nghiệp vụ Tạm trú/Tạm vắng, Import Excel, Đổi chủ hộ và Thiết lập công thức/đơn giá các khoản phí.  
  * **User Stories:** `US-02`, `US-04`, `US-07`, `US-08`, `US-10`, `US-11`, `US-14`.  
* **Sprint 3 (Tuần 8 – Tuần 9): Tạo kỳ thu, Quầy thu phí, Biên lai & Quỹ tự nguyện (Chốt First UAT \- 30/11)**  
  * **Mục tiêu:** Chạy luồng tính phí tự động cho 1.000 hộ, gạch nợ (đủ/một phần/dư), in biên lai PDF và thu quỹ tự nguyện.  
  * **User Stories:** `US-17`, `US-19`, `US-20`, `US-22`, `US-35`.  
* **Sprint 4 (Tuần 10 – Tuần 11): Tìm kiếm, Thống kê, Dashboard, Cổng cư dân & Sao lưu (Chốt Second UAT \- 15/12)**  
  * **Mục tiêu:** Hoàn thiện tìm kiếm $\le 1\text{s}$, xuất báo cáo công nợ, biểu đồ Dashboard, Cổng tra cứu cư dân và tự động sao lưu.  
  * **User Stories:** `US-23`, `US-24`, `US-27`, `US-31`, `US-33`, `US-34`, `US-45`.