import calendar
import datetime
import re
import tkinter as tk
from tkinter import messagebox, ttk
from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import get_icon, icon_button


ROLE_ADMIN = "Admin"
ROLE_MANAGER = "TruongPhong"
ROLE_EMPLOYEE = "NhanVien"

STATUS_WORKING = "Đang làm việc"
STATUS_PROBATION = "Thử việc"
STATUS_RESIGNED = "Đã nghỉ việc"
ACTIVE_EMPLOYEE_STATUSES = {STATUS_WORKING, STATUS_PROBATION}


class EmployeeManagementForm:

    def __init__(self, parent_frame, user_info=None):
        self.parent = parent_frame

        # Mặc định quyền thấp nhất nếu thiếu thông tin đăng nhập.
        self.user_info = user_info or {
            "id": None,
            "ten_dang_nhap": "",
            "vai_tro": ROLE_EMPLOYEE,
            "ho_ten": "",
        }
        self.role = self.user_info.get("vai_tro", ROLE_EMPLOYEE)
        self.user_login_name = self.user_info.get("ten_dang_nhap", "")
        self.user_db_id = self.user_info.get("id", None)

        # Thông tin phòng ban & Mã NV thực tế của Trưởng phòng
        self.user_ma_phong_ban = None
        self.user_actual_ma_nv = None
        self.selected_ma_nv = None
        self.generated_ma_nv = None

        # Biến quản lý giao diện
        self.var_ma_nv = tk.StringVar()
        self.var_ten_nv = tk.StringVar()
        self.var_gioi_tinh = tk.StringVar(value="Nam")
        self.var_ngay_sinh = tk.StringVar(value="01/01/1995")
        self.var_ngay_vao_lam = tk.StringVar(
            value=datetime.date.today().strftime("%d/%m/%Y")
        )
        self.var_ngay_nghi_viec = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_sdt = tk.StringVar()
        self.var_phong_ban = tk.StringVar()
        self.var_chuc_vu = tk.StringVar()
        self.var_luong_cb = tk.StringVar(value="12.000.000")
        self.var_trang_thai = tk.StringVar(value=STATUS_WORKING)
        self.var_tim_kiem = tk.StringVar()

        self.dict_phong_ban = {}
        self.dict_tien_to = {}
        self.dict_chuc_vu = {}

        self.get_user_department_and_id()
        self.create_widgets()
        self.load_combobox_data()
        self.load_data()

    def get_user_department_and_id(self):
        """Lấy mã nhân viên/phòng ban, ưu tiên liên kết tài khoản bằng ID."""
        conn = get_db_connection()
        if not conn:
            return
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            if self.user_db_id is not None:
                cursor.execute(
                    """
                    SELECT ma_nv, ma_phong_ban
                    FROM nhan_vien
                    WHERE nguoi_dung_id = %s
                    LIMIT 1
                    """,
                    (self.user_db_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT ma_nv, ma_phong_ban
                    FROM nhan_vien
                    WHERE ma_nv = %s
                    LIMIT 1
                    """,
                    (self.user_login_name,),
                )
            row = cursor.fetchone()
            if not row and self.user_login_name:
                cursor.execute(
                    """
                    SELECT ma_nv, ma_phong_ban
                    FROM nhan_vien
                    WHERE ma_nv = %s
                    LIMIT 1
                    """,
                    (self.user_login_name,),
                )
                row = cursor.fetchone()
            if row:
                self.user_ma_phong_ban = row["ma_phong_ban"]
                self.user_actual_ma_nv = row["ma_nv"]
        except Error as e:
            print(f"Lỗi lấy thông tin Trưởng phòng: {e}")
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def can_manage_employees(self):
        return self.role in (ROLE_ADMIN, ROLE_MANAGER)

    def ensure_manage_permission(self):
        if self.can_manage_employees():
            return True
        messagebox.showwarning(
            "Không có quyền",
            "Tài khoản hiện tại không có quyền quản lý nhân viên.",
        )
        return False

    def ensure_manager_department(self):
        if self.role != ROLE_MANAGER:
            return True
        if self.user_ma_phong_ban:
            return True
        messagebox.showerror(
            "Lỗi phân quyền",
            "Không xác định được phòng ban của Trưởng phòng. "
            "Dữ liệu nhân viên đã được khóa để tránh truy cập sai phạm vi.",
        )
        return False

    def is_manager_position(self, position_name):
        return position_name.strip().casefold() == "trưởng phòng".casefold()

    def account_status_from_employee_status(self, employee_status):
        return 1 if employee_status in ACTIVE_EMPLOYEE_STATUSES else 0

    def get_employee_for_update(self, cursor, ma_nv):
        """Khóa bản ghi và xác nhận người dùng được thao tác nhân viên này."""
        cursor.execute(
            """
            SELECT nv.ma_nv, nv.ma_phong_ban, nv.nguoi_dung_id,
                   nv.trang_thai, nd.vai_tro
            FROM nhan_vien nv
            LEFT JOIN nguoi_dung nd ON nd.id = nv.nguoi_dung_id
            WHERE nv.ma_nv = %s
            FOR UPDATE
            """,
            (ma_nv,),
        )
        employee = cursor.fetchone()
        if not employee:
            return None, "Không tìm thấy nhân viên cần thao tác."

        ma_phong_ban = employee[1]
        if self.role == ROLE_MANAGER:
            if not self.user_ma_phong_ban:
                return None, "Không xác định được phòng ban của Trưởng phòng."
            if ma_phong_ban != self.user_ma_phong_ban:
                return None, "Trưởng phòng chỉ được thao tác nhân viên thuộc phòng mình."
            if employee[4] == ROLE_MANAGER:
                return None, "Trưởng phòng không được thao tác hồ sơ Trưởng phòng khác."

        return employee, None

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

    @staticmethod
    def date_years_ago(source_date, years):
        try:
            return source_date.replace(year=source_date.year - years)
        except ValueError:
            # Xử lý ngày 29/02 khi năm đích không phải năm nhuận.
            return source_date.replace(year=source_date.year - years, day=28)

    def open_date_picker(
        self,
        target_var,
        target_entry,
        title,
        min_date,
        max_date,
        popup_attribute,
    ):
        """Mở lịch dùng chung cho ngày sinh, ngày vào làm và ngày nghỉ việc."""
        if min_date > max_date:
            min_date = max_date
        current_popup = getattr(self, popup_attribute, None)
        if current_popup and current_popup.winfo_exists():
            current_popup.lift()
            current_popup.focus_force()
            return

        try:
            selected_date = datetime.datetime.strptime(
                target_var.get().strip(), "%d/%m/%Y"
            ).date()
        except ValueError:
            selected_date = max_date

        if selected_date < min_date:
            selected_date = min_date
        elif selected_date > max_date:
            selected_date = max_date

        popup = tk.Toplevel(self.parent)
        setattr(self, popup_attribute, popup)
        popup.title(title)
        popup.configure(bg="white")
        popup.resizable(False, False)
        popup.transient(self.parent.winfo_toplevel())

        month_names = [f"Tháng {month}" for month in range(1, 13)]
        month_var = tk.StringVar(value=month_names[selected_date.month - 1])
        year_var = tk.IntVar(value=selected_date.year)

        header = tk.Frame(popup, bg="#f1f5f9", padx=8, pady=8)
        header.pack(fill=tk.X)
        calendar_frame = tk.Frame(popup, bg="white", padx=8, pady=6)
        calendar_frame.pack(fill=tk.BOTH, expand=True)

        def close_popup(event=None):
            if popup.winfo_exists():
                popup.grab_release()
                popup.destroy()
            setattr(self, popup_attribute, None)

        def choose_date(chosen_date):
            target_var.set(chosen_date.strftime("%d/%m/%Y"))
            target_entry.icursor(tk.END)
            close_popup()
            target_entry.focus_set()

        def render_calendar(event=None):
            for child in calendar_frame.winfo_children():
                child.destroy()

            month = month_names.index(month_var.get()) + 1
            year = int(year_var.get())
            weekdays = ("T2", "T3", "T4", "T5", "T6", "T7", "CN")
            for column, weekday in enumerate(weekdays):
                tk.Label(
                    calendar_frame,
                    text=weekday,
                    bg="white",
                    fg="#475569",
                    font=("Helvetica", 9, "bold"),
                    width=4,
                ).grid(row=0, column=column, padx=1, pady=(0, 3))

            weeks = calendar.Calendar(firstweekday=calendar.MONDAY).monthdayscalendar(
                year, month
            )
            for row_index, week in enumerate(weeks, start=1):
                for column, day in enumerate(week):
                    if day == 0:
                        tk.Label(calendar_frame, text="", bg="white", width=4).grid(
                            row=row_index, column=column, padx=1, pady=1
                        )
                        continue

                    date_value = datetime.date(year, month, day)
                    is_allowed = min_date <= date_value <= max_date
                    is_selected = date_value == selected_date
                    tk.Button(
                        calendar_frame,
                        text=str(day),
                        width=3,
                        bd=0,
                        relief=tk.FLAT,
                        font=("Helvetica", 9),
                        bg="#0ea5e9" if is_selected else "white",
                        fg="white" if is_selected else "#0f172a",
                        activebackground="#bae6fd",
                        disabledforeground="#cbd5e1",
                        state=tk.NORMAL if is_allowed else tk.DISABLED,
                        cursor="hand2" if is_allowed else "arrow",
                        command=lambda value=date_value: choose_date(value),
                    ).grid(row=row_index, column=column, padx=1, pady=1)

        def change_month(offset):
            month = month_names.index(month_var.get()) + 1 + offset
            year = int(year_var.get())
            if month < 1:
                month = 12
                year -= 1
            elif month > 12:
                month = 1
                year += 1

            if min_date.year <= year <= max_date.year:
                month_var.set(month_names[month - 1])
                year_var.set(year)
                render_calendar()

        tk.Button(
            header,
            text="‹",
            font=("Helvetica", 12, "bold"),
            width=2,
            bd=0,
            bg="#e2e8f0",
            command=lambda: change_month(-1),
        ).pack(side=tk.LEFT)
        month_combo = ttk.Combobox(
            header,
            textvariable=month_var,
            values=month_names,
            width=8,
            state="readonly",
            font=("Helvetica", 9),
        )
        month_combo.pack(side=tk.LEFT, padx=(6, 3))
        year_combo = ttk.Combobox(
            header,
            textvariable=year_var,
            values=list(range(max_date.year, min_date.year - 1, -1)),
            width=6,
            state="readonly",
            font=("Helvetica", 9),
        )
        year_combo.pack(side=tk.LEFT, padx=(3, 6))
        tk.Button(
            header,
            text="›",
            font=("Helvetica", 12, "bold"),
            width=2,
            bd=0,
            bg="#e2e8f0",
            command=lambda: change_month(1),
        ).pack(side=tk.LEFT)

        month_combo.bind("<<ComboboxSelected>>", render_calendar)
        year_combo.bind("<<ComboboxSelected>>", render_calendar)
        popup.protocol("WM_DELETE_WINDOW", close_popup)
        popup.bind("<Escape>", close_popup)

        render_calendar()
        popup.update_idletasks()
        popup_x = target_entry.winfo_rootx()
        popup_y = (
            target_entry.winfo_rooty()
            + target_entry.winfo_height()
            + 3
        )
        popup_width = popup.winfo_reqwidth()
        popup_height = popup.winfo_reqheight()
        popup_x = min(popup_x, popup.winfo_screenwidth() - popup_width - 10)
        popup_y = min(popup_y, popup.winfo_screenheight() - popup_height - 40)
        popup.geometry(f"+{max(0, popup_x)}+{max(0, popup_y)}")
        popup.grab_set()
        popup.focus_force()

    def open_birth_date_picker(self):
        today = datetime.date.today()
        self.open_date_picker(
            self.var_ngay_sinh,
            self.entry_ngay_sinh,
            "Chọn ngày sinh",
            self.date_years_ago(today, 65),
            self.date_years_ago(today, 18),
            "birth_date_popup",
        )

    def open_start_date_picker(self):
        today = datetime.date.today()
        try:
            birth_date = datetime.datetime.strptime(
                self.var_ngay_sinh.get().strip(), "%d/%m/%Y"
            ).date()
            min_date = self.date_years_ago(birth_date, -18)
        except ValueError:
            min_date = datetime.date(1950, 1, 1)
        self.open_date_picker(
            self.var_ngay_vao_lam,
            self.entry_ngay_vao_lam,
            "Chọn ngày vào làm",
            min_date,
            today,
            "start_date_popup",
        )

    def open_end_date_picker(self):
        today = datetime.date.today()
        try:
            min_date = datetime.datetime.strptime(
                self.var_ngay_vao_lam.get().strip(), "%d/%m/%Y"
            ).date()
        except ValueError:
            min_date = datetime.date(1950, 1, 1)
        self.open_date_picker(
            self.var_ngay_nghi_viec,
            self.entry_ngay_nghi_viec,
            "Chọn ngày nghỉ việc",
            min_date,
            today,
            "end_date_popup",
        )

    def on_employee_status_changed(self, event=None):
        """Giữ ngày nghỉ việc đồng bộ với trạng thái trên biểu mẫu."""
        if self.var_trang_thai.get() == STATUS_RESIGNED:
            if not self.var_ngay_nghi_viec.get().strip():
                self.var_ngay_nghi_viec.set(
                    datetime.date.today().strftime("%d/%m/%Y")
                )
        else:
            self.var_ngay_nghi_viec.set("")

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

        date_input_frame = tk.Frame(input_frame, bg="#f8fafc")
        date_input_frame.grid(row=1, column=5, padx=5, pady=5, sticky="w")

        self.entry_ngay_sinh = tk.Entry(
            date_input_frame,
            textvariable=self.var_ngay_sinh,
            width=16,
            font=("Helvetica", 10),
        )
        self.entry_ngay_sinh.pack(side=tk.LEFT)
        self.entry_ngay_sinh.bind(
            "<KeyRelease>",
            lambda e: self.on_date_key_release(e, self.var_ngay_sinh),
        )
        icon_button(
            date_input_frame,
            text="",
            icon="calendar",
            icon_color="#0f172a",
            bg="#e2e8f0",
            activebackground="#cbd5e1",
            padx=5,
            pady=1,
            bd=0,
            cursor="hand2",
            command=self.open_birth_date_picker,
        ).pack(side=tk.LEFT, padx=(3, 0))

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
        self.cb_trang_thai = ttk.Combobox(
            input_frame,
            textvariable=self.var_trang_thai,
            values=[STATUS_WORKING, STATUS_PROBATION, STATUS_RESIGNED],
            width=18,
            state="readonly",
            font=("Helvetica", 10),
        )
        self.cb_trang_thai.grid(
            row=3, column=1, padx=5, pady=5, sticky="w"
        )
        self.cb_trang_thai.bind(
            "<<ComboboxSelected>>", self.on_employee_status_changed
        )

        tk.Label(
            input_frame,
            text="Ngày vào làm (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=3, column=2, sticky="w", pady=5, padx=(15, 0))
        start_date_frame = tk.Frame(input_frame, bg="#f8fafc")
        start_date_frame.grid(row=3, column=3, padx=5, pady=5, sticky="w")
        self.entry_ngay_vao_lam = tk.Entry(
            start_date_frame,
            textvariable=self.var_ngay_vao_lam,
            width=13,
            font=("Helvetica", 10),
        )
        self.entry_ngay_vao_lam.pack(side=tk.LEFT)
        self.entry_ngay_vao_lam.bind(
            "<KeyRelease>",
            lambda e: self.on_date_key_release(e, self.var_ngay_vao_lam),
        )
        icon_button(
            start_date_frame,
            text="",
            icon="calendar",
            icon_color="#0f172a",
            bg="#e2e8f0",
            activebackground="#cbd5e1",
            padx=5,
            pady=1,
            bd=0,
            cursor="hand2",
            command=self.open_start_date_picker,
        ).pack(side=tk.LEFT, padx=(3, 0))

        tk.Label(
            input_frame,
            text="Ngày nghỉ việc:",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=3, column=4, sticky="w", pady=5, padx=(15, 0))
        end_date_frame = tk.Frame(input_frame, bg="#f8fafc")
        end_date_frame.grid(row=3, column=5, padx=5, pady=5, sticky="w")
        self.entry_ngay_nghi_viec = tk.Entry(
            end_date_frame,
            textvariable=self.var_ngay_nghi_viec,
            width=13,
            font=("Helvetica", 10),
        )
        self.entry_ngay_nghi_viec.pack(side=tk.LEFT)
        self.entry_ngay_nghi_viec.bind(
            "<KeyRelease>",
            lambda e: self.on_date_key_release(e, self.var_ngay_nghi_viec),
        )
        icon_button(
            end_date_frame,
            text="",
            icon="calendar",
            icon_color="#0f172a",
            bg="#e2e8f0",
            activebackground="#cbd5e1",
            padx=5,
            pady=1,
            bd=0,
            cursor="hand2",
            command=self.open_end_date_picker,
        ).pack(side=tk.LEFT, padx=(3, 0))

        # --- THANH CÔNG CỤ ---
        action_frame = tk.Frame(self.parent, bg="#f8fafc")
        action_frame.pack(fill=tk.X, pady=6)

        btn_sub_frame = tk.Frame(action_frame, bg="#f8fafc")
        btn_sub_frame.pack(side=tk.LEFT)

        if self.can_manage_employees():
            icon_button(
                btn_sub_frame,
                text="Thêm",
                icon="add",
                bg="#2563eb",
                fg="white",
                padx=10,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.them_nhan_vien,
            ).pack(side=tk.LEFT, padx=3)
            icon_button(
                btn_sub_frame,
                text="Sửa",
                icon="edit",
                bg="#eab308",
                fg="white",
                padx=10,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.sua_nhan_vien,
            ).pack(side=tk.LEFT, padx=3)
            icon_button(
                btn_sub_frame,
                text="Cho nghỉ việc",
                icon="resign",
                bg="#f97316",
                fg="white",
                padx=10,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.cho_nghi_viec,
            ).pack(side=tk.LEFT, padx=3)

        if self.role == ROLE_ADMIN:
            icon_button(
                btn_sub_frame,
                text="Xóa vĩnh viễn",
                icon="delete",
                bg="#dc2626",
                fg="white",
                padx=10,
                pady=5,
                bd=0,
                cursor="hand2",
                command=self.xoa_vinh_vien,
            ).pack(side=tk.LEFT, padx=3)
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
            fg="black",
        )
        self.entry_tim_kiem.pack(side=tk.LEFT, padx=4)

        # Hiển thị placeholder như một lớp phủ, không đưa vào giá trị thật của Entry.
        # Nhờ vậy người dùng không thể bôi chọn hoặc vô tình tìm kiếm placeholder.
        self.placeholder_label = tk.Label(
            self.entry_tim_kiem,
            text=self.placeholder_text,
            bg="white",
            fg="#94a3b8",
            font=("Helvetica", 10),
            bd=0,
            padx=0,
            pady=0,
            cursor="xterm",
        )
        self.placeholder_label.place(x=4, rely=0.5, anchor="w")
        self.placeholder_label.bind("<Button-1>", self.focus_search_entry)
        self.entry_tim_kiem.bind("<FocusIn>", self.on_search_focus_in)
        self.entry_tim_kiem.bind("<FocusOut>", self.on_search_focus_out)
        self.entry_tim_kiem.bind("<KeyPress>", self.on_search_key_press)
        self.entry_tim_kiem.bind("<Return>", self.on_search_enter)
        self.var_tim_kiem.trace_add("write", self.update_search_placeholder)

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
        self.btn_tat_ca = tk.Button(
            search_sub_frame,
            text="Tất cả",
            font=("Helvetica", 10),
            bg="#64748b",
            fg="white",
            padx=8,
            pady=4,
            bd=0,
            command=self.show_all_employees,
        )
        self.btn_tat_ca.pack(side=tk.LEFT, padx=2)

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
            "ngay_vao_lam",
            "ngay_nghi_viec",
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

        if self.can_manage_employees():
            self.context_menu.add_command(
                label="Chỉnh sửa nhân viên này",
                image=get_icon(self.parent, "edit", "#475569"),
                compound=tk.LEFT,
                command=self.context_edit_nhan_vien,
            )
            self.context_menu.add_separator()
            self.context_menu.add_command(
                label="Cho nghỉ việc",
                image=get_icon(self.parent, "resign", "#f97316"),
                compound=tk.LEFT,
                command=self.context_resign_nhan_vien,
            )

        if self.role == ROLE_ADMIN:
            self.context_menu.add_command(
                label="Xóa vĩnh viễn",
                image=get_icon(self.parent, "delete", "#dc2626"),
                compound=tk.LEFT,
                command=self.context_delete_nhan_vien,
            )

        headers = {
            "ma_nv": "Mã NV",
            "ten_nv": "Họ và Tên",
            "gioi_tinh": "Giới tính",
            "ngay_sinh": "Ngày sinh",
            "ngay_vao_lam": "Ngày vào làm",
            "ngay_nghi_viec": "Ngày nghỉ việc",
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
            "ngay_vao_lam": 95,
            "ngay_nghi_viec": 100,
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
        scrollbar_x = ttk.Scrollbar(
            table_frame, orient=tk.HORIZONTAL, command=self.tree.xview
        )
        self.tree.configure(
            yscroll=scrollbar.set,
            xscroll=scrollbar_x.set,
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def focus_search_entry(self, event=None):
        self.entry_tim_kiem.focus_set()
        self.placeholder_label.place_forget()

    def update_search_placeholder(self, *args):
        if self.var_tim_kiem.get() or self.entry_tim_kiem.focus_get() == self.entry_tim_kiem:
            self.placeholder_label.place_forget()
        else:
            self.placeholder_label.place(x=4, rely=0.5, anchor="w")

    def on_search_focus_in(self, event):
        self.placeholder_label.place_forget()

    def on_search_key_press(self, event):
        # Ẩn ngay từ lúc nhấn phím, không phụ thuộc thứ tự xử lý của StringVar.
        self.placeholder_label.place_forget()

    def on_search_focus_out(self, event):
        self.update_search_placeholder()

    def on_search_enter(self, event=None):
        self.tim_kiem()
        return "break"

    def show_all_employees(self):
        self.var_tim_kiem.set("")
        self.btn_tat_ca.focus_set()
        self.load_data(reset_search=False)
        # Chạy sau khi Tkinter xử lý xong sự kiện click và chuyển focus.
        self.parent.after_idle(self.update_search_placeholder)

    # --- TỰ ĐỘNG CHỌN & CHỈ LỌC DUY NHẤT 1 PHÒNG BAN CHO TRƯỜNG PHÒNG ---
    def load_combobox_data(self):
        conn = get_db_connection()
        if not conn:
            return
        cursor = None
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
            if self.role == ROLE_MANAGER and self.user_ma_phong_ban:
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
            elif self.role == ROLE_ADMIN:
                self.cb_pb["values"] = list(self.dict_phong_ban.keys())
                self.cb_pb.config(state="readonly")
                if self.dict_phong_ban:
                    self.cb_pb.current(0)
                    self.generate_employee_id()
            else:
                # Không tải danh sách phòng ban khi tài khoản không có quyền
                # hoặc Trưởng phòng chưa được gắn đúng phòng ban.
                self.cb_pb["values"] = []
                self.var_phong_ban.set("")
                self.cb_pb.config(state="disabled")

            # --- PHÂN QUYỀN CHỨC VỤ ---
            if self.dict_chuc_vu:

                all_chuc_vu = list(self.dict_chuc_vu.keys())

                if self.role == ROLE_MANAGER and self.user_ma_phong_ban:
                    # Trưởng phòng không được chọn chức vụ "Trưởng phòng"
                    allowed_chuc_vu = [
                        cv for cv in all_chuc_vu
                        if not self.is_manager_position(cv)
                    ]
                elif self.role == ROLE_ADMIN:
                    allowed_chuc_vu = all_chuc_vu
                else:
                    allowed_chuc_vu = []

                self.cb_cv["values"] = allowed_chuc_vu

                if allowed_chuc_vu:
                    self.cb_cv.config(state="readonly")
                    self.cb_cv.current(0)
                else:
                    self.var_chuc_vu.set("")
                    self.cb_cv.config(state="disabled")
        except Error as e:
            print(f"Lỗi Combobox: {e}")
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def on_phong_ban_changed(self, event):
        if not self.selected_ma_nv:
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
        cursor = None
        try:
            cursor = conn.cursor()
            new_ma_nv = self.calculate_next_employee_id(
                cursor, ma_phong, prefix
            )
            self.generated_ma_nv = new_ma_nv
            self.var_ma_nv.set(new_ma_nv)
        except Error as e:
            print(f"Lỗi sinh mã NV: {e}")
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def calculate_next_employee_id(
        self, cursor, ma_phong_ban, prefix, lock_rows=False
    ):
        query = "SELECT ma_nv FROM nhan_vien WHERE ma_phong_ban = %s"
        if lock_rows:
            query += " FOR UPDATE"
        cursor.execute(query, (ma_phong_ban,))

        used_numbers = []
        for row in cursor.fetchall():
            employee_id = str(row[0])
            if not employee_id.startswith(prefix):
                continue
            suffix = employee_id[len(prefix):]
            if suffix.isdigit():
                used_numbers.append(int(suffix))

        return f"{prefix}{max(used_numbers, default=0) + 1:03d}"

    def validate_inputs(self, for_create=False):
        ma = self.var_ma_nv.get().strip()
        ten = self.capitalize_name(self.var_ten_nv.get())
        email = self.var_email.get().strip().lower()
        sdt = self.var_sdt.get().strip()
        ngay_sinh_str = self.var_ngay_sinh.get().strip()
        ngay_vao_lam_str = self.var_ngay_vao_lam.get().strip()
        ngay_nghi_viec_str = self.var_ngay_nghi_viec.get().strip()
        selected_pb_name = self.var_phong_ban.get().strip()
        selected_cv_name = self.var_chuc_vu.get().strip()
        employee_status = self.var_trang_thai.get().strip()

        self.var_ten_nv.set(ten)
        self.var_email.set(email)

        if not ma or not ten or not email or not sdt or not ngay_vao_lam_str:
            messagebox.showwarning(
                "Cảnh báo",
                "Vui lòng nhập đầy đủ các thông tin bắt buộc (*): Mã NV, Họ Tên,"
                " Email, Số ĐT và Ngày vào làm!",
            )
            return False

        if selected_pb_name not in self.dict_phong_ban:
            messagebox.showwarning(
                "Cảnh báo", "Vui lòng chọn một phòng ban hợp lệ!"
            )
            return False

        if selected_cv_name not in self.dict_chuc_vu:
            messagebox.showwarning(
                "Cảnh báo", "Vui lòng chọn một chức vụ hợp lệ!"
            )
            return False

        if employee_status not in {
            STATUS_WORKING,
            STATUS_PROBATION,
            STATUS_RESIGNED,
        }:
            messagebox.showwarning(
                "Cảnh báo", "Trạng thái nhân viên không hợp lệ!"
            )
            return False

        if for_create and employee_status == STATUS_RESIGNED:
            messagebox.showwarning(
                "Cảnh báo",
                "Không thể thêm mới nhân viên ở trạng thái 'Đã nghỉ việc'.",
            )
            return False

        if len(ma) > 20 or len(ten) > 100 or len(email) > 100 or len(sdt) > 15:
            messagebox.showwarning(
                "Cảnh báo",
                "Dữ liệu vượt quá độ dài cho phép của Mã NV, Họ tên, "
                "Email hoặc Số điện thoại.",
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

        try:
            ngay_vao_lam = datetime.datetime.strptime(
                ngay_vao_lam_str, "%d/%m/%Y"
            ).date()
        except ValueError:
            messagebox.showwarning(
                "Cảnh báo",
                "Ngày vào làm không hợp lệ! Vui lòng nhập theo chuẩn DD/MM/YYYY.",
            )
            return False

        today_date = datetime.date.today()
        earliest_start = self.date_years_ago(parsed_date.date(), -18)
        if ngay_vao_lam < earliest_start:
            messagebox.showwarning(
                "Cảnh báo",
                "Ngày vào làm phải từ thời điểm nhân viên đủ 18 tuổi.",
            )
            return False
        if ngay_vao_lam > today_date:
            messagebox.showwarning(
                "Cảnh báo", "Ngày vào làm không được lớn hơn ngày hiện tại."
            )
            return False

        ngay_nghi_viec = None
        if ngay_nghi_viec_str:
            try:
                ngay_nghi_viec = datetime.datetime.strptime(
                    ngay_nghi_viec_str, "%d/%m/%Y"
                ).date()
            except ValueError:
                messagebox.showwarning(
                    "Cảnh báo",
                    "Ngày nghỉ việc không hợp lệ! Vui lòng nhập theo chuẩn DD/MM/YYYY.",
                )
                return False
            if ngay_nghi_viec < ngay_vao_lam:
                messagebox.showwarning(
                    "Cảnh báo", "Ngày nghỉ việc không được trước ngày vào làm."
                )
                return False
            if ngay_nghi_viec > today_date:
                messagebox.showwarning(
                    "Cảnh báo", "Ngày nghỉ việc không được lớn hơn ngày hiện tại."
                )
                return False

        if employee_status == STATUS_RESIGNED and ngay_nghi_viec is None:
            messagebox.showwarning(
                "Cảnh báo",
                "Nhân viên đã nghỉ việc phải có ngày nghỉ việc.",
            )
            return False
        if employee_status != STATUS_RESIGNED and ngay_nghi_viec is not None:
            messagebox.showwarning(
                "Cảnh báo",
                "Chỉ nhập ngày nghỉ việc khi trạng thái là 'Đã nghỉ việc'.",
            )
            return False

        luong_val = self.parse_money(self.var_luong_cb.get())
        if luong_val <= 0:
            messagebox.showwarning(
                "Cảnh báo", "Lương cơ bản phải lớn hơn 0 đồng!"
            )
            return False

        if luong_val > 9_999_999_999_999.99:
            messagebox.showwarning(
                "Cảnh báo", "Lương cơ bản vượt quá giới hạn lưu trữ!"
            )
            return False

        return True

    def check_truong_phong_constraint(
        self, ma_phong_ban, current_ma_nv="", cursor=None
    ):
        own_connection = cursor is None
        conn = get_db_connection() if own_connection else None
        if own_connection and not conn:
            return False
        work_cursor = None
        try:
            work_cursor = cursor or conn.cursor()
            if not own_connection:
                work_cursor.execute(
                    """
                    SELECT ma_phong_ban
                    FROM phong_ban
                    WHERE ma_phong_ban = %s
                    FOR UPDATE
                    """,
                    (ma_phong_ban,),
                )
                if not work_cursor.fetchone():
                    return False
            query = """
                SELECT nv.ma_nv
                FROM nhan_vien nv
                INNER JOIN chuc_vu cv ON cv.ma_chuc_vu = nv.ma_chuc_vu
                WHERE nv.ma_phong_ban = %s
                  AND LOWER(TRIM(cv.ten_chuc_vu)) = LOWER(%s)
                  AND nv.trang_thai <> %s
                  AND nv.ma_nv <> %s
                LIMIT 1
            """
            if not own_connection:
                query += " FOR UPDATE"
            work_cursor.execute(
                query,
                (
                    ma_phong_ban,
                    "Trưởng phòng",
                    STATUS_RESIGNED,
                    current_ma_nv,
                ),
            )
            return work_cursor.fetchone() is None
        except Error as e:
            print(f"Lỗi kiểm tra trưởng phòng: {e}")
            return False
        finally:
            if own_connection and conn:
                if work_cursor:
                    work_cursor.close()
                conn.close()

    def format_date_to_db(self, date_str):
        try:
            return datetime.datetime.strptime(date_str, "%d/%m/%Y").strftime(
                "%Y-%m-%d"
            )
        except Exception:
            return None

    def find_duplicate_employee_data(
        self,
        cursor,
        ma_nv,
        email,
        sdt,
        current_ma_nv=None,
        current_user_id=None,
        check_identity=False,
    ):
        """Trả về các trường bị trùng để cảnh báo trước khi ghi dữ liệu."""
        duplicates = []

        if check_identity:
            cursor.execute(
                "SELECT 1 FROM nhan_vien WHERE ma_nv = %s LIMIT 1",
                (ma_nv,),
            )
            if cursor.fetchone():
                duplicates.append(f"Mã nhân viên '{ma_nv}' đã được sử dụng")

            cursor.execute(
                "SELECT 1 FROM nguoi_dung WHERE ten_dang_nhap = %s LIMIT 1",
                (ma_nv,),
            )
            if cursor.fetchone():
                duplicates.append(f"Tên đăng nhập '{ma_nv}' đã được sử dụng")

        cursor.execute(
            """
            SELECT 1
            FROM nhan_vien
            WHERE email = %s AND (%s IS NULL OR ma_nv <> %s)
            LIMIT 1
            """,
            (email, current_ma_nv, current_ma_nv),
        )
        email_exists = cursor.fetchone() is not None

        if check_identity or current_user_id is not None:
            cursor.execute(
                """
                SELECT 1
                FROM nguoi_dung
                WHERE email = %s AND (%s IS NULL OR id <> %s)
                LIMIT 1
                """,
                (email, current_user_id, current_user_id),
            )
            # Luôn đọc kết quả truy vấn trước khi kết hợp điều kiện. Nếu dùng
            # phép `or` trực tiếp, Python có thể bỏ qua fetchone() và khiến
            # MySQL báo "Unread result found" ở câu lệnh kế tiếp.
            account_email_exists = cursor.fetchone() is not None
            email_exists = email_exists or account_email_exists

        if email_exists:
            duplicates.append(f"Email '{email}' đã được sử dụng")

        cursor.execute(
            """
            SELECT 1
            FROM nhan_vien
            WHERE sdt = %s AND (%s IS NULL OR ma_nv <> %s)
            LIMIT 1
            """,
            (sdt, current_ma_nv, current_ma_nv),
        )
        if cursor.fetchone():
            duplicates.append(f"Số điện thoại '{sdt}' đã được sử dụng")

        return duplicates

    @staticmethod
    def format_duplicate_warning(duplicates):
        details = "\n".join(f"• {item}" for item in duplicates)
        return (
            "Không thể lưu thông tin vì dữ liệu sau đã tồn tại:\n\n"
            f"{details}\n\n"
            "Vui lòng kiểm tra và nhập giá trị khác."
        )

    def show_operation_error(self, action, error):
        """Ẩn chi tiết MySQL và chuyển lỗi kỹ thuật thành hướng dẫn dễ hiểu."""
        print(f"Lỗi khi {action}: {error}")
        errno = getattr(error, "errno", None)
        error_text = str(error).lower()

        if errno == 1062:
            if "sdt" in error_text:
                message = "Số điện thoại này đã được sử dụng bởi nhân viên khác."
            elif "email" in error_text:
                message = "Email này đã được sử dụng bởi nhân viên hoặc tài khoản khác."
            elif "ten_dang_nhap" in error_text:
                message = "Tên đăng nhập này đã tồn tại. Vui lòng làm mới mã nhân viên."
            elif "primary" in error_text or "ma_nv" in error_text:
                message = "Mã nhân viên này đã tồn tại. Vui lòng làm mới hoặc đổi mã."
            else:
                message = "Một giá trị duy nhất đã được sử dụng. Vui lòng kiểm tra lại dữ liệu."
        elif errno in (1451, 1452):
            message = (
                "Dữ liệu đang liên kết với thông tin khác hoặc thông tin được chọn "
                "không còn tồn tại. Vui lòng tải lại danh sách và thử lại."
            )
        elif errno in (1048, 1265, 1366, 1406):
            message = (
                "Một trường dữ liệu đang thiếu, sai định dạng hoặc vượt quá độ dài "
                "cho phép. Vui lòng kiểm tra lại thông tin đã nhập."
            )
        elif errno in (1205, 1213):
            message = "Dữ liệu đang được xử lý ở phiên khác. Vui lòng thử lại sau ít giây."
        elif errno in (1049, 1146):
            message = "Cấu hình dữ liệu của hệ thống chưa đầy đủ. Vui lòng liên hệ quản trị viên."
        else:
            message = (
                f"Hệ thống chưa thể {action}. Vui lòng thử lại. "
                "Nếu lỗi tiếp tục xảy ra, hãy liên hệ quản trị viên."
            )

        messagebox.showerror(f"Không thể {action}", message)

    # --- NẠP DỮ LIỆU BẢNG: CHỈ LỌC DUY NHẤT NHÂN VIÊN PHÒNG MÌNH VỚI QUA N TRƯỜNG PHÒNG ---
    def load_data(self, reset_search=True):
        if reset_search:
            self.var_tim_kiem.set("")
        self.update_search_placeholder()

        if not self.can_manage_employees():
            self.refresh_table([])
            return
        if self.role == ROLE_MANAGER and not self.user_ma_phong_ban:
            self.refresh_table([])
            return

        conn = get_db_connection()
        if not conn:
            return
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)

            if self.role == ROLE_MANAGER:
                query = """
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh,
                           nv.ngay_vao_lam, nv.ngay_nghi_viec, nv.email, nv.sdt,
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
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh,
                           nv.ngay_vao_lam, nv.ngay_nghi_viec, nv.email, nv.sdt,
                           pb.ten_phong_ban, cv.ten_chuc_vu, nv.luong_co_ban, nv.trang_thai
                    FROM nhan_vien nv
                    LEFT JOIN phong_ban pb ON nv.ma_phong_ban = pb.ma_phong_ban
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    ORDER BY nv.ma_nv ASC
                """
                cursor.execute(query)

            self.refresh_table(cursor.fetchall())
        except Error as e:
            self.show_operation_error("tải danh sách nhân viên", e)
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def refresh_table(self, data_list):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in data_list:
            ngay_sinh = (
                row["ngay_sinh"].strftime("%d/%m/%Y") if row["ngay_sinh"] else ""
            )
            ngay_vao_lam = (
                row["ngay_vao_lam"].strftime("%d/%m/%Y")
                if row["ngay_vao_lam"]
                else ""
            )
            ngay_nghi_viec = (
                row["ngay_nghi_viec"].strftime("%d/%m/%Y")
                if row["ngay_nghi_viec"]
                else ""
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
                    ngay_vao_lam,
                    ngay_nghi_viec,
                    row["email"],
                    row["sdt"],
                    row["ten_phong_ban"] or "",
                    row["ten_chuc_vu"] or "",
                    luong_cb,
                    row["trang_thai"],
                ),
            )

    def them_nhan_vien(self):
        if not self.ensure_manage_permission():
            return
        if not self.ensure_manager_department():
            return
        if self.selected_ma_nv:
            messagebox.showwarning(
                "Cảnh báo",
                "Bạn đang chọn một nhân viên có sẵn. "
                "Hãy bấm 'Làm mới' trước khi thêm nhân viên.",
            )
            return
        if not self.validate_inputs(for_create=True):
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
        prefix = self.dict_tien_to.get(selected_pb_name, "NV")

        if self.role == ROLE_MANAGER:
            ma_phong = self.user_ma_phong_ban

        is_manager_position = self.is_manager_position(selected_cv_name)
        if is_manager_position and self.role == ROLE_MANAGER:
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không được phép tạo nhân viên "
                "có chức vụ Trưởng phòng!"
            )
            return

        vai_tro = ROLE_MANAGER if is_manager_position else ROLE_EMPLOYEE
        conn = get_db_connection()
        if not conn:
            messagebox.showerror(
                "Lỗi",
                "Không thể kết nối đến cơ sở dữ liệu!"
            )
            return

        cursor = None
        try:
            cursor = conn.cursor()

            # Khóa phòng ban để hai phiên không cùng sinh một mã nhân viên.
            cursor.execute(
                """
                SELECT ma_phong_ban
                FROM phong_ban
                WHERE ma_phong_ban = %s
                FOR UPDATE
                """,
                (ma_phong,),
            )
            if not cursor.fetchone():
                conn.rollback()
                messagebox.showerror(
                    "Lỗi", "Phòng ban đã chọn không còn tồn tại."
                )
                return

            if ma == self.generated_ma_nv:
                ma = self.calculate_next_employee_id(
                    cursor, ma_phong, prefix, lock_rows=True
                )
                self.var_ma_nv.set(ma)

            duplicates = self.find_duplicate_employee_data(
                cursor,
                ma,
                email,
                sdt,
                check_identity=True,
            )
            if duplicates:
                conn.rollback()
                messagebox.showwarning(
                    "Dữ liệu đã tồn tại",
                    self.format_duplicate_warning(duplicates),
                )
                return

            if is_manager_position and not self.check_truong_phong_constraint(
                ma_phong, cursor=cursor
            ):
                conn.rollback()
                messagebox.showwarning(
                    "Cảnh báo",
                    f"Phòng '{selected_pb_name}' đã có Trưởng phòng hoặc "
                    "không thể xác minh ràng buộc Trưởng phòng.",
                )
                return

            username = ma
            # Luồng đăng nhập hiện tại của ứng dụng vẫn dùng mật khẩu rõ.
            # Không hash riêng tại đây vì sẽ làm tài khoản mới không đăng nhập được.
            default_password = "123456"
            account_status = self.account_status_from_employee_status(
                self.var_trang_thai.get()
            )

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
                VALUES (%s, %s, %s, %s, %s, %s)
            """

            cursor.execute(
                query_user,
                (
                    username,
                    default_password,
                    ten,
                    email,
                    vai_tro,
                    account_status,
                )
            )

            nguoi_dung_id = cursor.lastrowid
            query_nv = """
                INSERT INTO nhan_vien
                (
                    ma_nv,
                    ho_ten,
                    gioi_tinh,
                    ngay_sinh,
                    ngay_vao_lam,
                    ngay_nghi_viec,
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
                    %s, %s, %s, %s, %s,
                    %s, %s, %s
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
                    self.format_date_to_db(
                        self.var_ngay_vao_lam.get()
                    ),
                    None,
                    email,
                    sdt,
                    ma_phong,
                    ma_chuc_vu,
                    luong_float,
                    self.var_trang_thai.get(),
                    nguoi_dung_id
                )
            )

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

            self.lam_moi()

        except Error as e:
            conn.rollback()
            self.show_operation_error("thêm nhân viên và tạo tài khoản", e)

        finally:
            if cursor:
                cursor.close()
            conn.close()

    def sua_nhan_vien(self):
        if not self.ensure_manage_permission():
            return
        if not self.ensure_manager_department():
            return
        if not self.selected_ma_nv:
            messagebox.showwarning(
                "Cảnh báo", "Vui lòng chọn nhân viên cần sửa từ danh sách!"
            )
            return
        if self.role == ROLE_MANAGER and self.selected_ma_nv in (
            self.user_actual_ma_nv,
            self.user_login_name,
        ):
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không thể tự chỉnh sửa hồ sơ của chính mình.",
            )
            return

        ma = self.var_ma_nv.get().strip()
        if ma != self.selected_ma_nv:
            messagebox.showwarning(
                "Không thể đổi mã",
                "Mã nhân viên là khóa định danh và không thể đổi khi sửa.",
            )
            return

        if not self.validate_inputs():
            return

        selected_pb_name = self.var_phong_ban.get().strip()
        selected_cv_name = self.var_chuc_vu.get().strip()

        ma_phong = self.dict_phong_ban.get(selected_pb_name)
        ma_chuc_vu = self.dict_chuc_vu.get(selected_cv_name)

        if self.role == ROLE_MANAGER:
            ma_phong = self.user_ma_phong_ban

        is_manager_position = self.is_manager_position(selected_cv_name)
        if is_manager_position and self.role == ROLE_MANAGER:
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không được phép bổ nhiệm nhân viên khác "
                "làm Trưởng phòng!",
            )
            return

        vai_tro = ROLE_MANAGER if is_manager_position else ROLE_EMPLOYEE
        luong_float = self.parse_money(self.var_luong_cb.get())
        ten = self.var_ten_nv.get().strip()
        email = self.var_email.get().strip()
        gioi_tinh = self.var_gioi_tinh.get()
        ngay_sinh = self.format_date_to_db(self.var_ngay_sinh.get())
        ngay_vao_lam = self.format_date_to_db(self.var_ngay_vao_lam.get())
        ngay_nghi_viec = (
            self.format_date_to_db(self.var_ngay_nghi_viec.get())
            if self.var_ngay_nghi_viec.get().strip()
            else None
        )
        sdt = self.var_sdt.get().strip()
        trang_thai = self.var_trang_thai.get()

        conn = get_db_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()
            employee, permission_error = self.get_employee_for_update(cursor, ma)
            if permission_error:
                conn.rollback()
                messagebox.showwarning("Không thể cập nhật", permission_error)
                return

            employee_user_id = employee[2]
            duplicates = self.find_duplicate_employee_data(
                cursor,
                ma,
                email,
                sdt,
                current_ma_nv=ma,
                current_user_id=employee_user_id,
            )
            if duplicates:
                conn.rollback()
                messagebox.showwarning(
                    "Dữ liệu đã tồn tại",
                    self.format_duplicate_warning(duplicates),
                )
                return

            is_current_user = (
                employee_user_id is not None
                and str(employee_user_id) == str(self.user_db_id)
            ) or ma in (self.user_actual_ma_nv, self.user_login_name)
            if self.role == ROLE_MANAGER and is_current_user:
                conn.rollback()
                messagebox.showwarning(
                    "Không có quyền",
                    "Trưởng phòng không thể tự chỉnh sửa hồ sơ của chính mình.",
                )
                return
            if is_current_user and trang_thai == STATUS_RESIGNED:
                conn.rollback()
                messagebox.showwarning(
                    "Không có quyền",
                    "Bạn không thể tự chuyển hồ sơ của mình sang trạng thái nghỉ việc.",
                )
                return

            if is_manager_position and not self.check_truong_phong_constraint(
                ma_phong, current_ma_nv=ma, cursor=cursor
            ):
                conn.rollback()
                messagebox.showwarning(
                    "Cảnh báo",
                    f"Phòng '{selected_pb_name}' đã có Trưởng phòng khác "
                    "hoặc không thể xác minh ràng buộc Trưởng phòng.",
                )
                return

            # Không tự hạ quyền tài khoản Admin đang đăng nhập.
            if self.role == ROLE_ADMIN and is_current_user:
                vai_tro = ROLE_ADMIN

            query_nv = """
                UPDATE nhan_vien
                SET
                    ho_ten=%s,
                    gioi_tinh=%s,
                    ngay_sinh=%s,
                    ngay_vao_lam=%s,
                    ngay_nghi_viec=%s,
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
                    ngay_vao_lam,
                    ngay_nghi_viec,
                    email,
                    sdt,
                    ma_phong,
                    ma_chuc_vu,
                    luong_float,
                    trang_thai,
                    ma,
                )
            )

            if employee_user_id is not None:
                cursor.execute(
                    """
                    UPDATE nguoi_dung
                    SET ho_ten=%s, email=%s, vai_tro=%s, trang_thai=%s
                    WHERE id=%s
                    """,
                    (
                        ten,
                        email,
                        vai_tro,
                        self.account_status_from_employee_status(trang_thai),
                        employee_user_id,
                    ),
                )

            conn.commit()

            account_message = (
                "Thông tin tài khoản đăng nhập cũng đã được đồng bộ."
                if employee_user_id is not None
                else "Nhân viên chưa có tài khoản đăng nhập để đồng bộ."
            )
            messagebox.showinfo(
                "Thành công",
                f"Đã cập nhật nhân viên {ma}!\n\n"
                f"{account_message}"
            )

            self.lam_moi()

        except Error as e:
            conn.rollback()
            self.show_operation_error("cập nhật nhân viên", e)

        finally:
            if cursor:
                cursor.close()
            conn.close()

    def cho_nghi_viec(self):
        if not self.ensure_manage_permission():
            return
        if not self.ensure_manager_department():
            return

        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn nhân viên cần cho nghỉ việc!"
            )
            return

        vals = self.tree.item(selected[0], "values")
        row_data = dict(zip(self.columns_def, vals))
        ma_nv = row_data["ma_nv"]
        ho_ten = row_data["ten_nv"]
        trang_thai = row_data["trang_thai"]

        if self.role == ROLE_MANAGER and ma_nv in (
            self.user_actual_ma_nv,
            self.user_login_name,
        ):
            messagebox.showwarning(
                "Không có quyền",
                "Trưởng phòng không thể tự cho hồ sơ của mình nghỉ việc.",
            )
            return

        # Đã nghỉ rồi thì không cho thực hiện lại
        if trang_thai == STATUS_RESIGNED:
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

        cursor = None
        try:
            cursor = conn.cursor()
            employee, permission_error = self.get_employee_for_update(
                cursor, ma_nv
            )
            if permission_error:
                conn.rollback()
                messagebox.showwarning("Không thể cho nghỉ việc", permission_error)
                return

            employee_user_id = employee[2]
            is_current_user = (
                employee_user_id is not None
                and str(employee_user_id) == str(self.user_db_id)
            ) or ma_nv in (self.user_actual_ma_nv, self.user_login_name)
            if is_current_user:
                conn.rollback()
                messagebox.showwarning(
                    "Không có quyền",
                    "Bạn không thể tự cho hồ sơ của chính mình nghỉ việc.",
                )
                return
            if employee[3] == STATUS_RESIGNED:
                conn.rollback()
                messagebox.showinfo(
                    "Thông báo",
                    f"Nhân viên {ho_ten} đã ở trạng thái 'Đã nghỉ việc'.",
                )
                return

            cursor.execute(
                """
                UPDATE nhan_vien
                SET trang_thai = %s,
                    ngay_nghi_viec = %s
                WHERE ma_nv = %s
                """,
                (STATUS_RESIGNED, datetime.date.today(), ma_nv),
            )

            if employee_user_id is not None:
                cursor.execute(
                    "UPDATE nguoi_dung SET trang_thai = 0 WHERE id = %s",
                    (employee_user_id,),
                )

            conn.commit()

            account_message = (
                "Tài khoản đăng nhập cũng đã được khóa."
                if employee_user_id is not None
                else "Nhân viên không có tài khoản đăng nhập cần khóa."
            )
            messagebox.showinfo(
                "Thành công",
                f"Đã cho nhân viên {ho_ten} nghỉ việc.\n\n"
                f"{account_message}"
            )

            self.lam_moi()

        except Error as e:
            conn.rollback()
            self.show_operation_error("cho nhân viên nghỉ việc", e)

        finally:
            if cursor:
                cursor.close()
            conn.close()
    def xoa_vinh_vien(self):
        if self.role != ROLE_ADMIN:
            messagebox.showwarning(
                "Không có quyền",
                "Chỉ Admin mới được phép xóa nhân viên vĩnh viễn!",
            )
            return

        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn nhân viên cần xóa!"
            )
            return

        vals = self.tree.item(selected[0], "values")
        row_data = dict(zip(self.columns_def, vals))
        ma_nv = row_data["ma_nv"]
        ho_ten = row_data["ten_nv"]
        trang_thai = row_data["trang_thai"]

        if trang_thai != STATUS_RESIGNED:
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
            "Xác nhận xóa vĩnh viễn",
            f"Bạn có chắc chắn muốn xóa:\n\n"
            f"{ho_ten} ({ma_nv})\n\n"
            f"khỏi hệ thống không?\n\n"
            f"- Tài khoản đăng nhập sẽ bị xóa hoàn toàn.\n"
            f"- Chỉ được xóa khi nhân viên chưa có lịch sử lương.\n"
            f"- Thao tác này không thể hoàn tác."
        )

        if not confirm:
            return

        conn = get_db_connection()

        if not conn:
            return

        cursor = None

        try:
            cursor = conn.cursor()
            employee, permission_error = self.get_employee_for_update(
                cursor, ma_nv
            )
            if permission_error:
                conn.rollback()
                messagebox.showwarning("Không thể xóa", permission_error)
                return

            nguoi_dung_id = employee[2]
            if employee[3] != STATUS_RESIGNED:
                conn.rollback()
                messagebox.showwarning(
                    "Không thể xóa",
                    "Nhân viên chưa ở trạng thái 'Đã nghỉ việc'.",
                )
                return

            is_current_user = (
                nguoi_dung_id is not None
                and str(nguoi_dung_id) == str(self.user_db_id)
            ) or ma_nv in (self.user_actual_ma_nv, self.user_login_name)
            if is_current_user:
                conn.rollback()
                messagebox.showwarning(
                    "Không có quyền",
                    "Bạn không thể tự xóa hồ sơ và tài khoản của chính mình.",
                )
                return

            cursor.execute(
                "SELECT COUNT(*) FROM bang_luong WHERE ma_nv = %s",
                (ma_nv,),
            )
            payroll_count = cursor.fetchone()[0]
            if payroll_count > 0:
                conn.rollback()
                messagebox.showwarning(
                    "Không thể xóa",
                    f"Nhân viên có {payroll_count} bảng lương cần được bảo toàn. "
                    "Hãy giữ hồ sơ ở trạng thái 'Đã nghỉ việc'.",
                )
                return

            cursor.execute(
                """
                DELETE FROM nhan_vien
                WHERE ma_nv = %s
                AND trang_thai = %s
                """,
                (ma_nv, STATUS_RESIGNED),
            )

            if cursor.rowcount == 0:
                conn.rollback()

                messagebox.showwarning(
                    "Không thể xóa",
                    "Nhân viên không tồn tại hoặc chưa ở trạng thái "
                    "'Đã nghỉ việc'."
                )
                return

            if nguoi_dung_id is not None:
                cursor.execute(
                    """
                    DELETE FROM nguoi_dung
                    WHERE id = %s
                    """,
                    (nguoi_dung_id,)
                )

            conn.commit()

            messagebox.showinfo(
                "Thành công",
                f"Đã xóa vĩnh viễn nhân viên:\n\n"
                f"{ho_ten} ({ma_nv})\n\n"
                f"Hồ sơ nhân viên đã xóa.\n"
                f"Tài khoản đăng nhập đã xóa."
            )

            self.lam_moi()

        except Error as e:
            conn.rollback()
            self.show_operation_error("xóa nhân viên và tài khoản", e)

        finally:
            if cursor:
                cursor.close()

            conn.close()
    def tim_kiem(self):
        keyword = self.var_tim_kiem.get().strip()
        if not keyword or keyword == self.placeholder_text:
            self.load_data()
            return
        if not self.can_manage_employees():
            self.refresh_table([])
            return
        if self.role == ROLE_MANAGER and not self.user_ma_phong_ban:
            self.refresh_table([])
            return

        conn = get_db_connection()
        if not conn:
            return
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            p = f"%{keyword}%"

            if self.role == ROLE_MANAGER:
                query = """
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh,
                           nv.ngay_vao_lam, nv.ngay_nghi_viec, nv.email, nv.sdt,
                           pb.ten_phong_ban, cv.ten_chuc_vu, nv.luong_co_ban, nv.trang_thai
                    FROM nhan_vien nv
                    LEFT JOIN phong_ban pb ON nv.ma_phong_ban = pb.ma_phong_ban
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    WHERE nv.ma_phong_ban = %s
                      AND (nv.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR nv.sdt LIKE %s)
                    ORDER BY nv.ma_nv ASC
                """
                cursor.execute(query, (self.user_ma_phong_ban, p, p, p))
            else:
                query = """
                    SELECT nv.ma_nv, nv.ho_ten, nv.gioi_tinh, nv.ngay_sinh,
                           nv.ngay_vao_lam, nv.ngay_nghi_viec, nv.email, nv.sdt,
                           pb.ten_phong_ban, cv.ten_chuc_vu, nv.luong_co_ban, nv.trang_thai
                    FROM nhan_vien nv
                    LEFT JOIN phong_ban pb ON nv.ma_phong_ban = pb.ma_phong_ban
                    LEFT JOIN chuc_vu cv ON nv.ma_chuc_vu = cv.ma_chuc_vu
                    WHERE nv.ma_nv LIKE %s OR nv.ho_ten LIKE %s OR nv.sdt LIKE %s
                    ORDER BY nv.ma_nv ASC
                """
                cursor.execute(query, (p, p, p))

            self.refresh_table(cursor.fetchall())
        except Error as e:
            self.show_operation_error("tìm kiếm nhân viên", e)
        finally:
            if cursor:
                cursor.close()
            conn.close()

    def lam_moi(self):
        self.selected_ma_nv = None
        self.generated_ma_nv = None
        self.entry_ma_nv.config(state="normal")
        self.var_ten_nv.set("")
        self.var_gioi_tinh.set("Nam")
        self.var_ngay_sinh.set("01/01/1995")
        self.var_ngay_vao_lam.set(
            datetime.date.today().strftime("%d/%m/%Y")
        )
        self.var_ngay_nghi_viec.set("")
        self.var_email.set("")
        self.var_sdt.set("")

        # NẾU LÀ TRƯỜNG PHÒNG: TỰ ĐỘNG GIỮ NGUYÊN PHÒNG BAN VÀ KHÔNG CHO ĐỔI
        if self.role == ROLE_MANAGER and self.user_ma_phong_ban:
            for ten_pb, ma_pb in self.dict_phong_ban.items():
                if ma_pb == self.user_ma_phong_ban:
                    self.var_phong_ban.set(ten_pb)
                    break
        elif self.role == ROLE_ADMIN and self.dict_phong_ban:
            self.cb_pb.current(0)

        self.generate_employee_id()

        if self.dict_chuc_vu:
            self.cb_cv.current(0)

        self.var_luong_cb.set("12.000.000")
        self.var_trang_thai.set(STATUS_WORKING)
        self.load_data()

    def on_double_click(self, event):
        self.on_tree_select(event)

    def show_context_menu(self, event):
        if not self.can_manage_employees():
            return
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
        vals = self.tree.item(selected[0], "values")
        row_data = dict(zip(self.columns_def, vals))
        self.selected_ma_nv = row_data["ma_nv"]
        self.generated_ma_nv = None

        if self.role == ROLE_MANAGER and (
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
        self.entry_ma_nv.config(state="readonly")
        self.var_ten_nv.set(row_data["ten_nv"])
        self.var_gioi_tinh.set(row_data["gioi_tinh"])
        self.var_ngay_sinh.set(row_data["ngay_sinh"])
        self.var_ngay_vao_lam.set(row_data["ngay_vao_lam"])
        self.var_ngay_nghi_viec.set(row_data["ngay_nghi_viec"])
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
