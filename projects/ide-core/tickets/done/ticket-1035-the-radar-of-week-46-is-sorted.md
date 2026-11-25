---
agent: codeur
created: 2026-11-20
depends_on: []
estimated_days: 0.25
id: ticket-1035
priority: low
status: done
title: The radar of week 46 is sorted and the daily journal ritual is added
type: docs
---

# ticket-1035 — Le radar de la semaine 46 est trié, le rituel du journal est ajouté

## Objectif

Premier passage du rituel `radar-hebdo` (ticket-1034) sur les exports de la
semaine 2026-W46, et ajout du rituel quotidien demandé par le projet carriere.

## Ce qui est fait

Fait **à la main** : lecture des exports et des dépôts, deux retouches de texte.

Neuf candidats confrontés aux dépôts, sur leur branche de base :

| Projet | Candidat | Suite |
|---|---|---|
| kadoomi | Better Auth 1.7.25 | écarté : 1.7.26 déjà installée |
| kadoomi | Next.js 16.4.6 | écarté : déjà installée |
| devinoo | retrait de `@types/bcryptjs` | écarté : absent du manifeste |
| devinoo | Next.js 16.4.6 | écarté : déjà installée |
| devinoo | décider du sort de `qrcode.react` | écarté : sans release depuis 23 mois, aucune raison de sécurité citée |
| tessera | relire Impeccable depuis `skill-v4.8.2` | fait ici, `docs/inspirations.md` |
| tessera | auditer `@monaco-editor/react` | écarté : dépendance sans release, aucune raison de sécurité citée |
| tessera | auditer `httpx` | écarté : même motif |
| tessera | inscrire `openai/codex-security` au registre | écarté : le registre ne porte que les outils dont une idée est reprise (un fichier dérivé est exigé), et rien n'en est repris |

- `docs/inspirations.md` : Impeccable relu jusqu'à `skill-v4.10.0`, rien de
  repris, la version reprise ne change pas.
- `rituels.md` : rituel `journal-du-jour`, chaque jour ouvré à 18:00
  (rythme `quotidien`, ticket-1033).

## Critères d'acceptation

- [x] `test_inspirations.py` passe.
- [x] `rituels.md` se lit sans erreur avec le rituel ajouté.

## Ce que ça ne fait pas

- La comparaison fichier par fichier de la guidance d'Impeccable reste à faire.
- Aucun ticket n'est écrit pour kadoomi ni devinoo : rien ne tenait.
