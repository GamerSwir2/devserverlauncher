@echo off

rd /s /q "dist"
rd /s /q "build"
nicegui-pack --windowed --icon "src/icon.ico" --name "m1pplauncher" --add-data "src/icon.ico;." --add-data "src/Mono.Cecil.dll;." "src/main.py"
