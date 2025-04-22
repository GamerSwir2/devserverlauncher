import platform
import os
from pathlib import Path
import asyncio
import aiohttp
import aiofiles
import aiofiles.os
import configmanager
import zipfile
import requests
import tempfile
import ctypes
import util
import crossfiledialog
import shutil

if platform.system() == "Windows":
    kdll = ctypes.windll.LoadLibrary("kernel32.dll")
elif platform.system() == "Linux":
    import prefixmanager

async def open_file_dialog(game_path):
    if platform.system() == "Windows":
        directory = os.path.join(os.getenv('LOCALAPPDATA'), 'osu!')
    elif platform.system() == "Linux":
        directory = os.path.expanduser("~/.local/share/osu-wine/osu!")
    if not os.path.isfile(os.path.join(directory, "osu!.exe")):
        await asyncio.to_thread(
            util.win_message_box,
            'We couldn\'t locate your osu! folder.\n\nPlease select the folder where osu! is installed.\n\nWe will create symbolic links to the Songs and Skins folders in order to make your experience better.',
            'Information',
            util.MB_OK | util.MB_ICONINFORMATION
        )

        directory = await asyncio.to_thread(
            crossfiledialog.choose_folder,
            title="Select your existing osu! folder",
        )

    osu_exe_path = os.path.join(directory, "osu!.exe")
    if directory and os.path.isfile(osu_exe_path):
        try:
            songs_link = str(os.path.join(game_path, "Songs"))
            songs_target = str(os.path.join(directory, "Songs"))
            skins_link = str(os.path.join(game_path, "Skins"))
            skins_target = str(os.path.join(directory, "Skins"))
            db_link = str(os.path.join(game_path, "osu!.db"))
            db_target = str(os.path.join(directory, "osu!.db"))
            if platform.system() == "Windows":
                response = await asyncio.to_thread(
                    util.win_message_box,
                    'Windows requires admin permissions to create symbolic links.\n\nWe will ask for admin now, so we can create the links.',
                    'Information',
                    util.MB_OK | util.MB_ICONINFORMATION
                )
                cmd_combined = f'mklink /D "{songs_link}" "{songs_target}" && mklink /D "{skins_link}" "{skins_target}" && mklink "{db_link}" "{db_target}"'
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "cmd.exe", f'/c "{cmd_combined}"', None, 0
                )
            elif platform.system() == "Linux":
                os.symlink(songs_target, songs_link)
                os.symlink(skins_target, skins_link)
                os.symlink(db_target, db_link)
        except Exception as e:
            await asyncio.to_thread(
                util.win_message_box,
                f"Failed to create symbolic links: {e}",
                "Error",
                util.MB_OK | util.MB_ICONERROR
            )
            return 1
    else:
        await asyncio.to_thread(
            util.win_message_box,
            'osu! executable not found in the selected folder.\nPlease select a valid osu! installation folder.',
            'Error',
            util.MB_OK | util.MB_ICONERROR
        )
        return 1

    return 0

if platform.system() == "Windows":
    config_path = configmanager.CONFIG_FILE
    default_game_path = os.path.join(Path.home(), r'AppData\Local\osu!m1pp')
if platform.system() == "Linux":
    config_path = configmanager.CONFIG_FILE
    default_game_path = os.path.join(os.getenv("HOME"), ".local", "share", "osu-m1pp", "osu!m1pp")

update_data_endpoint = "https://osu.ppy.sh/web/check-updates.php?action=check&stream=Stable40"

def _unzip_file(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

async def async_unzip(zip_path, extract_to):
    await asyncio.to_thread(_unzip_file, zip_path, extract_to)

async def download_and_extract(url: str, zip_name: str, extract_to: str, tmpdir: str):
    zip_path = os.path.join(tmpdir, zip_name)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.read()
    async with aiofiles.open(zip_path, "wb") as f:
        await f.write(content)
    await async_unzip(zip_path, extract_to)

class InstallError(Exception):
    def __init__(self, message, inner_exception=None):
        super().__init__(message)
        self.inner_exception = inner_exception

async def download_osu_files(destination_folder):
    update_data = requests.get(update_data_endpoint).json()
    async with aiohttp.ClientSession() as session:
        for file in update_data:
            total_bytes = 0
            chunk_size = 1024
            url = file["url_full"]
            destination_file = os.path.join(destination_folder, file["filename"])
            async with session.get(url) as response:
                async with aiofiles.open(destination_file, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        if chunk:
                            try:
                                await f.write(chunk)
                            except Exception as e:
                                raise InstallError(f"Failed to write chunk for {file['filename']}") from e

async def async_bootstrap_osu(destination_folder):
    if platform.system() == "Linux":
        await prefixmanager.setup_prefix(os.path.join(os.getenv("HOME"), ".local", "share", "osu-m1pp"))
    os.makedirs(destination_folder, exist_ok=True)
    if not os.path.isfile(os.path.join(destination_folder, "osu!.exe")):
        try:
            await download_osu_files(destination_folder)
            chk = await open_file_dialog(destination_folder)
            if chk == 1:
                raise InstallError("Could not create symlinks")
        except InstallError as e:
            raise InstallError("Failed to download osu! files") from e

        if "tosu" in enabled_mods:
            if not os.path.exists(os.path.join(destination_folder, "tosu.exe")):
                await download_and_extract(
                    "https://github.com/tosuapp/tosu/releases/download/v4.4.3/tosu-windows-v4.4.3.zip",
                    "tosu.zip",
                    destination_folder,
                    tmpdir
                )
                if not os.path.exists(os.path.join(destination_folder, "tosu.env")):
                    with open(os.path.join(destination_folder, "tosu.env"), "w") as f:
                        f.write(requests.get("https://raw.githubusercontent.com/4ayo-ovh/tosu/refs/heads/master/tosu.env").text)
                

        if "RelaxPatcher" in enabled_mods:
            if not os.path.exists(os.path.join(destination_folder, "relaxpatcher", "osu!.patcher.exe")):
                if platform.system() == "Windows":
                    await download_and_extract(
                        "https://github.com/4ayo-ovh/osu-patcher/releases/latest/download/relaxpatcher.zip",
                        "relaxpatcher.zip",
                        destination_folder,
                        tmpdir
                    )
                elif platform.system() == "Linux":
                    await download_and_extract(
                        "https://github.com/4ayo-ovh/osu-patcher-linux/releases/latest/download/relaxpatcher.zip",
                        "relaxpatcher.zip",
                        destination_folder,
                        tmpdir
                    )
        if platform.system() == "Linux":
            try:
                os.symlink(os.path.join(prefixmanager.default_location, "osu!m1pp"), os.path.join(prefixmanager.default_location, "osu-prefix", "dosdevices", "g:"))
            except:
                pass
            shutil.copyfile(
                util.resource_path("titledaemon.exe"),
                os.path.join(destination_folder, "titledaemon.exe")
            )
if __name__ == "__main__":
    configmanager.ensure_config_file()
    asyncio.run(async_bootstrap_osu(default_game_path))
