---
agent: codeur
created: 2026-11-10
depends_on: []
estimated_days: 1
id: ticket-902
pr_number: null
priority: high
status: done
title: Recurring rituals are read from a versioned file, their done state kept per
  PC
type: feat
---

# ticket-902 — Les rituels se lisent dans un fichier versionné, leur état « fait » reste sur chaque PC

## Objectif

Que le backend dise, pour chaque action récurrente de Benjamin (point revenus,
point hebdo, relevé marché…), si elle est en retard, faite ou à venir, à partir
d'une liste qui suit le dépôt sur n'importe quel PC.

## Contexte

Les rappels vivent aujourd'hui dans des tâches planifiées Windows (une fenêtre
`msg.exe` qu'un clic ferme pour de bon), une routine liée à un compte Anthropic
et la mémoire d'une session : changer de PC ou de compte les perd tous, et une
notification fermée ne revient pas. Benjamin a choisi le 10/11 de tout
centraliser dans Tessera, l'app qu'il ouvre chaque jour sur chaque poste.

La liste est déjà écrite : `rituels.md`, à la racine du dépôt, porte les
rituels dans son frontmatter YAML et décrit le format dans son corps. Ce
ticket la lit ; il ne la modifie pas. L'écran et le bandeau sont le ticket-903,
d'après la maquette `projects/ide-core/design/maquette/Rituels.dc.html`.

## Solution proposée

- **Lecture** : un module `services/projets/rituels.py` lit `rituels.md` à la
  racine du dépôt (`_REPO_ROOT` de `config.py`) avec `python-frontmatter`, comme
  les tickets, et valide chaque entrée par un modèle Pydantic v2 (rythme en
  union discriminée sur `type` : `hebdo`, `mensuel`, `unique`). Fichier absent :
  liste vide. Fichier ou entrée invalide : liste vide et un message `erreur`
  dans la réponse, jamais une 500.
- **Échéances**, en heure locale du PC, par une fonction pure qui prend
  « maintenant » en paramètre (testable sans horloge) :
  - `derniere` : la dernière échéance passée (`None` pour un `unique` dont `du`
    n'est pas encore atteint) ; `prochaine` : la suivante (`None` pour un
    `unique` déjà commencé).
  - `statut` : `fait` si `fait_le >= derniere` ; sinon `a_venir` si
    `derniere is None` ou si `reporte_jusqua > maintenant` ; sinon `en_retard`.
  - `depasse` : vrai pour un rituel `en_retard` dont la limite est passée
    (`avant` d'un `mensuel`, `au` d'un `unique`).
- **État local** : une migration ajoutée à `_MIGRATIONS` de
  `services/noyau/database.py` crée `rituels_etat (id TEXT PRIMARY KEY,
  fait_le TEXT, reporte_jusqua TEXT)`. L'état ne part jamais dans le dépôt.
- **Routes** (`routers/rituels.py`, monté sous `/api/v1`) :
  - `GET /rituels` → `{"rituels": [...], "erreur": null}` ; chaque rituel
    porte ses champs du fichier plus `statut`, `derniere`, `prochaine`,
    `depasse`, `fait_le`, `reporte_jusqua` (ISO 8601), triés : en retard
    d'abord, par `derniere` croissante, puis le reste par `prochaine`.
  - `POST /rituels/{id}/fait` pose `fait_le = maintenant` et efface le report.
  - `POST /rituels/{id}/reporter` pose `reporte_jusqua = maintenant + 24 h`.
  - Un `id` absent du fichier → 404.

## Critères d'acceptation

- [ ] `backend/src/tessera/services/projets/rituels.py` lit `rituels.md` à la
      racine du dépôt ; un test vérifie qu'un fichier absent donne une liste
      vide, et qu'un rythme de `type` inconnu donne une liste vide et un
      `erreur` non nul.
- [ ] Un test de la fonction d'échéances, à « maintenant » fixé au mardi
      2026-11-10 12:00, vérifie : un `hebdo` lundi 18:30 jamais fait est
      `en_retard` avec `derniere` = 2026-11-09T18:30 ; le même avec `fait_le`
      = 2026-11-09T20:00 est `fait` ; un `mensuel` jour 18 `avant` 22 est
      `fait` ou `en_retard` selon `fait_le`, et `depasse` est vrai pour
      « maintenant » = 2026-11-23 sans `fait_le` ; un `unique` du 2026-11-23
      est `a_venir` avec `derniere` nul.
- [ ] Un test vérifie qu'un `reporte_jusqua` dans le futur rend `a_venir` un
      rituel qui serait `en_retard`.
- [ ] La migration de `rituels_etat` est ajoutée à la fin de `_MIGRATIONS` dans
      `backend/src/tessera/services/noyau/database.py`.
- [ ] Un test de route vérifie que `POST /api/v1/rituels/{id}/fait` puis
      `GET /api/v1/rituels` rend ce rituel `fait`, et qu'un `id` inconnu rend 404.
- [ ] Le diff ne modifie pas `rituels.md`.

## Ce que ça ne fait pas

- Pas d'écran : ticket-903.
- Pas de détection automatique du « fait » (une note Carrière de la semaine qui
  existe, par exemple) : chaque app a sa base, un ticket suivant si le besoin
  se confirme.
- Pas de synchronisation de l'état entre PC : la liste suit le dépôt, l'état
  reste local. Un rituel fait sur un poste peut réapparaître sur un autre.
- Pas d'édition des rituels depuis l'interface : le fichier s'édite à la main.
- Un rituel jamais fait apparaît en retard à sa dernière échéance passée dès
  sa première lecture.

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

- Calcul des échéances autour d'un changement d'heure : heures locales
  naïves, une heure d'écart au pire sur deux jours par an, accepté.