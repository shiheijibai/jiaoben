@rem 同步Windows镜像目录。
@echo off

"C:\Windows\System32\Robocopy.exe" "%~1" "%~2" /MIR /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 exit /b 1
exit /b 0
