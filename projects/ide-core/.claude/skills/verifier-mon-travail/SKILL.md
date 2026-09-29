---
name: verifier-mon-travail
description: Use after writing or changing code on ide-core and before writing your report — runs the test files you touched, so a red test comes back to you instead of to the reviewer.
---

# Vérifier son travail sur ide-core

Le code de ce projet vit au-dessus de toi : `../../backend/` et `../../frontend/`.
Aucune étape du pipeline ne lance les tests sur ce projet. Si tu ne les lances
pas, personne ne le fera avant la PR.

## Ce que tu lances

**Les fichiers de test que tu as créés ou modifiés, et ceux du module touché.
Jamais la suite entière** : elle dure plusieurs minutes et te coûterait des
actions dont tu as besoin pour corriger.

Backend :

```bash
cd ../../backend && uv run python -m pytest tests/test_mon_module.py -q -p no:cacheprovider
```

Frontend, et le typage si tu as touché du TypeScript :

```bash
cd ../../frontend && npx vitest run src/chemin/mon-composant.test.tsx
cd ../../frontend && npx tsc -b --noEmit
```

## Ce que tu en fais

- **Rouge** : corrige, puis relance **le même** fichier. Trois essais au plus ;
  au-delà, arrête-toi et dis dans ton rapport ce qui reste rouge et pourquoi.
- **Vert** : recopie la ligne de résumé réelle (`12 passed in 3.1s`) dans la
  section « Vérification » de ton rapport. Pas de résumé inventé ou arrondi.
- **La commande ne démarre pas** (exécutable introuvable, dépendance absente) :
  ce n'est pas un test rouge. Dis-le tel quel, sans toucher au code pour ça.

## Ce que tu ne fais pas

- Pas de `uv sync`, `npm install` ni `npm ci` : l'environnement n'est pas à toi.
- Pas de `--update-snapshots`, pas de `-k` pour exclure un test qui échoue, pas
  de `skip` ajouté pour faire passer.
