"""Vérification des prérequis — ticket-056.

Les deux pannes de ticket-050 — une `ANTHROPIC_API_KEY` parasite et un
`IDE_PROMPTS_DIR` qui ne résolvait jamais — étaient l'une et l'autre
détectables **avant** de lancer quoi que ce soit. Elles ont coûté une session
de débogage parce que rien ne les cherchait.

Ce module ne répare rien : il constate, et dit quoi faire.
"""
import platform
import shutil
import socket
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from vibe_ide.config import settings

_BACKEND_PORT = 8000
_FRONTEND_PORT = 5173


@dataclass
class Check:
    """One verified prerequisite."""

    name: str
    ok: bool
    detail: str
    fix: str = ""

    @property
    def symbol(self) -> str:
        return "OK  " if self.ok else "KO  "


def _port_is_taken(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def check_python() -> Check:
    version = ".".join(str(n) for n in sys.version_info[:3])
    ok = sys.version_info >= (3, 11)
    return Check(
        name="Python 3.11+",
        ok=ok,
        detail=version,
        fix="" if ok else "Installe Python 3.11 ou plus récent.",
    )


def check_env_file() -> Check:
    env = Path(__file__).resolve().parents[3] / ".env"
    ok = env.is_file()
    return Check(
        name="Fichier .env",
        ok=ok,
        detail=str(env) if ok else "absent",
        fix="" if ok else "Lance `make setup`, ou copie `.env.example` en `.env`.",
    )


def check_prompts_dir() -> Check:
    """Le défaut ne résolvait jamais avec la méthode de lancement documentée."""
    prompts = settings.ide_prompts_dir
    missing = [
        name
        for name in ("codeur.md", "reviewer.md", "planificateur.md", "chat.md")
        if not (prompts / name).is_file()
    ]
    ok = prompts.is_dir() and not missing
    detail = str(prompts) if ok else f"{prompts} — manquants : {missing or 'dossier absent'}"
    return Check(
        name="Prompts des agents",
        ok=ok,
        detail=detail,
        fix="" if ok else "Pointe IDE_PROMPTS_DIR sur le dossier agents/prompts du dépôt.",
    )


def check_provider_auth() -> Check:
    """Une clef API présente mais invalide casse *tout* en mode abonnement."""
    provider = settings.llm_provider
    key = (settings.anthropic_api_key or "").strip()

    if provider == "agent_sdk":
        placeholder = key.endswith("...") or key in ("sk-ant-...", "")
        if key and placeholder:
            return Check(
                name="Authentification du provider",
                ok=True,
                detail="agent_sdk (abonnement) — clef placeholder ignorée",
            )
        if key:
            return Check(
                name="Authentification du provider",
                ok=False,
                detail="agent_sdk, mais ANTHROPIC_API_KEY est renseignée",
                fix=(
                    "Le CLI donne la priorité à la clef sur la session d'abonnement. "
                    "vibe-ide la neutralise pour ses appels, mais laisse-la vide dans "
                    "`.env` pour éviter toute ambiguïté."
                ),
            )
        cli = shutil.which("claude")
        return Check(
            name="Authentification du provider",
            ok=cli is not None,
            detail=f"agent_sdk (abonnement) — CLI : {cli or 'introuvable'}",
            fix="" if cli else "Installe le CLI Claude Code et authentifie une session.",
        )

    return Check(
        name="Authentification du provider",
        ok=bool(key),
        detail=f"{provider} — clef {'présente' if key else 'absente'}",
        fix="" if key else "Le mode anthropic_api exige une ANTHROPIC_API_KEY dans `.env`.",
    )


def check_workspace() -> Check:
    ws = settings.ide_workspace_dir
    ok = ws.is_dir()
    return Check(
        name="Dossier workspace",
        ok=ok,
        detail=str(ws) if ok else f"{ws} — absent",
        fix="" if ok else "Crée le dossier, ou corrige IDE_WORKSPACE_DIR dans `.env`.",
    )


def check_symlinks() -> Check:
    """Sous Windows, l'import en mode symlink exige le mode développeur."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / "cible"
        target.mkdir()
        try:
            (root / "lien").symlink_to(target, target_is_directory=True)
            available = True
        except (OSError, NotImplementedError):
            available = False

    return Check(
        name="Liens symboliques",
        ok=True,  # jamais bloquant : le mode `copy` fonctionne partout
        detail="disponibles" if available else "indisponibles — utilise le mode `copy`",
        fix=""
        if available
        else "Active le mode développeur Windows pour importer en mode `symlink`.",
    )


def check_rust() -> Check:
    """Tauri exige la toolchain Rust. Informatif : le mode web marche sans."""
    cargo = shutil.which("cargo")
    return Check(
        name="Toolchain Rust (Tauri)",
        ok=True,  # jamais bloquant : l'IDE tourne en web sans Tauri
        detail=f"cargo : {cargo}" if cargo else "absente — build desktop impossible",
        fix=""
        if cargo
        else "Installe Rust (https://rustup.rs) pour builder l'application desktop.",
    )


def check_ports() -> Check:
    taken = [p for p in (_BACKEND_PORT, _FRONTEND_PORT) if _port_is_taken(p)]
    return Check(
        name="Ports libres",
        ok=not taken,
        detail="8000 et 5173 libres" if not taken else f"déjà occupés : {taken}",
        fix=""
        if not taken
        else (
            r"Arrête l'instance en cours : `.\scripts\vibe.ps1 stop` sous Windows, "
            "`make stop` ailleurs. Si le port reste tenu par un PID introuvable, "
            "c'est un worker uvicorn --reload orphelin : taskkill /F /PID <pid>."
        ),
    )


def run_checks() -> list[Check]:
    return [
        check_python(),
        check_env_file(),
        check_workspace(),
        check_prompts_dir(),
        check_provider_auth(),
        check_symlinks(),
        check_rust(),
        check_ports(),
    ]


def main() -> int:
    """Print the report; non-zero exit when something is actually broken."""
    # La console Windows est en cp1252 : une flèche ou un tiret cadratin
    # y fait planter l'outil même censé diagnostiquer les problèmes
    # d'encodage. Constaté au premier lancement (ticket-056).
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    print(f"vibe-ide doctor — {platform.system()} {platform.release()}\n")

    checks = run_checks()
    width = max(len(c.name) for c in checks)
    for check in checks:
        print(f"  {check.symbol}{check.name.ljust(width)}  {check.detail}")
        if check.fix:
            print(f"        {' ' * width}  → {check.fix}")

    broken = [c for c in checks if not c.ok]
    print()
    if broken:
        print(f"{len(broken)} problème(s) à corriger avant de lancer l'IDE.")
        return 1
    print("Tout est en place.")
    return 0


if __name__ == "__main__":  # pragma: no cover — point d'entrée
    raise SystemExit(main())
