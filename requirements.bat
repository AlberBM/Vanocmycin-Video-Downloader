@echo off
setlocal enabledelayedexpansion

:: Set target paths
set "TARGET_PATH=C:\FFMPEG"
set "ZIP_PATH=%TEMP%\ffmpeg.zip"
set "TEMP_EXTRACT=%TEMP%\ffmpeg_extract"

:: Create target folder
if not exist "%TARGET_PATH%" (
    mkdir "%TARGET_PATH%"
)

:: Download using BITS (shows native progress bar)
echo Downloading FFmpeg with native progress bar...
powershell -Command "Start-BitsTransfer -Source 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -Destination '%ZIP_PATH%'"

:: Validate download
if not exist "%ZIP_PATH%" (
    echo ERROR: Download failed or ZIP not found.
    pause
    exit /b 1
)

:: Extract ZIP file
echo.
echo Extracting FFmpeg...
powershell -Command "Expand-Archive -Path '%ZIP_PATH%' -DestinationPath '%TEMP_EXTRACT%' -Force"

:: Move files from bin to C:\FFMPEG
for /d %%i in ("%TEMP_EXTRACT%\ffmpeg-*") do (
    xcopy "%%i\bin\*" "%TARGET_PATH%\" /E /Y
    goto found
)
:found

:: Cleanup
del "%ZIP_PATH%" >nul 2>&1
rd /s /q "%TEMP_EXTRACT%" >nul 2>&1

:: Check if already in user PATH
for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do (
    set "CURRENT_PATH=%%B"
)
if not defined CURRENT_PATH set "CURRENT_PATH="

echo !CURRENT_PATH! | find /I "%TARGET_PATH%" >nul
if !ERRORLEVEL! EQU 0 (
    echo %TARGET_PATH% is already in your user PATH.
    goto end
)

:: Append to user PATH
if defined CURRENT_PATH (
    set "NEW_PATH=!CURRENT_PATH!;%TARGET_PATH%"
) else (
    set "NEW_PATH=%TARGET_PATH%"
)
echo Adding %TARGET_PATH% to your user PATH...
setx Path "!NEW_PATH!" >nul

echo.
echo FFmpeg has been installed to %TARGET_PATH% and added to your PATH.
echo You may need to restart Command Prompt or log off and log in for changes to take effect.

:end
pause
