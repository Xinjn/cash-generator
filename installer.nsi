; NSIS installer script for CashGenerator
; Outputs: dist/CashGenerator_Setup.exe

!define APP_NAME "CashGenerator"
!define APP_DIR "CashGenerator"
!define INSTALLER_NAME "CashGenerator_Setup.exe"
!define SOURCE_DIR "dist\CashGenerator"

Name "${APP_NAME}"
OutFile "dist\${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES64\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" ""
RequestExecutionLevel admin

; Pages
Page directory
Page instfiles

; Uninstaller
UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
    SetOutPath "$INSTDIR"

    ; Copy all files from PyInstaller output
    File /r "${SOURCE_DIR}\*.*"

    ; Create start menu shortcut
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe"

    ; Create desktop shortcut
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe"

    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Registry entries
    WriteRegStr HKCU "Software\${APP_NAME}" "" $INSTDIR
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"

    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd
