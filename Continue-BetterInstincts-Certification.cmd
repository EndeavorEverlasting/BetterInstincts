@echo off
setlocal EnableExtensions DisableDelayedExpansion
title BetterInstincts Live Certification
pushd "%~dp0" || exit /b 2
where py.exe >nul 2>nul
if errorlevel 1 (
    python -m scripts.continue_certification %*
) else (
    py -3 -m scripts.continue_certification %*
)
set "CERT_EXIT=%ERRORLEVEL%"
popd
pause
exit /b %CERT_EXIT%
