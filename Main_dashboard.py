import hashlib
import tkinter as tk
from tkinter import messagebox, ttk
from db_connection import get_db_connection
from mysql.connector import Error



def init_db():
    """Tự động khởi tạo bảng nguoi_dung và dữ liệu mẫu với mật khẩu dạng chữ"""
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nguoi_dung (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ten_dang_nhap VARCHAR(50) NOT NULL UNIQUE,
                mat_khau VARCHAR(100) NOT NULL,
                ho_ten VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                vai_tro ENUM('Admin', 'TruongPhong', 'NhanVien') NOT NULL DEFAULT 'NhanVien',
                trang_thai TINYINT(1) DEFAULT 1,
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)

      
    except Error as e:
        print(f"Lỗi khởi tạo CSDL: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
# ==============================================================================
# CỬA SỔ QUÊN MẬT KHẨU
# ==============================================================================
class ForgotPasswordWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Khôi phục & Đổi mật khẩu")
        self.geometry("400x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.var_user = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_new_pw = tk.StringVar()
        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self, padx=25, pady=20, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="KHÔI PHỤC MẬT KHẨU", font=("Helvetica", 13, "bold"), fg="#1e293b", bg="#ffffff").pack(pady=(0, 15))
        tk.Label(frame, text="Tên đăng nhập:", font=("Helvetica", 9, "bold"), bg="#ffffff", fg="#334155", anchor="w").pack(fill=tk.X, pady=(2, 2))
        ttk.Entry(frame, textvariable=self.var_user, font=("Helvetica", 10)).pack(fill=tk.X, ipady=3, pady=(0, 10))

        tk.Label(frame, text="Email đăng ký:", font=("Helvetica", 9, "bold"), bg="#ffffff", fg="#334155", anchor="w").pack(fill=tk.X, pady=(2, 2))
        ttk.Entry(frame, textvariable=self.var_email, font=("Helvetica", 10)).pack(fill=tk.X, ipady=3, pady=(0, 10))

        tk.Label(frame, text="Mật khẩu mới:", font=("Helvetica", 9, "bold"), bg="#ffffff", fg="#334155", anchor="w").pack(fill=tk.X, pady=(2, 2))
        ttk.Entry(frame, textvariable=self.var_new_pw, show="•", font=("Helvetica", 10)).pack(fill=tk.X, ipady=3, pady=(0, 15))

        btn_reset = tk.Button(frame, text="CẬP NHẬT MẬT KHẨU", bg="#2563eb", fg="white", font=("Helvetica", 10, "bold"), bd=0, cursor="hand2", command=self.save_new_password_to_db)
        btn_reset.pack(fill=tk.X, ipady=6)

    def save_new_password_to_db(self):
        user = self.var_user.get().strip()
        email = self.var_email.get().strip()
        new_pw = self.var_new_pw.get().strip()

        if not user or not email or not new_pw:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ thông tin!", parent=self)
            return

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id FROM nguoi_dung WHERE ten_dang_nhap = %s AND email = %s", (user, email))
                row = cursor.fetchone()
                if row:
                    # Lưu trực tiếp chuỗi new_pw xuống CSDL
                    cursor.execute("UPDATE nguoi_dung SET mat_khau = %s WHERE id = %s", (new_pw, row["id"]))
                    conn.commit()
                    messagebox.showinfo("Thành công", f"Đổi mật khẩu thành công!\nMật khẩu mới là: {new_pw}", parent=self)
                    self.destroy()
                else:
                    messagebox.showerror("Lỗi", "Tên đăng nhập hoặc Email không chính xác!", parent=self)
            except Error as e:
                messagebox.showerror("Lỗi CSDL", f"{e}", parent=self)
            finally:
                conn.close()

# ==============================================================================
# FORM ĐĂNG NHẬP
# ==============================================================================
class LoginForm:
    def __init__(self, root):
        self.root = root
        self.root.title("ĐĂNG NHẬP HỆ THỐNG QUẢN LÝ NHÂN SỰ")
        self.root.geometry("450x440")
        self.root.resizable(False, False)
        self.user_info = None

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (450 // 2)
        y = (screen_height // 2) - (440 // 2)
        self.root.geometry(f"450x440+{x}+{y}")

        self.var_username = tk.StringVar()
        self.var_password = tk.StringVar()
        self.var_show_pw = tk.BooleanVar(value=False)
        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg="#f4f6f9", padx=30, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="ĐĂNG NHẬP", font=("Helvetica", 18, "bold"), fg="#1e293b", bg="#f4f6f9").pack(pady=(0, 5))
        tk.Label(main_frame, text="Hệ thống Quản lý Nhân sự - MySQL", font=("Helvetica", 10, "italic"), fg="#64748b", bg="#f4f6f9").pack(pady=(0, 15))

        tk.Label(main_frame, text="Tên đăng nhập:", font=("Helvetica", 10, "bold"), fg="#334155", bg="#f4f6f9", anchor="w").pack(fill=tk.X, pady=(5, 2))
        self.entry_user = ttk.Entry(main_frame, textvariable=self.var_username, font=("Helvetica", 11))
        self.entry_user.pack(fill=tk.X, ipady=4, pady=(0, 12))
        self.entry_user.focus()

        tk.Label(main_frame, text="Mật khẩu:", font=("Helvetica", 10, "bold"), fg="#334155", bg="#f4f6f9", anchor="w").pack(fill=tk.X, pady=(5, 2))
        self.entry_pw = ttk.Entry(main_frame, textvariable=self.var_password, show="•", font=("Helvetica", 11))
        self.entry_pw.pack(fill=tk.X, ipady=4, pady=(0, 5))

        self.entry_pw.bind("<Return>", lambda event: self.handle_login())
        self.entry_user.bind("<Return>", lambda event: self.entry_pw.focus())

        sub_frame = tk.Frame(main_frame, bg="#f4f6f9")
        sub_frame.pack(fill=tk.X, pady=(0, 15))

        tk.Checkbutton(sub_frame, text="Hiện mật khẩu", variable=self.var_show_pw, command=lambda: self.entry_pw.config(show="" if self.var_show_pw.get() else "•"), bg="#f4f6f9", font=("Helvetica", 9), fg="#475569").pack(side=tk.LEFT)

        btn_forgot = tk.Label(sub_frame, text="Quên mật khẩu?", font=("Helvetica", 9, "underline"), fg="#2563eb", bg="#f4f6f9", cursor="hand2")
        btn_forgot.pack(side=tk.RIGHT)
        btn_forgot.bind("<Button-1>", lambda e: ForgotPasswordWindow(self.root))

        tk.Button(main_frame, text="ĐĂNG NHẬP", font=("Helvetica", 11, "bold"), bg="#2563eb", fg="white", bd=0, cursor="hand2", command=self.handle_login).pack(fill=tk.X, ipady=6)

    def handle_login(self):
        username = self.var_username.get().strip()
        password = self.var_password.get().strip()

        if not username or not password:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ thông tin!")
            return

        conn = get_db_connection()
        if not conn:
            messagebox.showerror("Lỗi", "Không thể kết nối CSDL MySQL!")
            return

        try:
            cursor = conn.cursor(dictionary=True)
            # So sánh trực tiếp password với CSDL
            cursor.execute("SELECT id, ten_dang_nhap, ho_ten, email, vai_tro, trang_thai FROM nguoi_dung WHERE ten_dang_nhap = %s AND mat_khau = %s", (username, password))
            row = cursor.fetchone()

            if row:
                if row["trang_thai"] == 0:
                    messagebox.showerror("Lỗi", "Tài khoản đã bị khóa!")
                    return
                self.user_info = row
                self.root.destroy()
            else:
                messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu!")
        except Error as e:
            messagebox.showerror("Lỗi", f"{e}")
        finally:
            conn.close()

# ==============================================================================
# MAIN DASHBOARD (GIAO DIỆN CHÍNH GỒM HEADER + SIDEBAR)
# ==============================================================================
class MainDashboardApp:
    def __init__(self, root, user_info):
        self.root = root
        self.user_info = user_info

        role_names = {"Admin": "Quản Trị Viên", "TruongPhong": "Trưởng Phòng", "NhanVien": "Nhân Viên"}
        role_display = role_names.get(user_info['vai_tro'], user_info['vai_tro'])

        self.root.title(f"HỆ THỐNG QUẢN LÝ NHÂN SỰ - [{user_info['ho_ten']} ({role_display})]")
        self.root.geometry("1450x680")
        self.root.minsize(1000, 600)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.create_layout()

        # Hiển thị mặc định form đầu tiên tùy thuộc vào phân quyền
        if self.user_info["vai_tro"] == "NhanVien":
            self.show_profile_form()
        else:
            self.show_employee_form()

    def get_role_name(self, role):
        return {"Admin": "Quản Trị Viên", "TruongPhong": "Trưởng Phòng", "NhanVien": "Nhân Viên"}.get(role, role)

    def create_layout(self):
        # --- TOP HEADER BAR ---
        top_bar = tk.Frame(self.root, bg="#0f172a", height=50)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top_bar, text="🏢 HỆ THỐNG QUẢN LÝ NHÂN SỰ", font=("Helvetica", 13, "bold"), fg="#38bdf8", bg="#0f172a", padx=15).pack(side=tk.LEFT)

        user_desc = f"👤 {self.user_info['ho_ten']}  |  Quyền: {self.get_role_name(self.user_info['vai_tro'])}"
        tk.Label(top_bar, text=user_desc, font=("Helvetica", 10, "bold"), fg="#f8fafc", bg="#0f172a").pack(side=tk.RIGHT, padx=15)

        btn_logout = tk.Button(top_bar, text="Đăng xuất", font=("Helvetica", 9, "bold"), bg="#ef4444", fg="white", bd=0, padx=10, pady=3, cursor="hand2", command=self.logout)
        btn_logout.pack(side=tk.RIGHT, padx=(0, 10))

        # --- MAIN BODY CONTAINER ---
        body_container = tk.Frame(self.root, bg="#f1f5f9")
        body_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # --- SIDEBAR LEFT (Đã phân quyền lại nút bấm) ---
        self.sidebar = tk.Frame(body_container, bg="#1e293b", width=230)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="DANH MỤC CHỨC NĂNG",
            font=("Helvetica", 9, "bold"),
            fg="#94a3b8",
            bg="#1e293b",
            pady=15,
        ).pack(fill=tk.X)

        role = self.user_info.get("vai_tro", "NhanVien")

        # 1. QUYỀN ADMIN: Hiển thị đầy đủ tất cả chức năng (bao gồm Phòng Ban & Chức Vụ)
        if role == "Admin":
            self.create_nav_btn("👥 Quản Lý Nhân Viên", self.show_employee_form)
            self.create_nav_btn("🏢 Phòng Ban & Chức Vụ", self.show_department_form)
            self.create_nav_btn("🔐 Quản Lý Tài Khoản", self.show_account_form)
            self.create_nav_btn("💰 Bảng Tính Lương", self.show_payroll_form)
            self.create_nav_btn("📊 Thống Kê & Báo Cáo", self.show_report_form)
            self.create_nav_btn("👤 Hồ Sơ Cá Nhân", self.show_profile_form)

        # 2. QUYỀN TRƯỞNG PHÒNG: Ẩn nút "Phòng Ban & Chức Vụ"
        elif role == "TruongPhong":
            self.create_nav_btn("👥 Quản Lý Nhân Viên", self.show_employee_form)
            self.create_nav_btn("💰 Bảng Tính Lương", self.show_payroll_form)
            self.create_nav_btn("📊 Thống Kê & Báo Cáo", self.show_report_form)
            self.create_nav_btn("👤 Hồ Sơ Cá Nhân", self.show_profile_form)

        # 3. QUYỀN NHÂN VIÊN: Chỉ xem hồ sơ & phiếu lương cá nhân
        else:
            self.create_nav_btn("👤 Hồ Sơ Cá Nhân", self.show_profile_form)
            self.create_nav_btn("📄 Phiếu Lương Cá Nhân", self.show_payroll_form)
        
        # --- DYNAMIC CONTENT AREA RIGHT ---
        self.content_area = tk.Frame(body_container, bg="#f8fafc", padx=20, pady=15)
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def create_nav_btn(self, text, command):
        btn = tk.Button(self.sidebar, text=text, font=("Helvetica", 10, "bold"), fg="#e2e8f0", bg="#1e293b", activebackground="#334155", activeforeground="white", bd=0, anchor="w", padx=18, pady=12, cursor="hand2", command=command)
        btn.pack(fill=tk.X, pady=2)
        return btn

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    # --- NHÚNG FORM NHÂN VIÊN VÀO KHUNG CONTENT ---
    def show_employee_form(self):
        self.clear_content()
        from form_nhan_vien import EmployeeManagementForm
        EmployeeManagementForm(self.content_area, self.user_info)

    def show_department_form(self):
        self.clear_content()
        from form_phongban import DepartmentPositionForm
        DepartmentPositionForm(self.content_area, self.user_info)
    def show_account_form(self):

        # Chỉ Admin được mở
        if self.user_info.get("vai_tro") != "Admin":
            messagebox.showwarning(
                "Không có quyền",
                "Chỉ Admin mới được sử dụng chức năng "
                "Quản lý tài khoản!"
            )
            return

        self.clear_content()

        from form_quan_ly_tai_khoan import AccountManagementForm

        AccountManagementForm(
            self.content_area,
            self.user_info
        )
    def show_payroll_form(self):
        self.clear_content()
        from form_tinh_luong import PayrollManagementForm
        PayrollManagementForm(self.content_area, self.user_info)

    def show_report_form(self):
        self.clear_content()
        from form_thong_ke import StatisticsReportForm
        StatisticsReportForm(self.content_area, self.user_info)

    def show_profile_form(self):
        self.clear_content()
        tk.Label(self.content_area, text="HỒ SƠ CÁ NHÂN", font=("Helvetica", 14, "bold"), bg="#f8fafc").pack(anchor="w")
        p_card = tk.Frame(self.content_area, bg="white", padx=25, pady=25)
        p_card.pack(fill=tk.X, pady=10)
        fields = [
            ("Mã tài khoản ID:", self.user_info["id"]),
            ("Tên đăng nhập:", self.user_info["ten_dang_nhap"]),
            ("Họ và Tên:", self.user_info["ho_ten"]),
            ("Email đăng ký:", self.user_info["email"]),
            ("Vai trò hệ thống:", self.get_role_name(self.user_info["vai_tro"])),
        ]
        for i, (k, v) in enumerate(fields):
            tk.Label(p_card, text=k, font=("Helvetica", 10, "bold"), bg="white", fg="#475569").grid(row=i, column=0, sticky="w", pady=5)
            tk.Label(p_card, text=str(v), font=("Helvetica", 10), bg="white", fg="#0f172a").grid(row=i, column=1, sticky="w", padx=20, pady=5)

    def logout(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn đăng xuất?"):
            self.root.destroy()
            run_app()

# ==============================================================================
# HÀM CHẠY CHƯƠNG TRÌNH CHÍNH (MAIN ENTRY POINT)
# ==============================================================================
def run_app():
    init_db()
    while True:
        login_root = tk.Tk()
        login_app = LoginForm(login_root)
        login_root.mainloop()

        if login_app.user_info:
            dashboard_root = tk.Tk()
            MainDashboardApp(dashboard_root, login_app.user_info)
            dashboard_root.mainloop()
        else:
            break

if __name__ == "__main__":
    run_app()