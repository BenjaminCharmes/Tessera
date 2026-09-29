---
name: new-ticket
description: Use when creating a ticket for this repository, or before starting any work that does not yet have one — no work starts without a ticket file, and the frontmatter must match the model enums or the project stops loading.
---

# Créer un ticket

## La règle qui a déjà été enfreinte

`CLAUDE.md` règles 1 et 2 : lire le ticket complet avant de coder, tenir son
statut à jour. Les tickets 044 et 045 ont été implémentés **sans fichier de
ticket** — le travail a été piloté par des plans `docs/superpowers/` au lieu du
backlog. Résultat : aucune traçabilité, statuts jamais mis à jour, tickets
rédigés rétrospectivement.

**Pas de ticket, pas de code.** Si le travail démarre sans, créer le ticket
d'abord — même court.

## Emplacement

`projects/<projet>/tickets/<statut>/ticket-XXX-slug-court.md`

Le **dossier porte le statut** : `todo/`, `in-progress/`, `in-review/`,
`done/`, `blocked/`. Changer de statut = déplacer le fichier **et** mettre à
jour le champ `status`. Les deux, sinon l'UI et le fichier divergent.

Numéro : le plus grand existant + 1, tous dossiers confondus.

## Frontmatter — valeurs valides uniquement

Le parsing coerce chaque champ vers son enum. Une valeur hors liste fait
échouer le chargement du projet entier.

```yaml
---
id: ticket-050
title: "Une phrase, entre guillemets"
type: feat          # feat | fix | chore | docs | refactor | test | design
status: todo        # todo | in-progress | in-review | done | blocked | cancelled
pr_number: null
priority: medium    # critical | high | medium | low
agent: codeur
depends_on: []      # ["ticket-047"] — des ids, pas des titres
estimated_days: 1
created: 2026-09-15
---
```

`type` n'est pas cosmétique : le pipeline le réutilise comme **préfixe du
message de commit** écrit dans le dépôt (`feat: ticket-050 — …`).

## Corps

```markdown
# ticket-050 — Titre

## Objectif
Une phrase. Ce que ça doit faire, et pour qui.

## Contexte
Ce qui existe déjà et pourquoi ça ne suffit pas. La contrainte réelle.

## Solution proposée
Assez pour qu'un agent démarre sans deviner. Pas le code.

## Critères d'acceptation
- [ ] …

## Dépendances
## Estimation
## Risques
```

## Les critères d'acceptation sont la partie qui compte

L'agent **validateur** les reprend un par un et vérifie chacun contre le diff
produit. C'est la seule partie du ticket qui est mécaniquement contrôlée.

| ❌ Invérifiable | ✅ Vérifiable |
|---|---|
| Le code est propre | `uv run mypy src/` passe sans erreur |
| Ça marche | `GET /health` renvoie 200 avec `{"status":"ok"}` |
| Les tests sont bons | Un test couvre le cas où le chemin est relatif |
| Bien documenté | `README.md` décrit la variable `LLM_PROVIDER` |

Un critère qu'on ne peut pas trancher par oui/non produit une validation molle
et un reviewer qui refuse en boucle.

**Pas de « `uv run pytest` passe » ni de « `npm run test` passe »** tant que le
testeur est désactivé sur le projet : le validateur ne reçoit alors aucun
résultat de test, juge le critère invérifiable, et depuis le ticket-209 un
critère invérifiable fait refuser le run (ticket-219). Nommer plutôt le test
qui doit exister ; faire tourner les suites relève de la vérification avant
merge.

## Portée

Un ticket = **un changement cohérent**. Si les critères d'acceptation couvrent
deux sujets sans rapport, ce sont deux tickets. Le symptôme classique :
« et aussi » dans l'objectif.

Le codeur a un nombre d'actions borné (`LLM_MAX_TURNS`) : chaque lecture,
recherche, édition ou lancement de test en consomme une. Un ticket qui touche
backend **et** frontend avec plus de six critères se découpe — le ticket-213
(quatre changements, neuf critères, deux couches) a épuisé ses trente actions
avant d'avoir fini.

## Avant de valider

- [ ] Le fichier est dans le dossier qui correspond à son champ `status`
- [ ] Chaque valeur de frontmatter est dans la liste autorisée
- [ ] Chaque critère d'acceptation se tranche par oui/non
- [ ] `depends_on` contient des ids existants
- [ ] Si le ticket doit toucher `CLAUDE.md`, il le dit **explicitement**
      (règle 5 : aucune modification sans ticket qui l'autorise)
