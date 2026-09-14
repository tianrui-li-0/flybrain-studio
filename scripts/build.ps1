param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot
& $Python scripts/make_assets.py
if ($LASTEXITCODE -ne 0) { throw 'Asset preparation failed' }
& $Python -c "from studio.model import Dataset; Dataset('data')"
if ($LASTEXITCODE -ne 0) { throw 'Official dataset validation failed; download and prepare data first' }
& $Python -m PyInstaller --noconfirm --distpath release-official --workpath build FlyBrainStudio.spec
if ($LASTEXITCODE -ne 0) { throw 'Application build failed' }
