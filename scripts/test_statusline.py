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
INTERPRETERS = [i for i in ("pwsh", "powershell") if shutil.which(i)]


def context_window(pct, tokens, size=200000):
    """context_window dont current_usage totalise 'tokens' en entree."""
    return {
        "context_window_size": size,
        "used_percentage": pct,
        "current_usage": {
            "input_tokens": tokens // 2,
            "output_tokens": 999,
            "cache_creation_input_tokens": tokens // 4,
            "cache_read_input_tokens": tokens - tokens // 2 - tokens // 4,
        },
    }


OPUS = {"model": {"id": "claude-opus-5-5", "display_name": "Opus"}, "effort": {"level": "high"}}
PREFIX = "Opus (high)" + SEP + "ctx(42%) - (84k/200k)"

# (nom, payload, sortie attendue sans couleurs)
CASES = [
    (
        "abonnement complet",
        {
            **OPUS,
            "context_window": context_window(42, 84000),
            "rate_limits": {
                "five_hour": {"used_percentage": 23.2, "resets_at": 1738425600},
                "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
            },
            "cost": {"total_cost_usd": 3.5},
        },
        PREFIX + SEP + "quota 5h (23%)" + SEP + "quota 7j (41%)",
    ),
    (
        "fenetre 5h absente",
        {
            **OPUS,
            "context_window": context_window(42, 84000),
            "rate_limits": {"seven_day": {"used_percentage": 41.2, "resets_at": 1738857600}},
            "cost": {"total_cost_usd": 3.5},
        },
        PREFIX + SEP + "quota 7j (41%)",
    ),
    (
        "facturation API",
        {**OPUS, "context_window": context_window(42, 84000), "cost": {"total_cost_usd": 1.234}},
        PREFIX + SEP + "session ($1.23)",
    ),
    (
        "limite de depense seule",
        {
            **OPUS,
            "context_window": context_window(42, 84000),
            "rate_limits": {"spend_limit": {"used_percentage": 62.8, "resets_at": 1740787200}},
            "cost": {"total_cost_usd": 0.5},
        },
        PREFIX + SEP + "session ($0.50)",
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
            "context_window": context_window(10, 100000, 1000000),
            "cost": {"total_cost_usd": 0},
        },
        "Sonnet" + SEP + "ctx(10%) - (100k/1M)",
    ),
]


def run(
    interpreter: str, stdin_text: str, colors: bool = False, columns: str | None = None
) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "COLUMNS")}
    if not colors:
        env["NO_COLOR"] = "1"
    if columns is not None:
        env["COLUMNS"] = columns
    return subprocess.run(
        [interpreter, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(USAGE_SESSION)],
        input=stdin_text.encode("utf-8"), capture_output=True, env=env, timeout=60,
    )


class TestUsageSession(unittest.TestCase):
    def test_displays(self):
        for interpreter in INTERPRETERS:
            for name, payload, expected in CASES:
                with self.subTest(interpreter=interpreter, case=name):
                    r = run(interpreter, json.dumps(payload))
                    self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
                    self.assertEqual(r.stdout.decode("utf-8").strip(), expected)
                    self.assertEqual(r.stderr, b"")

    def test_unreadable_payload(self):
        for interpreter in INTERPRETERS:
            with self.subTest(interpreter=interpreter):
                r = run(interpreter, "pas du JSON")
                self.assertEqual(r.returncode, 0)
                self.assertEqual(r.stdout.strip(), b"")
                self.assertEqual(r.stderr, b"")

    def test_right_alignment(self):
        # Largeur visible hors sequences ANSI ; marge de 7 colonnes a droite.
        name, payload, expected = CASES[0]
        for interpreter in INTERPRETERS:
            for columns, colors, empty in (
                ("120", False, 120 - len(expected) - 7),
                ("120", True, 120 - len(expected) - 7),
                ("40", False, 0),
                ("abc", False, 0),
            ):
                with self.subTest(interpreter=interpreter, columns=columns, colors=colors):
                    r = run(interpreter, json.dumps(payload), colors, columns)
                    output = r.stdout.decode("utf-8").rstrip("\r\n")
                    if empty:
                        # Prefixe invisible qui protege les blancs de tete.
                        self.assertTrue(output.startswith("\x1b[0m"), repr(output[:10]))
                        output = output.removeprefix("\x1b[0m")
                    self.assertEqual(len(output) - len(output.lstrip(" ")), empty)
                    visible = re.sub(r"\x1b\[[0-9;]*m", "", output.lstrip(" "))
                    self.assertEqual(visible, expected)

    def test_color_by_threshold(self):
        payload = json.dumps({**OPUS, "context_window": context_window(85, 170000)})
        for interpreter in INTERPRETERS:
            with self.subTest(interpreter=interpreter):
                r = run(interpreter, payload, colors=True)
                self.assertIn("\x1b[31m85%\x1b[0m", r.stdout.decode("utf-8"))


if __name__ == "__main__":
    if not INTERPRETERS:
        print("test_statusline.py : ni pwsh ni powershell dans le PATH", file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if unittest.main(verbosity=2, exit=False).result.wasSuccessful() else 1)
