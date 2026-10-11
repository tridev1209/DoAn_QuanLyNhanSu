import csv
import datetime
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import icon_button, icon_label
from user_error import show_database_error, show_file_error


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

        # Biến bộ lọc
        self.var_thang = tk.StringVar(value=str(datetime.datetime.now().month))
        self.var_nam = tk.StringVar(value=str(datetime.datetime.now().year))
        self.var_phong_ban_filter = tk.StringVar(value="Tất cả")

        # Biến KPI Cards
        self.var_card_tong_nv = tk.StringVar(value="0 NV")
        self.var_card_dang_lam = tk.StringVar(value="0 NV")
        self.var_card_da_nghi = tk.StringVar(value="0 NV")
        self.var_card_quy_luong = tk.StringVar(value="0 đ")

        # Biến Tỷ lệ Nam / Nữ
        self.var_ty_le_nam = tk.StringVar(value="Nam: 0% (0 NV)")
        self.var_ty_le_nu = tk.StringVar(value="Nữ: 0% (0 NV)")

        self.dict_phong_ban_filter = {"Tất cả": "ALL"}

        self.get_user_department_and_id()
        self.create_widgets()
        self.load_phong_ban_combobox()
        self.load_all_dashboard_data()

    def get_user_department_and_id(self):
        """Lấy Mã phòng ban và Mã NV thực tế của Trưởng phòng"""
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

    def create_widgets(self):
        # 1. TIÊU ĐỀ
        title_text = (
            "THỐNG KÊ & BÁO CÁO NHÂN SỰ PHÒNG BAN"
            if self.role == "TruongPhong"
            else "THỐNG KÊ & BÁO CÁO NHÂN SỰ TỔNG QUAN"
        )
        sub_title = (
            "Tổng quan tình hình nhân sự và chi phí lương"
            if self.role == "Admin"
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
            text="TỔNG NV",
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
            text="ĐANG LÀM VIỆC",
            icon="active",
            icon_color="#16a34a",
            font=("Helvetica", 9, "bold"),
            fg="#64748b",
            bg="white",
        ).pack(anchor="w")
        tk.Label(
            card2,
            textvariable=self.var_card_dang_lam,
            font=("Helvetica", 15, "bold"),
            fg="#16a34a",
            bg="white",
        ).pack(anchor="w", pady=(4, 0))

        # Card 3: Đã nghỉ việc
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
            text="ĐÃ NGHỈ VIỆC",
            icon="inactive",
            icon_color="#dc2626",
            font=("Helvetica", 9, "bold"),
            fg="#64748b",
            bg="white",
        ).pack(anchor="w")
        tk.Label(
            card3,
            textvariable=self.var_card_da_nghi,
            font=("Helvetica", 15, "bold"),
            fg="#dc2626",
            bg="white",
        ).pack(anchor="w", pady=(4, 0))

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
            text=" Nhân viên theo Phòng ban ",
            font=("Helvetica", 10, "bold"),
            bg="white",
            fg="#0f172a",
            padx=12,
            pady=10,
        )
        chart1_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.frame_dept_bars = tk.Frame(chart1_box, bg="white")
        self.frame_dept_bars.pack(fill=tk.BOTH, expand=True)

        # Khối phải: Cơ cấu Giới tính (Nam / Nữ)
        chart2_box = tk.LabelFrame(
            visual_frame,
            text=" Cơ cấu Giới tính ",
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
            "so_nv": "Số Nhân Viên",
            "tong_luong": "Tổng Lương Thực Nhận (đ)",
            "luong_tb": "Lương Trung Bình (đ)",
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
            self.tree.column(c, width=widths[c], anchor=align)

        sb = ttk.Scrollbar(table_box, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
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

        cb_thang = ttk.Combobox(
            filter_box,
            textvariable=self.var_thang,
            width=4,
            state="readonly",
            values=[str(i) for i in range(1, 13)],
        )
        cb_thang.grid(row=0, column=1, padx=2)
        cb_thang.bind(
            "<<ComboboxSelected>>", lambda e: self.load_all_dashboard_data()
        )

        tk.Label(
            filter_box, text="/", bg="#f8fafc", font=("Helvetica", 9, "bold")
        ).grid(row=0, column=2)

        entry_nam = tk.Entry(
            filter_box, textvariable=self.var_nam, width=6, font=("Helvetica", 9)
        )
        entry_nam.grid(row=0, column=3, padx=2)
        entry_nam.bind("<KeyRelease>", self.on_nam_key_release)
        entry_nam.bind("<FocusOut>", self.validate_nam_value)
        entry_nam.bind("<Return>", self.validate_nam_value)

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
            text="Xuất CSV (Excel)",
            icon="export",
            font=("Segoe UI", 9, "bold"),
            bg="#16a34a",
            fg="white",
            padx=10,
            pady=3,
            bd=0,
            cursor="hand2",
            command=self.xuat_csv_report,
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
        raw = self.var_nam.get().strip()
        current_year = datetime.datetime.now().year

        if not raw:
            self.var_nam.set(str(current_year))
        else:
            try:
                val = int(raw)
                if val < 2000:
                    self.var_nam.set("2000")
                elif val > 2100:
                    self.var_nam.set("2100")
                else:
                    self.var_nam.set(str(val))
            except ValueError:
                self.var_nam.set(str(current_year))

        self.load_all_dashboard_data()

    def reset_filters_to_now(self):
        """Khôi phục bộ lọc về thời gian hiện tại của hệ thống"""
        now = datetime.datetime.now()
        self.var_thang.set(str(now.month))
        self.var_nam.set(str(now.year))

        if self.role != "TruongPhong":
            self.var_phong_ban_filter.set("Tất cả")

        self.load_all_dashboard_data()

    def load_phong_ban_combobox(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                cursor.execute(
                    "SELECT ma_phong_ban, ten_phong_ban FROM phong_ban WHERE"
                    " ma_phong_ban = %s",
                    (self.user_ma_phong_ban,),
                )
            else:
                cursor.execute(
                    "SELECT ma_phong_ban, ten_phong_ban FROM phong_ban"
                )

            rows = cursor.fetchall()
            self.dict_phong_ban_filter = {"Tất cả": "ALL"}
            for r in rows:
                self.dict_phong_ban_filter[r["ten_phong_ban"]] = r[
                    "ma_phong_ban"
                ]

            self.cb_filter_pb["values"] = list(
                self.dict_phong_ban_filter.keys()
            )
            if self.role == "TruongPhong" and len(rows) > 0:
                self.var_phong_ban_filter.set(rows[0]["ten_phong_ban"])
                self.cb_filter_pb.config(state="disabled")
            else:
                self.var_phong_ban_filter.set("Tất cả")
        except Error as e:
            print(f"Lỗi Combobox Phòng ban: {e}")
        finally:
            conn.close()

    def load_all_dashboard_data(self):
        """Tải toàn bộ số liệu cho Dashboard"""
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)

            selected_pb_name = self.var_phong_ban_filter.get()
            selected_ma_pb = self.dict_phong_ban_filter.get(
                selected_pb_name, "ALL"
            )

            # ------------------------------------------------------------------
            # 1. TẢI DỮ LIỆU KPI CARDS
            # ------------------------------------------------------------------
            where_nv = ""
            params_nv = []

            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                where_nv = " WHERE ma_phong_ban = %s"
                params_nv.append(self.user_ma_phong_ban)
            elif selected_ma_pb != "ALL":
                where_nv = " WHERE ma_phong_ban = %s"
                params_nv.append(selected_ma_pb)

            # Đếm tổng NV
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM nhan_vien{where_nv}",
                tuple(params_nv),
            )
            tong_nv = cursor.fetchone()["total"]

            # Đếm Đang làm việc
            where_active = (
                f"{where_nv} AND trang_thai != 'Đã nghỉ việc'"
                if where_nv
                else " WHERE trang_thai != 'Đã nghỉ việc'"
            )
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM nhan_vien{where_active}",
                tuple(params_nv),
            )
            dang_lam = cursor.fetchone()["total"]

            # Đếm Đã nghỉ việc
            where_resigned = (
                f"{where_nv} AND trang_thai = 'Đã nghỉ việc'"
                if where_nv
                else " WHERE trang_thai = 'Đã nghỉ việc'"
            )
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM nhan_vien{where_resigned}",
                tuple(params_nv),
            )
            da_nghi = cursor.fetchone()["total"]

            # Tổng Quỹ lương theo Tháng/Năm
            thang_val = int(self.var_thang.get() or datetime.datetime.now().month)
            nam_val = int(self.var_nam.get() or datetime.datetime.now().year)

            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                q_luong = """
                    SELECT SUM(bl.thuc_nhan) AS tong_luong FROM bang_luong bl
                    JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE nv.ma_phong_ban = %s AND bl.thang = %s AND bl.nam = %s
                """
                cursor.execute(
                    q_luong, (self.user_ma_phong_ban, thang_val, nam_val)
                )
            elif selected_ma_pb != "ALL":
                q_luong = """
                    SELECT SUM(bl.thuc_nhan) AS tong_luong FROM bang_luong bl
                    JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE nv.ma_phong_ban = %s AND bl.thang = %s AND bl.nam = %s
                """
                cursor.execute(q_luong, (selected_ma_pb, thang_val, nam_val))
            else:
                q_luong = "SELECT SUM(thuc_nhan) AS tong_luong FROM bang_luong WHERE thang = %s AND nam = %s"
                cursor.execute(q_luong, (thang_val, nam_val))

            r_l = cursor.fetchone()
            quy_luong = r_l["tong_luong"] if r_l and r_l["tong_luong"] else 0.0

            self.var_card_tong_nv.set(f"{tong_nv} NV")
            self.var_card_dang_lam.set(f"{dang_lam} NV")
            self.var_card_da_nghi.set(f"{da_nghi} NV")
            self.var_card_quy_luong.set(
                f"{self.format_money_str(quy_luong)} đ"
            )

            # ------------------------------------------------------------------
            # 2. TẢI CƠ CẤU GIỚI TÍNH (MÀU TƯƠI SẮC NÉT)
            # ------------------------------------------------------------------
            q_gender = f"SELECT gioi_tinh, COUNT(*) as cnt FROM nhan_vien{where_active} GROUP BY gioi_tinh"
            cursor.execute(q_gender, tuple(params_nv))
            g_rows = cursor.fetchall()

            nam_cnt = 0
            nu_cnt = 0
            for g in g_rows:
                if g["gioi_tinh"] == "Nam":
                    nam_cnt = g["cnt"]
                elif g["gioi_tinh"] == "Nữ":
                    nu_cnt = g["cnt"]

            total_gender = nam_cnt + nu_cnt
            pct_nam = (
                round((nam_cnt / total_gender) * 100, 1)
                if total_gender > 0
                else 0
            )
            pct_nu = (
                round((nu_cnt / total_gender) * 100, 1)
                if total_gender > 0
                else 0
            )

            self.var_ty_le_nam.set(f"Nam: {pct_nam}% ({nam_cnt} NV)")
            self.var_ty_le_nu.set(f"Nữ: {pct_nu}% ({nu_cnt} NV)")

            # Vẽ thanh phần trăm Nam/Nữ
            pct_nam_rel = (pct_nam / 100.0) if pct_nam <= 100 else 1.0
            pct_nu_rel = (pct_nu / 100.0) if pct_nu <= 100 else 1.0

            self.bar_nam_fill.place(
                relx=0, rely=0, relwidth=pct_nam_rel, relheight=1.0
            )
            self.bar_nu_fill.place(
                relx=0, rely=0, relwidth=pct_nu_rel, relheight=1.0
            )

            # ------------------------------------------------------------------
            # 3. TẢI THANH BIỂU ĐỒ PHÒNG BAN (MÀU TƯƠI SẮC NÉT)
            # ------------------------------------------------------------------
            for widget in self.frame_dept_bars.winfo_children():
                widget.destroy()

            q_dept = """
                SELECT pb.ten_phong_ban, COUNT(nv.ma_nv) as cnt
                FROM phong_ban pb
                LEFT JOIN nhan_vien nv ON pb.ma_phong_ban = nv.ma_phong_ban AND nv.trang_thai != 'Đã nghỉ việc'
            """
            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                q_dept += " WHERE pb.ma_phong_ban = %s"
                cursor.execute(
                    q_dept + " GROUP BY pb.ma_phong_ban, pb.ten_phong_ban",
                    (self.user_ma_phong_ban,),
                )
            elif selected_ma_pb != "ALL":
                q_dept += " WHERE pb.ma_phong_ban = %s"
                cursor.execute(
                    q_dept + " GROUP BY pb.ma_phong_ban, pb.ten_phong_ban",
                    (selected_ma_pb,),
                )
            else:
                cursor.execute(
                    q_dept
                    + " GROUP BY pb.ma_phong_ban, pb.ten_phong_ban ORDER BY cnt"
                    " DESC LIMIT 4"
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

            if self.role == "TruongPhong" and self.user_ma_phong_ban:
                q_tbl += " AND pb.ma_phong_ban = %s"
                p_tbl.append(self.user_ma_phong_ban)
            elif selected_ma_pb != "ALL":
                q_tbl += " AND pb.ma_phong_ban = %s"
                p_tbl.append(selected_ma_pb)

            q_tbl += " GROUP BY pb.ma_phong_ban, pb.ten_phong_ban ORDER BY tong_luong DESC"
            cursor.execute(q_tbl, tuple(p_tbl))

            tbl_rows = cursor.fetchall()
            for r in tbl_rows:
                self.tree.insert(
                    "",
                    tk.END,
                    values=(
                        r["ten_phong_ban"],
                        f"{r['so_nv']} người",
                        self.format_money_str(r["tong_luong"]),
                        self.format_money_str(r["luong_tb"]),
                    ),
                )

        except Error as e:
            show_database_error(e, "tải báo cáo thống kê")
        finally:
            conn.close()

    def xuat_csv_report(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("File CSV (Excel)", "*.csv"),
                ("Tất cả các file", "*.*"),
            ],
            title="Xuất Báo Cáo Thống Kê Nhân Sự",
        )
        if not filepath:
            return

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "BÁO CÁO THỐNG KÊ NHÂN SỰ & QUỸ LƯƠNG PHÒNG BAN"
                ])
                writer.writerow([
                    f"Tháng {self.var_thang.get()}/{self.var_nam.get()}"
                ])
                writer.writerow([])
                writer.writerow([
                    "Tổng NV",
                    "Đang làm việc",
                    "Đã nghỉ việc",
                    "Tổng Quỹ Lương",
                ])
                writer.writerow([
                    self.var_card_tong_nv.get(),
                    self.var_card_dang_lam.get(),
                    self.var_card_da_nghi.get(),
                    self.var_card_quy_luong.get(),
                ])
                writer.writerow([])
                writer.writerow([
                    "Phòng Ban",
                    "Số NV Lãnh Lương",
                    "Tổng Lương Thực Nhận (đ)",
                    "Lương TB (đ)",
                ])

                for item in self.tree.get_children():
                    writer.writerow(self.tree.item(item, "values"))

            messagebox.showinfo(
                "Thành công", f"Đã xuất báo cáo thành công tại:\n{filepath}"
            )
        except Exception as e:
            show_file_error(e, "xuất báo cáo")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Độc Lập - Thống Kê & Báo Cáo Dashboard")
    root.geometry("1100x650")

    test_frame = tk.Frame(root, bg="#f8fafc")
    test_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)

    app = StatisticsReportForm(test_frame)

    root.mainloop()
