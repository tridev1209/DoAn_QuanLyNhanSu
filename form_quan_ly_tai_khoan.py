import hashlib
import tkinter as tk
from tkinter import messagebox, ttk

from db_connection import get_db_connection
from mysql.connector import Error


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
    # HASH PASSWORD
    # =========================================================

    def hash_password(self, password):

        return hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()

    # =========================================================
    # GIAO DIỆN
    # =========================================================

    def create_widgets(self):

        title = tk.Label(
            self.parent,
            text="QUẢN LÝ TÀI KHOẢN NGƯỜI DÙNG",
            font=("Helvetica", 16, "bold"),
            bg="#f8fafc",
            fg="#0f172a"
        )

        title.pack(
            anchor="w",
            pady=(0, 15)
        )

        # =====================================================
        # THANH TÌM KIẾM
        # =====================================================

        search_frame = tk.Frame(
            self.parent,
            bg="#f8fafc"
        )

        search_frame.pack(
            fill=tk.X,
            pady=(0, 10)
        )

        tk.Label(
            search_frame,
            text="Tìm kiếm:",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc"
        ).pack(side=tk.LEFT)

        entry_search = ttk.Entry(
            search_frame,
            textvariable=self.var_search,
            width=40
        )

        entry_search.pack(
            side=tk.LEFT,
            padx=8
        )

        tk.Button(
            search_frame,
            text="🔍 Tìm",
            bg="#2563eb",
            fg="white",
            bd=0,
            padx=15,
            pady=5,
            command=self.search_accounts
        ).pack(side=tk.LEFT)

        tk.Button(
            search_frame,
            text="🔄 Làm mới",
            bg="#64748b",
            fg="white",
            bd=0,
            padx=15,
            pady=5,
            command=self.load_accounts
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        # =====================================================
        # BẢNG TÀI KHOẢN
        # =====================================================

        table_frame = tk.Frame(
            self.parent,
            bg="white"
        )

        table_frame.pack(
            fill=tk.BOTH,
            expand=True
        )

        columns = (
            "id",
            "ma_nv",
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
            "ho_ten": "Họ và tên",
            "username": "Tên đăng nhập",
            "email": "Email",
            "vai_tro": "Vai trò",
            "trang_thai": "Trạng thái"
        }

        widths = {
            "id": 50,
            "ma_nv": 90,
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

        # =====================================================
        # FORM THÔNG TIN
        # =====================================================

        info_frame = tk.LabelFrame(
            self.parent,
            text=" Thông tin tài khoản ",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
            padx=15,
            pady=12
        )

        info_frame.pack(
            fill=tk.X,
            pady=(10, 0)
        )

        # ID
        tk.Label(
            info_frame,
            text="ID:"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Entry(
            info_frame,
            textvariable=self.var_id,
            state="readonly",
            width=20
        ).grid(
            row=0,
            column=1,
            padx=5,
            pady=5
        )

        # Mã NV
        tk.Label(
            info_frame,
            text="Mã NV:"
        ).grid(
            row=0,
            column=2,
            sticky="w",
            padx=5
        )

        ttk.Entry(
            info_frame,
            textvariable=self.var_ma_nv,
            state="readonly",
            width=20
        ).grid(
            row=0,
            column=3,
            padx=5
        )

        # Username
        tk.Label(
            info_frame,
            text="Tên đăng nhập:"
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Entry(
            info_frame,
            textvariable=self.var_username,
            state="readonly",
            width=20
        ).grid(
            row=1,
            column=1,
            padx=5
        )

        # Họ tên
        tk.Label(
            info_frame,
            text="Họ tên:"
        ).grid(
            row=1,
            column=2,
            sticky="w",
            padx=5
        )

        ttk.Entry(
            info_frame,
            textvariable=self.var_ho_ten,
            state="readonly",
            width=25
        ).grid(
            row=1,
            column=3,
            padx=5
        )

        # Email
        tk.Label(
            info_frame,
            text="Email:"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        ttk.Entry(
            info_frame,
            textvariable=self.var_email,
            state="readonly",
            width=25
        ).grid(
            row=2,
            column=1,
            padx=5
        )

        # Vai trò
        tk.Label(
            info_frame,
            text="Vai trò:"
        ).grid(
            row=2,
            column=2,
            sticky="w",
            padx=5
        )

        self.cb_role = ttk.Combobox(
            info_frame,
            textvariable=self.var_vai_tro,
            values=[
                "Admin",
                "TruongPhong",
                "NhanVien"
            ],
            state="readonly",
            width=20
        )

        self.cb_role.grid(
            row=2,
            column=3,
            padx=5
        )

        # Trạng thái
        tk.Label(
            info_frame,
            text="Trạng thái:"
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )

        self.cb_status = ttk.Combobox(
            info_frame,
            textvariable=self.var_trang_thai,
            values=[
                "Hoạt động",
                "Khóa"
            ],
            state="readonly",
            width=20
        )

        self.cb_status.grid(
            row=3,
            column=1,
            padx=5
        )

        # =====================================================
        # BUTTON
        # =====================================================

        button_frame = tk.Frame(
            info_frame,
            bg="#f8fafc"
        )

        button_frame.grid(
            row=4,
            column=0,
            columnspan=4,
            pady=12
        )

        tk.Button(
            button_frame,
            text="💾 Lưu thay đổi",
            bg="#2563eb",
            fg="white",
            bd=0,
            padx=15,
            pady=7,
            command=self.update_account
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        tk.Button(
            button_frame,
            text="🔑 Reset mật khẩu",
            bg="#f59e0b",
            fg="white",
            bd=0,
            padx=15,
            pady=7,
            command=self.reset_password
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        tk.Button(
            button_frame,
            text="🔒 Khóa tài khoản",
            bg="#dc2626",
            fg="white",
            bd=0,
            padx=15,
            pady=7,
            command=self.lock_account
        ).pack(
            side=tk.LEFT,
            padx=5
        )

        tk.Button(
            button_frame,
            text="🔓 Mở khóa",
            bg="#16a34a",
            fg="white",
            bd=0,
            padx=15,
            pady=7,
            command=self.unlock_account
        ).pack(
            side=tk.LEFT,
            padx=5
        )

    # =========================================================
    # LOAD ACCOUNT
    # =========================================================

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
                    nd.ho_ten,
                    nd.ten_dang_nhap,
                    nd.email,
                    nd.vai_tro,
                    nd.trang_thai
                FROM nguoi_dung nd
                LEFT JOIN nhan_vien nv
                    ON nv.nguoi_dung_id = nd.id
                ORDER BY nd.id ASC
            """

            cursor.execute(query)

            rows = cursor.fetchall()

            self.refresh_table(rows)

        except Error as e:

            messagebox.showerror(
                "Lỗi CSDL",
                str(e)
            )

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
        self.var_ho_ten.set(values[2])
        self.var_username.set(values[3])
        self.var_email.set(values[4])

        role_map = {
            "Quản trị viên": "Admin",
            "Trưởng phòng": "TruongPhong",
            "Nhân viên": "NhanVien"
        }

        self.var_vai_tro.set(
            role_map.get(
                values[5],
                values[5]
            )
        )

        status = (
            "Hoạt động"
            if values[6] == "Hoạt động"
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
                    nd.ho_ten,
                    nd.ten_dang_nhap,
                    nd.email,
                    nd.vai_tro,
                    nd.trang_thai
                FROM nguoi_dung nd
                LEFT JOIN nhan_vien nv
                    ON nv.nguoi_dung_id = nd.id
                WHERE
                    nd.ten_dang_nhap LIKE %s
                    OR nd.ho_ten LIKE %s
                    OR nd.email LIKE %s
                    OR nv.ma_nv LIKE %s
                ORDER BY nd.id ASC
            """

            cursor.execute(
                query,
                (p, p, p, p)
            )

            self.refresh_table(
                cursor.fetchall()
            )

        except Error as e:

            messagebox.showerror(
                "Lỗi",
                str(e)
            )

        finally:
            conn.close()

    # =========================================================
    # UPDATE ACCOUNT
    # =========================================================

    def update_account(self):

        account_id = self.var_id.get().strip()

        if not account_id:
            messagebox.showwarning(
                "Cảnh báo",
                "Vui lòng chọn tài khoản!"
            )
            return

        # Không cho Admin hiện tại tự hạ quyền tài khoản của chính mình
        if str(self.user_info.get("id")) == account_id:

            if self.var_vai_tro.get() != "Admin":

                messagebox.showwarning(
                    "Không có quyền",
                    "Bạn không thể tự hạ quyền Admin "
                    "của chính mình!"
                )
                return

        status_value = (
            1
            if self.var_trang_thai.get() == "Hoạt động"
            else 0
        )

        conn = get_db_connection()

        if not conn:
            return

        try:

            cursor = conn.cursor()

            query = """
                UPDATE nguoi_dung
                SET
                    vai_tro=%s,
                    trang_thai=%s
                WHERE id=%s
            """

            cursor.execute(
                query,
                (
                    self.var_vai_tro.get(),
                    status_value,
                    account_id
                )
            )

            conn.commit()

            messagebox.showinfo(
                "Thành công",
                "Đã cập nhật tài khoản!"
            )

            self.load_accounts()

        except Error as e:

            conn.rollback()

            messagebox.showerror(
                "Lỗi CSDL",
                str(e)
            )

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

        if not messagebox.askyesno(
            "Xác nhận",
            f"Đặt lại mật khẩu của tài khoản "
            f"{username} về 123456?"
        ):
            return

        password_hash = self.hash_password(
            "123456"
        )

        conn = get_db_connection()

        if not conn:
            return

        try:

            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE nguoi_dung
                SET mat_khau=%s
                WHERE id=%s
                """,
                (
                    password_hash,
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

            messagebox.showerror(
                "Lỗi CSDL",
                str(e)
            )

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
            and status == 0
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
                UPDATE nguoi_dung
                SET trang_thai=%s
                WHERE id=%s
                """,
                (
                    status,
                    account_id
                )
            )

            # Đồng bộ trạng thái nhân viên
            if status == 0:

                cursor.execute(
                    """
                    UPDATE nhan_vien
                    SET trang_thai='Đã nghỉ việc'
                    WHERE nguoi_dung_id=%s
                    """,
                    (account_id,)
                )

            else:

                cursor.execute(
                    """
                    UPDATE nhan_vien
                    SET trang_thai='Đang làm việc'
                    WHERE nguoi_dung_id=%s
                    """,
                    (account_id,)
                )

            conn.commit()

            messagebox.showinfo(
                "Thành công",
                f"Đã {'khóa' if status == 0 else 'mở khóa'} "
                f"tài khoản {username}."
            )

            self.load_accounts()

        except Error as e:

            conn.rollback()

            messagebox.showerror(
                "Lỗi CSDL",
                str(e)
            )

        finally:
            conn.close()