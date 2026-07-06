# db_config.py
# -----------------------------------------------------------------------
# File cau hinh ket noi den SQL Server, duoc tach rieng khoi app.py
# de tien quan ly va tranh loi ImportError khi khoi dong server.
# -----------------------------------------------------------------------

DB_CONFIG = {
    "DRIVER": "{ODBC Driver 17 for SQL Server}",
    "SERVER": "localhost\\SQLEXPRESS",   # Đổi thành tên Server của bạn (VD: "DESKTOP-ABC\SQLEXPRESS" hoặc "localhost")
    "DATABASE": "QLKhachSan",            # Tên database trong SQL Server của bạn
    "UID": "",                           # Để trống khi dùng Windows Auth
    "PWD": "",                           # Để trống khi dùng Windows Auth
    "TRUSTED_CONNECTION": "yes",         # Bắt buộc là "yes" để dùng Windows Auth
}


def get_connection_string() -> str:
    """
    Xay dung chuoi ket noi pyodbc tu dictionary DB_CONFIG.
    Ham nay luon tra ve string, khong bao gio None,
    de tranh loi khi app.py import va goi ham nay.
    """
    if DB_CONFIG.get("TRUSTED_CONNECTION", "no").lower() == "yes":
        conn_str = (
            f"DRIVER={DB_CONFIG['DRIVER']};"
            f"SERVER={DB_CONFIG['SERVER']};"
            f"DATABASE={DB_CONFIG['DATABASE']};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={DB_CONFIG['DRIVER']};"
            f"SERVER={DB_CONFIG['SERVER']};"
            f"DATABASE={DB_CONFIG['DATABASE']};"
            f"UID={DB_CONFIG['UID']};"
            f"PWD={DB_CONFIG['PWD']};"
        )
    return conn_str


# Cau hinh secret key cho Flask session (doi khi len production)
FLASK_SECRET_KEY = "hotel-management-secret-key-2026"