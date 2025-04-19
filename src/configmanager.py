import os
import json
import util
from pathlib import Path

CONFIG_FILE = os.path.join(os.getenv('LOCALAPPDATA'), 'm1pposu_config.json')

def ensure_config_file():
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w") as f:
                default_config = {
                    "launcher_hide_startup": True,
                    "launch_info": True,
                    "animations": True,
                    "selected_server": "m1pposu.dev",
                    "osu_path": "",
                    "dark_mode": False,
                    "mods_enabled": ["RelaxPatcher", "tosu", "AssetPatcher"]
                }
                f.write(json.dumps(default_config, indent=4))
            return True
        except:
            return False
    else:
        try:
            config = load_config()
            launcher_hide_startup = get_config_value("launcher_hide_startup")
            launch_info = get_config_value("launch_info")
            animations = get_config_value("animations")
            mods_enabled = get_config_value("mods_enabled")

            if (
                isinstance(config.get("launcher_hide_startup"), bool)
                and isinstance(config.get("launch_info"), bool)
                and isinstance(config.get("animations"), bool)
                and isinstance(config.get("selected_server"), str)
                and isinstance(config.get("osu_path"), str)
                and isinstance(config.get("dark_mode"), bool)
                and isinstance(config.get("mods_enabled"), list)
            ):
                return True
            else:
                return False
        except:
            return False
def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def get_config_value(key, default=None):
    config = load_config()
    return config.get(key, default)

def set_config_value(key, value):
    config = load_config()
    config[key] = value
    save_config(config)
def update_mod(mod_name, state):
    mods_enabled = get_config_value("mods_enabled")

    if state:
        if mod_name not in mods_enabled:
            mods_enabled.append(mod_name)
    else:
        if mod_name in mods_enabled:
            mods_enabled.remove(mod_name)
    set_config_value("mods_enabled", mods_enabled)
if __name__ == "__main__":
    ensure_config_file()

