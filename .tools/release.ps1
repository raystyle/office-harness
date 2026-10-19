# Release three-stage script: pre-check, build, verify distribution.
# Exit codes: 0 pass / 1 violations / 2 error (dev-cli tri-state).
# Usage: pwsh -File .tools/release.ps1 [-VersionCheckOnly]
param([switch]$VersionCheckOnly)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

# ---- stage 1: pre-check (gates + version single-source) ----
Write-Host '== stage 1: pre-check =='
uv run ruff check .
if ($LASTEXITCODE -ne 0) { exit 1 }
uv run ty check src
if ($LASTEXITCODE -ne 0) { exit 1 }
uv run pytest -q
if ($LASTEXITCODE -ne 0) { exit 1 }
$pyVersion = (uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])").Trim()
$cliVersion = (uv run office-harness --schema | ConvertFrom-Json).version
if ($pyVersion -ne $cliVersion) {
  Write-Error "version drift: pyproject=$pyVersion schema=$cliVersion"
  exit 1
}
Write-Host "version single-source OK: $pyVersion"
if ($VersionCheckOnly) { exit 0 }

# ---- stage 2: build ----
Write-Host '== stage 2: build =='
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
uv build
if ($LASTEXITCODE -ne 0) { exit 2 }

# ---- stage 3: verify distribution + hash sidecars ----
Write-Host '== stage 3: verify distribution =='
$tmp = Join-Path $env:TEMP ("oh-release-" + [guid]::NewGuid().ToString('N').Substring(0, 8))
uv venv $tmp | Out-Null
if ($LASTEXITCODE -ne 0) { exit 2 }
$whl = (Get-ChildItem dist/*.whl | Select-Object -First 1).FullName
uv pip install --python "$tmp\Scripts\python.exe" $whl
if ($LASTEXITCODE -ne 0) { exit 2 }
& "$tmp\Scripts\office-harness.exe" --version
if ($LASTEXITCODE -ne 0) { exit 2 }
& "$tmp\Scripts\office-harness.exe" --llms | Select-Object -First 3
if ($LASTEXITCODE -ne 0) { exit 2 }
Get-ChildItem dist -File | Where-Object { $_.Extension -in '.whl', '.gz' } | ForEach-Object {
  $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower()
  "$h  $($_.Name)" | Set-Content ($_.FullName + '.sha256')
  Write-Host "sidecar: $($_.Name).sha256"
}
Remove-Item -Recurse -Force $tmp
Write-Host 'release OK: dist/ + sha256 sidecars'
exit 0
