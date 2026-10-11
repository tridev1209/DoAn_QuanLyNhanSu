"""Chuyển lỗi kỹ thuật thành thông báo an toàn, dễ hiểu cho người dùng."""

import logging
from tkinter import messagebox


logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _log_error(action, error):
    """Giữ chi tiết lỗi trong log kỹ thuật, không đưa lên hộp thoại."""
    logger.error("Không thể %s: %s", action, error, exc_info=True)


def show_database_error(error, action="xử lý dữ liệu", parent=None, duplicate_message=None):
    """Hiển thị lỗi CSDL theo ngôn ngữ nghiệp vụ và không làm lộ mã lỗi."""
    _log_error(action, error)
    errno = getattr(error, "errno", None)

    if errno == 1062:
        messagebox.showwarning(
            "Dữ liệu đã tồn tại",
            duplicate_message
            or "Thông tin này đã tồn tại trong hệ thống. Vui lòng kiểm tra và nhập lại.",
            parent=parent,
        )
        return

    messages = {
        1048: "Một số thông tin bắt buộc còn thiếu. Vui lòng kiểm tra lại.",
        1265: "Một số thông tin chưa đúng định dạng. Vui lòng kiểm tra lại.",
        1366: "Một số thông tin chưa đúng định dạng. Vui lòng kiểm tra lại.",
        1406: "Một số thông tin vượt quá độ dài cho phép. Vui lòng nhập ngắn hơn.",
        1451: "Không thể thực hiện vì dữ liệu này đang được sử dụng ở nơi khác.",
        1452: "Thông tin liên quan không còn tồn tại. Vui lòng tải lại dữ liệu và thử lại.",
        1205: "Dữ liệu đang được xử lý ở phiên khác. Vui lòng thử lại sau ít giây.",
        1213: "Có xung đột khi cập nhật dữ liệu. Vui lòng thử lại.",
        1045: "Không thể truy cập cơ sở dữ liệu. Vui lòng liên hệ quản trị viên.",
        1049: "Cơ sở dữ liệu chưa được cấu hình đúng. Vui lòng liên hệ quản trị viên.",
        1146: "Dữ liệu hệ thống chưa được cấu hình đầy đủ. Vui lòng liên hệ quản trị viên.",
        2003: "Không thể kết nối đến cơ sở dữ liệu. Vui lòng thử lại sau.",
        2006: "Kết nối cơ sở dữ liệu đã bị gián đoạn. Vui lòng thử lại.",
        2013: "Kết nối cơ sở dữ liệu đã bị gián đoạn. Vui lòng thử lại.",
    }
    message = messages.get(
        errno,
        f"Không thể {action}. Vui lòng thử lại. "
        "Nếu lỗi tiếp tục xảy ra, hãy liên hệ quản trị viên.",
    )
    messagebox.showerror(f"Không thể {action}", message, parent=parent)


def show_file_error(error, action="xuất file", parent=None):
    """Hiển thị lỗi thao tác tệp mà không làm lộ đường dẫn hay mã hệ thống."""
    _log_error(action, error)

    if isinstance(error, PermissionError):
        message = (
            "Không thể ghi vào file đã chọn. File có thể đang được mở trong "
            "ứng dụng khác hoặc bạn không có quyền ghi."
        )
    elif isinstance(error, FileNotFoundError):
        message = "Thư mục lưu file không còn tồn tại. Vui lòng chọn vị trí khác."
    elif isinstance(error, OSError):
        message = "Không thể ghi file tại vị trí đã chọn. Vui lòng chọn vị trí khác."
    else:
        message = f"Không thể {action}. Vui lòng thử lại."

    messagebox.showerror(f"Không thể {action}", message, parent=parent)
