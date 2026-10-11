import datetime
import re
import hashlib
import tkinter as tk
from tkinter import messagebox, ttk
from db_connection import get_db_connection
from mysql.connector import Error

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()

class EmployeeManagementForm:

    def __init__(self, parent_frame, user_info=None):
        self.parent = parent_frame

        # Dữ liệu tài khoản đăng nhập (Mặc định Admin nếu chạy test độc lập)
        self.user_info = user_info or {
            "id": 1,
            "ten_dang_nhap": "admin",
            "vai_tro": "Admin",
            "ho_ten": "Quản trị viên",
        }
        self.role = self.user_info.get("vai_tro", "NhanVien")
        self.user_login_name = self.user_info.get("ten_dang_nhap", "")
        self.user_db_id = self.user_info.get("id", None)

        # Thông tin phòng ban & Mã NV thực tế của Trưởng phòng
        self.user_ma_phong_ban = None
        self.user_actual_ma_nv = None

        # Biến quản lý giao diện
        self.var_ma_nv = tk.StringVar()
        self.var_ten_nv = tk.StringVar()
        self.var_gioi_tinh = tk.StringVar(value="Nam")
        self.var_ngay_sinh = tk.StringVar(value="01/01/1995")
        self.var_email = tk.StringVar()
        self.var_sdt = tk.StringVar()
        self.var_phong_ban = tk.StringVar()
        self.var_chuc_vu = tk.StringVar()
        self.var_luong_cb = tk.StringVar(value="12.000.000")
        self.var_trang_thai = tk.StringVar(value="Đang làm việc")
        self.var_tim_kiem = tk.StringVar()

        self.dict_phong_ban = {}
        self.dict_tien_to = {}
        self.dict_chuc_vu = {}

        self.get_user_department_and_id()
        self.create_widgets()
        self.load_combobox_data()
        self.load_data()

    def get_user_department_and_id(self):
        """Lấy chính xác Mã phòng ban và Mã NV thực tế của Trưởng phòng"""
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ma_nv, ma_phong_ban 
                FROM nhan_vien 
                WHERE nguoi_dung_id = %s OR ma_nv = %s
            """
            cursor.execute(query, (self.user_db_id, self.user_login_name))
            row = cursor.fetchone()
            if row:
                self.user_ma_phong_ban = row["ma_phong_ban"]
                self.user_actual_ma_nv = row["ma_nv"]
        except Error as e:
            print(f"Lỗi lấy thông tin Trưởng phòng: {e}")
        finally:
            conn.close()

    # --- CÁC HÀM HỖ TRỢ ĐỊNH DẠNG VÀ PARSE TIỀN TỆ ---
    def format_money_str(self, val):
        try:
            num = int(round(float(val)))
            return f"{num:,}".replace(",", ".")
        except (ValueError, TypeError):
            return "0"

    def parse_money(self, val_str):
        if not val_str:
            return 0.0
        digits = re.sub(r"\D", "", str(val_str))
        return float(digits) if digits else 0.0

    # --- CÁC HÀM XỬ LÝ LỌC KÝ TỰ THEO THỜI GIAN THỰC ---
    def on_date_key_release(self, event, var):
        raw = str(var.get())
        cleaned = re.sub(r"[^0-9/]", "", raw)
        if len(cleaned) > 10:
            cleaned = cleaned[:10]
        var.set(cleaned)
        event.widget.icursor(tk.END)

    def on_digits_only_key_release(self, event, var, max_len=11):
        raw = str(var.get())
        digits = re.sub(r"\D", "", raw)
        if len(digits) > max_len:
            digits = digits[:max_len]
        var.set(digits)
        event.widget.icursor(tk.END)

    def on_money_key_release(self, event, var):
        raw = str(var.get())
        digits = re.sub(r"\D", "", raw)
        if not digits:
            var.set("")
        else:
            num = int(digits)
            formatted = f"{num:,}".replace(",", ".")
            var.set(formatted)
            event.widget.icursor(tk.END)

    def on_ma_nv_key_release(self, event, var):
        raw = str(var.get())
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        var.set(cleaned)
        event.widget.icursor(tk.END)

    def on_ho_ten_key_release(self, event, var):
        raw = str(var.get())
        cleaned = re.sub(
            r"[^a-zA-ZàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s]",
            "",
            raw,
        )
        var.set(cleaned)
        event.widget.icursor(tk.END)

    def capitalize_name(self, name_str):
        words = name_str.strip().split()
        return " ".join(word.capitalize() for word in words)

    def create_widgets(self):
        tk.Label(
            self.parent,
            text="QUẢN LÝ THÔNG TIN NHÂN VIÊN",
            font=("Helvetica", 13, "bold"),
            fg="#1e293b",
            bg="#f8fafc",
        ).pack(anchor="w", pady=(0, 8))

        # --- KHUNG NHẬP LIỆU ---
        input_frame = tk.LabelFrame(
            self.parent,
            text=" Nhập liệu thông tin chi tiết nhân viên ",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            padx=12,
            pady=10,
        )
        input_frame.pack(fill=tk.X, pady=(0, 8))

        # Nhóm 1: Định danh & Phân quyền
        tk.Label(
            input_frame,
            text="Phòng ban (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=0, sticky="w", pady=5)
        self.cb_pb = ttk.Combobox(
            input_frame,
            textvariable=self.var_phong_ban,
            width=18,
            state="readonly",
            font=("Helvetica", 10),
        )
        self.cb_pb.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.cb_pb.bind("<<ComboboxSelected>>", self.on_phong_ban_changed)

        tk.Label(
            input_frame,
            text="Mã NV (Tự/Sửa) (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=2, sticky="w", pady=5, padx=(15, 0))
        self.entry_ma_nv = tk.Entry(
            input_frame,
            textvariable=self.var_ma_nv,
            width=15,
            bg="white",
            font=("Helvetica", 10, "bold"),
        )
        self.entry_ma_nv.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.entry_ma_nv.bind(
            "<KeyRelease>",
            lambda e: self.on_ma_nv_key_release(e, self.var_ma_nv),
        )

        tk.Label(
            input_frame,
            text="Chức vụ (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=4, sticky="w", pady=5, padx=(15, 0))
        self.cb_cv = ttk.Combobox(
            input_frame,
            textvariable=self.var_chuc_vu,
            width=20,
            state="readonly",
            font=("Helvetica", 10),
        )
        self.cb_cv.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        # Nhóm 2: Thông tin cá nhân cơ bản
        tk.Label(
            input_frame,
            text="Họ & Tên (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=1, column=0, sticky="w", pady=5)
        entry_ten = tk.Entry(
            input_frame,
            textvariable=self.var_ten_nv,
            width=20,
            font=("Helvetica", 10),
        )
        entry_ten.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        entry_ten.bind(
            "<KeyRelease>",
            lambda e: self.on_ho_ten_key_release(e, self.var_ten_nv),
        )

        tk.Label(
            input_frame,
            text="Giới tính:",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=1, column=2, sticky="w", pady=5, padx=(15, 0))
        ttk.Combobox(
            input_frame,
            textvariable=self.var_gioi_tinh,
            values=["Nam", "Nữ"],
            width=13,
            state="readonly",
            font=("Helvetica", 10),
        ).grid(row=1, column=3, padx=5, pady=5, sticky="w")

        tk.Label(
            input_frame,
            text="Ngày sinh (DD/MM/YYYY):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=1, column=4, sticky="w", pady=5, padx=(15, 0))

        entry_ngay_sinh = tk.Entry(
            input_frame,
            textvariable=self.var_ngay_sinh,
            width=20,
            font=("Helvetica", 10),
        )
        entry_ngay_sinh.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        entry_ngay_sinh.bind(
            "<KeyRelease>",
            lambda e: self.on_date_key_release(e, self.var_ngay_sinh),
        )

        # Nhóm 3: Thông tin liên hệ & Tài chính
        tk.Label(
            input_frame,
            text="Email (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=2, column=0, sticky="w", pady=5)
        tk.Entry(
            input_frame,
            textvariable=self.var_email,
            width=20,
            font=("Helvetica", 10),
        ).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        tk.Label(
            input_frame,
            text="Số ĐT (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=2, column=2, sticky="w", pady=5, padx=(15, 0))
        entry_sdt = tk.Entry(
            input_frame,
            textvariable=self.var_sdt,
            width=15,
            font=("Helvetica", 10),
        )
        entry_sdt.grid(row=2, column=3, padx=5, pady=5, sticky="w")
        entry_sdt.bind(
            "<KeyRelease>",
            lambda e: self.on_digits_only_key_release(
                e, self.var_sdt, max_len=11
            ),
        )

        tk.Label(
            input_frame,
            text="Lương cơ bản (đ):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=2, column=4, sticky="w", pady=5, padx=(15, 0))
        entry_luong = tk.Entry(
            input_frame,
            textvariable=self.var_luong_cb,
            width=20,
            font=("Helvetica", 10),
        )
        entry_luong.grid(row=2, column=5, padx=5, pady=5, sticky="w")
        entry_luong.bind(
            "<KeyRelease>",
            lambda e: self.on_money_key_release(e, self.var_luong_cb),
        )

        # Nhóm 4: Trạng thái làm việc
        tk.Label(
            input_frame,
            text="Trạng thái:",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=3, column=0, sticky="w", pady=5)
        ttk.Combobox(
            input_frame,
            textvariable=self.var_trang_thai,
            values=["Đang làm việc", "Thử việc", "Đã nghỉ việc"],
            width=18,
            state="readonly",
            font=("Helvetica", 10),
        ).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # --- THANH CÔNG CỤ ---
        action_frame = tk.Frame(self.parent, bg="#f8fafc")
        action_frame.pack(fill=tk.X, pady=6)

        btn_sub_frame = tk.Frame(action_frame, bg="#f8fafc")
        btn_sub_frame.pack(side=tk.LEFT)

        tk.Button(
            btn_sub_frame,
            text="➕ Thêm",
            font=("Helvetica", 10, "bold"),
            bg="#2563eb",
            fg="white",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.them_nhan_vien,
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btn_sub_frame,
            text="✏️ Sửa",
            font=("Helvetica", 10, "bold"),
            bg="#eab308",
            fg="white",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.sua_nhan_vien,
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btn_sub_frame,
            text="🚫 Cho nghỉ việc",
            font=("Helvetica", 10, "bold"),
            bg="#f97316",
            fg="white",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.cho_nghi_viec,
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btn_sub_frame,
            text="🗑️ Xóa vĩnh viễn",
            font=("Helvetica", 10, "bold"),
            bg="#dc2626",
            fg="white",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.xoa_vinh_vien,
        ).pack(side=tk.LEFT, padx=3)
        tk.Button(
            btn_sub_frame,
            text="🔄 Làm mới",
            font=("Helvetica", 10, "bold"),
            bg="#64748b",
            fg="white",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.lam_moi,
        ).pack(side=tk.LEFT, padx=3)

        search_sub_frame = tk.Frame(action_frame, bg="#f8fafc")
        search_sub_frame.pack(side=tk.RIGHT)

        tk.Label(
            search_sub_frame,
            text="Tìm kiếm:",
            bg="#f8fafc",
            font=("Helvetica", 10, "bold"),
        ).pack(side=tk.LEFT, padx=5)

        self.placeholder_text = "Nhập mã, tên hoặc SĐT..."
        self.entry_tim_kiem = tk.Entry(
            search_sub_frame,
            textvariable=self.var_tim_kiem,
            width=22,
            font=("Helvetica", 10),
            fg="grey",
        )
        self.entry_tim_kiem.pack(side=tk.LEFT, padx=4)

        self.entry_tim_kiem.insert(0, self.placeholder_text)
        self.entry_tim_kiem.bind("<FocusIn>", self.on_search_focus_in)
        self.entry_tim_kiem.bind("<FocusOut>", self.on_search_focus_out)

        tk.Button(
            search_sub_frame,
            text="🔍 Tìm",
            font=("Helvetica", 10, "bold"),
            bg="#0ea5e9",
            fg="white",
            padx=10,
            pady=4,
            bd=0,
            command=self.tim_kiem,
        ).pack(side=tk.LEFT, padx=2)
        tk.Button(
            search_sub_frame,
            text="Tất cả",
            font=("Helvetica", 10),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=4,
            bd=0,
            command=self.load_data,
        ).pack(side=tk.LEFT, padx=2)

        # --- BẢNG HIỂN THỊ DỮ LIỆU ---
        table_frame = tk.Frame(self.parent)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        style.configure("Treeview", font=("Helvetica", 10), rowheight=24)

        self.columns_def = (
            "ma_nv",
            "ten_nv",
            "gioi_tinh",
            "ngay_sinh",
            "email",
            "sdt",
            "phong_ban",
            "chuc_vu",
            "luong_cb",
            "trang_thai",
        )
        self.tree = ttk.Treeview(
            table_frame, columns=self.columns_def, show="headings", height=10
        )

        self.context_menu = tk.Menu(self.parent, tearoff=0)
        self.context_menu = tk.Menu(self.parent, tearoff=0)

        self.context_menu.add_command(
            label="✏️ Chỉnh sửa nhân viên này",
            command=self.context_edit_nhan_vien,
        )

        self.context_menu.add_separator()

        self.context_menu.add_command(
            label="🚫 Cho nghỉ việc",
            command=self.context_resign_nhan_vien,
        )

        self.context_menu.add_command(
            label="🗑️ Xóa vĩnh viễn",
            command=self.context_delete_nhan_vien,
        )

        headers = {
            "ma_nv": "Mã NV",
            "ten_nv": "Họ và Tên",
            "gioi_tinh": "Giới tính",
            "ngay_sinh": "Ngày sinh",
            "email": "Email",
            "sdt": "Số ĐT",
            "phong_ban": "Phòng ban",
            "chuc_vu": "Chức vụ",
            "luong_cb": "Lương CB (đ)",
            "trang_thai": "Trạng thái",
        }
        widths = {
            "ma_nv": 70,
            "ten_nv": 140,
            "gioi_tinh": 65,
            "ngay_sinh": 90,
            "email": 140,
            "sdt": 95,
            "phong_ban": 115,
            "chuc_vu": 115,
            "luong_cb": 110,
            "trang_thai": 100,
        }

        for col in self.columns_def:
            self.tree.heading(col, text=headers[col])
            self.tree.column(
                col,
                width=widths[col],
                anchor=(
                    tk.CENTER
                    if col not in ("ten_nv", "email", "phong_ban", "chuc_vu")
                    else tk.W
                ),
            )

        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def on_search_focus_in(self, event):
        if self.entry_tim_kiem.get() == self.placeholder_text:
            self.entry_tim_kiem.delete(0, tk.END)
            self.entry_tim_kiem.config(fg="black")

    def on_search_focus_out(self, event):
        if not self.entry_tim_kiem.get().strip():
            self.entry_tim_kiem.insert(0, self.placeholder_text)
            self.entry_tim_kiem.config(fg="grey")

    # --- TỰ ĐỘNG CHỌN & CHỈ LỌC DUY NHẤT 1 PHÒNG BAN CHO TRƯỜNG PHÒNG ---
    def load_combobox_data(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT ma_phong_ban, ten_phong_ban, tien_to_ma FROM phong_ban"
            )
            pb_rows = cursor.fetchall()

            self.dict_phong_ban = {
                row["ten_phong_ban"]: row["ma_phong_ban"] for row in pb_rows
            }
            self.dict_tien_to = {
                row["ten_phong_ban"]: row["tien_to_ma"] for row in pb_rows
            }

            cursor.execute("""
            SELECT ma_chuc_vu, TRIM(ten_chuc_vu) AS ten_chuc_vu
            FROM chuc_vu
            ORDER BY ma_chuc_vu
            """)

            self.dict_chuc_vu = {
                row["ten_chuc_vu"].strip(): row["ma_chuc_vu"]
                for row in cursor.fetchall()
}

            # NẾU LÀ TRƯỜNG PHÒNG: CHỈ NẠP DUY NHẤT PHÒNG BAN MÀ TRƯỜNG PHÒNG ĐÓ QUẢN LÝ
            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                tp_ten_pb = None
                for ten_pb, ma_pb in self.dict_phong_ban.items():
                    if ma_pb == self.user_ma_phong_ban:
                        tp_ten_pb = ten_pb
                        break

                if tp_ten_pb:
                    # Gán danh sách values duy nhất 1 phòng ban
                    self.cb_pb["values"] = [tp_ten_pb]
                    self.var_phong_ban.set(tp_ten_pb)
                    self.cb_pb.config(state="disabled")  # Khóa giao diện
                    self.generate_employee_id()
            else:
                self.cb_pb["values"] = list(self.dict_phong_ban.keys())
                self.cb_pb.config(state="readonly")
                if self.dict_phong_ban:
                    self.cb_pb.current(0)
                    self.generate_employee_id()

            # --- PHÂN QUYỀN CHỨC VỤ ---
            if self.dict_chuc_vu:

                all_chuc_vu = list(self.dict_chuc_vu.keys())

                if self.role == "TruongPhong":
                    # Trưởng phòng không được chọn chức vụ "Trưởng phòng"
                    allowed_chuc_vu = [
                        cv for cv in all_chuc_vu
                        if cv.strip().lower() != "trưởng phòng"
                    ]
                else:
                    # Admin và các quyền khác được chọn tất cả chức vụ
                    allowed_chuc_vu = all_chuc_vu

                self.cb_cv["values"] = allowed_chuc_vu

                if allowed_chuc_vu:
                    self.cb_cv.current(0)
        except Error as e:
            print(f"Lỗi Combobox: {e}")
        finally:
            conn.close()

    def on_phong_ban_changed(self, event):
        self.generate_employee_id()

    def generate_employee_id(self):
        selected_pb_name = self.var_phong_ban.get()
        if not selected_pb_name:
            return

        prefix = self.dict_tien_to.get(selected_pb_name, "NV")
        ma_phong = self.dict_phong_ban.get(selected_pb_name)

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = """
                SELECT ma_nv FROM nhan_vien 
                WHERE ma_phong_ban = %s AND ma_nv LIKE %s
                ORDER BY ma_nv DESC LIMIT 1
            """
            cursor.execute(query, (ma_phong, f"{prefix}%"))
            row = cursor.fetchone()

            if row:
                last_id = row[0]  # Lấy chuỗi mã NV
                try:
                    number_part = int(last_id.replace(prefix, ""))
                    new_number = number_part + 1
                except ValueError:
                    new_number = 1
            else:
                new_number = 1

            new_ma_nv = f"{prefix}{new_number:03d}"
            self.var_ma_nv.set(new_ma_nv)
        except Error as e:
            print(f"Lỗi sinh mã NV: {e}")
        finally:
            conn.close()

    def validate_inputs(self):
        ma = self.var_ma_nv.get().strip()
        ten = self.capitalize_name(self.var_ten_nv.get())
        email = self.var_email.get().strip()
        sdt = self.var_sdt.get().strip()
        ngay_sinh_str = self.var_ngay_sinh.get().strip()
        selected_pb_name = self.var_phong_ban.get()

        self.var_ten_nv.set(ten)

        if not ma or not ten or not email or not sdt:
            messagebox.showwarning(
                "Cảnh báo",
                "Vui lòng nhập đầy đủ các thông tin bắt buộc (*): Mã NV, Họ Tên,"
                " Email, Số ĐT!",
            )
            return False

        if not re.match(r"^[A-Za-z0-9]+$", ma):
            messagebox.showwarning(
                "Cảnh báo",
                "Mã nhân viên không được chứa ký tự đặc biệt hoặc khoảng trắng!",
            )
            return False

        expected_prefix = self.dict_tien_to.get(selected_pb_name, "")
        if expected_prefix and not ma.startswith(expected_prefix):
            messagebox.showwarning(
                "Mã NV không hợp lệ với Phòng ban",
                f"Phòng '{selected_pb_name}' yêu cầu Mã nhân viên phải bắt đầu"
                f" bằng tiền tố '{expected_prefix}' (Ví dụ:"
                f" {expected_prefix}001)!\nVui lòng sửa lại mã nhân viên cho"
                " khớp.",
            )
            return False

        if not re.match(
            r"^[a-zA-ZàáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ\s]+$",
            ten,
        ):
            messagebox.showwarning(
                "Cảnh báo",
                "Họ và tên không được chứa chữ số hoặc ký tự đặc biệt!",
            )
            return False

        if len(ten) < 2:
            messagebox.showwarning("Cảnh báo", "Họ và tên nhân viên quá ngắn!")
            return False

        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            messagebox.showwarning(
                "Cảnh báo",
                "Định dạng Email không hợp lệ! (Ví dụ: name@company.com)",
            )
            return False

        sdt_regex = r"^0\d{9,10}$"
        if not re.match(sdt_regex, sdt):
            messagebox.showwarning(
                "Cảnh báo",
                "Số điện thoại phải bắt đầu bằng số 0 và bao gồm từ 10 đến 11"
                " chữ số!",
            )
            return False

        try:
            parsed_date = datetime.datetime.strptime(ngay_sinh_str, "%d/%m/%Y")
            today = datetime.datetime.now()
            age = (
                today.year
                - parsed_date.year
                - (
                    (today.month, today.day)
                    < (parsed_date.month, parsed_date.day)
                )
            )
            if age < 18 or age > 65:
                messagebox.showwarning(
                    "Cảnh báo",
                    f"Độ tuổi nhân viên hiện tại là {age} tuổi.\nĐộ tuổi lao"
                    " động hợp lệ phải từ 18 đến 65 tuổi!",
                )
                return False
        except ValueError:
            messagebox.showwarning(
                "Cảnh báo",
                "Định dạng ngày sinh không hợp lệ! Vui lòng nhập theo chuẩn"
                " DD/MM/YYYY.",
            )
            return False

        luong_val = self.parse_money(self.var_luong_cb.get())
        if luong_val <= 0:
            messagebox.showwarning(
                "Cảnh báo", "Lương cơ bản phải lớn hơn 0 đồng!"
            )
            return False

        return True

    def check_truong_phong_constraint(
        self, ma_phong_ban, ma_chuc_vu_truong_phong, current_ma_nv=""
    ):
        conn = get_db_connection()
        if not conn:
            return True
        try:
            cursor = conn.cursor()
            query = (
                "SELECT ma_nv FROM nhan_vien WHERE ma_phong_ban = %s AND"
                " ma_chuc_vu = %s"
            )
            cursor.execute(query, (ma_phong_ban, ma_chuc_vu_truong_phong))
            rows = cursor.fetchall()

            for row in rows:
                existing_nv = row[0]
                if existing_nv != current_ma_nv:
                    return False
            return True
        except Error as e:
            print(f"Lỗi kiểm tra trưởng phòng: {e}")
            return True
        finally:
            conn.close()

    def format_date_to_db(self, date_str):
        try:
            return datetime.datetime.strptime(date_str, "%d/%m/%Y").strftime(
                "%Y-%m-%d"
            )
        except Exception:
            return None

    # --- NẠP DỮ LIỆU BẢNG: CHỈ LỌC DUY NHẤT NHÂN VIÊN PHÒNG MÌNH VỚI QUA N TRƯỜNG PHÒNG ---
    def load_data(self):
        self.entry_tim_kiem.delete(0, tk.END)
        self.entry_tim_kiem.insert(0, self.placeholder_text)
        self.entry_tim_kiem.config(fg="grey")

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)

            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                query = """
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh, nv.email, nv.sdt, 
                           pb.ten_phong_ban, cv.ten_chuc_vu, nv.luong_co_ban, nv.trang_thai
                    FROM nhan_vien nv
                    LEFT JOIN phong_ban pb ON nv.ma_phong_ban = pb.ma_phong_ban
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    WHERE nv.ma_phong_ban = %s
                    ORDER BY nv.ma_nv ASC
                """
                cursor.execute(query, (self.user_ma_phong_ban,))
            else:
                query = """
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh, nv.email, nv.sdt, 
                           pb.ten_phong_ban, cv.ten_chuc_vu, nv.luong_co_ban, nv.trang_thai
                    FROM nhan_vien nv
                    LEFT JOIN phong_ban pb ON nv.ma_phong_ban = pb.ma_phong_ban
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    ORDER BY nv.ma_nv ASC
                """
                cursor.execute(query)

            self.refresh_table(cursor.fetchall())
        except Error as e:
            messagebox.showerror("Lỗi", str(e))
        finally:
            conn.close()

    def refresh_table(self, data_list):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in data_list:
            ngay_sinh = (
                row["ngay_sinh"].strftime("%d/%m/%Y") if row["ngay_sinh"] else ""
            )
            luong_cb = self.format_money_str(row["luong_co_ban"])
            self.tree.insert(
                "",
                tk.END,
                values=(
                    row["ma_nv"],
                    row["ho_ten"],
                    row["gioi_tinh"],
                    ngay_sinh,
                    row["email"],
                    row["sdt"],
                    row["ten_phong_ban"] or "",
                    row["ten_chuc_vu"] or "",
                    luong_cb,
                    row["trang_thai"],
                ),
            )

    def them_nhan_vien(self):
        # =========================================================
        # 1. KIỂM TRA DỮ LIỆU
        # =========================================================
        if not self.validate_inputs():
            return

        selected_pb_name = self.var_phong_ban.get().strip()
        selected_cv_name = self.var_chuc_vu.get().strip()

        ma = self.var_ma_nv.get().strip()
        ten = self.var_ten_nv.get().strip()
        sdt = self.var_sdt.get().strip()
        email = self.var_email.get().strip()
        luong_float = self.parse_money(self.var_luong_cb.get())

        ma_phong = self.dict_phong_ban.get(selected_pb_name)
        ma_chuc_vu = self.dict_chuc_vu.get(selected_cv_name)

        # =========================================================
        # 2. KIỂM TRA PHÒNG BAN
        # =========================================================
        if not ma_phong:
            messagebox.showwarning(
                "Cảnh báo",
                "Không xác định được phòng ban của nhân viên!"
            )
            return

        # =========================================================
        # 3. TRƯỞNG PHÒNG CHỈ ĐƯỢC THÊM NHÂN VIÊN
        #    TRONG PHÒNG BAN CỦA MÌNH
        # =========================================================
        if self.role == "TruongPhong":
            if not self.user_ma_phong_ban:
                messagebox.showerror(
                    "Lỗi",
                    "Không xác định được phòng ban của Trưởng phòng!"
                )
                return

            # Không tin dữ liệu từ Combobox,
            # lấy phòng ban trực tiếp từ tài khoản đăng nhập
            ma_phong = self.user_ma_phong_ban

        # =========================================================
        # 4. KIỂM TRA CHỨC VỤ TRƯỞNG PHÒNG
        # =========================================================
        if "trưởng phòng" in selected_cv_name.lower():

            # Trưởng phòng không được tạo thêm Trưởng phòng
            if self.role == "TruongPhong":
                messagebox.showwarning(
                    "Không có quyền",
                    "Trưởng phòng không được phép tạo nhân viên "
                    "có chức vụ Trưởng phòng!"
                )
                return

            # Admin tạo Trưởng phòng thì phải kiểm tra mỗi phòng
            # chỉ có tối đa 1 Trưởng phòng
            if not self.check_truong_phong_constraint(
                ma_phong,
                ma_chuc_vu
            ):
                messagebox.showwarning(
                    "Cảnh báo",
                    f"Phòng '{selected_pb_name}' đã có Trưởng phòng rồi!\n\n"
                    "Mỗi phòng chỉ được phép có 1 Trưởng phòng."
                )
                return

        # =========================================================
        # 5. XÁC ĐỊNH VAI TRÒ TÀI KHOẢN
        # =========================================================
        if "trưởng phòng" in selected_cv_name.lower():
            vai_tro = "TruongPhong"
        else:
            vai_tro = "NhanVien"

        # =========================================================
        # 6. KẾT NỐI DATABASE
        # =========================================================
        conn = get_db_connection()

        if not conn:
            messagebox.showerror(
                "Lỗi",
                "Không thể kết nối đến cơ sở dữ liệu!"
            )
            return

        try:
            cursor = conn.cursor()

            # =====================================================
            # 7. TẠO TÀI KHOẢN ĐĂNG NHẬP
            # =====================================================
            username = ma
            default_password = "123456"

            query_user = """
                INSERT INTO nguoi_dung
                (
                    ten_dang_nhap,
                    mat_khau,
                    ho_ten,
                    email,
                    vai_tro,
                    trang_thai
                )
                VALUES (%s, %s, %s, %s, %s, 1)
            """

            cursor.execute(
                query_user,
                (
                    username,
                    default_password,
                    ten,
                    email,
                    vai_tro
                )
            )

            # Lấy ID tài khoản vừa tạo
            nguoi_dung_id = cursor.lastrowid

            # =====================================================
            # 8. TẠO NHÂN VIÊN
            # =====================================================
            query_nv = """
                INSERT INTO nhan_vien
                (
                    ma_nv,
                    ho_ten,
                    gioi_tinh,
                    ngay_sinh,
                    email,
                    sdt,
                    ma_phong_ban,
                    ma_chuc_vu,
                    luong_co_ban,
                    trang_thai,
                    nguoi_dung_id
                )
                VALUES
                (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
            """

            cursor.execute(
                query_nv,
                (
                    ma,
                    ten,
                    self.var_gioi_tinh.get(),
                    self.format_date_to_db(
                        self.var_ngay_sinh.get()
                    ),
                    email,
                    sdt,
                    ma_phong,
                    ma_chuc_vu,
                    luong_float,
                    self.var_trang_thai.get(),
                    nguoi_dung_id
                )
            )

            # =====================================================
            # 9. HOÀN TẤT TRANSACTION
            # =====================================================
            conn.commit()

            messagebox.showinfo(
                "Thêm nhân viên thành công",
                f"Đã thêm nhân viên:\n\n"
                f"Mã NV: {ma}\n"
                f"Họ tên: {ten}\n"
                f"Phòng ban: {selected_pb_name}\n\n"
                f"--- TÀI KHOẢN ĐĂNG NHẬP ---\n"
                f"Tên đăng nhập: {ma}\n"
                f"Mật khẩu mặc định: 123456\n"
                f"Vai trò: {vai_tro}"
            )

            self.load_data()
            self.lam_moi()

        except Error as e:

            # Nếu xảy ra lỗi thì hủy TOÀN BỘ thao tác
            conn.rollback()

            messagebox.showerror(
                "Lỗi CSDL",
                f"Không thể thêm nhân viên và tạo tài khoản!\n\n{e}"
            )

        finally:
            cursor.close()
            conn.close()

    def sua_nhan_vien(self):
        ma = self.var_ma_nv.get().strip()

        if not ma:
            messagebox.showwarning(
                "Cảnh báo",
                "Vui lòng chọn nhân viên cần sửa!"
            )
            return

        # =========================================================
        # TRƯỞNG PHÒNG KHÔNG ĐƯỢC SỬA CHÍNH MÌNH
        # =========================================================
        if self.role == "TruongPhong" and (
            ma == self.user_actual_ma_nv
            or ma == self.user_login_name
        ):
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không thể tự chỉnh sửa hồ sơ "
                "của chính mình!\n\n"
                "Thông tin Trưởng phòng do Admin quản lý."
            )
            return

        if not self.validate_inputs():
            return

        selected_pb_name = self.var_phong_ban.get().strip()
        selected_cv_name = self.var_chuc_vu.get().strip()

        ma_phong = self.dict_phong_ban.get(selected_pb_name)
        ma_chuc_vu = self.dict_chuc_vu.get(selected_cv_name)

        # =========================================================
        # TRƯỞNG PHÒNG CHỈ ĐƯỢC SỬA TRONG PHÒNG MÌNH
        # =========================================================
        if self.role == "TruongPhong":

            if not self.user_ma_phong_ban:
                messagebox.showerror(
                    "Lỗi",
                    "Không xác định được phòng ban của Trưởng phòng!"
                )
                return

            ma_phong = self.user_ma_phong_ban

        # =========================================================
        # KIỂM TRA TRƯỞNG PHÒNG
        # =========================================================
        if "trưởng phòng" in selected_cv_name.lower():

            if self.role == "TruongPhong":
                messagebox.showwarning(
                    "Không có quyền",
                    "Trưởng phòng không được phép bổ nhiệm "
                    "nhân viên khác làm Trưởng phòng!"
                )
                return

            if not self.check_truong_phong_constraint(
                ma_phong,
                ma_chuc_vu,
                current_ma_nv=ma
            ):
                messagebox.showwarning(
                    "Cảnh báo",
                    f"Phòng '{selected_pb_name}' đã có "
                    "Trưởng phòng khác!\n\n"
                    "Mỗi phòng chỉ được phép có 1 Trưởng phòng."
                )
                return

        # =========================================================
        # XÁC ĐỊNH ROLE MỚI
        # =========================================================
        if "trưởng phòng" in selected_cv_name.lower():
            vai_tro = "TruongPhong"
        else:
            vai_tro = "NhanVien"

        luong_float = self.parse_money(
            self.var_luong_cb.get()
        )

        ten = self.var_ten_nv.get().strip()
        email = self.var_email.get().strip()
        gioi_tinh = self.var_gioi_tinh.get()
        ngay_sinh = self.format_date_to_db(
            self.var_ngay_sinh.get()
        )
        sdt = self.var_sdt.get().strip()
        trang_thai = self.var_trang_thai.get()

        conn = get_db_connection()

        if not conn:
            return

        try:
            cursor = conn.cursor()

            # =====================================================
            # 1. CẬP NHẬT NHÂN VIÊN
            # =====================================================
            query_nv = """
                UPDATE nhan_vien
                SET
                    ho_ten=%s,
                    gioi_tinh=%s,
                    ngay_sinh=%s,
                    email=%s,
                    sdt=%s,
                    ma_phong_ban=%s,
                    ma_chuc_vu=%s,
                    luong_co_ban=%s,
                    trang_thai=%s
                WHERE ma_nv=%s
            """

            cursor.execute(
                query_nv,
                (
                    ten,
                    gioi_tinh,
                    ngay_sinh,
                    email,
                    sdt,
                    ma_phong,
                    ma_chuc_vu,
                    luong_float,
                    trang_thai,
                    ma
                )
            )

            # =====================================================
            # 2. ĐỒNG BỘ TÀI KHOẢN
            # =====================================================
            query_user = """
                UPDATE nguoi_dung nd
                INNER JOIN nhan_vien nv
                    ON nv.nguoi_dung_id = nd.id
                SET
                    nd.ho_ten=%s,
                    nd.email=%s,
                    nd.vai_tro=%s,
                    nd.trang_thai=
                        CASE
                            WHEN %s = 'Đang làm việc'
                            THEN 1
                            ELSE 0
                        END
                WHERE nv.ma_nv=%s
            """

            cursor.execute(
                query_user,
                (
                    ten,
                    email,
                    vai_tro,
                    trang_thai,
                    ma
                )
            )

            conn.commit()

            messagebox.showinfo(
                "Thành công",
                f"Đã cập nhật nhân viên {ma}!\n\n"
                "Thông tin tài khoản đăng nhập cũng đã được "
                "đồng bộ."
            )

            self.load_data()

        except Error as e:

            conn.rollback()

            messagebox.showerror(
                "Lỗi CSDL",
                f"Không thể cập nhật nhân viên!\n\n{e}"
            )

        finally:
            cursor.close()
            conn.close()

    def cho_nghi_viec(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn nhân viên cần cho nghỉ việc!"
            )
            return

        vals = self.tree.item(selected[0], "values")
        ma_nv = vals[0]
        ho_ten = vals[1]
        trang_thai = vals[9]

        # Trưởng phòng không được tự cho mình nghỉ việc
        if self.role == "TruongPhong" and (
            ma_nv == self.user_actual_ma_nv
            or ma_nv == self.user_login_name
        ):
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không thể tự cho mình nghỉ việc!"
            )
            return

        # Đã nghỉ rồi thì không cho thực hiện lại
        if trang_thai == "Đã nghỉ việc":
            messagebox.showinfo(
                "Thông báo",
                f"Nhân viên {ho_ten} đã ở trạng thái 'Đã nghỉ việc'."
            )
            return

        confirm = messagebox.askyesno(
            "Xác nhận cho nghỉ việc",
            f"Bạn có chắc muốn cho nhân viên:\n\n"
            f"{ho_ten} ({ma_nv})\n\n"
            f"nghỉ việc không?"
        )

        if not confirm:
            return

        conn = get_db_connection()

        if not conn:
            return

        try:
            cursor = conn.cursor()

            # 1. Chuyển trạng thái nhân viên
            cursor.execute(
                """
                UPDATE nhan_vien
                SET trang_thai = 'Đã nghỉ việc'
                WHERE ma_nv = %s
                """,
                (ma_nv,)
            )

            # 2. Khóa tài khoản đăng nhập
            cursor.execute(
                """
                UPDATE nguoi_dung nd
                INNER JOIN nhan_vien nv
                    ON nv.nguoi_dung_id = nd.id
                SET nd.trang_thai = 0
                WHERE nv.ma_nv = %s
                """,
                (ma_nv,)
            )

            conn.commit()

            messagebox.showinfo(
                "Thành công",
                f"Đã cho nhân viên {ho_ten} nghỉ việc.\n\n"
                f"Tài khoản đăng nhập cũng đã được khóa."
            )

            self.load_data()
            self.lam_moi()

        except Error as e:
            conn.rollback()
            messagebox.showerror(
                "Lỗi CSDL",
                f"Không thể cho nhân viên nghỉ việc:\n{e}"
            )

        finally:
            conn.close()
    def xoa_vinh_vien(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn nhân viên cần xóa!"
            )
            return

        vals = self.tree.item(selected[0], "values")

        ma_nv = vals[0]
        ho_ten = vals[1]
        trang_thai = vals[9]

        # =========================================================
        # 1. CHỈ ADMIN ĐƯỢC XÓA VĨNH VIỄN
        # =========================================================
        if self.role != "Admin":
            messagebox.showwarning(
                "Không có quyền",
                "Chỉ Admin mới được phép xóa nhân viên vĩnh viễn!"
            )
            return

        # =========================================================
        # 2. CHỈ ĐƯỢC XÓA NHÂN VIÊN ĐÃ NGHỈ VIỆC
        # =========================================================
        if trang_thai != "Đã nghỉ việc":
            messagebox.showwarning(
                "Không thể xóa",
                "Chỉ có thể xóa vĩnh viễn nhân viên đã nghỉ việc.\n\n"
                "Vui lòng sử dụng 'Cho nghỉ việc' trước."
            )
            return

        # =========================================================
        # 3. XÁC NHẬN
        # =========================================================
        confirm = messagebox.askyesno(
            "⚠️ Xác nhận xóa vĩnh viễn",
            f"Bạn có chắc chắn muốn xóa:\n\n"
            f"{ho_ten} ({ma_nv})\n\n"
            f"khỏi hệ thống không?\n\n"
            f"⚠ Tài khoản đăng nhập sẽ bị xóa hoàn toàn.\n"
            f"⚠ Dữ liệu lương liên quan có thể bị xóa.\n"
            f"⚠ Thao tác này không thể hoàn tác."
        )

        if not confirm:
            return

        conn = get_db_connection()

        if not conn:
            return

        cursor = None

        try:
            cursor = conn.cursor()

            # =====================================================
            # 4. LẤY ID TÀI KHOẢN CỦA NHÂN VIÊN
            # =====================================================
            cursor.execute(
                """
                SELECT nguoi_dung_id
                FROM nhan_vien
                WHERE ma_nv = %s
                """,
                (ma_nv,)
            )

            result = cursor.fetchone()

            if not result:
                messagebox.showwarning(
                    "Không thể xóa",
                    f"Không tìm thấy nhân viên {ma_nv}!"
                )
                conn.rollback()
                return

            nguoi_dung_id = result[0]

            # =====================================================
            # 5. XÓA NHÂN VIÊN
            #
            # Xóa nhân viên trước để không còn FK tham chiếu
            # đến tài khoản.
            # =====================================================
            cursor.execute(
                """
                DELETE FROM nhan_vien
                WHERE ma_nv = %s
                AND trang_thai = 'Đã nghỉ việc'
                """,
                (ma_nv,)
            )

            if cursor.rowcount == 0:
                conn.rollback()

                messagebox.showwarning(
                    "Không thể xóa",
                    "Nhân viên không tồn tại hoặc chưa ở trạng thái "
                    "'Đã nghỉ việc'."
                )
                return

            # =====================================================
            # 6. XÓA TÀI KHOẢN ĐĂNG NHẬP
            #
            # Đây là phần code cũ của bạn đang thiếu.
            # =====================================================
            if nguoi_dung_id is not None:
                cursor.execute(
                    """
                    DELETE FROM nguoi_dung
                    WHERE id = %s
                    """,
                    (nguoi_dung_id,)
                )

            # =====================================================
            # 7. HOÀN TẤT
            # =====================================================
            conn.commit()

            messagebox.showinfo(
                "Thành công",
                f"Đã xóa vĩnh viễn nhân viên:\n\n"
                f"{ho_ten} ({ma_nv})\n\n"
                f"✓ Hồ sơ nhân viên đã xóa\n"
                f"✓ Tài khoản đăng nhập đã xóa"
            )

            self.load_data()
            self.lam_moi()

        except Error as e:
            conn.rollback()

            messagebox.showerror(
                "Lỗi CSDL",
                f"Không thể xóa nhân viên và tài khoản!\n\n{e}"
            )

        finally:
            if cursor:
                cursor.close()

            conn.close()
    def tim_kiem(self):
        keyword = self.var_tim_kiem.get().strip()
        if not keyword or keyword == self.placeholder_text:
            self.load_data()
            return
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            p = f"%{keyword}%"

            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                query = """
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh, nv.email, nv.sdt, 
                           pb.ten_phong_ban, cv.ten_chuc_vu, nv.luong_co_ban, nv.trang_thai
                    FROM nhan_vien nv
                    LEFT JOIN phong_ban pb ON nv.ma_phong_ban = pb.ma_phong_ban
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    WHERE nv.ma_phong_ban = %s AND (nv.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR nv.sdt LIKE %s)
                """
                cursor.execute(query, (self.user_ma_phong_ban, p, p, p))
            else:
                query = """
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh, nv.email, nv.sdt, 
                           pb.ten_phong_ban, cv.ten_chuc_vu, nv.luong_co_ban, nv.trang_thai
                    FROM nhan_vien nv
                    LEFT JOIN phong_ban pb ON nv.ma_phong_ban = pb.ma_phong_ban
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    WHERE nv.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR nv.sdt LIKE %s
                """
                cursor.execute(query, (p, p, p))

            self.refresh_table(cursor.fetchall())
        except Error as e:
            messagebox.showerror("Lỗi", str(e))
        finally:
            conn.close()

    def lam_moi(self):
        self.var_ten_nv.set("")
        self.var_gioi_tinh.set("Nam")
        self.var_ngay_sinh.set("01/01/1995")
        self.var_email.set("")
        self.var_sdt.set("")

        # NẾU LÀ TRƯỜNG PHÒNG: TỰ ĐỘNG GIỮ NGUYÊN PHÒNG BAN VÀ KHÔNG CHO ĐỔI
        if self.role == "TruongPhong" and self.user_ma_phong_ban:
            for ten_pb, ma_pb in self.dict_phong_ban.items():
                if ma_pb == self.user_ma_phong_ban:
                    self.var_phong_ban.set(ten_pb)
                    break
        elif self.dict_phong_ban:
            self.cb_pb.current(0)

        self.generate_employee_id()

        if self.dict_chuc_vu:
            self.cb_cv.current(0)

        self.var_luong_cb.set("12.000.000")
        self.var_trang_thai.set("Đang làm việc")
        self.load_data()

    def on_double_click(self, event):
        self.on_tree_select(event)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree.focus(item)
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()

    def context_edit_nhan_vien(self):
        if self.tree.selection():
            self.on_tree_select(None)

    def context_resign_nhan_vien(self):
        self.cho_nghi_viec()

    def context_delete_nhan_vien(self):
        self.xoa_vinh_vien()

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected, "values")
        row_data = dict(zip(self.columns_def, vals))

        if self.role == "TruongPhong" and (
            row_data["ma_nv"] == self.user_actual_ma_nv
            or row_data["ma_nv"] == self.user_login_name
        ):
            messagebox.showinfo(
                "Thông báo phân quyền",
                "Đây là hồ sơ của bạn!\nTrưởng phòng chỉ được phép xem thông"
                " tin cá nhân, không thể tự chỉnh sửa hoặc xóa hồ sơ của chính"
                " mình.",
            )

        self.var_ma_nv.set(row_data["ma_nv"])
        self.var_ten_nv.set(row_data["ten_nv"])
        self.var_gioi_tinh.set(row_data["gioi_tinh"])
        self.var_ngay_sinh.set(row_data["ngay_sinh"])
        self.var_email.set(row_data["email"])
        self.var_sdt.set(row_data["sdt"])
        self.var_phong_ban.set(row_data["phong_ban"])
        self.var_chuc_vu.set(row_data["chuc_vu"])

        formatted_luong = self.format_money_str(
            self.parse_money(row_data["luong_cb"])
        )
        self.var_luong_cb.set(formatted_luong)
        self.var_trang_thai.set(row_data["trang_thai"])


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Độc Lập - Quản Lý Nhân Viên")
    root.geometry("1150x650")

    test_frame = tk.Frame(root, bg="#f8fafc")
    test_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

    app = EmployeeManagementForm(test_frame)

    root.mainloop()