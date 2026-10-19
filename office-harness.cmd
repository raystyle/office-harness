@echo off
rem Launcher chain: .venv python -> uv run -> bare python (hvperv-harness form)
setlocal
set "HERE=%~dp0"
if exist "%HERE%.venv\Scripts\python.exe" (
  "%HERE%.venv\Scripts\python.exe" -m office_harness %*
  exit /b %ERRORLEVEL%
)
where uv >nul 2>nul && (
  uv run --project "%HERE%" python -m office_harness %*
  exit /b %ERRORLEVEL%
)
python -m office_harness %*
exit /b %ERRORLEVEL%
