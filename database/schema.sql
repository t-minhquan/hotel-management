IF DB_ID('QLKhachSan') IS NOT NULL
BEGIN
    ALTER DATABASE QLKhachSan SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE QLKhachSan;
END
GO

CREATE DATABASE QLKhachSan;
GO

USE QLKhachSan;
GO

CREATE TABLE NHAN_VIEN (
    MaNV            INT IDENTITY(1,1) PRIMARY KEY,
    HoTen           NVARCHAR(100)   NOT NULL,
    ChucVu          NVARCHAR(50)    NOT NULL
        CHECK (ChucVu IN (N'Quản lý', N'Lễ tân', N'Kế toán', N'Buồng phòng', N'IT')),
    SDT             VARCHAR(15)     NULL,
    Email           NVARCHAR(100)   NULL,
    Username        VARCHAR(50)     NOT NULL UNIQUE,
    PasswordHash    VARCHAR(255)    NOT NULL,
    NgayVaoLam      DATETIME        NOT NULL DEFAULT GETDATE(),
    TrangThai       NVARCHAR(20)    NOT NULL DEFAULT N'Đang làm việc'
);
GO

CREATE TABLE KHACH_HANG (
    MaKH            INT IDENTITY(1,1) PRIMARY KEY,
    HoTen           NVARCHAR(100)   NOT NULL,
    CCCD            VARCHAR(20)     NOT NULL UNIQUE,
    SDT             VARCHAR(15)     NOT NULL,
    Email           NVARCHAR(100)   NULL,
    DiaChi          NVARCHAR(200)   NULL,
    NgayTao         DATETIME        NOT NULL DEFAULT GETDATE()
);
GO

CREATE TABLE PHONG (
    MaPhong         INT IDENTITY(1,1) PRIMARY KEY,
    SoPhong         VARCHAR(10)     NOT NULL UNIQUE,
    LoaiPhong       NVARCHAR(50)    NOT NULL,
    Gia             DECIMAL(18,2)   NOT NULL CHECK (Gia >= 0),
    TinhTrangPhong  NVARCHAR(30)    NOT NULL DEFAULT N'Còn trống'
        CHECK (TinhTrangPhong IN (N'Còn trống', N'Đang sử dụng', N'Đang dọn dẹp', N'Bảo trì'))
);
GO

CREATE TABLE DICH_VU (
    MaDV            INT IDENTITY(1,1) PRIMARY KEY,
    TenDV           NVARCHAR(100)   NOT NULL,
    DonGia          DECIMAL(18,2)   NOT NULL CHECK (DonGia >= 0),
    MoTa            NVARCHAR(200)   NULL
);
GO

CREATE TABLE NHIEM_VU (
    MaNhiemVu       INT IDENTITY(1,1) PRIMARY KEY,
    TenNhiemVu      NVARCHAR(100)   NOT NULL,
    MoTa            NVARCHAR(200)   NULL
);
GO

CREATE TABLE DAT_PHONG (
    MaDatPhong      INT IDENTITY(1,1) PRIMARY KEY,
    MaKH            INT             NOT NULL,
    MaPhong         INT             NOT NULL,
    MaNV            INT             NOT NULL,   -- nhan vien le tan lap phieu
    NgayNhan        DATETIME        NOT NULL,
    NgayTra         DATETIME        NULL,
    TrangThai       NVARCHAR(30)    NOT NULL DEFAULT N'Đã nhận phòng',
    CONSTRAINT FK_DatPhong_KhachHang FOREIGN KEY (MaKH) REFERENCES KHACH_HANG(MaKH),
    CONSTRAINT FK_DatPhong_Phong     FOREIGN KEY (MaPhong) REFERENCES PHONG(MaPhong),
    CONSTRAINT FK_DatPhong_NhanVien  FOREIGN KEY (MaNV) REFERENCES NHAN_VIEN(MaNV),
    CONSTRAINT CK_DatPhong_Ngay CHECK (NgayTra IS NULL OR NgayTra > NgayNhan)
);
GO

CREATE TABLE HOA_DON (
    MaHD            INT IDENTITY(1,1) PRIMARY KEY,
    MaDatPhong      INT             NOT NULL,
    NgayLap         DATETIME        NOT NULL DEFAULT GETDATE(),
    TongSoTien      DECIMAL(18,2)   NOT NULL DEFAULT 0,
    TrangThai       NVARCHAR(30)    NOT NULL DEFAULT N'Chưa thanh toán'
        CHECK (TrangThai IN (N'Chưa thanh toán', N'Đã thanh toán', N'Đã hủy')),
    CONSTRAINT FK_HoaDon_DatPhong FOREIGN KEY (MaDatPhong) REFERENCES DAT_PHONG(MaDatPhong)
);
GO

CREATE TABLE CHI_TIET_DICH_VU (
    MaCTDV          INT IDENTITY(1,1) PRIMARY KEY,
    MaHD            INT             NOT NULL,
    MaDV            INT             NOT NULL,
    SoLuong         INT             NOT NULL CHECK (SoLuong > 0),
    ThanhTien       DECIMAL(18,2)   NOT NULL,
    CONSTRAINT FK_CTDV_HoaDon FOREIGN KEY (MaHD) REFERENCES HOA_DON(MaHD),
    CONSTRAINT FK_CTDV_DichVu FOREIGN KEY (MaDV) REFERENCES DICH_VU(MaDV)
);
GO

CREATE TABLE PHAN_CONG_NHIEM_VU (
    MaPhanCong      INT IDENTITY(1,1) PRIMARY KEY,
    MaNV            INT             NOT NULL,
    MaNhiemVu       INT             NOT NULL,
    MaPhong         INT             NULL,
    NgayPhanCong    DATETIME        NOT NULL DEFAULT GETDATE(),
    GhiChu          NVARCHAR(200)   NULL,
    CONSTRAINT FK_PCNV_NhanVien  FOREIGN KEY (MaNV) REFERENCES NHAN_VIEN(MaNV),
    CONSTRAINT FK_PCNV_NhiemVu   FOREIGN KEY (MaNhiemVu) REFERENCES NHIEM_VU(MaNhiemVu),
    CONSTRAINT FK_PCNV_Phong     FOREIGN KEY (MaPhong) REFERENCES PHONG(MaPhong)
);
GO

/* TRIGGER 1:
   Khi them moi mot dong vao DAT_PHONG -> cap nhat TinhTrangPhong
   trong bang PHONG thanh N'Đang sử dụng'
*/
CREATE TRIGGER trg_DatPhong_CapNhatTinhTrangPhong
ON DAT_PHONG
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE P
    SET P.TinhTrangPhong = N'Đang sử dụng'
    FROM PHONG P
    INNER JOIN inserted I ON P.MaPhong = I.MaPhong;
END
GO

/* TRIGGER 2:
   Khi them du lieu vao CHI_TIET_DICH_VU -> cong don ThanhTien
   vao TongSoTien cua HOA_DON tuong ung
*/
CREATE TRIGGER trg_ChiTietDichVu_CapNhatTongTienHoaDon
ON CHI_TIET_DICH_VU
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE HD
    SET HD.TongSoTien = HD.TongSoTien + X.TongThanhTien
    FROM HOA_DON HD
    INNER JOIN (
        SELECT MaHD, SUM(ThanhTien) AS TongThanhTien
        FROM inserted
        GROUP BY MaHD
    ) X ON HD.MaHD = X.MaHD;
END
GO

-- DU LIEU MAU 
INSERT INTO KHACH_HANG (HoTen, CCCD, SDT, Email, DiaChi)
VALUES 
(N'Tống Minh Quân', '001099123456', '0901234567', 'tongminhquan@hotel.vn', N'Đồng Nai');

INSERT INTO NHAN_VIEN (HoTen, ChucVu, SDT, Email, Username, PasswordHash)
VALUES
(N'Nguyễn Văn Quản', N'Quản lý', '0900000001', 'quanly@hotel.vn', 'quanly', 'Quanly123'),
(N'Trần Thị Lễ',      N'Lễ tân',  '0900000002', 'letan@hotel.vn',  'letan',  'Letan123'),
(N'Lê Văn Kế',        N'Kế toán', '0900000003', 'ketoan@hotel.vn', 'ketoan', 'Kettoan123'),
(N'Phạm Thị Buồng',   N'Buồng phòng', '0900000004', 'buong@hotel.vn', 'buongphong', 'Buongphong123'),
(N'Đỗ Văn IT',        N'IT', '0900000005', 'it@hotel.vn', 'it', 'It123');

INSERT INTO PHONG (SoPhong, LoaiPhong, Gia, TinhTrangPhong)
VALUES
('101', N'Phòng đơn', 300000, N'Còn trống'),
('102', N'Phòng đôi', 500000, N'Còn trống'),
('201', N'VIP',       1200000, N'Còn trống');

INSERT INTO DICH_VU (TenDV, DonGia, MoTa)
VALUES
(N'Giặt ủi', 50000, N'Dịch vụ giặt ủi theo kg'),
(N'Ăn sáng', 80000, N'Buffet sáng'),
(N'Đưa đón sân bay', 250000, N'Xe đưa đón');
GO

INSERT INTO NHIEM_VU (TenNhiemVu, MoTa)
VALUES
(N'Dọn phòng',N'Dọn phòng cho kĩ vô');