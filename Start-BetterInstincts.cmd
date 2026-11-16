@echo off
setlocal EnableExtensions DisableDelayedExpansion
title BetterInstincts - Play The Sims 4
echo Welcome to BetterInstincts.
echo Opening your game...
set "PLAYMODE=production"
set "BI_BOOTSTRAP_GAP="
if /I "%~1"=="--dev" set "PLAYMODE=dev"
if /I "%PLAYMODE%"=="dev" if "%~2"=="" goto missing_context
if /I "%PLAYMODE%"=="dev" set "DEV_CONTEXT=%~f2"
rem User-scoped, no elevation, no registry/services/driver/input changes.
rem Canonical checkout: %%USERPROFILE%%\dev\BetterInstincts.
if not defined USERPROFILE goto blocked_home
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
if exist "%~dp0scripts\play.py" if exist "%~dp0bootstrap.py" goto local_checkout
where git.exe >nul 2>nul
if errorlevel 1 goto missing_git
set "CHECKOUT=%USERPROFILE%\dev\BetterInstincts"
if exist "%CHECKOUT%\" goto existing
if not exist "%USERPROFILE%\dev\" mkdir "%USERPROFILE%\dev"
if errorlevel 1 goto blocked_home
echo Downloading the latest BetterInstincts from its official repository...
git clone --branch main -- https://github.com/EndeavorEverlasting/BetterInstincts.git "%CHECKOUT%"
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
git -C "%CHECKOUT%" status --porcelain --untracked-files=all >nul 2>nul
if errorlevel 1 goto blocked_existing
set "DIRTY="
for /f "delims=" %%G in ('git -C "%CHECKOUT%" status --porcelain --untracked-files=all 2^>nul') do set "DIRTY=1"
if defined DIRTY goto blocked_dirty
echo Updating clean canonical checkout by fast-forward only...
git -C "%CHECKOUT%" fetch origin refs/heads/main:refs/remotes/origin/main
if errorlevel 1 goto blocked_update
git -C "%CHECKOUT%" merge --ff-only FETCH_HEAD
if errorlevel 1 goto blocked_update
:installed_checkout
cd /d "%CHECKOUT%"
if errorlevel 1 goto blocked_existing
set "CHECKOUT_HEAD="
set "UPSTREAM_HEAD="
for /f "delims=" %%G in ('git rev-parse HEAD') do set "CHECKOUT_HEAD=%%G"
for /f "delims=" %%G in ('git rev-parse refs/remotes/origin/main') do set "UPSTREAM_HEAD=%%G"
if not defined CHECKOUT_HEAD goto blocked_update
if /I not "%CHECKOUT_HEAD%"=="%UPSTREAM_HEAD%" goto blocked_update
if /I "%PLAYMODE%"=="dev" goto play_dev
%PYTHON% -m scripts.play --native-start --mode production --checkout-head "%CHECKOUT_HEAD%"
goto play_result
:play_dev
%PYTHON% -m scripts.play --native-start --mode dev --checkout-head "%CHECKOUT_HEAD%" --save-context "%DEV_CONTEXT%"
goto play_result
:local_checkout
cd /d "%~dp0"
if errorlevel 1 goto blocked_existing
if /I "%PLAYMODE%"=="dev" goto local_dev
%PYTHON% -m scripts.play --native-start --mode production
goto play_result
:local_dev
%PYTHON% -m scripts.play --native-start --mode dev --save-context "%DEV_CONTEXT%"
:play_result
if errorlevel 1 goto blocked_launcher
exit /b 0
:missing_context
set "BI_BOOTSTRAP_GAP=SUPPLY_DEV_SAVE_CONTEXT"
echo Dev play needs the path to your private calibrated save context as the second argument.
goto failure
:missing_git
set "BI_BOOTSTRAP_GAP=INSTALL_GIT"
echo Git is required. Install Git for Windows from https://git-scm.com/downloads/win then double-click this file again.
goto failure
:missing_python
set "BI_BOOTSTRAP_GAP=INSTALL_PYTHON"
echo Python 3.11 or newer is required. Install Python from https://www.python.org/downloads/windows/ then retry.
goto failure
:bad_python
set "BI_BOOTSTRAP_GAP=INSTALL_PYTHON_3_11"
echo Python 3.11 or newer is required. Check your installed Python version and try again.
goto failure
:blocked_home
set "BI_BOOTSTRAP_GAP=SELECT_WRITABLE_HOME"
echo Unable to use the normal per-user development folder.
goto failure
:blocked_clone
set "BI_BOOTSTRAP_GAP=RESTORE_CANONICAL_REPOSITORY_ACCESS"
echo Clone failed. Your existing files were not removed.
goto failure
:blocked_existing
set "BI_BOOTSTRAP_GAP=RESOLVE_CANONICAL_CHECKOUT_CONFLICT"
echo An unrelated checkout, Git worktree, or non-main branch already occupies the canonical path.
echo Preserve it and resolve the conflict before retrying. Nothing was reset.
goto failure
:blocked_dirty
set "BI_BOOTSTRAP_GAP=PRESERVE_AND_RESOLVE_LOCAL_CHANGES"
echo Existing work found in the checkout. No automatic update will overwrite it.
echo Commit/stash it yourself, or use an existing installed BetterInstincts entrypoint.
goto failure
:blocked_update
set "BI_BOOTSTRAP_GAP=RESOLVE_CANONICAL_MAIN_UPDATE"
echo Could not safely fetch/fast-forward. Nothing was force-reset.
goto failure
:blocked_launcher
echo See the required step and launch receipt above.
:failure
if defined LOCALAPPDATA if not "%BI_BOOTSTRAP_GAP%"=="" (
  if not exist "%LOCALAPPDATA%\BetterInstincts\runtime\play-receipts\" mkdir "%LOCALAPPDATA%\BetterInstincts\runtime\play-receipts"
  setlocal EnableDelayedExpansion
  set "BOOTSTRAP_RECEIPT=%LOCALAPPDATA%\BetterInstincts\runtime\play-receipts\bootstrap-%BI_BOOTSTRAP_GAP%.json"
  if not exist "!BOOTSTRAP_RECEIPT!" (
    >"!BOOTSTRAP_RECEIPT!" echo {"schema":"betterinstincts.play-bootstrap-receipt/v1","status":"blocked","startup_mode":"%PLAYMODE%","automation_gaps":[{"kind":"MISSING_REPOSITORY_LOGIC","stage":"bootstrap","reason":"%BI_BOOTSTRAP_GAP%","required_actor":"human_or_agent","required_step":"%BI_BOOTSTRAP_GAP%","repository_owner":"Start-BetterInstincts.cmd"}]}
  )
  if exist "!BOOTSTRAP_RECEIPT!" echo Launch receipt: !BOOTSTRAP_RECEIPT!
  endlocal
)
echo.
pause
exit /b 2
