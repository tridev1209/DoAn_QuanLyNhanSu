import tkinter as tk
from tkinter import messagebox, ttk
import base64
import hashlib
import hmac
import os
from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import get_icon, icon_button, icon_label
from user_error import show_database_error


MAX_FAILED_LOGIN_ATTEMPTS = 5
PASSWORD_HASH_ITERATIONS = 260_000


def hash_password(password):
    """Tạo chuỗi băm có salt, đủ ngắn để tương thích cột VARCHAR(100)."""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS
    )
    salt_text = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_text = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password, stored_password):
    """Kiểm tra cả mật khẩu đã băm và dữ liệu dạng chữ của phiên bản cũ."""
    if not stored_password.startswith("pbkdf2_sha256$"):
        return hmac.compare_digest(stored_password, password)

    try:
        _, iterations, salt_text, digest_text = stored_password.split("$", 3)
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(
            digest_text + "=" * (-len(digest_text) % 4)
        )
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError):
        return False


def validate_new_password(password):
    if len(password) < 8:
        return "Mật khẩu mới phải có ít nhất 8 ký tự."
    if not any(char.isalpha() for char in password) or not any(
        char.isdigit() for char in password
    ):
        return "Mật khẩu mới phải có cả chữ và số."
    return None


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
                so_lan_dang_nhap_sai INT UNSIGNED NOT NULL DEFAULT 0,
                ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)

        # Bổ sung bộ đếm cho các CSDL đã được tạo từ phiên bản cũ.
        cursor.execute(
            "SHOW COLUMNS FROM nguoi_dung LIKE 'so_lan_dang_nhap_sai'"
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                ALTER TABLE nguoi_dung
                ADD COLUMN so_lan_dang_nhap_sai INT UNSIGNED NOT NULL DEFAULT 0
                """
            )
        conn.commit()

      
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
        self.iconphoto(False, get_icon(self, "key", "#2563eb"))
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

        btn_reset = icon_button(frame, text="CẬP NHẬT MẬT KHẨU", icon="key", bg="#2563eb", fg="white", bd=0, cursor="hand2", command=self.save_new_password_to_db)
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
                    validation_error = validate_new_password(new_pw)
                    if validation_error:
                        messagebox.showwarning(
                            "Mật khẩu chưa hợp lệ", validation_error, parent=self
                        )
                        return
                    cursor.execute(
                        """
                        UPDATE nguoi_dung
                        SET mat_khau = %s, so_lan_dang_nhap_sai = 0
                        WHERE id = %s
                        """,
                        (hash_password(new_pw), row["id"]),
                    )
                    conn.commit()
                    messagebox.showinfo(
                        "Thành công", "Đổi mật khẩu thành công!", parent=self
                    )
                    self.destroy()
                else:
                    messagebox.showerror("Lỗi", "Tên đăng nhập hoặc Email không chính xác!", parent=self)
            except Error as e:
                show_database_error(e, "đổi mật khẩu", parent=self)
            finally:
                conn.close()

# ==============================================================================
# FORM ĐĂNG NHẬP
# ==============================================================================
class LoginForm:
    def __init__(self, root):
        self.root = root
        self.root.title("ĐĂNG NHẬP HỆ THỐNG QUẢN LÝ NHÂN SỰ")
        self.root.iconphoto(True, get_icon(self.root, "app", "#2563eb"))
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

        tk.Button(
            main_frame,
            text="ĐĂNG NHẬP",
            font=("Segoe UI", 11, "bold"),
            bg="#2563eb",
            fg="white",
            bd=0,
            cursor="hand2",
            command=self.handle_login,
        ).pack(fill=tk.X, ipady=6)

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
            cursor.execute(
                """
                SELECT id, ten_dang_nhap, mat_khau, ho_ten, email, vai_tro,
                       trang_thai, so_lan_dang_nhap_sai, ngay_tao
                FROM nguoi_dung
                WHERE ten_dang_nhap = %s
                FOR UPDATE
                """,
                (username,),
            )
            row = cursor.fetchone()

            if row:
                if row["trang_thai"] == 0:
                    messagebox.showerror("Lỗi", "Tài khoản đã bị khóa!")
                    return

                if verify_password(password, row["mat_khau"]):
                    updates = []
                    params = []
                    if row["so_lan_dang_nhap_sai"]:
                        updates.append("so_lan_dang_nhap_sai = 0")
                    # Tự động nâng cấp mật khẩu dạng chữ của dữ liệu cũ sau khi
                    # người dùng đăng nhập thành công.
                    if not row["mat_khau"].startswith("pbkdf2_sha256$"):
                        updates.append("mat_khau = %s")
                        params.append(hash_password(password))
                    if updates:
                        params.append(row["id"])
                        cursor.execute(
                            f"UPDATE nguoi_dung SET {', '.join(updates)} WHERE id = %s",
                            tuple(params),
                        )
                        conn.commit()

                    row.pop("mat_khau", None)
                    row.pop("so_lan_dang_nhap_sai", None)
                    self.user_info = row
                    self.root.destroy()
                else:
                    failed_attempts = int(row["so_lan_dang_nhap_sai"] or 0) + 1
                    is_locked = failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS
                    cursor.execute(
                        """
                        UPDATE nguoi_dung
                        SET so_lan_dang_nhap_sai = %s,
                            trang_thai = %s
                        WHERE id = %s
                        """,
                        (failed_attempts, 0 if is_locked else 1, row["id"]),
                    )
                    conn.commit()

                    if is_locked:
                        messagebox.showerror(
                            "Tài khoản đã bị khóa",
                            "Bạn đã nhập sai mật khẩu 5 lần. "
                            "Vui lòng liên hệ Admin để mở khóa tài khoản.",
                        )
                    else:
                        remaining = MAX_FAILED_LOGIN_ATTEMPTS - failed_attempts
                        messagebox.showerror(
                            "Lỗi",
                            "Sai tên đăng nhập hoặc mật khẩu! "
                            f"Tài khoản sẽ bị khóa sau {remaining} lần nhập sai nữa.",
                        )
            else:
                messagebox.showerror("Lỗi", "Sai tên đăng nhập hoặc mật khẩu!")
        except Error as e:
            show_database_error(e, "đăng nhập")
        finally:
            conn.close()


# ==============================================================================
# CỬA SỔ ĐỔI MẬT KHẨU KHI ĐÃ ĐĂNG NHẬP
# ==============================================================================
class ChangePasswordWindow(tk.Toplevel):
    def __init__(self, parent, user_info):
        super().__init__(parent)
        self.user_info = user_info
        self.title("Đổi mật khẩu")
        self.iconphoto(False, get_icon(self, "key", "#2563eb"))
        self.geometry("430x390")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.var_current_pw = tk.StringVar()
        self.var_new_pw = tk.StringVar()
        self.var_confirm_pw = tk.StringVar()
        self.var_show_pw = tk.BooleanVar(value=False)
        self.create_widgets()

    def create_widgets(self):
        frame = tk.Frame(self, padx=30, pady=25, bg="#ffffff")
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame,
            text="ĐỔI MẬT KHẨU",
            font=("Segoe UI", 14, "bold"),
            fg="#1e293b",
            bg="#ffffff",
        ).pack(pady=(0, 18))

        entries = []
        fields = [
            ("Mật khẩu hiện tại:", self.var_current_pw),
            ("Mật khẩu mới:", self.var_new_pw),
            ("Nhập lại mật khẩu mới:", self.var_confirm_pw),
        ]
        for label, variable in fields:
            tk.Label(
                frame,
                text=label,
                font=("Segoe UI", 9, "bold"),
                bg="#ffffff",
                fg="#334155",
                anchor="w",
            ).pack(fill=tk.X, pady=(3, 2))
            entry = ttk.Entry(
                frame, textvariable=variable, show="•", font=("Segoe UI", 10)
            )
            entry.pack(fill=tk.X, ipady=4, pady=(0, 8))
            entries.append(entry)

        def toggle_passwords():
            mask = "" if self.var_show_pw.get() else "•"
            for entry in entries:
                entry.config(show=mask)

        tk.Checkbutton(
            frame,
            text="Hiện mật khẩu",
            variable=self.var_show_pw,
            command=toggle_passwords,
            bg="#ffffff",
            fg="#475569",
            activebackground="#ffffff",
        ).pack(anchor="w", pady=(0, 12))

        icon_button(
            frame,
            text="CẬP NHẬT MẬT KHẨU",
            icon="key",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="white",
            bd=0,
            cursor="hand2",
            command=self.change_password,
        ).pack(fill=tk.X, ipady=6)

        entries[0].focus_set()
        entries[-1].bind("<Return>", lambda event: self.change_password())

    def change_password(self):
        current_pw = self.var_current_pw.get()
        new_pw = self.var_new_pw.get()
        confirm_pw = self.var_confirm_pw.get()

        if not current_pw or not new_pw or not confirm_pw:
            messagebox.showwarning(
                "Thiếu thông tin",
                "Vui lòng nhập đầy đủ các trường mật khẩu.",
                parent=self,
            )
            return
        if new_pw != confirm_pw:
            messagebox.showwarning(
                "Mật khẩu không khớp",
                "Mật khẩu mới và phần nhập lại không giống nhau.",
                parent=self,
            )
            return

        validation_error = validate_new_password(new_pw)
        if validation_error:
            messagebox.showwarning(
                "Mật khẩu chưa hợp lệ", validation_error, parent=self
            )
            return
        if hmac.compare_digest(current_pw, new_pw):
            messagebox.showwarning(
                "Mật khẩu chưa hợp lệ",
                "Mật khẩu mới phải khác mật khẩu hiện tại.",
                parent=self,
            )
            return

        conn = get_db_connection()
        if not conn:
            messagebox.showerror(
                "Lỗi", "Không thể kết nối CSDL MySQL!", parent=self
            )
            return

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT mat_khau FROM nguoi_dung WHERE id = %s",
                (self.user_info["id"],),
            )
            row = cursor.fetchone()
            if not row or not verify_password(current_pw, row["mat_khau"]):
                messagebox.showerror(
                    "Không thể đổi mật khẩu",
                    "Mật khẩu hiện tại không chính xác.",
                    parent=self,
                )
                return

            cursor.execute(
                """
                UPDATE nguoi_dung
                SET mat_khau = %s, so_lan_dang_nhap_sai = 0
                WHERE id = %s
                """,
                (hash_password(new_pw), self.user_info["id"]),
            )
            conn.commit()
            messagebox.showinfo(
                "Thành công", "Mật khẩu đã được cập nhật.", parent=self
            )
            self.destroy()
        except Error as e:
            show_database_error(e, "đổi mật khẩu", parent=self)
        finally:
            conn.close()


# ==============================================================================
# MAIN DASHBOARD (GIAO DIỆN CHÍNH GỒM HEADER + SIDEBAR)
# ==============================================================================
class MainDashboardApp:
    def __init__(self, root, user_info):
        self.root = root
        self.user_info = user_info
        self.logged_out = False

        role_names = {"Admin": "Quản Trị Viên", "TruongPhong": "Trưởng Phòng", "NhanVien": "Nhân Viên"}
        role_display = role_names.get(user_info['vai_tro'], user_info['vai_tro'])

        self.root.title(f"HỆ THỐNG QUẢN LÝ NHÂN SỰ - [{user_info['ho_ten']} ({role_display})]")
        self.root.iconphoto(True, get_icon(self.root, "app", "#38bdf8"))
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

        icon_label(top_bar, text="HỆ THỐNG QUẢN LÝ NHÂN SỰ", icon="app", font=("Segoe UI", 13, "bold"), fg="#38bdf8", bg="#0f172a", padx=15).pack(side=tk.LEFT)

        btn_logout = icon_button(top_bar, text="Đăng xuất", icon="logout", font=("Segoe UI", 9, "bold"), bg="#ef4444", fg="white", bd=0, padx=10, pady=3, cursor="hand2", command=self.logout)
        btn_logout.pack(side=tk.RIGHT, padx=(10, 12))

        user_desc = f"{self.user_info['ho_ten']}  |  Quyền: {self.get_role_name(self.user_info['vai_tro'])}"
        icon_label(top_bar, text=user_desc, icon="profile", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#0f172a").pack(side=tk.RIGHT, padx=(15, 0))

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
            self.create_nav_btn("Quản Lý Nhân Viên", "employees", self.show_employee_form)
            self.create_nav_btn("Phòng Ban & Chức Vụ", "department", self.show_department_form)
            self.create_nav_btn("Quản Lý Tài Khoản", "account", self.show_account_form)
            self.create_nav_btn("Bảng Tính Lương", "payroll", self.show_payroll_form)
            self.create_nav_btn("Thống Kê & Báo Cáo", "report", self.show_report_form)
            self.create_nav_btn("Hồ Sơ Cá Nhân", "profile", self.show_profile_form)

        # 2. QUYỀN TRƯỞNG PHÒNG: Ẩn nút "Phòng Ban & Chức Vụ"
        elif role == "TruongPhong":
            self.create_nav_btn("Quản Lý Nhân Viên", "employees", self.show_employee_form)
            self.create_nav_btn("Bảng Tính Lương", "payroll", self.show_payroll_form)
            self.create_nav_btn("Thống Kê & Báo Cáo", "report", self.show_report_form)
            self.create_nav_btn("Hồ Sơ Cá Nhân", "profile", self.show_profile_form)

        # 3. QUYỀN NHÂN VIÊN: Chỉ xem hồ sơ & phiếu lương cá nhân
        else:
            self.create_nav_btn("Hồ Sơ Cá Nhân", "profile", self.show_profile_form)
            self.create_nav_btn("Phiếu Lương Cá Nhân", "document", self.show_payroll_form)
        
        # --- DYNAMIC CONTENT AREA RIGHT ---
        self.content_area = tk.Frame(body_container, bg="#f8fafc", padx=20, pady=15)
        self.content_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def create_nav_btn(self, text, icon, command):
        btn = icon_button(self.sidebar, text=text, icon=icon, font=("Segoe UI", 10, "bold"), fg="#e2e8f0", bg="#1e293b", activebackground="#334155", activeforeground="white", bd=0, anchor="w", padx=18, pady=12, cursor="hand2", command=command)
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

        class DashboardPayrollForm(PayrollManagementForm):
            """Sửa bộ lọc phiếu lương cá nhân trong phạm vi dashboard."""

            def load_data(self):
                if self.role != "NhanVien":
                    return super().load_data()

                thang_flt = self.var_filter_thang.get().strip()
                nam_flt = self.var_filter_nam.get().strip()
                if nam_flt:
                    try:
                        nam_flt = int(nam_flt)
                    except ValueError:
                        messagebox.showwarning(
                            "Năm không hợp lệ", "Năm lọc phải là một số nguyên."
                        )
                        return

                conn = get_db_connection()
                if not conn:
                    return

                try:
                    cursor = conn.cursor(dictionary=True)
                    query = """
                        SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam,
                               bl.luong_cb, bl.ngay_cong, bl.gio_ot,
                               bl.luong_ot, bl.phu_cap, bl.khoan_tru,
                               bl.thuc_nhan
                        FROM bang_luong bl
                        LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                        WHERE (bl.ma_nv = %s OR nv.nguoi_dung_id = %s)
                    """
                    params = [
                        self.user_actual_ma_nv or self.user_login_name,
                        self.user_db_id,
                    ]

                    if thang_flt != "Tất cả":
                        query += " AND bl.thang = %s"
                        params.append(int(thang_flt))
                    if nam_flt:
                        query += " AND bl.nam = %s"
                        params.append(nam_flt)

                    query += " ORDER BY bl.nam DESC, bl.thang DESC"
                    cursor.execute(query, tuple(params))
                    self.refresh_table(cursor.fetchall())
                except Error as e:
                    show_database_error(e, "lọc phiếu lương cá nhân")
                finally:
                    conn.close()

        DashboardPayrollForm(self.content_area, self.user_info)

    def show_report_form(self):
        self.clear_content()
        from form_thong_ke import StatisticsReportForm
        StatisticsReportForm(self.content_area, self.user_info)

    def show_profile_form(self):
        self.clear_content()
        icon_label(self.content_area, text="HỒ SƠ CÁ NHÂN", icon="profile", icon_color="#2563eb", font=("Segoe UI", 14, "bold"), bg="#f8fafc").pack(anchor="w")
        p_card = tk.Frame(self.content_area, bg="white", padx=25, pady=25)
        p_card.pack(fill=tk.X, pady=10)
        fields = [
            ("Mã tài khoản ID:", self.user_info["id"]),
            ("Tên đăng nhập:", self.user_info["ten_dang_nhap"]),
            ("Họ và Tên:", self.user_info["ho_ten"]),
            ("Email đăng ký:", self.user_info["email"]),
            ("Vai trò hệ thống:", self.get_role_name(self.user_info["vai_tro"])),
            ("Trạng thái:", "Đang hoạt động" if self.user_info.get("trang_thai") else "Đã khóa"),
            ("Ngày tạo tài khoản:", self.user_info.get("ngay_tao") or "Chưa có thông tin"),
        ]
        for i, (k, v) in enumerate(fields):
            tk.Label(p_card, text=k, font=("Helvetica", 10, "bold"), bg="white", fg="#475569").grid(row=i, column=0, sticky="w", pady=5)
            tk.Label(p_card, text=str(v), font=("Helvetica", 10), bg="white", fg="#0f172a").grid(row=i, column=1, sticky="w", padx=20, pady=5)

        icon_button(
            p_card,
            text="Đổi mật khẩu",
            icon="key",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="white",
            bd=0,
            padx=14,
            pady=7,
            cursor="hand2",
            command=lambda: ChangePasswordWindow(self.root, self.user_info),
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(18, 0))

    def logout(self):
        if messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn đăng xuất?"):
            self.logged_out = True
            self.root.destroy()

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
            dashboard_app = MainDashboardApp(dashboard_root, login_app.user_info)
            dashboard_root.mainloop()

            # Chỉ quay lại form đăng nhập khi người dùng chọn "Đăng xuất".
            # Đóng dashboard bằng nút X sẽ kết thúc chương trình.
            if not dashboard_app.logged_out:
                break
        else:
            break

if __name__ == "__main__":
    run_app()
