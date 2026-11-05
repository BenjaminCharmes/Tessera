---
id: ticket-810
title: "A gear button at the foot of the rail opens the settings"
type: feat
status: todo
pr_number: null
priority: low
agent: codeur
depends_on: ["ticket-808"]
estimated_days: 1
created: 2026-11-05
---

# ticket-810 — Un bouton engrenage au pied du rail ouvre les réglages

## Objectif

Les cinq réglages se lisent et se changent depuis un panneau du rail, avec ce qui s'applique quand.

## Contexte

ADR-075, design §6. Le bouton « Réglages » du rail a été retiré (ticket-779) parce qu'il ne
montrait que des valeurs. `IconSettings` existe mais se lit comme un soleil : il n'est pas réutilisé.

## Ce que le ticket fait

- Une maquette de la fenêtre d'abord, dans `design/maquette/` (règle du projet pour toute interface).
- `frontend/src/design/icons.tsx` : `IconEngrenage`, une vraie roue dentée (huit dents, un moyeu
  percé) ; `IconSettings` reste intact.
- `frontend/src/lib/apiReglages.ts` et `frontend/src/hooks/useReglages.ts` : lecture, `ecrire`,
  `retirer`, erreurs 403 / 404 / 422 rendues en texte.
- `frontend/src/components/Sidebar/BoutonReglages.tsx` : le même ressort que `Cloche` (popover,
  `useFermetureAuDehors`), `aria-label="Réglages"`, `aria-haspopup="dialog"`. Placé sous la cloche
  dans `NavRail.tsx`, hors du `tablist`.
- `frontend/src/components/Sidebar/PanneauReglages.tsx` : une ligne par réglage — libellé, champ
  (nombre ou case à cocher), défaut de `.env`, « Appliquer », « Revenir au défaut » si `modifie`, effet
  en clair (« au prochain run », « dès la prochaine suite de tests ») ; si `runs_ouverts > 0`, « N run(s)
  gardent l'ancienne valeur ».
- ADR-026 : états en `zinc`, `red`, `amber`, `green`, `blue` ; le violet en fond ou en barre seulement.

## Tests

- `NavRail.test.tsx` : `renders_the_settings_button_below_the_bell_outside_the_tablist`
- `BoutonReglages.test.tsx` : `opens_and_closes_the_panel`, `closes_on_a_click_outside`
- `PanneauReglages.test.tsx` : `shows_five_rows_with_their_default`,
  `applies_a_value_with_a_put`, `resets_a_setting_with_a_delete`,
  `shows_the_effect_in_plain_words`, `shows_how_many_runs_keep_the_old_value`,
  `shows_the_error_message_for_a_422_and_a_403`, `does_not_offer_zero_for_a_budget`
- `icons.test.tsx` (ou équivalent) : `icon_engrenage_renders_an_aria_hidden_svg`
- `useReglages.test.ts` : `reloads_after_a_write`

## Critères d'acceptation

- [ ] Les tests ci-dessus passent ; `npm run build`, `tsc`, `eslint` et vitest sont verts
- [ ] Le test de couleurs d'ADR-026 passe
- [ ] Une capture du panneau ouvert à 1536 px est jointe au run

## Ce que ça ne fait pas

Aucun réglage par projet, aucun secret : le panneau n'en montre jamais.
