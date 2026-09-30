---
id: ticket-248
title: "Le violet a une règle tranchée, appliquée et mesurée"
type: refactor
status: done
pr_number: null
priority: medium
agent: codeur
depends_on: []
estimated_days: 1
created: 2026-09-29
---

# ticket-248 — Le violet a une règle tranchée, appliquée et mesurée

## Objectif

Que le violet ne serve plus qu'à l'identité et à l'interaction, jamais comme
couleur de texte, et qu'un test le mesure pour que la dérive ne revienne pas.

## Contexte

ADR-026 dit « l'accent d'identité est une barre, jamais la couleur d'un mot »,
mais sa décision cite le « nom du projet » comme usage d'identité : l'ADR se
contredit. Résultat, le violet a dérivé : texte violet dans AgentBadge (moment
« pipeline »), RunView (`File : x/y`), DiffView (lignes de hunk), sélections
(`AgentList`, `TicketCard`, `ConversationSidebar`, `Editor`, `AgentDetail`,
`DiffView`, `NavRail`), nom du projet (`ProjectHeader:75`,
`SelecteurDeProjet:59`), liens Markdown en hex (`index.css:62`).
`design/coherence.test.ts` ne contrôle pas le violet, ne lit pas `index.css`,
et son commentaire cite un `tailwind.config` qui n'existe plus.

## Solution proposée

Règle tranchée : **le violet s'emploie en fond ou en barre** — identité
(barre de `RegionTitle`), sélection (`bg-violet-*/10`), action principale
(`bg-violet-600`) — **jamais en couleur de texte** dans les `.tsx`. Seule
exception : les liens du Markdown rendu, soulignés, définis uniquement dans
`index.css`. Amender la conséquence d'ADR-026 en ce sens (skill `write-adr`,
budget tenu). Remplacer chaque `text-violet-*` / `hover:text-violet-*` : texte
des sélections et nom du projet en `text-zinc-100`, badge « pipeline » en
zinc, `File : x/y` et hunks du diff en zinc. Étendre `coherence.test.ts` :
interdire `text-violet` dans les `.tsx`, lire `index.css` (hex violets admis
seulement sur `a` souligné et la bordure de citation), corriger le commentaire
`tailwind.config`.

## Critères d'acceptation

- [ ] Aucun `text-violet` ni `hover:text-violet` ne subsiste dans `frontend/src/**/*.tsx`
- [ ] Un test de `design/coherence.test.ts` échoue si on ajoute `text-violet-300` dans un composant
- [ ] Un test de `design/coherence.test.ts` lit `index.css` et n'admet les hex violets que sur les liens (soulignés) et la bordure de citation
- [ ] La conséquence d'ADR-026 énonce la règle fond-ou-barre et l'exception des liens, sans plus citer le nom du projet comme texte violet
- [ ] Le commentaire de `coherence.test.ts` ne mentionne plus `tailwind.config`
- [ ] Les boutons « Lancer la file » et « Enregistrer » gardent leur fond violet (`bg-violet-500/15`, action principale), seul leur texte passe en zinc

## Dépendances

Aucune.

## Estimation

1 jour.

## Risques

Changement purement visuel mais étendu (~12 fichiers) : vérifier à l'écran
que les sélections restent lisibles une fois le texte repassé en zinc.
