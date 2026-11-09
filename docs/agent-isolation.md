# Installer le compte agent sur un nouveau poste

Les agents peuvent tourner sous un compte Windows dédié, `tessera-agent`, réglé
par `AGENT_USER` (ticket-894). Ce guide l'installe sur un poste neuf. Windows
seulement : un conteneur jouera ce rôle ailleurs.

## Deux parties, car l'utilisateur n'est pas toujours administrateur

Sur un poste où ton compte n'est **pas** administrateur, une fenêtre élevée
tourne sous *un autre compte*, avec un autre profil et un autre coffre. La
partie admin ne lit donc rien dans ton profil et n'y écrit rien ; elle ne fait
que ce qui exige l'élévation.

| Partie | Script | Lancé par | Ce qu'elle fait |
|---|---|---|---|
| Admin | `scripts/agent-setup-admin.ps1` | un compte administrateur | crée le compte, le masque de l'écran de connexion, prépare `C:\ProgramData\Tessera\bin`, remet le mot de passe par un fichier lisible par toi seul |
| Utilisateur | `scripts/agent-setup.ps1` | toi, **sans** élévation | range le mot de passe dans ton coffre et efface le fichier, copie le CLI, donne la lecture-exécution sur les outils, range le jeton d'abonnement |

`agent-setup.ps1` refuse de tourner en administrateur : le coffre qu'il remplit
est celui de ton compte.

## Étapes

1. Dans un Windows PowerShell **administrateur** (le compte admin importe peu) :
   `powershell -ExecutionPolicy Bypass -File scripts\agent-setup-admin.ps1 -Proprietaire <ton compte>`
2. Ferme cette fenêtre. Dans ta fenêtre normale, depuis la racine du dépôt
   (`.\scripts\tessera.ps1 setup` d'abord si `backend\.venv` n'existe pas) :
   `.\scripts\tessera.ps1 agent setup`
3. Le script demande le jeton d'abonnement : lance `claude setup-token` sous ton
   compte, **copie le jeton affiché après** avoir lancé le script (copier une
   autre commande avant l'écrase), puis valide. Il est rangé sous
   `AGENT_OAUTH_TOKEN` et le presse-papiers est vidé.
4. Vérifie : `.\scripts\tessera.ps1 agent doctor`.

Changer d'abonnement : `.\scripts\tessera.ps1 agent jeton`.

## `agent doctor`

Il liste chaque point avec son remède : compte présent, mot de passe et jeton
dans le coffre, CLI partagé présent **et de la même version** que celui du SDK
installé, `uv` et `node` trouvés. Après une montée du SDK, la version du CLI
partagé diverge : relance `agent setup`, ou recopie à la main
`backend\.venv\Lib\site-packages\claude_agent_sdk\_bundled\claude.exe` vers
`C:\ProgramData\Tessera\bin\claude.exe`.

## Pièges connus

- Windows PowerShell 5.1 lit un script sans BOM en ANSI : les scripts sont en
  ASCII pur (un test le vérifie).
- `New-LocalUser -Description` est limité à 48 caractères.
- Le fichier de remise s'efface par `[IO.File]::Delete` : `Remove-Item -Force`
  exige le droit de changer les attributs, que ton compte n'a pas.
- Une saisie masquée de Windows PowerShell 5.1 ignore Ctrl+V : le jeton passe
  par le presse-papiers.
- Ces scripts créent un compte : la CI ne les exécute pas, la recette se fait à
  la main.
