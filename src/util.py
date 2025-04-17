import sys, os
import ctypes
import psutil
import webbrowser
import requests
import os.path
from pathlib import Path
import pygetwindow as gw


current_version = "0.2alpha"

MB_OK = 0x0
MB_OKCANCEL = 0x1
MB_YESNO = 0x4
MB_ICONERROR = 0x10
MB_ICONWARNING = 0x30
MB_ICONINFORMATION = 0x40

IDOK = 1
IDCANCEL = 2
IDYES = 6
IDNO = 7

user32 = ctypes.windll.user32

import win32gui
import win32process
import psutil

def _enum_osu_windows():
    results = []

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True

        title = win32gui.GetWindowText(hwnd) or ""
        classname = win32gui.GetClassName(hwnd) or ""
        low_t = title.lower()
        low_c = classname.lower()

        if "osu!" in low_t or "osu!" in low_c:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            results.append((hwnd, pid, title, classname))
        return True

    win32gui.EnumWindows(_cb, None)
    return results

def is_osu_updater_present():
    for hwnd, pid, title, classname in _enum_osu_windows():
        lt = title.lower()
        if "updater" in lt:
            return True
    return False

def is_osu_loading_window_present():
    for hwnd, pid, title, classname in _enum_osu_windows():
        lt = title.lower()
        if "(loading)" in lt:
            return True
    return False

def is_osu_main_window_present():
    for hwnd, pid, title, classname in _enum_osu_windows():
        lt = title.lower()
        lc = classname.lower()
        if "updater" not in lt and "(loading)" not in lt:
            if lc == "osu!" or lt.startswith("osu!"):
                return True
    return False
def win_message_box(message, title, style):
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.SetForegroundWindow(hwnd)
    return ctypes.windll.user32.MessageBoxW(hwnd, message, title, style)

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(relative)

def check_for_updates():

    data = requests.get("https://launcher.m1pposu.dev/version/latest/version.json").json()
    latest_version = data["latest_version"]

    if latest_version != current_version:
        response = win_message_box(
            f"A new version {latest_version} is available. Do you want to download it?",
            "Update Available",
            MB_YESNO | MB_ICONINFORMATION
        )
        if response == IDYES:
            webbrowser.open(data["latest_version_url"])
            sys.exit()
