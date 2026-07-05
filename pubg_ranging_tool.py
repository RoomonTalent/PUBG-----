#!/usr/bin/env python3
"""
PUBG 迫击炮测距工具 v1.1
自动检测PUBG启动，通过F8呼出测距菜单，右键标记两点自动计算距离。
支持系统托盘、运行日志、最小化到托盘。

使用前请将PUBG设置为无边框窗口模式（Borderless Windowed）。
依赖: pip install psutil
"""

import ctypes
import ctypes.wintypes
import json
import threading
import time
import math
import queue
import sys
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ============================================================
# 可选依赖
# ============================================================
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ============================================================
# 常量
# ============================================================
PUBG_PROCESS_NAME = "TslGame.exe"
COLOR_KEY = 0x00010101

# 虚拟键码
VK_F8 = 0x77
VK_M = 0x4D
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_CONTROL = 0x11

# Hook 类型
WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14

# 窗口消息
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_RBUTTONDOWN = 0x0204
WM_MBUTTONDOWN = 0x0207
WM_PAINT = 0x000F
WM_DESTROY = 0x0002
WM_COMMAND = 0x0111
WM_USER = 0x0400
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205

WM_TRAYICON = WM_USER + 1

# 窗口样式
WS_POPUP = 0x80000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_NOACTIVATE = 0x08000000

LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002

SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1

# GDI 常量
TRANSPARENT = 1
PS_SOLID = 0

# System metrics
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# Shell notify
NIM_ADD = 0
NIM_MODIFY = 1
NIM_DELETE = 2
NIF_MESSAGE = 1
NIF_ICON = 2
NIF_TIP = 4
NIF_STATE = 8
NIF_INFO = 0x10
NIS_HIDDEN = 1

# TrackPopupMenu
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002
TPM_LEFTALIGN = 0x0000
TPM_BOTTOMALIGN = 0x0020

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800

ID_TRAY_SHOW = 1001
ID_TRAY_EXIT = 1002

# ============================================================
# Windows API 类型定义
# ============================================================

ULONG_PTR = ctypes.wintypes.WPARAM
LRESULT = ctypes.wintypes.LPARAM
WPARAM = ctypes.wintypes.WPARAM
LPARAM = ctypes.wintypes.LPARAM
HWND = ctypes.wintypes.HWND
HINSTANCE = ctypes.wintypes.HINSTANCE
HHOOK = ctypes.wintypes.HHOOK
HDC = ctypes.wintypes.HDC
HGDIOBJ = ctypes.wintypes.HGDIOBJ
HBITMAP = ctypes.wintypes.HBITMAP
HBRUSH = ctypes.wintypes.HBRUSH
HPEN = ctypes.wintypes.HPEN
HFONT = ctypes.wintypes.HFONT
HICON = ctypes.wintypes.HANDLE
HMENU = ctypes.wintypes.HANDLE
COLORREF = ctypes.wintypes.DWORD
ATOM = ctypes.wintypes.ATOM
DWORD = ctypes.wintypes.DWORD
UINT = ctypes.wintypes.UINT
BOOL = ctypes.wintypes.BOOL
INT = ctypes.wintypes.INT
LONG = ctypes.wintypes.LONG
LPCTSTR = ctypes.wintypes.LPCWSTR
LPVOID = ctypes.wintypes.LPVOID
HANDLE = ctypes.wintypes.HANDLE


class POINT(ctypes.Structure):
    _fields_ = [("x", LONG), ("y", LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", HWND), ("message", UINT), ("wParam", WPARAM),
        ("lParam", LPARAM), ("time", DWORD), ("pt", POINT),
    ]


class RECT(ctypes.Structure):
    _fields_ = [("left", LONG), ("top", LONG), ("right", LONG), ("bottom", LONG)]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", UINT), ("style", UINT),
        ("lpfnWndProc", ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)),
        ("cbClsExtra", INT), ("cbWndExtra", INT), ("hInstance", HINSTANCE),
        ("hIcon", HANDLE), ("hCursor", HANDLE), ("hbrBackground", HBRUSH),
        ("lpszMenuName", LPCTSTR), ("lpszClassName", LPCTSTR), ("hIconSm", HANDLE),
    ]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", HDC), ("fErase", BOOL), ("rcPaint", RECT),
        ("fRestore", BOOL), ("fIncUpdate", BOOL), ("rgbReserved", ctypes.c_ubyte * 32),
    ]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", DWORD), ("scanCode", DWORD), ("flags", DWORD),
        ("time", DWORD), ("dwExtraInfo", ULONG_PTR),
    ]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", POINT), ("mouseData", DWORD), ("flags", DWORD),
        ("time", DWORD), ("dwExtraInfo", ULONG_PTR),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", BOOL), ("xHotspot", DWORD), ("yHotspot", DWORD),
        ("hbmMask", HBITMAP), ("hbmColor", HBITMAP),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", DWORD), ("hWnd", HWND), ("uID", UINT), ("uFlags", UINT),
        ("uCallbackMessage", UINT), ("hIcon", HICON),
        ("szTip", ctypes.c_wchar * 128), ("dwState", DWORD),
        ("dwStateMask", DWORD), ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", UINT), ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", DWORD), ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", HICON),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, INT, WPARAM, LPARAM)
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)


# ============================================================
# 加载 Windows API
# ============================================================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32
shell32 = ctypes.windll.shell32


def _setup_api():
    """设置 Windows API 函数签名"""

    # --- kernel32 ---
    kernel32.GetModuleHandleW.argtypes = [LPCTSTR]
    kernel32.GetModuleHandleW.restype = HINSTANCE

    # --- user32 ---
    user32.SetWindowsHookExW.argtypes = [INT, HOOKPROC, HINSTANCE, DWORD]
    user32.SetWindowsHookExW.restype = HHOOK

    user32.CallNextHookEx.argtypes = [HHOOK, INT, WPARAM, LPARAM]
    user32.CallNextHookEx.restype = LRESULT

    user32.UnhookWindowsHookEx.argtypes = [HHOOK]
    user32.UnhookWindowsHookEx.restype = BOOL

    user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
    user32.TranslateMessage.restype = BOOL

    user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
    user32.DispatchMessageW.restype = LRESULT

    user32.PostQuitMessage.argtypes = [INT]
    user32.PostQuitMessage.restype = None

    user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
    user32.RegisterClassExW.restype = ATOM

    user32.CreateWindowExW.argtypes = [
        DWORD, LPCTSTR, LPCTSTR, DWORD, INT, INT, INT, INT,
        HWND, HANDLE, HINSTANCE, LPVOID,
    ]
    user32.CreateWindowExW.restype = HWND

    user32.DefWindowProcW.argtypes = [HWND, UINT, WPARAM, LPARAM]
    user32.DefWindowProcW.restype = LRESULT

    user32.SetLayeredWindowAttributes.argtypes = [HWND, COLORREF, ctypes.c_byte, DWORD]
    user32.SetLayeredWindowAttributes.restype = BOOL

    user32.SetWindowPos.argtypes = [HWND, HWND, INT, INT, INT, INT, UINT]
    user32.SetWindowPos.restype = BOOL

    user32.GetSystemMetrics.argtypes = [INT]
    user32.GetSystemMetrics.restype = INT

    user32.GetDC.argtypes = [HWND]
    user32.GetDC.restype = HDC

    user32.ReleaseDC.argtypes = [HWND, HDC]
    user32.ReleaseDC.restype = INT

    user32.BeginPaint.argtypes = [HWND, ctypes.POINTER(PAINTSTRUCT)]
    user32.BeginPaint.restype = HDC

    user32.EndPaint.argtypes = [HWND, ctypes.POINTER(PAINTSTRUCT)]
    user32.EndPaint.restype = BOOL

    user32.InvalidateRect.argtypes = [HWND, ctypes.POINTER(RECT), BOOL]
    user32.InvalidateRect.restype = BOOL

    user32.LoadCursorW.argtypes = [HINSTANCE, ctypes.wintypes.LPARAM]
    user32.LoadCursorW.restype = HANDLE

    user32.LoadIconW.argtypes = [HINSTANCE, ctypes.wintypes.LPARAM]
    user32.LoadIconW.restype = HICON

    user32.ShowWindow.argtypes = [HWND, INT]
    user32.ShowWindow.restype = BOOL

    user32.UpdateWindow.argtypes = [HWND]
    user32.UpdateWindow.restype = BOOL

    user32.DestroyWindow.argtypes = [HWND]
    user32.DestroyWindow.restype = BOOL

    user32.PeekMessageW.argtypes = [ctypes.POINTER(MSG), HWND, UINT, UINT, UINT]
    user32.PeekMessageW.restype = BOOL

    user32.PostMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
    user32.PostMessageW.restype = BOOL

    user32.FindWindowW.argtypes = [LPCTSTR, LPCTSTR]
    user32.FindWindowW.restype = HWND

    user32.FillRect.argtypes = [HDC, ctypes.POINTER(RECT), HBRUSH]
    user32.FillRect.restype = INT

    user32.CreatePopupMenu.argtypes = []
    user32.CreatePopupMenu.restype = HMENU

    user32.AppendMenuW.argtypes = [HMENU, UINT, ctypes.wintypes.WPARAM, LPCTSTR]
    user32.AppendMenuW.restype = BOOL

    user32.TrackPopupMenu.argtypes = [HMENU, UINT, INT, INT, INT, HWND, ctypes.POINTER(RECT)]
    user32.TrackPopupMenu.restype = BOOL

    user32.DestroyMenu.argtypes = [HMENU]
    user32.DestroyMenu.restype = BOOL

    user32.SetForegroundWindow.argtypes = [HWND]
    user32.SetForegroundWindow.restype = BOOL

    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.GetCursorPos.restype = BOOL

    user32.GetAsyncKeyState.argtypes = [INT]
    user32.GetAsyncKeyState.restype = ctypes.c_short

    user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
    user32.CreateIconIndirect.restype = HICON

    # --- gdi32 ---
    gdi32.CreatePen.argtypes = [INT, INT, COLORREF]
    gdi32.CreatePen.restype = HPEN

    gdi32.CreateSolidBrush.argtypes = [COLORREF]
    gdi32.CreateSolidBrush.restype = HBRUSH

    gdi32.SelectObject.argtypes = [HDC, HGDIOBJ]
    gdi32.SelectObject.restype = HGDIOBJ

    gdi32.DeleteObject.argtypes = [HGDIOBJ]
    gdi32.DeleteObject.restype = BOOL

    gdi32.MoveToEx.argtypes = [HDC, INT, INT, ctypes.POINTER(POINT)]
    gdi32.MoveToEx.restype = BOOL

    gdi32.LineTo.argtypes = [HDC, INT, INT]
    gdi32.LineTo.restype = BOOL

    gdi32.Ellipse.argtypes = [HDC, INT, INT, INT, INT]
    gdi32.Ellipse.restype = BOOL

    gdi32.SetBkMode.argtypes = [HDC, INT]
    gdi32.SetBkMode.restype = INT

    gdi32.SetTextColor.argtypes = [HDC, COLORREF]
    gdi32.SetTextColor.restype = COLORREF

    gdi32.CreateFontW.argtypes = [INT, INT, INT, INT, INT, BOOL, BOOL, BOOL,
                                  DWORD, DWORD, DWORD, DWORD, DWORD, LPCTSTR]
    gdi32.CreateFontW.restype = HFONT

    gdi32.TextOutW.argtypes = [HDC, INT, INT, LPCTSTR, INT]
    gdi32.TextOutW.restype = BOOL

    gdi32.CreateCompatibleDC.argtypes = [HDC]
    gdi32.CreateCompatibleDC.restype = HDC

    gdi32.CreateCompatibleBitmap.argtypes = [HDC, INT, INT]
    gdi32.CreateCompatibleBitmap.restype = HBITMAP

    gdi32.CreateBitmap.argtypes = [INT, INT, UINT, UINT, LPVOID]
    gdi32.CreateBitmap.restype = HBITMAP

    gdi32.DeleteDC.argtypes = [HDC]
    gdi32.DeleteDC.restype = BOOL

    # --- shell32 ---
    shell32.Shell_NotifyIconW.argtypes = [DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = BOOL


_setup_api()

# ============================================================
# 配置文件 (保存参考像素值)
# ============================================================

def get_app_dir():
    """获取程序所在目录 (兼容 PyInstaller 打包和开发模式)"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(get_app_dir(), "pubg_ranging_config.json")


def save_config(reference=None, menu_x=None, menu_y=None, font_size=None,
                borderless_mode=None, fullscreen_opt=None):
    """保存配置到文件（只更新传入的字段，保留其他字段不变）"""
    try:
        data = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        if reference is not None:
            data["reference"] = reference
        if menu_x is not None:
            data["menu_x"] = menu_x
        if menu_y is not None:
            data["menu_y"] = menu_y
        if font_size is not None:
            data["font_size"] = font_size
        if borderless_mode is not None:
            data["borderless_mode"] = borderless_mode
        if fullscreen_opt is not None:
            data["fullscreen_opt"] = fullscreen_opt
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        log_message(f"保存配置文件失败: {e}", "warn")


def load_config():
    """从配置文件读取全部设置"""
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                ref = float(data.get("reference", 0))
                if ref < 0:
                    ref = 0
                mx = data.get("menu_x")
                my = data.get("menu_y")
                fs = int(data.get("font_size", 22))
                if fs < 10:
                    fs = 10
                if fs > 80:
                    fs = 80
                bm = bool(data.get("borderless_mode", False))
                fo = bool(data.get("fullscreen_opt", False))
                return ref, mx, my, fs, bm, fo
    except Exception as e:
        log_message(f"读取配置文件失败: {e}", "warn")
    return 0.0, None, None, 22, False, False


# ============================================================
# PUBG 全屏兼容方案
# ============================================================

PUBG_CONFIG_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "TslGame", "Saved", "Config", "WindowsNoEditor"
)
PUBG_SETTINGS_INI = os.path.join(PUBG_CONFIG_DIR, "GameUserSettings.ini")

_ini_original = {}  # 记录原始值，用于退出时恢复


def patch_pubg_ini_to_borderless():
    """将 PUBG GameUserSettings.ini 切换为无边框窗口模式"""
    global _ini_original
    try:
        if not os.path.exists(PUBG_SETTINGS_INI):
            log_message("未找到 PUBG 配置文件，无法切换无边框模式", "warn")
            return False

        with open(PUBG_SETTINGS_INI, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找并记录原始值
        changed = False
        for key in ["FullscreenMode", "LastConfirmedFullscreenMode"]:
            m = re.search(rf"^{key}=(\d+)", content, re.MULTILINE)
            if m:
                old_val = m.group(1)
                if key not in _ini_original:
                    _ini_original[key] = old_val
                if old_val != "1":
                    content = re.sub(
                        rf"^{key}=\d+", f"{key}=1", content, flags=re.MULTILINE
                    )
                    changed = True
            else:
                if key not in _ini_original:
                    _ini_original[key] = None
                content += f"\n{key}=1"
                changed = True

        if changed:
            with open(PUBG_SETTINGS_INI, "w", encoding="utf-8") as f:
                f.write(content)
            log_message("已自动切换 PUBG 为无边框窗口模式 (FullscreenMode=1)", "good")
        else:
            log_message("PUBG 已处于无边框窗口模式，无需切换")
        return True
    except Exception as e:
        log_message(f"切换无边框模式失败: {e}", "error")
        return False


def restore_pubg_ini():
    """恢复 PUBG GameUserSettings.ini 原始设置"""
    global _ini_original
    if not _ini_original:
        return
    try:
        if not os.path.exists(PUBG_SETTINGS_INI):
            return

        with open(PUBG_SETTINGS_INI, "r", encoding="utf-8") as f:
            content = f.read()

        for key, old_val in _ini_original.items():
            if old_val is not None:
                content = re.sub(
                    rf"^{key}=\d+", f"{key}={old_val}", content, flags=re.MULTILINE
                )

        with open(PUBG_SETTINGS_INI, "w", encoding="utf-8") as f:
            f.write(content)
        log_message("已恢复 PUBG 原始显示模式设置")
        _ini_original = {}
    except Exception as e:
        log_message(f"恢复 PUBG 设置失败: {e}", "warn")


def check_fullscreen_opt_disabled():
    """检查 PUBG 是否被设置了'禁用全屏优化'"""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    if "TslGame" in name or "PUBG" in name:
                        if "DISABLEFULLSCREENOPTIMIZE" in value.upper():
                            winreg.CloseKey(key)
                            return True, name
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
    except Exception:
        pass
    return False, None


def enable_fullscreen_opt():
    """移除 PUBG 的'禁用全屏优化'注册表标志"""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, key_path,
                0, winreg.KEY_READ | winreg.KEY_WRITE
            )
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    if "TslGame" in name or "PUBG" in name:
                        if "DISABLEFULLSCREENOPTIMIZE" in value.upper():
                            new_val = re.sub(
                                r'\s*DISABLEFULLSCREENOPTIMIZE\s*',
                                ' ', value, flags=re.IGNORECASE
                            ).strip()
                            if new_val:
                                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, new_val)
                            else:
                                winreg.DeleteValue(key, name)
                            winreg.CloseKey(key)
                            log_message(f"已移除 PUBG 的'禁用全屏优化'标志", "good")
                            return True
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
    except Exception as e:
        log_message(f"移除全屏优化禁用标志失败: {e}", "warn")
    return False


# ============================================================
# 日志系统 (线程安全)
# ============================================================
log_queue = queue.Queue()


def log_message(msg):
    """写入日志 (线程安全，主线程定期刷新到UI)"""
    ts = datetime.now().strftime("%H:%M:%S")
    log_queue.put(f"[{ts}] {msg}")


# ============================================================
# 线程间通信
# ============================================================
event_queue = queue.Queue()

state_lock = threading.Lock()
app_state = {
    "pubg_running": False,
    "overlay_active": False,
    "show_menu": False,
    "reference": 0.0,
    "points": [],
    "pixel_distance": 0.0,
    "real_distance": 0.0,
    "font_size": 22,
    "calibration_mode": False,
}

overlay_hwnd = None
tray_hicon = None

shutdown_flag = threading.Event()
hooks_ready = threading.Event()


def set_overlay_active(active):
    with state_lock:
        app_state["overlay_active"] = active
        if not active:
            app_state["show_menu"] = False
            app_state["points"] = []
            app_state["pixel_distance"] = 0.0
            app_state["real_distance"] = 0.0
    if overlay_hwnd:
        user32.InvalidateRect(overlay_hwnd, None, True)


def set_menu_visible(visible):
    with state_lock:
        app_state["show_menu"] = visible
        if not visible:
            app_state["points"] = []
            app_state["pixel_distance"] = 0.0
            app_state["real_distance"] = 0.0
    if overlay_hwnd:
        user32.InvalidateRect(overlay_hwnd, None, True)


def set_reference(value):
    with state_lock:
        app_state["reference"] = value
        if len(app_state["points"]) == 2:
            if value > 0:
                app_state["real_distance"] = app_state["pixel_distance"] / value * 100.0
            else:
                app_state["real_distance"] = 0.0
    if overlay_hwnd:
        user32.InvalidateRect(overlay_hwnd, None, True)


def add_or_clear_point(x, y):
    with state_lock:
        pts = app_state["points"]
        if len(pts) >= 2:
            pts.clear()
        pts.append((x, y))
        if len(pts) == 2:
            dx = pts[1][0] - pts[0][0]
            dy = pts[1][1] - pts[0][1]
            px_dist = math.sqrt(dx * dx + dy * dy)
            app_state["pixel_distance"] = px_dist
            ref = app_state["reference"]
            if ref > 0:
                app_state["real_distance"] = px_dist / ref * 100.0
            else:
                app_state["real_distance"] = 0.0
    if overlay_hwnd:
        user32.InvalidateRect(overlay_hwnd, None, True)


def get_state_snapshot():
    with state_lock:
        return dict(app_state)


# ============================================================
# 托盘图标
# ============================================================

def create_app_icon():
    """创建托盘图标 (使用系统内置图标)"""
    # IDI_APPLICATION = 32512, 使用系统默认应用图标
    hicon = user32.LoadIconW(None, 32512)
    if not hicon:
        # 备用: 使用信息图标
        hicon = user32.LoadIconW(None, 32516)  # IDI_INFORMATION
    return hicon


def add_tray_icon(hwnd):
    """添加系统托盘图标"""
    hicon = create_app_icon()

    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    nid.hIcon = hicon
    nid.szTip = "PUBG 迫击炮测距工具"

    shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))


def remove_tray_icon(hwnd):
    """移除系统托盘图标"""
    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))


def show_tray_menu(hwnd):
    """在托盘位置显示右键菜单"""
    menu = user32.CreatePopupMenu()
    user32.AppendMenuW(menu, MF_STRING, ID_TRAY_SHOW, "显示主窗口")
    user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
    user32.AppendMenuW(menu, MF_STRING, ID_TRAY_EXIT, "完全退出")

    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))

    user32.SetForegroundWindow(hwnd)

    cmd = user32.TrackPopupMenu(
        menu, TPM_RETURNCMD | TPM_LEFTALIGN | TPM_BOTTOMALIGN,
        pt.x, pt.y, 0, hwnd, None
    )

    user32.DestroyMenu(menu)

    if cmd == ID_TRAY_SHOW:
        event_queue.put(("tray_show", None))
    elif cmd == ID_TRAY_EXIT:
        event_queue.put(("tray_exit", None))


# ============================================================
# 覆盖窗口 (透明、置顶、点击穿透) + 托盘消息处理
# ============================================================

overlay_wndproc_ref = None


def create_overlay_window():
    """在独立线程中创建透明覆盖窗口"""
    global overlay_hwnd, overlay_wndproc_ref

    hinst = kernel32.GetModuleHandleW(None)

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == WM_PAINT:
            ps = PAINTSTRUCT()
            hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
            draw_overlay(hdc)
            user32.EndPaint(hwnd, ctypes.byref(ps))
            return 0
        elif msg == WM_TRAYICON:
            if lparam == WM_LBUTTONUP:
                event_queue.put(("tray_show", None))
            elif lparam == WM_RBUTTONUP:
                threading.Thread(target=show_tray_menu, args=(hwnd,), daemon=True).start()
            return 0
        elif msg == WM_COMMAND:
            # 备用：如果TrackPopupMenu返回0时通过WM_COMMAND处理
            if wparam == ID_TRAY_SHOW:
                event_queue.put(("tray_show", None))
            elif wparam == ID_TRAY_EXIT:
                event_queue.put(("tray_exit", None))
            return 0
        elif msg == WM_DESTROY:
            remove_tray_icon(hwnd)
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    overlay_wndproc_ref = WNDPROC(wnd_proc)

    wc = WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wc.style = 0
    wc.lpfnWndProc = overlay_wndproc_ref
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = hinst
    wc.hIcon = None
    wc.hCursor = user32.LoadCursorW(None, 32512)
    wc.hbrBackground = gdi32.CreateSolidBrush(COLOR_KEY)
    wc.lpszMenuName = None
    wc.lpszClassName = "PUBGRangingOverlay"
    wc.hIconSm = None

    if not user32.RegisterClassExW(ctypes.byref(wc)):
        raise RuntimeError("注册窗口类失败")

    vs_x = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vs_y = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vs_w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vs_h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

    hwnd = user32.CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE,
        "PUBGRangingOverlay", "PUBG Ranging Overlay", WS_POPUP,
        vs_x, vs_y, vs_w, vs_h,
        None, None, hinst, None,
    )

    if not hwnd:
        raise RuntimeError("创建覆盖窗口失败")

    user32.SetLayeredWindowAttributes(hwnd, COLOR_KEY, 0, LWA_COLORKEY)

    # 注册托盘图标 (失败不影响主功能)
    try:
        add_tray_icon(hwnd)
        log_message("系统托盘图标已创建")
    except Exception as e:
        log_message(f"创建托盘图标失败 (不影响测距功能): {e}", "warn")

    overlay_hwnd = hwnd
    return hwnd


def rgb(r, g, b):
    return r | (g << 8) | (b << 16)


def draw_overlay(hdc):
    """在覆盖窗口上绘制标记点和连线"""
    state = get_state_snapshot()

    if not state["overlay_active"]:
        return

    pts = state["points"]

    if not pts:
        if state["show_menu"]:
            font = gdi32.CreateFontW(
                22, 0, 0, 0, 400, 0, 0, 0,
                0, 0, 0, 4, 0, "Microsoft YaHei"
            )
            old_font = gdi32.SelectObject(hdc, font)
            gdi32.SetBkMode(hdc, TRANSPARENT)
            gdi32.SetTextColor(hdc, rgb(200, 200, 200))
            hint = "右键标记第一个点"
            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)
            gdi32.TextOutW(hdc, sw // 2 - 90, sh // 2 - 40, hint, len(hint))
            gdi32.SelectObject(hdc, old_font)
            gdi32.DeleteObject(font)
        return

    point_radius = 5
    red_brush = gdi32.CreateSolidBrush(rgb(255, 60, 60))
    white_pen = gdi32.CreatePen(PS_SOLID, 2, rgb(255, 255, 255))
    yellow_pen = gdi32.CreatePen(PS_SOLID, 2, rgb(255, 220, 50))

    for px, py in pts:
        old_brush = gdi32.SelectObject(hdc, red_brush)
        old_pen = gdi32.SelectObject(hdc, white_pen)
        gdi32.Ellipse(hdc,
                       px - point_radius, py - point_radius,
                       px + point_radius, py + point_radius)
        gdi32.SelectObject(hdc, old_brush)
        gdi32.SelectObject(hdc, old_pen)

    if len(pts) == 1 and state.get("calibration_mode"):
        px, py = pts[0]
        tip_font = gdi32.CreateFontW(
            16, 0, 0, 0, 400, 0, 0, 0,
            0, 0, 0, 4, 0, "Microsoft YaHei"
        )
        old_font = gdi32.SelectObject(hdc, tip_font)
        gdi32.SetBkMode(hdc, TRANSPARENT)
        gdi32.SetTextColor(hdc, rgb(100, 255, 100))
        hint = "标定模式: 右键标记100m距离"
        gdi32.TextOutW(hdc, px + 12, py - 10, hint, len(hint))
        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(tip_font)

    if len(pts) == 2:
        x1, y1 = pts[0]
        x2, y2 = pts[1]

        line_pen = gdi32.CreatePen(PS_SOLID, 2, rgb(255, 220, 50))
        old_pen = gdi32.SelectObject(hdc, line_pen)
        gdi32.MoveToEx(hdc, x1, y1, None)
        gdi32.LineTo(hdc, x2, y2)
        gdi32.SelectObject(hdc, old_pen)
        gdi32.DeleteObject(line_pen)

        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2

        fsize = state.get("font_size", 22)
        font = gdi32.CreateFontW(
            fsize, 0, 0, 0, 700, 0, 0, 0,
            0, 0, 0, 4, 0, "Microsoft YaHei"
        )
        old_font = gdi32.SelectObject(hdc, font)
        gdi32.SetBkMode(hdc, TRANSPARENT)

        px_dist = state["pixel_distance"]
        real_dist = state["real_distance"]

        if real_dist > 0:
            gdi32.SetTextColor(hdc, rgb(255, 255, 255))
            t1 = f"像素: {px_dist:.1f}"
            gdi32.TextOutW(hdc, mid_x - 50, mid_y - fsize - 6, t1, len(t1))
            gdi32.SetTextColor(hdc, rgb(255, 220, 50))
            t2 = f"{real_dist:.1f}m"
            gdi32.TextOutW(hdc, mid_x - 35, mid_y + 6, t2, len(t2))
        else:
            gdi32.SetTextColor(hdc, rgb(255, 255, 255))
            t1 = f"像素: {px_dist:.1f}"
            gdi32.TextOutW(hdc, mid_x - 50, mid_y - fsize // 2, t1, len(t1))

        gdi32.SelectObject(hdc, old_font)
        gdi32.DeleteObject(font)

    gdi32.DeleteObject(red_brush)
    gdi32.DeleteObject(white_pen)
    gdi32.DeleteObject(yellow_pen)


# ============================================================
# 低级别键盘和鼠标 Hook
# ============================================================

kb_hook = None
mouse_hook = None
kb_proc_ref = None
mouse_proc_ref = None

_last_f8_time = 0
_last_m_time = 0
_last_tab_time = 0
_last_esc_time = 0
_last_rclick_time = 0
_last_mclick_time = 0
THROTTLE_MS = 300


def _on_key_event(key_code, is_keydown):
    global _last_f8_time, _last_m_time, _last_tab_time, _last_esc_time

    if not is_keydown:
        return

    now_ms = int(time.time() * 1000)
    state = get_state_snapshot()
    overlay_active = state["overlay_active"]
    show_menu = state["show_menu"]

    if key_code == VK_F8 and overlay_active:
        if now_ms - _last_f8_time > THROTTLE_MS:
            _last_f8_time = now_ms
            event_queue.put(("toggle_menu", None))

    elif key_code in (VK_M, VK_TAB, VK_ESCAPE) and show_menu:
        if key_code == VK_M and now_ms - _last_m_time > THROTTLE_MS:
            _last_m_time = now_ms
            event_queue.put(("close_menu", None))
        elif key_code == VK_TAB and now_ms - _last_tab_time > THROTTLE_MS:
            _last_tab_time = now_ms
            event_queue.put(("close_menu", None))
        elif key_code == VK_ESCAPE and now_ms - _last_esc_time > THROTTLE_MS:
            _last_esc_time = now_ms
            event_queue.put(("close_menu", None))


def _on_right_click(x, y):
    global _last_rclick_time

    now_ms = int(time.time() * 1000)
    state = get_state_snapshot()
    if not state["show_menu"]:
        return

    if now_ms - _last_rclick_time > THROTTLE_MS:
        _last_rclick_time = now_ms
        event_queue.put(("right_click", (x, y)))


def _on_middle_click(x, y):
    global _last_mclick_time

    now_ms = int(time.time() * 1000)
    state = get_state_snapshot()
    if not state["show_menu"]:
        return

    if now_ms - _last_mclick_time > THROTTLE_MS:
        _last_mclick_time = now_ms
        event_queue.put(("middle_click", (x, y)))


def _keyboard_hook_proc(nCode, wParam, lParam):
    if nCode >= 0:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        is_keydown = (wParam == WM_KEYDOWN or wParam == WM_SYSKEYDOWN)
        _on_key_event(kb.vkCode, is_keydown)
    return user32.CallNextHookEx(None, nCode, wParam, lParam)


def _mouse_hook_proc(nCode, wParam, lParam):
    if nCode >= 0:
        if wParam == WM_RBUTTONDOWN:
            ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            _on_right_click(ms.pt.x, ms.pt.y)
        elif wParam == WM_MBUTTONDOWN:
            ms = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            _on_middle_click(ms.pt.x, ms.pt.y)
    return user32.CallNextHookEx(None, nCode, wParam, lParam)


def install_hooks():
    global kb_hook, mouse_hook, kb_proc_ref, mouse_proc_ref

    hinst = kernel32.GetModuleHandleW(None)

    kb_proc_ref = HOOKPROC(_keyboard_hook_proc)
    mouse_proc_ref = HOOKPROC(_mouse_hook_proc)

    kb_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, kb_proc_ref, hinst, 0)
    mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, mouse_proc_ref, hinst, 0)

    if not kb_hook:
        raise RuntimeError("安装键盘钩子失败")
    if not mouse_hook:
        raise RuntimeError("安装鼠标钩子失败")


def uninstall_hooks():
    if kb_hook:
        user32.UnhookWindowsHookEx(kb_hook)
    if mouse_hook:
        user32.UnhookWindowsHookEx(mouse_hook)


# ============================================================
# Hook + 覆盖窗口线程
# ============================================================

def overlay_thread_main():
    """运行覆盖窗口消息循环和钩子"""
    try:
        hwnd = create_overlay_window()
        user32.ShowWindow(hwnd, 5)
        user32.UpdateWindow(hwnd)

        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)

        install_hooks()
        hooks_ready.set()
        log_message("覆盖层和钩子系统已启动")

        last_topmost = time.time()
        msg = MSG()
        while not shutdown_flag.is_set():
            ret = user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1)
            if ret == 0:
                time.sleep(0.005)
                now = time.time()
                if now - last_topmost > 2.0:
                    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
                    last_topmost = now
                continue

            if msg.message == 0x0012:  # WM_QUIT
                break

            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        uninstall_hooks()
        log_message("钩子系统已卸载")

        if hwnd:
            user32.DestroyWindow(hwnd)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log_message(f"覆盖线程异常: {e}", "error")
        for line in tb.split("\n"):
            if line.strip():
                log_message(f"  {line}", "error")
        hooks_ready.set()


# ============================================================
# 进程检测器
# ============================================================

def check_pubg_running():
    """检测PUBG是否正在运行"""
    if not HAS_PSUTIL:
        try:
            hwnd = user32.FindWindowW(None, "PLAYERUNKNOWN'S BATTLEGROUNDS")
            return hwnd != 0
        except Exception:
            return False

    try:
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == PUBG_PROCESS_NAME.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


# ============================================================
# Tkinter UI - 主窗口 (带日志面板和托盘支持)
# ============================================================

class MainWindow:
    """主窗口：状态显示 + 运行日志 + 托盘支持"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PUBG 迫击炮测距工具")
        self.root.geometry("500x650")
        self.root.minsize(450, 550)
        self.root.configure(bg="#1a1a2e")

        # 居中
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 500) // 2
        y = (sh - 650) // 2
        self.root.geometry(f"+{x}+{y}")

        # 状态
        self._pubg_running = False
        self._game_was_running = False
        self._minimized_to_tray = False

        # 定时器
        self._check_timer = None
        self._log_timer = None
        self._monitor_counter = 0

        self._build_ui()
        self._start_monitoring()
        self._start_log_polling()

        # 拦截关闭按钮
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # --- 标题栏 ---
        title_frame = tk.Frame(self.root, bg="#1a1a2e")
        title_frame.pack(fill=tk.X, pady=(15, 5))

        tk.Label(
            title_frame,
            text="PUBG 迫击炮测距工具",
            font=("Microsoft YaHei", 16, "bold"),
            fg="#e94560", bg="#1a1a2e",
        ).pack()

        tk.Label(
            title_frame,
            text="Mortar Ranging Tool v1.1",
            font=("Microsoft YaHei", 8),
            fg="#666677", bg="#1a1a2e",
        ).pack()

        # --- 状态栏 ---
        status_frame = tk.Frame(self.root, bg="#16213e")
        status_frame.pack(fill=tk.X, padx=20, pady=(8, 5))

        status_left = tk.Frame(status_frame, bg="#16213e")
        status_left.pack(side=tk.LEFT, padx=10, pady=8)

        self.status_dot = tk.Canvas(
            status_left, width=12, height=12,
            bg="#16213e", highlightthickness=0
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self._dot_id = self.status_dot.create_oval(1, 1, 11, 11, fill="#ffaa00", outline="")

        self.status_label = tk.Label(
            status_left,
            text="等待PUBG启动...",
            font=("Microsoft YaHei", 11),
            fg="#cccccc", bg="#16213e",
        )
        self.status_label.pack(side=tk.LEFT)

        # 右侧: 跳过按钮 (仅在未检测到时显示)
        self.skip_btn = tk.Button(
            status_frame,
            text="我已启动游戏",
            font=("Microsoft YaHei", 9),
            bg="#e94560", fg="white",
            activebackground="#c23152", activeforeground="white",
            relief=tk.FLAT, cursor="hand2",
            padx=15, pady=4,
            command=self._on_skip,
        )
        self.skip_btn.pack(side=tk.RIGHT, padx=10, pady=8)

        # --- 使用说明 (紧凑) ---
        tip_frame = tk.Frame(self.root, bg="#1a1a2e")
        tip_frame.pack(fill=tk.X, padx=25, pady=(3, 3))

        tips = "F8=呼出菜单 | 右键(两次)=标记测距 | 中键=标定模式 | M/Tab/Esc=关闭菜单"
        tk.Label(
            tip_frame, text=tips,
            font=("Microsoft YaHei", 7),
            fg="#555566", bg="#1a1a2e",
        ).pack(anchor="w")

        # --- 字体大小设置 ---
        font_setting = tk.Frame(self.root, bg="#16213e")
        font_setting.pack(fill=tk.X, padx=20, pady=(8, 3))

        tk.Label(
            font_setting, text="标注字体大小:",
            font=("Microsoft YaHei", 9),
            fg="#aaaaaa", bg="#16213e",
        ).pack(side=tk.LEFT, padx=(10, 6), pady=6)

        init_fs = get_state_snapshot().get("font_size", 22)
        self.font_var = tk.IntVar(value=init_fs)
        self.font_spinbox = tk.Spinbox(
            font_setting,
            from_=10, to=80, increment=1, width=5,
            textvariable=self.font_var,
            font=("Microsoft YaHei", 10),
            bg="#0f3460", fg="white",
            buttonbackground="#333355",
            relief=tk.FLAT, justify=tk.CENTER,
            command=self._on_font_size_change,
        )
        self.font_spinbox.pack(side=tk.LEFT, pady=6)
        self.font_spinbox.bind("<Return>", lambda e: self._on_font_size_change())

        tk.Label(
            font_setting, text="(10-80,  默认22)",
            font=("Microsoft YaHei", 7),
            fg="#555566", bg="#16213e",
        ).pack(side=tk.LEFT, padx=(6, 0), pady=6)

        # --- 全屏兼容选项 ---
        compat_frame = tk.Frame(self.root, bg="#16213e")
        compat_frame.pack(fill=tk.X, padx=20, pady=(8, 3))

        tk.Label(
            compat_frame, text="全屏兼容:",
            font=("Microsoft YaHei", 9, "bold"),
            fg="#e94560", bg="#16213e",
        ).pack(anchor="w", padx=(10, 0), pady=(6, 2))

        self._borderless_var = tk.BooleanVar(value=False)
        self._borderless_cb = tk.Checkbutton(
            compat_frame,
            text="自动切换无边框窗口模式 (修改GameUserSettings.ini)",
            variable=self._borderless_var,
            font=("Microsoft YaHei", 8),
            fg="#aaaaaa", bg="#16213e",
            selectcolor="#16213e",
            activebackground="#16213e", activeforeground="#ffffff",
            command=self._on_borderless_toggle,
        )
        self._borderless_cb.pack(anchor="w", padx=(8, 0), pady=(0, 2))

        self._fullscreen_opt_var = tk.BooleanVar(value=False)
        self._fullscreen_opt_cb = tk.Checkbutton(
            compat_frame,
            text="启用全屏优化兼容 (移除禁用全屏优化的注册表标志)",
            variable=self._fullscreen_opt_var,
            font=("Microsoft YaHei", 8),
            fg="#aaaaaa", bg="#16213e",
            selectcolor="#16213e",
            activebackground="#16213e", activeforeground="#ffffff",
            command=self._on_fullscreen_opt_toggle,
        )
        self._fullscreen_opt_cb.pack(anchor="w", padx=(8, 0), pady=(0, 6))

        # --- 日志标题 ---
        log_header = tk.Frame(self.root, bg="#1a1a2e")
        log_header.pack(fill=tk.X, padx=20, pady=(8, 2))

        tk.Label(
            log_header,
            text="运行日志",
            font=("Microsoft YaHei", 10, "bold"),
            fg="#888899", bg="#1a1a2e",
        ).pack(side=tk.LEFT)

        # 清除日志按钮
        tk.Button(
            log_header,
            text="清除",
            font=("Microsoft YaHei", 8),
            bg="#333355", fg="#888888",
            relief=tk.FLAT, cursor="hand2",
            padx=8, pady=1,
            command=self._clear_log,
        ).pack(side=tk.RIGHT)

        # --- 日志文本框 ---
        log_container = tk.Frame(self.root, bg="#0d1117")
        log_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))

        self.log_text = tk.Text(
            log_container,
            font=("Consolas", 9),
            bg="#0d1117", fg="#c9d1d9",
            insertbackground="white",
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # 滚动条
        scrollbar = tk.Scrollbar(log_container, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 颜色标签配置
        self.log_text.tag_configure("info", foreground="#c9d1d9")
        self.log_text.tag_configure("warn", foreground="#d29922")
        self.log_text.tag_configure("good", foreground="#3fb950")
        self.log_text.tag_configure("error", foreground="#f85149")

    def _start_monitoring(self):
        if HAS_PSUTIL:
            self._check_timer = self.root.after(2000, self._check_pubg)
        else:
            self._set_status("psutil未安装, 请手动点击跳过或 pip install psutil", "#ffaa00")

    def _check_pubg(self):
        if shutdown_flag.is_set():
            return

        pubg_running = check_pubg_running()

        if pubg_running != self._pubg_running:
            self._pubg_running = pubg_running
            if pubg_running:
                self._game_was_running = True
                self._set_status("PUBG运行中 - 覆盖层已激活", "#3fb950")
                self.skip_btn.pack_forget()
                if self._borderless_var.get():
                    self.root.after(500, patch_pubg_ini_to_borderless)
                set_overlay_active(True)
                self._on_pubg_detected()
            else:
                if self._game_was_running:
                    self._set_status("PUBG已退出 - 等待中...", "#ffaa00")
                    self.skip_btn.pack(side=tk.RIGHT, padx=10, pady=8)
                    set_overlay_active(False)
                    self._on_pubg_exited()

        self._check_timer = self.root.after(2000, self._check_pubg)

    def _on_skip(self):
        self._pubg_running = True
        self._set_status("已手动启动 - 覆盖层已激活 (调试模式)", "#3fb950")
        self.skip_btn.pack_forget()
        if self._borderless_var.get():
            self.root.after(500, patch_pubg_ini_to_borderless)
        set_overlay_active(True)
        self._on_pubg_detected()

    def _on_pubg_detected(self):
        """子类可重写以接收通知"""
        pass

    def _on_pubg_exited(self):
        """子类可重写以接收通知"""
        pass

    def _set_status(self, text, color):
        self.status_label.config(text=text)
        self.status_dot.itemconfig(self._dot_id, fill=color)
        if color == "#3fb950":
            log_message(text, "good")
        elif color == "#ffaa00":
            log_message(text, "warn")
        else:
            log_message(text)

    def _on_font_size_change(self):
        try:
            fs = self.font_var.get()
            if fs < 10:
                fs = 10
                self.font_var.set(10)
            if fs > 80:
                fs = 80
                self.font_var.set(80)
            with state_lock:
                app_state["font_size"] = fs
            save_config(font_size=fs)
            if overlay_hwnd:
                user32.InvalidateRect(overlay_hwnd, None, True)
            log_message(f"标注字体大小已更改为: {fs}")
        except Exception:
            pass

    def set_font_size(self, fs):
        self.font_var.set(fs)
        with state_lock:
            app_state["font_size"] = fs

    def init_compat_settings(self, borderless_mode, fullscreen_opt):
        self._borderless_var.set(borderless_mode)
        self._fullscreen_opt_var.set(fullscreen_opt)
        if borderless_mode:
            log_message("全屏兼容: 自动切换无边框窗口模式 已启用")
        if fullscreen_opt:
            log_message("全屏兼容: 全屏优化兼容 已启用")
            if not check_fullscreen_opt_disabled()[0]:
                log_message("PUBG 全屏优化未被禁用，无需修改注册表")

    def _on_borderless_toggle(self):
        enabled = self._borderless_var.get()
        save_config(borderless_mode=enabled)
        if enabled:
            log_message("全屏兼容: 已开启自动切换无边框窗口模式")
            if self._pubg_running:
                patch_pubg_ini_to_borderless()
        else:
            log_message("全屏兼容: 已关闭自动切换无边框窗口模式")
            restore_pubg_ini()

    def _on_fullscreen_opt_toggle(self):
        enabled = self._fullscreen_opt_var.get()
        save_config(fullscreen_opt=enabled)
        if enabled:
            log_message("全屏兼容: 已开启全屏优化兼容")
            disabled, path = check_fullscreen_opt_disabled()
            if disabled:
                enable_fullscreen_opt()
                log_message(f"已为 PUBG 启用全屏优化 ({path})")
            else:
                log_message("PUBG 全屏优化已处于启用状态")
        else:
            log_message("全屏兼容: 已关闭全屏优化兼容 (建议保持开启)")

    def _start_log_polling(self):
        """定期从log_queue读取日志并更新UI"""
        self._flush_logs()
        self._log_timer = self.root.after(200, self._start_log_polling)

    def _flush_logs(self):
        try:
            while True:
                msg = log_queue.get_nowait()
                if isinstance(msg, tuple):
                    text, tag = msg
                else:
                    text, tag = msg, "info"
                self._append_log(text, tag)
        except queue.Empty:
            pass

    def _append_log(self, text, tag="info"):
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, text + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _clear_log(self):
        try:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _on_close(self):
        """关闭窗口时询问: 完全退出还是最小化到托盘"""
        result = messagebox.askyesnocancel(
            "退出选项",
            "请选择退出方式:\n\n"
            "是(Y) - 最小化到系统托盘\n"
            "否(N) - 完全退出程序\n"
            "取消 - 返回",
            parent=self.root,
        )
        if result is None:  # 取消
            return
        elif result:  # 是 = 最小化到托盘
            self._minimize_to_tray()
        else:  # 否 = 完全退出
            self._full_exit()

    def _minimize_to_tray(self):
        """最小化到系统托盘"""
        self._minimized_to_tray = True
        self.root.withdraw()
        log_message("已最小化到系统托盘 (双击托盘图标恢复)", "warn")

    def restore_from_tray(self):
        """从托盘恢复窗口"""
        if self._minimized_to_tray:
            self._minimized_to_tray = False
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            log_message("主窗口已恢复")

    def _full_exit(self):
        """完全退出"""
        log_message("正在退出程序...")
        if self._borderless_var.get():
            restore_pubg_ini()
        shutdown_flag.set()
        if self._check_timer:
            self.root.after_cancel(self._check_timer)
        if self._log_timer:
            self.root.after_cancel(self._log_timer)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# 更新 log_message 以支持 tag
_original_log_message = log_message


def log_message(msg, tag="info"):
    if isinstance(msg, str):
        log_queue.put((msg, tag))
    else:
        log_queue.put(msg)


# ============================================================
# Tkinter UI - F8 输入菜单
# ============================================================

class InputMenu:
    """F8快捷菜单 - 输入框（支持拖动和位置记忆）"""

    def __init__(self, on_confirm, on_close):
        self.on_confirm = on_confirm
        self.on_close = on_close
        self.window = None
        self.entry = None
        self._drag_x = 0
        self._drag_y = 0

    def show(self, default_value=0, saved_x=None, saved_y=None):
        if self.window is not None:
            return

        self.window = tk.Toplevel()
        self.window.title("测距菜单")
        self.window.geometry("320x180")
        self.window.resizable(False, False)
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#1a1a2e")
        self.window.overrideredirect(True)

        if saved_x is not None and saved_y is not None:
            x, y = saved_x, saved_y
        else:
            self.window.update_idletasks()
            sw = self.window.winfo_screenwidth()
            x = (sw - 320) // 2
            y = 0

        self.window.geometry(f"+{x}+{y}")
        self.window.bind("<Escape>", lambda e: self._close())

        self._build_ui(default_value)
        self.entry.focus_set()
        self._keep_on_top()

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _do_drag(self, event):
        x = self.window.winfo_x() + event.x - self._drag_x
        y = self.window.winfo_y() + event.y - self._drag_y
        self.window.geometry(f"+{x}+{y}")

    def _keep_on_top(self):
        if self.window is not None:
            try:
                self.window.attributes("-topmost", True)
                self.window.after(500, self._keep_on_top)
            except tk.TclError:
                pass

    def _build_ui(self, default_value=0):
        title_bar = tk.Frame(self.window, bg="#e94560", height=30, cursor="fleur")
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)
        title_bar.bind("<Button-1>", self._start_drag)
        title_bar.bind("<B1-Motion>", self._do_drag)

        title_label = tk.Label(
            title_bar, text="PUBG 测距工具 - 快捷菜单（可拖动）",
            font=("Microsoft YaHei", 9, "bold"),
            fg="white", bg="#e94560",
        )
        title_label.pack(side=tk.LEFT, padx=(10, 0), pady=3)
        title_label.bind("<Button-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._do_drag)

        tk.Button(
            title_bar, text="✕",
            font=("Arial", 10, "bold"),
            fg="white", bg="#e94560",
            relief=tk.FLAT, bd=0, cursor="hand2",
            command=self._close,
        ).pack(side=tk.RIGHT, padx=(0, 5), pady=3)

        content = tk.Frame(self.window, bg="#16213e")
        content.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            content, text="输入100米参考像素数",
            font=("Microsoft YaHei", 11),
            fg="#cccccc", bg="#16213e",
        ).pack(pady=(20, 5))

        tk.Label(
            content, text="(先在地图上量100m距离输入, 0=仅显示像素数)",
            font=("Microsoft YaHei", 8),
            fg="#777788", bg="#16213e",
        ).pack(pady=(0, 8))

        self.entry = tk.Entry(
            content,
            font=("Microsoft YaHei", 14),
            bg="#0f3460", fg="white",
            insertbackground="white",
            relief=tk.FLAT, justify=tk.CENTER,
            width=12,
        )
        self.entry.pack(pady=(0, 12))
        self.entry.insert(0, str(int(default_value) if default_value == int(default_value) else default_value))
        self.entry.bind("<Return>", self._confirm)
        self.entry.bind("<Key-Escape>", lambda e: self._close())

        btn_frame = tk.Frame(content, bg="#16213e")
        btn_frame.pack()

        tk.Button(
            btn_frame, text="确认",
            font=("Microsoft YaHei", 10),
            bg="#e94560", fg="white",
            relief=tk.FLAT, cursor="hand2",
            padx=20, pady=4,
            command=self._confirm,
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Button(
            btn_frame, text="关闭",
            font=("Microsoft YaHei", 10),
            bg="#333355", fg="#aaaaaa",
            relief=tk.FLAT, cursor="hand2",
            padx=20, pady=4,
            command=self._close,
        ).pack(side=tk.LEFT)

    def _confirm(self, event=None):
        try:
            val = float(self.entry.get())
            if val < 0:
                val = 0
            self.on_confirm(val)
        except ValueError:
            self.on_confirm(0)

    def _close(self):
        self.on_close()
        self.destroy()

    def destroy(self):
        if self.window:
            try:
                save_config(menu_x=self.window.winfo_x(), menu_y=self.window.winfo_y())
            except Exception:
                pass
            try:
                self.window.destroy()
            except tk.TclError:
                pass
            self.window = None
            self.entry = None

    def is_shown(self):
        return self.window is not None


# ============================================================
# 主应用程序
# ============================================================

class PubgRangingTool:
    """主控制器"""

    def __init__(self):
        self.overlay_thread = None
        self.input_menu = None
        self.main_window = None
        self.menu_visible = False

    def run(self):
        self.main_window = MainWindow()

        bm = getattr(self, '_saved_bm', False)
        fo = getattr(self, '_saved_fo', False)
        self.main_window.init_compat_settings(bm, fo)

        def on_detected():
            """PUBG检测到后启动覆盖层"""
            self._start_overlay()

        def on_exited():
            """PUBG退出后，关闭菜单"""
            if self.menu_visible:
                self._close_menu_from_hook()

        self.main_window._on_pubg_detected = on_detected
        self.main_window._on_pubg_exited = on_exited

        # 启动事件处理循环
        self._start_event_loop()
        self.main_window.run()

    def _start_overlay(self):
        if self.overlay_thread and self.overlay_thread.is_alive():
            return  # 已启动

        self.overlay_thread = threading.Thread(
            target=overlay_thread_main, daemon=True
        )
        self.overlay_thread.start()

        hooks_ready.wait(timeout=5)
        if not hooks_ready.is_set():
            log_message("错误: 无法初始化钩子系统", "error")
            messagebox.showerror("错误", "无法初始化钩子系统")
            return

    def _start_event_loop(self):
        """定期处理 hook 事件队列"""
        self._menu_visible = False

        def process_events():
            # 1. 处理 hook 事件
            try:
                while True:
                    event = event_queue.get_nowait()
                    self._handle_event(event)
            except queue.Empty:
                pass

            # 2. 定期刷新覆盖
            if overlay_hwnd:
                user32.InvalidateRect(overlay_hwnd, None, True)

            if not shutdown_flag.is_set():
                self.main_window.root.after(50, process_events)

        self.main_window.root.after(100, process_events)

    def _handle_event(self, event):
        event_type, data = event

        if event_type == "toggle_menu":
            self._toggle_menu()

        elif event_type == "close_menu":
            self._close_menu_from_hook()

        elif event_type == "right_click":
            x, y = data
            self._handle_right_click(x, y)

        elif event_type == "middle_click":
            x, y = data
            self._handle_middle_click(x, y)

        elif event_type == "tray_show":
            self.main_window.restore_from_tray()

        elif event_type == "tray_exit":
            self.main_window._full_exit()

    def _handle_right_click(self, x, y):
        pts_before = len(get_state_snapshot()["points"])

        if pts_before >= 2:
            with state_lock:
                app_state["calibration_mode"] = False

        add_or_clear_point(x, y)

        state_after = get_state_snapshot()
        pts_after = len(state_after["points"])
        calib = state_after.get("calibration_mode", False)

        if calib and pts_after == 2:
            px = state_after["pixel_distance"]
            set_reference(px)
            save_config(reference=px)
            with state_lock:
                app_state["calibration_mode"] = False
            if self.input_menu and self.input_menu.entry:
                try:
                    self.input_menu.entry.delete(0, tk.END)
                    val_str = str(int(px) if px == int(px) else round(px, 1))
                    self.input_menu.entry.insert(0, val_str)
                except Exception:
                    pass
            log_message(f"标定完成: {px:.1f} 像素 → 已自动设为100m参考值", "good")

    def _handle_middle_click(self, x, y):
        pts_before = len(get_state_snapshot()["points"])

        with state_lock:
            app_state["calibration_mode"] = True

        add_or_clear_point(x, y)

        if pts_before == 0:
            log_message("标定模式: 请右键标记地图上100m距离的第二个点")
        else:
            log_message("标定模式: 已重新开始标定")

    def _toggle_menu(self):
        if self.menu_visible:
            self._close_menu_from_hook()
        else:
            self._show_menu()

    def _show_menu(self):
        if self.menu_visible:
            return

        self.menu_visible = True
        set_menu_visible(True)

        def on_confirm(value):
            set_reference(value)
            save_config(reference=value)
            log_message(f"参考像素已设置: {value}")

        def on_close():
            self._close_menu_from_hook()

        def _create():
            current_ref = get_state_snapshot()["reference"]
            _, saved_x, saved_y, *_ = load_config()
            self.input_menu = InputMenu(on_confirm, on_close)
            self.input_menu.show(default_value=current_ref, saved_x=saved_x, saved_y=saved_y)
            log_message("测距菜单已打开")

        self.main_window.root.after(0, _create)

    def _close_menu_from_hook(self):
        if not self.menu_visible:
            return

        self.menu_visible = False
        set_menu_visible(False)

        if self.input_menu:
            self.input_menu.destroy()
            self.input_menu = None

        log_message("测距菜单已关闭")


# ============================================================
# 入口
# ============================================================

def main():
    # DPI 感知
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    log_message("PUBG 迫击炮测距工具 v1.1 启动", "good")

    saved_ref, _, _, saved_fs, saved_bm, saved_fo = load_config()
    if saved_ref > 0:
        set_reference(saved_ref)
        log_message(f"已加载保存的参考像素: {saved_ref}")
    with state_lock:
        app_state["font_size"] = saved_fs
    log_message(f"标注字体大小: {saved_fs}")

    app = PubgRangingTool()
    app._saved_bm = saved_bm
    app._saved_fo = saved_fo

    try:
        app.run()
    except KeyboardInterrupt:
        log_message("用户中断", "warn")
    except Exception as e:
        log_message(f"程序异常: {e}", "error")
        import traceback
        traceback.print_exc()
    finally:
        shutdown_flag.set()
        log_message("程序已退出")


if __name__ == "__main__":
    main()
