---
name: run-tessera
description: Use when asked to launch, start, restart or stop Tessera locally, or to check whether the backend and frontend are actually serving — covers the port-8000 and orphaned-worker traps that make a "running" server serve stale code.
---

# Lancer Tessera en local

## Avant tout : vérifier ce qui tourne déjà

Ne jamais lancer sans vérifier. Un backend qui répond ne prouve pas qu'il sert
le code courant.

```bash
curl -s -m 5 http://127.0.0.1:8000/health
curl -s -m 5 -o /dev/null -w "%{http_code}\n" http://localhost:5173/
```

Si `/health` répond `{"status":"ok"}`, **identifier le processus avant de
conclure** — voir le piège du worker orphelin plus bas.

## Lancer

Depuis la racine du dépôt, jamais depuis `backend/` :

```powershell
.\scripts\tessera.ps1 run       # Windows : backend (8000) + frontend (5173)
.\scripts\tessera.ps1 stop      # arrête tout, worker orphelin compris
```

```bash
make run          # ailleurs : les deux dans un seul terminal
make dev          # backend seul
make dev-frontend
```

`make run` s'appuie sur `trap`/`wait` et se comporte mal sous Windows : c'est
ce que `tessera.ps1 run` remplace. Ne pas relancer les deux serveurs à la main.

## Vérifier que ça sert vraiment

`/health` ne suffit pas — il répond même si le chargement des projets est
cassé. Vérifier au moins un projet réel :

```bash
curl -s http://127.0.0.1:8000/api/v1/projects | head -c 200
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/projects/ide-core/tickets
```

Un `500` ici avec un `/health` vert signale presque toujours un fichier de
ticket que le parsing refuse (valeur hors enum dans le frontmatter), ou un
worker orphelin.

## Piège : le worker `--reload` orphelin

`uvicorn --reload` lance un process parent **et** un worker enfant. Tuer le
parent laisse l'enfant vivant : il garde le port 8000 et continue de servir le
code tel qu'il était à son dernier rechargement — souvent un état incohérent,
qui produit des 500 inexplicables et survit à tous les redémarrages
(`[Errno 10048] ... bind`).

Le symptôme : `Get-NetTCPConnection -LocalPort 8000` donne un PID que
`Get-Process` ne trouve pas.

```bash
# identifier le vrai coupable (Windows)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select-Object ProcessId, CommandLine | Format-List"
```

Un worker orphelin a une ligne de commande en
`spawn_main(parent_pid=<PID mort>, ...)`. Le tuer par PID :

```bash
taskkill //F //PID <pid>
```

Puis relancer **sans `--reload`** quand on enchaîne des modifications de
fichiers : le rechargement automatique pendant une série d'éditions est
précisément ce qui crée ces états incohérents.

## Arrêter proprement

```powershell
.\scripts\tessera.ps1 stop
```

Il arrête les deux serveurs **et** cherche le worker orphelin. Vérifier
ensuite que le port 8000 est libre — sinon l'identifier comme ci-dessus.

## Provider LLM

Le défaut est `agent_sdk` (abonnement, aucune clef API nécessaire). Si une
action d'agent renvoie 500, tester le provider isolément avant d'accuser le
pipeline :

```bash
cd backend && uv run python -c "
import asyncio
from tessera.services.providers import get_provider
async def main():
    p = get_provider(allow_tools=False)
    print(await p.complete(system='Reponds OK.', user='dis OK', model=None, max_tokens=64))
asyncio.run(main())
"
```

En Docker, `agent_sdk` ne peut pas s'authentifier : il faut
`LLM_PROVIDER=anthropic_api` et une `ANTHROPIC_API_KEY`.
