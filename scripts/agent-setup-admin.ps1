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

# 4 bis. Chaine d'outils partagee (node, uv, python) : l'agent la lit et
#    l'execute, ne l'ecrit pas. Memes droits que $Partage, poses par SID,
#    heritage coupe : rien ne vient du profil de l'utilisateur.
$Outils = Join-Path $Partage 'toolchain'
New-Item -ItemType Directory -Force -Path $Outils | Out-Null
Invoke-Icacls $Outils /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" `
    "${Proprietaire}:(OI)(CI)M" "${Compte}:(OI)(CI)RX"
Invoke-Icacls $Outils /inheritance:r
Write-Host "-> $Outils pret ($Proprietaire : modifier, $Compte : lecture-execution, heritage coupe)"

# 5. Remise du mot de passe : le fichier nait avec son ACL finale (heritage
#    coupe ; SYSTEM et administrateurs, lecture-suppression pour l'utilisateur),
#    jamais lisible par un autre compte, meme un instant, avant d'y ecrire.
Remove-Item -LiteralPath $Remise -Force -ErrorAction SilentlyContinue
$Sec = New-Object System.Security.AccessControl.FileSecurity
$Sec.SetAccessRuleProtection($true, $false)
foreach ($Sid in 'S-1-5-18', 'S-1-5-32-544') {
    $Id = New-Object System.Security.Principal.SecurityIdentifier($Sid)
    $Sec.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($Id, 'FullControl', 'Allow')))
}
$Sec.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($Proprietaire, 'Read,Delete', 'Allow')))
$Flux = New-Object System.IO.FileStream($Remise, 'CreateNew', 'Write', 'None', 4096, 'None', $Sec)
try {
    $Octets = [System.Text.Encoding]::ASCII.GetBytes($mdp)
    $Flux.Write($Octets, 0, $Octets.Length)
} finally { $Flux.Dispose() }
$mdp = $null
Write-Host "-> mot de passe remis a $Proprietaire (fichier lu puis efface par agent-setup.ps1)"
Write-Host '-> Partie admin terminee. Ferme cette fenetre et lance agent-setup.ps1 depuis ta fenetre normale.'
