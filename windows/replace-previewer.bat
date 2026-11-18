@rem 替换DevEco预览器文件。
@echo off
"C:\Windows\System32\taskkill.exe" /F /IM Previewer.exe >nul 2>&1
"C:\Windows\System32\Robocopy.exe" "%~1" "%~2" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 exit /b 1
exit /b 0
