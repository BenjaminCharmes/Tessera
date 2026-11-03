---
name: write-adr
description: Use when recording a non-trivial architecture decision in memory/decisions.md — enforces the house format and the length budget, because every ADR is read by people and, when contraintes.md is missing, by agents.
---

# Écrire un ADR

## Le coût caché — lire ceci en premier

Chaque appel d'agent reçoit `memory/contraintes.md`, réduit au rôle appelé
(`services/adr.py`, ticket-311) ; `memory/decisions.md` ne part qu'en repli,
sur un projet sans `contraintes.md`. Sur un ticket qui va au bout, c'est
jusqu'à 18 appels. Une règle de `contraintes.md` coûte donc à chaque appel,
et un ADR long coûte à chaque lecteur, et à chaque appel d'un projet en repli.

Un ADR long n'est pas un défaut de style. C'est une taxe permanente.

Depuis ticket-087, `services/adr.py` réduit la section aux ADR qui concernent
le rôle appelé. Ça n'annule pas le budget : un ADR **sans portée** — donc
toute contrainte de comportement — continue de partir dans les 18 appels.

## Budget

| | Mots |
|---|---|
| Décision structurante, avec conséquence assumée | **≤ 160** |

Si tu dépasses, tu écris une spec, pas un ADR. La spec va dans le ticket.

**Le budget est mesuré.** `backend/tests/test_consignes_coherentes.py` refuse
tout ADR au-dessus de 160 mots, et vérifie que chacun porte sa `**Date**` et
sa `**Décision**`. Douze des trente et un ADR de l'époque le dépassaient avant qu'il
existe, dont trois écrits le jour même où ce fichier le rappelait : un budget
que rien ne mesure n'est pas un budget, c'est un souhait.

## Format

```markdown
## ADR-0XX — Titre à l'impératif, pas de nom de ticket

**Date** : AAAA-MM-JJ
**Portée** : rôles concernés   ← seulement si l'ADR enregistre un choix passé
**Décision** : Ce qui est décidé. Au présent, à l'actif.
**Raison** : Pourquoi, en pointant la contrainte réelle qui force le choix.
**Alternative rejetée** : Ce qu'on n'a pas fait, et ce qui le disqualifie.
**Détail** : voir `tickets/.../ticket-XXX-....md`   ← si le sujet est vaste
```

Deux lignes optionnelles, seulement quand elles portent une information qu'on
regretterait de perdre :

- **Conséquence assumée** — un effet indésirable accepté en connaissance de
  cause (exemple : ADR-018 écrit du code bloqué par la sécurité dans
  l'historique git).

## Portée : une question, une seule

**« Un agent qui ne lit pas cet ADR peut-il mal se comporter ? »**

- **Oui** → pas de `**Portée**`. L'ADR part à tous les agents. C'est le cas de
  toutes les contraintes : git, artefacts, périmètre d'écriture, commits,
  plafonds. Une contrainte qu'un agent n'a pas lue n'en est plus une.
- **Non, il enregistre un choix déjà fait** → `**Portée**` avec les rôles qui
  auraient à le rediscuter. Pourquoi `uv` plutôt que Poetry, pourquoi Tauri
  plutôt qu'Electron, comment `ProjectLoader` est structuré : `architect`,
  parfois `codeur` et `reviewer`.

Dans le doute, **pas de portée**. Un ADR de trop dans un prompt coûte des
tokens ; un ADR manquant coûte un comportement.

`test_adr_pertinents.py` refuse une portée posée sur une contrainte de
comportement, et exige une portée sur les choix passés. Les deux listes y sont
**explicites** et ne se mettent pas à jour seules : un ADR nouveau s'ajoute à
l'une ou à l'autre le jour où il est écrit — elles se sont arrêtées à ADR-031
pendant que cinq contraintes s'écrivaient sans protection.

## Ce qui n'a rien à faire dans un ADR

| À écrire ailleurs | Où |
|---|---|
| Le détail d'implémentation | Le ticket |
| Les invariants à respecter dans le code | Un commentaire, à l'endroit où ils s'appliquent |
| La liste des fichiers touchés | Le message de commit |
| Le mode d'emploi | `docs/guide-utilisateur.md` |

## Numérotation

Prendre le numéro suivant le plus élevé du fichier. Les ADR ne sont pas
réordonnés ni renumérotés — ADR-011 apparaît après ADR-015 dans le fichier,
c'est l'ordre d'écriture, il n'a pas d'importance. Un numéro archivé
(`memory/decisions-archive.md`) n'est jamais réattribué : le prochain ADR
prend le suivant, pas le trou.

## Avant de valider

- [ ] Sous 160 mots
- [ ] La ligne « Alternative rejetée » dit pourquoi elle est rejetée, pas
      seulement laquelle
- [ ] Aucun détail d'implémentation qui vivrait mieux dans le ticket
- [ ] Le titre se comprend sans lire le corps
