import sys, os
import ctypes
import psutil
import webbrowser
import requests
import os.path
from pathlib import Path

current_version = "0.1alpha"

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