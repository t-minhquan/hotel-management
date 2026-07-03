# Hệ Thống Quản Lý Khách Sạn (Hotel Management System) 🏨

Đây là mã nguồn dự án xây dựng Hệ thống thông tin Quản lý Khách sạn, thuộc Đồ án môn học Phân tích Thiết kế Hệ thống - Trường Đại học Giao thông Vận tải TP.HCM (UTH). 

Hệ thống được thiết kế theo tiêu chuẩn Chuẩn hóa 3NF, tích hợp Triggers tự động hóa nghiệp vụ và giao diện Web quản lý trực quan.

## 🛠 Công nghệ sử dụng
* **Backend:** Python (Flask Framework)
* **Database:** Hệ quản trị Cơ sở dữ liệu Microsoft SQL Server (MSSQL)
* **Frontend:** HTML5, CSS3, Jinja2 Template
* **Thư viện giao tiếp:** `pyodbc`

## 📂 Cấu trúc thư mục
```text
hotel-management/
├── database/          
│   └── setup.sql           # Script khởi tạo Database, Bảng và Triggers (SSMS)
├── static/                 # Chứa file CSS, JS, Hình ảnh
├── templates/              # Chứa các giao diện HTML (base, login, dashboard...)
├── app.py                  # File khởi chạy server chính
├── db_config.example.py    # File cấu hình Database mẫu
└── requirements.txt        # Danh sách thư viện môi trường
