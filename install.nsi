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
Icon "src\icon.ico"
UninstallIcon "src\icon.ico"
RequestExecutionLevel admin

;--------------------------------
; Pages
;--------------------------------
!insertmacro MUI_PAGE_DIRECTORY
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

    StrCmp $RemoveOldData "1" remove_old_data skip_remove_old_data
remove_old_data:
    RMDir /r "$LOCALAPPDATA\osu!m1pp"
    Delete "$LOCALAPPDATA\m1pposu_config.json"
skip_remove_old_data:

    File "dist\m1pplauncher\m1pplauncher.exe"
    SetOutPath "$INSTDIR\_internal"
    File /r "dist\m1pplauncher\_internal\*.*"
    CreateShortCut "$DESKTOP\M1PP Launcher.lnk" "$INSTDIR\m1pplauncher.exe"
    CreateDirectory "$SMPROGRAMS\M1PP Launcher"
    CreateShortCut "$SMPROGRAMS\M1PP Launcher\M1PP Launcher.lnk" "$INSTDIR\m1pplauncher.exe"
    WriteRegStr HKLM "Software\M1PP Launcher" "InstallDir" "$INSTDIR"
    
    ; Write the uninstaller executable so that the uninstallation section can be run later.
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

;--------------------------------
; Uninstallation Section
;--------------------------------
Section "Uninstall"
    Delete "$INSTDIR\m1pplauncher.exe"
    RMDir /r "$INSTDIR\_internal"
    Delete "$DESKTOP\M1PP Launcher.lnk"
    Delete "$SMPROGRAMS\M1PP Launcher\M1PP Launcher.lnk"
    DeleteRegKey HKLM "Software\M1PP Launcher"
    RMDir "$INSTDIR"
    RMDir "$SMPROGRAMS\M1PP Launcher"
SectionEnd

;--------------------------------
; MUI Settings
;--------------------------------
!insertmacro MUI_LANGUAGE "English"
