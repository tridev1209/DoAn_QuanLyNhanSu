import datetime
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import icon_button, icon_label
from user_error import show_database_error, show_file_error


ROLE_ADMIN = "Admin"
ROLE_MANAGER = "TruongPhong"
ALL_DEPARTMENTS = "Tất cả"
MIN_REPORT_YEAR = 2000
MAX_REPORT_YEAR = 2100


class StatisticsReportForm:

    def __init__(self, parent_frame, user_info=None):
        self.parent = parent_frame

        # Dữ liệu người dùng đăng nhập
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
        self.last_load_succeeded = False
        self.last_loaded_filter = None

        # Biến bộ lọc
        today = datetime.date.today()
        self.var_thang = tk.StringVar(value=str(today.month))
        self.var_nam = tk.StringVar(value=str(today.year))
        self.var_phong_ban_filter = tk.StringVar(value=ALL_DEPARTMENTS)
        self.var_report_status = tk.StringVar(value="Đang tải dữ liệu...")

        # Biến KPI Cards
        self.var_card_tong_nv = tk.StringVar(value="0 NV")
        self.var_card_dang_lam = tk.StringVar(value="0 vào / 0 nghỉ")
        self.var_card_bien_dong = tk.StringVar(value="0 NV")
        self.var_card_quy_luong = tk.StringVar(value="0 đ")

        # Biến Tỷ lệ Nam / Nữ
        self.var_ty_le_nam = tk.StringVar(value="Nam: 0% (0 NV)")
        self.var_ty_le_nu = tk.StringVar(value="Nữ: 0% (0 NV)")

        self.dict_phong_ban_filter = {ALL_DEPARTMENTS: None}

        self.get_user_department_and_id()
        self.create_widgets()
        self.load_phong_ban_combobox()
        self.load_all_dashboard_data()

    def _manager_scope_is_valid(self):
        """Trưởng phòng chỉ được xem dữ liệu khi xác định được phòng ban."""
        return self.role != ROLE_MANAGER or bool(self.user_ma_phong_ban)

    def _has_report_access(self):
        """Báo cáo tổng hợp chỉ dành cho quản trị viên và trưởng phòng."""
        return self.role in {ROLE_ADMIN, ROLE_MANAGER}

    def _selected_department_id(self):
        """Trả về phòng ban được phép xem; None tương ứng với toàn hệ thống."""
        if self.role == ROLE_MANAGER:
            return self.user_ma_phong_ban
        return self.dict_phong_ban_filter.get(
            self.var_phong_ban_filter.get()
        )

    def _get_valid_period(self):
        """Chuẩn hóa kỳ báo cáo để mọi đường gọi đều dùng tháng/năm hợp lệ."""
        today = datetime.date.today()
        try:
            month = int(self.var_thang.get())
        except (TypeError, ValueError):
            month = today.month
        month = min(12, max(1, month))

        try:
            year = int(self.var_nam.get())
        except (TypeError, ValueError):
            year = today.year
        year = min(MAX_REPORT_YEAR, max(MIN_REPORT_YEAR, year))

        self.var_thang.set(str(month))
        self.var_nam.set(str(year))
        return month, year

    @staticmethod
    def _previous_period(month, year):
        """Trả về tháng liền trước, bao gồm chuyển năm tại tháng 1."""
        return (12, year - 1) if month == 1 else (month - 1, year)

    def _on_department_mousewheel(self, event):
        """Cuộn danh sách phòng ban bằng bánh xe chuột trên Windows."""
        if event.delta:
            units = -1 if event.delta > 0 else 1
            self.dept_canvas.yview_scroll(units, "units")
        return "break"

    def _bind_department_mousewheel(self, widget):
        """Gắn cuộn chuột cho cả các widget con trong biểu đồ phòng ban."""
        widget.bind("<MouseWheel>", self._on_department_mousewheel)
        for child in widget.winfo_children():
            self._bind_department_mousewheel(child)

    def _clear_dashboard(self, status_message="Chưa có dữ liệu"):
        """Xóa số liệu cũ để không hiển thị nhầm sau khi tải thất bại."""
        self.last_load_succeeded = False
        self.last_loaded_filter = None
        self.var_card_tong_nv.set("0 NV")
        self.var_card_dang_lam.set("0 vào / 0 nghỉ")
        self.var_card_bien_dong.set("0 NV")
        self.var_card_quy_luong.set("0 đ")
        self.var_ty_le_nam.set("Nam: 0% (0 NV)")
        self.var_ty_le_nu.set("Nữ: 0% (0 NV)")

        if hasattr(self, "card_bien_dong_value"):
            self.card_bien_dong_value.configure(fg="#64748b")

        if hasattr(self, "bar_nam_fill"):
            self.bar_nam_fill.place_configure(relwidth=0)
            self.bar_nu_fill.place_configure(relwidth=0)
        if hasattr(self, "frame_dept_bars"):
            for widget in self.frame_dept_bars.winfo_children():
                widget.destroy()
        if hasattr(self, "tree"):
            for item in self.tree.get_children():
                self.tree.delete(item)

        self.var_report_status.set(status_message)

    def get_user_department_and_id(self):
        """Lấy Mã phòng ban và Mã NV thực tế của Trưởng phòng"""
        if self.role != ROLE_MANAGER:
            return

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT ma_nv, ma_phong_ban 
                FROM nhan_vien 
                WHERE nguoi_dung_id = %s OR ma_nv = %s
                ORDER BY (nguoi_dung_id = %s) DESC
                LIMIT 1
            """
            cursor.execute(
                query,
                (self.user_db_id, self.user_login_name, self.user_db_id),
            )
            row = cursor.fetchone()
            if row:
                self.user_ma_phong_ban = row["ma_phong_ban"]
                self.user_actual_ma_nv = row["ma_nv"]
        except Error as e:
            show_database_error(
                e, "xác định phạm vi phòng ban", parent=self.parent
            )
        finally:
            conn.close()

    def format_money_str(self, val):
        try:
            num = int(round(float(val)))
            return f"{num:,}".replace(",", ".")
        except (ValueError, TypeError):
            return "0"

    def create_widgets(self):
        # 1. TIÊU ĐỀ
        title_text = (
            "THỐNG KÊ & BÁO CÁO NHÂN SỰ PHÒNG BAN"
            if self.role == ROLE_MANAGER
            else "THỐNG KÊ & BÁO CÁO NHÂN SỰ TỔNG QUAN"
        )
        sub_title = (
            "Tổng quan tình hình nhân sự và chi phí lương"
            if self.role == ROLE_ADMIN
            else "Tình hình nhân sự và bảng lương nội bộ phòng ban"
        )

        header_frame = tk.Frame(self.parent, bg="#f8fafc")
        header_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            header_frame,
            text=title_text,
            font=("Helvetica", 14, "bold"),
            fg="#0f172a",
            bg="#f8fafc",
        ).pack(anchor="w")
        tk.Label(
            header_frame,
            text=sub_title,
            font=("Helvetica", 9, "italic"),
            fg="#64748b",
            bg="#f8fafc",
        ).pack(anchor="w")

        # 2. KHU VỰC 1: 4 THẺ TỔNG QUAN KPI CARDS
        kpi_frame = tk.Frame(self.parent, bg="#f8fafc")
        kpi_frame.pack(fill=tk.X, pady=(0, 10))

        # Card 1: Tổng NV
        card1 = tk.Frame(
            kpi_frame,
            bg="white",
            padx=12,
            pady=10,
            highlightbackground="#cbd5e1",
            highlightthickness=1,
        )
        card1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        icon_label(
            card1,
            text="NHÂN SỰ CUỐI THÁNG",
            icon="employees",
            icon_color="#2563eb",
            font=("Helvetica", 9, "bold"),
            fg="#64748b",
            bg="white",
        ).pack(anchor="w")
        tk.Label(
            card1,
            textvariable=self.var_card_tong_nv,
            font=("Helvetica", 15, "bold"),
            fg="#2563eb",
            bg="white",
        ).pack(anchor="w", pady=(4, 0))

        # Card 2: Đang làm việc
        card2 = tk.Frame(
            kpi_frame,
            bg="white",
            padx=12,
            pady=10,
            highlightbackground="#cbd5e1",
            highlightthickness=1,
        )
        card2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        icon_label(
            card2,
            text="BIẾN ĐỘNG NHÂN SỰ",
            icon="report",
            icon_color="#7c3aed",
            font=("Helvetica", 9, "bold"),
            fg="#64748b",
            bg="white",
        ).pack(anchor="w")
        tk.Label(
            card2,
            textvariable=self.var_card_dang_lam,
            font=("Helvetica", 15, "bold"),
            fg="#7c3aed",
            bg="white",
        ).pack(anchor="w", pady=(4, 0))

        # Card 3: So sánh nhân sự cuối tháng với tháng trước
        card3 = tk.Frame(
            kpi_frame,
            bg="white",
            padx=12,
            pady=10,
            highlightbackground="#cbd5e1",
            highlightthickness=1,
        )
        card3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        icon_label(
            card3,
            text="SO VỚI THÁNG TRƯỚC",
            icon="report",
            icon_color="#7c3aed",
            font=("Helvetica", 9, "bold"),
            fg="#64748b",
            bg="white",
        ).pack(anchor="w")
        self.card_bien_dong_value = tk.Label(
            card3,
            textvariable=self.var_card_bien_dong,
            font=("Helvetica", 15, "bold"),
            fg="#64748b",
            bg="white",
        )
        self.card_bien_dong_value.pack(anchor="w", pady=(4, 0))

        # Card 4: Quỹ lương
        card4 = tk.Frame(
            kpi_frame,
            bg="white",
            padx=12,
            pady=10,
            highlightbackground="#cbd5e1",
            highlightthickness=1,
        )
        card4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        icon_label(
            card4,
            text="TỔNG QUỸ LƯƠNG",
            icon="payroll",
            icon_color="#0284c7",
            font=("Helvetica", 9, "bold"),
            fg="#64748b",
            bg="white",
        ).pack(anchor="w")
        tk.Label(
            card4,
            textvariable=self.var_card_quy_luong,
            font=("Helvetica", 15, "bold"),
            fg="#0284c7",
            bg="white",
        ).pack(anchor="w", pady=(4, 0))

        # 3. KHU VỰC 2: BIỂU ĐỒ PHÂN BỔ PHÒNG BAN & CƠ CẤU GIỚI TÍNH (ĐÃ PHỐI MÀU SẮC NÉT)
        visual_frame = tk.Frame(self.parent, bg="#f8fafc")
        visual_frame.pack(fill=tk.X, pady=(0, 10))

        # Khối trái: Phân bổ Nhân viên theo Phòng Ban
        chart1_box = tk.LabelFrame(
            visual_frame,
            text=" Nhân sự cuối tháng theo Phòng ban ",
            font=("Helvetica", 10, "bold"),
            bg="white",
            fg="#0f172a",
            padx=12,
            pady=10,
        )
        chart1_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        dept_chart_container = tk.Frame(chart1_box, bg="white", height=110)
        dept_chart_container.pack(fill=tk.BOTH, expand=True)
        dept_chart_container.pack_propagate(False)

        self.dept_canvas = tk.Canvas(
            dept_chart_container,
            bg="white",
            highlightthickness=0,
            height=110,
        )
        dept_scrollbar = ttk.Scrollbar(
            dept_chart_container,
            orient=tk.VERTICAL,
            command=self.dept_canvas.yview,
        )
        self.dept_canvas.configure(yscrollcommand=dept_scrollbar.set)
        dept_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.dept_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame_dept_bars = tk.Frame(self.dept_canvas, bg="white")
        self.dept_canvas_window = self.dept_canvas.create_window(
            (0, 0), window=self.frame_dept_bars, anchor="nw"
        )
        self.frame_dept_bars.bind(
            "<Configure>",
            lambda _event: self.dept_canvas.configure(
                scrollregion=self.dept_canvas.bbox("all")
            ),
        )
        self.dept_canvas.bind(
            "<Configure>",
            lambda event: self.dept_canvas.itemconfigure(
                self.dept_canvas_window, width=event.width
            ),
        )
        self._bind_department_mousewheel(self.dept_canvas)
        self._bind_department_mousewheel(self.frame_dept_bars)

        # Khối phải: Cơ cấu Giới tính (Nam / Nữ)
        chart2_box = tk.LabelFrame(
            visual_frame,
            text=" Cơ cấu Giới tính theo kỳ ",
            font=("Helvetica", 10, "bold"),
            bg="white",
            fg="#0f172a",
            padx=12,
            pady=10,
        )
        chart2_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Thanh Nam (Xanh dương tươi)
        tk.Label(
            chart2_box,
            textvariable=self.var_ty_le_nam,
            font=("Helvetica", 9, "bold"),
            fg="#2563eb",
            bg="white",
        ).pack(anchor="w", pady=(2, 2))

        self.frame_nam_bg = tk.Frame(chart2_box, bg="#e2e8f0", height=14)
        self.frame_nam_bg.pack(fill=tk.X, pady=(0, 10))
        self.frame_nam_bg.pack_propagate(False)

        self.bar_nam_fill = tk.Frame(self.frame_nam_bg, bg="#2563eb")
        self.bar_nam_fill.place(relx=0, rely=0, relwidth=0, relheight=1.0)

        # Thanh Nữ (Hồng rực)
        tk.Label(
            chart2_box,
            textvariable=self.var_ty_le_nu,
            font=("Helvetica", 9, "bold"),
            fg="#ec4899",
            bg="white",
        ).pack(anchor="w", pady=(2, 2))

        self.frame_nu_bg = tk.Frame(chart2_box, bg="#e2e8f0", height=14)
        self.frame_nu_bg.pack(fill=tk.X, pady=(0, 5))
        self.frame_nu_bg.pack_propagate(False)

        self.bar_nu_fill = tk.Frame(self.frame_nu_bg, bg="#ec4899")
        self.bar_nu_fill.place(relx=0, rely=0, relwidth=0, relheight=1.0)

        # 4. KHU VỰC 3: BẢNG THỐNG KÊ LƯƠNG THEO PHÒNG BAN
        table_box = tk.LabelFrame(
            self.parent,
            text=" Thống kê Lương theo Phòng ban ",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            padx=8,
            pady=6,
        )
        table_box.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        cols = ("phong_ban", "so_nv", "tong_luong", "luong_tb")
        headers = {
            "phong_ban": "Phòng Ban",
            "so_nv": "Số NV Nhận Lương",
            "tong_luong": "Tổng Lương Thực Nhận (đ)",
            "luong_tb": "Thực Nhận TB/NV (đ)",
        }
        widths = {
            "phong_ban": 280,
            "so_nv": 120,
            "tong_luong": 220,
            "luong_tb": 220,
        }

        self.tree = ttk.Treeview(
            table_box, columns=cols, show="headings", height=5
        )
        for c in cols:
            self.tree.heading(c, text=headers[c])
            align = (
                tk.W
                if c == "phong_ban"
                else (tk.CENTER if c == "so_nv" else tk.E)
            )
            self.tree.column(
                c,
                width=widths[c],
                minwidth=90 if c != "phong_ban" else 150,
                anchor=align,
                stretch=True,
            )

        self.tree.tag_configure("odd", background="#f8fafc")
        self.tree.tag_configure("even", background="white")

        sb = ttk.Scrollbar(table_box, orient=tk.VERTICAL, command=self.tree.yview)
        sb_x = ttk.Scrollbar(
            table_box, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        self.tree.configure(yscroll=sb.set, xscroll=sb_x.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Label(
            table_box,
            textvariable=self.var_report_status,
            font=("Helvetica", 8, "italic"),
            fg="#64748b",
            bg="#f8fafc",
            anchor="w",
        ).pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))
        self.tree.pack(fill=tk.BOTH, expand=True)

        # 5. KHU VỰC 4: BỘ LỌC BÁO CÁO & NÚT CHỨC NĂNG
        bottom_frame = tk.Frame(self.parent, bg="#f8fafc")
        bottom_frame.pack(fill=tk.X)

        filter_box = tk.LabelFrame(
            bottom_frame,
            text=" Bộ lọc Báo cáo ",
            font=("Helvetica", 9, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            padx=10,
            pady=5,
        )
        filter_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tk.Label(
            filter_box, text="Tháng/Năm:", bg="#f8fafc", font=("Helvetica", 9)
        ).grid(row=0, column=0, sticky="w")

        self.cb_thang = ttk.Combobox(
            filter_box,
            textvariable=self.var_thang,
            width=4,
            state="readonly",
            values=[str(i) for i in range(1, 13)],
        )
        self.cb_thang.grid(row=0, column=1, padx=2)
        self.cb_thang.bind(
            "<<ComboboxSelected>>", lambda e: self.load_all_dashboard_data()
        )

        tk.Label(
            filter_box, text="/", bg="#f8fafc", font=("Helvetica", 9, "bold")
        ).grid(row=0, column=2)

        self.entry_nam = tk.Entry(
            filter_box, textvariable=self.var_nam, width=6, font=("Helvetica", 9)
        )
        self.entry_nam.grid(row=0, column=3, padx=2)
        self.entry_nam.bind("<KeyRelease>", self.on_nam_key_release)
        self.entry_nam.bind("<FocusOut>", self.validate_nam_value)
        self.entry_nam.bind("<Return>", self.validate_nam_value)

        tk.Label(
            filter_box,
            text="Phòng ban:",
            bg="#f8fafc",
            font=("Helvetica", 9),
        ).grid(row=0, column=4, padx=(10, 2))

        self.cb_filter_pb = ttk.Combobox(
            filter_box,
            textvariable=self.var_phong_ban_filter,
            width=18,
            state="readonly",
        )
        self.cb_filter_pb.grid(row=0, column=5, padx=2)
        self.cb_filter_pb.bind(
            "<<ComboboxSelected>>", lambda e: self.load_all_dashboard_data()
        )

        # Khung Chức Năng
        action_box = tk.LabelFrame(
            bottom_frame,
            text=" Chức năng ",
            font=("Helvetica", 9, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            padx=10,
            pady=5,
        )
        action_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        icon_button(
            action_box,
            text="Làm mới (Hôm nay)",
            icon="refresh",
            font=("Segoe UI", 9, "bold"),
            bg="#0284c7",
            fg="white",
            padx=10,
            pady=3,
            bd=0,
            cursor="hand2",
            command=self.reset_filters_to_now,
        ).pack(side=tk.LEFT, padx=3)

        icon_button(
            action_box,
            text="Xuất Báo Cáo (Excel)",
            icon="export",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="white",
            padx=10,
            pady=3,
            bd=0,
            cursor="hand2",
            command=self.xuat_excel_report,
        ).pack(side=tk.LEFT, padx=3)

    def on_nam_key_release(self, event):
        """Chỉ cho phép nhập số và tối đa 4 chữ số"""
        raw = str(self.var_nam.get())
        digits = re.sub(r"\D", "", raw)
        if len(digits) > 4:
            digits = digits[:4]
        self.var_nam.set(digits)

    def validate_nam_value(self, event=None):
        """Kiểm tra ngưỡng từ 2000 đến 2100 khi rời ô nhập hoặc nhấn Enter"""
        self._get_valid_period()
        self.load_all_dashboard_data()
        if event is not None and getattr(event, "keysym", None) == "Return":
            return "break"

    def reset_filters_to_now(self):
        """Khôi phục bộ lọc về thời gian hiện tại của hệ thống"""
        today = datetime.date.today()
        self.var_thang.set(str(today.month))
        self.var_nam.set(str(today.year))

        if self.role == ROLE_ADMIN:
            self.var_phong_ban_filter.set(ALL_DEPARTMENTS)

        self.load_all_dashboard_data()

    def load_phong_ban_combobox(self):
        if not self._has_report_access():
            self.var_phong_ban_filter.set("Không có quyền truy cập")
            self.cb_filter_pb["values"] = ("Không có quyền truy cập",)
            self.cb_filter_pb.config(state="disabled")
            return

        if self.role == ROLE_MANAGER and not self.user_ma_phong_ban:
            self.var_phong_ban_filter.set("Chưa xác định phòng ban")
            self.cb_filter_pb["values"] = ("Chưa xác định phòng ban",)
            self.cb_filter_pb.config(state="disabled")
            return

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            if self.role == ROLE_MANAGER and self.user_ma_phong_ban:
                cursor.execute(
                    "SELECT ma_phong_ban, ten_phong_ban FROM phong_ban WHERE"
                    " ma_phong_ban = %s",
                    (self.user_ma_phong_ban,),
                )
            else:
                cursor.execute(
                    "SELECT ma_phong_ban, ten_phong_ban FROM phong_ban "
                    "ORDER BY ten_phong_ban"
                )

            rows = cursor.fetchall()
            self.dict_phong_ban_filter = {ALL_DEPARTMENTS: None}
            for r in rows:
                self.dict_phong_ban_filter[r["ten_phong_ban"]] = r[
                    "ma_phong_ban"
                ]

            self.cb_filter_pb["values"] = list(
                self.dict_phong_ban_filter.keys()
            )
            if self.role == ROLE_MANAGER and rows:
                self.var_phong_ban_filter.set(rows[0]["ten_phong_ban"])
                self.cb_filter_pb.config(state="disabled")
            elif self.role == ROLE_MANAGER:
                self.var_phong_ban_filter.set("Chưa xác định phòng ban")
                self.cb_filter_pb["values"] = ("Chưa xác định phòng ban",)
                self.cb_filter_pb.config(state="disabled")
            else:
                self.var_phong_ban_filter.set(ALL_DEPARTMENTS)
        except Error as e:
            show_database_error(e, "tải danh sách phòng ban", parent=self.parent)
        finally:
            conn.close()

    def load_all_dashboard_data(self):
        """Tải toàn bộ số liệu cho Dashboard"""
        if not self._has_report_access():
            self._clear_dashboard(
                "Tài khoản hiện tại không có quyền xem báo cáo tổng hợp."
            )
            return

        if not self._manager_scope_is_valid():
            self._clear_dashboard(
                "Không thể tải báo cáo: tài khoản trưởng phòng chưa được gán phòng ban."
            )
            return

        thang_val, nam_val = self._get_valid_period()
        period_start = datetime.date(nam_val, thang_val, 1)
        if thang_val == 12:
            next_period_start = datetime.date(nam_val + 1, 1, 1)
        else:
            next_period_start = datetime.date(nam_val, thang_val + 1, 1)
        period_end = next_period_start - datetime.timedelta(days=1)
        previous_period_end = period_start - datetime.timedelta(days=1)
        conn = get_db_connection()
        if not conn:
            self._clear_dashboard("Không thể kết nối cơ sở dữ liệu.")
            return

        try:
            cursor = conn.cursor(dictionary=True)
            selected_ma_pb = self._selected_department_id()

            # ------------------------------------------------------------------
            # 1. TẢI DỮ LIỆU KPI CARDS
            # ------------------------------------------------------------------
            kpi_department_filter = ""
            kpi_params = [
                period_end,
                period_end,
                period_start,
                period_end,
                period_start,
                period_end,
                previous_period_end,
                previous_period_end,
            ]
            if selected_ma_pb is not None:
                kpi_department_filter = " WHERE nv.ma_phong_ban = %s"
                kpi_params.append(selected_ma_pb)

            # Ảnh chụp biên chế tại ngày cuối kỳ được xác định hoàn toàn từ
            # ngày vào làm/ngày nghỉ việc, không phụ thuộc bảng lương.
            cursor.execute(
                f"""
                    SELECT COALESCE(SUM(CASE
                               WHEN nv.ngay_vao_lam <= %s
                                AND (nv.ngay_nghi_viec IS NULL
                                     OR nv.ngay_nghi_viec > %s)
                               THEN 1 ELSE 0 END), 0) AS tong_nv,
                           COALESCE(SUM(CASE
                               WHEN nv.ngay_vao_lam BETWEEN %s AND %s
                               THEN 1 ELSE 0 END), 0) AS vao_lam,
                           COALESCE(SUM(CASE
                               WHEN nv.ngay_nghi_viec BETWEEN %s AND %s
                               THEN 1 ELSE 0 END), 0) AS nghi_viec,
                           COALESCE(SUM(CASE
                               WHEN nv.ngay_vao_lam <= %s
                                AND (nv.ngay_nghi_viec IS NULL
                                     OR nv.ngay_nghi_viec > %s)
                               THEN 1 ELSE 0 END), 0) AS tong_nv_truoc
                    FROM nhan_vien nv
                    {kpi_department_filter}
                """,
                tuple(kpi_params),
            )
            kpi_row = cursor.fetchone() or {}
            tong_nv = int(kpi_row.get("tong_nv") or 0)
            vao_lam = int(kpi_row.get("vao_lam") or 0)
            nghi_viec = int(kpi_row.get("nghi_viec") or 0)
            previous_total = int(kpi_row.get("tong_nv_truoc") or 0)

            thang_truoc, nam_truoc = self._previous_period(
                thang_val, nam_val
            )

            salary_department_filter = ""
            salary_params = [thang_val, nam_val]
            if selected_ma_pb is not None:
                salary_department_filter = " AND nv.ma_phong_ban = %s"
                salary_params.append(selected_ma_pb)

            cursor.execute(
                f"""
                    SELECT COALESCE(SUM(bl.thuc_nhan), 0) AS tong_luong
                    FROM bang_luong bl
                    JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE bl.thang = %s AND bl.nam = %s
                    {salary_department_filter}
                """,
                tuple(salary_params),
            )
            salary_row = cursor.fetchone() or {}
            quy_luong = salary_row.get("tong_luong") or 0
            employee_delta = tong_nv - previous_total

            self.var_card_tong_nv.set(f"{tong_nv} NV")
            self.var_card_dang_lam.set(
                f"{vao_lam} vào / {nghi_viec} nghỉ"
            )
            delta_text = f"{employee_delta:+d} NV" if employee_delta else "0 NV"
            self.var_card_bien_dong.set(delta_text)
            self.card_bien_dong_value.configure(
                fg=(
                    "#16a34a"
                    if employee_delta > 0
                    else "#dc2626" if employee_delta < 0 else "#64748b"
                )
            )
            self.var_card_quy_luong.set(
                f"{self.format_money_str(quy_luong)} đ"
            )

            # ------------------------------------------------------------------
            # 2. TẢI CƠ CẤU GIỚI TÍNH
            # ------------------------------------------------------------------
            gender_conditions = [
                "nv.ngay_vao_lam <= %s",
                "(nv.ngay_nghi_viec IS NULL OR nv.ngay_nghi_viec > %s)",
            ]
            gender_params = [period_end, period_end]
            if selected_ma_pb is not None:
                gender_conditions.append("nv.ma_phong_ban = %s")
                gender_params.append(selected_ma_pb)

            q_gender = f"""
                SELECT nv.gioi_tinh, COUNT(*) AS cnt
                FROM nhan_vien nv
                WHERE {' AND '.join(gender_conditions)}
                GROUP BY nv.gioi_tinh
            """
            cursor.execute(q_gender, tuple(gender_params))
            g_rows = cursor.fetchall()

            nam_cnt = 0
            nu_cnt = 0
            for g in g_rows:
                if g["gioi_tinh"] == "Nam":
                    nam_cnt = g["cnt"]
                elif g["gioi_tinh"] == "Nữ":
                    nu_cnt = g["cnt"]

            total_gender = nam_cnt + nu_cnt

            def percent(count):
                return (
                    round((count / total_gender) * 100, 1)
                    if total_gender
                    else 0
                )

            pct_nam = percent(nam_cnt)
            pct_nu = percent(nu_cnt)

            self.var_ty_le_nam.set(f"Nam: {pct_nam}% ({nam_cnt} NV)")
            self.var_ty_le_nu.set(f"Nữ: {pct_nu}% ({nu_cnt} NV)")

            self.bar_nam_fill.place(
                relx=0, rely=0, relwidth=pct_nam / 100.0, relheight=1.0
            )
            self.bar_nu_fill.place(
                relx=0, rely=0, relwidth=pct_nu / 100.0, relheight=1.0
            )

            # ------------------------------------------------------------------
            # 3. TẢI THANH BIỂU ĐỒ PHÒNG BAN (MÀU TƯƠI SẮC NÉT)
            # ------------------------------------------------------------------
            for widget in self.frame_dept_bars.winfo_children():
                widget.destroy()
            self.dept_canvas.yview_moveto(0)

            q_dept = """
                SELECT pb.ten_phong_ban,
                       COUNT(nv.ma_nv) AS cnt
                FROM phong_ban pb
                LEFT JOIN nhan_vien nv
                    ON pb.ma_phong_ban = nv.ma_phong_ban
                    AND nv.ngay_vao_lam <= %s
                    AND (nv.ngay_nghi_viec IS NULL
                         OR nv.ngay_nghi_viec > %s)
            """
            if selected_ma_pb is not None:
                q_dept += " WHERE pb.ma_phong_ban = %s"
                cursor.execute(
                    q_dept + " GROUP BY pb.ma_phong_ban, pb.ten_phong_ban",
                    (period_end, period_end, selected_ma_pb),
                )
            else:
                cursor.execute(
                    q_dept
                    + " GROUP BY pb.ma_phong_ban, pb.ten_phong_ban ORDER BY cnt"
                    " DESC, pb.ten_phong_ban",
                    (period_end, period_end),
                )

            dept_rows = cursor.fetchall()
            max_cnt = max([r["cnt"] for r in dept_rows], default=1) or 1
            palette = ["#2563eb", "#0284c7", "#0d9488", "#7c3aed", "#e11d48"]

            for idx, d in enumerate(dept_rows):
                row_f = tk.Frame(self.frame_dept_bars, bg="white")
                row_f.pack(fill=tk.X, pady=3)

                tk.Label(
                    row_f,
                    text=d["ten_phong_ban"],
                    width=15,
                    anchor="w",
                    font=("Helvetica", 9),
                    bg="white",
                    fg="#334155",
                ).pack(side=tk.LEFT)

                # Custom Colored Progress Bar
                pbar_bg = tk.Frame(row_f, bg="#e2e8f0", height=12)
                pbar_bg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
                pbar_bg.pack_propagate(False)

                color_code = palette[idx % len(palette)]
                ratio = (d["cnt"] / max_cnt) if max_cnt > 0 else 0

                pbar_fill = tk.Frame(pbar_bg, bg=color_code)
                pbar_fill.place(relx=0, rely=0, relwidth=ratio, relheight=1.0)

                tk.Label(
                    row_f,
                    text=f"{d['cnt']} NV",
                    font=("Helvetica", 9, "bold"),
                    bg="white",
                    fg=color_code,
                ).pack(side=tk.LEFT)

            if not dept_rows:
                tk.Label(
                    self.frame_dept_bars,
                    text="Chưa có dữ liệu phòng ban.",
                    font=("Helvetica", 9, "italic"),
                    bg="white",
                    fg="#64748b",
                ).pack(anchor="w", pady=8)

            self._bind_department_mousewheel(self.frame_dept_bars)

            # ------------------------------------------------------------------
            # 4. TẢI BẢNG THỐNG KÊ LƯƠNG THEO PHÒNG BAN
            # ------------------------------------------------------------------
            for item in self.tree.get_children():
                self.tree.delete(item)

            q_tbl = """
                SELECT pb.ten_phong_ban, 
                       COUNT(DISTINCT nv.ma_nv) AS so_nv,
                       SUM(bl.thuc_nhan) AS tong_luong,
                       AVG(bl.thuc_nhan) AS luong_tb
                FROM phong_ban pb
                JOIN nhan_vien nv ON pb.ma_phong_ban = nv.ma_phong_ban
                JOIN bang_luong bl ON nv.ma_nv = bl.ma_nv
                WHERE bl.thang = %s AND bl.nam = %s
            """
            p_tbl = [thang_val, nam_val]

            if selected_ma_pb is not None:
                q_tbl += " AND pb.ma_phong_ban = %s"
                p_tbl.append(selected_ma_pb)

            q_tbl += " GROUP BY pb.ma_phong_ban, pb.ten_phong_ban ORDER BY tong_luong DESC"
            cursor.execute(q_tbl, tuple(p_tbl))

            tbl_rows = cursor.fetchall()
            for index, r in enumerate(tbl_rows):
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        r["ten_phong_ban"],
                        f"{r['so_nv']} người",
                        self.format_money_str(r["tong_luong"]),
                        self.format_money_str(r["luong_tb"]),
                    ),
                    tags=("even" if index % 2 == 0 else "odd",),
                )

            filter_name = self.var_phong_ban_filter.get()
            self.var_report_status.set(
                f"Kỳ báo cáo: {thang_val:02d}/{nam_val}  •  "
                f"Phạm vi: {filter_name}  •  {len(tbl_rows)} phòng ban có bảng lương  •  "
                f"Vào: {vao_lam}, nghỉ: {nghi_viec}  •  "
                f"Ròng so với {thang_truoc:02d}/{nam_truoc}  •  "
                "Nhân sự được tính theo ngày vào/nghỉ việc"
            )
            self.last_load_succeeded = True
            self.last_loaded_filter = (thang_val, nam_val, selected_ma_pb)

        except Error as e:
            self._clear_dashboard("Không thể tải dữ liệu báo cáo.")
            show_database_error(e, "tải báo cáo thống kê", parent=self.parent)
        finally:
            conn.close()

    def xuat_excel_report(self):
        thang_val, nam_val = self._get_valid_period()
        thang_truoc, nam_truoc = self._previous_period(
            thang_val, nam_val
        )
        current_filter = (
            thang_val,
            nam_val,
            self._selected_department_id(),
        )
        if self.last_loaded_filter != current_filter:
            self.load_all_dashboard_data()

        if not self.last_load_succeeded:
            messagebox.showwarning(
                "Chưa thể xuất báo cáo",
                "Dữ liệu báo cáo chưa được tải thành công. Vui lòng làm mới và thử lại.",
                parent=self.parent,
            )
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile=f"bao_cao_nhan_su_{nam_val}_{thang_val:02d}.xlsx",
            filetypes=[
                ("Excel Workbook", "*.xlsx"),
                ("Tất cả các file", "*.*"),
            ],
            title="Xuất Báo Cáo Thống Kê Nhân Sự",
            parent=self.parent,
        )
        if not filepath:
            return

        try:
            employee_changes = re.findall(
                r"-?\d+", self.var_card_dang_lam.get()
            )
            joined_count = int(employee_changes[0]) if employee_changes else 0
            left_count = int(employee_changes[1]) if len(employee_changes) > 1 else 0
            male_count, male_rate = self.parse_gender_summary(
                self.var_ty_le_nam.get()
            )
            female_count, female_rate = self.parse_gender_summary(
                self.var_ty_le_nu.get()
            )

            department_rows = []
            for item in self.tree.get_children():
                values = self.tree.item(item, "values")
                department_rows.append([
                    str(values[0]),
                    self.export_integer(values[1]),
                    self.export_integer(values[2]),
                    self.export_integer(values[3]),
                ])

            report_data = {
                "period": f"{thang_val:02d}/{nam_val}",
                "scope": self.var_phong_ban_filter.get(),
                "previous_period": f"{thang_truoc:02d}/{nam_truoc}",
                "total_employees": self.export_integer(
                    self.var_card_tong_nv.get()
                ),
                "joined": joined_count,
                "left": left_count,
                "employee_delta": self.export_integer(
                    self.var_card_bien_dong.get(), allow_negative=True
                ),
                "total_payroll": self.export_integer(
                    self.var_card_quy_luong.get()
                ),
                "gender_rows": [
                    ["Nam", male_count, male_rate],
                    ["Nữ", female_count, female_rate],
                ],
                "department_rows": department_rows,
            }
            self.write_statistics_xlsx(
                filepath, datetime.datetime.now(), report_data
            )

            messagebox.showinfo(
                "Thành công",
                f"Đã xuất thành công file Excel tại:\n{filepath}",
                parent=self.parent,
            )
        except Exception as e:
            show_file_error(e, "xuất báo cáo", parent=self.parent)

    @staticmethod
    def export_integer(value, allow_negative=False):
        pattern = r"[-+]?\d[\d.]*" if allow_negative else r"\d[\d.]*"
        match = re.search(pattern, str(value))
        if not match:
            return 0
        sign = -1 if match.group(0).startswith("-") else 1
        digits = re.sub(r"\D", "", match.group(0))
        return sign * int(digits) if digits else 0

    @staticmethod
    def parse_gender_summary(value):
        match = re.search(r"([\d.,]+)%\s*\((\d+)\s*NV\)", str(value))
        if not match:
            return 0, 0.0
        rate = float(match.group(1).replace(",", ".")) / 100
        return int(match.group(2)), rate

    def write_statistics_xlsx(self, filepath, exported_at, report):
        """Tạo báo cáo XLSX có kiểu dữ liệu và kích thước cột rõ ràng."""
        department_rows = report["department_rows"]
        column_widths = [32, 22, 27, 22, 24]

        def text_cell(ref, value, style=8):
            value = escape(str(value or ""))
            return (
                f'<c r="{ref}" t="inlineStr" s="{style}">'
                f'<is><t xml:space="preserve">{value}</t></is></c>'
            )

        def number_cell(ref, value, style=9):
            return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'

        rows_xml = [
            f'<row r="1" ht="27" customHeight="1">{text_cell("A1", "BÁO CÁO THỐNG KÊ NHÂN SỰ VÀ QUỸ LƯƠNG", 1)}</row>',
            f'<row r="2">{text_cell("A2", f"Kỳ báo cáo: {report["period"]}", 2)}</row>',
            f'<row r="3">{text_cell("A3", f"Phạm vi: {report["scope"]}", 2)}</row>',
            f'<row r="4">{text_cell("A4", f"Thời điểm xuất: {exported_at:%d/%m/%Y %H:%M}", 2)}</row>',
            '<row r="5"/>',
        ]

        kpi_labels = [
            "Nhân sự cuối tháng",
            "Nhân viên vào",
            "Nhân viên nghỉ",
            f'Thay đổi so với {report["previous_period"]}',
            "Tổng quỹ lương (đ)",
        ]
        kpi_values = [
            report["total_employees"], report["joined"], report["left"],
            report["employee_delta"], report["total_payroll"],
        ]
        kpi_headers = "".join(
            text_cell(f"{chr(65 + index)}6", label, 4)
            for index, label in enumerate(kpi_labels)
        )
        kpi_cells = "".join(
            number_cell(
                f"{chr(65 + index)}7", value, 6 if index == 4 else 5
            )
            for index, value in enumerate(kpi_values)
        )
        rows_xml.extend([
            f'<row r="6" ht="32" customHeight="1">{kpi_headers}</row>',
            f'<row r="7" ht="25" customHeight="1">{kpi_cells}</row>',
            '<row r="8"/>',
            f'<row r="9" ht="23" customHeight="1">{text_cell("A9", "Cơ cấu giới tính", 3)}</row>',
            f'<row r="10">{text_cell("A10", "Giới tính", 7)}{text_cell("B10", "Số nhân viên", 7)}{text_cell("C10", "Tỷ lệ", 7)}</row>',
        ])

        for row_number, gender in enumerate(report["gender_rows"], start=11):
            rows_xml.append(
                f'<row r="{row_number}">'
                f'{text_cell(f"A{row_number}", gender[0])}'
                f'{number_cell(f"B{row_number}", gender[1])}'
                f'{number_cell(f"C{row_number}", gender[2], 10)}'
                f'</row>'
            )

        rows_xml.extend([
            '<row r="13"/>',
            f'<row r="14" ht="32" customHeight="1">'
            f'{text_cell("A14", "Phòng ban", 7)}'
            f'{text_cell("B14", "Số NV lãnh lương", 7)}'
            f'{text_cell("C14", "Tổng lương thực nhận (đ)", 7)}'
            f'{text_cell("D14", "Lương trung bình (đ)", 7)}'
            f'</row>',
        ])

        total_count = 0
        total_salary = 0
        for row_number, department in enumerate(department_rows, start=15):
            total_count += department[1]
            total_salary += department[2]
            rows_xml.append(
                f'<row r="{row_number}">'
                f'{text_cell(f"A{row_number}", department[0])}'
                f'{number_cell(f"B{row_number}", department[1])}'
                f'{number_cell(f"C{row_number}", department[2], 11)}'
                f'{number_cell(f"D{row_number}", department[3], 11)}'
                f'</row>'
            )

        total_row = 15 + len(department_rows)
        average_salary = round(total_salary / total_count) if total_count else 0
        rows_xml.append(
            f'<row r="{total_row}" ht="23" customHeight="1">'
            f'{text_cell(f"A{total_row}", "TỔNG CỘNG", 12)}'
            f'{number_cell(f"B{total_row}", total_count, 13)}'
            f'{number_cell(f"C{total_row}", total_salary, 14)}'
            f'{number_cell(f"D{total_row}", average_salary, 14)}'
            f'</row>'
        )

        columns_xml = "".join(
            f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
            for index, width in enumerate(column_widths, start=1)
        )
        last_data_row = max(14, 14 + len(department_rows))
        worksheet_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView showGridLines="0" workbookViewId="0"><pane ySplit="14" topLeftCell="A15" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <sheetFormatPr defaultRowHeight="20"/>
  <cols>{columns_xml}</cols>
  <sheetData>{"".join(rows_xml)}</sheetData>
  <autoFilter ref="A14:D{last_data_row}"/>
  <mergeCells count="5"><mergeCell ref="A1:E1"/><mergeCell ref="A2:E2"/><mergeCell ref="A3:E3"/><mergeCell ref="A4:E4"/><mergeCell ref="A9:E9"/></mergeCells>
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
  <sheets><sheet name="Thống kê nhân sự" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
        workbook_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
        styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="5"><font><sz val="11"/><name val="Arial"/></font><font><b/><sz val="16"/><color rgb="FF1E293B"/><name val="Arial"/></font><font><i/><sz val="10"/><color rgb="FF475569"/><name val="Arial"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font><font><b/><sz val="11"/><color rgb="FF0F172A"/><name val="Arial"/></font></fonts>
  <fills count="5"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFEFF6FF"/><bgColor indexed="64"/></patternFill></fill><fill><patternFill patternType="solid"><fgColor rgb="FFDBEAFE"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="2"><border/><border><left style="thin"><color rgb="FFCBD5E1"/></left><right style="thin"><color rgb="FFCBD5E1"/></right><top style="thin"><color rgb="FFCBD5E1"/></top><bottom style="thin"><color rgb="FFCBD5E1"/></bottom></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="15">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="4" fillId="4" borderId="0" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="0" fontId="3" fillId="2" borderId="1" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="3" fontId="4" fillId="3" borderId="1" xfId="0"><alignment horizontal="center" vertical="center"/></xf>
    <xf numFmtId="3" fontId="4" fillId="3" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="0" fontId="3" fillId="2" borderId="1" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="3" fontId="0" fillId="0" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="10" fontId="0" fillId="0" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="3" fontId="0" fillId="0" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="0" fontId="4" fillId="4" borderId="1" xfId="0"><alignment vertical="center"/></xf>
    <xf numFmtId="3" fontId="4" fillId="4" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
    <xf numFmtId="3" fontId="4" fillId="4" borderId="1" xfId="0"><alignment horizontal="right" vertical="center"/></xf>
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


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Độc Lập - Thống Kê & Báo Cáo Dashboard")
    root.geometry("1100x650")

    test_frame = tk.Frame(root, bg="#f8fafc")
    test_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)

    app = StatisticsReportForm(test_frame)

    root.mainloop()
