# Décisions d'architecture — archive

Les ADR qui ne contraignent plus rien : le code qu'ils décrivaient n'existe
plus, ou un ADR postérieur les a explicitement remplacés.

**Ce fichier n'est importé par aucun `CLAUDE.md` et n'est injecté dans aucun
appel d'agent.** Il est ici pour qu'on retrouve *pourquoi* une décision a été
prise, le jour où la question se repose — pas pour être lu à chaque run.

Les numéros ne sont jamais réattribués : un ADR archivé garde le sien, et
aucun ADR futur ne le reprend.

---

## ADR-016 — Scope filesystem Tauri : $HOME pour la v0

**Date** : 2026-06-20
**Portée** : architect  
**Décision** : Le plugin `tauri-plugin-fs` a accès à `$HOME/**` en v0.
**Raison** : Les projets Tessera seront dans `~/` (dossier utilisateur). Scope plus restrictif nécessiterait de connaître le chemin exact au build time.
**Alternative rejetée** : Scope filesystem complet `/` (trop large, rejeté par App Store), scope fixe `~/tessera-workspace/` (impose un emplacement).

---

**Archivé le 2026-09-23 (ticket-131)** — remplacé par **ADR-040** : l'app
Tauri n'expose plus aucune permission `fs:*`, donc il n'y a plus de scope
filesystem à définir. Le contrôle de chemin vit entièrement dans
`routers/fs.py`, côté backend.
