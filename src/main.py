import os
import sys
import asyncio
import subprocess
import platform
import ctypes
import webbrowser
from pathlib import Path
import psutil
import nicegui as ng
from nicegui import app, ui
import configmanager
import util
import requests
import atexit
import bootstrapper
import time
import logging
import re

if platform.system() == "Linux":
    import prefixmanager

if platform.system() == "Windows":
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] -> %(message)s',
        handlers=[
            logging.handlers.TimedRotatingFileHandler(os.path.join(os.getenv('LOCALAPPDATA'), 'm1pplauncher-log'), when='midnight'),
            logging.StreamHandler()
        ]
    )
elif platform.system() == "Linux":
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] -> %(message)s',
        handlers=[
            logging.handlers.TimedRotatingFileHandler(os.path.expanduser("~/.local/share/osu-m1pp") + "m1pplauncher-log", when='midnight'),
            logging.StreamHandler()
        ]
    )
    app.native.start_args['gui'] = "cef"

app.middleware_stack = None
app.native.window_args['resizable'] = False

task = None

can_edit_settings = False


def validate_config():
    if platform.system() == "Linux":
        try:
            prefixmanager.kill_wineserver()
        except:
            pass
    util.check_for_updates()
    if not configmanager.ensure_config_file():
        response = util.win_message_box(
            'Your configuration file is either corrupted or inaccessible to the launcher. Do you want to correct this error?',
            'Configuration file error',
            util.MB_YESNO
        )
        if response != 7:
            try:
                os.remove(configmanager.CONFIG_FILE)
                if not configmanager.ensure_config_file():
                    util.win_message_box(
                        'We were unable to fix the error. Please contact support and provide the following information:\n\nRecreated config is invalid.',
                        'Unable to fix',
                        util.MB_OK
                    )
                    sys.exit()
            except Exception as err:
                util.win_message_box(
                    f'We were unable to fix the error. Please contact support and provide the following information:\n\n{err}',
                    'Unable to fix',
                    util.MB_OK
                )
                sys.exit()
        else:
            sys.exit()
    selected_server = configmanager.get_config_value("selected_server").lower()

    if selected_server == "ppy.sh":
        util.win_message_box(
            "We have detected that you modified the launcher config manually in order to connect to the official Bancho servers. "
            "We disallow this to keep your account safe. Mods used here inject directly into the osu! process or even modify the game files. "
            "Such actions are likely to trigger an autoban on Bancho.",
            'WARNING',
            util.MB_OK
        )
        sys.exit()
    if selected_server not in {"m1pposu.dev", "4ayosu.ovh"}:
        util.win_message_box(
            "We have detected that you modified the launcher config manually in order to connect to unsupported servers. "
            "Using some mods included here might result in a ban when used outside M1PP & 4ayo. Proceed with caution.",
            'WARNING',
            util.MB_OK
        )
        return

app.on_startup(validate_config)


def cleanup():
    if platform.system() == "Windows":
        for p in psutil.process_iter(['pid','name']):
            name = (p.info['name'] or '').lower()
            if name in ('osu!.exe', 'tosu.exe', 'osu!.patcher.exe', 'tosu-overlay.exe'):
                try:
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
    elif platform.system() == "Linux":
        try:
            prefixmanager.kill_wineserver()
        except:
            pass

app.on_shutdown(cleanup)

def on_tab_change(event):
    global can_edit_settings
    global tab_block_html
    if event.value == 'a':
        launch_info_card.visible = configmanager.get_config_value("launch_info")
    if not can_edit_settings:
        tab_block_html = ui.html('''
            <style>
            .tb-sw-tg {
                pointer-events: none;
            }
            </style>
        ''')

def launch_handler(tabs, server_input, lbtn, progress_label):
    global task
    task = asyncio.create_task(launch_osu(tabs, server_input, lbtn, progress_label))

def set_window_visibility(title: str, visible: bool) -> bool:
    if platform.system() == "Windows":
        SW_HIDE = 0
        SW_SHOW = 5

        FindWindow = ctypes.windll.user32.FindWindowW
        ShowWindow = ctypes.windll.user32.ShowWindow

        hwnd = FindWindow(None, title)
        if hwnd:
            ShowWindow(hwnd, SW_SHOW if visible else SW_HIDE)
            return True
        else:
            return False
    else:
        logging.warning("set_window_visibility unimplemented")
        return True

def toggle_mod(name, value):
    global debug_mods
    configmanager.update_mod(name, value)
    debug_mods.set_text('Mods: {}'.format(configmanager.get_config_value("mods_enabled")))
    debug_mods.update()


async def launch_osu(tabs, server_input, lbtn, progress_label):
    logging.info("Starting osu!")
    try:
        logging.debug("Disabling launch button and freezing tabs")
        lbtn.disable()
        set_tab_change_state(tabs, server_input, False)

        configmanager.set_config_value("osu_path", bootstrapper.default_game_path)
        osu_path = bootstrapper.default_game_path
        logging.debug("Configured osu_path: %s", osu_path)
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        loadosu = True
        logging.debug("Entering launch loop")
        while loadosu:
            progress_label.set_text('Bootstrapping osu!... (this might take a long time)')
            pathdir = configmanager.get_config_value("osu_path")
            logging.info("Bootstrapping osu at %s", pathdir)
            res = await bootstrapper.async_bootstrap_osu(pathdir)
            logging.debug("Bootstrap result: %s", res)
            if res == 1:
                logging.info("Bootstrap cancelled (result code 1)")
                return

            progress_label.set_text('Launching osu!...')
            server = server_input.value
            logging.info("Launching osu!.exe with devserver %s", server)
            if platform.system() == "Windows":
                proc = subprocess.Popen(
                    [os.path.join(pathdir, "osu!.exe"),
                    "-devserver", server],
                    cwd=pathdir,
                    startupinfo=startupinfo
                )
            elif platform.system() == "Linux":
                proc = prefixmanager.open_wine_process(f"G:\\osu!.exe -devserver {server}")
            logging.debug("Started osu process with PID=%s", getattr(proc, 'pid', None))
            if configmanager.get_config_value("launcher_hide_startup"):
                logging.debug("Hiding M1PP Launcher window on startup")
                set_window_visibility("M1PP Launcher", False)

            tosu_injected = False
            rp_injected = False
            presentosu = False
            if platform.system() == "Windows":
                target = proc.poll()
            elif platform.system() == "Linux":
                oprocess = None
                while not oprocess:
                    for p in psutil.process_iter(['pid','name']):
                        if p.info['name'] and p.info['name'].lower() == 'osu!.exe':
                            cmd = open(f"/proc/{p.pid}/cmdline", 'r').read()
                            if "-devserver" in cmd:
                                oprocess = p
                                break
                target = util.linux_poll(oprocess)
            while target is None:
                if platform.system() == "Windows":
                    target = proc.poll()
                elif platform.system() == "Linux":
                    target = util.linux_poll(oprocess)
                try:
                    if platform.system() == "Windows":
                        process = None
                        for p in psutil.process_iter(['pid','name']):
                            if p.info['name'] and p.info['name'].lower() == 'osu!.exe':
                                process = p
                                break
                        if not process:
                            logging.warning("osu!.exe process not found, attempting retry loop")
                            timeout_start = time.time()
                            while (time.time() - timeout_start) < 4 and not process:
                                await asyncio.sleep(0.5)
                                for p in psutil.process_iter(['pid','name']):
                                    if p.info['name'] and p.info['name'].lower() == 'osu!.exe':
                                        process = p
                                        break
                            if not process:
                                logging.error("osu!.exe process still not found after timeout, restarting launch")
                                break
                    elif platform.system() == "Linux":
                        process = []
                        for p in psutil.process_iter(['pid','name']):
                            if p.info['name'] and p.info['name'].lower() == 'osu!.exe':
                                if not p in process:
                                    process.append(p)
                                    break
                        if process == []:
                            logging.warning("osu!.exe process not found, attempting retry loop")
                            timeout_start = time.time()
                            while (time.time() - timeout_start) < 1 and not process:
                                await asyncio.sleep(0.5)
                                for p in psutil.process_iter(['pid','name']):
                                    if p.info['name'] and p.info['name'].lower() == 'osu!.exe':
                                        if not p in process:
                                            process.append(p)
                                            break
                            if process == []:
                                if not presentosu:
                                    logging.error("osu!.exe process still not found after timeout, restarting launch")
                                    break
                                else:
                                    prefixmanager.kill_wineserver()
                                    logging.error("osu!.exe process still not found after timeout, killing wineserver")
                                    loadosu = False
                                    break

                    if process:
                        if platform.system() == "Windows":
                            cmd = process.cmdline()
                            if server_input.value not in cmd:
                                if not any(ext in cmd for ext in [".osk", ".osr", ".osu", ".osz", ".osb"]):
                                    logging.warning("Detected osu! update: server arg missing in command line %s", cmd)
                                    asyncio.to_thread(util.win_message_box,
                                        'osu! has updated. Please launch the game again.',
                                        'osu! update',
                                        util.MB_OK | util.MB_ICONINFORMATION
                                    )
                                    loadosu = False
                                    break
                        elif platform.system() == "Linux" and len(process) >= 1:
                            saferun = False
                            for processx in process:
                                cmdpid = processx.pid
                                cmd = open(f"/proc/{cmdpid}/cmdline", 'r').read()
                                logging.debug("Command line: %s", cmd)
                                if "-devserver" in cmd:
                                    saferun = True
                            if not saferun:
                                logging.warning("Detected osu! update: server arg missing in command line %s", cmd)
                                await asyncio.to_thread(util.win_message_box,
                                    'osu! has updated. Please launch the game again.',
                                    'osu! update',
                                    util.MB_OK | util.MB_ICONINFORMATION
                                )
                                loadosu = False
                                break

                    mods = configmanager.get_config_value("mods_enabled")
                    if "tosu" in mods and not tosu_injected:
                        logging.info("Injecting tosu.exe")
                        if platform.system() == "Windows":
                            subprocess.Popen(
                                [os.path.join(pathdir, "tosu.exe")],
                                cwd=pathdir,
                                startupinfo=startupinfo
                            )
                        elif platform.system() == "Linux":
                            cmdstr = "G:\\\\tosu.exe"

                            prefixmanager.open_wine_process(cmdstr)
                        tosu_injected = True
                    if "RelaxPatcher" in mods and not rp_injected:
                        logging.info("Injecting RelaxPatcher")
                        if platform.system() == "Windows":
                            patcher_proc = subprocess.Popen(
                                [os.path.join(pathdir, "relaxpatcher", "osu!.patcher.exe")],
                                cwd=pathdir,
                                startupinfo=startupinfo,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True
                            )
                        elif platform.system() == "Linux":

                            tasklist_proc = prefixmanager.open_wine_process("C:\\\\windows\\\\system32\\\\tasklist.exe", isoutput=True)
                            tasklist_output = tasklist_proc.stdout.read()
                            tasklist_proc.kill()
                            try:
                                dec = tasklist_output.decode("utf-8")
                            except:
                                dec = tasklist_output.decode("windows-1252")
                            for line in dec.splitlines():
                                if line.strip().startswith("osu!.exe"):
                                    match = re.search(r'osu!\.exe\s+(\d+)', line)
                                    if match:
                                        opid = int(match.group(1))

                            cmdstr = "G:\\\\relaxpatcher\\\\osu!.patcher.exe " + str(opid)

                            patcher_proc = prefixmanager.open_wine_process(cmdstr, isoutput=True)
                        try:
                            await asyncio.sleep(0.1)
                            out = await asyncio.wait_for(
                                asyncio.to_thread(patcher_proc.stdout.readline),
                                timeout=1.3
                            )
                            if platform.system() == "Linux":
                                out = out.decode("utf-8")
                            logging.debug("RelaxPatcher output: %s", out)
                            if out and "Written to " in out or "starting in the Windows directory" in out:
                                rp_injected = True
                            if "System.Exception" in out:
                                patcher_proc.kill()
                            if "install .NET" in out:
                                logging.error("RelaxPatcher error: %s", out)
                                util.win_message_box(
                                    'RelaxPatcher mod requires .NET 8.0.15, would you like to install it?\n\n(If you have it already installed, try restarting your PC)',
                                    'Mod error',
                                    util.MB_YESNO | util.MB_ICONERROR
                                )
                                if response == util.IDYES:
                                    webbrowser.open("https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/8.0.15/windowsdesktop-runtime-8.0.15-win-x64.exe")
                                loadosu = False
                                break
                        except Exception as e:
                            logging.error("Patch error: %s", e)
                    if util.is_osu_updater_present():
                        logging.warning("osu! auto‑updater still running; waiting for it to finish")
                    elif util.is_osu_loading_window_present():
                        logging.info("osu! loading stub detected; still booting")
                    elif util.is_osu_main_window_present():
                        logging.info("osu! main window detected")
                        presentosu = True
                    else:
                        logging.debug("no osu! windows found yet")
                    if presentosu:
                        if not util.is_osu_main_window_present():
                            if platform.system() == "Linux":
                                prefixmanager.kill_wineserver()
                            logging.error("Failed to detect osu! main window, killing wineserver")
                            loadosu = False
                            break

                except Exception as loop_err:
                    logging.exception("Error in launch monitoring loop")
                await asyncio.sleep(0.5)

            logging.debug("Launch loop exited, cleaning up processes")
            if platform.system() == "Windows":
                for p in psutil.process_iter(['pid','name']):
                    name = (p.info['name'] or '').lower()
                    if name in ('osu!.exe', 'tosu.exe', 'osu!.patcher.exe', 'tosu-overlay.exe'):
                        try:
                            logging.debug("Killing process PID=%d Name=%s", p.pid, p.info['name'])
                            p.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as kill_err:
                            logging.warning("Failed to kill process PID=%d: %s", p.pid, kill_err)
            elif platform.system() == "Linux":
                prefixmanager.kill_wineserver()
                logging.debug("Killing wineserver")
            if presentosu:
                loadosu = False

    except Exception as err:
        logging.exception(f"Unable to launch the game: {err}")
        util.win_message_box(
            f'We were unable to launch the game. Please contact support and provide the following information:\n\n{err}',
            'Unable to launch',
            util.MB_OK
        )
        loadosu = False

    finally:
        logging.debug("Re-enabling launch button and restoring UI state")
        lbtn.enable()
        progress_label.set_text('')
        set_tab_change_state(tabs, server_input, True)
        if platform.system() == "Linux":
            prefixmanager.kill_wineserver()
            logging.debug("Killing wineserver")
        if configmanager.get_config_value("launcher_hide_startup"):
            logging.debug("Restoring M1PP Launcher window visibility")
            set_window_visibility("M1PP Launcher", True)

def set_tab_change_state(tabs, server_input, state):
    if state:
        tabs.style("pointer-events: auto;")
        server_input.style("pointer-events: auto;")
    else:
        tabs.style("pointer-events: none;")
        server_input.style("pointer-events: none;")

@ui.page('/')
def main():
    ui.add_head_html('''
    <style>
        html, body {
            margin: 0;
            height: 100%;
            overflow: hidden;
        }

        .nicegui-content {
            height: 100% !important;
            overflow: hidden !important;
            display: flex;
            flex-direction: column;
        }

        .q-tab-panels, .q-tab-panel {
            flex-grow: 1;
            height: 100%;
            overflow: hidden;
        }

        @keyframes fadep {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .fade-animation {
            animation-timing-function: ease-in-out;
            opacity: 0;
        }
        .animate {
            animation: fadep 1s forwards;
        }
        /* --- TABS --- */
        .dark .q-tabs {
            background-color: transparent !important;
            border-bottom: 1px solid #333 !important;
        }

        .dark .q-tab {
            color: #aaa !important;
            background-color: transparent !important;
            transition: color 0.2s ease;
        }

        .dark .q-tab:hover {
            color: #ffc4ff !important;
        }

        .dark .q-tab--active {
            color: #ffc4ff !important;
            font-weight: 600;
            border-bottom: 2px solid #ffc4ff !important;
        }

        .dark .q-tab-panels {
            background-color: transparent !important;
        }
    </style>
    ''')
    ui.add_head_html('''
        <script>
        window.onload = () => {
            setTimeout(() => {
                const elw = document.querySelector('.fade-animation');
                const elements = document.querySelectorAll('.fade-animation');
                elements.forEach(el => {
                    el.classList.add('animate');

                });
                elw.addEventListener('animationend', () => {
                    elements.forEach(el => {
                        el.style.opacity = '1';
                        el.classList.remove('fade-animation');
                        el.classList.remove('animate');
                    });
                });
            }, 100);
        };
        </script>
    ''')
    ui.run_javascript("""
    document.addEventListener('keydown', function(event) {
        if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        }
    });
    """)
    if configmanager.get_config_value("dark_mode"):
        ui.dark_mode().enable()
    ui.colors(primary='#e4ade4', brand='#ffc4ff')
    ui.page_title('M1PP Launcher')
    with ui.tabs().classes('w-full fade-animation') as tabs:
        ui.tab('a', label='Home').classes('px-12')
        ui.tab('b', label='News').classes('px-12')
        ui.tab('c', label='Settings').classes('px-12')
        ui.tab('d', label='Runtime').classes('px-12')
        ui.tab('e', label='About').classes('px-12')
    with ui.tab_panels(tabs, value='a', on_change=on_tab_change).classes('w-full'):
        with ui.tab_panel('a').classes("overflow-hidden"):
            global progress_label
            global debug_mods
            global debug_server
            with ui.column().classes("h-96 w-full align-middle flex justify-center items-center overflow-hidden fade-animation"):
                server_input = ui.input(
                    label='Server Address',
                    value=configmanager.get_config_value("selected_server"),
                    validation={'Please enter a valid server address': lambda value: len(value) > 0}
                ).classes('w-64')

                def on_server_change():
                    configmanager.set_config_value("selected_server", server_input.value)
                    debug_server.set_text('Server: {}'.format(server_input.value))

                server_input.on('blur', on_server_change)

                lbtn = ui.button('Launch', on_click=lambda: launch_handler(tabs, server_input, lbtn, progress_label)).classes('px-12 mt-7')
                progress_label = ui.label('')

                global launch_info_card
                with ui.card().classes('w-full max-w-lg p-6 items-center gap-0 overflow-hidden') as launch_info_card:
                    ui.label('Launch info').classes('text-l font-bold gap-2')
                    ui.label('Installation: Separate')
                    ui.label('Platform: {}'.format(platform.system()))
                    debug_mods = ui.label('Mods: {}'.format(configmanager.get_config_value("mods_enabled")))
                    debug_server = ui.label('Server: {}'.format(configmanager.get_config_value("selected_server")))
        with ui.tab_panel('b'):
            with ui.column().classes("h-full w-full align-middle flex justify-center items-center"):
                ui.label('Latest News').classes('text-xl font-bold')
                with ui.scroll_area().classes('space-y-0 py-0 w-full h-80 overflow-hidden'):
                    with ui.column().classes('flex-grow w-full items-center justify-center'):
                        for news in requests.get("https://launcher.m1pposu.dev/news.json").json():
                            with ui.card().classes('w-full max-w-lg p-4'):
                                ui.label(news["title"]).classes('text-xl font-bold gap-2')
                                ui.label(news["content"])
                                ui.button(news["button"], on_click=lambda: webbrowser.open(news["button_link"]))
        with ui.tab_panel('c'):
            value1 = configmanager.get_config_value("launcher_hide_startup")
            value2 = configmanager.get_config_value("launch_info")
            value3 = configmanager.get_config_value("animations")
            value4 = configmanager.get_config_value("dark_mode")

            ui.label('General').classes('text-xl font-bold gap-2')
            if platform.system() == "Windows":
                ui.switch('Hide launcher on game startup', value=configmanager.get_config_value("launcher_hide_startup"), on_change=lambda e: configmanager.set_config_value("launcher_hide_startup", e.sender.value))
            ui.switch('Show launch info', value=configmanager.get_config_value("launch_info"), on_change=lambda e: (configmanager.set_config_value("launch_info", e.sender.value)))
            # ui.switch('Play animations', value=configmanager.get_config_value("animations"), on_change=lambda e: configmanager.set_config_value("animations", e.sender.value))
            ui.switch('Dark mode', value=value4, on_change=lambda e: (ui.run_javascript('location.reload();'), configmanager.set_config_value("dark_mode", e.value), ui.run_javascript('location.reload();')))

        with ui.tab_panel('d').classes("overflow-hidden"):
            mods_enabled = configmanager.get_config_value("mods_enabled")

            ui.label('Mods').classes('text-xl font-bold gap-2')
            ui.switch('RelaxPatcher (rushiiMachine)', value="RelaxPatcher" in mods_enabled, on_change=lambda e: toggle_mod("RelaxPatcher", e.sender.value))
            ui.switch('tosu (tosu contributors)', value="tosu" in mods_enabled, on_change=lambda e: toggle_mod("tosu", e.sender.value))
            ui.switch('AssetPatcher (M1PP)', value="AssetPatcher" in mods_enabled, on_change=lambda e: toggle_mod("AssetPatcher", e.sender.value))
            ui.label('Game enviroment').classes('text-xl font-bold gap-2')
            ui.switch('Separate osu! install (Required for now)', value=True).props('disable')

        with ui.tab_panel('e').classes("overflow-hidden"):
            with ui.scroll_area().classes('space-y-0 py-0 w-full h-96 overflow-hidden'):
                with ui.column().classes('h-full w-full items-center justify-center'):

                    with ui.card().classes('w-96 shadow-lg'):
                        ui.label('M1PP Launcher Source Code').classes('text-xl font-semibold')
                        ui.label('The source code of this launcher').classes('text-sm text-gray-500')
                        ui.button('GitHub', icon='code', on_click=lambda: webbrowser.open("https://github.com/M1PPosuDEV/m1pplauncher")) \
                            .classes('bg-blue-500 hover:bg-blue-600 text-white rounded-full px-4 py-2')

                    with ui.card().classes('w-96 shadow-lg'):
                        ui.label('M1PP/4ayo Discord').classes('text-xl font-semibold')
                        ui.label('Join our Discord server to share your plays, chat with others, report bugs, and suggest improvements!').classes('text-sm text-gray-500')
                        ui.button('Discord', icon='discord', on_click=lambda: webbrowser.open("https://dsc.gg/m1ppand4ayo")) \
                            .classes('bg-purple-500 hover:bg-purple-600 text-white rounded-full px-4 py-2')
                    with ui.card().classes('w-96 shadow-lg'):
                        ui.label('tosu GitHub').classes('text-xl font-semibold')
                        ui.label('Memory reader and PP counters provider for osu! and osu! Lazer') \
                            .classes('text-sm text-gray-500')
                        ui.button('GitHub', icon='extension', on_click=lambda: webbrowser.open("https://github.com/tosuapp/tosu")) \
                            .classes('text-white rounded-full px-4 py-2')
                    with ui.card().classes('w-96 shadow-lg'):
                        ui.label('osu-patcher Github (fork)').classes('text-xl font-semibold')
                        ui.label('osu!stable patcher for adding extra features') \
                            .classes('text-sm text-gray-500')
                        ui.button('GitHub', icon='extension', on_click=lambda: webbrowser.open("https://github.com/rushiiMachine/osu-patcher")) \
                            .classes('text-white rounded-full px-4 py-2')


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(native=True, window_size=(970, 530), fullscreen=False, reload=False, title='M1PP Launcher', favicon=util.resource_path("icon.ico"), reconnect_timeout=99999, port=64821)