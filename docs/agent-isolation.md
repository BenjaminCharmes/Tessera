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

## Variables d'environnement du compte

Le compte agent `tessera-agent` a un profil unique chez `C:\ProgramData\Tessera\profil-agent`, géré par l'IDE. Entre deux appels du compte, ce profil est entièrement vidé sauf deux caches :
- `npm-cache/` : npm peut réutiliser les dépendances installées
- `uv\cache/` : uv peut réutiliser ses wheels

Cela permet aux worktrees de démarrer rapidement — `npm install` ou `uv sync` vérifieront l'intégrité des lockfiles mais utiliseront les archives en cache si elles sont saines.

Concrètement, quand `vitest` ou `npm ci` tourne sous le compte agent :
- `HOME` = `C:\ProgramData\Tessera\profil-agent`
- `TEMP` = `C:\ProgramData\Tessera\profil-agent\AppData\Local\Temp`
- `APPDATA` = `C:\ProgramData\Tessera\profil-agent\AppData\Roaming`
- `LOCALAPPDATA` = `C:\ProgramData\Tessera\profil-agent\AppData\Local`
- `npm_config_cache` = `C:\ProgramData\Tessera\profil-agent\npm-cache`
- `UV_CACHE_DIR` = `C:\ProgramData\Tessera\profil-agent\uv\cache`

**Aucune pollution entre appels** : un `.bashrc`, `.npmrc` ou fichier Python `.pth` qu'un appel aurait écrit n'existe plus au suivant. Le profil vierge repart à chaque fois.

**Tu n'as rien à faire.** L'IDE gère cela automatiquement quand il lance les outils sous le compte agent.

## La ruche Windows n'est pas chargée

Le compte agent démarre ses processus **sans charger la ruche HKCU** (`HKEY_CURRENT_USER`). Cela empêche un `AutoRun` ou toute autre clé de l'environment de survivre d'un appel à l'autre.

L'environnement du compte est bâti de zéro à chaque appel — aucune pollution Registry, aucune persistance involontaire.

## Protection du profil et des worktrees

Le compte agent dispose de plusieurs protections contre les contournements de droits et les tentatives de redéfinition de l'isolation :

**Nettoyage du profil**

Après chaque appel, le profil du compte est entièrement vidé sauf deux caches (npm et uv). Le nettoyage restaure les droits via `icacls /setowner` suivi de `/reset /T /C /L`, qui remet une DACL propre. Les droits du compte et une ACE `OWNER RIGHTS` sont ensuite reposés. Si le nettoyage échoue — par exemple, parce qu'un fichier reste inaccessible — l'IDE refuse tout appel suivant sous le compte. `agent doctor` le détecte et propose de réinitialiser le profil.

**Isolation stricte du worktree**

La racine d'un run n'est jamais calculée en remontant à la recherche d'un `.git`. Elle est définie comme l'enfant direct du dossier des worktrees du projet : `<dossier des worktrees>/<projet>/<ticket>`. Un agent qui crée un `.git` dans un sous-dossier ne peut donc pas redéfinir où les droits s'appliquent. Si le `.git` de la racine est une jonction NTFS ou un symlink, l'IDE refuse l'appel. Cela empêche un agent de créer un lien vers le profil d'un utilisateur ou un autre emplacement sensible.

**Icacls sans suivi de jonctions**

Tous les appels `icacls` portent le flag `/L` pour opérer sur le lien lui-même, jamais sur sa cible. Un agent ne peut donc pas modifier les droits d'un profil d'utilisateur en créant une jonction vers lui.

Sans `AGENT_USER` configuré, aucune de ces protections ne s'applique : l'IDE tourne sous ton compte, avec tes droits.

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
