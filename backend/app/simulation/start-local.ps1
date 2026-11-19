param([int]$Port = 8001)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$python = Join-Path $repo '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Create the backend .venv and install backend/app/simulation/requirements.txt first.'
}

if (-not $env:NAMMAMOVE_DEMO_KEY) { $env:NAMMAMOVE_DEMO_KEY = [guid]::NewGuid().ToString('N') }
if (-not $env:NAMMAMOVE_PASSENGER_KEY) { $env:NAMMAMOVE_PASSENGER_KEY = [guid]::NewGuid().ToString('N') }
if (-not $env:NAMMAMOVE_TAXI_PASSWORD) { $env:NAMMAMOVE_TAXI_PASSWORD = [guid]::NewGuid().ToString('N') }
if (-not $env:NAMMAMOVE_METRO_PASSWORD) { $env:NAMMAMOVE_METRO_PASSWORD = [guid]::NewGuid().ToString('N') }
if (-not $env:NAMMAMOVE_BMTC_PASSWORD) { $env:NAMMAMOVE_BMTC_PASSWORD = [guid]::NewGuid().ToString('N') }
if (-not $env:NAMMAMOVE_PARTNER_KEY) { $env:NAMMAMOVE_PARTNER_KEY = [guid]::NewGuid().ToString('N') }
if (-not $env:NAMMAMOVE_SIMULATION_DB) {
    $env:NAMMAMOVE_SIMULATION_DB = Join-Path $repo 'simulation.sqlite3'
}

Push-Location (Join-Path $repo 'backend')
try {
    & $python -m app.simulation.init_store $env:NAMMAMOVE_SIMULATION_DB
    if ($LASTEXITCODE -ne 0) { throw 'Simulation database setup failed.' }
    Write-Host "Console   http://127.0.0.1:$Port/"
    Write-Host "Passenger http://127.0.0.1:$Port/passenger"
    Write-Host "Staff     http://127.0.0.1:$Port/driver"
    Write-Host "Console key        $env:NAMMAMOVE_DEMO_KEY"
    Write-Host "Passenger key      $env:NAMMAMOVE_PASSENGER_KEY"
    Write-Host "taxi-driver        $env:NAMMAMOVE_TAXI_PASSWORD"
    Write-Host "metro-validator    $env:NAMMAMOVE_METRO_PASSWORD"
    Write-Host "bmtc-driver        $env:NAMMAMOVE_BMTC_PASSWORD"
    Write-Host "Partner route key  $env:NAMMAMOVE_PARTNER_KEY"
    & $python -m uvicorn app.simulation.api:app --host 127.0.0.1 --port $Port
}
finally {
    Pop-Location
}
