# Three-gate pre-commit blocker: 0 pass / 1 violations / 2 error (dev-cli tri-state)
param()
$ErrorActionPreference = 'Continue'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
$fail = 0
uv run ruff check .
if ($LASTEXITCODE -ne 0) { $fail = 1 }
uv run ty check src
if ($LASTEXITCODE -ne 0) { $fail = 1 }
uv run pytest -q
if ($LASTEXITCODE -ne 0) { $fail = 1 }
exit $fail
