-- =====================================================================
-- DỮ LIỆU MẪU DEMO - Hệ thống Quản lý Chung cư BlueMoon
-- Chạy sau: 01_schema.sql → seed_sprint1_test.sql → seed_sprint2_test.sql
-- Mật khẩu tất cả tài khoản: BlueMoon@2026
-- Quy mô: 20 căn hộ, 15 hộ gia đình, ~40 nhân khẩu, đầy đủ nghiệp vụ
-- =====================================================================

BEGIN;

-- =====================================================================
-- 1. CĂN HỘ BỔ SUNG (20 căn, 5 tòa A-E, tầng 3-20)
-- =====================================================================
INSERT INTO apartments (code, floor, area_m2, status, note) VALUES
    ('A0301',  3, 55.00, 'ACTIVE', 'Căn studio 1 phòng ngủ tầng 3'),
    ('A0702',  7, 68.50, 'ACTIVE', 'Căn 2PN hướng Đông'),
    ('A1001', 10, 72.00, 'ACTIVE', 'Căn 2PN ban công rộng'),
    ('A1503', 15, 85.00, 'ACTIVE', 'Căn 3PN hướng Nam'),
    ('B0301',  3, 45.00, 'ACTIVE', 'Căn studio nhỏ tầng 3'),
    ('B0602',  6, 62.00, 'ACTIVE', 'Căn 2PN tầng 6'),
    ('B1101', 11, 78.50, 'ACTIVE', 'Căn 2PN + 1 phòng làm việc'),
    ('B1402', 14, 92.00, 'ACTIVE', 'Căn 3PN penthouse nhỏ'),
    ('C0401',  4, 50.00, 'ACTIVE', 'Căn 1PN tầng 4'),
    ('C0803',  8, 75.00, 'ACTIVE', 'Căn 2PN + 1 tiện ích'),
    ('C1201', 12, 110.00, 'ACTIVE', 'Căn duplex tầng 12'),
    ('C1601', 16, 65.00, 'ACTIVE', 'Căn 2PN view hồ'),
    ('D0501',  5, 58.00, 'ACTIVE', 'Căn 1PN + 1 phòng ngủ nhỏ'),
    ('D0802',  8, 82.00, 'ACTIVE', 'Căn 3PN tầng 8'),
    ('D1201', 12, 95.00, 'ACTIVE', 'Căn 3PN ban công kép'),
    ('E0301',  3, 48.00, 'ACTIVE', 'Căn studio tầng 3 tòa E'),
    ('E0602',  6, 70.00, 'ACTIVE', 'Căn 2PN tầng 6 tòa E'),
    ('E1001', 10, 88.00, 'ACTIVE', 'Căn 3PN tầng 10 tòa E'),
    ('E1501', 15, 120.00, 'ACTIVE', 'Căn penthouse tầng 15 tòa E'),
    ('E2001', 20, 150.00, 'INACTIVE', 'Căn penthouse VIP - đang sửa chữa')
ON CONFLICT (code) DO NOTHING;

-- =====================================================================
-- 2. HỘ GIA ĐÌNH BỔ SUNG (15 hộ mới)
-- =====================================================================
INSERT INTO households (household_code, status, contact_phone, contact_email, note) VALUES
    ('H-A0301-01', 'ACTIVE', '0971111001', 'hoa0301@bluemoon.local',   'Hộ gia đình căn A0301 - Studio'),
    ('H-A0702-01', 'ACTIVE', '0971111002', 'long0702@bluemoon.local',  'Hộ gia đình căn A0702'),
    ('H-A1001-01', 'ACTIVE', '0971111003', 'mai1001@bluemoon.local',   'Hộ gia đình căn A1001'),
    ('H-A1503-01', 'ACTIVE', '0971111004', 'duc1503@bluemoon.local',   'Hộ gia đình căn A1503 - 3PN'),
    ('H-B0301-01', 'ACTIVE', '0971111005', 'thao0301b@bluemoon.local', 'Hộ gia đình căn B0301'),
    ('H-B0602-01', 'ACTIVE', '0971111006', 'minh0602@bluemoon.local',  'Hộ gia đình căn B0602'),
    ('H-B1101-01', 'ACTIVE', '0971111007', 'ha1101@bluemoon.local',    'Hộ gia đình căn B1101'),
    ('H-B1402-01', 'ACTIVE', '0971111008', 'khoa1402@bluemoon.local',  'Hộ gia đình căn B1402 - penthouse'),
    ('H-C0401-01', 'ACTIVE', '0971111009', 'lan0401@bluemoon.local',   'Hộ gia đình căn C0401'),
    ('H-C0803-01', 'ACTIVE', '0971111010', 'hung0803@bluemoon.local',  'Hộ gia đình căn C0803'),
    ('H-C1201-01', 'ACTIVE', '0971111011', 'nam1201@bluemoon.local',   'Hộ gia đình căn C1201 - duplex'),
    ('H-D0501-01', 'ACTIVE', '0971111012', 'vy0501@bluemoon.local',    'Hộ gia đình căn D0501'),
    ('H-D0802-01', 'ACTIVE', '0971111013', 'son0802@bluemoon.local',   'Hộ gia đình căn D0802'),
    ('H-E0602-01', 'ACTIVE', '0971111014', 'thu0602e@bluemoon.local',  'Hộ gia đình căn E0602'),
    ('H-E1001-01', 'ACTIVE', '0971111015', 'quang1001@bluemoon.local', 'Hộ gia đình căn E1001')
ON CONFLICT (household_code) DO NOTHING;

-- =====================================================================
-- 3. GÁN CƯ TRÚ (apartment_occupancies)
-- =====================================================================
INSERT INTO apartment_occupancies (apartment_id, household_id, start_date, end_date)
SELECT a.id, h.id, start_dt::date, NULL
FROM (VALUES
    ('A0301', 'H-A0301-01', '2025-06-01'),
    ('A0702', 'H-A0702-01', '2025-03-15'),
    ('A1001', 'H-A1001-01', '2025-01-01'),
    ('A1503', 'H-A1503-01', '2024-09-01'),
    ('B0301', 'H-B0301-01', '2025-07-01'),
    ('B0602', 'H-B0602-01', '2025-04-01'),
    ('B1101', 'H-B1101-01', '2024-12-15'),
    ('B1402', 'H-B1402-01', '2024-06-01'),
    ('C0401', 'H-C0401-01', '2025-08-01'),
    ('C0803', 'H-C0803-01', '2025-02-01'),
    ('C1201', 'H-C1201-01', '2024-10-01'),
    ('D0501', 'H-D0501-01', '2025-05-01'),
    ('D0802', 'H-D0802-01', '2025-01-15'),
    ('E0602', 'H-E0602-01', '2025-06-15'),
    ('E1001', 'H-E1001-01', '2024-11-01')
) AS t(apt_code, hh_code, start_dt)
JOIN apartments a ON a.code = t.apt_code
JOIN households h ON h.household_code = t.hh_code
WHERE NOT EXISTS (
    SELECT 1 FROM apartment_occupancies ao
    WHERE ao.household_id = h.id AND ao.end_date IS NULL
);

-- =====================================================================
-- 4. NHÂN KHẨU (~40 người, đa dạng quan hệ, giới tính, tuổi)
-- =====================================================================

-- H-A0301-01: Chị Hoa sống một mình (studio)
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trần Thị Hoa', '1995-03-20'::date, 'NU', '001195003001', '0971111001', 'hoa0301@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A0301-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001195003001' AND NOT r.is_deleted);

-- H-A0702-01: Vợ chồng Long + 1 con nhỏ
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Nguyễn Hoàng Long', '1988-11-05'::date, 'NAM', '001188007001', '0971111002', 'long0702@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A0702-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001188007001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Phạm Thị Lan Anh', '1990-05-12'::date, 'NU', '001190007002', '0971111022', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A0702-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001190007002' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Nguyễn Hoàng Minh', '2020-08-15'::date, 'NAM', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A0702-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Nguyễn Hoàng Minh' AND NOT r.is_deleted);

-- H-A1001-01: Chị Mai + mẹ già
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lê Thị Mai', '1985-12-10'::date, 'NU', '001185010001', '0971111003', 'mai1001@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A1001-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001185010001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Nguyễn Thị Thanh', '1958-02-28'::date, 'NU', '001158010002', '0971111033', NULL, 'Mẹ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A1001-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001158010002' AND NOT r.is_deleted);

-- H-A1503-01: Gia đình anh Đức - 4 người (vợ chồng + 2 con)
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Vũ Mạnh Đức', '1982-07-20'::date, 'NAM', '001182015001', '0971111004', 'duc1503@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A1503-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001182015001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trần Thanh Hằng', '1984-04-15'::date, 'NU', '001184015002', '0971111044', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A1503-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001184015002' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Vũ Thanh Tùng', '2010-09-01'::date, 'NAM', '001210015003', NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A1503-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Vũ Thanh Tùng' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Vũ Phương Linh', '2015-11-22'::date, 'NU', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-A1503-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Vũ Phương Linh' AND NOT r.is_deleted);

-- H-B0301-01: Chị Thảo - người ở một mình
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Đinh Phương Thảo', '1993-06-18'::date, 'NU', '001193003005', '0971111005', 'thao0301b@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B0301-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001193003005' AND NOT r.is_deleted);

-- H-B0602-01: Vợ chồng Minh
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Hoàng Văn Minh', '1987-01-25'::date, 'NAM', '001187006001', '0971111006', 'minh0602@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B0602-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001187006001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Nguyễn Thị Hạnh', '1989-10-08'::date, 'NU', '001189006002', '0971111066', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B0602-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001189006002' AND NOT r.is_deleted);

-- H-B1101-01: Anh Hà + em trai
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Bùi Quang Hà', '1991-03-30'::date, 'NAM', '001191011001', '0971111007', 'ha1101@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B1101-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001191011001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Bùi Quang Huy', '1996-08-14'::date, 'NAM', '001196011002', '0971111077', NULL, 'Em trai', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B1101-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001196011002' AND NOT r.is_deleted);

-- H-B1402-01: Gia đình anh Khoa - 5 người (vợ chồng + 2 con + bà ngoại)
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trương Minh Khoa', '1980-05-10'::date, 'NAM', '001180014001', '0971111008', 'khoa1402@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B1402-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001180014001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lý Thị Kim Ngân', '1983-09-25'::date, 'NU', '001183014002', '0971111088', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B1402-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001183014002' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trương Minh Phúc', '2008-12-01'::date, 'NAM', '001208014003', NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B1402-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Trương Minh Phúc' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trương Thị Bảo Ngọc', '2017-03-14'::date, 'NU', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B1402-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Trương Thị Bảo Ngọc' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lý Thị Xuân', '1955-01-20'::date, 'NU', '001155014005', '0971111089', NULL, 'Mẹ vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-B1402-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001155014005' AND NOT r.is_deleted);

-- H-C0401-01: Chị Lan + con gái
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Phạm Thị Lan', '1992-02-14'::date, 'NU', '001192004001', '0971111009', 'lan0401@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-C0401-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001192004001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Phạm Khánh Linh', '2019-07-20'::date, 'NU', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-C0401-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Phạm Khánh Linh' AND NOT r.is_deleted);

-- H-C0803-01: Anh Hùng + vợ
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Ngô Quốc Hùng', '1986-08-08'::date, 'NAM', '001186008001', '0971111010', 'hung0803@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-C0803-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001186008001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Đặng Thị Thu Hà', '1988-12-25'::date, 'NU', '001188008002', '0971111100', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-C0803-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001188008002' AND NOT r.is_deleted);

-- H-C1201-01: Gia đình anh Nam - duplex - 3 người
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trần Thanh Nam', '1979-04-02'::date, 'NAM', '001179012001', '0971111011', 'nam1201@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-C1201-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001179012001' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lê Thị Phương', '1981-06-18'::date, 'NU', '001181012002', '0971111111', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-C1201-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001181012002' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trần Phương Anh', '2006-01-10'::date, 'NU', '001206012003', NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-C1201-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001206012003' AND NOT r.is_deleted);

-- H-D0501-01: Chị Vy sống một mình
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Nguyễn Thảo Vy', '1997-09-15'::date, 'NU', '001197005001', '0971111012', 'vy0501@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-D0501-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001197005001' AND NOT r.is_deleted);

-- H-D0802-01: Anh Sơn + vợ + 1 con
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lê Văn Sơn', '1984-10-30'::date, 'NAM', '001184008003', '0971111013', 'son0802@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-D0802-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001184008003' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trần Thị Huyền', '1986-03-07'::date, 'NU', '001186008004', '0971111130', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-D0802-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001186008004' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lê Bảo An', '2021-04-18'::date, 'NAM', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-D0802-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Lê Bảo An' AND NOT r.is_deleted);

-- H-E0602-01: Chị Thu + chồng
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Đỗ Thị Thu', '1991-11-11'::date, 'NU', '001191006003', '0971111014', 'thu0602e@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-E0602-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001191006003' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Phạm Quốc Việt', '1989-07-04'::date, 'NAM', '001189006004', '0971111140', NULL, 'Chồng', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-E0602-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001189006004' AND NOT r.is_deleted);

-- H-E1001-01: Anh Quang + vợ + 2 con + bố
INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lý Minh Quang', '1983-02-15'::date, 'NAM', '001183010003', '0971111015', 'quang1001@bluemoon.local', 'Chủ hộ', true, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-E1001-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001183010003' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Trần Thị Hồng Nhung', '1985-06-30'::date, 'NU', '001185010004', '0971111150', NULL, 'Vợ', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-E1001-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001185010004' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lý Minh Khôi', '2012-11-20'::date, 'NAM', '001212010005', NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-E1001-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Lý Minh Khôi' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lý Ngọc Hân', '2018-05-05'::date, 'NU', NULL, NULL, NULL, 'Con', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-E1001-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.household_id = h.id AND r.full_name = 'Lý Ngọc Hân' AND NOT r.is_deleted);

INSERT INTO residents (household_id, full_name, date_of_birth, gender, cccd, phone, email, relationship_to_head, is_head, residence_status)
SELECT h.id, 'Lý Văn Thành', '1955-12-01'::date, 'NAM', '001155010006', '0971111151', NULL, 'Bố', false, 'THUONG_TRU'
FROM households h WHERE h.household_code = 'H-E1001-01'
AND NOT EXISTS (SELECT 1 FROM residents r WHERE r.cccd = '001155010006' AND NOT r.is_deleted);

-- =====================================================================
-- 5. TÀI KHOẢN CƯ DÂN BỔ SUNG (thêm 5 tài khoản cư dân mới)
-- =====================================================================
-- Password hash (Bcrypt rounds=12): BlueMoon@2026
INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT 'cudan_a0301', '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
       'Trần Thị Hoa', 'hoa0301@bluemoon.local', '0971111001', r.id, h.id, true, false
FROM roles r JOIN households h ON h.household_code = 'H-A0301-01' WHERE r.code = 'RESIDENT'
ON CONFLICT (lower(username)) DO NOTHING;

INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT 'cudan_a1503', '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
       'Vũ Mạnh Đức', 'duc1503@bluemoon.local', '0971111004', r.id, h.id, true, false
FROM roles r JOIN households h ON h.household_code = 'H-A1503-01' WHERE r.code = 'RESIDENT'
ON CONFLICT (lower(username)) DO NOTHING;

INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT 'cudan_b1402', '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
       'Trương Minh Khoa', 'khoa1402@bluemoon.local', '0971111008', r.id, h.id, true, false
FROM roles r JOIN households h ON h.household_code = 'H-B1402-01' WHERE r.code = 'RESIDENT'
ON CONFLICT (lower(username)) DO NOTHING;

INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT 'cudan_c1201', '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
       'Trần Thanh Nam', 'nam1201@bluemoon.local', '0971111011', r.id, h.id, true, false
FROM roles r JOIN households h ON h.household_code = 'H-C1201-01' WHERE r.code = 'RESIDENT'
ON CONFLICT (lower(username)) DO NOTHING;

INSERT INTO users (username, password_hash, full_name, email, phone, role_id, household_id, is_active, must_change_password)
SELECT 'cudan_e1001', '$2b$12$8ti3VaXTf/crPrvxdk27suXT.Kxj3IB5gqbyXNLbX8Mc.pfGslmSu',
       'Lý Minh Quang', 'quang1001@bluemoon.local', '0971111015', r.id, h.id, true, false
FROM roles r JOIN households h ON h.household_code = 'H-E1001-01' WHERE r.code = 'RESIDENT'
ON CONFLICT (lower(username)) DO NOTHING;

-- =====================================================================
-- 6. KHOẢN THU BỔ SUNG (thêm ô tô, xe đạp, nước, phí đỗ xe)
-- =====================================================================
INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, cycle, due_day, status, description, created_by)
SELECT 'PHI_GUI_OTO', 'Phí gửi ô tô', 'PARKING', 'PER_VEHICLE', 'xe', 'CAR', false, 'MONTHLY', 15, 'ACTIVE', 'Phí trông giữ ô tô theo tháng', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt' ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, cycle, due_day, status, description, created_by)
SELECT 'PHI_GUI_XEDAP', 'Phí gửi xe đạp', 'PARKING', 'PER_VEHICLE', 'xe', 'BICYCLE', false, 'MONTHLY', 15, 'ACTIVE', 'Phí trông giữ xe đạp theo tháng', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt' ON CONFLICT (code) DO NOTHING;

INSERT INTO fee_types (code, name, fee_group, calc_method, unit_label, vehicle_type, is_pass_through, cycle, due_day, status, description, created_by)
SELECT 'PHI_DICH_VU', 'Phí dịch vụ chung', 'OTHER', 'PER_HOUSEHOLD', 'hộ', NULL, false, 'MONTHLY', 15, 'ACTIVE', 'Phí dịch vụ tiện ích chung (thang máy, bảo vệ, cảnh quan)', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt' ON CONFLICT (code) DO NOTHING;

-- Đơn giá bổ sung
INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 1200000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u WHERE ft.code = 'PHI_GUI_OTO' AND lower(u.username) = 'admin_bqt'
AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_to IS NULL);

INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 20000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u WHERE ft.code = 'PHI_GUI_XEDAP' AND lower(u.username) = 'admin_bqt'
AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_to IS NULL);

INSERT INTO fee_rates (fee_type_id, unit_price, effective_from, effective_to, created_by)
SELECT ft.id, 150000.00, DATE '2026-01-01', NULL, u.id
FROM fee_types ft, users u WHERE ft.code = 'PHI_DICH_VU' AND lower(u.username) = 'admin_bqt'
AND NOT EXISTS (SELECT 1 FROM fee_rates fr WHERE fr.fee_type_id = ft.id AND fr.effective_to IS NULL);

-- =====================================================================
-- 7. PHƯƠNG TIỆN (đăng ký xe cho các hộ)
-- =====================================================================
INSERT INTO vehicles (household_id, plate_number, vehicle_type, brand, color, status, registered_date)
SELECT h.id, plate, vtype, brand, color, 'ACTIVE', reg_date::date
FROM (VALUES
    ('H-A0301-01', '29B1-11101', 'MOTORBIKE', 'Honda Vision', 'Đỏ',     '2025-06-01'),
    ('H-A0702-01', '29B1-22201', 'MOTORBIKE', 'Yamaha NVX',   'Đen',    '2025-03-15'),
    ('H-A0702-01', '30A-22202',  'CAR',       'VinFast VF8',  'Xanh',   '2025-03-15'),
    ('H-A1001-01', '29C1-33301', 'MOTORBIKE', 'Honda SH',     'Trắng',  '2025-01-01'),
    ('H-A1503-01', '30G-44401',  'CAR',       'Toyota Corolla','Bạc',    '2024-09-01'),
    ('H-A1503-01', '29F1-44402', 'MOTORBIKE', 'Honda Lead',   'Hồng',   '2024-09-01'),
    ('H-B0301-01', '29B1-55501', 'MOTORBIKE', 'Yamaha Janus', 'Xanh',   '2025-07-01'),
    ('H-B0602-01', '29D1-66601', 'MOTORBIKE', 'Honda Winner', 'Đen',    '2025-04-01'),
    ('H-B0602-01', 'XD-B0602',   'BICYCLE',   'Giant Escape',  'Xám',    '2025-04-01'),
    ('H-B1101-01', '29B1-77701', 'MOTORBIKE', 'SYM Abela',    'Nâu',    '2024-12-15'),
    ('H-B1402-01', '30H-88801',  'CAR',       'Mazda CX5',    'Đỏ',     '2024-06-01'),
    ('H-B1402-01', '29A1-88802', 'MOTORBIKE', 'Honda AirBlade','Đen',   '2024-06-01'),
    ('H-B1402-01', 'XD-B1402',   'BICYCLE',   'Xe đạp trẻ em', 'Vàng',   '2025-01-01'),
    ('H-C0401-01', '29C1-99901', 'MOTORBIKE', 'Yamaha Grande', 'Trắng', '2025-08-01'),
    ('H-C0803-01', '30K-10001',  'CAR',       'KIA Seltos',   'Trắng',  '2025-02-01'),
    ('H-C0803-01', '29E1-10002', 'MOTORBIKE', 'Honda Wave',   'Xanh',   '2025-02-01'),
    ('H-C1201-01', '30L-11001',  'CAR',       'BMW X3',       'Đen',    '2024-10-01'),
    ('H-C1201-01', '29F1-11002', 'MOTORBIKE', 'Vespa Sprint',  'Xanh',   '2024-10-01'),
    ('H-D0501-01', '29B1-12001', 'MOTORBIKE', 'Honda PCX',    'Đen',    '2025-05-01'),
    ('H-D0802-01', '30A-13001',  'CAR',       'Hyundai Tucson','Trắng', '2025-01-15'),
    ('H-D0802-01', '29G1-13002', 'MOTORBIKE', 'Yamaha Sirius', 'Đỏ',    '2025-01-15'),
    ('H-E0602-01', '29H1-14001', 'MOTORBIKE', 'Honda Vision', 'Xám',    '2025-06-15'),
    ('H-E0602-01', '29H1-14002', 'MOTORBIKE', 'SYM Star SR',  'Đen',    '2025-06-15'),
    ('H-E1001-01', '30M-15001',  'CAR',       'Mercedes C200','Đen',    '2024-11-01'),
    ('H-E1001-01', '29K1-15002', 'MOTORBIKE', 'Honda SH350i', 'Nâu',    '2024-11-01'),
    ('H-E1001-01', 'XD-E1001',   'BICYCLE',   'Thống Nhất',   'Đỏ',     '2025-01-01')
) AS t(hh_code, plate, vtype, brand, color, reg_date)
JOIN households h ON h.household_code = t.hh_code
WHERE NOT EXISTS (SELECT 1 FROM vehicles v WHERE v.plate_number = t.plate);

-- =====================================================================
-- 8. MIỄN GIẢM PHÍ MẪU (fee_exemptions)
-- =====================================================================
-- Hộ chị Lan (C0401) - mẹ đơn thân, giảm 50% phí quản lý
INSERT INTO fee_exemptions (household_id, fee_type_id, discount_type, discount_value, reason, decision_no, approved_by, valid_from, valid_to, status)
SELECT h.id, ft.id, 'PERCENT', 50.00, 'Hộ nghèo - mẹ đơn thân nuôi con nhỏ', 'QD-2026-001', u.id, DATE '2026-01-01', DATE '2026-12-31', 'ACTIVE'
FROM households h, fee_types ft, users u
WHERE h.household_code = 'H-C0401-01' AND ft.code = 'PHI_QUAN_LY' AND lower(u.username) = 'admin_bqt'
AND NOT EXISTS (
    SELECT 1 FROM fee_exemptions fe WHERE fe.household_id = h.id AND fe.fee_type_id = ft.id AND fe.status = 'ACTIVE'
);

-- Hộ bà Xuân (B1402) - người cao tuổi, miễn 100% phí vệ sinh
INSERT INTO fee_exemptions (household_id, fee_type_id, discount_type, discount_value, reason, decision_no, approved_by, valid_from, valid_to, status)
SELECT h.id, ft.id, 'PERCENT', 100.00, 'Hộ có người cao tuổi trên 70 - Miễn phí vệ sinh', 'QD-2026-002', u.id, DATE '2026-01-01', NULL, 'ACTIVE'
FROM households h, fee_types ft, users u
WHERE h.household_code = 'H-B1402-01' AND ft.code = 'PHI_VE_SINH' AND lower(u.username) = 'admin_bqt'
AND NOT EXISTS (
    SELECT 1 FROM fee_exemptions fe WHERE fe.household_id = h.id AND fe.fee_type_id = ft.id AND fe.status = 'ACTIVE'
);

-- Hộ chị Hoa (A0301) - giảm 20.000đ phí dịch vụ
INSERT INTO fee_exemptions (household_id, fee_type_id, discount_type, discount_value, reason, decision_no, approved_by, valid_from, valid_to, status)
SELECT h.id, ft.id, 'AMOUNT', 20000.00, 'Căn studio diện tích nhỏ - Giảm phí dịch vụ', 'QD-2026-003', u.id, DATE '2026-06-01', DATE '2026-12-31', 'ACTIVE'
FROM households h, fee_types ft, users u
WHERE h.household_code = 'H-A0301-01' AND ft.code = 'PHI_DICH_VU' AND lower(u.username) = 'admin_bqt'
AND NOT EXISTS (
    SELECT 1 FROM fee_exemptions fe WHERE fe.household_id = h.id AND fe.fee_type_id = ft.id AND fe.status = 'ACTIVE'
);

-- =====================================================================
-- 9. TẠM TRÚ MẪU (temporary_residences)
-- =====================================================================
INSERT INTO temporary_residences (household_id, apartment_id, full_name, date_of_birth, gender, cccd, phone, permanent_address, start_date, end_date, status, note, created_by)
SELECT h.id, a.id,
    'Nguyễn Văn Khách', '1995-05-10'::date, 'NAM', '034195005010', '0988111222',
    'Số 10, Phố Huế, Hai Bà Trưng, Hà Nội',
    DATE '2026-10-01', DATE '2026-12-31', 'ACTIVE',
    'Khách ở nhờ 3 tháng - bạn của chủ hộ', u.id
FROM households h
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
JOIN users u ON lower(u.username) = 'admin_bqt'
WHERE h.household_code = 'H-A0702-01'
AND NOT EXISTS (
    SELECT 1 FROM temporary_residences tr WHERE tr.household_id = h.id AND tr.cccd = '034195005010' AND tr.status = 'ACTIVE'
);

-- Tạm trú sắp hết hạn (cảnh báo 15 ngày)
INSERT INTO temporary_residences (household_id, apartment_id, full_name, date_of_birth, gender, cccd, phone, permanent_address, start_date, end_date, status, note, created_by)
SELECT h.id, a.id,
    'Trần Thị Ngọc', '2000-08-20'::date, 'NU', '038200008020', '0977333444',
    'Thị trấn Lâm, Ý Yên, Nam Định',
    DATE '2026-09-01', DATE '2026-12-10', 'ACTIVE',
    'Sinh viên thực tập - sắp hết hạn', u.id
FROM households h
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
JOIN users u ON lower(u.username) = 'admin_bqt'
WHERE h.household_code = 'H-B0602-01'
AND NOT EXISTS (
    SELECT 1 FROM temporary_residences tr WHERE tr.household_id = h.id AND tr.cccd = '038200008020' AND tr.status = 'ACTIVE'
);

-- =====================================================================
-- 10. TẠM VẮNG MẪU (temporary_absences)
-- =====================================================================
-- Anh Hà (B1101) đi công tác 2 tháng
INSERT INTO temporary_absences (resident_id, start_date, end_date, destination, reason, status, created_by)
SELECT r.id, DATE '2026-11-01', DATE '2026-12-31',
    'TP. Hồ Chí Minh', 'Đi công tác dài hạn', 'ACTIVE', u.id
FROM residents r
JOIN households h ON h.id = r.household_id
JOIN users u ON lower(u.username) = 'admin_bqt'
WHERE h.household_code = 'H-B1101-01' AND r.full_name = 'Bùi Quang Hà' AND NOT r.is_deleted
AND NOT EXISTS (
    SELECT 1 FROM temporary_absences ta WHERE ta.resident_id = r.id AND ta.status = 'ACTIVE'
);

-- Chị Phương Anh (C1201) đi du học - sắp hết hạn tạm vắng
INSERT INTO temporary_absences (resident_id, start_date, end_date, destination, reason, status, created_by)
SELECT r.id, DATE '2026-06-01', DATE '2026-12-15',
    'Tokyo, Nhật Bản', 'Du học trao đổi 1 học kỳ', 'ACTIVE', u.id
FROM residents r
JOIN households h ON h.id = r.household_id
JOIN users u ON lower(u.username) = 'admin_bqt'
WHERE h.household_code = 'H-C1201-01' AND r.full_name = 'Trần Phương Anh' AND NOT r.is_deleted
AND NOT EXISTS (
    SELECT 1 FROM temporary_absences ta WHERE ta.resident_id = r.id AND ta.status = 'ACTIVE'
);

-- =====================================================================
-- 11. KỲ THU THÁNG 10/2026 (OPEN) + 11/2026 (DRAFT)
-- =====================================================================
INSERT INTO billing_periods (period_month, name, due_date, status, generated_at, created_by)
SELECT DATE '2026-10-01', 'Kỳ thu phí tháng 10/2026', DATE '2026-10-20', 'OPEN',
       TIMESTAMPTZ '2026-10-02 09:00:00+07', u.id
FROM users u WHERE lower(u.username) = 'ketoan_01'
ON CONFLICT (period_month) DO NOTHING;

INSERT INTO billing_periods (period_month, name, due_date, status, created_by)
SELECT DATE '2026-11-01', 'Kỳ thu phí tháng 11/2026', DATE '2026-11-20', 'DRAFT', u.id
FROM users u WHERE lower(u.username) = 'ketoan_01'
ON CONFLICT (period_month) DO NOTHING;

-- =====================================================================
-- 12. CHỈ SỐ ĐIỆN NƯỚC KỲ 10/2026
-- =====================================================================
-- Điện kỳ 10/2026 cho các hộ mới
INSERT INTO utility_readings (household_id, fee_type_id, billing_period_id, previous_index, current_index, unit_price, amount, recorded_by)
SELECT h.id, ft.id, bp.id, prev_idx, curr_idx, 3000.00, (curr_idx - prev_idx) * 3000.00, u.id
FROM (VALUES
    ('H-A0301-01', 200.00,  280.00),
    ('H-A0702-01', 350.00,  490.00),
    ('H-A1001-01', 500.00,  650.00),
    ('H-A1503-01', 800.00, 1020.00),
    ('H-B0301-01', 100.00,  165.00),
    ('H-B0602-01', 400.00,  540.00),
    ('H-B1101-01', 300.00,  420.00),
    ('H-B1402-01', 900.00, 1180.00),
    ('H-C0401-01', 150.00,  230.00),
    ('H-C0803-01', 600.00,  780.00),
    ('H-C1201-01', 1200.00, 1550.00),
    ('H-D0501-01', 180.00,  260.00),
    ('H-D0802-01', 450.00,  610.00),
    ('H-E0602-01', 320.00,  450.00),
    ('H-E1001-01', 700.00,  950.00)
) AS t(hh_code, prev_idx, curr_idx)
JOIN households h ON h.household_code = t.hh_code
CROSS JOIN fee_types ft
CROSS JOIN billing_periods bp
CROSS JOIN (SELECT id FROM users WHERE lower(username) = 'ketoan_01') u
WHERE ft.code = 'TIEN_DIEN' AND bp.period_month = DATE '2026-10-01'
ON CONFLICT (household_id, fee_type_id, billing_period_id) DO NOTHING;

-- Nước kỳ 10/2026
INSERT INTO utility_readings (household_id, fee_type_id, billing_period_id, previous_index, current_index, unit_price, amount, recorded_by)
SELECT h.id, ft.id, bp.id, prev_idx, curr_idx, 15000.00, (curr_idx - prev_idx) * 15000.00, u.id
FROM (VALUES
    ('H-A0301-01',  50.00,  58.00),
    ('H-A0702-01',  80.00,  95.00),
    ('H-A1001-01', 100.00, 115.00),
    ('H-A1503-01', 120.00, 142.00),
    ('H-B0301-01',  30.00,  36.00),
    ('H-B0602-01',  70.00,  85.00),
    ('H-B1101-01',  60.00,  74.00),
    ('H-B1402-01', 150.00, 178.00),
    ('H-C0401-01',  40.00,  50.00),
    ('H-C0803-01',  90.00, 108.00),
    ('H-C1201-01', 180.00, 215.00),
    ('H-D0501-01',  35.00,  43.00),
    ('H-D0802-01',  85.00, 100.00),
    ('H-E0602-01',  65.00,  78.00),
    ('H-E1001-01', 130.00, 155.00)
) AS t(hh_code, prev_idx, curr_idx)
JOIN households h ON h.household_code = t.hh_code
CROSS JOIN fee_types ft
CROSS JOIN billing_periods bp
CROSS JOIN (SELECT id FROM users WHERE lower(username) = 'ketoan_01') u
WHERE ft.code = 'TIEN_NUOC' AND bp.period_month = DATE '2026-10-01'
ON CONFLICT (household_id, fee_type_id, billing_period_id) DO NOTHING;

-- =====================================================================
-- 13. GIẤY BÁO (invoices) KỲ 10/2026 cho 5 hộ mẫu
-- =====================================================================

-- Hộ H-A0301-01: 55m2 × 7000 = 385000 (QL) + 30000 (VS) + 150000-20000=130000 (DV) + 70000 (xe máy) + 240000 (điện) + 120000 (nước)
-- fee_amount = 975000, discount_amount = 20000, total_due = 955000
INSERT INTO invoices (billing_period_id, household_id, apartment_id, apartment_area, fee_amount, discount_amount, previous_debt, credit_applied, total_due, paid_amount, status)
SELECT bp.id, h.id, a.id, 55.00, 975000.00, 20000.00, 0.00, 0.00, 955000.00, 0.00, 'UNPAID'
FROM billing_periods bp
JOIN households h ON h.household_code = 'H-A0301-01'
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
WHERE bp.period_month = DATE '2026-10-01'
ON CONFLICT (billing_period_id, household_id) DO NOTHING;

-- Invoice items cho H-A0301-01
INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, qty, uprice, gross, disc, net, 0.00, descr
FROM (VALUES
    ('PHI_QUAN_LY',   55.000, 7000.00, 385000.00,     0.00, 385000.00, '55 m² × 7.000 đ'),
    ('PHI_VE_SINH',    1.000, 30000.00, 30000.00,      0.00,  30000.00, '1 hộ × 30.000 đ'),
    ('PHI_DICH_VU',    1.000, 150000.00, 150000.00, 20000.00, 130000.00, '1 hộ × 150.000 đ (giảm 20.000 đ)'),
    ('PHI_GUI_XEMAY',  1.000, 70000.00, 70000.00,      0.00,  70000.00, '1 xe × 70.000 đ'),
    ('TIEN_DIEN',     80.000, 3000.00, 240000.00,      0.00, 240000.00, 'Điện: 280-200 = 80 kWh × 3.000 đ'),
    ('TIEN_NUOC',      8.000, 15000.00, 120000.00,     0.00, 120000.00, 'Nước: 58-50 = 8 m³ × 15.000 đ')
) AS t(fee_code, qty, uprice, gross, disc, net, descr)
JOIN invoices inv ON true
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-10-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-A0301-01'
JOIN fee_types ft ON ft.code = t.fee_code
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

-- Hộ H-A1503-01: 85m2 × 7000 = 595000 (QL) + 30000 (VS) + 150000 (DV) + 1200000 (ô tô) + 70000 (xe máy) + 660000 (điện) + 330000 (nước)
-- fee_amount = 3035000, discount_amount = 0, total_due = 3035000
INSERT INTO invoices (billing_period_id, household_id, apartment_id, apartment_area, fee_amount, discount_amount, previous_debt, credit_applied, total_due, paid_amount, status)
SELECT bp.id, h.id, a.id, 85.00, 3035000.00, 0.00, 0.00, 0.00, 3035000.00, 0.00, 'UNPAID'
FROM billing_periods bp
JOIN households h ON h.household_code = 'H-A1503-01'
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
WHERE bp.period_month = DATE '2026-10-01'
ON CONFLICT (billing_period_id, household_id) DO NOTHING;

INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, qty, uprice, gross, disc, net, 0.00, descr
FROM (VALUES
    ('PHI_QUAN_LY',    85.000,  7000.00, 595000.00,  0.00, 595000.00, '85 m² × 7.000 đ'),
    ('PHI_VE_SINH',     1.000, 30000.00,  30000.00,  0.00,  30000.00, '1 hộ × 30.000 đ'),
    ('PHI_DICH_VU',     1.000, 150000.00, 150000.00, 0.00, 150000.00, '1 hộ × 150.000 đ'),
    ('PHI_GUI_OTO',     1.000, 1200000.00, 1200000.00, 0.00, 1200000.00, '1 ô tô × 1.200.000 đ'),
    ('PHI_GUI_XEMAY',   1.000, 70000.00,  70000.00,  0.00,  70000.00, '1 xe máy × 70.000 đ'),
    ('TIEN_DIEN',     220.000,  3000.00, 660000.00,  0.00, 660000.00, 'Điện: 1020-800 = 220 kWh × 3.000 đ'),
    ('TIEN_NUOC',      22.000, 15000.00, 330000.00,  0.00, 330000.00, 'Nước: 142-120 = 22 m³ × 15.000 đ')
) AS t(fee_code, qty, uprice, gross, disc, net, descr)
JOIN invoices inv ON true
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-10-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-A1503-01'
JOIN fee_types ft ON ft.code = t.fee_code
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

-- Hộ H-B1402-01: 92m2 × 7000 = 644000 (QL) + 0 (VS miễn 100%) + 150000 (DV) + 1200000 (ô tô) + 70000 (xe máy) + 20000 (xe đạp) + 840000 (điện) + 420000 (nước)
-- fee_amount = 3374000, discount_amount = 30000 (VS), total_due = 3344000
INSERT INTO invoices (billing_period_id, household_id, apartment_id, apartment_area, fee_amount, discount_amount, previous_debt, credit_applied, total_due, paid_amount, status)
SELECT bp.id, h.id, a.id, 92.00, 3374000.00, 30000.00, 0.00, 0.00, 3344000.00, 3344000.00, 'PAID'
FROM billing_periods bp
JOIN households h ON h.household_code = 'H-B1402-01'
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
WHERE bp.period_month = DATE '2026-10-01'
ON CONFLICT (billing_period_id, household_id) DO NOTHING;

INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, qty, uprice, gross, disc, net, net, descr
FROM (VALUES
    ('PHI_QUAN_LY',    92.000,   7000.00, 644000.00,     0.00, 644000.00, '92 m² × 7.000 đ'),
    ('PHI_VE_SINH',     1.000,  30000.00,  30000.00, 30000.00,      0.00, '1 hộ × 30.000 đ (miễn 100%)'),
    ('PHI_DICH_VU',     1.000, 150000.00, 150000.00,     0.00, 150000.00, '1 hộ × 150.000 đ'),
    ('PHI_GUI_OTO',     1.000, 1200000.00, 1200000.00,   0.00, 1200000.00, '1 ô tô × 1.200.000 đ'),
    ('PHI_GUI_XEMAY',   1.000,  70000.00,  70000.00,     0.00,  70000.00, '1 xe máy × 70.000 đ'),
    ('PHI_GUI_XEDAP',   1.000,  20000.00,  20000.00,     0.00,  20000.00, '1 xe đạp × 20.000 đ'),
    ('TIEN_DIEN',     280.000,   3000.00, 840000.00,     0.00, 840000.00, 'Điện: 1180-900 = 280 kWh × 3.000 đ'),
    ('TIEN_NUOC',      28.000,  15000.00, 420000.00,     0.00, 420000.00, 'Nước: 178-150 = 28 m³ × 15.000 đ')
) AS t(fee_code, qty, uprice, gross, disc, net, descr)
JOIN invoices inv ON true
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-10-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-B1402-01'
JOIN fee_types ft ON ft.code = t.fee_code
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

-- Hộ H-C0401-01: 50m2 × 7000 = 350000 → giảm 50% = 175000 (QL) + 30000 (VS) + 150000 (DV) + 70000 (xe máy) + 240000 (điện) + 150000 (nước)
-- fee_amount = 990000, discount_amount = 175000, total_due = 815000, paid 500000 → PARTIAL
INSERT INTO invoices (billing_period_id, household_id, apartment_id, apartment_area, fee_amount, discount_amount, previous_debt, credit_applied, total_due, paid_amount, status)
SELECT bp.id, h.id, a.id, 50.00, 990000.00, 175000.00, 0.00, 0.00, 815000.00, 500000.00, 'PARTIAL'
FROM billing_periods bp
JOIN households h ON h.household_code = 'H-C0401-01'
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
WHERE bp.period_month = DATE '2026-10-01'
ON CONFLICT (billing_period_id, household_id) DO NOTHING;

INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, qty, uprice, gross, disc, net, paid, descr
FROM (VALUES
    ('PHI_QUAN_LY',   50.000,  7000.00, 350000.00, 175000.00, 175000.00, 175000.00, '50 m² × 7.000 đ (giảm 50%)'),
    ('PHI_VE_SINH',    1.000, 30000.00,  30000.00,      0.00,  30000.00,  30000.00, '1 hộ × 30.000 đ'),
    ('PHI_DICH_VU',    1.000, 150000.00, 150000.00,     0.00, 150000.00, 150000.00, '1 hộ × 150.000 đ'),
    ('PHI_GUI_XEMAY',  1.000, 70000.00,  70000.00,      0.00,  70000.00,  70000.00, '1 xe máy × 70.000 đ'),
    ('TIEN_DIEN',     80.000,  3000.00, 240000.00,      0.00, 240000.00,  75000.00, 'Điện: 230-150 = 80 kWh × 3.000 đ'),
    ('TIEN_NUOC',     10.000, 15000.00, 150000.00,      0.00, 150000.00,      0.00, 'Nước: 50-40 = 10 m³ × 15.000 đ')
) AS t(fee_code, qty, uprice, gross, disc, net, paid, descr)
JOIN invoices inv ON true
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-10-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-C0401-01'
JOIN fee_types ft ON ft.code = t.fee_code
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

-- Hộ H-E1001-01: 88m2 × 7000 = 616000 (QL) + 30000 (VS) + 150000 (DV) + 1200000 (ô tô) + 70000 (xe máy) + 20000 (xe đạp) + 750000 (điện) + 375000 (nước)
-- fee_amount = 3211000, discount_amount = 0, total_due = 3211000 → UNPAID
INSERT INTO invoices (billing_period_id, household_id, apartment_id, apartment_area, fee_amount, discount_amount, previous_debt, credit_applied, total_due, paid_amount, status)
SELECT bp.id, h.id, a.id, 88.00, 3211000.00, 0.00, 0.00, 0.00, 3211000.00, 0.00, 'UNPAID'
FROM billing_periods bp
JOIN households h ON h.household_code = 'H-E1001-01'
JOIN apartment_occupancies ao ON ao.household_id = h.id AND ao.end_date IS NULL
JOIN apartments a ON a.id = ao.apartment_id
WHERE bp.period_month = DATE '2026-10-01'
ON CONFLICT (billing_period_id, household_id) DO NOTHING;

INSERT INTO invoice_items (invoice_id, fee_type_id, quantity, unit_price, gross_amount, discount_amount, net_amount, paid_amount, description)
SELECT inv.id, ft.id, qty, uprice, gross, disc, net, 0.00, descr
FROM (VALUES
    ('PHI_QUAN_LY',    88.000,   7000.00,  616000.00, 0.00,  616000.00, '88 m² × 7.000 đ'),
    ('PHI_VE_SINH',     1.000,  30000.00,   30000.00, 0.00,   30000.00, '1 hộ × 30.000 đ'),
    ('PHI_DICH_VU',     1.000, 150000.00,  150000.00, 0.00,  150000.00, '1 hộ × 150.000 đ'),
    ('PHI_GUI_OTO',     1.000, 1200000.00, 1200000.00, 0.00, 1200000.00, '1 ô tô × 1.200.000 đ'),
    ('PHI_GUI_XEMAY',   1.000,  70000.00,   70000.00, 0.00,   70000.00, '1 xe máy × 70.000 đ'),
    ('PHI_GUI_XEDAP',   1.000,  20000.00,   20000.00, 0.00,   20000.00, '1 xe đạp × 20.000 đ'),
    ('TIEN_DIEN',     250.000,   3000.00,  750000.00, 0.00,  750000.00, 'Điện: 950-700 = 250 kWh × 3.000 đ'),
    ('TIEN_NUOC',      25.000,  15000.00,  375000.00, 0.00,  375000.00, 'Nước: 155-130 = 25 m³ × 15.000 đ')
) AS t(fee_code, qty, uprice, gross, disc, net, descr)
JOIN invoices inv ON true
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-10-01'
JOIN households h ON h.id = inv.household_id AND h.household_code = 'H-E1001-01'
JOIN fee_types ft ON ft.code = t.fee_code
ON CONFLICT (invoice_id, fee_type_id) DO NOTHING;

-- =====================================================================
-- 14. THANH TOÁN (payments) + PHÂN BỔ (payment_allocations) cho hộ B1402
-- =====================================================================
INSERT INTO payments (receipt_no, household_id, paid_at, amount, allocated_amount, credit_amount, method, reference_no, collected_by, status, note)
SELECT 'BL' || lpad(next_document_no('RECEIPT')::text, 8, '0'),
       h.id, TIMESTAMPTZ '2026-10-15 10:30:00+07', 3344000.00, 3344000.00, 0.00,
       'BANK_TRANSFER', 'VCB-2026-10-88801', u.id, 'VALID', 'Thanh toán toàn bộ kỳ 10/2026 qua chuyển khoản'
FROM households h
JOIN users u ON lower(u.username) = 'thuquy_01'
WHERE h.household_code = 'H-B1402-01'
AND NOT EXISTS (
    SELECT 1 FROM payments p WHERE p.household_id = h.id AND p.amount = 3344000.00 AND p.status = 'VALID'
);

-- Phân bổ thanh toán cho từng invoice_item của B1402
INSERT INTO payment_allocations (payment_id, invoice_item_id, amount)
SELECT p.id, ii.id, ii.net_amount
FROM payments p
JOIN households h ON h.id = p.household_id AND h.household_code = 'H-B1402-01'
JOIN invoices inv ON inv.household_id = h.id
JOIN billing_periods bp ON bp.id = inv.billing_period_id AND bp.period_month = DATE '2026-10-01'
JOIN invoice_items ii ON ii.invoice_id = inv.id
WHERE p.status = 'VALID' AND p.amount = 3344000.00
  AND ii.net_amount > 0
  AND NOT EXISTS (
    SELECT 1 FROM payment_allocations pa WHERE pa.payment_id = p.id AND pa.invoice_item_id = ii.id
);

-- Thanh toán một phần cho hộ C0401 (500.000đ)
INSERT INTO payments (receipt_no, household_id, paid_at, amount, allocated_amount, credit_amount, method, collected_by, status, note)
SELECT 'BL' || lpad(next_document_no('RECEIPT')::text, 8, '0'),
       h.id, TIMESTAMPTZ '2026-10-18 14:00:00+07', 500000.00, 500000.00, 0.00,
       'CASH', u.id, 'VALID', 'Nộp tiền mặt một phần - hẹn trả nốt cuối tháng'
FROM households h
JOIN users u ON lower(u.username) = 'thuquy_01'
WHERE h.household_code = 'H-C0401-01'
AND NOT EXISTS (
    SELECT 1 FROM payments p WHERE p.household_id = h.id AND p.amount = 500000.00 AND p.status = 'VALID'
);

-- =====================================================================
-- 15. ĐỢT VẬN ĐỘNG ĐÓNG GÓP TỰ NGUYỆN (donation_campaigns + donations)
-- =====================================================================
INSERT INTO donation_campaigns (code, name, description, start_date, end_date, status, created_by)
SELECT 'QUY_VI_NGUOI_NGHEO_2026', 'Quỹ Vì người nghèo năm 2026',
       'Đợt vận động quyên góp Quỹ Vì người nghèo do UBMTTQ Phường phát động, từ 01/10 đến 31/12/2026.',
       DATE '2026-10-01', DATE '2026-12-31', 'ACTIVE', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt'
ON CONFLICT (code) DO NOTHING;

INSERT INTO donation_campaigns (code, name, description, start_date, end_date, status, created_by)
SELECT 'QUY_KHUYEN_HOC_2026', 'Quỹ Khuyến học năm 2026',
       'Quỹ khuyến học nhằm hỗ trợ học sinh có hoàn cảnh khó khăn trong chung cư.',
       DATE '2026-09-01', DATE '2026-11-30', 'ACTIVE', u.id
FROM users u WHERE lower(u.username) = 'admin_bqt'
ON CONFLICT (code) DO NOTHING;

-- Các hộ đóng góp Quỹ Vì người nghèo
INSERT INTO donations (campaign_id, household_id, voucher_no, amount, donated_at, method, collected_by, status, note)
SELECT dc.id, h.id,
       'QT' || lpad(next_document_no('DONATION')::text, 8, '0'),
       donate_amt, donate_time::timestamptz, pay_method, u.id, 'VALID', note_text
FROM (VALUES
    ('H-A1503-01', 500000.00,  '2026-10-05 09:00:00+07', 'CASH',          'Gia đình anh Đức ủng hộ'),
    ('H-B1402-01', 1000000.00, '2026-10-06 10:30:00+07', 'BANK_TRANSFER', 'Gia đình anh Khoa ủng hộ'),
    ('H-C1201-01', 300000.00,  '2026-10-07 15:00:00+07', 'CASH',          'Gia đình anh Nam ủng hộ'),
    ('H-E1001-01', 2000000.00, '2026-10-08 11:00:00+07', 'BANK_TRANSFER', 'Gia đình anh Quang ủng hộ'),
    ('H-A0702-01', 200000.00,  '2026-10-10 08:30:00+07', 'CASH',          'Gia đình anh Long ủng hộ')
) AS t(hh_code, donate_amt, donate_time, pay_method, note_text)
JOIN donation_campaigns dc ON dc.code = 'QUY_VI_NGUOI_NGHEO_2026'
JOIN households h ON h.household_code = t.hh_code
JOIN users u ON lower(u.username) = 'thuquy_01'
WHERE NOT EXISTS (
    SELECT 1 FROM donations d WHERE d.campaign_id = dc.id AND d.household_id = h.id AND d.status = 'VALID'
);

-- Đóng góp Quỹ Khuyến học
INSERT INTO donations (campaign_id, household_id, voucher_no, amount, donated_at, method, collected_by, status, note)
SELECT dc.id, h.id,
       'QT' || lpad(next_document_no('DONATION')::text, 8, '0'),
       donate_amt, donate_time::timestamptz, pay_method, u.id, 'VALID', note_text
FROM (VALUES
    ('H-A1503-01', 200000.00,  '2026-09-15 09:00:00+07', 'CASH',          'Ủng hộ quỹ khuyến học'),
    ('H-B1402-01', 500000.00,  '2026-09-16 14:00:00+07', 'BANK_TRANSFER', 'Ủng hộ quỹ khuyến học'),
    ('H-E1001-01', 1000000.00, '2026-09-20 10:00:00+07', 'BANK_TRANSFER', 'Ủng hộ quỹ khuyến học')
) AS t(hh_code, donate_amt, donate_time, pay_method, note_text)
JOIN donation_campaigns dc ON dc.code = 'QUY_KHUYEN_HOC_2026'
JOIN households h ON h.household_code = t.hh_code
JOIN users u ON lower(u.username) = 'thuquy_01'
WHERE NOT EXISTS (
    SELECT 1 FROM donations d WHERE d.campaign_id = dc.id AND d.household_id = h.id AND d.status = 'VALID'
);

-- =====================================================================
-- 16. NHẬT KÝ KIỂM TOÁN MẪU (audit_logs)
-- =====================================================================
INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_value, new_value, reason, ip_address, created_at)
SELECT u.id, action_text, entity, eid, old_val::jsonb, new_val::jsonb, reason_text, '192.168.1.100'::inet, ts::timestamptz
FROM (VALUES
    ('admin_bqt',  'LOGIN',              'User',      NULL, NULL, '{"username":"admin_bqt"}', NULL,                     '2026-10-01 08:00:00+07'),
    ('ketoan_01',  'LOGIN',              'User',      NULL, NULL, '{"username":"ketoan_01"}', NULL,                     '2026-10-02 08:30:00+07'),
    ('ketoan_01',  'CREATE_BILLING',     'BillingPeriod', NULL, NULL, '{"period":"2026-10-01","status":"OPEN"}', 'Tạo kỳ thu tháng 10/2026', '2026-10-02 09:00:00+07'),
    ('admin_bqt',  'CREATE_EXEMPTION',   'FeeExemption', NULL, NULL, '{"household":"H-C0401-01","fee":"PHI_QUAN_LY","discount":"50%"}', 'Duyệt miễn giảm cho hộ nghèo', '2026-10-03 10:00:00+07'),
    ('thuquy_01',  'LOGIN',              'User',      NULL, NULL, '{"username":"thuquy_01"}', NULL,                     '2026-10-15 10:00:00+07'),
    ('thuquy_01',  'CREATE_PAYMENT',     'Payment',   NULL, NULL, '{"household":"H-B1402-01","amount":3344000}', 'Thu tiền chuyển khoản', '2026-10-15 10:30:00+07'),
    ('thuquy_01',  'CREATE_PAYMENT',     'Payment',   NULL, NULL, '{"household":"H-C0401-01","amount":500000}', 'Thu tiền mặt một phần', '2026-10-18 14:00:00+07'),
    ('admin_bqt',  'CREATE_TEMP_RES',    'TempResidence', NULL, NULL, '{"household":"H-A0702-01","name":"Nguyễn Văn Khách"}', 'Đăng ký tạm trú', '2026-10-01 09:30:00+07'),
    ('admin_bqt',  'CREATE_TEMP_ABS',    'TempAbsence', NULL, NULL, '{"resident":"Bùi Quang Hà","dest":"TP.HCM"}', 'Đăng ký tạm vắng', '2026-11-01 08:00:00+07'),
    ('cudan_b1204','LOGIN',              'User',      NULL, NULL, '{"username":"cudan_b1204"}', NULL,                   '2026-10-20 19:00:00+07')
) AS t(uname, action_text, entity, eid, old_val, new_val, reason_text, ts)
JOIN users u ON lower(u.username) = t.uname;

-- =====================================================================
-- 17. LỊCH SỬ SAO LƯU MẪU (backup_jobs)
-- =====================================================================
INSERT INTO backup_jobs (status, requested_by, requested_at, finished_at, size_bytes, file_path)
VALUES
    ('SUCCEEDED', NULL, TIMESTAMPTZ '2026-10-01 02:00:00+07', TIMESTAMPTZ '2026-10-01 02:03:15+07', 52428800, '/backups/bluemoon_20261001_020000.sql.gz'),
    ('SUCCEEDED', NULL, TIMESTAMPTZ '2026-10-15 02:00:00+07', TIMESTAMPTZ '2026-10-15 02:04:22+07', 55574528, '/backups/bluemoon_20261015_020000.sql.gz'),
    ('SUCCEEDED', NULL, TIMESTAMPTZ '2026-11-01 02:00:00+07', TIMESTAMPTZ '2026-11-01 02:03:50+07', 58720256, '/backups/bluemoon_20261101_020000.sql.gz'),
    ('SUCCEEDED', NULL, TIMESTAMPTZ '2026-11-15 02:00:00+07', TIMESTAMPTZ '2026-11-15 02:05:10+07', 61865984, '/backups/bluemoon_20261115_020000.sql.gz');

COMMIT;
