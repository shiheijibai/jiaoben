@rem 替换Windows TDD测试目录。
@echo off

if exist "%~2" rmdir /s /q "%~2"
"C:\Windows\System32\Robocopy.exe" "%~1" "%~2" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 exit /b 1
exit /b 0
