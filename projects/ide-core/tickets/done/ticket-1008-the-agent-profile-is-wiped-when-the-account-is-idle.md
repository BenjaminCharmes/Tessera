---
agent: codeur
depends_on: []
id: ticket-1008
preuve_reelle: true
priority: medium
status: done
title: The agent profile folder is wiped when the account is idle
type: fix
---

## Signalement

- Suite du ticket-998 (ADR-087), constat M3 : `~/.bashrc`, `~/.npmrc`,
  `%APPDATA%\uv\uv.toml`, `.pth` utilisateur persistent d'un appel à l'autre.

## Ce qu'il faut faire

- `services/providers/env_agent.py` : `profil_de(compte)` vise
  `C:\ProgramData\Tessera\profil-agent\` (constante, comme `CLI_PARTAGE`) ;
  `HOME`, `USERPROFILE`, `APPDATA`, `LOCALAPPDATA`, `TEMP`, `TMP` en dérivent.
  Les caches `npm-cache` et `uv\cache` vivent dans ce dossier mais **survivent**
  au nettoyage (installation du worktree rapide, preuves d'intégrité des
  lockfiles) ; le dire dans la docstring.
- Nouveau module `services/providers/profil_agent.py` : `reinitialiser_profil()`
  supprime tout le dossier sauf ces deux caches, le recrée, et rend au compte
  `M` dessus (`icacls`, injectable). Aucun lien ne se suit (`/L`, comme ticket-996).
- Appelé quand le dernier appel du compte se ferme (`clore_appel`, après l'arrêt
  des processus restants) et au démarrage du backend. Un échec lève
  `DroitsAgentRefuses` (ADR-037).
- `agent setup` (`scripts/agent-setup-admin.ps1`) crée le dossier avec ses droits ;
  `agent doctor` constate qu'il existe et que le compte y écrit.

## Critères d'acceptation

- [ ] `env_de_l_agent` ne contient plus `C:\Users\<compte>` ; toutes les clés de profil visent le dossier partagé.
- [ ] `reinitialiser_profil` supprime un `.bashrc`, un `.npmrc`, un `uv.toml` posés dans le dossier et garde les deux caches.
- [ ] `clore_appel` l'appelle au dernier appel, jamais tant qu'un appel est actif.
- [ ] Un échec de suppression lève `DroitsAgentRefuses`.
- [ ] Sans `AGENT_USER`, rien n'est touché.

## Preuve réelle

Faire écrire `~/.bashrc` et `%APPDATA%\uv\uv.toml` par un appel ; au suivant,
constater qu'ils n'existent plus ; constater que `npm install` d'un projet connu
réutilise le cache.

### Faite le 19/11, sur le poste, sous le compte agent

Le run s'est bloqué au troisième tour sur une remarque juste du reviewer
(`Path` sur des chemins Windows, faux sous Linux). Fini à la main : `ntpath`
dans `_recreer`, un test, et le contrôle total du propriétaire sur le dossier
dans `agent-setup-admin.ps1` (il y repose le droit du compte à chaque
nettoyage, ce que « modifier » ne permet pas à qui n'est pas propriétaire).

- Un appel écrit `~/.bashrc`, `~/.npmrc` et `uv.toml` sous `%APPDATA%` : à sa
  clôture ils n'existent plus, et l'appel suivant ne les voit pas. Le dossier
  temporaire est recréé.
- `npm ci` de Serpent : 29 s, cache vide. Le cache (1 484 entrées) survit à
  la clôture ; `npm ci --offline` aboutit ensuite, sans réseau.
- Sur ce poste, le dossier `profil-agent` a été créé à la main sous le
  dossier partagé de Tessera, avec les droits du script : `agent setup`
  n'est pas à relancer.

Limite relevée : un fichier dont l'agent a refermé les droits dans un
sous-dossier qu'il a créé fait échouer le nettoyage. Le run passe en
`blocked` (échec fermé) et le fichier se retire à la main.

## Ce que ça ne fait pas

- Ne traite pas la ruche `HKCU` (ticket-1009).
- Ne vérifie pas le contenu des caches au-delà de l'intégrité que npm et uv appliquent eux-mêmes.