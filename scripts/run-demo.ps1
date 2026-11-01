param([switch]$Offline)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Create .venv and install dependencies using the README first.'
}
$env:PYTHONPATH = Join-Path $projectRoot 'src'
$env:MPLCONFIGDIR = Join-Path $projectRoot 'tmp\matplotlib'
$pipelineArgs = @('-m', 'airbnb_lab.cli', 'run')
if ($Offline) { $pipelineArgs += '--offline' }
& $pythonExe @pipelineArgs
if ($LASTEXITCODE -ne 0) { throw 'Pipeline failed. See the run manifest and console output.' }
Invoke-Item -LiteralPath (Join-Path $projectRoot 'outputs\albany\2026-09-14\explorer.html')
