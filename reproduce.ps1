#!/usr/bin/env pwsh
# PowerShell stand-in for `make reproduce`.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = "src"
$py = if ($env:PY) { $env:PY } else { "python" }
$stages = if ($args.Count -gt 0) { $args } else { @("study") }
$map = @{
    "ff"     = @("scripts/fetch_ff.py")
    "prices" = @("scripts/fetch_prices.py", "--tickers", "tickers.txt")
    "study"  = @("scripts/run_study.py")
}
foreach ($s in $stages) {
    Write-Host "== stage: $s"
    & $py $map[$s]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
