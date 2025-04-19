rm -r dist
rm -r build
nicegui-pack --windowed --icon "src/icon.ico" --name "m1pplauncher" --add-data "src/icon.ico;." --add-data "src/Mono.Cecil.dll;." "src/main.py"
