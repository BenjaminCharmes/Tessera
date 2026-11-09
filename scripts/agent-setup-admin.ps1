# Partie ADMIN de l'installation du compte agent. A lancer EN PREMIER dans un
# Windows PowerShell (5.1) administrateur, quel que soit le compte admin.
#   powershell -ExecutionPolicy Bypass -File scripts\agent-setup-admin.ps1 -Proprietaire <compte>
# Elle ne lit ni n'ecrit rien dans le profil de l'utilisateur : elle cree le
# compte `tessera-agent`, le masque de l'ecran de connexion, prepare
# C:\ProgramData\Tessera\bin et remet le mot de passe par un fichier que
# l'utilisateur seul peut lire. agent-setup.ps1 le range dans son coffre.
param([Parameter(Mandatory = $true)][string]$Proprietaire)
$ErrorActionPreference = 'Stop'
$Compte  = 'tessera-agent'
$Partage = 'C:\ProgramData\Tessera'
$Remise  = Join-Path $Partage 'remise-mot-de-passe.txt'

if (-not (Get-LocalUser -Name $Proprietaire -ErrorAction SilentlyContinue)) {
    throw "Compte proprietaire introuvable : $Proprietaire"
}

# 1. Mot de passe aleatoire (32 caracteres, les quatre classes).
$jeu = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!#%+-=@_'
$rng = [Security.Cryptography.RandomNumberGenerator]::Create()
$octets = New-Object byte[] 28
$rng.GetBytes($octets)
$mdp = 'Aa7!' + (-join ($octets | ForEach-Object { $jeu[$_ % $jeu.Length] }))
$secure = ConvertTo-SecureString $mdp -AsPlainText -Force

# 2. Compte local, simple utilisateur, mot de passe sans expiration.
if (-not (Get-LocalUser -Name $Compte -ErrorAction SilentlyContinue)) {
    # -Description est limite a 48 caracteres.
    New-LocalUser -Name $Compte -Password $secure -PasswordNeverExpires -UserMayNotChangePassword `
        -Description 'Tessera : execute les agents IA' | Out-Null
    # Groupe Utilisateurs par son SID, quel que soit son nom local.
    Add-LocalGroupMember -SID 'S-1-5-32-545' -Member $Compte
} else {
    Set-LocalUser -Name $Compte -Password $secure
}
Write-Host "-> compte $Compte pret"

# 3. Masque de l'ecran de connexion.
$cle = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList'
New-Item -Path $cle -Force | Out-Null
New-ItemProperty -Path $cle -Name $Compte -Value 0 -PropertyType DWord -Force | Out-Null
Write-Host '-> compte masque de l ecran de connexion'

# 4. Dossier partage : l'utilisateur y copie le CLI, l'agent le lit et l'execute.
New-Item -ItemType Directory -Force -Path "$Partage\bin" | Out-Null
icacls $Partage /grant "${Proprietaire}:(OI)(CI)M" /Q | Out-Null
icacls $Partage /grant "${Compte}:(OI)(CI)RX" /Q | Out-Null
Write-Host "-> $Partage pret ($Proprietaire : modifier, $Compte : lecture)"

# 5. Remise du mot de passe : fichier sans heritage, lisible et supprimable par
#    l'utilisateur seul (plus SYSTEM et les administrateurs).
Set-Content -LiteralPath $Remise -Value $mdp -NoNewline -Encoding ASCII
$mdp = $null
icacls $Remise /inheritance:r /Q | Out-Null
icacls $Remise /grant:r "${Proprietaire}:(R,D)" "*S-1-5-18:(F)" "*S-1-5-32-544:(F)" /Q | Out-Null
Write-Host "-> mot de passe remis a $Proprietaire (fichier lu puis efface par agent-setup.ps1)"
Write-Host '-> Partie admin terminee. Ferme cette fenetre et lance agent-setup.ps1 depuis ta fenetre normale.'
