---
agent: codeur
created: 2026-11-11
depends_on: []
estimated_days: 0.5
id: ticket-925
pr_number: 1035
priority: medium
status: done
title: The Bash write guard skips heredoc bodies and resolves paths after a leading
  cd
type: fix
---

# ticket-925 — La garde d'écriture Bash saute le corps des heredocs et suit un `cd` de tête

## Objectif

Que la garde de périmètre ne refuse plus une écriture légitime dans le projet
à cause d'un heredoc ou d'un `cd` vers un sous-dossier.

## Contexte

Signalement d'un codeur d'Affût (ticket-097, 11/11) : depuis `backend/tests`,
un heredoc qui crée `fixtures/pages/*.html` a été refusé « chemin hors du
projet ».

Reproduit sur `cibles_ecrites` (`services/providers/redirections_bash.py`) :

- `cd backend/tests && cat > fixtures/pages/a.html <<'EOF'` suivi d'une ligne
  `<p>prix > 10</p> voir ../app/models.py` rend
  `['fixtures/pages/a.html', 'prix', '10', 'voir']` : le corps du heredoc est
  lu comme des commandes, et un `>` dans du HTML devient une redirection.
- `cd backend/tests && echo x > ../app/y.py` rend `['../app/y.py']`, que
  `hors_perimetre` (`services/providers/perimetre.py`) résout depuis la racine
  du run et non depuis `backend/tests` : une écriture dans le projet est
  refusée.

## Solution proposée

- `cibles_ecrites` ignore le corps d'un heredoc (`<<MOT`, `<<'MOT'`,
  `<<"MOT"`, `<<-MOT`) jusqu'à sa ligne de fin.
- Un `cd <chemin>` en tête de chaîne (`cd x && …`, `cd x; …`) rend les cibles
  suivantes relatives à ce dossier : elles sont préfixées par lui avant la
  résolution. Un `cd` qui ne se lit pas avec certitude (variable, `cd -`,
  sous-shell) laisse le comportement actuel.
- La garde reste ce qu'elle est (ADR-031) : elle attrape une erreur, pas une
  évasion.

## Critères d'acceptation

- [ ] Un test de `cibles_ecrites` vérifie que, pour un heredoc dont le corps
      contient `a > b`, seule la cible de la redirection de `cat` est rendue.
- [ ] Un test vérifie que `cd backend/tests && echo x > ../app/y.py` rend une
      cible qui se résout dans `backend/app/y.py`.
- [ ] Un test du hook de `services/providers/perimetre.py` vérifie que cette
      commande est acceptée pour un projet qui contient `backend/`.
- [ ] Un test vérifie que `cd backend && echo x > ../../dehors.txt` reste
      refusé.
- [ ] Un test vérifie que `cd "$X" && echo x > y` garde le comportement
      actuel (cible `y` résolue depuis la racine).

## Ce que ça ne fait pas

- Ne suit pas plusieurs `cd` successifs ni `pushd`.
- N'élargit pas ce que la garde voit : ce qui ne se lit pas avec certitude
  passe toujours.

## Dépendances

Aucune.

## Estimation

Une demi-journée.

## Risques

Un heredoc mal fermé : le corps court jusqu'à la fin de la commande, ce qui
ne rend aucune cible de plus qu'aujourd'hui.