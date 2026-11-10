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

# Un icacls qui echoue arrete le script : un droit mal pose ne se decouvre pas
# apres coup.
function Invoke-Icacls {
    & icacls @args /Q | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "icacls a echoue ($LASTEXITCODE) : $($args -join ' ')" }
}

# 4. Dossier partage : l'utilisateur y copie le CLI, l'agent le lit et l'execute.
#    Heritage coupe : C:\ProgramData donne a BUILTIN\Users le droit de creer des
#    fichiers, et tessera-agent en fait partie. Herite, ce droit lui laisserait
#    deposer une DLL a cote de claude.exe, chargee ensuite sous le compte de
#    l'utilisateur (`agent doctor`). Restent SYSTEM, les administrateurs, le
#    proprietaire (modifier) et l'agent (lecture).
New-Item -ItemType Directory -Force -Path "$Partage\bin" | Out-Null
Invoke-Icacls $Partage /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" `
    "${Proprietaire}:(OI)(CI)M" "${Compte}:(OI)(CI)RX"
Invoke-Icacls $Partage /inheritance:r
Invoke-Icacls "$Partage\bin" /reset /T
Write-Host "-> $Partage pret ($Proprietaire : modifier, $Compte : lecture, heritage coupe)"

# 5. Remise du mot de passe : le fichier est cree vide et verrouille AVANT d'y
#    ecrire, pour n'etre jamais lisible par un autre compte, meme un instant.
#    Ensuite lisible et supprimable par l'utilisateur seul (plus SYSTEM et les
#    administrateurs).
New-Item -ItemType File -Force -Path $Remise | Out-Null
Invoke-Icacls $Remise /inheritance:r
Invoke-Icacls $Remise /grant:r "*S-1-5-18:(F)" "*S-1-5-32-544:(F)"
Set-Content -LiteralPath $Remise -Value $mdp -NoNewline -Encoding ASCII
$mdp = $null
Invoke-Icacls $Remise /grant:r "${Proprietaire}:(R,D)"
Write-Host "-> mot de passe remis a $Proprietaire (fichier lu puis efface par agent-setup.ps1)"
Write-Host '-> Partie admin terminee. Ferme cette fenetre et lance agent-setup.ps1 depuis ta fenetre normale.'
