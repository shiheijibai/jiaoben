@rem 复制并解压Windows SDK。
@echo off

set "source=%~1"
set "target=%~2"

for %%D in (ets js native previewer toolchains) do rmdir /s /q "%target%\%%D" 2>nul
del /q "%target%\*-windows-x64-*.zip" 2>nul
for %%D in ("%target%") do del /q "%target%\%%~nxD.txt" 2>nul

"C:\Windows\System32\Robocopy.exe" "%source%" "%target%" "*-windows-x64-*.zip" /R:1 /W:1 /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 exit /b 1

cd /d "%target%" || exit /b 1
for %%F in (*-windows-x64-*.zip) do (
    "C:\Program Files\7-Zip\7z.exe" x -y -bd -bso0 -bsp0 "%%F" || exit /b 1
)

for %%D in ("%target%") do type nul >"%%~nxD.txt"
