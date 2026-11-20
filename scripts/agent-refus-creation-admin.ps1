# Refus de creation pour le compte agent dans les dossiers ouverts a tout
# utilisateur (ticket-1020, ADR-088 point 3). A lancer UNE fois dans un
# PowerShell administrateur :
#   powershell -ExecutionPolicy Bypass -File scripts\agent-refus-creation-admin.ps1
# Pour le defaire :
#   powershell -ExecutionPolicy Bypass -File scripts\agent-refus-creation-admin.ps1 -Retirer
# Il pose, pour le seul compte `tessera-agent`, une entree de refus
# 'creer un fichier, creer un dossier' sur chaque dossier de $Dossiers,
# heritee par leurs sous-dossiers. Il ne touche ni au compte, ni a son mot de
# passe, ni a son jeton, ni aux droits d'aucun autre compte. Le relancer ne
# change rien : un dossier qui porte deja le refus est laisse tel quel.
param(
    [switch]$Retirer,
    [string]$Compte = 'tessera-agent',
    # Les trois dossiers ou le compte creait un fichier (essai du 19/11).
    [string[]]$Dossiers = @('C:\Users\Public', 'C:\Windows\Temp', 'C:\ProgramData')
)
$ErrorActionPreference = 'Stop'

$Utilisateur = Get-LocalUser -Name $Compte -ErrorAction SilentlyContinue
if (-not $Utilisateur) { throw "Compte introuvable : $Compte" }
$Sid = $Utilisateur.SID.Value

# Vrai si le dossier porte, en propre, un refus pour le compte.
function Test-Refus([string]$Dossier) {
    $Regles = (Get-Acl -LiteralPath $Dossier).GetAccessRules($true, $false, [System.Security.Principal.SecurityIdentifier])
    foreach ($Regle in $Regles) {
        if ($Regle.IdentityReference.Value -eq $Sid -and $Regle.AccessControlType -eq 'Deny') { return $true }
    }
    return $false
}

# Tous les dossiers se verifient avant le premier changement.
foreach ($Dossier in $Dossiers) {
    if (-not (Test-Path -LiteralPath $Dossier -PathType Container)) { throw "Dossier introuvable : $Dossier" }
}

foreach ($Dossier in $Dossiers) {
    # icacls ajouterait une seconde entree identique : rien a faire si l'etat voulu est la.
    if ((Test-Refus $Dossier) -ne [bool]$Retirer) {
        Write-Host "-> $Dossier : deja fait, rien a changer"
        continue
    }
    if ($Retirer) {
        # /remove:d ne retire que les refus du compte, poses en propre sur ce dossier.
        & icacls $Dossier /remove:d "*$Sid" /Q | Out-Null
    } else {
        # (CI) : ce dossier et ses sous-dossiers. WD = creer un fichier,
        # AD = creer un dossier. Un sous-dossier dont l'heritage est coupe
        # (C:\ProgramData\Tessera, donc les worktrees et le profil du compte)
        # ne recoit rien.
        & icacls $Dossier /deny "*${Sid}:(CI)(WD,AD)" /Q | Out-Null
    }
    $Code = $LASTEXITCODE
    # La racine fait foi : un sous-dossier que l'administrateur ne peut pas
    # modifier fait echouer la propagation sans annuler l'entree posee.
    $Present = Test-Refus $Dossier
    if ($Present -eq [bool]$Retirer) { throw "icacls a echoue ($Code) sur $Dossier : rien n'a change" }
    if ($Code -ne 0) { Write-Warning "$Dossier : icacls a rendu $Code, des sous-dossiers n'ont pas suivi" }
    if ($Retirer) { Write-Host "-> $Dossier : refus retire" }
    else { Write-Host "-> $Dossier : $Compte ne peut plus y creer ni fichier ni dossier" }
}
Write-Host '-> Termine. Rien d autre n a ete modifie.'
