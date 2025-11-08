@echo off
REM 优化的打包脚本 - 减少文件大小和提升性能

echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building optimized executable...
pyinstaller --noconfirm --clean MouseCenterLock.spec

echo.
echo Build complete! Checking file size...
if exist dist\MouseCenterLock.exe (
    for %%A in (dist\MouseCenterLock.exe) do echo File size: %%~zA bytes (%%~zA / 1048576 MB)
)

pause

