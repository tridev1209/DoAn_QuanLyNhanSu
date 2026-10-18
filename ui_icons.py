"""Bộ icon nét đơn dùng chung cho giao diện Tkinter.

Icon được vẽ bằng ``PhotoImage`` để luôn có cùng kích thước trên mọi màn hình,
không phụ thuộc cách Windows hiển thị emoji màu.
"""

import tkinter as tk


ICON_SIZE = 16
BUTTON_FONT = ("Segoe UI", 10, "bold")

_ICON_CACHE = {}


def _pixel(image, color, x, y, size):
    scale = size / 16
    px = max(0, min(size - 1, round(x * scale)))
    py = max(0, min(size - 1, round(y * scale)))
    image.put(color, (px, py))


def _line(image, color, x1, y1, x2, y2, size, width=1):
    dx = abs(x2 - x1)
    sx = 1 if x1 < x2 else -1
    dy = -abs(y2 - y1)
    sy = 1 if y1 < y2 else -1
    error = dx + dy

    while True:
        for offset_x in range(width):
            for offset_y in range(width):
                _pixel(image, color, x1 + offset_x, y1 + offset_y, size)
        if x1 == x2 and y1 == y2:
            break
        error_twice = 2 * error
        if error_twice >= dy:
            error += dy
            x1 += sx
        if error_twice <= dx:
            error += dx
            y1 += sy


def _rect(image, color, x1, y1, x2, y2, size, fill=False, width=1):
    if fill:
        for y in range(y1, y2 + 1):
            _line(image, color, x1, y, x2, y, size)
        return
    for offset in range(width):
        _line(image, color, x1 + offset, y1 + offset, x2 - offset, y1 + offset, size)
        _line(image, color, x1 + offset, y2 - offset, x2 - offset, y2 - offset, size)
        _line(image, color, x1 + offset, y1 + offset, x1 + offset, y2 - offset, size)
        _line(image, color, x2 - offset, y1 + offset, x2 - offset, y2 - offset, size)


def _circle(image, color, cx, cy, radius, size, width=1):
    x = radius
    y = 0
    error = 1 - radius
    while x >= y:
        points = (
            (cx + x, cy + y), (cx + y, cy + x),
            (cx - y, cy + x), (cx - x, cy + y),
            (cx - x, cy - y), (cx - y, cy - x),
            (cx + y, cy - x), (cx + x, cy - y),
        )
        for px, py in points:
            for offset in range(width):
                _pixel(image, color, px, py + offset, size)
        y += 1
        if error < 0:
            error += 2 * y + 1
        else:
            x -= 1
            error += 2 * (y - x) + 1


def _draw_icon(image, name, color, size):
    line = lambda x1, y1, x2, y2, width=1: _line(
        image, color, x1, y1, x2, y2, size, width
    )
    rect = lambda x1, y1, x2, y2, fill=False, width=1: _rect(
        image, color, x1, y1, x2, y2, size, fill, width
    )
    circle = lambda cx, cy, radius, width=1: _circle(
        image, color, cx, cy, radius, size, width
    )

    if name == "app":
        rect(2, 2, 7, 7, width=2)
        rect(9, 2, 14, 7, width=2)
        rect(2, 9, 7, 14, width=2)
        rect(9, 9, 14, 14, width=2)
    elif name == "employees":
        circle(6, 5, 3, width=2)
        circle(12, 6, 2)
        line(1, 14, 1, 12, 2)
        line(1, 12, 4, 9, 2)
        line(4, 9, 8, 9, 2)
        line(8, 9, 11, 12, 2)
        line(11, 12, 11, 14, 2)
        line(11, 10, 14, 10)
        line(14, 10, 15, 13)
    elif name == "department":
        rect(2, 4, 13, 14, width=2)
        line(1, 4, 7, 1, 2)
        line(7, 1, 14, 4, 2)
        rect(4, 6, 6, 8, fill=True)
        rect(9, 6, 11, 8, fill=True)
        rect(6, 10, 9, 14, width=1)
    elif name == "position":
        circle(8, 6, 4, width=2)
        line(5, 10, 4, 15, 2)
        line(11, 10, 12, 15, 2)
        line(4, 15, 8, 13, 1)
        line(12, 15, 8, 13, 1)
    elif name == "account":
        rect(1, 3, 14, 13, width=2)
        circle(5, 7, 2)
        line(3, 11, 7, 11, 2)
        line(9, 6, 12, 6)
        line(9, 9, 12, 9)
    elif name == "payroll":
        circle(8, 8, 6, width=2)
        line(8, 3, 8, 13)
        line(5, 5, 10, 5, 2)
        line(5, 5, 5, 8)
        line(5, 8, 10, 8, 2)
        line(10, 8, 10, 11)
        line(5, 11, 10, 11, 2)
    elif name == "report":
        line(2, 2, 2, 14, 2)
        line(2, 14, 14, 14, 2)
        rect(4, 9, 6, 13, fill=True)
        rect(8, 6, 10, 13, fill=True)
        rect(12, 3, 14, 13, fill=True)
    elif name == "profile":
        circle(8, 5, 3, width=2)
        line(3, 14, 3, 12, 2)
        line(3, 12, 6, 9, 2)
        line(6, 9, 10, 9, 2)
        line(10, 9, 13, 12, 2)
        line(13, 12, 13, 14, 2)
    elif name == "document":
        rect(3, 1, 12, 14, width=2)
        line(8, 1, 12, 5)
        line(8, 1, 8, 5)
        line(8, 5, 12, 5)
        line(5, 8, 10, 8)
        line(5, 11, 10, 11)
    elif name == "logout":
        rect(2, 2, 9, 14, width=2)
        line(7, 8, 15, 8, 2)
        line(12, 5, 15, 8, 2)
        line(12, 11, 15, 8, 2)
    elif name == "add":
        circle(8, 8, 6, width=2)
        line(8, 4, 8, 12, 2)
        line(4, 8, 12, 8, 2)
    elif name == "edit":
        line(3, 12, 11, 4, 2)
        line(5, 14, 13, 6, 2)
        line(11, 3, 14, 6, 2)
        line(2, 14, 5, 14, 2)
    elif name == "resign":
        circle(8, 8, 6, width=2)
        line(4, 12, 12, 4, 2)
    elif name == "delete":
        rect(4, 5, 12, 14, width=2)
        line(2, 4, 14, 4, 2)
        line(6, 2, 10, 2, 2)
        line(7, 7, 7, 12)
        line(10, 7, 10, 12)
    elif name == "refresh":
        circle(8, 8, 6, width=2)
        line(10, 1, 14, 2, 2)
        line(14, 2, 13, 6, 2)
        line(6, 15, 2, 14, 2)
        line(2, 14, 3, 10, 2)
    elif name == "search":
        circle(6, 6, 4, width=2)
        line(9, 9, 14, 14, 2)
    elif name == "chevron_down":
        line(3, 6, 8, 11, 2)
        line(8, 11, 13, 6, 2)
    elif name == "save":
        rect(2, 2, 13, 14, width=2)
        rect(5, 2, 10, 6, width=1)
        rect(5, 9, 11, 14, width=1)
    elif name == "key":
        circle(5, 6, 3, width=2)
        line(8, 8, 14, 14, 2)
        line(11, 11, 13, 9, 1)
    elif name in ("lock", "unlock"):
        rect(3, 7, 13, 14, width=2)
        if name == "lock":
            circle(8, 7, 4, width=2)
        else:
            circle(5, 6, 4, width=2)
            line(9, 6, 9, 8, 2)
        circle(8, 10, 1)
        line(8, 11, 8, 13)
    elif name == "export":
        line(8, 1, 8, 10, 2)
        line(4, 7, 8, 11, 2)
        line(12, 7, 8, 11, 2)
        line(2, 13, 14, 13, 2)
    elif name == "calendar":
        rect(2, 3, 14, 14, width=2)
        line(2, 7, 14, 7, 2)
        line(5, 1, 5, 5, 2)
        line(11, 1, 11, 5, 2)
        rect(5, 9, 7, 11, fill=True)
        rect(10, 9, 12, 11, fill=True)
    elif name == "active":
        circle(8, 8, 6, width=2)
        line(4, 8, 7, 11, 2)
        line(7, 11, 12, 5, 2)
    elif name == "inactive":
        circle(8, 8, 6, width=2)
        line(5, 5, 11, 11, 2)
        line(11, 5, 5, 11, 2)
    else:
        rect(3, 3, 12, 12, width=2)


def get_icon(master, name, color="#ffffff", size=ICON_SIZE):
    """Trả về icon đã cache theo cửa sổ Tcl, tên, màu và kích thước."""
    cache_key = (id(master.tk), name, color, size)
    if cache_key not in _ICON_CACHE:
        image = tk.PhotoImage(master=master, width=size, height=size)
        _draw_icon(image, name, color, size)
        _ICON_CACHE[cache_key] = image
    return _ICON_CACHE[cache_key]


def icon_button(parent, text, icon, icon_color=None, **kwargs):
    """Tạo nút có icon 16x16 và khoảng cách thống nhất."""
    foreground = kwargs.get("fg", "#0f172a")
    image = get_icon(parent, icon, icon_color or foreground)
    kwargs.setdefault("font", BUTTON_FONT)
    kwargs.setdefault("compound", tk.LEFT)
    kwargs.setdefault("padx", 10)
    button = tk.Button(parent, text=text, image=image, **kwargs)
    button._icon_image = image
    return button


def icon_label(parent, text, icon, icon_color=None, **kwargs):
    """Tạo nhãn có icon 16x16 và khoảng cách thống nhất."""
    foreground = kwargs.get("fg", "#0f172a")
    image = get_icon(parent, icon, icon_color or foreground)
    kwargs.setdefault("compound", tk.LEFT)
    label = tk.Label(parent, text=text, image=image, **kwargs)
    label._icon_image = image
    return label

