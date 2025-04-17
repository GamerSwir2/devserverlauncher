;--------------------------------
; Head
;--------------------------------

!include "MUI2.nsh"
!include "nsDialogs.nsh"

;--------------------------------
; General Installer Settings
;--------------------------------
Name "M1PP Launcher"
OutFile "m1pplauncher-setup.exe"
InstallDir "$PROGRAMFILES\M1PPLauncher"
InstallDirRegKey HKLM "Software\M1PP Launcher" "InstallDir"
Icon "icon.ico"
UninstallIcon "icon.ico"
SetCompressor /SOLID lzma
BrandingText " "
RequestExecutionLevel admin

;--------------------------------
; Pages
;--------------------------------
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "banner.bmp"
!define MUI_ICON "icon.ico"
!insertmacro MUI_PAGE_DIRECTORY
; !insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
Page Custom RemoveOldDataPageCreate RemoveOldDataPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES


;--------------------------------
; Variables
;--------------------------------
Var RemoveOldData
Var OldDataCheckbox

;--------------------------------
; Custom Page Functions
;--------------------------------
Function RemoveOldDataPageCreate
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
        Abort
    ${EndIf}
    ${NSD_CreateCheckbox} 20u 20u 200u 12u "Remove osu!m1pp data (Separate from your main osu! installation)"
    Pop $OldDataCheckbox
    nsDialogs::Show
FunctionEnd

Function RemoveOldDataPageLeave
    ${NSD_GetState} $OldDataCheckbox $RemoveOldData
FunctionEnd

;--------------------------------
; Main Installation Section
;--------------------------------
Section "Install M1PP Launcher" SEC01
    SetOutPath "$INSTDIR"
    SetRegView 64
    StrCmp $RemoveOldData "1" remove_old_data skip_remove_old_data
remove_old_data:
    nsExec::Exec '"cmd.exe /c del "$LOCALAPPDATA\osu!m1pp\osu!.db"'
    nsExec::Exec '"cmd.exe /c rmdir "$LOCALAPPDATA\osu!m1pp\Songs"'
    nsExec::Exec '"cmd.exe /c rmdir "$LOCALAPPDATA\osu!m1pp\Skins"'
    RMDir /r "$LOCALAPPDATA\osu!m1pp"
    Delete "$LOCALAPPDATA\m1pposu_config.json"
skip_remove_old_data:
    SetRegView 64
    File "dist\m1pplauncher\m1pplauncher.exe"
    SetOutPath "$INSTDIR\_internal"
    File /r "dist\m1pplauncher\_internal\*.*"
    CreateShortCut "$DESKTOP\M1PP Launcher.lnk" "$INSTDIR\m1pplauncher.exe"
    CreateDirectory "$SMPROGRAMS\M1PP Launcher"
    CreateShortCut "$SMPROGRAMS\M1PP Launcher\M1PP Launcher.lnk" "$INSTDIR\m1pplauncher.exe"
    WriteRegStr HKLM "Software\M1PP Launcher" "InstallDir" "$INSTDIR"
    
    WriteUninstaller "$INSTDIR\uninstall.exe"

    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher" "DisplayName" "M1PP Launcher"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher" "DisplayIcon" "$INSTDIR\m1pplauncher.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher" "Publisher" "YourPublisherName"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher" "NoRepair" 1
SectionEnd

;--------------------------------
; Uninstallation Section
;--------------------------------
Section "Uninstall"
    SetRegView 64
    Delete "$INSTDIR\m1pplauncher.exe"
    RMDir /r "$INSTDIR\_internal"
    Delete "$DESKTOP\M1PP Launcher.lnk"
    Delete "$SMPROGRAMS\M1PP Launcher\M1PP Launcher.lnk"
    DeleteRegKey HKLM "Software\M1PP Launcher"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\M1PP Launcher"
    RMDir "$INSTDIR"
    RMDir "$SMPROGRAMS\M1PP Launcher"
SectionEnd

;--------------------------------
; MUI Settings
;--------------------------------
!insertmacro MUI_LANGUAGE "English"
