# db_config.example.py
# HƯỚNG DẪN CÀI ĐẶT: 
# 1. Đổi tên file này thành db_config.py
# 2. Cập nhật thông số 'server' cho khớp với SQL Server Management Studio (SSMS) trên máy của bạn.

DB_CONFIG = {
    'driver': '{ODBC Driver 17 for SQL Server}', # Có thể đổi thành bản 18, 13 tùy máy
    'server': 'TÊN_MÁY_TÍNH\\SQLEXPRESS',        # VD: localhost\SQLEXPRESS hoặc DESKTOP-ABC\SQLEXPRESS
    'database': 'QLKhachSan',                    # Phải chạy file setup.sql trong SSMS trước
    'trusted_connection': 'yes',                 # Sử dụng Windows Authentication
    'TrustServerCertificate': 'yes'
}
