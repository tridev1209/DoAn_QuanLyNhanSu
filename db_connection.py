import mysql.connector
from mysql.connector import Error
from tkinter import messagebox
# Cấu hình thông số kết nối MySQL (chỉnh sửa password nếu MySQL của bạn có thiết lập)


def get_db_connection():
    """Tạo kết nối tới cơ sở dữ liệu MySQL"""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port = 3306,
            database="QuanLyNhanVien",  # Tên database trên MySQL Workbench của bạn
            user="root",  # Tên đăng nhập MySQL (mặc định là root)
            password="Zalo@123",  # Điền mật khẩu MySQL của bạn vào đây (nếu để trống thì giữ nguyên chuỗi rỗng '')
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Lỗi kết nối MySQL: {e}")
        return None
# Kiểm tra MySQL trước khi đụng vào các form
# if __name__ == "__main__":
#     conn = get_db_connection()

#     if conn:
#         print("Kết nối MySQL thành công!")
#         conn.close()
#     else:
#         print("Kết nối MySQL thất bại!")
