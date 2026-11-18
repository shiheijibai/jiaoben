@rem 解压并部署Windows构建产物。
@echo off
setlocal

set "SEVEN_ZIP=C:\Program Files\7-Zip\7z.exe"
set "PACKAGE_TYPE=%~1"
set "ARCHIVE=%~2"
set "TEMP_PATH=D:\rk3568\temp"

if not exist "%TEMP_PATH%" mkdir "%TEMP_PATH%" || exit /b 1
cd /d "%TEMP_PATH%" || exit /b 1
"%SEVEN_ZIP%" x "%ARCHIVE%" -y >nul || exit /b 1

set "INNER_ARCHIVE=%TEMP_PATH%\%~n2"
if not exist "%INNER_ARCHIVE%" exit /b 2

if /i "%PACKAGE_TYPE%"=="image" (
    if exist "D:\rk3568\imagestemp" rmdir /s /q "D:\rk3568\imagestemp"
    mkdir "D:\rk3568\imagestemp" || exit /b 1
    "%SEVEN_ZIP%" x "%INNER_ARCHIVE%" "-oD:\rk3568\imagestemp" -y >nul || exit /b 1
    exit /b 0
)

for %%F in ("%INNER_ARCHIVE%") do set "PACKAGE_NAME=%%~nF"
set "PACKAGE_PATH=%TEMP_PATH%\%PACKAGE_NAME%"
if exist "%PACKAGE_PATH%" rmdir /s /q "%PACKAGE_PATH%"
mkdir "%PACKAGE_PATH%" || exit /b 1
"%SEVEN_ZIP%" x "%INNER_ARCHIVE%" "-o%PACKAGE_PATH%" -y >nul || exit /b 1

if /i "%PACKAGE_TYPE%"=="tdd" (
    call "%~dp0copy-tdd.bat" "%PACKAGE_PATH%\tests\unittest" "D:\rk3568\TDD\tests\unittest"
    if errorlevel 1 exit /b 1
    if exist "%PACKAGE_PATH%\unittest" (
        "C:\Windows\System32\Robocopy.exe" "%PACKAGE_PATH%\unittest" "D:\rk3568\TDD\tests\unittest" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
        if errorlevel 8 exit /b 1
    )
    exit /b 0
)
if /i "%PACKAGE_TYPE%"=="xts" (
    call "%~dp0copy-xts.bat" "%PACKAGE_PATH%\suites\acts\acts\testcases" "D:\rk3568\XTS\dynamic\acts\testcases"
    if errorlevel 1 exit /b 1
    exit /b 0
)
exit /b 3
