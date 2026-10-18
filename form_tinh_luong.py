import datetime
import re
import tkinter as tk
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
from tkinter import filedialog, messagebox, ttk
from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import get_icon, icon_button
from user_error import show_database_error, show_file_error


class PayrollManagementForm:

    STANDARD_WORK_DAYS = 24
    HOURS_PER_DAY = 8
    OT_RATE = 1.5
    MAX_OT_HOURS = 40.0
    MIN_PAYROLL_YEAR = 2000
    # Dùng khi chuc_vu.phu_cap chưa được cấu hình (đang bằng 0 trong CSDL).
    # Nếu CSDL có mức phụ cấp lớn hơn 0 thì luôn ưu tiên mức trong CSDL.
    DEFAULT_POSITION_ALLOWANCES = {
        "CV01": 2_000_000,
        "CV02": 1_000_000,
        "CV03": 500_000,
        "CV04": 0,
    }

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

        self.user_ma_phong_ban = None
        self.user_actual_ma_nv = None

        # Biến giao diện
        self.var_ma_nv = tk.StringVar()
        self.var_ten_nv = tk.StringVar()
        self.var_thang = tk.StringVar(value=str(datetime.datetime.now().month))
        self.var_nam = tk.StringVar(value=str(datetime.datetime.now().year))

        self.var_filter_thang = tk.StringVar(value="Tất cả")
        self.var_filter_nam = tk.StringVar(
            value=str(datetime.datetime.now().year)
        )

        self.var_luong_cb = tk.StringVar(value="10.000.000")
        self.var_ngay_cong = tk.StringVar(value="24")
        self.var_gio_ot = tk.StringVar(value="0")  # Chuyển Lương OT thành Số giờ OT
        self.var_phu_cap = tk.StringVar(value="0")
        self.var_khoan_tru = tk.StringVar(value="0")
        self.var_thuc_nhan = tk.StringVar(value="0 đ")
        self.var_tim_kiem = tk.StringVar()

        self.dict_nhan_vien = {}  # ma_nv -> (ho_ten, luong_cb, phu_cap)
        self.all_employee_display_list = []
        # Popup tìm kiếm nhân viên
        self.employee_popup = None
        self.employee_popup_tree = None
        self.filtered_employee_display_list = []
        self.get_user_department_and_id()
        self.create_widgets()

        if self.role != "NhanVien":
            self.load_employee_combobox()

        self.load_data()

    def get_user_department_and_id(self):
        """Lấy chính xác Mã phòng ban và Mã NV thực tế qua nguoi_dung_id"""
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

    def get_selected_ma_nv(self):
        """Tách lấy mã nhân viên từ chuỗi 'Mã - Tên'"""
        val = self.var_ma_nv.get().strip()
        if " - " in val:
            return val.split(" - ")[0].strip()
        return val

    def create_widgets(self):
        title_text = (
            "PHIẾU LƯƠNG CÁ NHÂN"
            if self.role == "NhanVien"
            else "QUẢN LÝ BẢNG LƯƠNG & CHẤM CÔNG NHÂN VIÊN"
        )
        tk.Label(
            self.parent,
            text=title_text,
            font=("Helvetica", 13, "bold"),
            fg="#1e293b",
            bg="#f8fafc",
        ).pack(anchor="w", pady=(0, 8))

        if self.role != "NhanVien":
            self.input_frame = tk.LabelFrame(
                self.parent,
                text=" Nhập liệu thông tin tính lương & chấm công ",
                font=("Helvetica", 10, "bold"),
                bg="#f8fafc",
                fg="#0f172a",
                padx=12,
                pady=10,
            )
            self.input_frame.pack(fill=tk.X, pady=(0, 8))

            # Hàng 0: Chọn Nhân viên (Gồm Mã & Tên), Tháng/Năm
            tk.Label(
                self.input_frame,
                text="Chọn Nhân viên (*):",
                bg="#f8fafc",
                font=("Helvetica", 10, "bold"),
            ).grid(row=0, column=0, sticky="w", pady=5)

            # Ô chọn nhân viên có tìm kiếm và nút xổ danh sách.
            self.employee_picker_frame = tk.Frame(
                self.input_frame,
                bg="white",
                highlightbackground="#cbd5e1",
                highlightcolor="#2563eb",
                highlightthickness=1,
            )
            self.employee_picker_frame.grid(
                row=0,
                column=1,
                columnspan=2,
                padx=5,
                pady=5,
                sticky="w",
            )

            self.cb_ma_nv = tk.Entry(
                self.employee_picker_frame,
                textvariable=self.var_ma_nv,
                width=30,
                font=("Helvetica", 10),
                relief="flat",
                bd=0,
            )
            self.cb_ma_nv.pack(
                side=tk.LEFT,
                padx=(8, 4),
                pady=5,
            )
            self.employee_placeholder_label = tk.Label(
                self.employee_picker_frame,
                text="Gõ mã hoặc tên nhân viên...",
                bg="white",
                fg="#94a3b8",
                font=("Helvetica", 10),
                cursor="xterm",
            )
            self.employee_placeholder_label.place(
                x=9, rely=0.5, anchor="w"
            )
            self.employee_placeholder_label.bind(
                "<Button-1>", self.focus_employee_picker
            )
            tk.Button(
                self.employee_picker_frame,
                image=get_icon(self.parent, "chevron_down", "#475569"),
                bg="white",
                activebackground="#eff6ff",
                relief="flat",
                bd=0,
                width=28,
                padx=0,
                pady=0,
                cursor="hand2",
                command=self.show_all_employee_options,
            ).pack(side=tk.RIGHT, fill=tk.Y)

            # Gõ tới đâu tìm kiếm tới đó
            self.cb_ma_nv.bind(
                "<KeyRelease>",
                self.on_employee_key_release
            )

            # Phím điều hướng
            self.cb_ma_nv.bind(
                "<Down>",
                self.on_employee_down
            )

            self.cb_ma_nv.bind(
                "<Up>",
                self.on_employee_up
            )

            self.cb_ma_nv.bind(
                "<Return>",
                self.on_employee_enter
            )

            self.cb_ma_nv.bind(
                "<Escape>",
                self.on_employee_escape
            )
            self.cb_ma_nv.bind("<FocusIn>", self.on_employee_focus_in)
            self.cb_ma_nv.bind("<FocusOut>", self.on_employee_focus_out)

            # Sự kiện đi qua cửa sổ chính; click vào popup không bị đóng nhầm.
            self._outside_click_root = self.parent.winfo_toplevel()
            self._outside_click_bind_id = self._outside_click_root.bind(
                "<Button-1>",
                self.on_click_outside_employee_picker,
                add="+",
            )
            self.input_frame.bind(
                "<Destroy>", self.on_employee_picker_destroy, add="+"
            )

            tk.Label(
                self.input_frame,
                text="Tháng / Năm (*):",
                bg="#f8fafc",
                font=("Helvetica", 10),
            ).grid(row=0, column=3, sticky="w", pady=5, padx=(20, 0))

            frame_tn = tk.Frame(self.input_frame, bg="#f8fafc")
            frame_tn.grid(row=0, column=4, padx=5, pady=5, sticky="w")

            entry_thang = tk.Entry(
                frame_tn,
                textvariable=self.var_thang,
                width=5,
                font=("Helvetica", 10),
            )
            entry_thang.pack(side=tk.LEFT)
            entry_thang.bind(
                "<KeyRelease>",
                lambda e: self.on_digits_only_key_release(
                    e, self.var_thang, max_val=12
                ),
            )

            tk.Label(
                frame_tn,
                text="/",
                bg="#f8fafc",
                font=("Helvetica", 10, "bold"),
            ).pack(side=tk.LEFT, padx=2)

            entry_nam = tk.Entry(
                frame_tn,
                textvariable=self.var_nam,
                width=8,
                font=("Helvetica", 10),
            )
            entry_nam.pack(side=tk.LEFT)
            entry_nam.bind(
                "<KeyRelease>",
                lambda e: self.on_digits_only_key_release(
                    e,
                    self.var_nam,
                    max_val=datetime.datetime.now().year,
                ),
            )

            # Hàng 1: Lương CB, Số ngày công, Số giờ OT
            tk.Label(
                self.input_frame,
                text="Lương cơ bản (đ):",
                bg="#f8fafc",
                font=("Helvetica", 10),
            ).grid(row=1, column=0, sticky="w", pady=5)
            self.entry_luong_cb = tk.Entry(
                self.input_frame,
                textvariable=self.var_luong_cb,
                width=22,
                state="readonly",
                bg="#e2e8f0",
                font=("Helvetica", 10, "bold"),
            )
            self.entry_luong_cb.grid(
                row=1, column=1, padx=5, pady=5, sticky="w"
            )

            tk.Label(
                self.input_frame,
                text="Số ngày công:",
                bg="#f8fafc",
                font=("Helvetica", 10),
            ).grid(row=1, column=2, sticky="w", pady=5, padx=(15, 0))
            entry_ngay_cong = tk.Entry(
                self.input_frame,
                textvariable=self.var_ngay_cong,
                width=18,
                font=("Helvetica", 10),
            )
            entry_ngay_cong.grid(row=1, column=3, padx=5, pady=5, sticky="w")
            entry_ngay_cong.bind(
                "<KeyRelease>",
                lambda e: self.on_digits_only_key_release(
                    e, self.var_ngay_cong, max_val=31
                ),
            )

            # Ô NHẬP SỐ GIỜ OT
            tk.Label(
                self.input_frame,
                text="Số giờ OT (giờ):",
                bg="#f8fafc",
                font=("Helvetica", 10),
            ).grid(row=1, column=4, sticky="w", pady=5, padx=(15, 0))
            entry_gio_ot = tk.Entry(
                self.input_frame,
                textvariable=self.var_gio_ot,
                width=20,
                font=("Helvetica", 10),
            )
            entry_gio_ot.grid(row=1, column=5, padx=5, pady=5, sticky="w")
            entry_gio_ot.bind(
                "<KeyRelease>",
                lambda e: self.on_hours_key_release(e, self.var_gio_ot),
            )

            # Hàng 2: Phụ cấp, Khoản trừ, Lương thực nhận
            tk.Label(
                self.input_frame,
                text="Phụ cấp chức vụ (đ):",
                bg="#f8fafc",
                font=("Helvetica", 10),
            ).grid(row=2, column=0, sticky="w", pady=5)
            entry_phu_cap = tk.Entry(
                self.input_frame,
                textvariable=self.var_phu_cap,
                width=22,
                state="readonly",
                readonlybackground="#e2e8f0",
                font=("Helvetica", 10),
            )
            entry_phu_cap.grid(row=2, column=1, padx=5, pady=5, sticky="w")

            tk.Label(
                self.input_frame,
                text="Khoản trừ (đ):",
                bg="#f8fafc",
                font=("Helvetica", 10),
            ).grid(row=2, column=2, sticky="w", pady=5, padx=(15, 0))
            entry_khoan_tru = tk.Entry(
                self.input_frame,
                textvariable=self.var_khoan_tru,
                width=18,
                font=("Helvetica", 10),
            )
            entry_khoan_tru.grid(row=2, column=3, padx=5, pady=5, sticky="w")
            entry_khoan_tru.bind(
                "<KeyRelease>",
                self.on_deduction_key_release,
            )

            tk.Label(
                self.input_frame,
                text="LƯƠNG THỰC NHẬN:",
                bg="#f8fafc",
                font=("Helvetica", 10, "bold"),
                fg="#16a34a",
            ).grid(row=2, column=4, sticky="w", pady=5, padx=(15, 0))
            self.entry_thuc_nhan = tk.Entry(
                self.input_frame,
                textvariable=self.var_thuc_nhan,
                width=20,
                state="readonly",
                bg="#f0fdf4",
                fg="#15803d",
                font=("Helvetica", 10, "bold"),
            )
            self.entry_thuc_nhan.grid(
                row=2, column=5, padx=5, pady=5, sticky="w"
            )

        # Action Buttons & Search Bar
        action_frame = tk.Frame(self.parent, bg="#f8fafc")
        action_frame.pack(fill=tk.X, pady=6)

        btn_sub_frame = tk.Frame(action_frame, bg="#f8fafc")
        btn_sub_frame.pack(side=tk.LEFT)

        if self.role != "NhanVien":
            # 1. Nút Lưu / Cập nhật (Được đưa lên đầu làm nút chính)
            icon_button(
                btn_sub_frame,
                text="Lưu / Cập nhật",
                icon="save",
                bg="#2563eb",
                fg="white",
                padx=12,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.luu_bang_luong,
            ).pack(side=tk.LEFT, padx=3)

            # 2. Nút Xóa
            icon_button(
                btn_sub_frame,
                text="Xóa",
                icon="delete",
                bg="#ef4444",
                fg="white",
                padx=10,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.xoa_bang_luong,
            ).pack(side=tk.LEFT, padx=3)

            # 3. Nút Làm mới
            icon_button(
                btn_sub_frame,
                text="Làm mới",
                icon="refresh",
                bg="#64748b",
                fg="white",
                padx=10,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.lam_moi,
            ).pack(side=tk.LEFT, padx=3)

        icon_button(
            btn_sub_frame,
            text="Xuất Bảng Lương (Excel)",
            icon="export",
            bg="#10b981",
            fg="white",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.xuat_excel,
        ).pack(side=tk.LEFT, padx=3)

        # Search Sub-frame
        search_sub_frame = tk.Frame(action_frame, bg="#f8fafc")
        search_sub_frame.pack(side=tk.RIGHT)

        if self.role == "NhanVien":
            tk.Label(
                search_sub_frame,
                text="Lọc Tháng:",
                bg="#f8fafc",
                font=("Helvetica", 10, "bold"),
            ).pack(side=tk.LEFT, padx=(5, 2))
            cb_filter_thang = ttk.Combobox(
                search_sub_frame,
                textvariable=self.var_filter_thang,
                width=8,
                state="readonly",
                values=["Tất cả"] + [str(i) for i in range(1, 13)],
            )
            cb_filter_thang.pack(side=tk.LEFT, padx=2)

            tk.Label(
                search_sub_frame,
                text="Năm:",
                bg="#f8fafc",
                font=("Helvetica", 10, "bold"),
            ).pack(side=tk.LEFT, padx=(8, 2))
            entry_filter_nam = tk.Entry(
                search_sub_frame,
                textvariable=self.var_filter_nam,
                width=6,
                font=("Helvetica", 10),
            )
            entry_filter_nam.pack(side=tk.LEFT, padx=2)

            icon_button(
                search_sub_frame,
                text="Xem",
                icon="search",
                bg="#0ea5e9",
                fg="white",
                padx=10,
                pady=3,
                bd=0,
                command=self.load_data,
            ).pack(side=tk.LEFT, padx=5)
        else:
            tk.Label(
                search_sub_frame,
                text="Tìm kiếm:",
                bg="#f8fafc",
                font=("Helvetica", 10, "bold"),
            ).pack(side=tk.LEFT, padx=5)
            self.placeholder_text = "Nhập mã, tên hoặc tháng/năm..."
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
            self.entry_tim_kiem.bind("<Return>", self.on_search_enter)

            icon_button(
                search_sub_frame,
                text="Tìm",
                icon="search",
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

        # Table Treeview
        table_frame = tk.Frame(self.parent)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        style.configure("Treeview", font=("Helvetica", 10), rowheight=24)

        self.columns_def = (
            "ma_nv",
            "ten_nv",
            "thang_nam",
            "luong_cb",
            "ngay_cong",
            "gio_ot",
            "luong_ot",
            "phu_cap",
            "khoan_tru",
            "thuc_nhan",
        )
        self.tree = ttk.Treeview(
            table_frame, columns=self.columns_def, show="headings", height=10
        )

        if self.role != "NhanVien":
            self.context_menu = tk.Menu(self.parent, tearoff=0)
            self.context_menu.add_command(
                label="Xem / Chỉnh sửa dòng này",
                image=get_icon(self.parent, "edit", "#475569"),
                compound=tk.LEFT,
                command=self.context_edit_luong,
            )
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Xóa dữ liệu bảng lương này",
                image=get_icon(self.parent, "delete", "#dc2626"),
                compound=tk.LEFT,
                command=self.context_delete_luong,
            )
            self.tree.bind("<Button-3>", self.show_context_menu)

        headers = {
            "ma_nv": "Mã NV",
            "ten_nv": "Họ và Tên",
            "thang_nam": "Tháng/Năm",
            "luong_cb": "Lương CB (đ)",
            "ngay_cong": "Ngày công",
            "gio_ot": "Giờ OT",
            "luong_ot": "Lương OT (đ)",
            "phu_cap": "Phụ cấp (đ)",
            "khoan_tru": "Khoản trừ (đ)",
            "thuc_nhan": "Thực nhận (đ)",
        }
        widths = {
            "ma_nv": 80,
            "ten_nv": 150,
            "thang_nam": 90,
            "luong_cb": 120,
            "ngay_cong": 85,
            "gio_ot": 75,
            "luong_ot": 110,
            "phu_cap": 110,
            "khoan_tru": 110,
            "thuc_nhan": 130,
        }

        for col in self.columns_def:
            col_anchor = (
                tk.CENTER
                if col in ("ma_nv", "thang_nam", "ngay_cong", "gio_ot")
                else (tk.W if col == "ten_nv" else tk.E)
            )
            self.tree.heading(col, text=headers[col], anchor=col_anchor)
            self.tree.column(col, width=widths[col], anchor=col_anchor)

        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        if self.role != "NhanVien":
            self.tree.bind("<Double-1>", self.on_double_click)
    def on_employee_key_release(self, event=None):
        """Tìm nhân viên ngay khi gõ vào ô tìm kiếm."""

        if event and event.keysym in (
            "Up",
            "Down",
            "Return",
            "Escape",
        ):
            return

        text = self.var_ma_nv.get().strip().lower()

        # Không có nội dung -> đóng popup
        if not text:
            self.hide_employee_popup()
            self.clear_employee_details()
            return

        ma_nv = self.get_selected_ma_nv()
        employee = self.dict_nhan_vien.get(ma_nv)
        canonical_value = (
            f"{ma_nv} - {employee[0]}".lower() if employee else ""
        )
        if text != canonical_value:
            self.clear_employee_details()

        filtered = self.filter_employee_options(text)

        # Không tìm thấy
        if not filtered:
            self.hide_employee_popup()
            self.clear_employee_details()
            return

        # Không cho popup quá dài
        filtered = filtered[:12]

        self.show_employee_popup(filtered)

    def on_employee_focus_in(self, event=None):
        self.employee_picker_frame.config(highlightbackground="#2563eb")
        self.employee_placeholder_label.place_forget()
        if not self.var_ma_nv.get().strip():
            self.show_all_employee_options()

    def on_employee_focus_out(self, event=None):
        self.employee_picker_frame.config(highlightbackground="#cbd5e1")
        self.parent.after_idle(self.update_employee_placeholder)

    def focus_employee_picker(self, event=None):
        self.cb_ma_nv.focus_set()

    def update_employee_placeholder(self):
        if (
            not self.var_ma_nv.get().strip()
            and self.cb_ma_nv.focus_get() != self.cb_ma_nv
        ):
            self.employee_placeholder_label.place(x=9, rely=0.5, anchor="w")
        else:
            self.employee_placeholder_label.place_forget()

    def filter_employee_options(self, keyword):
        """Ưu tiên lọc mã bắt đầu bằng từ khóa, sau đó mới tìm rộng."""
        query = keyword.strip().casefold()
        if not query:
            return list(self.all_employee_display_list)

        employees = []
        for display in self.all_employee_display_list:
            employee_code, _, employee_name = display.partition(" - ")
            employees.append(
                (display, employee_code.casefold(), employee_name.casefold())
            )

        code_prefix_matches = [
            display
            for display, employee_code, _ in employees
            if employee_code.startswith(query)
        ]
        if code_prefix_matches:
            return code_prefix_matches

        return [
            display
            for display, employee_code, employee_name in employees
            if query in employee_code or query in employee_name
        ]

    def clear_employee_details(self):
        self.var_ten_nv.set("")
        self.var_luong_cb.set("0")
        self.var_phu_cap.set("0")
        self.tinh_luong()

    def show_all_employee_options(self):
        if not self.all_employee_display_list:
            return
        self.cb_ma_nv.focus_set()
        self.show_employee_popup(self.all_employee_display_list[:12])

    def on_click_outside_employee_picker(self, event):
        widget = event.widget
        while widget is not None:
            if widget in (self.employee_picker_frame, self.employee_popup):
                return
            widget = getattr(widget, "master", None)
        self.hide_employee_popup()
        self.update_employee_placeholder()

    def on_employee_picker_destroy(self, event):
        if event.widget is not self.input_frame:
            return
        bind_id = getattr(self, "_outside_click_bind_id", None)
        root = getattr(self, "_outside_click_root", None)
        if bind_id and root:
            try:
                root.unbind("<Button-1>", bind_id)
            except tk.TclError:
                pass
            self._outside_click_bind_id = None
        if self.employee_popup is not None:
            try:
                self.employee_popup.destroy()
            except tk.TclError:
                pass
            self.employee_popup = None
            self.employee_popup_tree = None

    def show_employee_popup(self, values):
        """
        Hiển thị popup danh sách nhân viên
        ngay bên dưới ô tìm kiếm.
        """
         # Nếu popup chưa tồn tại -> tạo mới
        if self.employee_popup is None or not self.employee_popup.winfo_exists():
            self.employee_popup = tk.Toplevel(self.parent)

            self.employee_popup.wm_overrideredirect(True)
            self.employee_popup.attributes("-topmost", True)

            # Khung popup
            popup_frame = tk.Frame(
                self.employee_popup,
                bg="white",
                bd=1,
                relief="solid"
            )

            popup_frame.pack(fill=tk.BOTH, expand=True)

            # Treeview
            self.employee_popup_tree = ttk.Treeview(
                popup_frame,
                columns=("ma_nv", "ho_ten"),
                show="headings",
                height=8,
                selectmode="browse"
            )

            self.employee_popup_tree.heading("ma_nv", text="Mã nhân viên")

            self.employee_popup_tree.heading(
                "ho_ten",
                text="Họ và Tên"
            )

            self.employee_popup_tree.column(
                "ma_nv",
                width=90,
                anchor="center"
            )

            self.employee_popup_tree.column(
                "ho_ten",
                width=230,
                anchor="w"
            )

            scrollbar = ttk.Scrollbar(
                popup_frame,
                orient=tk.VERTICAL,
                command=self.employee_popup_tree.yview
            )

            self.employee_popup_tree.configure(
                yscrollcommand=scrollbar.set
            )

            self.employee_popup_tree.pack(
                side=tk.LEFT,
                fill=tk.BOTH,
                expand=True
            )

            scrollbar.pack(
                side=tk.RIGHT,
                fill=tk.Y
            )

            # Click chuột để chọn
            self.employee_popup_tree.bind(
                "<ButtonRelease-1>",
                self.on_employee_popup_click
            )

            # Double click cũng chọn
            self.employee_popup_tree.bind(
                "<Double-1>",
                self.on_employee_popup_click
            )
        # Xóa kết quả cũ
        for item in self.employee_popup_tree.get_children():
            self.employee_popup_tree.delete(item)
        # Thêm kết quả mới
        for index, display in enumerate(values):

            if " - " in display:
                ma_nv, ho_ten = display.split(
                    " - ",
                    1
                )
            else:
                ma_nv = display
                ho_ten = ""

            self.employee_popup_tree.insert(
                "",
                tk.END,
                values=(ma_nv, ho_ten),
                tags=("even" if index % 2 == 0 else "odd",),
            )
        self.employee_popup_tree.tag_configure("even", background="#ffffff")
        self.employee_popup_tree.tag_configure("odd", background="#f8fafc")
        # Vị trí và kích thước bám theo toàn bộ khung chọn nhân viên.
        self.employee_picker_frame.update_idletasks()
        x = self.employee_picker_frame.winfo_rootx()
        y = (
            self.employee_picker_frame.winfo_rooty()
            + self.employee_picker_frame.winfo_height()
        )

        popup_width = max(self.employee_picker_frame.winfo_width(), 330)
        popup_height = min(max(len(values), 1), 8) * 25 + 28

        self.employee_popup.geometry(
            f"{popup_width}x{popup_height}+{x}+{y}"
        )

        self.employee_popup.deiconify()
        self.employee_popup.lift()

        # Chỉ hiển thị kết quả; không tự chọn nhân viên đầu tiên.
        self.employee_popup_tree.selection_remove(
            self.employee_popup_tree.selection()
        )
        self.employee_popup_tree.focus("")
    def hide_employee_popup(self):
        """
        Đóng popup tìm kiếm nhân viên.
        """

        if self.employee_popup is not None:

            try:
                self.employee_popup.withdraw()
            except tk.TclError:
                pass
    def on_employee_popup_click(self, event=None):
        """
        Chọn nhân viên bằng chuột.
        """

        if not self.employee_popup_tree:
            return

        selected = self.employee_popup_tree.selection()

        if not selected:
            return

        values = self.employee_popup_tree.item(
            selected[0],
            "values"
        )

        if not values:
            return

        ma_nv = values[0]
        ho_ten = values[1]

        # Đưa mã + tên vào ô tìm kiếm
        self.var_ma_nv.set(
            f"{ma_nv} - {ho_ten}"
        )
        self.employee_placeholder_label.place_forget()

        # Đóng popup
        self.hide_employee_popup()

        # Luôn để mã nhân viên ở đầu ô nhập được nhìn thấy đầy đủ.
        self.cb_ma_nv.focus_set()
        self.cb_ma_nv.icursor(0)
        self.cb_ma_nv.xview_moveto(0)

        # Nạp thông tin nhân viên
        self.on_employee_selected(None)
    def on_employee_down(self, event=None):
        """
        Nhấn ↓ để di chuyển xuống trong danh sách.
        """

        if not self.employee_popup_tree:
            return "break"

        if (
            self.employee_popup is None
            or not self.employee_popup.winfo_viewable()
        ):
            return "break"

        items = self.employee_popup_tree.get_children()

        if not items:
            return "break"

        selected = self.employee_popup_tree.selection()

        if not selected:
            # Lần đầu nhấn ↓ -> chọn dòng đầu
            self.employee_popup_tree.selection_set(items[0])
            self.employee_popup_tree.focus(items[0])
        else:
            current = items.index(selected[0])

            if current < len(items) - 1:
                next_item = items[current + 1]

                self.employee_popup_tree.selection_set(
                    next_item
                )

                self.employee_popup_tree.focus(
                    next_item
                )

        return "break"
    def on_employee_up(self, event=None):
        """
        Nhấn ↑ để di chuyển lên trong danh sách.
        """

        if not self.employee_popup_tree:
            return "break"

        if (
            self.employee_popup is None
            or not self.employee_popup.winfo_viewable()
        ):
            return "break"

        items = self.employee_popup_tree.get_children()

        if not items:
            return "break"

        selected = self.employee_popup_tree.selection()

        if not selected:
            return "break"

        current = items.index(selected[0])

        if current > 0:

            previous_item = items[current - 1]

            self.employee_popup_tree.selection_set(
                previous_item
            )

            self.employee_popup_tree.focus(
                previous_item
            )

        return "break"

    def on_digits_only_key_release(self, event, var, max_val=None):
        raw = str(var.get())
        digits = re.sub(r"\D", "", raw)

        if not digits:
            var.set("")
        else:
            val = int(digits)
            if max_val and val > max_val:
                val = max_val
            var.set(str(val))
            event.widget.icursor(tk.END)
        self.tinh_luong()
    def on_employee_enter(self, event=None):
        """
        Enter lần đầu mở danh sách đã lọc; chỉ chọn dòng đã highlight.
        """

        popup_visible = (
            self.employee_popup_tree is not None
            and self.employee_popup is not None
            and self.employee_popup.winfo_viewable()
        )
        if popup_visible:
            selected = self.employee_popup_tree.selection()
            if selected:
                self.on_employee_popup_click()
                return "break"

        keyword = self.var_ma_nv.get().strip()
        filtered = self.filter_employee_options(keyword)[:12]
        if filtered:
            self.show_employee_popup(filtered)
        else:
            self.hide_employee_popup()

        return "break"
    def on_employee_escape(self, event=None):
        """
        Nhấn Esc để đóng danh sách tìm kiếm.
        """

        self.hide_employee_popup()

        return "break"
    def on_hours_key_release(self, event, var):
        raw = str(var.get())

        # Chỉ cho phép số và dấu chấm
        cleaned = re.sub(r"[^0-9.]", "", raw)

        # Chỉ giữ 1 dấu chấm thập phân
        if cleaned.count(".") > 1:
            first_dot = cleaned.find(".")
            cleaned = (
                cleaned[:first_dot + 1]
                + cleaned[first_dot + 1:].replace(".", "")
            )

        # Giới hạn tối đa 1 chữ số thập phân
        if "." in cleaned:
            integer_part, decimal_part = cleaned.split(".", 1)
            decimal_part = decimal_part[:1]
            cleaned = integer_part + "." + decimal_part

        if cleaned not in ("", "."):
            value = min(float(cleaned), self.MAX_OT_HOURS)
            cleaned = f"{value:.1f}".rstrip("0").rstrip(".")

        var.set(cleaned)
        event.widget.icursor(tk.END)
        self.tinh_luong()

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
        self.tinh_luong()

    def on_deduction_key_release(self, event):
        """Định dạng và giới hạn khoản trừ không vượt tổng thu nhập."""
        raw = str(self.var_khoan_tru.get())
        digits = re.sub(r"\D", "", raw)
        deduction = int(digits) if digits else 0
        maximum = int(round(self.calculate_gross_income()))
        deduction = min(deduction, maximum)
        self.var_khoan_tru.set(self.format_money_str(deduction))
        event.widget.icursor(tk.END)
        self.tinh_luong()

    def on_search_focus_in(self, event):
        if self.entry_tim_kiem.get() == self.placeholder_text:
            self.entry_tim_kiem.delete(0, tk.END)
            self.entry_tim_kiem.config(fg="black")

    def on_search_focus_out(self, event):
        if not self.entry_tim_kiem.get().strip():
            self.entry_tim_kiem.insert(0, self.placeholder_text)
            self.entry_tim_kiem.config(fg="grey")

    def on_search_enter(self, event=None):
        self.tim_kiem()
        return "break"

    def load_employee_combobox(self):
        """
        Nạp danh sách nhân viên đang làm việc.

        Danh sách được giữ trong bộ nhớ để tìm kiếm,
        nhưng không tự động chọn bất kỳ nhân viên nào.
        """

        conn = get_db_connection()

        if not conn:
            return

        try:
            cursor = conn.cursor(dictionary=True)

            if self.role == "TruongPhong" and self.user_ma_phong_ban:

                query = """
                    SELECT
                        nv.ma_nv,
                        nv.ho_ten,
                        nv.luong_co_ban,
                        nv.ma_chuc_vu,
                        COALESCE(cv.phu_cap, 0) AS phu_cap
                    FROM nhan_vien nv
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    WHERE nv.ma_phong_ban = %s
                    AND (nv.ma_nv != %s OR %s IS NULL)
                    AND (
                        nv.nguoi_dung_id != %s
                        OR %s IS NULL
                        OR nv.nguoi_dung_id IS NULL
                    )
                    AND nv.trang_thai <> 'Đã nghỉ việc'
                    ORDER BY nv.ma_nv ASC
                """

                cursor.execute(
                    query,
                    (
                        self.user_ma_phong_ban,
                        self.user_actual_ma_nv,
                        self.user_actual_ma_nv,
                        self.user_db_id,
                        self.user_db_id,
                    )
                )

            else:

                query = """
                    SELECT
                        nv.ma_nv,
                        nv.ho_ten,
                        nv.luong_co_ban,
                        nv.ma_chuc_vu,
                        COALESCE(cv.phu_cap, 0) AS phu_cap
                    FROM nhan_vien nv
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    WHERE nv.trang_thai <> 'Đã nghỉ việc'
                    ORDER BY nv.ma_nv ASC
                """

                cursor.execute(query)

            rows = cursor.fetchall()

            # Lưu dữ liệu nhân viên
            self.dict_nhan_vien = {
                row["ma_nv"]: (
                    row["ho_ten"],
                    float(row["luong_co_ban"] or 0),
                    self.get_position_allowance(
                        row["ma_chuc_vu"], row["phu_cap"]
                    ),
                )
                for row in rows
            }

            # Danh sách dùng để tìm kiếm
            self.all_employee_display_list = [
                f"{row['ma_nv']} - {row['ho_ten']}"
                for row in rows
            ]

            # Quan trọng:
            # Không tự chọn nhân viên đầu tiên
            self.var_ma_nv.set("")
            self.var_ten_nv.set("")
            self.var_luong_cb.set("0")

            self.hide_employee_popup()
            self.update_employee_placeholder()

        except Error as e:

            show_database_error(e, "tải danh sách nhân viên")

        finally:
            conn.close()

    def get_position_allowance(self, position_code, database_allowance):
        """Lấy một phụ cấp chức vụ, ưu tiên mức đã cấu hình trong CSDL."""
        allowance = float(database_allowance or 0)
        if allowance > 0:
            return allowance
        return float(self.DEFAULT_POSITION_ALLOWANCES.get(position_code, 0))

    def calculate_gross_income(self):
        """Tổng lương trước khoản trừ, dùng chung để giới hạn dữ liệu nhập."""
        base_salary = self.parse_money(self.var_luong_cb.get())
        work_days = int(self.parse_money(self.var_ngay_cong.get()))
        allowance = self.parse_money(self.var_phu_cap.get())
        try:
            overtime_hours = float(self.var_gio_ot.get().strip() or 0)
        except ValueError:
            overtime_hours = 0.0
        regular_salary = (base_salary / self.STANDARD_WORK_DAYS) * work_days
        hourly_salary = base_salary / (
            self.STANDARD_WORK_DAYS * self.HOURS_PER_DAY
        )
        overtime_salary = round(
            overtime_hours * hourly_salary * self.OT_RATE, 2
        )
        return regular_salary + overtime_salary + allowance

    def on_employee_selected(self, event=None):
        ma = self.get_selected_ma_nv()
        if ma in self.dict_nhan_vien:
            ten, luong_cb, phu_cap = self.dict_nhan_vien[ma]
            self.var_ten_nv.set(ten)
            self.var_luong_cb.set(self.format_money_str(luong_cb))
            self.var_phu_cap.set(self.format_money_str(phu_cap))
            self.tinh_luong()

    def tinh_luong(self):
        """Tính toán Lương Thực Nhận & Tiền Lương OT theo số giờ OT nhập vào"""
        try:
            luong_cb = self.parse_money(self.var_luong_cb.get())
            ngay_cong = int(self.parse_money(self.var_ngay_cong.get()))

            try:
                gio_ot = float(self.var_gio_ot.get().strip() or 0)
            except ValueError:
                gio_ot = 0.0

            phu_cap = self.parse_money(self.var_phu_cap.get())
            khoan_tru = self.parse_money(self.var_khoan_tru.get())

            # Một mô hình thống nhất: 24 ngày công, 8 giờ/ngày, OT hệ số 1,5.
            luong_1_gio = (
                luong_cb / (self.STANDARD_WORK_DAYS * self.HOURS_PER_DAY)
                if luong_cb > 0
                else 0.0
            )

            # Tiền Lương OT với hệ số làm thêm 1.5
            tien_luong_ot = round(gio_ot * luong_1_gio * self.OT_RATE, 2)

            # Lương chính theo ngày công thực tế
            luong_chinh = (luong_cb / self.STANDARD_WORK_DAYS) * ngay_cong

            thuc_nhan = luong_chinh + tien_luong_ot + phu_cap - khoan_tru
            if thuc_nhan < 0:
                thuc_nhan = 0.0

            self.var_thuc_nhan.set(f"{self.format_money_str(thuc_nhan)} đ")
            return thuc_nhan, tien_luong_ot
        except (ValueError, tk.TclError):
            return 0.0, 0.0

    def luu_bang_luong(self):
        ma_nv = self.get_selected_ma_nv()
        try:
            thang = int(self.var_thang.get() or 0)
            nam = int(self.var_nam.get() or 0)
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Tháng và Năm phải là số!")
            return

        if not ma_nv:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn Nhân viên!")
            return

        if ma_nv not in self.dict_nhan_vien:
            messagebox.showwarning(
                "Cảnh báo", "Vui lòng chọn nhân viên hợp lệ từ danh sách!"
            )
            return

        # Cho phép gõ đúng mã rồi bấm Lưu mà không bắt buộc chọn bằng chuột.
        self.on_employee_selected()

        if self.role == "TruongPhong" and (
            ma_nv == self.user_actual_ma_nv or ma_nv == self.user_login_name
        ):
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không thể tự tính hoặc cập nhật lương cho chính"
                " bản thân!\nLương Trưởng phòng do Ban Giám đốc (Admin) phê"
                " duyệt.",
            )
            return

        if not (1 <= thang <= 12):
            messagebox.showwarning("Cảnh báo", "Tháng phải từ 1 đến 12!")
            return

        current_year = datetime.datetime.now().year
        if not (self.MIN_PAYROLL_YEAR <= nam <= current_year):
            messagebox.showwarning(
                "Cảnh báo",
                f"Năm phải từ {self.MIN_PAYROLL_YEAR} đến {current_year}!",
            )
            return

        ngay_cong = int(self.parse_money(self.var_ngay_cong.get()))
        if not (0 <= ngay_cong <= self.STANDARD_WORK_DAYS):
            messagebox.showwarning(
                "Cảnh báo",
                f"Số ngày công phải từ 0 đến {self.STANDARD_WORK_DAYS}!",
            )
            return

        try:
            gio_ot = float(self.var_gio_ot.get().strip() or 0)
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Số giờ OT không hợp lệ!")
            return
        if not (0 <= gio_ot <= self.MAX_OT_HOURS):
            messagebox.showwarning(
                "Cảnh báo",
                f"Số giờ OT phải từ 0 đến {self.MAX_OT_HOURS:g} giờ/tháng!",
            )
            return

        # Không tin dữ liệu từ ô nhập: phụ cấp luôn lấy theo chức vụ đã nạp từ CSDL.
        phu_cap = self.dict_nhan_vien[ma_nv][2]
        self.var_phu_cap.set(self.format_money_str(phu_cap))
        _, tien_luong_ot = self.tinh_luong()
        luong_cb = self.parse_money(self.var_luong_cb.get())
        khoan_tru = self.parse_money(self.var_khoan_tru.get())
        tong_thu_nhap = (
            (luong_cb / self.STANDARD_WORK_DAYS) * ngay_cong
            + tien_luong_ot
            + phu_cap
        )
        if khoan_tru > tong_thu_nhap:
            messagebox.showwarning(
                "Cảnh báo",
                "Khoản trừ không được lớn hơn tổng lương và phụ cấp!",
            )
            return

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            values = (
                luong_cb,
                ngay_cong,
                gio_ot,
                phu_cap,
                khoan_tru,
            )
            cursor.execute(
                """
                SELECT id
                FROM bang_luong
                WHERE ma_nv = %s AND thang = %s AND nam = %s
                LIMIT 1 FOR UPDATE
                """,
                (ma_nv, thang, nam),
            )
            existing_row = cursor.fetchone()

            if existing_row:
                cursor.execute(
                    """
                    UPDATE bang_luong
                    SET luong_cb = %s, ngay_cong = %s, gio_ot = %s,
                        phu_cap = %s, khoan_tru = %s,
                        ngay_tinh = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    values + (existing_row[0],),
                )
                action = "cập nhật"
            else:
                cursor.execute(
                    """
                    INSERT INTO bang_luong
                        (ma_nv, thang, nam, luong_cb, ngay_cong, gio_ot,
                         phu_cap, khoan_tru)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (ma_nv, thang, nam) + values,
                )
                action = "lưu"
            conn.commit()
            messagebox.showinfo(
                "Thành công",
                f"Đã {action} bảng lương tháng {thang}/{nam} cho nhân viên"
                f" {self.var_ten_nv.get()} ({ma_nv})!",
            )
            self.load_data()
        except Error as e:
            conn.rollback()
            show_database_error(e, "lưu bảng lương")
        finally:
            conn.close()

    def xoa_bang_luong(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(
                "Thông báo", "Vui lòng chọn bảng lương cần xóa!"
            )
            return

        vals = self.tree.item(selected, "values")
        ma_nv = vals[0]
        ho_ten = vals[1]
        thang_nam = vals[2]

        try:
            thang, nam = map(int, thang_nam.split("/"))
        except ValueError:
            messagebox.showerror("Lỗi", "Định dạng Tháng/Năm không hợp lệ!")
            return

        if self.role == "TruongPhong" and (
            ma_nv == self.user_actual_ma_nv or ma_nv == self.user_login_name
        ):
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không thể tự xóa bảng lương của chính bản thân!",
            )
            return

        if messagebox.askyesno(
            "Xác nhận",
            f"Bạn có chắc chắn muốn xóa bảng lương tháng {thang_nam} của nhân"
            f" viên {ho_ten} ({ma_nv})?",
        ):
            conn = get_db_connection()
            if not conn:
                return
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM bang_luong WHERE ma_nv=%s AND thang=%s AND"
                    " nam=%s",
                    (ma_nv, thang, nam),
                )
                conn.commit()
                messagebox.showinfo("Thành công", "Đã xóa bảng lương!")
                self.load_data()
                self.lam_moi()
            except Error as e:
                show_database_error(e, "xóa bảng lương")
            finally:
                conn.close()

    def xuat_excel(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning(
                "Không có dữ liệu",
                "Không có dữ liệu bảng lương để xuất.",
                parent=self.parent,
            )
            return

        now = datetime.datetime.now()
        if self.role == "NhanVien":
            ma_nv = self.user_actual_ma_nv or self.user_login_name or "nhan_vien"
            nam = self.var_filter_nam.get().strip() or str(now.year)
            thang = self.var_filter_thang.get().strip()
            period_suffix = (
                f"_{int(thang):02d}" if thang.isdigit() else "_tat_ca"
            )
            initial_filename = f"bang_luong_{ma_nv}_{nam}{period_suffix}.xlsx"
        else:
            initial_filename = f"bang_luong_{now:%Y_%m}.xlsx"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=initial_filename,
            filetypes=[
                ("Excel Workbook", "*.xlsx"),
                ("Tất cả các file", "*.*"),
            ],
            title="Xuất bảng lương ra file Excel",
            parent=self.parent,
        )
        if not filepath:
            return

        try:
            rows = []
            totals = [0, 0, 0.0, 0, 0, 0, 0]
            for index, item in enumerate(items, start=1):
                values = list(self.tree.item(item, "values"))
                thang, nam = self.split_payroll_period(values[2])
                row = [
                    index,
                    str(values[0]),
                    str(values[1]),
                    thang,
                    nam,
                    self.export_integer(values[3]),
                    self.export_number(values[4]),
                    self.export_number(values[5]),
                    self.export_integer(values[6]),
                    self.export_integer(values[7]),
                    self.export_integer(values[8]),
                    self.export_integer(values[9]),
                ]
                totals[0] += row[5]
                totals[1] += row[6]
                totals[2] += row[7]
                totals[3] += row[8]
                totals[4] += row[9]
                totals[5] += row[10]
                totals[6] += row[11]
                rows.append(row)

            self.write_payroll_xlsx(filepath, now, rows, totals)
            messagebox.showinfo(
                "Thành công",
                f"Đã xuất thành công file Excel tại:\n{filepath}",
                parent=self.parent,
            )
        except Exception as e:
            show_file_error(e, "xuất bảng lương", parent=self.parent)

    def get_export_scope(self):
        if self.role == "NhanVien":
            thang = self.var_filter_thang.get().strip()
            nam = self.var_filter_nam.get().strip()
            ky_luong = (
                f"tháng {int(thang):02d}/{nam}"
                if thang.isdigit()
                else f"tất cả các tháng năm {nam}"
            )
            ma_nv = self.user_actual_ma_nv or self.user_login_name
            return f"Nhân viên {ma_nv} - {ky_luong}"
        if self.role == "TruongPhong" and self.user_ma_phong_ban:
            return f"Phòng ban {self.user_ma_phong_ban} - dữ liệu đang hiển thị"
        return "Toàn bộ nhân viên - dữ liệu đang hiển thị"

    @staticmethod
    def split_payroll_period(value):
        parts = str(value).split("/", 1)
        if len(parts) != 2:
            return "", ""
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return parts[0], parts[1]

    @staticmethod
    def export_integer(value):
        digits = re.sub(r"[^0-9-]", "", str(value))
        return int(digits) if digits not in ("", "-") else 0

    @staticmethod
    def export_number(value):
        try:
            number = float(str(value).replace(",", "."))
            return int(number) if number.is_integer() else number
        except (TypeError, ValueError):
            return 0

    def write_payroll_xlsx(self, filepath, exported_at, rows, totals):
        """Tạo XLSX bằng thư viện chuẩn để giữ kiểu số và độ rộng cột."""
        headers = [
            "STT", "Mã NV", "Họ và Tên", "Tháng", "Năm", "Lương CB (đ)",
            "Ngày công", "Số giờ OT", "Lương OT (đ)", "Phụ cấp (đ)",
            "Khoản trừ (đ)", "Thực nhận (đ)",
        ]
        column_widths = [6, 16, 32, 10, 10, 20, 14, 14, 20, 18, 18, 20]

        def text_cell(ref, value, style=4):
            value = escape(str(value or ""))
            return (
                f'<c r="{ref}" t="inlineStr" s="{style}">'
                f'<is><t xml:space="preserve">{value}</t></is></c>'
            )

        def number_cell(ref, value, style=5):
            return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'

        sheet_rows = [
            f'<row r="1" ht="26" customHeight="1">{text_cell("A1", "BÁO CÁO BẢNG LƯƠNG NHÂN VIÊN", 1)}</row>',
            f'<row r="2">{text_cell("A2", f"Thời điểm xuất: {exported_at:%d/%m/%Y %H:%M}", 2)}</row>',
            f'<row r="3">{text_cell("A3", f"Phạm vi: {self.get_export_scope()}", 2)}</row>',
            '<row r="4"/>',
        ]

        header_cells = "".join(
            text_cell(f"{chr(65 + index)}5", header, 3)
            for index, header in enumerate(headers)
        )
        sheet_rows.append(
            f'<row r="5" ht="32" customHeight="1">{header_cells}</row>'
        )

        for row_number, row in enumerate(rows, start=6):
            cells = [
                number_cell(f"A{row_number}", row[0]),
                text_cell(f"B{row_number}", row[1]),
                text_cell(f"C{row_number}", row[2]),
                number_cell(f"D{row_number}", row[3]),
                number_cell(f"E{row_number}", row[4]),
                number_cell(f"F{row_number}", row[5]),
                number_cell(f"G{row_number}", row[6], 6),
                number_cell(f"H{row_number}", row[7], 6),
                number_cell(f"I{row_number}", row[8]),
                number_cell(f"J{row_number}", row[9]),
                number_cell(f"K{row_number}", row[10]),
                number_cell(f"L{row_number}", row[11]),
            ]
            sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')

        total_row = len(rows) + 7
        total_cells = [
            text_cell(f"A{total_row}", "", 7),
            text_cell(f"B{total_row}", "", 7),
            text_cell(f"C{total_row}", "TỔNG CỘNG", 7),
            text_cell(f"D{total_row}", "", 7),
            text_cell(f"E{total_row}", "", 7),
            number_cell(f"F{total_row}", totals[0], 8),
            number_cell(f"G{total_row}", totals[1], 9),
            number_cell(f"H{total_row}", totals[2], 9),
            number_cell(f"I{total_row}", totals[3], 8),
            number_cell(f"J{total_row}", totals[4], 8),
            number_cell(f"K{total_row}", totals[5], 8),
            number_cell(f"L{total_row}", totals[6], 8),
        ]
        sheet_rows.append(
            f'<row r="{total_row}" ht="22" customHeight="1">'
            f'{"".join(total_cells)}</row>'
        )

        columns_xml = "".join(
            f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
            for index, width in enumerate(column_widths, start=1)
        )
        last_data_row = len(rows) + 5
        worksheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="5" topLeftCell="A6" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="20"/>
  <cols>{columns_xml}</cols>
  <sheetData>{"".join(sheet_rows)}</sheetData>
  <autoFilter ref="A5:L{last_data_row}"/>
  <mergeCells count="3"><mergeCell ref="A1:L1"/><mergeCell ref="A2:L2"/><mergeCell ref="A3:L3"/></mergeCells>
</worksheet>'''

        content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
        root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
        workbook_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Bảng lương" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
        workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
        styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="16"/><color rgb="FF1E293B"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><color rgb="FF0F172A"/><name val="Calibri"/></font>
  </fonts>
  <fills count="4"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDBEAFE"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="2"><border/><border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="10">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="3" fontId="0" fillId="0" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="4" fontId="0" fillId="0" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="3" fontId="3" fillId="3" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="4" fontId="3" fillId="3" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''

        with ZipFile(filepath, "w", ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", content_types)
            workbook.writestr("_rels/.rels", root_rels)
            workbook.writestr("xl/workbook.xml", workbook_xml)
            workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            workbook.writestr("xl/styles.xml", styles_xml)
            workbook.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    def load_data(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)

            if self.role == "NhanVien":
                query = """
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb,
                           bl.ngay_cong, bl.gio_ot, bl.luong_ot, bl.phu_cap,
                           bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE bl.ma_nv = %s OR nv.nguoi_dung_id = %s
                """
                params = [
                    self.user_actual_ma_nv or self.user_login_name,
                    self.user_db_id,
                ]

                thang_flt = self.var_filter_thang.get()
                nam_flt = self.var_filter_nam.get()
                if thang_flt != "Tất cả":
                    query += " AND bl.thang = %s"
                    params.append(int(thang_flt))
                if nam_flt:
                    query += " AND bl.nam = %s"
                    params.append(int(nam_flt))

                query += " ORDER BY bl.nam DESC, bl.thang DESC"
                cursor.execute(query, tuple(params))

            elif self.role == "TruongPhong" and self.user_ma_phong_ban:
                query = """
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb,
                           bl.ngay_cong, bl.gio_ot, bl.luong_ot, bl.phu_cap,
                           bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE nv.ma_phong_ban = %s AND trang_thai <> 'Đã nghỉ việc'
                    ORDER BY bl.nam DESC, bl.thang DESC, bl.ma_nv ASC
                """
                cursor.execute(query, (self.user_ma_phong_ban,))

            else:
                query = """
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb,
                           bl.ngay_cong, bl.gio_ot, bl.luong_ot, bl.phu_cap,
                           bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    ORDER BY bl.nam DESC, bl.thang DESC, bl.ma_nv ASC
                """
                cursor.execute(query)

            self.refresh_table(cursor.fetchall())
        except Error as e:
            show_database_error(e, "tải danh sách bảng lương")
        finally:
            conn.close()

    def refresh_table(self, data_list):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in data_list:
            thang_nam = f"{row['thang']:02d}/{row['nam']}"
            luong_cb = self.format_money_str(row["luong_cb"])
            luong_ot = self.format_money_str(row["luong_ot"])
            gio_ot = float(row["gio_ot"] or 0)
            gio_ot = f"{gio_ot:.1f}".rstrip("0").rstrip(".")
            phu_cap = self.format_money_str(row["phu_cap"])
            khoan_tru = self.format_money_str(row["khoan_tru"])
            thuc_nhan = self.format_money_str(row["thuc_nhan"])

            self.tree.insert(
                "",
                tk.END,
                values=(
                    row["ma_nv"],
                    row["ho_ten"] or "Chưa cập nhật",
                    thang_nam,
                    luong_cb,
                    row["ngay_cong"],
                    gio_ot,
                    luong_ot,
                    phu_cap,
                    khoan_tru,
                    thuc_nhan,
                ),
            )

    def tim_kiem(self):
        if self.role == "NhanVien":
            self.load_data()
            return

        keyword = self.var_tim_kiem.get().strip()
        if not keyword or keyword == getattr(
            self, "placeholder_text", "Nhập..."
        ):
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
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb,
                           bl.ngay_cong, bl.gio_ot, bl.luong_ot, bl.phu_cap,
                           bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE nv.ma_phong_ban = %s AND (bl.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR CONCAT(bl.thang, '/', bl.nam) LIKE %s) 
                """
                cursor.execute(query, (self.user_ma_phong_ban, p, p, p))
            else:
                query = """
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb,
                           bl.ngay_cong, bl.gio_ot, bl.luong_ot, bl.phu_cap,
                           bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE bl.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR CONCAT(bl.thang, '/', bl.nam) LIKE %s
                """
                cursor.execute(query, (p, p, p))

            self.refresh_table(cursor.fetchall())
        except Error as e:
            show_database_error(e, "tìm kiếm bảng lương")
        finally:
            conn.close()

    def lam_moi(self):
        self.var_thang.set(str(datetime.datetime.now().month))
        self.var_nam.set(str(datetime.datetime.now().year))
        self.var_ngay_cong.set(str(self.STANDARD_WORK_DAYS))
        self.var_gio_ot.set("0")
        self.var_phu_cap.set("0")
        self.var_khoan_tru.set("0")
        self.var_thuc_nhan.set("0 đ")
        self.var_ten_nv.set("")

        if self.role != "NhanVien":
            self.var_ma_nv.set("")
            self.var_luong_cb.set("0")
            self.var_tim_kiem.set("")
            self.hide_employee_popup()
            self.update_employee_placeholder()
            for item in self.tree.selection():
                self.tree.selection_remove(item)
        self.load_data()

    def on_double_click(self, event):
        if self.role != "NhanVien":
            self.on_tree_select(event)

    def show_context_menu(self, event):
        if self.role != "NhanVien":
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                self.tree.focus(item)
                try:
                    self.context_menu.tk_popup(event.x_root, event.y_root)
                finally:
                    self.context_menu.grab_release()

    def context_edit_luong(self):
        if self.tree.selection():
            self.on_tree_select(None)

    def context_delete_luong(self):
        self.xoa_bang_luong()

    def on_tree_select(self, event):
        if self.role == "NhanVien":
            return
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
                "Đây là bảng lương của bạn!\nTrưởng phòng chỉ được phép xem"
                " lương cá nhân, không thể tự chỉnh sửa lương cho chính mình.",
            )
            return

        display_str = f"{row_data['ma_nv']} - {row_data['ten_nv']}"
        self.var_ma_nv.set(display_str)
        self.var_ten_nv.set(row_data["ten_nv"])

        thang_nam_parts = row_data["thang_nam"].split("/")
        if len(thang_nam_parts) == 2:
            self.var_thang.set(str(int(thang_nam_parts[0])))
            self.var_nam.set(str(int(thang_nam_parts[1])))

        luong_cb_val = self.parse_money(row_data["luong_cb"])
        self.var_luong_cb.set(self.format_money_str(luong_cb_val))
        self.var_ngay_cong.set(str(int(row_data["ngay_cong"])))

        self.var_gio_ot.set(str(row_data["gio_ot"]))

        employee = self.dict_nhan_vien.get(row_data["ma_nv"])
        phu_cap = employee[2] if employee else self.parse_money(row_data["phu_cap"])
        self.var_phu_cap.set(self.format_money_str(phu_cap))
        self.var_khoan_tru.set(
            self.format_money_str(self.parse_money(row_data["khoan_tru"]))
        )
        self.tinh_luong()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Độc Lập - Quản Lý Bảng Lương")
    root.geometry("1150x650")

    test_frame = tk.Frame(root, bg="#f8fafc")
    test_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

    app = PayrollManagementForm(test_frame)

    root.mainloop()
