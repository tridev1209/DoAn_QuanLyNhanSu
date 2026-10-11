import csv
import datetime
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from db_connection import get_db_connection
from mysql.connector import Error


class PayrollManagementForm:

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

        self.dict_nhan_vien = {}  # ma_nv -> (ho_ten, luong_cb)
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

            # Ô tìm kiếm nhân viên
            self.cb_ma_nv = tk.Entry(
                self.input_frame,
                textvariable=self.var_ma_nv,
                width=34,
                font=("Helvetica", 10),
                relief="solid",
                bd=1,
            )

            self.cb_ma_nv.grid(
                row=0,
                column=1,
                columnspan=2,
                padx=5,
                pady=5,
                sticky="w"
            )

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
            self.cb_ma_nv.bind("<Return>", self.on_employee_enter)

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
                lambda e: self.on_digits_only_key_release(e, self.var_nam),
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
                text="Phụ cấp (đ):",
                bg="#f8fafc",
                font=("Helvetica", 10),
            ).grid(row=2, column=0, sticky="w", pady=5)
            entry_phu_cap = tk.Entry(
                self.input_frame,
                textvariable=self.var_phu_cap,
                width=22,
                font=("Helvetica", 10),
            )
            entry_phu_cap.grid(row=2, column=1, padx=5, pady=5, sticky="w")
            entry_phu_cap.bind(
                "<KeyRelease>",
                lambda e: self.on_money_key_release(e, self.var_phu_cap),
            )

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
                lambda e: self.on_money_key_release(e, self.var_khoan_tru),
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
            tk.Button(
                btn_sub_frame,
                text="💾 Lưu / Cập nhật",
                font=("Helvetica", 10, "bold"),
                bg="#2563eb",
                fg="white",
                padx=12,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.luu_bang_luong,
            ).pack(side=tk.LEFT, padx=3)

            # 2. Nút Xóa
            tk.Button(
                btn_sub_frame,
                text="🗑️ Xóa",
                font=("Helvetica", 10, "bold"),
                bg="#ef4444",
                fg="white",
                padx=10,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.xoa_bang_luong,
            ).pack(side=tk.LEFT, padx=3)

            # 3. Nút Làm mới
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

        tk.Button(
            btn_sub_frame,
            text="📊 Xuất Bảng Lương (CSV)",
            font=("Helvetica", 10, "bold"),
            bg="#10b981",
            fg="white",
            padx=10,
            pady=5,
            bd=0,
            cursor="hand2",
            command=self.xuat_csv,
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

            tk.Button(
                search_sub_frame,
                text="🔍 Xem",
                font=("Helvetica", 10, "bold"),
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
                command=self.context_edit_luong,
            )
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Xóa dữ liệu bảng lương này",
                command=self.context_delete_luong,
            )
            self.tree.bind("<Button-3>", self.show_context_menu)

        headers = {
            "ma_nv": "Mã NV",
            "ten_nv": "Họ và Tên",
            "thang_nam": "Tháng/Năm",
            "luong_cb": "Lương CB (đ)",
            "ngay_cong": "Ngày công",
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
            "luong_ot": 110,
            "phu_cap": 110,
            "khoan_tru": 110,
            "thuc_nhan": 130,
        }

        for col in self.columns_def:
            col_anchor = (
                tk.CENTER
                if col in ("ma_nv", "thang_nam", "ngay_cong")
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
            self.var_ten_nv.set("")
            self.var_luong_cb.set("0")
            return

        # Tìm theo mã NV hoặc họ tên
        filtered = [
            item
            for item in self.all_employee_display_list
            if text in item.lower()
        ]

        # Không tìm thấy
        if not filtered:
            self.hide_employee_popup()
            return

        # Không cho popup quá dài
        filtered = filtered[:12]

        self.show_employee_popup(filtered)
    
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

            self.employee_popup_tree.heading(
                "ma_nv",
                text="Mã NV"
            )

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
        for display in values:

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
                values=(ma_nv, ho_ten)
            )
         # Vị trí Entry trên màn hình
        x = self.cb_ma_nv.winfo_rootx()
        y = (
            self.cb_ma_nv.winfo_rooty()
            + self.cb_ma_nv.winfo_height()
        )

        width = self.cb_ma_nv.winfo_width()

        # Popup rộng hơn Entry một chút
        popup_width = max(width, 330)

        self.employee_popup.geometry(
            f"{popup_width}x205+{x}+{y}"
        )

        self.employee_popup.deiconify()
        self.employee_popup.lift()

        # KHÔNG tự chọn dòng đầu tiên
        self.employee_popup_tree.selection_remove(
            self.employee_popup_tree.selection()
        )
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

        # Đóng popup
        self.hide_employee_popup()

        # Đưa con trỏ về cuối
        self.cb_ma_nv.focus_set()
        self.cb_ma_nv.icursor(tk.END)

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
        Nhấn Enter để chọn nhân viên đang được highlight.
        """

        if not self.employee_popup_tree:
            return "break"

        if (
            self.employee_popup is None
            or not self.employee_popup.winfo_viewable()
        ):
            return "break"

        selected = self.employee_popup_tree.selection()

        if not selected:
            return "break"

        self.on_employee_popup_click()

        return "break"
    def on_employee_escape(self, event=None):
        """
        Nhấn Esc để đóng danh sách tìm kiếm.
        """

        self.hide_employee_popup()

        return "break"
    def on_hours_key_release(self, event, var):
        """Cho phép nhập số giờ OT (số nguyên hoặc số thập phân như 10 hay 12.5)"""
        raw = str(var.get())
        cleaned = re.sub(r"[^0-9.]", "", raw)
        if cleaned.count(".") > 1:
            parts = cleaned.split(".")
            cleaned = parts + "." + "".join(parts[1:])
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

    def on_search_focus_in(self, event):
        if self.entry_tim_kiem.get() == self.placeholder_text:
            self.entry_tim_kiem.delete(0, tk.END)
            self.entry_tim_kiem.config(fg="black")

    def on_search_focus_out(self, event):
        if not self.entry_tim_kiem.get().strip():
            self.entry_tim_kiem.insert(0, self.placeholder_text)
            self.entry_tim_kiem.config(fg="grey")

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
                        ma_nv,
                        ho_ten,
                        luong_co_ban
                    FROM nhan_vien
                    WHERE ma_phong_ban = %s
                    AND (ma_nv != %s OR %s IS NULL)
                    AND (
                        nguoi_dung_id != %s
                        OR %s IS NULL
                        OR nguoi_dung_id IS NULL
                    )
                    AND trang_thai <> 'Đã nghỉ việc'
                    ORDER BY ma_nv ASC
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
                        ma_nv,
                        ho_ten,
                        luong_co_ban
                    FROM nhan_vien
                    WHERE trang_thai <> 'Đã nghỉ việc'
                    ORDER BY ma_nv ASC
                """

                cursor.execute(query)

            rows = cursor.fetchall()

            # Lưu dữ liệu nhân viên
            self.dict_nhan_vien = {
                row["ma_nv"]: (
                    row["ho_ten"],
                    float(row["luong_co_ban"] or 0)
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

        except Error as e:

            messagebox.showerror(
                "Lỗi CSDL",
                f"Không thể tải danh sách nhân viên:\n{e}"
            )

        finally:
            conn.close()

    def on_employee_selected(self, event=None):
        ma = self.get_selected_ma_nv()
        if ma in self.dict_nhan_vien:
            ten, luong_cb = self.dict_nhan_vien[ma]
            self.var_ten_nv.set(ten)
            self.var_luong_cb.set(self.format_money_str(luong_cb))
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

            # Tính lương 1 giờ công tiêu chuẩn (1 tháng 24 ngày, 8 giờ/ngày = 192 giờ)
            luong_1_gio = (luong_cb / 24.0) / 8.0 if luong_cb > 0 else 0.0

            # Tiền Lương OT với hệ số làm thêm 1.5
            tien_luong_ot = gio_ot * luong_1_gio * 1.5

            # Lương chính theo ngày công thực tế
            luong_chinh = (luong_cb / 24.0) * ngay_cong

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

        thuc_nhan_val, tien_luong_ot_val = self.tinh_luong()

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO bang_luong (ma_nv, thang, nam, luong_cb, ngay_cong, luong_ot, phu_cap, khoan_tru)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    luong_cb = VALUES(luong_cb),
                    ngay_cong = VALUES(ngay_cong),
                    luong_ot = VALUES(luong_ot),
                    phu_cap = VALUES(phu_cap),
                    khoan_tru = VALUES(khoan_tru)
            """
            cursor.execute(
                query,
                (
                    ma_nv,
                    thang,
                    nam,
                    self.parse_money(self.var_luong_cb.get()),
                    int(self.parse_money(self.var_ngay_cong.get())),
                    tien_luong_ot_val,  # Lưu tiền Lương OT tự động tính xuống CSDL
                    self.parse_money(self.var_phu_cap.get()),
                    self.parse_money(self.var_khoan_tru.get()),
                ),
            )
            conn.commit()
            messagebox.showinfo(
                "Thành công",
                f"Đã lưu bảng lương tháng {thang}/{nam} cho nhân viên"
                f" {self.var_ten_nv.get()} ({ma_nv})!",
            )
            self.load_data()
        except Error as e:
            messagebox.showerror("Lỗi CSDL", f"{e}")
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
                messagebox.showerror("Lỗi CSDL", f"{e}")
            finally:
                conn.close()

    def xuat_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("File CSV (Excel)", "*.csv"),
                ("Tất cả các file", "*.*"),
            ],
            title="Xuất bảng lương ra file CSV",
        )
        if not filepath:
            return

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Mã NV",
                    "Họ và Tên",
                    "Tháng/Năm",
                    "Lương CB (đ)",
                    "Ngày công",
                    "Lương OT (đ)",
                    "Phụ cấp (đ)",
                    "Khoản trừ (đ)",
                    "Thực nhận (đ)",
                ])
                for item in self.tree.get_children():
                    writer.writerow(self.tree.item(item, "values"))
            messagebox.showinfo(
                "Thành công", f"Đã xuất file thành công tại:\n{filepath}"
            )
        except Exception as e:
            messagebox.showerror("Lỗi xuất file", str(e))

    def load_data(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)

            if self.role == "NhanVien":
                query = """
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb, 
                           bl.ngay_cong, bl.luong_ot, bl.phu_cap, bl.khoan_tru, bl.thuc_nhan
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
                           bl.ngay_cong, bl.luong_ot, bl.phu_cap, bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE nv.ma_phong_ban = %s AND trang_thai <> 'Đã nghỉ việc'
                    ORDER BY bl.nam DESC, bl.thang DESC, bl.ma_nv ASC
                """
                cursor.execute(query, (self.user_ma_phong_ban,))

            else:
                query = """
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb, 
                           bl.ngay_cong, bl.luong_ot, bl.phu_cap, bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    ORDER BY bl.nam DESC, bl.thang DESC, bl.ma_nv ASC
                """
                cursor.execute(query)

            self.refresh_table(cursor.fetchall())
        except Error as e:
            messagebox.showerror("Lỗi CSDL", str(e))
        finally:
            conn.close()

    def refresh_table(self, data_list):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in data_list:
            thang_nam = f"{row['thang']:02d}/{row['nam']}"
            luong_cb = self.format_money_str(row["luong_cb"])
            luong_ot = self.format_money_str(row["luong_ot"])
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
                           bl.ngay_cong, bl.luong_ot, bl.phu_cap, bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE nv.ma_phong_ban = %s AND (bl.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR CONCAT(bl.thang, '/', bl.nam) LIKE %s) 
                """
                cursor.execute(query, (self.user_ma_phong_ban, p, p, p))
            else:
                query = """
                    SELECT bl.ma_nv, nv.ho_ten, bl.thang, bl.nam, bl.luong_cb, 
                           bl.ngay_cong, bl.luong_ot, bl.phu_cap, bl.khoan_tru, bl.thuc_nhan
                    FROM bang_luong bl
                    LEFT JOIN nhan_vien nv ON bl.ma_nv = nv.ma_nv
                    WHERE bl.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR CONCAT(bl.thang, '/', bl.nam) LIKE %s
                """
                cursor.execute(query, (p, p, p))

            self.refresh_table(cursor.fetchall())
        except Error as e:
            messagebox.showerror("Lỗi", str(e))
        finally:
            conn.close()

    def lam_moi(self):
        if self.role != "NhanVien":
            if self.all_employee_display_list:
                first_item = self.all_employee_display_list[0]
                self.cb_ma_nv.set(first_item)
                self.on_employee_selected(None)
            else:
                self.cb_ma_nv.set("")
                self.var_ten_nv.set("")

        self.var_thang.set(str(datetime.datetime.now().month))
        self.var_nam.set(str(datetime.datetime.now().year))
        self.var_ngay_cong.set("24")
        self.var_gio_ot.set("0")
        self.var_phu_cap.set("0")
        self.var_khoan_tru.set("0")
        if self.role != "NhanVien":
            self.tinh_luong()
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

        # Quy đổi từ Tiền Lương OT trên bảng ngược lại ra Số giờ OT để nạp lên ô nhập
        luong_ot_val = self.parse_money(row_data["luong_ot"])
        luong_1_gio = (luong_cb_val / 24.0) / 8.0 if luong_cb_val > 0 else 0.0
        gio_ot_calc = (
            round(luong_ot_val / (luong_1_gio * 1.5), 1)
            if luong_1_gio > 0
            else 0.0
        )
        gio_ot_str = (
            str(int(gio_ot_calc))
            if gio_ot_calc.is_integer()
            else str(gio_ot_calc)
        )
        self.var_gio_ot.set(gio_ot_str)

        self.var_phu_cap.set(
            self.format_money_str(self.parse_money(row_data["phu_cap"]))
        )
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