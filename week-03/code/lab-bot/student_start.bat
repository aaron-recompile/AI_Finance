@echo off
setlocal EnableDelayedExpansion

:: student_start.bat — run YOUR OWN bot dashboard (read-only: no wallet, no gas, no risk).
::
:: Usage:
::   student_start.bat          :: start  ->  http://localhost:8010/dashboard.html
::   student_start.bat stop     :: stop

set "PORT=8010"
cd /d "%~dp0"

:: Handle 'stop' argument
if /i "%~1"=="stop" (
    call :stop_services
    exit /b 0
)

:: Pick a python command that can import web3
set "PY="
for %%c in (python py) do (
    where %%c >nul 2>&1
    if !errorlevel! equ 0 (
        %%c -c "import web3" >nul 2>&1
        if !errorlevel! equ 0 (
            set "PY=%%c"
            goto :found_python
        )
    )
)

:found_python
if "%PY%"=="" (
    echo !! Python cannot import web3 yet. Install it once, then re-run:
    echo        python -m pip install web3
    exit /b 1
)

:: Clean slate before starting so re-running is safe
call :stop_services

:: 1) Tiny web server so dashboard.html can fetch state.json
start "StudentHttpd" /min %PY% -m http.server %PORT%

:: 2) Orchestrator bots — DRY-RUN + gentle 12s heartbeat
start "StudentOrchestrator" /min %PY% orchestrator.py --interval 12

timeout /t 1 /nobreak >nul

echo.
echo   [+] Your bot dashboard is live -- DRY-RUN, read-only, no wallet, no gas:
echo.
echo          http://localhost:%PORT%/dashboard.html
echo.
echo   Watch it while the instructor skews the market. A GREEN row = your own bot
echo   found the opportunity. It's only watching -- it never fires a trade.
echo   Stop when done:   student_start.bat stop
echo.
exit /b 0

:stop_services
:: Kill any process listening on the specified PORT
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%PORT% "') do (
    taskkill /f /pid %%a >nul 2>&1
)
:: Kill background windows spawned by this script
taskkill /f /fi "WINDOWTITLE eq StudentHttpd*" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq StudentOrchestrator*" >nul 2>&1
echo stopped (port %PORT% + orchestrator).
exit /b 0