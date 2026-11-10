# Partie UTILISATEUR de l'installation du compte agent, SANS admin, a lancer
# APRES agent-setup-admin.ps1 dans ta fenetre PowerShell normale :
#   powershell -ExecutionPolicy Bypass -File scripts\agent-setup.ps1 [-Jeton]
# Range le mot de passe remis dans ton coffre et efface le fichier, copie le CLI
# du SDK, donne la lecture-execution sur les outils. Avec -Jeton (ou
# `tessera.ps1 agent jeton`), lit un jeton `claude setup-token` dans le
# presse-papiers et le range sous AGENT_OAUTH_TOKEN.
param([switch]$Jeton)
$ErrorActionPreference = 'Stop'
$Compte  = 'tessera-agent'
$Moi     = $env:USERPROFILE
$Racine  = Split-Path -Parent $PSScriptRoot
$PyVenv  = Join-Path $Racine 'backend\.venv\Scripts\python.exe'
$Partage = 'C:\ProgramData\Tessera'
$Remise  = Join-Path $Partage 'remise-mot-de-passe.txt'

$id = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if ($id.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Ce script se lance SANS admin, depuis ta fenetre normale.'
}
if (-not (Test-Path $PyVenv)) { throw "Introuvable : $PyVenv (lance d'abord tessera.ps1 setup)" }

function Save-Secret([string]$Nom, [string]$Valeur) {
    # Par l'entree standard : jamais en argument ni a l'ecran (ADR-073).
    $Valeur | & $PyVenv -m tessera.coffre_cli set $Nom
    if ($LASTEXITCODE -ne 0) { throw "Echec du rangement de $Nom dans le coffre." }
}

function Set-AgentPassword {
    if (-not (Get-LocalUser -Name $Compte -ErrorAction SilentlyContinue)) {
        throw "Le compte $Compte n'existe pas : lance d'abord agent-setup-admin.ps1."
    }
    if (-not (Test-Path -LiteralPath $Remise)) {
        Write-Host '-> pas de fichier de remise : mot de passe deja range, on continue'
        return
    }
    $mdp = (Get-Content -LiteralPath $Remise -Raw).Trim()
    if ($mdp.Length -lt 24) { throw 'Fichier de remise illisible : relance agent-setup-admin.ps1.' }
    Save-Secret 'AGENT_LOGON_PASSWORD' $mdp
    # Pas de Remove-Item -Force : il veut changer les attributs, droit que ce compte n'a pas.
    [IO.File]::Delete($Remise)
    Write-Host '-> mot de passe range dans ton coffre (AGENT_LOGON_PASSWORD), fichier efface'
}

function Copy-AgentCli {
    $source = Join-Path $Racine 'backend\.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe'
    New-Item -ItemType Directory -Force -Path "$Partage\bin" | Out-Null
    Copy-Item $source "$Partage\bin\claude.exe" -Force
    Write-Host "-> CLI copie dans $Partage\bin"
    foreach ($d in @("$Moi\scoop\apps", "$Moi\AppData\Roaming\uv\python", "$Moi\.local\bin")) {
        if (Test-Path $d) {
            icacls $d /grant "${Compte}:(OI)(CI)RX" /Q | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "icacls a echoue ($LASTEXITCODE) sur $d" }
            Write-Host "-> lecture seule : $d"
        }
    }
}

function Set-AgentToken {
    Write-Host 'Lance `claude setup-token` sous ton compte, puis copie le jeton sk-ant-oat... affiche.'
    Write-Host '(copier une autre commande avant ecraserait le jeton)'
    Read-Host 'Entree une fois le jeton copie' | Out-Null
    $jeton = (Get-Clipboard -Raw)
    if ($jeton) { $jeton = ($jeton -replace '\s', '') }
    if (-not $jeton -or -not $jeton.StartsWith('sk-ant-oat')) {
        throw 'Le presse-papiers ne contient pas un jeton sk-ant-oat... : copie celui que claude setup-token a affiche.'
    }
    Save-Secret 'AGENT_OAUTH_TOKEN' $jeton
    Set-Clipboard -Value ' '
    Write-Host '-> jeton range dans ton coffre (AGENT_OAUTH_TOKEN), presse-papiers vide'
}

if ($Jeton) { Set-AgentToken; exit 0 }
Set-AgentPassword
Copy-AgentCli
Set-AgentToken
Write-Host '-> Installation terminee. Verifie : .\scripts\tessera.ps1 agent doctor'
