import os
from pathlib import Path
import asyncio
import aiohttp
import aiofiles
import aiofiles.os
import configmanager
import assetpatcher
import zipfile
import requests
import tempfile
import ctypes
import util
import crossfiledialog


kdll = ctypes.windll.LoadLibrary("kernel32.dll")

async def open_file_dialog(game_path):
    directory = os.path.join(os.getenv('LOCALAPPDATA'), 'osu!')
    if not os.path.isfile(os.path.join(directory, "osu!.exe")):
        await asyncio.to_thread(
            util.win_message_box,
            'We couldn\'t locate your osu! folder.\n\nPlease select the folder where osu! is installed.\n\nWe will create symbolic links to the Songs and Skins folders in order to make your experience better.',
            'Information',
            util.MB_OK | util.MB_ICONINFORMATION
        )

        directory = await asyncio.to_thread(
            crossfiledialog.choose_folder,
            title="Select the osu! installation folder",
        )

    osu_exe_path = os.path.join(directory, "osu!.exe")
    if directory and os.path.isfile(osu_exe_path):
        try:
            response = await asyncio.to_thread(
                util.win_message_box,
                'Windows requires admin permissions to create symbolic links.\n\nWe will ask for admin now, so we can create the links.',
                'Information',
                util.MB_OK | util.MB_ICONINFORMATION
            )
            if response == util.IDYES:
                songs_link = str(os.path.join(game_path, "Songs"))
                songs_target = str(os.path.join(directory, "Songs"))
                skins_link = str(os.path.join(game_path, "Skins"))
                skins_target = str(os.path.join(directory, "Skins"))
                db_link = str(os.path.join(game_path, "osu!.db"))
                db_target = str(os.path.join(directory, "osu!.db"))
                cmd_combined = f'mklink /D "{songs_link}" "{songs_target}" && mklink /D "{skins_link}" "{skins_target}" && mklink "{db_link}" "{db_target}"'
                print(cmd_combined)
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "cmd.exe", f'/c "{cmd_combined}"', None, 0
                )
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

config_path = os.path.join(os.getenv('LOCALAPPDATA'), 'm1pplauncher-config.json')
default_game_path = os.path.join(Path.home(), r'AppData\Local\osu!m1pp')

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
    os.makedirs(destination_folder, exist_ok=True)
    if not os.path.isfile(os.path.join(destination_folder, "osu!.exe")):
        try:
            await download_osu_files(destination_folder)
            chk = await open_file_dialog(destination_folder)
            if chk == 1:
                return 1
        except InstallError as e:
            raise InstallError("Failed to download osu! files") from e

    osu_asset_array = ["menu-osu@2x", "menu-osu"]
    asset_endpoint = "https://assets.m1pposu.dev/launcher/m1pp/"

    with tempfile.TemporaryDirectory() as tmpdir:
        async with aiohttp.ClientSession() as session:
            for asset in osu_asset_array:
                asset_url = asset_endpoint + asset + ".png"
                async with session.get(asset_url) as resp:
                    asset_content = await resp.read()
                tmp_asset_path = os.path.join(tmpdir, asset + ".png")
                async with aiofiles.open(tmp_asset_path, 'wb') as f:
                    await f.write(asset_content)

        enabled_mods = await asyncio.to_thread(configmanager.get_config_value, "mods_enabled")
        if "AssetPatcher" in enabled_mods:
            target_dll = os.path.join(destination_folder, "osu!ui.dll")
            output_temp = os.path.join(destination_folder, "osu!ui.temp")
            
            await asyncio.to_thread(
                assetpatcher.patch_assets,
                target_dll=target_dll,
                asset_array=["menu-osu@2x", "menu-osu"],
                asset_src_folder=tmpdir,
                output_path=output_temp
            )
            old_dll_path = os.path.join(destination_folder, "osu!ui.dll")
            await asyncio.to_thread(os.remove, old_dll_path)
            await asyncio.to_thread(os.rename, output_temp, old_dll_path)
        else:
            update_data = requests.get(update_data_endpoint).json()
            async with aiohttp.ClientSession() as session:
                for file in update_data:
                    if file["filename"] == "osu!ui.dll":
                        os.remove(os.path.join(destination_folder, "osu!ui.dll"))
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

        if "tosu" in enabled_mods:
            if not os.path.exists(os.path.join(destination_folder, "tosu.exe")):
                await download_and_extract(
                    "https://github.com/tosuapp/tosu/releases/download/v4.4.3/tosu-windows-v4.4.3.zip",
                    "tosu.zip",
                    destination_folder,
                    tmpdir
                )

        if "RelaxPatcher" in enabled_mods:
            if not os.path.exists(os.path.join(destination_folder, "relaxpatcher", "osu!.patcher.exe")):
                await download_and_extract(
                    "https://github.com/4ayo-ovh/osu-patcher/releases/download/Slim/relaxpatcher.zip",
                    "relaxpatcher.zip",
                    destination_folder,
                    tmpdir
                )

        
        
if __name__ == "__main__":
    asyncio.run(async_bootstrap_osu(default_game_path))