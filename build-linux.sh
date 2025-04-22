rm -r dist
rm -r build
nicegui-pack --windowed --icon "src/icon.ico" --name "m1pplauncher" --add-data "src/icon.ico:." --add-data "src/titledaemon.exe:." "src/main.py"
