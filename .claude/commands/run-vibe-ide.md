---
description: Lance vibe-ide en local (backend + frontend) et vérifie qu'il sert vraiment
---

Lance vibe-ide en local et vérifie qu'il sert réellement.

Utilise le skill `run-vibe-ide` : il couvre la détection des processus déjà en
cours, le piège du worker `--reload` orphelin, et les vérifications qui vont
au-delà de `/health`.

Arguments éventuels : $ARGUMENTS
