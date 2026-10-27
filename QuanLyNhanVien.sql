CREATE DATABASE IF NOT EXISTS QuanLyNhanVien
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

use QuanLyNhanVien;
-- ==============================================================================
CREATE TABLE IF NOT EXISTS phong_ban (
ma_phong_ban VARCHAR(10) PRIMARY KEY,
ten_phong_ban VARCHAR(100) NOT NULL UNIQUE,
tien_to_ma VARCHAR(5) NOT NULL UNIQUE -- Dùng để sinh mã tự động (NS, KT, KTH, KD)
) ENGINE=InnoDB;

INSERT INTO phong_ban (ma_phong_ban, ten_phong_ban, tien_to_ma) VALUES
('PB01', 'Phòng IT', 'IT'),
('PB02', 'Phòng Nhân sự', 'NS'),
('PB03', 'Phòng Marketing', 'MKT'),
('PB04', 'Phòng Kinh doanh', 'KD'),
('PB05', 'Phòng Kế toán', 'KT')
AS new_pb
ON DUPLICATE KEY UPDATE ten_phong_ban = new_pb.ten_phong_ban;
-- ==============================================================================
-- 3. TẠO BẢNG CHỨC VỤ (chuc_vu)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS chuc_vu (
ma_chuc_vu VARCHAR(10) PRIMARY KEY,
ten_chuc_vu VARCHAR(100) NOT NULL UNIQUE,
phu_cap DECIMAL(15, 2) DEFAULT 0.00
) ENGINE=InnoDB;
-- . Thêm dữ liệu mẫu cho bảng Chức vụ (chuc_vu)
INSERT INTO chuc_vu (ma_chuc_vu, ten_chuc_vu, phu_cap) VALUES
('CV01', 'Trưởng phòng', 2000000.00),
('CV02', 'Phó phòng', 1000000.00),
('CV03', 'Nhân viên', 500000.00),
('CV04', 'Thực tập sinh', 0.00)
AS new_cv
ON DUPLICATE KEY UPDATE
    ten_chuc_vu = new_cv.ten_chuc_vu,
    phu_cap = new_cv.phu_cap;
-- ==============================================================================
-- 4. TẠO BẢNG NGƯỜI DÙNG & TÀI KHOẢN (nguoi_dung)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS nguoi_dung (
id INT AUTO_INCREMENT PRIMARY KEY,
ten_dang_nhap VARCHAR(50) NOT NULL UNIQUE, -- Trùng với Mã NV (ví dụ: NS001, KT001)
mat_khau VARCHAR(100) NOT NULL,            -- Lưu mật khẩu dạng chữ theo ứng dụng
ho_ten VARCHAR(100) NOT NULL,
email VARCHAR(100) NOT NULL UNIQUE,
vai_tro ENUM('Admin', 'TruongPhong', 'NhanVien') NOT NULL DEFAULT 'NhanVien',
trang_thai TINYINT(1) DEFAULT 1,            -- 1: Hoạt động, 0: Khóa
ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
-- ==============================================================================
-- 5. TẠO BẢNG NHÂN VIÊN (nhan_vien)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS nhan_vien (
ma_nv VARCHAR(20) PRIMARY KEY,
ho_ten VARCHAR(100) NOT NULL,
gioi_tinh VARCHAR(10) DEFAULT 'Nam',
ngay_sinh DATE,
ngay_vao_lam DATE NOT NULL,
ngay_nghi_viec DATE DEFAULT NULL,
sdt VARCHAR(15) NOT NULL UNIQUE,
email VARCHAR(100) NOT NULL UNIQUE,
ma_phong_ban VARCHAR(10),
ma_chuc_vu VARCHAR(10),
luong_co_ban DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
trang_thai VARCHAR(30) DEFAULT 'Đang làm việc',
nguoi_dung_id INT UNIQUE, -- Liên kết 1-1 với bảng nguoi_dung
CONSTRAINT chk_nhan_vien_ngay_lam_viec CHECK (
    ngay_nghi_viec IS NULL OR ngay_nghi_viec >= ngay_vao_lam
),
KEY idx_nhan_vien_ngay_lam (ngay_vao_lam, ngay_nghi_viec),
CONSTRAINT fk_nv_phongban FOREIGN KEY (ma_phong_ban)
    REFERENCES phong_ban(ma_phong_ban) ON DELETE SET NULL ON UPDATE CASCADE,
CONSTRAINT fk_nv_chucvu FOREIGN KEY (ma_chuc_vu)
    REFERENCES chuc_vu(ma_chuc_vu) ON DELETE SET NULL ON UPDATE CASCADE,
CONSTRAINT fk_nv_nguoidung FOREIGN KEY (nguoi_dung_id)
    REFERENCES nguoi_dung(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bang_luong (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ma_nv VARCHAR(20) NOT NULL,
    thang TINYINT UNSIGNED NOT NULL,
    nam SMALLINT UNSIGNED NOT NULL,
    luong_cb DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    ngay_cong TINYINT UNSIGNED NOT NULL DEFAULT 24,
    gio_ot DECIMAL(4, 1) UNSIGNED NOT NULL DEFAULT 0.0,
    -- Chỉ lưu giờ OT; tiền OT được sinh tự động để không thể sai lệch công thức.
    luong_ot DECIMAL(15, 2) GENERATED ALWAYS AS (
        ROUND((luong_cb / (24.0 * 8.0)) * gio_ot * 1.5, 2)
    ) STORED,
    -- Chỉ có một loại phụ cấp: phụ cấp chức vụ, lấy từ chuc_vu.phu_cap khi lập lương.
    phu_cap DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    khoan_tru DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
    -- Không cho thực nhận âm; công thức này đồng nhất với form tính lương.
    thuc_nhan DECIMAL(15, 2) GENERATED ALWAYS AS (
        GREATEST(
            0,
            ROUND(
                ((luong_cb / 24.0) * ngay_cong)
                + luong_ot
                + phu_cap - khoan_tru,
                2
            )
        )
    ) STORED,
    ngay_tinh DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_bang_luong_thang CHECK (thang BETWEEN 1 AND 12),
    CONSTRAINT chk_bang_luong_nam CHECK (nam BETWEEN 2000 AND 2100),
    CONSTRAINT chk_bang_luong_ngay_cong CHECK (ngay_cong BETWEEN 0 AND 24),
    CONSTRAINT chk_bang_luong_gio_ot CHECK (gio_ot BETWEEN 0 AND 40),
    CONSTRAINT chk_bang_luong_luong_cb CHECK (luong_cb >= 0),
    CONSTRAINT chk_bang_luong_phu_cap CHECK (phu_cap >= 0),
    CONSTRAINT chk_bang_luong_khoan_tru CHECK (
        khoan_tru BETWEEN 0 AND (
            ((luong_cb / 24.0) * ngay_cong) + luong_ot + phu_cap
        )
    ),
    UNIQUE KEY uq_nv_thang_nam (ma_nv, thang, nam),
    KEY idx_bang_luong_nam_thang (nam, thang),
    CONSTRAINT fk_luong_nhanvien FOREIGN KEY (ma_nv) 
        REFERENCES nhan_vien(ma_nv) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Cấu trúc dùng bởi form nhân viên đã được khai báo đầy đủ ngay trong
-- CREATE TABLE nhan_vien, nên bản khởi tạo mới không cần chạy ALTER TABLE.
-- 3. Thêm dữ liệu mẫu cho bảng Người dùng / Tài khoản (nguoi_dung)
INSERT INTO nguoi_dung (id, ten_dang_nhap, mat_khau, ho_ten, email, vai_tro, trang_thai) VALUES
(101, 'NS001',    '123456', 'Nguyễn Thị Hoa',         'hoants@company.com',  'TruongPhong', 1),
(102, 'KT001',    '123456', 'Trần Văn Minh',          'minhkt@company.com',  'NhanVien',    1),
(103, 'KD001',    '123456', 'Lê Hoàng Long',          'longkd@company.com',  'NhanVien',    1),
(104, 'IT001',    '123456', 'Phạm Quốc Anh',          'anhit@company.com',   'NhanVien',    1),
(105, 'MKT001',   '123456', 'Đỗ Phương Thảo',         'thaomkt@company.com', 'TruongPhong', 1),
(106, 'MKT002', '123456', 'Nguyễn Văn Nam', 'nammkt@company.com', 'NhanVien', 1),
(107, 'MKT003', '123456', 'Lê Khánh Linh',  'linhmkt@company.com', 'NhanVien', 1)
AS new_nd
ON DUPLICATE KEY UPDATE ho_ten = new_nd.ho_ten,  vai_tro = new_nd.vai_tro;

-- 4. Thêm dữ liệu mẫu cho bảng Nhân viên (nhan_vien)
INSERT INTO nhan_vien (ma_nv, ho_ten, gioi_tinh, ngay_sinh, ngay_vao_lam, ngay_nghi_viec, sdt, email, ma_phong_ban, ma_chuc_vu, luong_co_ban, trang_thai, nguoi_dung_id) VALUES
('NS001',  'Nguyễn Thị Hoa', 'Nữ',  '1995-05-12', '2018-06-01', NULL, '0901112233', 'hoants@company.com',  'PB02', 'CV01', 12000000.00, 'Đang làm việc', 101),
('KT001',  'Trần Văn Minh',  'Nam', '1998-08-20', '2021-03-15', NULL, '0902223344', 'minhkt@company.com',  'PB05', 'CV03', 10000000.00, 'Đang làm việc', 102),
('KD001',  'Lê Hoàng Long',  'Nam', '1997-03-15', '2020-08-10', NULL, '0903334455', 'longkd@company.com',  'PB04', 'CV03', 11000000.00, 'Đang làm việc', 103),
('IT001',  'Phạm Quốc Anh',  'Nam', '1996-11-05', '2019-04-08', NULL, '0904445566', 'anhit@company.com',   'PB01', 'CV03', 11500000.00, 'Đang làm việc', 104),
('MKT001', 'Đỗ Phương Thảo', 'Nữ',  '1994-09-18', '2017-11-20', NULL, '0905556677', 'thaomkt@company.com', 'PB03', 'CV01', 13000000.00, 'Đang làm việc', 105),
('MKT002', 'Nguyễn Văn Nam', 'Nam', '1998-04-12', '2022-01-05', NULL, '0907778899', 'nammkt@company.com', 'PB03', 'CV03', 10500000.00, 'Đang làm việc', 106),
('MKT003', 'Lê Khánh Linh',  'Nữ',  '2000-09-25', '2023-07-12', NULL, '0908889900', 'linhmkt@company.com', 'PB03', 'CV03', 10000000.00, 'Đang làm việc', 107)
AS new_nv
-- DROP DATABASE IF EXISTS QuanLyNhanVien;
ON DUPLICATE KEY UPDATE
    ho_ten = new_nv.ho_ten,
    ngay_vao_lam = new_nv.ngay_vao_lam,
    ngay_nghi_viec = new_nv.ngay_nghi_viec;

SELECT * FROM nhan_vien;
SELECT * FROM nguoi_dung;