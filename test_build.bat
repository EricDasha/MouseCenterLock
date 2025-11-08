@echo off
echo Testing MouseCenterLock.exe...
echo.

REM 检查文件是否存在
if not exist "dist\MouseCenterLock.exe" (
    echo ERROR: dist\MouseCenterLock.exe not found!
    echo Please build first using: pyinstaller --noconfirm --clean MouseCenterLock.spec
    pause
    exit /b 1
)

echo File exists. Starting program...
echo Waiting 5 seconds to check if program starts...
echo.

REM 启动程序并等待
start "" "dist\MouseCenterLock.exe"
timeout /t 5 /nobreak >nul

REM 检查进程是否还在运行
tasklist /FI "IMAGENAME eq MouseCenterLock.exe" 2>NUL | find /I /N "MouseCenterLock.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo SUCCESS: Program is running!
    echo.
    echo Closing program...
    taskkill /F /IM MouseCenterLock.exe >nul 2>&1
) else (
    echo WARNING: Program may have exited or failed to start.
    echo Check for error messages above.
)

echo.
pause

