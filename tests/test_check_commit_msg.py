#!/usr/bin/env python3
"""Tests de scripts/check_commit_msg.py : messages conformes admis, chaque
ecart vu en rouge, y compris par les modes --range (depot git temporaire) et
--pr (variables d'environnement).

Usage : python tests/test_check_commit_msg.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_commit_msg.py"
sys.path.insert(0, str(SCRIPT.parent))
from check_commit_msg import issues  # noqa: E402

VALID = [
    "fix: corrige le hook",
    "docs: met à jour SETUP\n\nLe pourquoi du changement.",
    "build: PDF généré par pandoc",
    "Merge branch 'x' into main",
    "feat: ajout\n\n# ligne de commentaire ignoree par git",
]

BROKEN = [
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
    def test_valid_messages(self):
        for message in VALID:
            with self.subTest(message=message):
                text = "\n".join(l for l in message.splitlines() if not l.startswith("#"))
                self.assertEqual(issues(text.strip()), [])

    def test_broken_messages(self):
        for name, message, expected in BROKEN:
            with self.subTest(name):
                found = issues(message)
                self.assertTrue(any(expected in e for e in found), f"{name} : {found}")


def run(*args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    # GITHUB_ACTIONS est fixe par le test, pas herite : meme resultat en local et en CI.
    base_env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd, env={**base_env, **(env or {})},
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )


class TestRange(unittest.TestCase):
    """--range : un commit conforme passe, un commit non conforme est signale."""

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

    def test_range_valid(self):
        r = run("--range", f"{self.shas[0]}..{self.shas[1]}", cwd=self.d)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_range_with_issue(self):
        r = run("--range", f"{self.shas[0]}..{self.shas[2]}", cwd=self.d)
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"{self.shas[2][:7]} : sujet sans prefixe", r.stderr)
        self.assertNotIn(self.shas[1][:7], r.stderr)

    def test_range_unreadable(self):
        r = run("--range", "nulle..part", cwd=self.d)
        self.assertEqual(r.returncode, 1)
        self.assertIn("plage illisible", r.stderr)


class TestPr(unittest.TestCase):
    """--pr : seule l'attribution d'IA est controlee, dans le titre et la description."""

    def test_pr_valid(self):
        r = run("--pr", env={"PR_TITLE": "docs: x", "PR_BODY": "## Contexte\n\nPDF genere par pandoc."})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_pr_body_attributed(self):
        r = run("--pr", env={"PR_TITLE": "docs: x", "PR_BODY": "Generated with [Claude Code](https://claude.com)"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("description de la pull request", r.stderr)

    def test_pr_title_attributed(self):
        r = run("--pr", env={"PR_TITLE": "feat: x, genere par l'IA", "PR_BODY": ""})
        self.assertEqual(r.returncode, 1)
        self.assertIn("titre de la pull request", r.stderr)

    def test_annotations(self):
        attributed = {"PR_TITLE": "docs: x", "PR_BODY": "Generated with Claude Code"}
        r = run("--pr", env=attributed)
        self.assertNotIn("::error", r.stdout, "annotation emise hors CI")
        r = run("--pr", env={**attributed, "GITHUB_ACTIONS": "true"})
        self.assertIn("::error title=check_commit_msg.py::description de la pull request", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
