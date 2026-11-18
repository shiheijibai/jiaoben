@rem 将OpenHarmony源码中的TDD框架同步到Windows。
@echo off

set "TDD_ROOT=D:\rk3568\TDD"

"C:\Windows\System32\Robocopy.exe" "%~1\test\testfwk\developer_test" "%TDD_ROOT%\developer_test" /MIR /R:1 /W:1 /XJ /XD reports /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 exit /b 1

"C:\Windows\System32\Robocopy.exe" "%~1\test\testfwk\xdevice" "%TDD_ROOT%\xdevice" /MIR /R:1 /W:1 /XJ /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 exit /b 1

exit /b 0
