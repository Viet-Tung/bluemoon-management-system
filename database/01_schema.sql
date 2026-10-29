-- =====================================================================
-- BLUEMOON - Phần mềm quản lý & thu phí chung cư  |  Nhóm 18
-- CSDL: PostgreSQL 15+  (khuyến nghị 16)
-- Tham chiếu: US-xx / F-xx / WBS / D-xx / NFR-xx trong Kế hoạch dự án
-- =====================================================================
-- Nguyên tắc thiết kế
--  1. Không xóa vật lý dữ liệu nghiệp vụ (xóa logic / đổi trạng thái).
--  2. Mọi biến động có ngày hiệu lực + lịch sử (nhân khẩu, đơn giá, căn hộ-hộ).
--  3. Snapshot đơn giá, diện tích vào giấy báo -> kỳ đã chốt không bị nhảy số.
--  4. Tiền dùng NUMERIC(14,2); mọi ràng buộc quan trọng đặt ở tầng DB (ACID).
--  5. audit_logs chỉ được INSERT (trigger chặn UPDATE/DELETE/TRUNCATE).
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS btree_gist;  -- exclusion constraint chống chồng ngày
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- tìm kiếm gần đúng theo tên (US-23)

-- ---------------------------------------------------------------------
-- 0. HÀM DÙNG CHUNG
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION forbid_modification() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Bảng % không cho phép thao tác % (chỉ được thêm mới)', TG_TABLE_NAME, TG_OP;
END $$;

CREATE OR REPLACE FUNCTION forbid_delete() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Bảng % không cho phép xóa vật lý; hãy đổi trạng thái (hủy/ngừng áp dụng)', TG_TABLE_NAME;
END $$;

-- =====================================================================
-- MODULE 1: NGƯỜI DÙNG & NỀN TẢNG HỆ THỐNG (EP-05, EP-08)
-- =====================================================================

CREATE TABLE roles (
    id          smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        text NOT NULL UNIQUE,            -- ADMIN, ACCOUNTANT, TREASURER, RESIDENT
    name        text NOT NULL,
    description text
);

CREATE TABLE apartments (                         -- US-01: thực thể Căn hộ (T-01)
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        text NOT NULL UNIQUE,            -- AC-01.1: không trùng mã căn
    floor       smallint NOT NULL CHECK (floor >= 0),
    area_m2     numeric(8,2) NOT NULL CHECK (area_m2 > 0),   -- AC-01.1: diện tích > 0
    status      text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),
    note        text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE households (                         -- US-01: thực thể Hộ gia đình (T-02), tách khỏi Căn hộ
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_code  text NOT NULL UNIQUE,
    status          text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),  -- "ngừng quản lý hộ"
    contact_phone   text,
    contact_email   text,
    note            text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_households_phone ON households (contact_phone) WHERE contact_phone IS NOT NULL;

CREATE TABLE users (                              -- US-28..31
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username             text NOT NULL,
    password_hash        text NOT NULL,                       -- bcrypt (US-44, AC-44.1)
    full_name            text NOT NULL,
    email                text,
    phone                text,
    role_id              smallint NOT NULL REFERENCES roles(id),
    household_id         bigint REFERENCES households(id),    -- chỉ có giá trị với tài khoản Cư dân
    is_active            boolean NOT NULL DEFAULT true,       -- khóa/mở khóa (US-30)
    must_change_password boolean NOT NULL DEFAULT true,       -- AC-29.2
    failed_login_count   smallint NOT NULL DEFAULT 0,         -- AC-28.2: sai 5 lần -> khóa 15 phút
    locked_until         timestamptz,
    last_login_at        timestamptz,
    password_changed_at  timestamptz,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_users_username  ON users (lower(username));
CREATE UNIQUE INDEX ux_users_household ON users (household_id) WHERE household_id IS NOT NULL;  -- mỗi hộ 1 tài khoản (D-12)

CREATE TABLE audit_logs (                         -- US-32 / EP-08: không thể sửa/xóa
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      bigint REFERENCES users(id),     -- NULL = hệ thống / chưa đăng nhập
    action       text NOT NULL,                   -- VD: UPDATE_FEE_RATE, CANCEL_RECEIPT, CHANGE_HEAD, ACCESS_DENIED
    entity_type  text NOT NULL,
    entity_id    text,
    old_value    jsonb,
    new_value    jsonb,
    reason       text,
    ip_address   inet,
    user_agent   text,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_entity  ON audit_logs (entity_type, entity_id);
CREATE INDEX ix_audit_user    ON audit_logs (user_id, created_at DESC);
CREATE INDEX ix_audit_created ON audit_logs (created_at DESC);

CREATE TRIGGER trg_audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION forbid_modification();
CREATE TRIGGER trg_audit_logs_no_truncate
    BEFORE TRUNCATE ON audit_logs
    FOR EACH STATEMENT EXECUTE FUNCTION forbid_modification();

CREATE TABLE backup_jobs (                        -- US-45 / EP-08: Quản lý lịch sử sao lưu CSDL
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    status       text NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED')),
    requested_by bigint REFERENCES users(id),     -- NULL = cronjob tự động (02:00 sáng hàng ngày)
    requested_at timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz,
    size_bytes   bigint CHECK (size_bytes IS NULL OR size_bytes >= 0),
    file_path    text,
    error_message text,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_backup_status    ON backup_jobs (status, requested_at DESC);
CREATE INDEX ix_backup_requested ON backup_jobs (requested_at DESC);

-- Bộ đếm sinh số chứng từ liên tục, không nhảy số (biên lai, phiếu quỹ) - rủi ro NFR-008/010
CREATE TABLE document_counters (
    counter_code text PRIMARY KEY,                -- RECEIPT, DONATION
    last_no      bigint NOT NULL DEFAULT 0
);

CREATE OR REPLACE FUNCTION next_document_no(p_code text) RETURNS bigint
LANGUAGE plpgsql AS $$
DECLARE v bigint;
BEGIN
    -- UPDATE khóa dòng tới hết transaction: các giao dịch đồng thời xếp hàng,
    -- rollback thì số được trả lại -> không bị hổng số.
    UPDATE document_counters SET last_no = last_no + 1
     WHERE counter_code = p_code RETURNING last_no INTO v;
    IF v IS NULL THEN
        RAISE EXCEPTION 'Chưa khai báo bộ đếm %', p_code;
    END IF;
    RETURN v;
END $$;

-- =====================================================================
-- MODULE 2: HỘ GIA ĐÌNH, NHÂN KHẨU & CỔNG CƯ DÂN (EP-01, EP-09.1)
-- =====================================================================

-- Căn hộ <-> Hộ theo thời gian: phục vụ chuyển nhượng giữ lịch sử (US-03)
CREATE TABLE apartment_occupancies (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    apartment_id bigint NOT NULL REFERENCES apartments(id),
    household_id bigint NOT NULL REFERENCES households(id),
    start_date   date NOT NULL,
    end_date     date,                             -- NULL = đang cư trú
    end_reason   text,                             -- chuyển nhượng, chuyển đi...
    created_at   timestamptz NOT NULL DEFAULT now(),
    CHECK (end_date IS NULL OR end_date >= start_date),
    -- một căn hộ không thể có 2 hộ cùng lúc
    EXCLUDE USING gist (apartment_id WITH =, daterange(start_date, end_date, '[]') WITH &&)
);
CREATE UNIQUE INDEX ux_occupancy_household_current ON apartment_occupancies (household_id) WHERE end_date IS NULL;

CREATE TABLE residents (                          -- nhân khẩu thường trú (US-05..07)
    id                    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id          bigint NOT NULL REFERENCES households(id),
    full_name             text NOT NULL,
    date_of_birth         date NOT NULL,
    gender                text NOT NULL CHECK (gender IN ('NAM','NU','KHAC')),
    cccd                  text,                    -- AC-05.3: cho phép trống nếu < 14 tuổi (kiểm ở tầng ứng dụng)
    phone                 text,
    email                 text,
    relationship_to_head  text,                    -- Quan hệ với chủ hộ
    is_head               boolean NOT NULL DEFAULT false,
    residence_status      text NOT NULL DEFAULT 'THUONG_TRU'
                          CHECK (residence_status IN ('THUONG_TRU','TAM_VANG','DA_CHUYEN_DI','DA_QUA_DOI')),
    status_effective_date date,                    -- ngày hiệu lực của trạng thái hiện tại
    status_reason         text,
    is_deleted            boolean NOT NULL DEFAULT false,   -- xóa logic (US-06)
    deleted_at            timestamptz,
    deleted_by            bigint REFERENCES users(id),
    delete_reason         text,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now(),
    CHECK (cccd IS NULL OR cccd ~ '^[0-9]{9,12}$'),
    CHECK (NOT is_deleted OR deleted_at IS NOT NULL)
);
-- AC-05.2: không trùng CCCD trên toàn hệ thống
CREATE UNIQUE INDEX ux_residents_cccd ON residents (cccd) WHERE cccd IS NOT NULL AND NOT is_deleted;
-- AC-05.1: mỗi hộ chỉ có đúng 1 chủ hộ đang hoạt động
CREATE UNIQUE INDEX ux_residents_one_head ON residents (household_id)
    WHERE is_head AND NOT is_deleted AND residence_status IN ('THUONG_TRU','TAM_VANG');
CREATE INDEX ix_residents_household ON residents (household_id) WHERE NOT is_deleted;
CREATE INDEX ix_residents_phone     ON residents (phone) WHERE phone IS NOT NULL AND NOT is_deleted;
CREATE INDEX ix_residents_name_trgm ON residents USING gin (lower(full_name) gin_trgm_ops);   -- US-23

CREATE TABLE temporary_residences (               -- Tạm trú (US-08): người thuê / khách ở dài ngày
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id       bigint NOT NULL REFERENCES households(id),   -- hộ tiếp nhận
    apartment_id       bigint NOT NULL REFERENCES apartments(id),   -- căn hộ tạm trú
    full_name          text NOT NULL,
    date_of_birth      date,
    gender             text CHECK (gender IN ('NAM','NU','KHAC')),
    cccd               text NOT NULL,
    phone              text,
    permanent_address  text NOT NULL,              -- địa chỉ thường trú
    start_date         date NOT NULL,
    end_date           date NOT NULL,
    status             text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','EXPIRED','ENDED')),
    note               text,
    created_by         bigint REFERENCES users(id),
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    CHECK (end_date > start_date)                  -- AC-08.1
);
CREATE INDEX ix_temp_res_expiry ON temporary_residences (end_date) WHERE status = 'ACTIVE';

CREATE TABLE temporary_absences (                 -- Tạm vắng (US-10)
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resident_id   bigint NOT NULL REFERENCES residents(id),
    start_date    date NOT NULL,
    end_date      date NOT NULL,
    destination   text,                            -- nơi đến
    reason        text,
    status        text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ENDED','RETURNED')),
    returned_date date,                            -- cư dân báo về sớm
    created_by    bigint REFERENCES users(id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    CHECK (end_date >= start_date)
);
CREATE INDEX ix_temp_abs_expiry ON temporary_absences (end_date) WHERE status = 'ACTIVE';

CREATE TABLE residency_events (                   -- Lịch sử biến động kèm ngày hiệu lực (US-07, US-11, M1)
    id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resident_id             bigint REFERENCES residents(id),
    temporary_residence_id  bigint REFERENCES temporary_residences(id),
    event_type              text NOT NULL
                            CHECK (event_type IN ('CHUYEN_DEN','CHUYEN_DI','SINH','QUA_DOI','TAM_TRU','TAM_VANG','TRO_VE')),
    effective_date          date NOT NULL,
    reason                  text,
    created_by              bigint REFERENCES users(id),
    created_at              timestamptz NOT NULL DEFAULT now(),
    CHECK ((resident_id IS NOT NULL)::int + (temporary_residence_id IS NOT NULL)::int = 1)
);
CREATE INDEX ix_events_date     ON residency_events (effective_date, event_type);
CREATE INDEX ix_events_resident ON residency_events (resident_id);

CREATE TABLE profile_change_requests (            -- Cổng cư dân: đề nghị chỉnh sửa (US-34)
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id   bigint NOT NULL REFERENCES households(id),
    resident_id    bigint REFERENCES residents(id),
    requested_by   bigint NOT NULL REFERENCES users(id),
    request_type   text NOT NULL CHECK (request_type IN ('UPDATE_RESIDENT','ADD_RESIDENT','UPDATE_HOUSEHOLD')),
    proposed_data  jsonb NOT NULL,                 -- giá trị đề nghị
    evidence_files jsonb,                          -- danh sách ảnh minh chứng
    status         text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','APPROVED','REJECTED')),
    reject_reason  text,
    reviewed_by    bigint REFERENCES users(id),
    reviewed_at    timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now(),
    CHECK (status <> 'REJECTED' OR reject_reason IS NOT NULL),                              -- AC-34.3
    CHECK (status = 'PENDING' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
);
CREATE INDEX ix_pcr_status ON profile_change_requests (status, created_at);

-- =====================================================================
-- MODULE 3A: DANH MỤC KHOẢN THU (EP-02), PHƯƠNG TIỆN (EP-06), ĐIỆN/NƯỚC (EP-07)
-- =====================================================================

CREATE TABLE service_providers (                  -- Nhà cung cấp điện/nước/internet (thu hộ, US-39)
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          text NOT NULL,
    service_type  text NOT NULL CHECK (service_type IN ('ELECTRIC','WATER','INTERNET','OTHER')),
    contact       text,
    is_active     boolean NOT NULL DEFAULT true
);

CREATE TABLE fee_types (                          -- Khoản thu BẮT BUỘC (US-12/13). Quỹ tự nguyện nằm riêng (US-40)
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code             text NOT NULL UNIQUE,
    name             text NOT NULL,
    fee_group        text NOT NULL CHECK (fee_group IN ('MANAGEMENT','PARKING','UTILITY','OTHER')),  -- US-25
    calc_method      text NOT NULL CHECK (calc_method IN ('PER_M2','PER_HOUSEHOLD','PER_PERSON','PER_VEHICLE','METERED')),
    unit_label       text NOT NULL,                -- m2, hộ, người, xe, kWh, m3...
    vehicle_type     text CHECK (vehicle_type IN ('MOTORBIKE','CAR','BICYCLE')),   -- cho khoản PER_VEHICLE
    is_pass_through  boolean NOT NULL DEFAULT false,   -- thu hộ: không gộp vào công nợ phí quản lý (AC-39.1)
    provider_id      bigint REFERENCES service_providers(id),
    cycle            text NOT NULL DEFAULT 'MONTHLY' CHECK (cycle IN ('MONTHLY','QUARTERLY','YEARLY')),
    due_day          smallint CHECK (due_day BETWEEN 1 AND 31),   -- hạn nộp
    status           text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),  -- AC-13.1: chỉ ngừng áp dụng
    description      text,
    created_by       bigint REFERENCES users(id),
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    CHECK (calc_method <> 'PER_VEHICLE' OR vehicle_type IS NOT NULL)
);

CREATE TABLE fee_rates (                          -- Lịch sử đơn giá theo ngày hiệu lực (US-14)
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fee_type_id     bigint NOT NULL REFERENCES fee_types(id),
    unit_price      numeric(14,2) NOT NULL CHECK (unit_price >= 0),
    effective_from  date NOT NULL,
    effective_to    date,                          -- NULL = đang áp dụng
    created_by      bigint REFERENCES users(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    -- không cho hai đơn giá của cùng một khoản chồng ngày hiệu lực
    EXCLUDE USING gist (fee_type_id WITH =, daterange(effective_from, effective_to, '[]') WITH &&)
);

CREATE TABLE fee_exemptions (                     -- Miễn giảm theo hộ + khoản thu + thời hạn (US-15/16)
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id   bigint NOT NULL REFERENCES households(id),
    fee_type_id    bigint NOT NULL REFERENCES fee_types(id),
    discount_type  text NOT NULL CHECK (discount_type IN ('PERCENT','AMOUNT')),
    discount_value numeric(14,2) NOT NULL CHECK (discount_value > 0),
    reason         text NOT NULL,
    decision_no    text,                           -- số quyết định
    approved_by    bigint REFERENCES users(id),    -- AC-16.1
    valid_from     date NOT NULL,
    valid_to       date,
    status         text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED')),
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    CHECK (valid_to IS NULL OR valid_to >= valid_from),
    CHECK (discount_type <> 'PERCENT' OR discount_value <= 100)
);
CREATE INDEX ix_exemptions_lookup ON fee_exemptions (household_id, fee_type_id) WHERE status = 'ACTIVE';

CREATE TABLE vehicles (                           -- US-36
    id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id     bigint NOT NULL REFERENCES households(id),
    plate_number     text NOT NULL,
    vehicle_type     text NOT NULL CHECK (vehicle_type IN ('MOTORBIKE','CAR','BICYCLE')),
    brand            text,
    color            text,
    status           text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','INACTIVE')),
    registered_date  date NOT NULL DEFAULT current_date,
    unregistered_date date,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ux_vehicles_plate_active ON vehicles (upper(replace(plate_number, ' ', ''))) WHERE status = 'ACTIVE';
CREATE INDEX ix_vehicles_household ON vehicles (household_id) WHERE status = 'ACTIVE';

-- =====================================================================
-- MODULE 3B: KỲ THU, GIẤY BÁO, THU TIỀN, BIÊN LAI (EP-03)
-- =====================================================================

CREATE TABLE billing_periods (                    -- Kỳ thu (US-17)
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_month  date NOT NULL UNIQUE CHECK (EXTRACT(day FROM period_month) = 1),   -- ngày 1 của tháng
    name          text NOT NULL,
    due_date      date,
    status        text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','OPEN','CLOSED')),
    generated_at  timestamptz,
    closed_at     timestamptz,
    created_by    bigint REFERENCES users(id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE utility_readings (                   -- Chỉ số điện/nước (US-38)
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id      bigint NOT NULL REFERENCES households(id),
    fee_type_id       bigint NOT NULL REFERENCES fee_types(id),
    billing_period_id bigint NOT NULL REFERENCES billing_periods(id),
    previous_index    numeric(12,2) NOT NULL CHECK (previous_index >= 0),
    current_index     numeric(12,2) NOT NULL,
    consumption       numeric(12,2) GENERATED ALWAYS AS (current_index - previous_index) STORED,
    unit_price        numeric(14,2) NOT NULL CHECK (unit_price >= 0),   -- snapshot biểu giá
    amount            numeric(14,2) NOT NULL CHECK (amount >= 0),
    recorded_by       bigint REFERENCES users(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CHECK (current_index >= previous_index),
    UNIQUE (household_id, fee_type_id, billing_period_id)
);

CREATE TABLE invoices (                           -- Giấy báo nộp phí: 1 hộ / 1 kỳ (US-17, US-47)
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    billing_period_id bigint NOT NULL REFERENCES billing_periods(id),
    household_id      bigint NOT NULL REFERENCES households(id),
    apartment_id      bigint REFERENCES apartments(id),
    apartment_area    numeric(8,2) NOT NULL CHECK (apartment_area > 0),   -- snapshot diện tích
    fee_amount        numeric(14,2) NOT NULL DEFAULT 0 CHECK (fee_amount >= 0),       -- Σ phí kỳ này
    discount_amount   numeric(14,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),  -- Σ miễn giảm
    previous_debt     numeric(14,2) NOT NULL DEFAULT 0 CHECK (previous_debt >= 0),    -- nợ cũ (snapshot lúc tạo kỳ)
    credit_applied    numeric(14,2) NOT NULL DEFAULT 0 CHECK (credit_applied >= 0),   -- số dư có được trừ
    total_due         numeric(14,2) NOT NULL,
    paid_amount       numeric(14,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    status            text NOT NULL DEFAULT 'UNPAID' CHECK (status IN ('UNPAID','PARTIAL','PAID')),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (billing_period_id, household_id),
    -- AC-17.1: Tổng phải nộp = Σ(Phí - Miễn giảm) + Nợ cũ - Số dư có
    CHECK (total_due = fee_amount - discount_amount + previous_debt - credit_applied),
    CHECK (total_due >= 0),
    CHECK (discount_amount <= fee_amount),
    CHECK (credit_applied <= fee_amount - discount_amount + previous_debt)
);
CREATE INDEX ix_invoices_household ON invoices (household_id, billing_period_id DESC);
CREATE INDEX ix_invoices_status    ON invoices (billing_period_id, status);

CREATE TABLE invoice_items (                      -- Chi tiết từng khoản: ghi rõ "diện tích × đơn giá"
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id      bigint NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    fee_type_id     bigint NOT NULL REFERENCES fee_types(id),   -- RESTRICT: khoản đã phát sinh thì không xóa được
    quantity        numeric(14,3) NOT NULL CHECK (quantity >= 0),   -- m2 / số xe / kWh...
    unit_price      numeric(14,2) NOT NULL CHECK (unit_price >= 0), -- snapshot đơn giá (AC-14.1)
    gross_amount    numeric(14,2) NOT NULL CHECK (gross_amount >= 0),
    discount_amount numeric(14,2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    net_amount      numeric(14,2) NOT NULL CHECK (net_amount >= 0),
    paid_amount     numeric(14,2) NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    description     text,                          -- VD: "85,5 m² × 7.000 đ"
    UNIQUE (invoice_id, fee_type_id),
    CHECK (discount_amount <= gross_amount),       -- AC-15.1
    CHECK (net_amount = gross_amount - discount_amount),
    CHECK (paid_amount <= net_amount)              -- phần nộp thừa đi vào số dư có, không nằm ở đây
);
CREATE INDEX ix_invoice_items_fee ON invoice_items (fee_type_id);

CREATE TABLE payments (                           -- Biên lai điện tử (US-19, US-20)
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receipt_no     text NOT NULL UNIQUE,           -- tự sinh bởi trigger bên dưới, tăng dần duy nhất
    household_id   bigint NOT NULL REFERENCES households(id),
    paid_at        timestamptz NOT NULL DEFAULT now(),
    amount         numeric(14,2) NOT NULL CHECK (amount > 0),            -- tổng tiền khách nộp
    allocated_amount numeric(14,2) NOT NULL DEFAULT 0 CHECK (allocated_amount >= 0),  -- phần gạch vào khoản nợ
    credit_amount  numeric(14,2) NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),       -- phần nộp thừa (AC-19.5)
    method         text NOT NULL CHECK (method IN ('CASH','BANK_TRANSFER')),
    reference_no   text,                           -- mã giao dịch ngân hàng
    collected_by   bigint NOT NULL REFERENCES users(id),
    status         text NOT NULL DEFAULT 'VALID' CHECK (status IN ('VALID','CANCELLED')),
    cancel_reason  text,
    cancelled_by   bigint REFERENCES users(id),
    cancelled_at   timestamptz,
    print_count    integer NOT NULL DEFAULT 0,     -- từ lần in thứ 2 -> đóng dấu "BẢN SAO" (AC-20.2)
    idempotency_key text UNIQUE,                   -- Header Idempotency-Key chống bấm đúp tạo 2 biên lai (NFR-008/010, AC-19.1)
    note           text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    CHECK (amount = allocated_amount + credit_amount),
    CHECK (status = 'VALID' OR (cancel_reason IS NOT NULL AND cancelled_by IS NOT NULL AND cancelled_at IS NOT NULL))  -- AC-22.1
);
CREATE INDEX ix_payments_household ON payments (household_id, paid_at DESC);
CREATE INDEX ix_payments_paid_at   ON payments (paid_at) WHERE status = 'VALID';

CREATE OR REPLACE FUNCTION trg_payments_set_receipt_no() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.receipt_no IS NULL THEN
        NEW.receipt_no := 'BL' || lpad(next_document_no('RECEIPT')::text, 8, '0');
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_payments_receipt_no BEFORE INSERT ON payments
    FOR EACH ROW EXECUTE FUNCTION trg_payments_set_receipt_no();
CREATE TRIGGER trg_payments_no_delete BEFORE DELETE ON payments
    FOR EACH ROW EXECUTE FUNCTION forbid_delete();

CREATE TABLE payment_allocations (                -- Gạch nợ theo từng khoản (AC-19.2)
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id      bigint NOT NULL REFERENCES payments(id),
    invoice_item_id bigint NOT NULL REFERENCES invoice_items(id),
    amount          numeric(14,2) NOT NULL CHECK (amount > 0),
    UNIQUE (payment_id, invoice_item_id)
);
CREATE INDEX ix_alloc_item ON payment_allocations (invoice_item_id);

CREATE TABLE household_credit_ledger (            -- Sổ "số dư có" (credit) của hộ
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id bigint NOT NULL REFERENCES households(id),
    entry_type   text NOT NULL CHECK (entry_type IN ('OVERPAYMENT','APPLIED','REVERSAL','ADJUSTMENT')),
    amount       numeric(14,2) NOT NULL CHECK (amount <> 0),   -- dương = tăng dư, âm = trừ dư
    payment_id   bigint REFERENCES payments(id),
    invoice_id   bigint REFERENCES invoices(id),
    note         text,
    created_by   bigint REFERENCES users(id),
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_credit_household ON household_credit_ledger (household_id);

CREATE TABLE provider_settlements (               -- Đối soát thu hộ với nhà cung cấp (US-39)
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provider_id       bigint NOT NULL REFERENCES service_providers(id),
    billing_period_id bigint NOT NULL REFERENCES billing_periods(id),
    total_collected   numeric(14,2) NOT NULL DEFAULT 0,
    amount_remitted   numeric(14,2) NOT NULL DEFAULT 0,
    remitted_date     date,
    status            text NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RECONCILED')),
    note              text,
    created_by        bigint REFERENCES users(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider_id, billing_period_id)
);

-- =====================================================================
-- MODULE 3C: QUỸ VẬN ĐỘNG TỰ NGUYỆN (EP-10)  -- tách hẳn khỏi công nợ (AC-40.1)
-- =====================================================================

CREATE TABLE donation_campaigns (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        text NOT NULL UNIQUE,
    name        text NOT NULL,                     -- Quỹ Vì người nghèo, Khuyến học...
    description text,
    start_date  date NOT NULL,
    end_date    date,
    status      text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('DRAFT','ACTIVE','CLOSED')),
    created_by  bigint REFERENCES users(id),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE donations (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id    bigint NOT NULL REFERENCES donation_campaigns(id),
    household_id   bigint NOT NULL REFERENCES households(id),
    voucher_no     text NOT NULL UNIQUE,           -- số phiếu xác nhận, tự sinh
    amount         numeric(14,2) NOT NULL CHECK (amount > 0),
    donated_at     timestamptz NOT NULL DEFAULT now(),
    method         text NOT NULL CHECK (method IN ('CASH','BANK_TRANSFER')),
    collected_by   bigint NOT NULL REFERENCES users(id),
    status         text NOT NULL DEFAULT 'VALID' CHECK (status IN ('VALID','CANCELLED')),
    cancel_reason  text,
    note           text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    CHECK (status = 'VALID' OR cancel_reason IS NOT NULL)
);
-- LƯU Ý riêng tư (US-41, WL-026): tầng API KHÔNG trả bảng này cho vai trò RESIDENT;
-- cư dân chỉ thấy tổng đợt vận động, không thấy số tiền của hộ khác.
CREATE INDEX ix_donations_campaign  ON donations (campaign_id) WHERE status = 'VALID';
CREATE INDEX ix_donations_household ON donations (household_id);

CREATE OR REPLACE FUNCTION trg_donations_set_voucher_no() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.voucher_no IS NULL THEN
        NEW.voucher_no := 'QT' || lpad(next_document_no('DONATION')::text, 8, '0');
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_donations_voucher_no BEFORE INSERT ON donations
    FOR EACH ROW EXECUTE FUNCTION trg_donations_set_voucher_no();
CREATE TRIGGER trg_donations_no_delete BEFORE DELETE ON donations
    FOR EACH ROW EXECUTE FUNCTION forbid_delete();

-- =====================================================================
-- TỰ ĐỘNG CẬP NHẬT updated_at CHO MỌI BẢNG CÓ CỘT NÀY
-- =====================================================================
DO $$
DECLARE r record;
BEGIN
    FOR r IN SELECT table_name FROM information_schema.tables
              WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                AND table_name IN (
                    SELECT table_name FROM information_schema.columns
                     WHERE table_schema = 'public' AND column_name = 'updated_at'
                )
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%1$s_updated_at ON %1$I;
                        CREATE TRIGGER trg_%1$s_updated_at BEFORE UPDATE ON %1$I
                        FOR EACH ROW EXECUTE FUNCTION set_updated_at()', r.table_name);
    END LOOP;
END $$;

-- =====================================================================
-- VIEW PHỤC VỤ TRA CỨU & BÁO CÁO
-- =====================================================================

-- Tổng quan hộ: căn hộ hiện tại, chủ hộ, số thành viên (US-18, US-23, US-33)
CREATE VIEW v_household_overview AS
SELECT h.id AS household_id, h.household_code, h.status,
       a.id AS apartment_id, a.code AS apartment_code, a.floor, a.area_m2,
       hd.id AS head_resident_id, hd.full_name AS head_name, hd.phone AS head_phone,
       (SELECT count(*) FROM residents r
         WHERE r.household_id = h.id AND NOT r.is_deleted
           AND r.residence_status IN ('THUONG_TRU','TAM_VANG')) AS member_count
FROM households h
LEFT JOIN apartment_occupancies o ON o.household_id = h.id AND o.end_date IS NULL
LEFT JOIN apartments a            ON a.id = o.apartment_id
LEFT JOIN residents hd            ON hd.household_id = h.id AND hd.is_head AND NOT hd.is_deleted
                                 AND hd.residence_status IN ('THUONG_TRU','TAM_VANG');

-- Công nợ hiện tại của từng hộ (US-21, US-02, US-35)
CREATE VIEW v_household_debt AS
SELECT i.household_id,
       SUM(ii.net_amount - ii.paid_amount) AS total_debt,
       COUNT(DISTINCT i.billing_period_id) FILTER (WHERE ii.net_amount > ii.paid_amount) AS unpaid_periods
FROM invoices i
JOIN invoice_items ii ON ii.invoice_id = i.id
GROUP BY i.household_id
HAVING SUM(ii.net_amount - ii.paid_amount) > 0;

-- Số dư có hiện tại của hộ
CREATE VIEW v_household_credit AS
SELECT household_id, SUM(amount) AS credit_balance
FROM household_credit_ledger
GROUP BY household_id;

-- Tạm trú / tạm vắng còn <= 15 ngày là hết hạn (US-09, D-04)
CREATE VIEW v_expiring_stays AS
SELECT 'TAM_TRU'::text AS stay_type, t.id AS record_id, t.household_id, t.full_name,
       t.end_date, (t.end_date - current_date) AS days_left
FROM temporary_residences t
WHERE t.status = 'ACTIVE' AND t.end_date - current_date <= 15
UNION ALL
SELECT 'TAM_VANG', a.id, r.household_id, r.full_name,
       a.end_date, (a.end_date - current_date)
FROM temporary_absences a
JOIN residents r ON r.id = a.resident_id
WHERE a.status = 'ACTIVE' AND a.end_date - current_date <= 15;

-- Phải thu / thực thu theo kỳ & khoản (US-24, US-25); chỉ tính biên lai hợp lệ
CREATE VIEW v_collection_by_period_fee AS
SELECT bp.id AS billing_period_id, bp.period_month,
       ft.id AS fee_type_id, ft.code AS fee_code, ft.name AS fee_name, ft.fee_group,
       SUM(ii.net_amount)                    AS receivable,
       SUM(COALESCE(pd.amount, 0))           AS collected
FROM invoice_items ii
JOIN invoices i         ON i.id = ii.invoice_id
JOIN billing_periods bp ON bp.id = i.billing_period_id
JOIN fee_types ft       ON ft.id = ii.fee_type_id
LEFT JOIN LATERAL (
    SELECT SUM(pa.amount) AS amount
    FROM payment_allocations pa
    JOIN payments p ON p.id = pa.payment_id AND p.status = 'VALID'
    WHERE pa.invoice_item_id = ii.id
) pd ON true
GROUP BY bp.id, bp.period_month, ft.id, ft.code, ft.name, ft.fee_group;

-- =====================================================================
-- DỮ LIỆU CẤU HÌNH BAN ĐẦU BẮT BUỘC (SYSTEM SEED METADATA)
-- =====================================================================

-- 1. Bốn vai trò chuẩn theo tài liệu kiến trúc & OpenAPI (US-30, US-31)
INSERT INTO roles (code, name, description) VALUES
    ('ADMIN', 'Ban Quản Trị / Quản Trị Viên', 'Toàn quyền quản trị hệ thống, phê duyệt nhân khẩu, xem dashboard'),
    ('ACCOUNTANT', 'Kế toán', 'Cấu hình danh mục phí, đơn giá, tạo kỳ thu, đối soát dịch vụ, báo cáo'),
    ('TREASURER', 'Thủ quỹ', 'Thu tiền mặt/chuyển khoản tại quầy, in biên lai, quản lý đợt vận động tự nguyện'),
    ('RESIDENT', 'Cư dân', 'Xem thông tin hộ, lịch sử hóa đơn/thanh toán, gửi đề nghị sửa đổi thông tin')
ON CONFLICT (code) DO NOTHING;

-- 2. Bộ đếm chứng từ khởi tạo bắt buộc cho hàm next_document_no() (US-19, US-41)
INSERT INTO document_counters (counter_code, last_no) VALUES
    ('RECEIPT', 0),
    ('DONATION', 0)
ON CONFLICT (counter_code) DO NOTHING;
