import asyncio
import tempfile
import tarfile
import os
import stat
import aiohttp
import aiofiles
import shutil
import subprocess
import shlex
import util

WINEDL = "https://github.com/NelloKudo/WineBuilder/releases/download/wine-osu-staging-10.5-1/wine-osu-winello-fonts-wow64-10.5-1-x86_64.tar.xz"
WINETRICKS = "https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks"
PREFIXDL = "https://github.com/NelloKudo/osu-winello/releases/download/winello-bins/osu-winello-prefix.tar.xz"

default_location = os.path.join(os.getenv("HOME"), ".local", "share", "osu-m1pp")

envx={
    "WINEDLLOVERRIDES": "winemenubuilder.exe=;",
    "WINENTSYNC": "1",
    "WINEFSYNC": "1",
    "WINEESYNC": "1",
    "WINEPREFIX": os.path.expanduser("~/.local/share/osu-m1pp/osu-prefix"),
    "WINE": os.path.expanduser("~/.local/share/osu-m1pp/wine-osu/bin/wine"),
    "XDG_CACHE_HOME": os.path.expanduser("~/.local/share/osu-m1pp/cache"),
    "WINE_INSTALL_PATH": os.path.expanduser("~/.local/share/osu-m1pp/wine-osu"),
    "WINESERVER": os.path.expanduser("~/.local/share/osu-m1pp/wine-osu/bin/wineserver"),
    "LC_ALL": "en_US.UTF-8",
    "LANG": "en_US.UTF-8"
}

def _extract_tar_xz(archive_path, extract_to):
    with tarfile.open(archive_path, "r:xz") as tar_ref:
        tar_ref.extractall(extract_to)

async def async_extract_tar_xz(archive_path, extract_to):
    await asyncio.to_thread(_extract_tar_xz, archive_path, extract_to)

async def download_and_extract_tar(url: str, archive_name: str, extract_to: str, tmpdir: str):
    archive_path = os.path.join(tmpdir, archive_name)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            content = await resp.read()
    async with aiofiles.open(archive_path, "wb") as f:
        await f.write(content)
    await async_extract_tar_xz(archive_path, extract_to)

async def setup_prefix(destination_folder):
    if not os.path.exists(os.path.join(destination_folder, "wine-osu")):
        for name in ["wine-osu", "osu-prefix", "winetricks", "cache"]:
            target = os.path.join(destination_folder, name)
            try:
                if os.path.isdir(target):
                    shutil.rmtree(target)
                elif os.path.isfile(target):
                    os.remove(target)
            except:
                pass
        os.makedirs(destination_folder, exist_ok=True)
        os.makedirs(os.path.join(destination_folder, "cache"), exist_ok=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            await download_and_extract_tar(WINEDL, "wine.tar.xz", destination_folder, tmpdir)
            await download_and_extract_tar(PREFIXDL, "osu-winello-prefix.tar.xz", destination_folder, tmpdir)
            with open(os.path.join(destination_folder, "winetricks"), "wb") as f:
                async with aiohttp.ClientSession() as session:
                    async with session.get(WINETRICKS) as resp:
                        content = await resp.read()
                    f.write(content)
            st = os.stat(os.path.join(destination_folder, "winetricks"))
            os.chmod(os.path.join(destination_folder, "winetricks"), st.st_mode | stat.S_IEXEC)
            
            wine_env = os.environ.copy()
            wine_env.update(envx)

            process = await asyncio.create_subprocess_exec(
                os.path.join(destination_folder, "winetricks"), "-q",
                "nocrashdialog", "autostart_winedbg=disabled",
                "dotnet48", "dotnet20", "gdiplus_winxp", "meiryo", "win10", "dotnet8",
                env=wine_env
            )
            await process.wait()

            

def open_wine_process(process, isoutput=False):
    process_args = shlex.split(process)

    wine_env = os.environ.copy()
    wine_env["WINEPREFIX"] = envx["WINEPREFIX"]
    wine_env["WINEDEBUG"] = "-all"

    process_args = [envx["WINE"]] + process_args
    if isoutput:
        process = subprocess.Popen(
            process_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=wine_env
        )
    else:
        process = subprocess.Popen(
            process_args,
            env=wine_env
        )
    return process

def kill_wineserver():
    wine_env = os.environ.copy()
    wine_env["WINEPREFIX"] = envx["WINEPREFIX"]
    wine_env["WINEDEBUG"] = "-all"
    

    process_args = [envx["WINE"] + "server", "--kill"] 
    process = subprocess.Popen(
        process_args,
        env=wine_env
    )
    return process

if __name__ == "__main__":
    asyncio.run(setup_prefix(default_location))
