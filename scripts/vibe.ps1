<#
.SYNOPSIS
    Lanceur vibe-ide pour Windows — équivalent du Makefile (ticket-056).

.DESCRIPTION
    Le Makefile repose sur `make`, qui n'est pas installé par défaut sous
    Windows, et sur `trap`/`wait`, sémantiques POSIX. Toute la procédure
    documentée était donc inutilisable telle quelle.

    Ce script couvre les mêmes tâches sans dépendance supplémentaire.

.EXAMPLE
    .\scripts\vibe.ps1 doctor
    .\scripts\vibe.ps1 run
    .\scripts\vibe.ps1 stop
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'setup', 'doctor', 'run', 'dev', 'dev-frontend', 'stop', 'test', 'lint')]
    [string]$Task = 'help'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

function Show-Help {
    Write-Host ''
    Write-Host '  .\scripts\vibe.ps1 setup        Installe les dependances et cree .env'
    Write-Host '  .\scripts\vibe.ps1 doctor       Verifie les prerequis (a faire en premier)'
    Write-Host '  .\scripts\vibe.ps1 run          Lance backend + frontend'
    Write-Host '  .\scripts\vibe.ps1 dev          Lance le backend seul'
    Write-Host '  .\scripts\vibe.ps1 dev-frontend Lance le frontend seul'
    Write-Host '  .\scripts\vibe.ps1 stop         Arrete tout, worker orphelin compris'
    Write-Host '  .\scripts\vibe.ps1 test         Suite de tests backend'
    Write-Host '  .\scripts\vibe.ps1 lint         Type-check mypy'
    Write-Host ''
}

function Invoke-Doctor {
    Push-Location (Join-Path $Root 'backend')
    try { & uv run python -m vibe_ide.doctor }
    finally { Pop-Location }
}

function Invoke-Setup {
    $envFile = Join-Path $Root '.env'
    if (-not (Test-Path $envFile)) {
        Copy-Item (Join-Path $Root '.env.example') $envFile
        Write-Host "-> .env cree depuis .env.example"
    }
    Push-Location (Join-Path $Root 'backend')
    try { & uv sync --extra dev } finally { Pop-Location }
    Push-Location (Join-Path $Root 'frontend')
    try { & npm install } finally { Pop-Location }
}

function Stop-VibeIde {
    # Le worker `uvicorn --reload` orphelin est le piège principal : tuer le
    # parent laisse l'enfant vivant, qui garde le port 8000 et sert le code de
    # son dernier rechargement. On cible donc la ligne de commande, pas un PID.
    $stopped = 0
    foreach ($spec in @(
            @{ Name = 'python.exe'; Match = '*uvicorn*' },
            @{ Name = 'node.exe'; Match = '*vite*' })) {
        Get-CimInstance Win32_Process -Filter "Name='$($spec.Name)'" |
            Where-Object { $_.CommandLine -like $spec.Match } |
            ForEach-Object {
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
                $stopped++
            }
    }
    Write-Host "-> $stopped processus arrete(s)"

    foreach ($port in 8000, 5173) {
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($conn) {
            Write-Warning "Le port $port est encore tenu par le PID $($conn.OwningProcess)."
            Write-Warning "Si Get-Process ne le trouve pas, c'est un worker orphelin : taskkill /F /PID $($conn.OwningProcess)"
        }
    }
}

function Start-Backend {
    # Pas de `--reload` : c'est lui qui engendre les workers orphelins.
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', `
        "cd /d `"$Root\backend`" && uv run uvicorn vibe_ide.main:app --host 127.0.0.1 --port 8000"
}

function Start-Frontend {
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "cd /d `"$Root\frontend`" && npm run dev"
}

switch ($Task) {
    'help' { Show-Help }
    'setup' { Invoke-Setup }
    'doctor' { Invoke-Doctor }
    'stop' { Stop-VibeIde }
    'dev' { Start-Backend; Write-Host '-> http://localhost:8000/docs' }
    'dev-frontend' { Start-Frontend; Write-Host '-> http://localhost:5173' }
    'run' {
        Invoke-Doctor
        Start-Backend
        Start-Frontend
        Write-Host ''
        Write-Host '-> Backend  : http://localhost:8000/docs'
        Write-Host '-> Frontend : http://localhost:5173'
        Write-Host '-> Arreter  : .\scripts\vibe.ps1 stop'
    }
    'test' {
        Push-Location (Join-Path $Root 'backend')
        try { & uv run pytest -q } finally { Pop-Location }
    }
    'lint' {
        Push-Location (Join-Path $Root 'backend')
        try { & uv run mypy src/ } finally { Pop-Location }
    }
}
