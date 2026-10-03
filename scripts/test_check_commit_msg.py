#!/usr/bin/env python3
"""Tests de scripts/check_commit_msg.py : messages conformes admis, chaque
ecart vu en rouge, y compris par les modes --plage (depot git temporaire) et
--pr (variables d'environnement).

Usage : python scripts/test_check_commit_msg.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check_commit_msg.py"
sys.path.insert(0, str(SCRIPT.parent))
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


def lancer(*args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, env={**os.environ, **(env or {})},
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )


class TestPlage(unittest.TestCase):
    """--plage : un commit conforme passe, un commit non conforme est signale."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.d = Path(self._tmp.name)
        self.git("init", "-q")
        self.shas = [self.commit(m) for m in ("chore: base", "fix: conforme", "Corrige sans prefixe")]

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.hooksPath=", *args],
            cwd=self.d, capture_output=True, text=True, check=True,
        ).stdout.strip()

    def commit(self, message: str) -> str:
        self.git("commit", "-q", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def test_plage_conforme(self):
        r = lancer("--plage", f"{self.shas[0]}..{self.shas[1]}", cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_plage_avec_ecart(self):
        r = lancer("--plage", f"{self.shas[0]}..{self.shas[2]}", cwd=self.d)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"{self.shas[2][:7]} : sujet sans prefixe", r.stderr)
        self.assertNotIn(self.shas[1][:7], r.stderr)

    def test_plage_illisible(self):
        r = lancer("--plage", "nulle..part", cwd=self.d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("plage illisible", r.stderr)


class TestPr(unittest.TestCase):
    """--pr : seule l'attribution d'IA est controlee, dans le titre et la description."""

    def test_pr_conforme(self):
        r = lancer("--pr", env={"PR_TITLE": "docs: x", "PR_BODY": "## Contexte\n\nPDF genere par pandoc."})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_pr_description_attribuee(self):
        r = lancer("--pr", env={"PR_TITLE": "docs: x", "PR_BODY": "Generated with [Claude Code](https://claude.com)"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("description de la pull request", r.stderr)

    def test_pr_titre_attribue(self):
        r = lancer("--pr", env={"PR_TITLE": "feat: x, genere par l'IA", "PR_BODY": ""})
        self.assertEqual(r.returncode, 1)
        self.assertIn("titre de la pull request", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
