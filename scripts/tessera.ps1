<#
.SYNOPSIS
    Lanceur Tessera pour Windows — équivalent du Makefile (ticket-056).

.DESCRIPTION
    Le Makefile repose sur `make`, qui n'est pas installé par défaut sous
    Windows, et sur `trap`/`wait`, sémantiques POSIX. Toute la procédure
    documentée était donc inutilisable telle quelle.

    Ce script couvre les mêmes tâches sans dépendance supplémentaire.

.EXAMPLE
    .\scripts\tessera.ps1 doctor
    .\scripts\tessera.ps1 run
    .\scripts\tessera.ps1 stop
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('help', 'setup', 'doctor', 'run', 'dev', 'dev-frontend', 'stop', 'test', 'lint', 'verify', 'check-tickets')]
    [string]$Task = 'help',

    # Identifiant du projet, pour `check-tickets`.
    [Parameter(Position = 1)]
    [string]$Projet = ''
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot

function Show-Help {
    Write-Host ''
    Write-Host '  .\scripts\tessera.ps1 setup        Installe les dependances et cree .env'
    Write-Host '  .\scripts\tessera.ps1 doctor       Verifie les prerequis (a faire en premier)'
    Write-Host '  .\scripts\tessera.ps1 run          Lance backend + frontend'
    Write-Host '  .\scripts\tessera.ps1 dev          Lance le backend seul'
    Write-Host '  .\scripts\tessera.ps1 dev-frontend Lance le frontend seul'
    Write-Host '  .\scripts\tessera.ps1 stop         Arrete tout, worker orphelin compris'
    Write-Host '  .\scripts\tessera.ps1 test         Suite de tests backend'
    Write-Host '  .\scripts\tessera.ps1 lint         Type-check mypy'
    Write-Host '  .\scripts\tessera.ps1 check-tickets <id>  Verifie les tickets d un projet avant de les committer'
    Write-Host ''
}

function Invoke-Doctor {
    Push-Location (Join-Path $Root 'backend')
    try { & uv run python -m tessera.doctor }
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

function Get-ProcessusTessera {
    # Le worker `uvicorn --reload` orphelin est le piege principal : tuer le
    # parent laisse l'enfant vivant, qui garde le port 8100. Mais le filtre
    # ne doit viser que Tessera (ticket-423) : la selection est faite par
    # scripts/arreter_tessera.py (testee), ce script ne fait que lister et tuer.
    $processus = @(Get-CimInstance Win32_Process |
            Where-Object { $_.Name -in 'python.exe', 'node.exe' } |
            ForEach-Object { @{ pid = [int]$_.ProcessId; nom = $_.Name; commande = [string]$_.CommandLine } })
    $ecoutes = @{}
    foreach ($port in 8100, 5173) {
        $ecoutes["$port"] = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
                ForEach-Object { [int]$_.OwningProcess })
    }
    $entree = ConvertTo-Json -Compress -Depth 4 -InputObject @{ processus = $processus; ecoutes = $ecoutes }
    $ancien = $OutputEncoding
    $OutputEncoding = [Text.UTF8Encoding]::new($false)
    Push-Location (Join-Path $Root 'backend')
    try { $sortie = $entree | & uv run python (Join-Path $PSScriptRoot 'arreter_tessera.py') $Root }
    finally { Pop-Location; $OutputEncoding = $ancien }
    if ($LASTEXITCODE -ne 0) { throw "arreter_tessera.py a echoue (code $LASTEXITCODE)" }
    $json = [string]::Join('', $sortie)
    if ([string]::IsNullOrWhiteSpace($json)) { return @() }
    # Windows PowerShell 5.1 ne deroule pas un tableau JSON : `[]` revient comme
    # un objet unique (un tableau vide), d'ou une iteration a vide. Le passage
    # par le pipeline le deroule dans les deux versions ; le filtre ecarte tout
    # element sans PID.
    return @(ConvertFrom-Json $json | ForEach-Object { $_ } | Where-Object { $null -ne $_ -and $null -ne $_.pid })
}

function Stop-Tessera {
    $stopped = 0
    foreach ($p in Get-ProcessusTessera) {
        if ($p.pid -eq $PID) { continue }
        Stop-Process -Id $p.pid -Force -ErrorAction SilentlyContinue
        Write-Host "-> arrete PID $($p.pid) ($($p.nom)) : $($p.debut)"
        $stopped++
    }
    Write-Host "-> $stopped processus arrete(s)"

    foreach ($port in 8100, 5173) {
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
        -ArgumentList 'run', 'python', '-m', 'uvicorn', 'tessera.main:app', '--host', '127.0.0.1', '--port', '8100' `
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
    'stop' { Stop-Tessera }
    'dev' { Start-Backend; Write-Host '-> http://localhost:8100/docs' }
    'dev-frontend' { Start-Frontend; Write-Host '-> http://localhost:5173' }
    'run' {
        Invoke-Doctor
        Start-Backend
        Start-Frontend
        Write-Host ''
        Write-Host '-> Backend  : http://localhost:8100/docs'
        Write-Host '-> Frontend : http://localhost:5173'
        Write-Host '-> Arreter  : .\scripts\tessera.ps1 stop'
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
            @{ Titre = '1/5 Backend - pytest';   Dossier = 'backend';  Commande = { & uv run pytest -q -m 'not integration' } },
            # Deux passes : mypy n'analyse qu'une plateforme a la fois, celle
            # sur laquelle il tourne. Du code Windows-only typait ici et
            # cassait la CI Linux, que rien en local ne pouvait voir (ticket-153).
            @{ Titre = '2/5 Backend - mypy';     Dossier = 'backend';  Commande = { & uv run mypy src/; if ($LASTEXITCODE -eq 0) { & uv run mypy --platform linux src/ } } },
            @{ Titre = '3/5 Frontend - lint';    Dossier = 'frontend'; Commande = { & npm run lint } },
            @{ Titre = '4/5 Frontend - types';   Dossier = 'frontend'; Commande = { & npm run typecheck; if ($LASTEXITCODE -eq 0) { & npm run test -- --run } } },
            @{ Titre = '5/5 E2E - playwright';   Dossier = 'frontend'; Commande = { & npm run test:e2e } }
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
    'check-tickets' {
        # Sort en erreur au moindre probleme : utilisable avant un commit (ticket-433).
        if ([string]::IsNullOrWhiteSpace($Projet)) {
            Write-Host 'usage : .\scripts\tessera.ps1 check-tickets <id>' -ForegroundColor Red
            exit 2
        }
        Push-Location (Join-Path $Root 'backend')
        try { & uv run python -m tessera.services.ticket_check $Projet }
        finally { Pop-Location }
        exit $LASTEXITCODE
    }
    'lint' {
        Push-Location (Join-Path $Root 'backend')
        try {
            & uv run mypy src/
            if ($LASTEXITCODE -eq 0) { & uv run mypy --platform linux src/ }
        } finally { Pop-Location }
    }
}
