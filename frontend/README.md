# frontend — l'UI de Tessera

Interface React de Tessera : le cockpit depuis lequel on lance les agents, lit
leurs diffs et suit les runs. Elle parle au backend FastAPI en HTTP et en
WebSocket ; elle ne fait aucun appel LLM elle-même.

La même base sert dans le navigateur et dans l'application desktop — Tauri
charge ce bundle, il n'existe pas de seconde UI (ADR-004).

## Lancer

Depuis la racine du dépôt, jamais depuis ce dossier :

```bash
make dev            # le backend, sur http://localhost:8000
make dev-frontend   # cette UI, sur http://localhost:5173
```

L'UI sans le backend affiche une liste de projets vide : ce n'est pas une
panne, c'est un `fetch` qui échoue.

## Vérifier

```bash
npm run typecheck      # tsc --noEmit, strict
npm run test           # Vitest + Testing Library
npm run test:e2e       # Playwright, nécessite le backend lancé
npm run build          # bundle de production dans dist/
```

## Ce qu'il faut savoir avant d'écrire du code ici

- **`strict: true`, jamais de `any`.** Les types de l'API vivent dans
  `src/types/api.ts` et suivent les modèles Pydantic du backend.
- **Les couleurs ne se choisissent pas au cas par cas.** Cinq familles portent
  les états — `zinc`, `red`, `amber`, `green`, `blue` — et `violet` porte
  l'identité, jamais un état (ADR-026). Un test verrouille la règle, parce
  qu'une palette non mesurée dérive d'un ticket à l'autre.
- **Les bandes d'en-tête ont une hauteur unique**, le token `BAND` de
  `src/design/layout.ts`. Sur quatre colonnes côte à côte, un écart de deux
  pixels se voit tout de suite.
- **Pas de gestionnaire d'état global** (ADR-013) : l'état partagé tient dans
  `useActiveProject`, les autres hooks sont autonomes.
- **Monaco est bundlé, pas chargé depuis un CDN** (ADR-012) : une application
  desktop packagée n'a pas d'accès réseau garanti.

Les contraintes en vigueur sont dans `projects/ide-core/memory/decisions.md`.
