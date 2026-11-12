@echo off
setlocal EnableExtensions DisableDelayedExpansion
title BetterInstincts - Install and Play
rem User-scoped, no elevation, no registry/services/driver/input changes.
rem Canonical checkout: %%USERPROFILE%%\dev\BetterInstincts.
if not defined USERPROFILE goto blocked_home
where git.exe >nul 2>nul
if errorlevel 1 goto missing_git
where py.exe >nul 2>nul
if not errorlevel 1 (
  set "PYTHON=py -3"
) else (
  where python.exe >nul 2>nul
  if errorlevel 1 goto missing_python
  set "PYTHON=python"
)
%PYTHON% -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 goto bad_python
set "CHECKOUT=%USERPROFILE%\dev\BetterInstincts"
if exist "%CHECKOUT%\" goto existing
if not exist "%USERPROFILE%\dev\" mkdir "%USERPROFILE%\dev"
if errorlevel 1 goto blocked_home
echo Downloading the latest BetterInstincts from its official repository...
git clone -- https://github.com/EndeavorEverlasting/BetterInstincts.git "%CHECKOUT%"
if errorlevel 1 goto blocked_clone
goto installed_checkout
:existing
rem Never take over an unrelated checkout, linked Git worktree, or dirty branch.
if not exist "%CHECKOUT%\.git\" goto blocked_existing
set "ORIGIN="
for /f "delims=" %%G in ('git -C "%CHECKOUT%" remote get-url origin 2^>nul') do set "ORIGIN=%%G"
if /I "%ORIGIN%"=="https://github.com/EndeavorEverlasting/BetterInstincts.git" goto origin_ok
if /I "%ORIGIN%"=="git@github.com:EndeavorEverlasting/BetterInstincts.git" goto origin_ok
goto blocked_existing
:origin_ok
set "BRANCH="
for /f "delims=" %%G in ('git -C "%CHECKOUT%" symbolic-ref --short HEAD 2^>nul') do set "BRANCH=%%G"
if /I not "%BRANCH%"=="main" goto blocked_existing
set "DIRTY="
for /f "delims=" %%G in ('git -C "%CHECKOUT%" status --porcelain --untracked-files=all 2^>nul') do set "DIRTY=1"
if defined DIRTY goto blocked_dirty
echo Updating clean canonical checkout by fast-forward only...
git -C "%CHECKOUT%" fetch origin main
if errorlevel 1 goto blocked_update
git -C "%CHECKOUT%" merge --ff-only origin/main
if errorlevel 1 goto blocked_update
:installed_checkout
cd /d "%CHECKOUT%"
if errorlevel 1 goto blocked_existing
echo Installing BetterInstincts offline toolkit...
%PYTHON% bootstrap.py install
if errorlevel 1 goto blocked_install
echo Starting The Sims 4 when a unique installation and idle game process are verified...
rem The double-click itself requests launch; never guess a save or bypass EA authentication.
%PYTHON% -m scripts.first_run auto --fallback-gui
if errorlevel 1 goto blocked_launcher
exit /b 0
:missing_git
echo Git is required. Install Git for Windows from https://git-scm.com/downloads/win then double-click this file again.
goto failure
:missing_python
echo Python 3.11 or newer is required. Install Python from https://www.python.org/downloads/windows/ then retry.
goto failure
:bad_python
echo Python 3.11 or newer is required. Check your installed Python version and try again.
goto failure
:blocked_home
echo Unable to use the normal per-user development folder.
goto failure
:blocked_clone
echo Clone failed. Your existing files were not removed.
goto failure
:blocked_existing
echo An unrelated checkout, Git worktree, or non-main branch already occupies the canonical path.
echo Preserve it and resolve the conflict before retrying. Nothing was reset.
goto failure
:blocked_dirty
echo Existing work found in the checkout. No automatic update will overwrite it.
echo Commit/stash it yourself, or use an existing installed BetterInstincts entrypoint.
goto failure
:blocked_update
echo Could not safely fetch/fast-forward. Nothing was force-reset.
goto failure
:blocked_install
echo Installation did not complete; your checkout and game files were preserved.
goto failure
:blocked_launcher
echo The local launcher was unavailable. See the error above.
:failure
echo.
pause
exit /b 2
