@rem 调用TDD框架执行测试。
@echo off

set "PATH=D:\Path\hdc;%PATH%"
set "PYTHONUTF8=1"
cd /d "D:\rk3568\TDD\developer_test\src" || exit /b 1
"D:\Path\python\python.exe" -m main %*
exit /b %errorlevel%
