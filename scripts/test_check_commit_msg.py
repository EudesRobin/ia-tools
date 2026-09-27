#!/usr/bin/env python3
"""Tests de scripts/check_commit_msg.py : messages conformes admis, chaque
ecart vu en rouge.

Usage : python scripts/test_check_commit_msg.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_commit_msg import ecarts  # noqa: E402

CONFORMES = [
    "fix: corrige le hook",
    "docs: met à jour SETUP\n\nLe pourquoi du changement.",
    "build: PDF généré par pandoc",
    "Merge branch 'x' into main",
    "feat: ajout\n\n# ligne de commentaire ignoree par git",
]

ECARTS = [
    ("sans prefixe", "Corrige le hook", "prefixe"),
    ("prefixe hors liste", "style: espaces", "prefixe"),
    ("point final", "fix: corrige le hook.", "point"),
    ("trop long", "docs: " + "mot " * 60, "mots"),
    ("co-auteur Claude", "feat: x\n\nCo-Authored-By: Claude Opus <noreply@anthropic.com>", "attribution"),
    ("co-auteur Copilot", "feat: x\n\nCo-authored-by: Copilot <copilot@github.com>", "attribution"),
    ("mention generee", "feat: x\n\nGenerated with Claude Code", "attribution"),
    ("mention generee fr", "feat: x\n\nGénéré avec l'IA", "attribution"),
]


class TestCheckCommitMsg(unittest.TestCase):
    def test_conformes(self):
        for message in CONFORMES:
            with self.subTest(message=message):
                texte = "\n".join(l for l in message.splitlines() if not l.startswith("#"))
                self.assertEqual(ecarts(texte.strip()), [])

    def test_ecarts(self):
        for nom, message, attendu in ECARTS:
            with self.subTest(nom):
                trouves = ecarts(message)
                self.assertTrue(any(attendu in e for e in trouves), f"{nom} : {trouves}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
