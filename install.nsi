;--------------------------------
; Head
;--------------------------------

!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "FileFunc.nsh"

!define INSTALLED_VIA_NSIS

;--------------------------------
; General Installer Settings
;--------------------------------
Name "M1PP Launcher"
OutFile "m1pplauncher-setup-alpha3.exe"
InstallDir "$PROGRAMFILES\M1PPLauncher"
InstallDirRegKey HKLM "Software\M1PP Launcher" "InstallDir"
Icon "icon.ico"
UninstallIcon "icon.ico"
SetCompressor /SOLID lzma
BrandingText " "
RequestExecutionLevel admin

;--------------------------------
; Plugin / Download Settings
;--------------------------------
!define DOTNET_VERSION     "8.0"
!define HOSTING_BUNDLE_URL "https://builds.dotnet.microsoft.com/dotnet/WindowsDesktop/8.0.15/windowsdesktop-runtime-8.0.15-win-x64.exe"
!define HOSTING_BUNDLE_EXE "windowsdesktop-runtime-8.0.15-win-x64.exe"

;--------------------------------
; Pages
;--------------------------------
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "banner.bmp"
!define MUI_ICON "icon.ico"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
Page Custom RemoveOldDataPageCreate RemoveOldDataPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Variables
;--------------------------------
Var RemoveOldData
Var OldDataCheckbox
Var BundlePath
Var BundleExit
Var ExitCode
Var StdOut

;--------------------------------
; Custom Page Functions
;--------------------------------
Function RemoveOldDataPageCreate
    nsDialogs::Create 1018
    Pop $0
    StrCmp $0 "error" 0 +2
        Abort
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
    ExecWait 'taskkill /F /IM m1pplauncher.exe' $0
    ExecWait 'taskkill /F /IM tosu.exe' $0
    ExecWait 'taskkill /F /IM "osu!.patcher.exe"' $0
    ExecWait 'taskkill /F /IM "tosu-overlay.exe"' $0

    SetOutPath "$INSTDIR"
    SetRegView 64

    StrCmp $RemoveOldData "1" remove_old_data skip_remove_old_data

  remove_old_data:
    System::Call 'kernel32::DeleteFileW(w "$LOCALAPPDATA\\osu!m1pp\\osu!.db") i .r0'
    System::Call 'kernel32::RemoveDirectoryW(w "$LOCALAPPDATA\\osu!m1pp\\Songs") i .r0'
    System::Call 'kernel32::RemoveDirectoryW(w "$LOCALAPPDATA\\osu!m1pp\\Skins") i .r0'
    RMDir /r "$LOCALAPPDATA\\osu!m1pp"
    Delete "$LOCALAPPDATA\\m1pposu_config.json"
  skip_remove_old_data:
    IfFileExists "C:\Program Files\dotnet\host\fxr\8.0.15\hostfxr.dll" dotnetAlreadyInstalled
    DetailPrint "Downloading .NET"
    StrCpy $BundlePath "$PLUGINSDIR\${HOSTING_BUNDLE_EXE}"

    nsExec::ExecToStack `"powershell.exe" -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-WebRequest -Uri '${HOSTING_BUNDLE_URL}' -OutFile '$BundlePath' -UseBasicParsing -ErrorAction Stop } catch { Write-Host 'DOWNLOAD_FAILED'; exit 1 }"`
    Pop $ExitCode
    Pop $StdOut

    StrCmp $ExitCode 0 +3
        MessageBox MB_ICONSTOP "Failed to download .NET Hosting Bundle (`${HOSTING_BUNDLE_URL}`)."
        Abort

    DetailPrint "Downloaded .NET Hosting Bundle to: $BundlePath"

    DetailPrint "Installing .NET..."
    ExecWait '"$BundlePath"' $BundleExit
    StrCmp $BundleExit 0 +3
        MessageBox MB_ICONSTOP ".NET installation failed (exit code: $BundleExit)."
        Abort

    Delete "$BundlePath"
  dotnetAlreadyInstalled:
    File "dist\m1pplauncher\m1pplauncher.exe"
    SetOutPath "$INSTDIR\_internal"
    File /r "dist\m1pplauncher\_internal\*.*"
    
    File "dist\\m1pplauncher\\m1pplauncher.exe"
    SetOutPath "$INSTDIR\\_internal"
    File /r "dist\\m1pplauncher\\_internal\\*.*"

    CreateShortCut "$DESKTOP\\M1PP Launcher.lnk" "$INSTDIR\\m1pplauncher.exe"
    CreateDirectory "$SMPROGRAMS\\M1PP Launcher"
    CreateShortCut "$SMPROGRAMS\\M1PP Launcher\\M1PP Launcher.lnk" "$INSTDIR\\m1pplauncher.exe"
    WriteRegStr HKLM "Software\\M1PP Launcher" "InstallDir" "$INSTDIR"
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher" "DisplayName" "M1PP Launcher"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher" "DisplayIcon" "$INSTDIR\\m1pplauncher.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher" "Publisher" "M1PPosu"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher" "NoRepair" 1
SectionEnd

;--------------------------------
; Uninstallation Section
;--------------------------------
Section "Uninstall"
    ExecWait 'taskkill /F /IM m1pplauncher.exe' $0
    ExecWait 'taskkill /F /IM tosu.exe' $0
    ExecWait 'taskkill /F /IM "osu!.patcher.exe"' $0
    ExecWait 'taskkill /F /IM "tosu-overlay.exe"' $0
    
    System::Call 'kernel32::DeleteFileW(w "$LOCALAPPDATA\\osu!m1pp\\osu!.db") i .r0'
    System::Call 'kernel32::RemoveDirectoryW(w "$LOCALAPPDATA\\osu!m1pp\\Songs") i .r0'
    System::Call 'kernel32::RemoveDirectoryW(w "$LOCALAPPDATA\\osu!m1pp\\Skins") i .r0'

    SetRegView 64
    Delete "$INSTDIR\\m1pplauncher.exe"
    RMDir /r "$INSTDIR\\_internal"
    Delete "$DESKTOP\\M1PP Launcher.lnk"
    Delete "$SMPROGRAMS\\M1PP Launcher\\M1PP Launcher.lnk"
    DeleteRegKey HKLM "Software\\M1PP Launcher"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\M1PP Launcher"
    RMDir "$INSTDIR"
    RMDir "$SMPROGRAMS\\M1PP Launcher"
SectionEnd

;--------------------------------
; MUI Settings
;--------------------------------
!insertmacro MUI_LANGUAGE "English"
