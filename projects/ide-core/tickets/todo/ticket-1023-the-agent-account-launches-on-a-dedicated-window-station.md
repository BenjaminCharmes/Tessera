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

## À faire

- Nouveau module `backend/src/tessera/services/providers/station_agent.py` :
  `creer_station(sid_compte) -> StationAgent` (`CreateWindowStationW`,
  `CreateDesktopW`, nom unique par appel, DACL qui n'ouvre que le SID du compte
  agent et le propriétaire — droits minimaux, ajustés par la preuve) ;
  `StationAgent.nom_bureau` (`"station\\bureau"`), `fermer()`.
- `LanceurWindows._lancer` renseigne `StartupInfo.lpDesktop` avec ce nom ; la
  station vit tant que le job de l'appel vit et se ferme avec lui (ADR-087).
- Échec de création, de DACL ou de lancement : `EchecLancementCompte`, jamais de
  repli sur `WinSta0\Default` (ADR-037). Le message nomme l'étape, sans mot de
  passe.
- Si une session antérieure a laissé un ACE du compte agent sur `WinSta0` ou
  `Default`, le backend le retire (c'est sa propre station) et le journalise.
- Un `Protocol` pour la création de station, pour tester sans Windows.

## Critères d'acceptation

- [ ] `station_agent.py` expose `creer_station` et `StationAgent`, typés strict,
      sous 200 lignes.
- [ ] `LanceurWindows` passe `lpDesktop` ; un test avec un faux fournisseur de
      station vérifie le nom reçu et la fermeture après `fermer()`.
- [ ] Un test vérifie que l'échec de création lève `EchecLancementCompte` et
      qu'aucun processus n'est lancé.
- [ ] Un test par fonction publique ; `mypy` et `pytest` passent.

## Preuve réelle

À lancer sur la machine, sous le compte de l'utilisateur, par un script hors
dépôt dans `~/.tessera/worktrees/manuel/` (aucun agent ne peut la fournir) :

1. Le backend écrit une valeur dans le presse-papiers, puis lance sous le compte
   agent un script qui appelle `GetClipboardData` : la valeur n'est **pas** lue.
2. Dans le processus agent, `OpenWindowStationW("WinSta0")` est refusé et
   `GetProcessWindowStationName` rend la station dédiée.
3. `SendInput` depuis le processus agent n'atteint pas le terminal au premier
   plan de l'utilisateur ; `BitBlt` sur le bureau ne rend pas l'écran de
   l'utilisateur.
4. Démarrent encore sur la station dédiée : le CLI Claude (un appel complet),
   `node --version`, `uv run pytest` d'un projet, un Chromium headless de
   Playwright qui charge une page locale.
5. Après l'appel, la station n'existe plus et la DACL de `WinSta0\Default` ne
   porte aucun ACE du compte agent.

**Si `CreateProcessWithLogonW` refuse un `lpDesktop` qui nomme une autre station,
ou si l'un des démarrages de l'étape 4 échoue** : ne rien câbler, passer le
ticket en `blocked` avec le code d'erreur, et rouvrir ADR-089 (le seul repli
sans privilège, `UILIMIT` du ticket-1024, ne ferme ni frappes ni capture).

## Ce que ça ne fait pas

- Ne limite pas le réseau ni l'accès aux fichiers (ADR-083).
- Ne couvre pas le contrôle visuel en mode fenêtré : un navigateur non headless
  n'affiche rien sur le bureau de l'utilisateur, par construction.
