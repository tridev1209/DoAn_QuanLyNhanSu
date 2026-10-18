import tkinter as tk
from tkinter import messagebox, ttk

from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import icon_button
from user_error import show_database_error


class AccountManagementForm:

    def __init__(self, parent_frame, user_info=None):

        self.parent = parent_frame

        self.user_info = user_info or {
            "id": 1,
            "ten_dang_nhap": "admin",
            "vai_tro": "Admin",
            "ho_ten": "Quản trị viên",
        }

        self.role = self.user_info.get(
            "vai_tro",
            "NhanVien"
        )

        # =====================================================
        # BIẾN
        # =====================================================

        self.var_search = tk.StringVar()

        self.var_id = tk.StringVar()
        self.var_ma_nv = tk.StringVar()
        self.var_username = tk.StringVar()
        self.var_ho_ten = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_vai_tro = tk.StringVar()
        self.var_trang_thai = tk.StringVar()

        self.create_widgets()
        self.load_accounts()

    # =========================================================
    # GIAO DIỆN
    # =========================================================

    def create_widgets(self):
        title = tk.Label(
            self.parent,
            text="QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG",
            font=("Helvetica", 13, "bold"),
            bg="#f8fafc",
            fg="#1e293b",
        )
        title.pack(anchor="w", pady=(0, 8))

        # =====================================================
        # FORM THÔNG TIN
        # =====================================================
        info_frame = tk.LabelFrame(
            self.parent,
            text=" Thông tin tài khoản ",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            padx=12,
            pady=10,
        )
        info_frame.pack(fill=tk.X, pady=(0, 8))
        info_frame.bind("<Button-1>", self.focus_account_form)

        # Giữ cố định ba cặp cột để các trường thẳng hàng.
        for column in (1, 3, 5):
            info_frame.grid_columnconfigure(column, weight=1, uniform="account_fields")

        fields = (
            ("ID:", self.var_id, "entry", 0, 0),
            ("Mã NV:", self.var_ma_nv, "entry", 0, 2),
            ("Tên đăng nhập:", self.var_username, "entry", 0, 4),
            ("Họ tên:", self.var_ho_ten, "entry", 1, 0),
            ("Email:", self.var_email, "entry", 1, 2),
            ("Vai trò (theo chức vụ):", self.var_vai_tro, "role", 1, 4),
            ("Trạng thái:", self.var_trang_thai, "status", 2, 0),
        )

        for label_text, variable, field_type, row, column in fields:
            label = tk.Label(
                info_frame,
                text=label_text,
                bg="#f8fafc",
                font=("Helvetica", 10),
            )
            label.grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0 if column == 0 else 15, 0),
                pady=5,
            )
            label.bind("<Button-1>", self.focus_account_form)

            if field_type == "role":
                widget = ttk.Entry(
                    info_frame,
                    textvariable=variable,
                    state="readonly",
                    width=20,
                    font=("Helvetica", 10),
                )
                self.cb_role = widget
            elif field_type == "status":
                widget = ttk.Entry(
                    info_frame,
                    textvariable=variable,
                    state="readonly",
                    width=20,
                    font=("Helvetica", 10),
                )
                self.cb_status = widget
            else:
                widget = ttk.Entry(
                    info_frame,
                    textvariable=variable,
                    state="readonly",
                    width=22,
                    font=("Helvetica", 10),
                )

            widget.grid(
                row=row,
                column=column + 1,
                sticky="ew",
                padx=5,
                pady=5,
            )
            widget.bind("<Button-1>", self.focus_account_form)

        # =====================================================
        # THANH CÔNG CỤ VÀ TÌM KIẾM
        # =====================================================
        action_frame = tk.Frame(self.parent, bg="#f8fafc")
        action_frame.pack(fill=tk.X, pady=(0, 8))

        button_frame = tk.Frame(action_frame, bg="#f8fafc")
        button_frame.pack(side=tk.LEFT)

        icon_button(
            button_frame,
            text="Reset mật khẩu",
            icon="key",
            bg="#f59e0b",
            fg="white",
            bd=0,
            padx=10,
            pady=5,
            command=self.reset_password,
        ).pack(side=tk.LEFT, padx=3)

        icon_button(
            button_frame,
            text="Khóa tài khoản",
            icon="lock",
            bg="#dc2626",
            fg="white",
            bd=0,
            padx=10,
            pady=5,
            command=self.lock_account,
        ).pack(side=tk.LEFT, padx=3)

        icon_button(
            button_frame,
            text="Mở khóa",
            icon="unlock",
            bg="#16a34a",
            fg="white",
            bd=0,
            padx=10,
            pady=5,
            command=self.unlock_account,
        ).pack(side=tk.LEFT, padx=3)

        icon_button(
            button_frame,
            text="Làm mới",
            icon="refresh",
            bg="#64748b",
            fg="white",
            bd=0,
            padx=10,
            pady=5,
            command=self.refresh_form,
        ).pack(side=tk.LEFT, padx=3)

        search_frame = tk.Frame(action_frame, bg="#f8fafc")
        search_frame.pack(side=tk.RIGHT)

        tk.Label(
            search_frame,
            text="Tìm kiếm:",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
        ).pack(side=tk.LEFT, padx=5)

        self.entry_search = tk.Entry(
            search_frame,
            textvariable=self.var_search,
            width=25,
            font=("Helvetica", 10),
        )
        self.entry_search.pack(side=tk.LEFT, padx=4)

        self.search_placeholder = tk.Label(
            self.entry_search,
            text="Nhập ID, mã NV, phòng ban, họ tên, tên đăng nhập hoặc email...",
            bg="white",
            fg="#94a3b8",
            font=("Helvetica", 10),
            bd=0,
            padx=0,
            pady=0,
            cursor="xterm",
        )
        self.search_placeholder.place(x=4, rely=0.5, anchor="w")
        self.search_placeholder.bind("<Button-1>", self.focus_search_entry)
        self.entry_search.bind("<FocusIn>", self.update_search_placeholder)
        self.entry_search.bind("<FocusOut>", self.update_search_placeholder)
        self.entry_search.bind("<Return>", self.on_search_enter)
        self.var_search.trace_add("write", self.update_search_placeholder)

        icon_button(
            search_frame,
            text="Tìm",
            icon="search",
            bg="#0ea5e9",
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            command=self.search_accounts,
        ).pack(side=tk.LEFT, padx=2)

        self.btn_tat_ca = tk.Button(
            search_frame,
            text="Tất cả",
            font=("Helvetica", 10),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=4,
            bd=0,
            command=self.show_all_accounts,
        )
        self.btn_tat_ca.pack(side=tk.LEFT, padx=2)

        # =====================================================
        # BẢNG TÀI KHOẢN
        # =====================================================
        table_frame = tk.Frame(self.parent, bg="white")
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = (
            "id",
            "ma_nv",
            "phong_ban",
            "ho_ten",
            "username",
            "email",
            "vai_tro",
            "trang_thai"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15
        )

        headers = {
            "id": "ID",
            "ma_nv": "Mã NV",
            "phong_ban": "Phòng ban",
            "ho_ten": "Họ và tên",
            "username": "Tên đăng nhập",
            "email": "Email",
            "vai_tro": "Vai trò",
            "trang_thai": "Trạng thái"
        }

        widths = {
            "id": 50,
            "ma_nv": 90,
            "phong_ban": 140,
            "ho_ten": 150,
            "username": 120,
            "email": 180,
            "vai_tro": 110,
            "trang_thai": 110
        }

        for col in columns:

            self.tree.heading(
                col,
                text=headers[col]
            )

            self.tree.column(
                col,
                width=widths[col],
                anchor=tk.CENTER
            )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient=tk.VERTICAL,
            command=self.tree.yview
        )

        self.tree.configure(
            yscrollcommand=scrollbar.set
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        self.tree.pack(
            fill=tk.BOTH,
            expand=True
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.on_select
        )

    def focus_search_entry(self, event=None):
        self.entry_search.focus_set()
        self.update_search_placeholder()

    def focus_account_form(self, event=None):
        """Rời ô tìm kiếm khi người dùng bấm vào vùng thông tin tài khoản."""
        self.parent.focus_set()
        self.parent.after_idle(self.update_search_placeholder)
        return "break"

    def update_search_placeholder(self, *args):
        if self.var_search.get() or self.entry_search.focus_get() == self.entry_search:
            self.search_placeholder.place_forget()
        else:
            self.search_placeholder.place(x=4, rely=0.5, anchor="w")

    def on_search_enter(self, event=None):
        self.search_accounts()
        return "break"

    def show_all_accounts(self):
        self.var_search.set("")
        self.btn_tat_ca.focus_set()
        self.load_accounts()
        self.parent.after_idle(self.update_search_placeholder)

    # =========================================================
    # LOAD ACCOUNT
    # =========================================================

    def refresh_form(self):
        """Tải lại danh sách và xóa toàn bộ dữ liệu đang hiển thị trên form."""
        self.var_search.set("")

        for variable in (
            self.var_id,
            self.var_ma_nv,
            self.var_username,
            self.var_ho_ten,
            self.var_email,
            self.var_vai_tro,
            self.var_trang_thai,
        ):
            variable.set("")

        selected = self.tree.selection()
        if selected:
            self.tree.selection_remove(*selected)
        self.tree.focus("")

        self.load_accounts()
        self.parent.focus_set()
        self.parent.after_idle(self.update_search_placeholder)

    def load_accounts(self):

        conn = get_db_connection()

        if not conn:
            return

        try:

            cursor = conn.cursor(
                dictionary=True
            )

            query = """
                SELECT
                    nd.id,
                    nv.ma_nv,
                    pb.ten_phong_ban,
                    nd.ho_ten,
                    nd.ten_dang_nhap,
                    nd.email,
                    nd.vai_tro,
                    nd.trang_thai
                FROM nguoi_dung nd
                LEFT JOIN nhan_vien nv
                    ON nv.nguoi_dung_id = nd.id
                LEFT JOIN phong_ban pb
                    ON pb.ma_phong_ban = nv.ma_phong_ban
                ORDER BY nd.id ASC
            """

            cursor.execute(query)

            rows = cursor.fetchall()

            self.refresh_table(rows)

        except Error as e:

            show_database_error(e, "tải danh sách tài khoản")

        finally:
            conn.close()

    # =========================================================
    # REFRESH TABLE
    # =========================================================

    def refresh_table(self, rows):

        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in rows:

            role_display = {
                "Admin": "Quản trị viên",
                "TruongPhong": "Trưởng phòng",
                "NhanVien": "Nhân viên"
            }.get(
                row["vai_tro"],
                row["vai_tro"]
            )

            status_display = (
                "Hoạt động"
                if row["trang_thai"] == 1
                else "Đã khóa"
            )

            self.tree.insert(
                "",
                tk.END,
                values=(
                    row["id"],
                    row["ma_nv"] or "",
                    row["ten_phong_ban"] or "",
                    row["ho_ten"],
                    row["ten_dang_nhap"],
                    row["email"],
                    role_display,
                    status_display
                )
            )

    # =========================================================
    # SELECT
    # =========================================================

    def on_select(self, event=None):

        selected = self.tree.selection()

        if not selected:
            return

        values = self.tree.item(
            selected[0],
            "values"
        )

        self.var_id.set(values[0])
        self.var_ma_nv.set(values[1])
        self.var_ho_ten.set(values[3])
        self.var_username.set(values[4])
        self.var_email.set(values[5])

        role_map = {
            "Quản trị viên": "Admin",
            "Trưởng phòng": "TruongPhong",
            "Nhân viên": "NhanVien"
        }

        self.var_vai_tro.set(
            role_map.get(
                values[6],
                values[6]
            )
        )

        status = (
            "Hoạt động"
            if values[7] == "Hoạt động"
            else "Khóa"
        )

        self.var_trang_thai.set(status)

    # =========================================================
    # SEARCH
    # =========================================================

    def search_accounts(self):

        keyword = self.var_search.get().strip()

        if not keyword:
            self.load_accounts()
            return

        conn = get_db_connection()

        if not conn:
            return

        try:

            cursor = conn.cursor(
                dictionary=True
            )

            p = f"%{keyword}%"

            query = """
                SELECT
                    nd.id,
                    nv.ma_nv,
                    pb.ten_phong_ban,
                    nd.ho_ten,
                    nd.ten_dang_nhap,
                    nd.email,
                    nd.vai_tro,
                    nd.trang_thai
                FROM nguoi_dung nd
                LEFT JOIN nhan_vien nv
                    ON nv.nguoi_dung_id = nd.id
                LEFT JOIN phong_ban pb
                    ON pb.ma_phong_ban = nv.ma_phong_ban
                WHERE
                    CAST(nd.id AS CHAR) LIKE %s
                    OR nd.ten_dang_nhap LIKE %s
                    OR nd.ho_ten LIKE %s
                    OR nd.email LIKE %s
                    OR nv.ma_nv LIKE %s
                    OR pb.ten_phong_ban LIKE %s
                ORDER BY nd.id ASC
            """

            cursor.execute(
                query,
                (p, p, p, p, p, p)
            )

            self.refresh_table(
                cursor.fetchall()
            )

        except Error as e:

            show_database_error(e, "tìm kiếm tài khoản")

        finally:
            conn.close()

    # =========================================================
    # RESET PASSWORD
    # =========================================================

    def reset_password(self):

        account_id = self.var_id.get().strip()

        username = self.var_username.get().strip()

        if not account_id:
            messagebox.showwarning(
                "Cảnh báo",
                "Vui lòng chọn tài khoản!"
            )
            return

        # Luồng đăng nhập hiện tại so sánh mật khẩu trực tiếp với CSDL.
        default_password = "123456"

        conn = get_db_connection()

        if not conn:
            return

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT trang_thai
                FROM nhan_vien
                WHERE nguoi_dung_id=%s
                LIMIT 1
                FOR UPDATE
                """,
                (account_id,),
            )
            employee = cursor.fetchone()
            if employee and employee[0] == "Đã nghỉ việc":
                conn.rollback()
                messagebox.showwarning(
                    "Không thể reset mật khẩu",
                    "Không thể đặt lại mật khẩu cho tài khoản của nhân viên "
                    "đã nghỉ việc.",
                )
                return

            if not messagebox.askyesno(
                "Xác nhận",
                f"Đặt lại mật khẩu của tài khoản "
                f"{username} về 123456?"
            ):
                conn.rollback()
                return

            cursor.execute(
                """
                UPDATE nguoi_dung
                SET mat_khau=%s,
                    so_lan_dang_nhap_sai=0
                WHERE id=%s
                """,
                (
                    default_password,
                    account_id
                )
            )

            conn.commit()

            messagebox.showinfo(
                "Thành công",
                f"Mật khẩu của {username} "
                "đã được đặt lại thành 123456."
            )

        except Error as e:

            conn.rollback()

            show_database_error(e, "đặt lại mật khẩu")

        finally:
            conn.close()

    # =========================================================
    # LOCK
    # =========================================================

    def lock_account(self):

        self.change_status(0)

    # =========================================================
    # UNLOCK
    # =========================================================

    def unlock_account(self):

        self.change_status(1)

    # =========================================================
    # CHANGE STATUS
    # =========================================================

    def change_status(self, status):

        requested_status = 1 if status == 1 else 0

        account_id = self.var_id.get().strip()

        username = self.var_username.get().strip()

        if not account_id:
            messagebox.showwarning(
                "Cảnh báo",
                "Vui lòng chọn tài khoản!"
            )
            return

        # Không cho Admin tự khóa chính mình
        if (
            str(self.user_info.get("id"))
            == account_id
            and requested_status == 0
        ):
            messagebox.showwarning(
                "Không có quyền",
                "Bạn không thể tự khóa tài khoản "
                "Admin của chính mình!"
            )
            return

        conn = get_db_connection()

        if not conn:
            return

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT nd.trang_thai, nv.trang_thai
                FROM nguoi_dung nd
                LEFT JOIN nhan_vien nv
                    ON nv.nguoi_dung_id=nd.id
                WHERE nd.id=%s
                FOR UPDATE
                """,
                (account_id,),
            )
            account = cursor.fetchone()
            if not account:
                conn.rollback()
                messagebox.showwarning(
                    "Không tìm thấy tài khoản",
                    "Tài khoản đã chọn không còn tồn tại. Hãy làm mới danh sách.",
                )
                return

            current_status, employee_status = account

            if requested_status == 1 and employee_status == "Đã nghỉ việc":
                conn.rollback()
                messagebox.showwarning(
                    "Không thể mở khóa",
                    "Nhân viên này đang ở trạng thái 'Đã nghỉ việc'. "
                    "Hãy cập nhật lại trạng thái trong form Nhân viên trước.",
                )
                return

            if int(current_status) == requested_status:
                conn.rollback()
                self.show_unchanged_status(username, requested_status)
                return

            cursor.execute(
                """
                UPDATE nguoi_dung
                SET trang_thai=%s,
                    so_lan_dang_nhap_sai=CASE
                        WHEN %s=1 THEN 0
                        ELSE so_lan_dang_nhap_sai
                    END
                WHERE id=%s
                  AND trang_thai<>%s
                """,
                (
                    requested_status,
                    requested_status,
                    account_id,
                    requested_status,
                )
            )

            if cursor.rowcount == 0:
                conn.rollback()
                self.show_unchanged_status(username, requested_status)
                return

            conn.commit()

            messagebox.showinfo(
                "Thành công",
                f"Đã {'khóa' if requested_status == 0 else 'mở khóa'} "
                f"tài khoản {username}."
            )

            self.load_accounts()

        except Error as e:

            conn.rollback()

            show_database_error(e, "thay đổi trạng thái tài khoản")

        finally:
            conn.close()

    def show_unchanged_status(self, username, status):
        current_state = "đã bị khóa" if status == 0 else "đang hoạt động"
        messagebox.showinfo(
            "Không có thay đổi",
            f"Tài khoản {username} {current_state}. Không cập nhật CSDL.",
        )
