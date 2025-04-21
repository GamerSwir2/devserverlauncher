import platform
import sys, os
import ctypes
import psutil
import webbrowser
import requests
import os.path
from pathlib import Path
import psutil
import socket
import subprocess

if platform.system() == "Windows":
    import pygetwindow as gw
    import win32gui
    import win32process

    user32 = ctypes.windll.user32
elif platform.system() == "Linux":
    import prefixmanager
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

current_version = "0.3alpha"

def _enum_osu_windows():
    if platform.system() == "Windows":
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
    elif platform.system() == "Linux":
        daemon = prefixmanager.open_wine_process("G:\\titledaemon.exe", True)
        while True:
            line = daemon.stdout.readline()
            if not line:
                continue
            if b"Waiting for client on port" in line:
                break
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 55345))
        dataret = []
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            dataret.append(data.decode('utf-8'))
        return dataret

def is_osu_updater_present():
    if platform.system() == "Windows":
        for hwnd, pid, title, classname in _enum_osu_windows():
            lt = title.lower()
            if "updater" in lt:
                return True
        return False
    elif platform.system() == "Linux":
        for winname in _enum_osu_windows():
            if "updater" in winname.lower():
                return True
        return False
def is_osu_loading_window_present():
    if platform.system() == "Windows":
        for hwnd, pid, title, classname in _enum_osu_windows():
            lt = title.lower()
            if "(loading)" in lt:
                return True
        return False
    elif platform.system() == "Linux":
        for winname in _enum_osu_windows():
            if "(loading)" in winname.lower():
                return True
        return False
def is_osu_main_window_present():
    if platform.system() == "Windows":
        for hwnd, pid, title, classname in _enum_osu_windows():
            lt = title.lower()
            lc = classname.lower()
            if "updater" not in lt and "(loading)" not in lt:
                if lc == "osu!" or lt.startswith("osu!"):
                    return True
        return False
    elif platform.system() == "Linux":
        for winname in _enum_osu_windows():
            if "updater" not in winname.lower() and "(loading)" not in winname.lower():
                if winname.lower() == "osu!" or winname.lower().startswith("osu!"):
                    return True
        return False

def win_message_box(message: str, title: str, style: int) -> int:
    system = platform.system()

    if system == "Linux":
        btn = style & 0xF
        ico = style & (MB_ICONERROR | MB_ICONWARNING | MB_ICONINFORMATION)

        if btn == MB_OK:
            if ico == MB_ICONERROR:
                subprocess.run(['zenity', '--error', '--title', title, '--text', message])
            elif ico == MB_ICONWARNING:
                subprocess.run(['zenity', '--warning', '--title', title, '--text', message])
            else:
                subprocess.run(['zenity', '--info', '--title', title, '--text', message])
            return IDOK

        elif btn == MB_OKCANCEL:
            raise Exception("MB_OKCANCEL not implemented")

        elif btn == MB_YESNO:
            ret = subprocess.run(['zenity', '--question', '--title', title, '--text', message]).returncode
            return IDYES if ret == 0 else IDNO

        else:
            subprocess.run(['zenity', '--info', '--title', title, '--text', message])
            return IDOK

    elif system == "Windows":
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        return ctypes.windll.user32.MessageBoxW(hwnd, message, title, style)

    else:
        raise Exception("Unsupported OS")

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

def linux_poll(process):
    try:
        if process.is_running():
            return None
        else:
            return process.wait()
    except psutil.NoSuchProcess:
        return -1
    except psutil.ZombieProcess:
        return None
