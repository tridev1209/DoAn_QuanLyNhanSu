import re
import tkinter as tk
from tkinter import messagebox, ttk
from db_connection import get_db_connection
from mysql.connector import Error
from ui_icons import get_icon, icon_button
from user_error import show_database_error


class DepartmentPositionForm:

    def __init__(self, parent_frame, user_info=None):
        self.parent = parent_frame
        self.user_info = user_info or {
            "id": 1,
            "ten_dang_nhap": "admin",
            "vai_tro": "Admin",
            "ho_ten": "Quản trị viên",
        }
        self.role = self.user_info.get("vai_tro", "NhanVien")

        # --- BIẾN PHÒNG BAN ---
        self.var_pb_ma = tk.StringVar()
        self.var_pb_ten = tk.StringVar()
        self.var_pb_tien_to = tk.StringVar()

        # --- BIẾN CHỨC VỤ ---
        self.var_cv_ma = tk.StringVar()
        self.var_cv_ten = tk.StringVar()
        self.var_cv_phu_cap = tk.StringVar(value="0")

        self.create_widgets()
        self.load_phong_ban_data()
        self.load_chuc_vu_data()

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

    def on_money_key_release(self, event, var):
        raw = str(var.get())
        digits = re.sub(r"\D", "", raw)
        if not digits:
            var.set("")
        else:
            num = int(digits)
            var.set(f"{num:,}".replace(",", "."))
            event.widget.icursor(tk.END)

    def on_tien_to_key_release(self, event, var):
        raw = str(var.get())
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        if len(cleaned) > 5:
            cleaned = cleaned[:5]
        var.set(cleaned)
        event.widget.icursor(tk.END)

    def validate_ten_chuc_vu(self, proposed_value):
        """Tên chức vụ chỉ được chứa các ký tự không phải chữ số."""
        return not any(char.isdigit() for char in proposed_value)

    def validate_chuc_vu_input(self, ten):
        if any(char.isdigit() for char in ten):
            messagebox.showwarning(
                "Tên chức vụ không hợp lệ",
                "Tên chức vụ không được chứa chữ số!",
            )
            return False
        return True

    def create_widgets(self):
        tk.Label(
            self.parent,
            text="QUẢN LÝ DANH MỤC PHÒNG BAN & CHỨC VỤ",
            font=("Helvetica", 13, "bold"),
            fg="#1e293b",
            bg="#f8fafc",
        ).pack(anchor="w", pady=(0, 8))

        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_pb = tk.Frame(self.notebook, bg="#f8fafc", padx=12, pady=10)
        self.notebook.add(
            self.tab_pb,
            text=" Quản Lý Phòng Ban ",
            image=get_icon(self.parent, "department", "#2563eb"),
            compound=tk.LEFT,
        )

        self.tab_cv = tk.Frame(self.notebook, bg="#f8fafc", padx=12, pady=10)
        self.notebook.add(
            self.tab_cv,
            text=" Quản Lý Chức Vụ ",
            image=get_icon(self.parent, "position", "#7c3aed"),
            compound=tk.LEFT,
        )

        self.setup_tab_phong_ban()
        self.setup_tab_chuc_vu()

    # ==============================================================================
    # TAB 1: PHÒNG BAN
    # ==============================================================================
    def setup_tab_phong_ban(self):
        input_pb = tk.LabelFrame(
            self.tab_pb,
            text=" Thông tin phòng ban ",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            padx=10,
            pady=8,
        )
        input_pb.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            input_pb,
            text="Mã Phòng Ban (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=0, sticky="w", pady=5)
        entry_pb_ma = tk.Entry(
            input_pb,
            textvariable=self.var_pb_ma,
            width=15,
            font=("Helvetica", 10, "bold"),
        )
        entry_pb_ma.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(
            input_pb,
            text="Tên Phòng Ban (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=2, sticky="w", pady=5, padx=(15, 0))
        tk.Entry(
            input_pb,
            textvariable=self.var_pb_ten,
            width=30,
            font=("Helvetica", 10),
        ).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        tk.Label(
            input_pb,
            text="Tiền Tố Sinh Mã NV (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=4, sticky="w", pady=5, padx=(15, 0))
        entry_tien_to = tk.Entry(
            input_pb,
            textvariable=self.var_pb_tien_to,
            width=10,
            font=("Helvetica", 10, "bold"),
        )
        entry_tien_to.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        entry_tien_to.bind(
            "<KeyRelease>",
            lambda e: self.on_tien_to_key_release(e, self.var_pb_tien_to),
        )

        btn_frame_pb = tk.Frame(self.tab_pb, bg="#f8fafc")
        btn_frame_pb.pack(fill=tk.X, pady=5)

        if self.role == "Admin":
            icon_button(
                btn_frame_pb,
                text="Thêm Phòng",
                icon="add",
                bg="#2563eb",
                fg="white",
                padx=10,
                pady=4,
                bd=0,
                command=self.them_phong_ban,
            ).pack(side=tk.LEFT, padx=3)
            icon_button(
                btn_frame_pb,
                text="Sửa",
                icon="edit",
                bg="#eab308",
                fg="white",
                padx=10,
                pady=4,
                bd=0,
                command=self.sua_phong_ban,
            ).pack(side=tk.LEFT, padx=3)
            icon_button(
                btn_frame_pb,
                text="Xóa",
                icon="delete",
                bg="#ef4444",
                fg="white",
                padx=10,
                pady=4,
                bd=0,
                command=self.xoa_phong_ban,
            ).pack(side=tk.LEFT, padx=3)

        icon_button(
            btn_frame_pb,
            text="Làm mới",
            icon="refresh",
            bg="#64748b",
            fg="white",
            padx=10,
            pady=4,
            bd=0,
            command=self.lam_moi_pb,
        ).pack(side=tk.LEFT, padx=3)

        table_frame_pb = tk.Frame(self.tab_pb)
        table_frame_pb.pack(fill=tk.BOTH, expand=True, pady=5)

        cols_pb = ("ma_pb", "ten_pb", "tien_to", "so_nv")
        self.tree_pb = ttk.Treeview(
            table_frame_pb, columns=cols_pb, show="headings", height=8
        )

        headers_pb = {
            "ma_pb": "Mã Phòng",
            "ten_pb": "Tên Phòng Ban",
            "tien_to": "Tiền Tố Sinh Mã NV",
            "so_nv": "Số Nhân Viên Hiện Có",
        }
        widths_pb = {"ma_pb": 120, "ten_pb": 320, "tien_to": 180, "so_nv": 180}

        for c in cols_pb:
            self.tree_pb.heading(c, text=headers_pb[c])
            self.tree_pb.column(
                c,
                width=widths_pb[c],
                anchor=tk.W if c == "ten_pb" else tk.CENTER,
            )

        sb_pb = ttk.Scrollbar(
            table_frame_pb, orient=tk.VERTICAL, command=self.tree_pb.yview
        )
        self.tree_pb.configure(yscroll=sb_pb.set)
        sb_pb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_pb.pack(fill=tk.BOTH, expand=True)

        self.tree_pb.bind(
            "<ButtonRelease-1>", lambda e: self.on_select_pb(None)
        )

    def generate_ma_phong_ban(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ma_phong_ban FROM phong_ban WHERE ma_phong_ban LIKE"
                " 'PB%' ORDER BY ma_phong_ban DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                try:
                    num = int(row[0].replace("PB", "")) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            self.var_pb_ma.set(f"PB{num:02d}")
        except Error as e:
            print(f"Lỗi sinh mã phòng: {e}")
        finally:
            conn.close()

    def load_phong_ban_data(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT pb.ma_phong_ban, pb.ten_phong_ban, pb.tien_to_ma, 
                       COUNT(nv.ma_nv) AS so_luong_nv
                FROM phong_ban pb
                LEFT JOIN nhan_vien nv ON pb.ma_phong_ban = nv.ma_phong_ban
                GROUP BY pb.ma_phong_ban, pb.ten_phong_ban, pb.tien_to_ma
                ORDER BY pb.ma_phong_ban ASC
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            for item in self.tree_pb.get_children():
                self.tree_pb.delete(item)

            for r in rows:
                self.tree_pb.insert(
                    "",
                    tk.END,
                    values=(
                        r["ma_phong_ban"],
                        r["ten_phong_ban"],
                        r["tien_to_ma"],
                        f"{r['so_luong_nv']} người",
                    ),
                )

            self.generate_ma_phong_ban()
        except Error as e:
            show_database_error(e, "tải danh sách phòng ban")
        finally:
            conn.close()

    def them_phong_ban(self):
        ma = self.var_pb_ma.get().strip().upper()
        ten = self.var_pb_ten.get().strip()
        tien_to = self.var_pb_tien_to.get().strip().upper()

        if not ma or not ten or not tien_to:
            messagebox.showwarning(
                "Cảnh báo",
                "Vui lòng nhập đầy đủ Mã phòng, Tên phòng ban và Tiền tố"
                " mã!",
            )
            return

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = (
                "INSERT INTO phong_ban (ma_phong_ban, ten_phong_ban,"
                " tien_to_ma) VALUES (%s, %s, %s)"
            )
            cursor.execute(query, (ma, ten, tien_to))
            conn.commit()
            messagebox.showinfo("Thành công", f"Đã thêm phòng ban '{ten}'!")
            self.load_phong_ban_data()
            self.lam_moi_pb()
        except Error as e:
            show_database_error(
                e,
                "thêm phòng ban",
                duplicate_message=(
                    "Mã phòng ban, tên phòng ban hoặc tiền tố mã đã tồn tại. "
                    "Vui lòng nhập thông tin khác."
                ),
            )
        finally:
            conn.close()

    def sua_phong_ban(self):
        ma = self.var_pb_ma.get().strip()
        ten = self.var_pb_ten.get().strip()
        tien_to = self.var_pb_tien_to.get().strip().upper()

        if not ma or not ten or not tien_to:
            messagebox.showwarning(
                "Cảnh báo", "Vui lòng chọn phòng ban cần sửa!"
            )
            return

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = (
                "UPDATE phong_ban SET ten_phong_ban=%s, tien_to_ma=%s WHERE"
                " ma_phong_ban=%s"
            )
            cursor.execute(query, (ten, tien_to, ma))
            conn.commit()
            messagebox.showinfo(
                "Thành công", f"Đã cập nhật thông tin phòng ban {ma}!"
            )
            self.load_phong_ban_data()
        except Error as e:
            show_database_error(
                e,
                "cập nhật phòng ban",
                duplicate_message=(
                    "Tên phòng ban hoặc tiền tố mã đã tồn tại. "
                    "Vui lòng nhập thông tin khác."
                ),
            )
        finally:
            conn.close()

    def xoa_phong_ban(self):
        selected = self.tree_pb.selection()
        if not selected:
            messagebox.showwarning(
                "Thông báo", "Vui lòng chọn phòng ban cần xóa!"
            )
            return

        vals = self.tree_pb.item(selected, "values")
        ma_pb = vals[0]
        ten_pb = vals[1]

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            # RÀNG BUỘC: Kiểm tra số nhân viên đang thuộc phòng ban này
            cursor.execute(
                "SELECT COUNT(*) FROM nhan_vien WHERE ma_phong_ban = %s",
                (ma_pb,),
            )
            count = cursor.fetchone()[0]

            if count > 0:
                messagebox.showerror(
                    "Không thể xóa!",
                    f"Phòng ban '{ten_pb}' ({ma_pb}) hiện đang có {count} nhân"
                    " viên!\n\nVui lòng chuyển toàn bộ nhân viên sang phòng ban"
                    " khác trước khi tiến hành xóa phòng ban này.",
                )
                return

            if messagebox.askyesno(
                "Xác nhận xóa",
                f"Bạn có chắc chắn muốn xóa phòng ban '{ten_pb}' ({ma_pb})?",
            ):
                cursor.execute(
                    "DELETE FROM phong_ban WHERE ma_phong_ban=%s", (ma_pb,)
                )
                conn.commit()
                messagebox.showinfo(
                    "Thành công", "Đã xóa phòng ban thành công!"
                )
                self.load_phong_ban_data()
                self.lam_moi_pb()
        except Error as e:
            show_database_error(e, "xóa phòng ban")
        finally:
            conn.close()

    def lam_moi_pb(self):
        self.var_pb_ten.set("")
        self.var_pb_tien_to.set("")
        self.generate_ma_phong_ban()

    def on_select_pb(self, event):
        selected = self.tree_pb.selection()
        if not selected:
            return
        vals = self.tree_pb.item(selected, "values")
        if vals and len(vals) >= 3:
            self.var_pb_ma.set(vals[0])
            self.var_pb_ten.set(vals[1])
            self.var_pb_tien_to.set(vals[2])

    # ==============================================================================
    # TAB 2: CHỨC VỤ
    # ==============================================================================
    def setup_tab_chuc_vu(self):
        input_cv = tk.LabelFrame(
            self.tab_cv,
            text=" Thông tin chức vụ ",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            padx=10,
            pady=8,
        )
        input_cv.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            input_cv,
            text="Mã Chức Vụ (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=0, sticky="w", pady=5)
        entry_cv_ma = tk.Entry(
            input_cv,
            textvariable=self.var_cv_ma,
            width=15,
            font=("Helvetica", 10, "bold"),
        )
        entry_cv_ma.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(
            input_cv,
            text="Tên Chức Vụ (*):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=2, sticky="w", pady=5, padx=(15, 0))
        validate_ten_cv = self.parent.register(self.validate_ten_chuc_vu)
        tk.Entry(
            input_cv,
            textvariable=self.var_cv_ten,
            width=25,
            font=("Helvetica", 10),
            validate="key",
            validatecommand=(validate_ten_cv, "%P"),
        ).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        tk.Label(
            input_cv,
            text="Phụ Cấp Chức Vụ (đ):",
            bg="#f8fafc",
            font=("Helvetica", 10),
        ).grid(row=0, column=4, sticky="w", pady=5, padx=(15, 0))
        entry_phu_cap = tk.Entry(
            input_cv,
            textvariable=self.var_cv_phu_cap,
            width=18,
            font=("Helvetica", 10),
        )
        entry_phu_cap.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        entry_phu_cap.bind(
            "<KeyRelease>",
            lambda e: self.on_money_key_release(e, self.var_cv_phu_cap),
        )

        btn_frame_cv = tk.Frame(self.tab_cv, bg="#f8fafc")
        btn_frame_cv.pack(fill=tk.X, pady=5)

        if self.role == "Admin":
            icon_button(
                btn_frame_cv,
                text="Thêm Chức Vụ",
                icon="add",
                bg="#2563eb",
                fg="white",
                padx=10,
                pady=4,
                bd=0,
                command=self.them_chuc_vu,
            ).pack(side=tk.LEFT, padx=3)
            icon_button(
                btn_frame_cv,
                text="Sửa",
                icon="edit",
                bg="#eab308",
                fg="white",
                padx=10,
                pady=4,
                bd=0,
                command=self.sua_chuc_vu,
            ).pack(side=tk.LEFT, padx=3)
            icon_button(
                btn_frame_cv,
                text="Xóa",
                icon="delete",
                bg="#ef4444",
                fg="white",
                padx=10,
                pady=4,
                bd=0,
                command=self.xoa_chuc_vu,
            ).pack(side=tk.LEFT, padx=3)

        icon_button(
            btn_frame_cv,
            text="Làm mới",
            icon="refresh",
            bg="#64748b",
            fg="white",
            padx=10,
            pady=4,
            bd=0,
            command=self.lam_moi_cv,
        ).pack(side=tk.LEFT, padx=3)

        table_frame_cv = tk.Frame(self.tab_cv)
        table_frame_cv.pack(fill=tk.BOTH, expand=True, pady=5)

        cols_cv = ("ma_cv", "ten_cv", "phu_cap", "so_nv")
        self.tree_cv = ttk.Treeview(
            table_frame_cv, columns=cols_cv, show="headings", height=8
        )

        headers_cv = {
            "ma_cv": "Mã Chức Vụ",
            "ten_cv": "Tên Chức Vụ",
            "phu_cap": "Phụ Cấp Chức Vụ (đ)",
            "so_nv": "Số Nhân Viên Đảm Nhận",
        }
        widths_cv = {"ma_cv": 130, "ten_cv": 280, "phu_cap": 200, "so_nv": 200}

        for c in cols_cv:
            self.tree_cv.heading(c, text=headers_cv[c])
            self.tree_cv.column(
                c,
                width=widths_cv[c],
                anchor=(
                    tk.W
                    if c == "ten_cv"
                    else (tk.E if c == "phu_cap" else tk.CENTER)
                ),
            )

        sb_cv = ttk.Scrollbar(
            table_frame_cv, orient=tk.VERTICAL, command=self.tree_cv.yview
        )
        self.tree_cv.configure(yscroll=sb_cv.set)
        sb_cv.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_cv.pack(fill=tk.BOTH, expand=True)

        self.tree_cv.bind(
            "<ButtonRelease-1>", lambda e: self.on_select_cv(None)
        )

    def generate_ma_chuc_vu(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ma_chuc_vu FROM chuc_vu WHERE ma_chuc_vu LIKE 'CV%'"
                " ORDER BY ma_chuc_vu DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                try:
                    num = int(row[0].replace("CV", "")) + 1
                except ValueError:
                    num = 1
            else:
                num = 1
            self.var_cv_ma.set(f"CV{num:02d}")
        except Error as e:
            print(f"Lỗi sinh mã chức vụ: {e}")
        finally:
            conn.close()

    def load_chuc_vu_data(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT cv.ma_chuc_vu, cv.ten_chuc_vu, cv.phu_cap, 
                       COUNT(nv.ma_nv) AS so_luong_nv
                FROM chuc_vu cv
                LEFT JOIN nhan_vien nv ON cv.ma_chuc_vu = nv.ma_chuc_vu
                GROUP BY cv.ma_chuc_vu, cv.ten_chuc_vu, cv.phu_cap
                ORDER BY cv.ma_chuc_vu ASC
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            for item in self.tree_cv.get_children():
                self.tree_cv.delete(item)

            for r in rows:
                phu_cap_str = self.format_money_str(r["phu_cap"])
                self.tree_cv.insert(
                    "",
                    tk.END,
                    values=(
                        r["ma_chuc_vu"],
                        r["ten_chuc_vu"],
                        f"{phu_cap_str} đ",
                        f"{r['so_luong_nv']} người",
                    ),
                )

            self.generate_ma_chuc_vu()
        except Error as e:
            show_database_error(e, "tải danh sách chức vụ")
        finally:
            conn.close()

    def them_chuc_vu(self):
        ma = self.var_cv_ma.get().strip().upper()
        ten = self.var_cv_ten.get().strip()
        phu_cap_val = self.parse_money(self.var_cv_phu_cap.get())

        if not ma or not ten:
            messagebox.showwarning(
                "Cảnh báo", "Vui lòng nhập đầy đủ Mã chức vụ và Tên chức vụ!"
            )
            return
        if not self.validate_chuc_vu_input(ten):
            return

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = (
                "INSERT INTO chuc_vu (ma_chuc_vu, ten_chuc_vu, phu_cap) VALUES"
                " (%s, %s, %s)"
            )
            cursor.execute(query, (ma, ten, phu_cap_val))
            conn.commit()
            messagebox.showinfo("Thành công", f"Đã thêm chức vụ '{ten}'!")
            self.load_chuc_vu_data()
            self.lam_moi_cv()
        except Error as e:
            show_database_error(
                e,
                "thêm chức vụ",
                duplicate_message=(
                    "Mã chức vụ hoặc tên chức vụ đã tồn tại. "
                    "Vui lòng nhập thông tin khác."
                ),
            )
        finally:
            conn.close()

    def sua_chuc_vu(self):
        ma = self.var_cv_ma.get().strip()
        ten = self.var_cv_ten.get().strip()
        phu_cap_val = self.parse_money(self.var_cv_phu_cap.get())

        if not ma or not ten:
            messagebox.showwarning(
                "Cảnh báo", "Vui lòng chọn chức vụ cần sửa!"
            )
            return
        if not self.validate_chuc_vu_input(ten):
            return

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = (
                "UPDATE chuc_vu SET ten_chuc_vu=%s, phu_cap=%s WHERE"
                " ma_chuc_vu=%s"
            )
            cursor.execute(query, (ten, phu_cap_val, ma))
            conn.commit()
            messagebox.showinfo(
                "Thành công", f"Đã cập nhật thông tin chức vụ {ma}!"
            )
            self.load_chuc_vu_data()
        except Error as e:
            show_database_error(
                e,
                "cập nhật chức vụ",
                duplicate_message=(
                    "Tên chức vụ đã tồn tại. Vui lòng nhập tên khác."
                ),
            )
        finally:
            conn.close()

    def xoa_chuc_vu(self):
        selected = self.tree_cv.selection()
        if not selected:
            messagebox.showwarning(
                "Thông báo", "Vui lòng chọn chức vụ cần xóa!"
            )
            return

        vals = self.tree_cv.item(selected, "values")
        ma_cv = vals[0]
        ten_cv = vals[1]

        conn = get_db_connection()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            # RÀNG BUỘC: Kiểm tra số nhân viên đang giữ chức vụ này
            cursor.execute(
                "SELECT COUNT(*) FROM nhan_vien WHERE ma_chuc_vu = %s",
                (ma_cv,),
            )
            count = cursor.fetchone()[0]

            if count > 0:
                messagebox.showerror(
                    "Không thể xóa!",
                    f"Chức vụ '{ten_cv}' ({ma_cv}) hiện đang được đảm nhận bởi"
                    f" {count} nhân viên!\n\nVui lòng cập nhật lại chức vụ cho"
                    " các nhân viên này trước khi xóa.",
                )
                return

            if messagebox.askyesno(
                "Xác nhận xóa",
                f"Bạn có chắc chắn muốn xóa chức vụ '{ten_cv}' ({ma_cv})?",
            ):
                cursor.execute(
                    "DELETE FROM chuc_vu WHERE ma_chuc_vu=%s", (ma_cv,)
                )
                conn.commit()
                messagebox.showinfo("Thành công", "Đã xóa chức vụ thành công!")
                self.load_chuc_vu_data()
                self.lam_moi_cv()
        except Error as e:
            show_database_error(e, "xóa chức vụ")
        finally:
            conn.close()

    def lam_moi_cv(self):
        self.var_cv_ten.set("")
        self.var_cv_phu_cap.set("0")
        self.generate_ma_chuc_vu()

    def on_select_cv(self, event):
        selected = self.tree_cv.selection()
        if not selected:
            return
        vals = self.tree_cv.item(selected, "values")
        if vals and len(vals) >= 3:
            self.var_cv_ma.set(vals[0])
            self.var_cv_ten.set(vals[1])
            self.var_cv_phu_cap.set(
                self.format_money_str(self.parse_money(vals[2]))
            )


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Test Độc Lập - Quản Lý Phòng Ban & Chức Vụ")
    root.geometry("900x550")

    test_frame = tk.Frame(root, bg="#f8fafc")
    test_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

    app = DepartmentPositionForm(test_frame)

    root.mainloop()
