---
id: ticket-1023
title: "The agent account launches on a dedicated window station and desktop"
type: feat
status: todo
priority: high
agent: codeur
depends_on: []
preuve_reelle: true
---

# ticket-1023 — Le compte agent part sur une window station et un bureau dédiés

## Objectif

Appliquer ADR-089 : plus aucun processus du compte agent sur `WinSta0\Default`.

## Contexte

`lanceur_windows.py` laisse `lpDesktop` à `NULL` (ticket-944). La documentation
de `CreateProcessWithLogonW` précise que l'application doit elle-même donner au
compte l'accès à la station et au bureau nommés. Un module en `ctypes`, sans
pywin32 (ADR-083), crée donc la station et le bureau.

## Essai du 20/11, avant câblage

Fait sur le poste, hors dépôt, sous le compte agent, avec `pywin32` pour aller
vite (le module livré reste en `ctypes`) et le lanceur réel dont seul
`lpDesktop` était renseigné.

Avec `lpDesktop` à `NULL` (aujourd'hui), la sonde lancée sous le compte tourne
sur `WinSta0\Default`, lit le presse-papiers de l'utilisateur, injecte des
frappes (`SendInput` rend 2) et lit les pixels de l'écran.

Ce que l'essai a appris, et qui change la fiche :

- **Une station nommée est refusée** au backend, non administrateur
  (`CreateWindowStationW` avec un nom : erreur 5). Avec un nom `NULL`, Windows
  rend la station automatique de la session de logon, `Service-0x0-<luid>$`.
- **Cette station existe déjà, avec sa propre DACL** : les attributs de sécurité
  passés à la création sont ignorés, et le compte agent n'y a aucune entrée. Sans
  entrée, tout processus qui charge une DLL d'interface échoue (`0xC0000142`,
  ou « DLL load failed » pour `_ctypes`). Le backend peut y ajouter une entrée
  (il a `WRITE_DAC`) et la retirer.
- **Le bureau, lui, se crée par appel**, avec un nom et une DACL à lui (compte
  agent et backend seuls). `CreateDesktopW` crée dans la station du processus :
  il faut `SetProcessWindowStation` vers la station dédiée, créer, puis revenir.
- Droits : `0xF037F` sur la station et `0xF01FF` sur le bureau passent. Un jeu
  étroit (`0x20026` et `0x20087`) échoue (`0xC0000142`).

Sur la station dédiée, avec ces droits : la sonde rend la station
`Service-0x0-…$` et le bureau de l'appel ; `OpenWindowStationW("WinSta0")` est
refusé (erreur 5), `OpenDesktopW("Default")` introuvable, le presse-papiers est
vide, `SendInput` rend 0 (erreur 5), aucun pixel de l'écran n'est lu. Démarrent
et vont au bout : `node --version`, `uv run python`, `claude --version`, un appel
complet du CLI avec l'outil Bash, puis `npm ci`, `tsc`, `eslint`, les 193 tests
`vitest` et `vite build` de Serpent. Après les essais, la station ne porte plus
d'entrée du compte.

Non essayé : `uv run pytest` d'un projet et un Chromium de Playwright sous le
compte (aucun projet à compte agent n'en lance aujourd'hui, et le compte n'a pas
de navigateur installé).

## À faire

- Nouveau module `backend/src/tessera/services/providers/station_agent.py`, en
  `ctypes`, sans `pywin32` (ADR-083), typé strict, sous 200 lignes :
  - `ouvrir_bureau(sid_compte) -> BureauAgent` : ouvre la station automatique
    (`CreateWindowStationW(NULL, …)`), y ajoute l'entrée du compte si elle
    manque, crée un bureau au nom unique dont la DACL ne nomme que le SID du
    compte agent et celui du backend ; `BureauAgent.nom` rend
    `"<station>\<bureau>"`, lu par `GetUserObjectInformationW`.
  - `BureauAgent.fermer()` ferme le bureau ; quand le dernier bureau ouvert se
    ferme, l'entrée du compte est retirée de la station. Idempotent.
  - Le passage par `SetProcessWindowStation` se fait sous un verrou, et la
    station d'origine est toujours rétablie (`try/finally`).
  - Une entrée du compte déjà présente sur la station à l'ouverture (reste d'un
    backend arrêté net) est remplacée, pas doublée.
- `LanceurWindows._lancer` renseigne `StartupInfo.lpDesktop` avec ce nom ; le
  bureau vit tant que le job de l'appel vit et se ferme avec lui (ADR-087).
- Échec d'ouverture, de DACL ou de lancement : `EchecLancementCompte` (ou
  `ProviderIndisponible` au niveau du lanceur, comme aujourd'hui), jamais de
  repli sur `WinSta0\Default` (ADR-037). Le message nomme l'étape, sans mot de
  passe.
- Un `Protocol` pour l'ouverture du bureau, pour tester sans Windows.

## Critères d'acceptation

- [ ] `station_agent.py` expose `ouvrir_bureau` et `BureauAgent`, typés strict,
      sous 200 lignes, sans import de `pywin32`.
- [ ] `LanceurWindows` passe `lpDesktop` ; un test avec un faux fournisseur de
      bureau vérifie le nom reçu et la fermeture après la fermeture du job.
- [ ] Un test vérifie que l'échec d'ouverture du bureau lève et qu'aucun
      processus n'est lancé.
- [ ] Un test vérifie que l'entrée du compte n'est retirée de la station qu'à
      la fermeture du dernier bureau ouvert.
- [ ] Un test par fonction publique ; `mypy` et `pytest` passent.

## Preuve réelle

Sur la machine, avec le code du ticket, par un script hors dépôt dans
`~/.tessera/worktrees/manuel/` (aucun agent ne peut la fournir) :

1. Une sonde lancée sous le compte par le lanceur réel rend la station
   `Service-0x0-…$` et un bureau propre à l'appel ; `OpenWindowStationW("WinSta0")`
   est refusé ; le presse-papiers de l'utilisateur n'est pas lu ; `SendInput`
   rend 0 ; aucun pixel de l'écran n'est lu.
2. Démarrent encore : un appel complet du CLI avec l'outil Bash, `node
   --version`, et un run complet de Serpent (installation, tests, agents).
3. Après le dernier appel, la station ne porte plus d'entrée du compte agent,
   et le backend répond toujours (son propre processus est revenu sur sa
   station d'origine).

**Si l'un de ces démarrages échoue** : ne rien câbler, passer le ticket en
`blocked` avec le code d'erreur.

## Ce que ça ne fait pas

- Ne limite pas le réseau ni l'accès aux fichiers (ADR-083).
- Ne couvre pas le contrôle visuel en mode fenêtré : un navigateur non headless
  n'affiche rien sur le bureau de l'utilisateur, par construction.
