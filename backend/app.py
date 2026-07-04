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
                       "view_service", "view_task", "update_service"},
    "Lễ tân":        {"create_booking", "create_invoice", "update_invoice", "view_customers", 
                       "view_service", "view_room_status"},
    "Kế toán":       {"view_revenue", "create_invoice", "update_invoice", "view_customers", 
                       "view_service", "view_room_status", "create_booking"},
    "Buồng phòng":   {"view_room_status", "view_task"},
    "IT":            {"manage_staff", "view_customers", "view_task"},
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
    return render_template("hoa_don_list.html", hoa_don_list=hoa_don_list, role=session.get("role"))


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


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
