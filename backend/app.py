# Backend Flask cho He thong Quan ly Khach san
import functools
from datetime import datetime

import pyodbc
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify
)

# Import cau hinh ket noi tu file rieng db_config.py
# (dat cung thu muc voi app.py de tranh ImportError)
from db_config import get_connection_string, FLASK_SECRET_KEY

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY


# HAM TIEN ICH: KET NOI DATABASE
def get_db_connection():
    """Mo mot ket noi moi toi SQL Server. Dong sau khi dung xong."""
    conn_str = get_connection_string()
    return pyodbc.connect(conn_str)


def query(sql, params=(), fetch=True, commit=False):
    """Ham dung chung de chay cau lenh SQL, tra ve list of dict."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params)

    result = None
    if fetch:
        columns = [col[0] for col in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]

    if commit:
        conn.commit()

    cursor.close()
    conn.close()
    return result


# RBAC (ROLE-BASED ACCESS CONTROL)
# Dinh nghia quyen han theo tung chuc vu (Đã cập nhật các quyền dịch vụ và nhiệm vụ)
ROLE_PERMISSIONS = {
    "Quản lý":       {"view_revenue", "delete_invoice", "create_booking", "create_invoice", 
                       "update_invoice", "manage_staff", "view_customers", "view_room_status",
                       "view_service", "view_task", "update_service", "create_service", "delete_service", "manage_task"},
    "Lễ tân":        {"create_booking", "create_invoice", "update_invoice", "view_customers", 
                       "view_service", "view_room_status"},
    "Kế toán":       {"view_revenue", "create_invoice", "update_invoice", "view_customers", 
                       "view_service", "view_room_status", "create_booking"},
    "Buồng phòng":   {"view_room_status", "view_task"},
    "IT":            {"manage_staff", "view_customers", "view_task", "manage_task"},
}


def login_required(view_func):
    @functools.wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập để tiếp tục.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


def permission_required(permission):
    """Decorator chan quyen truy cap dua tren ChucVu cua nhan vien dang dang nhap."""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Vui lòng đăng nhập để tiếp tục.", "warning")
                return redirect(url_for("login"))

            role = session.get("role")
            allowed = ROLE_PERMISSIONS.get(role, set())

            if permission not in allowed:
                flash(f"Chức vụ '{role}' không có quyền thực hiện thao tác này.", "danger")
                return redirect(url_for("dashboard"))

            return view_func(*args, **kwargs)
        return wrapped
    return decorator


# ROUTE: DANG NHAP / DANG XUAT
@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        rows = query(
            "SELECT MaNV, HoTen, ChucVu, PasswordHash FROM NHAN_VIEN WHERE Username = ?",
            (username,)
        )

        # Luu y: day la vi du don gian, thuc te nen dung check_password_hash
        if rows and rows[0]["PasswordHash"] is not None:
            user = rows[0]
            session["user_id"] = user["MaNV"]
            session["hoten"] = user["HoTen"]
            session["role"] = user["ChucVu"]
            flash(f"Chào mừng {user['HoTen']} ({user['ChucVu']})!", "success")
            return redirect(url_for("dashboard"))

        flash("Sai tài khoản hoặc mật khẩu.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("login"))


# ROUTE: DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", role=session.get("role"))


# ROUTE: DANH SACH KHACH HANG
@app.route("/khach-hang")
@permission_required("view_customers")
def danh_sach_khach_hang():
    khach_hang_list = query("SELECT * FROM KHACH_HANG ORDER BY MaKH DESC")
    return render_template(
        "khach_hang_list.html",
        khach_hang_list=khach_hang_list,
        role=session.get("role")
    )


@app.route("/khach-hang/them", methods=["GET", "POST"])
@permission_required("view_customers")
def them_khach_hang():
    if request.method == "POST":
        hoten = request.form.get("hoten")
        cccd = request.form.get("cccd")
        sdt = request.form.get("sdt")
        email = request.form.get("email")
        diachi = request.form.get("diachi")

        query(
            """INSERT INTO KHACH_HANG (HoTen, CCCD, SDT, Email, DiaChi)
               VALUES (?, ?, ?, ?, ?)""",
            (hoten, cccd, sdt, email, diachi),
            fetch=False, commit=True
        )
        flash("Thêm khách hàng thành công.", "success")
        return redirect(url_for("danh_sach_khach_hang"))

    return render_template("khach_hang_form.html", role=session.get("role"))


# ROUTE: DAT PHONG
@app.route("/dat-phong", methods=["GET", "POST"])
@permission_required("create_booking")
def dat_phong():
    if request.method == "POST":
        ma_kh = request.form.get("ma_kh")
        ma_phong = request.form.get("ma_phong")
        ngay_nhan_raw = request.form.get("ngay_nhan")
        if ngay_nhan_raw:
            # Input datetime-local tra ve dang "2026-07-04T10:30" -> chuyen thanh datetime object
            ngay_nhan = datetime.strptime(ngay_nhan_raw, "%Y-%m-%dT%H:%M")
        else:
            ngay_nhan = datetime.now()

        query(
            """INSERT INTO DAT_PHONG (MaKH, MaPhong, MaNV, NgayNhan)
               VALUES (?, ?, ?, ?)""",
            (ma_kh, ma_phong, session["user_id"], ngay_nhan),
            fetch=False, commit=True
        )
        # Trigger trg_DatPhong_CapNhatTinhTrangPhong se tu dong cap nhat PHONG
        flash("Đặt phòng thành công. Phòng đã chuyển sang trạng thái 'Đang sử dụng'.", "success")
        return redirect(url_for("dat_phong"))

    khach_hang_list = query("SELECT MaKH, HoTen FROM KHACH_HANG ORDER BY HoTen")
    phong_trong = query("SELECT MaPhong, SoPhong, LoaiPhong, Gia FROM PHONG WHERE TinhTrangPhong = N'Còn trống'")
    danh_sach_dat_phong = query("""
        SELECT DP.MaDatPhong, KH.HoTen AS TenKH, P.SoPhong, DP.NgayNhan, DP.NgayTra, DP.TrangThai
        FROM DAT_PHONG DP
        JOIN KHACH_HANG KH ON DP.MaKH = KH.MaKH
        JOIN PHONG P ON DP.MaPhong = P.MaPhong
        ORDER BY DP.MaDatPhong DESC
    """)

    return render_template(
        "dat_phong_form.html",
        khach_hang_list=khach_hang_list,
        phong_trong=phong_trong,
        danh_sach_dat_phong=danh_sach_dat_phong,
        role=session.get("role")
    )


# ROUTE: LAP HOA DON
@app.route("/hoa-don", methods=["GET"])
@permission_required("create_invoice")
def danh_sach_hoa_don():
    hoa_don_list = query("""
        SELECT HD.MaHD, HD.NgayLap, HD.TongSoTien, HD.TrangThai,
               KH.HoTen AS TenKH, P.SoPhong
        FROM HOA_DON HD
        JOIN DAT_PHONG DP ON HD.MaDatPhong = DP.MaDatPhong
        JOIN KHACH_HANG KH ON DP.MaKH = KH.MaKH
        JOIN PHONG P ON DP.MaPhong = P.MaPhong
        ORDER BY HD.MaHD DESC
    """)
    # Lấy danh sách dịch vụ để sinh option cho select mã dịch vụ
    dich_vu_list = query("SELECT MaDV FROM DICH_VU ORDER BY MaDV")
    return render_template("hoa_don_list.html", hoa_don_list=hoa_don_list, dich_vu_list=dich_vu_list, role=session.get("role"))


@app.route("/hoa-don/lap/<int:ma_dat_phong>", methods=["GET", "POST"])
@permission_required("create_invoice")
def lap_hoa_don(ma_dat_phong):
    if request.method == "POST":
        query(
            "INSERT INTO HOA_DON (MaDatPhong, TongSoTien) VALUES (?, 0)",
            (ma_dat_phong,), fetch=False, commit=True
        )
        flash("Lập hóa đơn thành công.", "success")
        return redirect(url_for("danh_sach_hoa_don"))

    return render_template("hoa_don_form.html", ma_dat_phong=ma_dat_phong, role=session.get("role"))


@app.route("/hoa-don/<int:ma_hd>/them-dich-vu", methods=["POST"])
@permission_required("create_invoice")
def them_dich_vu_vao_hoa_don(ma_hd):
    ma_dv = request.form.get("ma_dv")
    so_luong = int(request.form.get("so_luong", 1))

    don_gia_row = query("SELECT DonGia FROM DICH_VU WHERE MaDV = ?", (ma_dv,))
    don_gia = don_gia_row[0]["DonGia"] if don_gia_row else 0
    thanh_tien = float(don_gia) * so_luong

    query(
        """INSERT INTO CHI_TIET_DICH_VU (MaHD, MaDV, SoLuong, ThanhTien)
           VALUES (?, ?, ?, ?)""",
        (ma_hd, ma_dv, so_luong, thanh_tien),
        fetch=False, commit=True
    )
    # Trigger trg_ChiTietDichVu_CapNhatTongTienHoaDon se tu cong don vao HOA_DON
    flash("Đã thêm dịch vụ vào hóa đơn.", "success")
    return redirect(url_for("danh_sach_hoa_don"))


@app.route("/thanh-toan-hoa-don/<int:ma_hd>")
@permission_required("update_invoice")
def thanh_toan_hoa_don(ma_hd):
    sql_update = """
        UPDATE HOA_DON 
        SET TrangThai = N'Đã thanh toán' 
        WHERE MaHD = ? AND TrangThai = N'Chưa thanh toán'
    """
    try:
        query(sql_update, (ma_hd,), fetch=False, commit=True)
        flash("Thanh toán hóa đơn thành công!", "success")
    except Exception as e:
        flash(f"Lỗi khi thanh toán: {e}", "danger")
        
    return redirect(url_for("danh_sach_hoa_don"))


@app.route("/hoa-don/<int:ma_hd>/xoa", methods=["POST"])
@permission_required("delete_invoice")
def xoa_hoa_don(ma_hd):
    query("DELETE FROM CHI_TIET_DICH_VU WHERE MaHD = ?", (ma_hd,), fetch=False, commit=True)
    query("DELETE FROM HOA_DON WHERE MaHD = ?", (ma_hd,), fetch=False, commit=True)
    flash("Đã xóa hóa đơn.", "success")
    return redirect(url_for("danh_sach_hoa_don"))


# 1. QUẢN LÝ DỊCH VỤ (Ăn sáng, Giặt ủi...)
@app.route("/dich-vu")
@permission_required("view_service")
def danh_sach_dich_vu():
    sql = "SELECT * FROM DICH_VU"
    dich_vu_list = query(sql)
    # Đã truyền thêm role để đồng bộ giao diện hiển thị sidebar/navbar
    return render_template("dich_vu_list.html", dich_vu_list=dich_vu_list, role=session.get("role"))


@app.route("/dich-vu/sua/<int:ma_dv>", methods=["GET", "POST"])
@permission_required("update_service")
def sua_dich_vu(ma_dv):
    if request.method == "POST":
        ten_dv = request.form.get("ten_dv")
        don_gia = request.form.get("don_gia")
        mo_ta = request.form.get("mo_ta")

        # Thực thi câu lệnh UPDATE vào DB
        query(
            "UPDATE DICH_VU SET TenDV = ?, DonGia = ?, MoTa = ? WHERE MaDV = ?",
            (ten_dv, don_gia, mo_ta, ma_dv),
            fetch=False, commit=True
        )
        flash("Cập nhật thông tin dịch vụ thành công.", "success")
        return redirect(url_for("danh_sach_dich_vu"))

    # Dành cho phương thức GET: Lấy dữ liệu cũ để hiển thị lên Form
    dich_vu_row = query("SELECT * FROM DICH_VU WHERE MaDV = ?", (ma_dv,))
    
    if not dich_vu_row:
        flash("Không tìm thấy dịch vụ này.", "danger")
        return redirect(url_for("danh_sach_dich_vu"))

    return render_template("dich_vu_form.html", dich_vu=dich_vu_row[0], role=session.get("role"))

@app.route("/dich-vu/them", methods=["GET", "POST"])
@permission_required("create_service")
def them_dich_vu():
    if request.method == "POST":
        ten_dv = request.form.get("ten_dv")
        don_gia = request.form.get("don_gia")
        mo_ta = request.form.get("mo_ta")

        # Thực thi câu lệnh INSERT vào DB
        query(
            "INSERT INTO DICH_VU (TenDV, DonGia, MoTa) VALUES (?, ?, ?)",
            (ten_dv, don_gia, mo_ta),
            fetch=False, commit=True
        )
        flash("Thêm dịch vụ mới thành công.", "success")
        return redirect(url_for("danh_sach_dich_vu"))

    return render_template("dich_vu_add.html", role=session.get("role"))

@app.route("/dich-vu/xoa/<int:ma_dv>", methods=["POST"])
@permission_required("delete_service")
def xoa_dich_vu(ma_dv):
    try:
        # Thử xóa dịch vụ khỏi CSDL
        query("DELETE FROM DICH_VU WHERE MaDV = ?", (ma_dv,), fetch=False, commit=True)
        flash("Đã xóa dịch vụ thành công.", "success")
    except Exception as e:
        # Nếu dịch vụ đã nằm trong hóa đơn, MSSQL sẽ chặn lại. Bắt lỗi tại đây:
        flash("Không thể xóa dịch vụ này vì đã được sử dụng trong hóa đơn khách hàng.", "danger")
        
    return redirect(url_for("danh_sach_dich_vu"))

# 2. QUẢN LÝ & PHÂN CÔNG NHIỆM VỤ
@app.route("/nhiem-vu")
@permission_required("view_task") 
def danh_sach_nhiem_vu():
    role = session.get("role")
    ma_nv = session.get("user_id")
    
    if role in ['Quản lý', 'IT']:
        sql = """
            SELECT PC.MaPhanCong, NV.HoTen, N.TenNhiemVu, PC.NgayPhanCong, PC.GhiChu, P.SoPhong 
            FROM PHAN_CONG_NHIEM_VU PC
            INNER JOIN NHAN_VIEN NV ON PC.MaNV = NV.MaNV
            INNER JOIN NHIEM_VU N ON PC.MaNhiemVu = N.MaNhiemVu
            LEFT JOIN PHONG P ON PC.MaPhong = P.MaPhong
        """
        nhiem_vu_list = query(sql)
    else: # Buồng phòng
        sql = """
            SELECT PC.MaPhanCong, NV.HoTen, N.TenNhiemVu, PC.NgayPhanCong, PC.GhiChu, P.SoPhong 
            FROM PHAN_CONG_NHIEM_VU PC
            INNER JOIN NHAN_VIEN NV ON PC.MaNV = NV.MaNV
            INNER JOIN NHIEM_VU N ON PC.MaNhiemVu = N.MaNhiemVu
            LEFT JOIN PHONG P ON PC.MaPhong = P.MaPhong
            WHERE PC.MaNV = ?
        """
        nhiem_vu_list = query(sql, (ma_nv,))
        
    # Đã truyền thêm role để đồng bộ giao diện hiển thị sidebar/navbar
    return render_template("nhiem_vu_list.html", nhiem_vu_list=nhiem_vu_list, role=role)

# ROUTE: THÊM PHÂN CÔNG NHIỆM VỤ
@app.route("/nhiem-vu/them", methods=["GET", "POST"])
@permission_required("manage_task")
def them_phan_cong():
    if request.method == "POST":
        ma_nv = request.form.get("ma_nv")
        ma_nhiem_vu = request.form.get("ma_nhiem_vu")
        ma_phong = request.form.get("ma_phong") or None  # Có thể null
        ghi_chu = request.form.get("ghi_chu")

        query("""
            INSERT INTO PHAN_CONG_NHIEM_VU (MaNV, MaNhiemVu, MaPhong, GhiChu)
            VALUES (?, ?, ?, ?)
        """, (ma_nv, ma_nhiem_vu, ma_phong, ghi_chu), fetch=False, commit=True)
        flash("Phân công nhiệm vụ mới thành công.", "success")
        return redirect(url_for("danh_sach_nhiem_vu"))

    # Lấy dữ liệu cho các thẻ <select>
    nhan_vien_list = query("SELECT MaNV, HoTen, ChucVu FROM NHAN_VIEN WHERE TrangThai = N'Đang làm việc'")
    danh_muc_nhiem_vu = query("SELECT MaNhiemVu, TenNhiemVu FROM NHIEM_VU")
    phong_list = query("SELECT MaPhong, SoPhong FROM PHONG")

    return render_template("nhiem_vu_form.html", action="Them", 
                           nhan_vien_list=nhan_vien_list, danh_muc_nhiem_vu=danh_muc_nhiem_vu, 
                           phong_list=phong_list, role=session.get("role"))

# ROUTE: SỬA PHÂN CÔNG NHIỆM VỤ
@app.route("/nhiem-vu/sua/<int:ma_pc>", methods=["GET", "POST"])
@permission_required("manage_task")
def sua_phan_cong(ma_pc):
    if request.method == "POST":
        ma_nv = request.form.get("ma_nv")
        ma_nhiem_vu = request.form.get("ma_nhiem_vu")
        ma_phong = request.form.get("ma_phong") or None
        ghi_chu = request.form.get("ghi_chu")

        query("""
            UPDATE PHAN_CONG_NHIEM_VU 
            SET MaNV = ?, MaNhiemVu = ?, MaPhong = ?, GhiChu = ?
            WHERE MaPhanCong = ?
        """, (ma_nv, ma_nhiem_vu, ma_phong, ghi_chu, ma_pc), fetch=False, commit=True)
        flash("Cập nhật phân công thành công.", "success")
        return redirect(url_for("danh_sach_nhiem_vu"))

    phan_cong_row = query("SELECT * FROM PHAN_CONG_NHIEM_VU WHERE MaPhanCong = ?", (ma_pc,))
    if not phan_cong_row:
        flash("Không tìm thấy phân công.", "danger")
        return redirect(url_for("danh_sach_nhiem_vu"))

    nhan_vien_list = query("SELECT MaNV, HoTen, ChucVu FROM NHAN_VIEN WHERE TrangThai = N'Đang làm việc'")
    danh_muc_nhiem_vu = query("SELECT MaNhiemVu, TenNhiemVu FROM NHIEM_VU")
    phong_list = query("SELECT MaPhong, SoPhong FROM PHONG")

    return render_template("nhiem_vu_form.html", action="Sua", phan_cong=phan_cong_row[0], 
                           nhan_vien_list=nhan_vien_list, danh_muc_nhiem_vu=danh_muc_nhiem_vu, 
                           phong_list=phong_list, role=session.get("role"))

# ROUTE: XÓA PHÂN CÔNG NHIỆM VỤ
@app.route("/nhiem-vu/xoa/<int:ma_pc>", methods=["POST"])
@permission_required("manage_task")
def xoa_phan_cong(ma_pc):
    query("DELETE FROM PHAN_CONG_NHIEM_VU WHERE MaPhanCong = ?", (ma_pc,), fetch=False, commit=True)
    flash("Đã xóa phân công nhiệm vụ.", "success")
    return redirect(url_for("danh_sach_nhiem_vu"))

@app.route("/danh-muc-nhiem-vu/them", methods=["GET", "POST"])
@permission_required("manage_task")
def them_danh_muc_nhiem_vu():
    if request.method == "POST":
        ten_nhiem_vu = request.form.get("ten_nhiem_vu")
        mo_ta = request.form.get("mo_ta")

        query("""
            INSERT INTO NHIEM_VU (TenNhiemVu, MoTa)
            VALUES (?, ?)
        """, (ten_nhiem_vu, mo_ta), fetch=False, commit=True)
        
        flash("Đã thêm đầu mục công việc mới vào hệ thống.", "success")
        return redirect(url_for("danh_sach_nhiem_vu"))

    return render_template("danh_muc_nhiem_vu_form.html", role=session.get("role"))

# ROUTE: DOANH THU (chi Quan ly / Ke toan duoc xem)
@app.route("/doanh-thu")
@permission_required("view_revenue")
def doanh_thu():
    tong_doanh_thu = query("""
        SELECT ISNULL(SUM(TongSoTien), 0) AS TongDoanhThu
        FROM HOA_DON
        WHERE TrangThai = N'Đã thanh toán'
    """)
    return render_template("doanh_thu.html", tong_doanh_thu=tong_doanh_thu[0], role=session.get("role"))


# ROUTE: TINH TRANG PHONG (Buong phong duoc xem)
@app.route("/tinh-trang-phong")
@permission_required("view_room_status")
def tinh_trang_phong():
    phong_list = query("SELECT * FROM PHONG ORDER BY SoPhong")
    return render_template("tinh_trang_phong.html", phong_list=phong_list, role=session.get("role"))

# ROUTE: NHAN VIEN
@app.route("/nhan-vien")
@permission_required("manage_staff") 
def danh_sach_nhan_vien():
    sql = """
        SELECT MaNV, HoTen, ChucVu, SDT, Email, Username, NgayVaoLam, TrangThai 
        FROM NHAN_VIEN
    """
    nhan_vien_list = query(sql)
    
    return render_template("nhan_vien_list.html", nhan_vien_list=nhan_vien_list, role=session.get("role"))

# ROUTE: THÊM NHÂN VIÊN
@app.route("/nhan-vien/them", methods=["GET", "POST"])
@permission_required("manage_staff")
def them_nhan_vien():
    if request.method == "POST":
        hoten = request.form.get("hoten")
        chucvu = request.form.get("chucvu")
        sdt = request.form.get("sdt")
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            query("""
                INSERT INTO NHAN_VIEN (HoTen, ChucVu, SDT, Email, Username, PasswordHash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (hoten, chucvu, sdt, email, username, password), fetch=False, commit=True)
            flash("Thêm nhân viên mới thành công.", "success")
            return redirect(url_for("danh_sach_nhan_vien"))
        except Exception as e:
            flash("Lỗi: Tên đăng nhập (Username) đã tồn tại hoặc dữ liệu không hợp lệ.", "danger")

    return render_template("nhan_vien_form.html", action="Them", role=session.get("role"))

# ROUTE: SỬA NHÂN VIÊN
@app.route("/nhan-vien/sua/<int:ma_nv>", methods=["GET", "POST"])
@permission_required("manage_staff")
def sua_nhan_vien(ma_nv):
    if request.method == "POST":
        hoten = request.form.get("hoten")
        chucvu = request.form.get("chucvu")
        sdt = request.form.get("sdt")
        email = request.form.get("email")
        trangthai = request.form.get("trangthai")

        query("""
            UPDATE NHAN_VIEN 
            SET HoTen = ?, ChucVu = ?, SDT = ?, Email = ?, TrangThai = ?
            WHERE MaNV = ?
        """, (hoten, chucvu, sdt, email, trangthai, ma_nv), fetch=False, commit=True)
        flash("Cập nhật thông tin nhân viên thành công.", "success")
        return redirect(url_for("danh_sach_nhan_vien"))

    nhan_vien_row = query("SELECT * FROM NHAN_VIEN WHERE MaNV = ?", (ma_nv,))
    if not nhan_vien_row:
        flash("Không tìm thấy nhân viên này.", "danger")
        return redirect(url_for("danh_sach_nhan_vien"))

    return render_template("nhan_vien_form.html", action="Sua", nv=nhan_vien_row[0], role=session.get("role"))

# ROUTE: XÓA NHÂN VIÊN
@app.route("/nhan-vien/xoa/<int:ma_nv>", methods=["POST"])
@permission_required("manage_staff")
def xoa_nhan_vien(ma_nv):
    # Chống tự hủy: Không cho phép tự xóa tài khoản của chính mình đang đăng nhập
    if ma_nv == session.get("user_id"):
        flash("Bạn không thể tự xóa tài khoản của chính mình!", "danger")
        return redirect(url_for("danh_sach_nhan_vien"))

    try:
        query("DELETE FROM NHAN_VIEN WHERE MaNV = ?", (ma_nv,), fetch=False, commit=True)
        flash("Đã xóa nhân viên khỏi hệ thống.", "success")
    except Exception as e:
        flash("Nhân viên này đã có dữ liệu lịch sử (Đặt phòng, Nhiệm vụ...). Hãy dùng chức năng Sửa để đổi trạng thái thành 'Đã nghỉ' thay vì xóa hẳn.", "warning")

    return redirect(url_for("danh_sach_nhan_vien"))

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
