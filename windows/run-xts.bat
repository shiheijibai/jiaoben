@rem 调用XTS框架执行测试。
@echo off

set "PATH=D:\Path\python;D:\Path\hdc;%PATH%"
cd /d "%~1" || exit /b 1
call run.bat %~2
exit /b %errorlevel%
