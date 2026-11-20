---
agent: codeur
created: '2026-11-12'
depends_on: []
id: ticket-959
priority: high
status: done
title: A relative Bash write target is resolved from the agent's folder, not from the write root
type: fix
---

# ticket-959 — Une cible d'écriture Bash relative se lit depuis le dossier de l'agent

## Signalement

- Source : agent:codeur@ticket-958
- Nature : bug
- Projet source : ide-core
- Catégorie : garde_trop_strict
- Composant : garde_perimetre

Run du ticket-958 (ide-core, 12/11 18:38) : le hook PreToolUse a refusé
`cd ../../backend/src/tessera && cat > services/pipeline/… <<'EOF'` (« chemin
hors du projet »), alors qu'ide-core déclare `git_root: ancestor`. Trois tours
sans code, la file s'est arrêtée avant le 957.

## Cause

`hors_perimetre` rattachait une cible relative à la **racine d'écriture**. Or
`cibles_ecrites` la calcule depuis le dossier de l'agent (son `cwd`, le
dossier du projet). Sans `ancestor` les deux coïncident ; avec, la cible
`../../backend/x` devenait `<dépôt>/../../backend/x`, hors du dépôt. Les
écritures `Write`/`Edit` en chemin absolu n'étaient pas touchées, d'où des
runs ide-core qui passaient le même jour.

## Correctif

La cible relative se rattache à `project_path` (le `cwd` de l'agent) ; la
comparaison reste faite contre la racine figée.

## Critères d'acceptation

- [x] Un test : sous une racine `ancestor`, `cd ../../backend && cat > m.py`
      et `echo x > ../../backend/m.py` passent depuis `projects/ide-core`.
- [x] Un test : une sortie du dépôt (`cd ../../.. && echo x > f`) reste refusée.
- [x] Les tests existants de la garde d'écriture passent sans changement.

## Ce que ça ne fait pas

- Ne change pas la racine d'écriture elle-même ni les fichiers protégés.
- Fait à la main : le pipeline d'ide-core butait sur ce défaut même.
