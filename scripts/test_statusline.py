#!/usr/bin/env python3
"""Tests des status lines de statuslines/claude/ : chaque script recoit un
payload JSON sur son entree standard, sous chaque PowerShell present (pwsh,
powershell), et sa sortie est comparee a l'affichage attendu (AGENTS.md, DoD
des scripts).

Usage : python scripts/test_statusline.py
Code de sortie : 0 si tout passe, 1 sinon, 2 si aucun PowerShell n'est present.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USAGE_SESSION = ROOT / "statuslines" / "claude" / "usage-session" / "statusline.ps1"
SEP = " │ "
INTERPRETES = [i for i in ("pwsh", "powershell") if shutil.which(i)]


def contexte(pct, tokens, taille=200000):
    """context_window dont current_usage totalise 'tokens' en entree."""
    return {
        "context_window_size": taille,
        "used_percentage": pct,
        "current_usage": {
            "input_tokens": tokens // 2,
            "output_tokens": 999,
            "cache_creation_input_tokens": tokens // 4,
            "cache_read_input_tokens": tokens - tokens // 2 - tokens // 4,
        },
    }


OPUS = {"model": {"id": "claude-opus-5-5", "display_name": "Opus"}, "effort": {"level": "high"}}
TETE = "Opus (high)" + SEP + "ctx(42%) - (84k/200k)"

# (nom, payload, sortie attendue sans couleurs)
CAS = [
    (
        "abonnement complet",
        {
            **OPUS,
            "context_window": contexte(42, 84000),
            "rate_limits": {
                "five_hour": {"used_percentage": 23.2, "resets_at": 1738425600},
                "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
            },
            "cost": {"total_cost_usd": 3.5},
        },
        TETE + SEP + "quota 5h (23%)" + SEP + "quota 7j (41%)",
    ),
    (
        "fenetre 5h absente",
        {
            **OPUS,
            "context_window": contexte(42, 84000),
            "rate_limits": {"seven_day": {"used_percentage": 41.2, "resets_at": 1738857600}},
            "cost": {"total_cost_usd": 3.5},
        },
        TETE + SEP + "quota 7j (41%)",
    ),
    (
        "facturation API",
        {**OPUS, "context_window": contexte(42, 84000), "cost": {"total_cost_usd": 1.234}},
        TETE + SEP + "session ($1.23)",
    ),
    (
        "limite de depense seule",
        {
            **OPUS,
            "context_window": contexte(42, 84000),
            "rate_limits": {"spend_limit": {"used_percentage": 62.8, "resets_at": 1740787200}},
            "cost": {"total_cost_usd": 0.5},
        },
        TETE + SEP + "session ($0.50)",
    ),
    (
        "debut de session",
        {
            **OPUS,
            "context_window": {
                "context_window_size": 200000,
                "used_percentage": None,
                "current_usage": None,
            },
            "cost": {"total_cost_usd": 0},
        },
        "Opus (high)" + SEP + "ctx(0%) - (0/200k)",
    ),
    (
        "modele sans effort, contexte etendu",
        {
            "model": {"id": "claude-sonnet-5-5", "display_name": "Sonnet"},
            "context_window": contexte(10, 100000, 1000000),
            "cost": {"total_cost_usd": 0},
        },
        "Sonnet" + SEP + "ctx(10%) - (100k/1M)",
    ),
]


def lancer(
    interprete: str, entree: str, couleurs: bool = False, colonnes: str | None = None
) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "COLUMNS")}
    if not couleurs:
        env["NO_COLOR"] = "1"
    if colonnes is not None:
        env["COLUMNS"] = colonnes
    return subprocess.run(
        [interprete, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(USAGE_SESSION)],
        input=entree.encode("utf-8"), capture_output=True, env=env, timeout=60,
    )


class TestUsageSession(unittest.TestCase):
    def test_affichages(self):
        for interprete in INTERPRETES:
            for nom, payload, attendu in CAS:
                with self.subTest(interprete=interprete, cas=nom):
                    r = lancer(interprete, json.dumps(payload))
                    self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
                    self.assertEqual(r.stdout.decode("utf-8").strip(), attendu)
                    self.assertEqual(r.stderr, b"")

    def test_payload_illisible(self):
        for interprete in INTERPRETES:
            with self.subTest(interprete=interprete):
                r = lancer(interprete, "pas du JSON")
                self.assertEqual(r.returncode, 0)
                self.assertEqual(r.stdout.strip(), b"")
                self.assertEqual(r.stderr, b"")

    def test_alignement_a_droite(self):
        # Largeur visible hors sequences ANSI ; marge de 7 colonnes a droite.
        nom, payload, attendu = CAS[0]
        for interprete in INTERPRETES:
            for colonnes, couleurs, vide in (
                ("120", False, 120 - len(attendu) - 7),
                ("120", True, 120 - len(attendu) - 7),
                ("40", False, 0),
                ("abc", False, 0),
            ):
                with self.subTest(interprete=interprete, colonnes=colonnes, couleurs=couleurs):
                    r = lancer(interprete, json.dumps(payload), couleurs, colonnes)
                    sortie = r.stdout.decode("utf-8").rstrip("\r\n")
                    if vide:
                        # Prefixe invisible qui protege les blancs de tete.
                        self.assertTrue(sortie.startswith("\x1b[0m"), repr(sortie[:10]))
                        sortie = sortie.removeprefix("\x1b[0m")
                    self.assertEqual(len(sortie) - len(sortie.lstrip(" ")), vide)
                    visible = re.sub(r"\x1b\[[0-9;]*m", "", sortie.lstrip(" "))
                    self.assertEqual(visible, attendu)

    def test_couleur_par_seuil(self):
        payload = json.dumps({**OPUS, "context_window": contexte(85, 170000)})
        for interprete in INTERPRETES:
            with self.subTest(interprete=interprete):
                r = lancer(interprete, payload, couleurs=True)
                self.assertIn("\x1b[31m85%\x1b[0m", r.stdout.decode("utf-8"))


if __name__ == "__main__":
    if not INTERPRETES:
        print("test_statusline.py : ni pwsh ni powershell dans le PATH", file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1)
