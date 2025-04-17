@echo off

rd /s /q "dist" > nul
rd /s /q "build" > nul
nicegui-pack --windowed --icon "src/icon.ico" --name "m1pplauncher" --add-data "src/icon.ico;." --add-data "src/Mono.Cecil.dll;." "src/main.py"
