@rem 复制 ArkUI-X Windows SDK。
@echo off

set "source=%~1"
set "target=%~2"

if not exist "%source%\" exit /b 1
if exist "%target%" rmdir /s /q "%target%" || exit /b 1
"C:\Windows\System32\Robocopy.exe" "%source%" "%target%" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 exit /b 1
