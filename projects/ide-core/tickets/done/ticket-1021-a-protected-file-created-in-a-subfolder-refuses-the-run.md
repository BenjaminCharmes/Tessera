---
agent: codeur
id: ticket-1021
pr_number: 1195
priority: medium
status: done
title: A protected file created in a subfolder refuses the run
type: feat
---

# ticket-1021 — Un fichier protégé créé en sous-dossier refuse le run

## Objectif

ADR-088, point 4. L'empreinte d'ADR-084 (`pipeline_empreinte.py`) ne hache que
les fichiers protégés qui existent au début du run : un `CLAUDE.md`, un
`.mcp.json` ou un `.claude/settings.json` créé dans un sous-dossier n'a pas
d'empreinte avant, donc aucune différence à constater.

## Ce qu'il faut faire

- Après chaque appel, lister les fichiers ajoutés (`git status --porcelain`
  avec `core.fsmonitor=false`, fichiers non suivis dépliés) et passer chacun à
  `motif_de_protection` (`services/providers/chemins_proteges.py`).
- Un fichier ajouté dont le motif n'est pas `None` termine le run `blocked`
  avec commit (ADR-037), même motif nommant le chemin sans contenu.
- Le contrôle part au même endroit que l'empreinte, avant la lecture du diff
  au tour du codeur.

## Critères d'acceptation

- [ ] Un test : un `CLAUDE.md` créé dans `sous/dossier/` pendant un appel
  met le run en `blocked`.
- [ ] Un test : un `.mcp.json` créé dans un sous-dossier fait de même.
- [ ] Un test : un fichier ordinaire ajouté ne change rien.
- [ ] Un test : un `CLAUDE.md` déjà suivi par git et inchangé ne déclenche
  rien.

## Ce que ça ne fait pas

- Ne change pas la liste des fichiers protégés ; n'empêche pas l'écriture,
  la constate (comme ADR-084).