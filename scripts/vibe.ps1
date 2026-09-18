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
    [ValidateSet('help', 'setup', 'doctor', 'run', 'dev', 'dev-frontend', 'stop', 'test', 'lint', 'verify')]
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
    # Deux pieges constates en verifiant reellement (ticket-056) :
    #  1. `cmd /c "cd ... && ..."` ne marche pas : Start-Process re-quote la
    #     liste d'arguments et la chaine `&&` y est perdue. D'ou
    #     `-WorkingDirectory`, qui fait le travail sans intermediaire.
    #  2. Depuis une session NON interactive (un agent, un pipeline CI), la
    #     nouvelle console ne demarre pas. `-NoNewWindow` la ferait demarrer
    #     mais bloquerait le terminal appelant : ce lanceur est prevu pour un
    #     PowerShell interactif. En session non interactive, lancer les deux
    #     commandes directement (voir README).
    Start-Process -FilePath 'uv' `
        -ArgumentList 'run', 'uvicorn', 'vibe_ide.main:app', '--host', '127.0.0.1', '--port', '8000' `
        -WorkingDirectory (Join-Path $Root 'backend')
}

function Start-Frontend {
    Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' `
        -WorkingDirectory (Join-Path $Root 'frontend')
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
    'verify' {
        # Les memes verifications que la CI, dans le meme ordre. Utile quand
        # les minutes GitHub Actions sont epuisees, et de toute facon plus
        # sur : la CI lancait `npx tsc --noEmit`, qui ne verifiait aucun
        # fichier, et `mypy || true`, qui avalait ses erreurs (ticket-095).
        $etapes = @(
            @{ Titre = '1/4 Backend - pytest';   Dossier = 'backend';  Commande = { & uv run pytest -q -m 'not integration' } },
            @{ Titre = '2/4 Backend - mypy';     Dossier = 'backend';  Commande = { & uv run mypy src/ } },
            @{ Titre = '3/4 Frontend - types';   Dossier = 'frontend'; Commande = { & npm run typecheck; if ($LASTEXITCODE -eq 0) { & npm run test -- --run } } },
            @{ Titre = '4/4 E2E - playwright';   Dossier = 'frontend'; Commande = { & npm run test:e2e } }
        )
        foreach ($etape in $etapes) {
            Write-Host ''
            Write-Host "-> $($etape.Titre)"
            Push-Location (Join-Path $Root $etape.Dossier)
            try { & $etape.Commande } finally { Pop-Location }
            if ($LASTEXITCODE -ne 0) {
                Write-Host ''
                Write-Host "ECHEC : $($etape.Titre)" -ForegroundColor Red
                exit 1
            }
        }
        Write-Host ''
        Write-Host 'Vert.' -ForegroundColor Green
        Write-Host 'Hors de portee ici : cargo check (Rust absent de ce poste).'
        Write-Host 'Il ne tourne en CI que si frontend/src-tauri/ a change.'
    }
    'lint' {
        Push-Location (Join-Path $Root 'backend')
        try { & uv run mypy src/ } finally { Pop-Location }
    }
}
