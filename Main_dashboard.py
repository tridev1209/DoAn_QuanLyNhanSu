import tkinter as tk
from tkinter import messagebox, ttk
import hmac
from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import get_icon, icon_button, icon_label
from user_error import show_database_error


MAX_FAILED_LOGIN_ATTEMPTS = 5
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "123456"
DEFAULT_ADMIN_FULL_NAME = "Quản Trị Viên Hệ Thống"
DEFAULT_ADMIN_EMAIL = "admin@company.com"


def verify_password(password, stored_password):
    """So sánh trực tiếp với mật khẩu dạng chữ trong cơ sở dữ liệu."""
    return hmac.compare_digest(str(stored_password), password)


def validate_new_password(password):
    if len(password) < 8:
        return "Mật khẩu mới phải có ít nhất 8 ký tự."
    if not any(char.isalpha() for char in password) or not any(
        char.isdigit() for char in password
    ):
        return "Mật khẩu mới phải có cả chữ và số."
    return None


def get_password_criteria(password):
    """Trả về các tiêu chí đang dùng để kiểm tra mật khẩu mới."""
    return (
        ("Có ít nhất 8 ký tự", len(password) >= 8),
        ("Có ít nhất 1 chữ cái", any(char.isalpha() for char in password)),
        ("Có ít nhất 1 chữ số", any(char.isdigit() for char in password)),
    )


class PasswordEntry(ttk.Entry):
    REVEAL_DURATION_MS = 800

    def __init__(self, master, variable, **kwargs):
        self.password_variable = variable
        self.reveal_after_id = None
        self.password_visible = False
        entry_font = kwargs.get("font", ("Segoe UI", 10))
        super().__init__(
            master,
            textvariable=self.password_variable,
            show="*",
            **kwargs,
        )
        field_bg = ttk.Style(self).lookup("TEntry", "fieldbackground") or "white"
        self.reveal_label = tk.Label(
            self,
            text="",
            font=entry_font,
            bg=field_bg,
            fg="#111827",
            bd=0,
            padx=0,
            pady=0,
        )
        self.eye_button = tk.Button(
            self,
            image=get_icon(self, "eye_off", "#64748b", 16),
            bg=field_bg,
            activebackground=field_bg,
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
            takefocus=False,
            command=self.toggle_visibility,
        )
        self.eye_button._icon_image = self.eye_button.cget("image")
        self.eye_button.place(relx=1.0, rely=0.5, x=-3, anchor="e", width=25, height=22)
        self.bind("<KeyPress>", self._hide_password, add="+")
        self.bind("<KeyRelease>", self._handle_key_release, add="+")
        self.bind("<<Paste>>", self._handle_paste, add="+")
        self.bind("<Button-1>", self._hide_password, add="+")
        self.bind("<FocusOut>", self._hide_password, add="+")

    def _hide_password(self, _event=None):
        if self.reveal_after_id is not None:
            try:
                self.after_cancel(self.reveal_after_id)
            except tk.TclError:
                pass
            self.reveal_after_id = None
        self.reveal_label.place_forget()

    def toggle_visibility(self):
        self._hide_password()
        self.password_visible = not self.password_visible
        icon_name = "eye" if self.password_visible else "eye_off"
        icon = get_icon(self, icon_name, "#2563eb" if self.password_visible else "#64748b", 16)
        self.eye_button.config(image=icon)
        self.eye_button._icon_image = icon
        self.config(show="" if self.password_visible else "*")
        self.eye_button.lift()
        self.focus_set()
        self.icursor(tk.END)

    def _handle_key_release(self, event):
        if self.password_visible:
            return
        control_pressed = bool(event.state & 0x4)
        alt_pressed = bool(event.state & 0x8)
        if event.char and event.char.isprintable() and not control_pressed and not alt_pressed:
            self._reveal_last_character()

    def _handle_paste(self, _event=None):
        self.after_idle(self._reveal_last_character)

    def _reveal_last_character(self):
        if self.password_visible:
            return
        password = self.password_variable.get()
        cursor = self.index(tk.INSERT)
        if not password or cursor <= 0:
            self._hide_password()
            return

        character_index = cursor - 1
        bounds = self.bbox(character_index)
        if not bounds:
            return

        x, y, width, height = bounds
        self._hide_password()
        self.reveal_label.config(text=password[character_index])
        self.reveal_label.place(x=x, y=y, width=max(width, 1), height=height)
        self.reveal_label.lift()
        self.eye_button.lift()
        self.reveal_after_id = self.after(
            self.REVEAL_DURATION_MS, self._hide_password
        )


class PasswordCriteriaPanel(tk.Frame):
    """Hiển thị trạng thái tiêu chí mật khẩu theo thời gian thực."""

    def __init__(
        self,
        master,
        password_variable,
        confirm_variable=None,
        current_variable=None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.password_variable = password_variable
        self.confirm_variable = confirm_variable
        self.current_variable = current_variable
        self.labels = []

        criteria_count = 3
        if confirm_variable is not None:
            criteria_count += 1
        if current_variable is not None:
            criteria_count += 1
        for row in range(criteria_count):
            label = tk.Label(
                self,
                font=("Segoe UI", 9),
                bg=self.cget("bg"),
                fg="#64748b",
                anchor="w",
            )
            label.grid(row=row, column=0, sticky="w", pady=1)
            self.labels.append(label)

        self.password_trace_id = password_variable.trace_add(
            "write", self._update_status
        )
        self.confirm_trace_id = None
        if confirm_variable is not None:
            self.confirm_trace_id = confirm_variable.trace_add(
                "write", self._update_status
            )
        self.current_trace_id = None
        if current_variable is not None:
            self.current_trace_id = current_variable.trace_add(
                "write", self._update_status
            )
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._update_status()

    def _update_status(self, *_args):
        password = self.password_variable.get()
        criteria = list(get_password_criteria(password))
        if self.confirm_variable is not None:
            confirmation = self.confirm_variable.get()
            criteria.append(
                (
                    "Mật khẩu nhập lại trùng khớp",
                    bool(confirmation) and confirmation == password,
                )
            )
        if self.current_variable is not None:
            current_password = self.current_variable.get()
            criteria.append(
                (
                    "Mật khẩu mới khác mật khẩu hiện tại",
                    bool(password)
                    and bool(current_password)
                    and password != current_password,
                )
            )

        for label, (description, passed) in zip(self.labels, criteria):
            label.config(
                text=f"{'✓' if passed else '○'} {description}",
                fg="#16a34a" if passed else "#64748b",
            )

    def _on_destroy(self, event):
        if event.widget is not self:
            return
        if self.password_trace_id:
            self.password_variable.trace_remove("write", self.password_trace_id)
            self.password_trace_id = None
        if self.confirm_trace_id:
            self.confirm_variable.trace_remove("write", self.confirm_trace_id)
            self.confirm_trace_id = None
        if self.current_trace_id:
            self.current_variable.trace_remove("write", self.current_trace_id)
            self.current_trace_id = None


def get_available_admin_email(cursor):
    """Chọn email quản trị chưa được tài khoản khác sử dụng."""
    local_part, domain = DEFAULT_ADMIN_EMAIL.split("@", 1)
    candidate = DEFAULT_ADMIN_EMAIL
    suffix = 1
    while True:
        cursor.execute(
            "SELECT id FROM nguoi_dung WHERE email = %s LIMIT 1",
            (candidate,),
        )
        if not cursor.fetchone():
            return candidate
        candidate = f"{local_part}{suffix}@{domain}"
        suffix += 1


def ensure_default_admin(cursor):
    """Đảm bảo luôn có tài khoản admin mặc định nhưng không ghi đè mật khẩu."""
    cursor.execute(
        """
        SELECT id, vai_tro, trang_thai, so_lan_dang_nhap_sai
        FROM nguoi_dung
        WHERE ten_dang_nhap = %s
        LIMIT 1
        """,
        (DEFAULT_ADMIN_USERNAME,),
    )
    admin = cursor.fetchone()

    if admin:
        admin_id, role, status, failed_attempts = admin
        if role != "Admin" or status != 1 or failed_attempts:
            cursor.execute(
                """
                UPDATE nguoi_dung
                SET vai_tro = 'Admin',
                    trang_thai = 1,
                    so_lan_dang_nhap_sai = 0
                WHERE id = %s
                """,
                (admin_id,),
            )
        return False

    admin_email = get_available_admin_email(cursor)
    cursor.execute(
        """
        INSERT INTO nguoi_dung
        (
            ten_dang_nhap,
            mat_khau,
            ho_ten,
            email,
            vai_tro,
            trang_thai,
            so_lan_dang_nhap_sai
        )
        VALUES (%s, %s, %s, %s, 'Admin', 1, 0)
        """,
        (
            DEFAULT_ADMIN_USERNAME,
            DEFAULT_ADMIN_PASSWORD,
            DEFAULT_ADMIN_FULL_NAME,
            admin_email,
        ),
    )
    return True


def init_db():
    """Khởi tạo bảng tài khoản và bảo đảm có tài khoản Admin mặc định."""
    conn = get_db_connection()
    if not conn:
        return
    cursor = None
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

        ensure_default_admin(cursor)
        conn.commit()

      
    except Error as e:
        print(f"Lỗi khởi tạo CSDL: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor:
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
        self.geometry("400x410")
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
        PasswordEntry(
            frame, variable=self.var_new_pw, font=("Helvetica", 10)
        ).pack(fill=tk.X, ipady=3, pady=(0, 6))

        PasswordCriteriaPanel(
            frame,
            self.var_new_pw,
            bg="#ffffff",
        ).pack(fill=tk.X, pady=(0, 14))

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
                        (new_pw, row["id"]),
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
        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self.root, bg="#f4f6f9", padx=30, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="ĐĂNG NHẬP", font=("Helvetica", 18, "bold"), fg="#1e293b", bg="#f4f6f9").pack(pady=(0, 5))
        tk.Label(main_frame, text="Hệ thống Quản lý Nhân sự ", font=("Helvetica", 10, "italic"), fg="#64748b", bg="#f4f6f9").pack(pady=(0, 15))

        tk.Label(main_frame, text="Tên đăng nhập:", font=("Helvetica", 10, "bold"), fg="#334155", bg="#f4f6f9", anchor="w").pack(fill=tk.X, pady=(5, 2))
        self.entry_user = ttk.Entry(main_frame, textvariable=self.var_username, font=("Helvetica", 11))
        self.entry_user.pack(fill=tk.X, ipady=4, pady=(0, 12))
        self.entry_user.focus()

        tk.Label(main_frame, text="Mật khẩu:", font=("Helvetica", 10, "bold"), fg="#334155", bg="#f4f6f9", anchor="w").pack(fill=tk.X, pady=(5, 2))
        self.entry_pw = PasswordEntry(
            main_frame, variable=self.var_password, font=("Helvetica", 11)
        )
        self.entry_pw.pack(fill=tk.X, ipady=4, pady=(0, 5))

        self.entry_pw.bind("<Return>", lambda event: self.handle_login())
        self.entry_user.bind("<Return>", lambda event: self.entry_pw.focus())

        sub_frame = tk.Frame(main_frame, bg="#f4f6f9")
        sub_frame.pack(fill=tk.X, pady=(0, 15))

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
                    if row["so_lan_dang_nhap_sai"]:
                        cursor.execute(
                            """
                            UPDATE nguoi_dung
                            SET so_lan_dang_nhap_sai = 0
                            WHERE id = %s
                            """,
                            (row["id"],),
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
        self.geometry("430x530")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.var_current_pw = tk.StringVar()
        self.var_new_pw = tk.StringVar()
        self.var_confirm_pw = tk.StringVar()
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
            entry = PasswordEntry(
                frame, variable=variable, font=("Segoe UI", 10)
            )
            entry.pack(fill=tk.X, ipady=4, pady=(0, 8))
            entries.append(entry)

        PasswordCriteriaPanel(
            frame,
            self.var_new_pw,
            self.var_confirm_pw,
            current_variable=self.var_current_pw,
            bg="#ffffff",
        ).pack(fill=tk.X, pady=(0, 12))

        action_frame = tk.Frame(frame, bg="#ffffff")
        action_frame.pack(fill=tk.X)
        action_frame.grid_columnconfigure(0, weight=1)
        action_frame.grid_columnconfigure(1, weight=2)

        icon_button(
            action_frame,
            text="HỦY",
            icon="inactive",
            font=("Segoe UI", 10, "bold"),
            bg="#e2e8f0",
            fg="#334155",
            bd=0,
            cursor="hand2",
            command=self.destroy,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5), ipady=6)

        self.update_password_button = icon_button(
            action_frame,
            text="CẬP NHẬT MẬT KHẨU",
            icon="key",
            font=("Segoe UI", 10, "bold"),
            bg="#cbd5e1",
            fg="white",
            disabledforeground="#64748b",
            bd=0,
            cursor="arrow",
            state=tk.DISABLED,
            command=self.change_password,
        )
        self.update_password_button.grid(
            row=0, column=1, sticky="ew", padx=(5, 0), ipady=6
        )

        self.validation_trace_ids = [
            variable.trace_add("write", self.update_change_button_state)
            for variable in (
                self.var_current_pw,
                self.var_new_pw,
                self.var_confirm_pw,
            )
        ]
        self.update_change_button_state()

        entries[0].focus_set()
        entries[-1].bind("<Return>", self.submit_change_if_valid)

    def update_change_button_state(self, *_args):
        current_pw = self.var_current_pw.get()
        new_pw = self.var_new_pw.get()
        confirm_pw = self.var_confirm_pw.get()
        criteria_valid = all(
            passed for _description, passed in get_password_criteria(new_pw)
        )
        is_valid = (
            bool(current_pw)
            and criteria_valid
            and confirm_pw == new_pw
            and new_pw != current_pw
        )

        self.update_password_button.config(
            state=tk.NORMAL if is_valid else tk.DISABLED,
            bg="#2563eb" if is_valid else "#cbd5e1",
            cursor="hand2" if is_valid else "arrow",
        )

    def submit_change_if_valid(self, _event=None):
        if str(self.update_password_button.cget("state")) == str(tk.NORMAL):
            self.change_password()

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
                (new_pw, self.user_info["id"]),
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
                    self.refresh_table(
                        cursor.fetchall(),
                        "Không tìm thấy phiếu lương phù hợp!",
                    )
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
