#!/usr/bin/env python3
"""Tests de scripts/install.py sur une cible temporaire (--target), pour chaque
agent hote : installation sur cible vide, idempotence, etat par outil, conflit
sur edition locale sans ecriture de l'outil concerne, echec d'ecriture signale,
validation prealable bloquant --apply, settings.json jamais ecrit (AGENTS.md,
DoD des scripts ; docs/SETUP.md).

Usage : python tests/test_install.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ("claude", "copilot")

# Outil de plusieurs fichiers, distribue a chaque agent hote sous le meme chemin.
TOOL = "skills/clean-android-tv"
EDITED = f"{TOOL}/SKILL.md"
DELETED = f"{TOOL}/paquets.md"


def run_install(agent: str, target: Path, *options: str) -> tuple[int, dict]:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "install.py"),
         "--agent", agent, "--target", str(target), "--json", *options],
        cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    try:
        report = json.loads(r.stdout)["agents"][agent]
    except (ValueError, KeyError):
        raise AssertionError(f"sortie --json illisible (code {r.returncode}) : {r.stdout}{r.stderr}")
    return r.returncode, report


def counts(report: dict) -> dict:
    return {status: len(sources) for status, sources in report["classes"].items()}


class TestInstall(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_target_then_idempotent(self):
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                code, r = run_install(agent, target, "--apply")
                self.assertEqual(code, 0, r)
                self.assertTrue(r["ecrits"], f"{agent} : rien n'a ete ecrit")
                self.assertEqual(sorted(r["ecrits"]), sorted(r["classes"]["absent"]))
                self.assertEqual(r["echecs"], [])
                self.assertEqual(set(r["outils"].values()), {"installe"}, r["outils"])
                # Le chemin cible depend de l'agent hote (agent .md ou .agent.md) :
                # seul le nombre de fichiers presents est compare.
                present = [p for p in target.rglob("*") if p.is_file()]
                self.assertEqual(len(present), len(r["ecrits"]), f"{agent} : {present}")
                code, r = run_install(agent, target)
                self.assertEqual(code, 0, r)
                n = counts(r)
                self.assertGreater(n["identique"], 0)
                self.assertEqual(sum(v for k, v in n.items() if k != "identique"), 0, n)
                self.assertEqual(set(r["outils"].values()), {"a_jour"}, r["outils"])

    def test_conflict_blocks_tool(self):
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                run_install(agent, target, "--apply")
                edited, deleted = target / EDITED, target / DELETED
                self.assertTrue(edited.is_file() and deleted.is_file(), f"{agent} : {TOOL} non installe")
                edited.write_text("edition locale\n", encoding="utf-8")
                deleted.unlink()

                code, r = run_install(agent, target, "--apply")
                self.assertEqual(code, 1, f"{agent} : un conflit doit sortir en 1")
                self.assertIn(EDITED, r["classes"]["conflit"])
                self.assertIn("clean-android-tv", " ".join(r["outils_bloques"]))
                self.assertEqual(edited.read_text(encoding="utf-8"), "edition locale\n",
                                 f"{agent} : edition locale ecrasee")
                self.assertFalse(deleted.exists(), f"{agent} : fichier d'un outil bloque reecrit")
                self.assertNotIn(DELETED, r["ecrits"])
                self.assertEqual(r["outils"]["clean-android-tv"], "conflit")

    def test_write_failure_reported(self):
        """Une ecriture impossible est signalee et sort en 1, sans arreter les autres outils."""
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                (target / EDITED).mkdir(parents=True)  # un dossier a la place du fichier
                code, r = run_install(agent, target, "--apply")
                self.assertEqual(code, 1, f"{agent} : un echec d'ecriture doit sortir en 1")
                self.assertIn(EDITED, r["echecs"])
                self.assertNotIn(EDITED, r["ecrits"])
                self.assertEqual(r["outils"]["clean-android-tv"], "echec")
                others = [s for s in r["ecrits"] if not s.startswith(TOOL + "/")]
                self.assertTrue(others, f"{agent} : les autres outils n'ont pas ete ecrits")

    def test_settings_json_never_written(self):
        for agent in AGENTS:
            with self.subTest(agent):
                target = self.tmp / agent
                target.mkdir()
                settings = target / "settings.json"
                content = b'{\n  "model": "local"\n}\n'
                settings.write_bytes(content)
                code, r = run_install(agent, target, "--apply")
                self.assertEqual(code, 0, r)
                self.assertEqual(settings.read_bytes(), content, f"{agent} : settings.json modifie")


    def test_tool_option_and_deprecated_alias(self):
        """--tool restreint l'installation ; --outil reste accepte et avertit."""
        for option, warns in (("--tool", False), ("--outil", True)):
            with self.subTest(option):
                target = self.tmp / option.strip("-")
                r = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "install.py"), "--agent", "claude",
                     "--target", str(target), option, "clean-android-tv", "--apply", "--json"],
                    cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                )
                self.assertEqual(r.returncode, 0, r.stderr)
                written = json.loads(r.stdout)["agents"]["claude"]["ecrits"]
                self.assertTrue(written)
                self.assertTrue(all(s.startswith(TOOL + "/") for s in written), written)
                self.assertEqual("obsolete" in r.stderr, warns, r.stderr)

    def test_validation_gates_apply(self):
        """Validateur en echec : --apply n'ecrit rien ; anomalie d'environnement : avertit."""
        spec = importlib.util.spec_from_file_location("install", ROOT / "scripts" / "install.py")
        install = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(install)
        for exit_code, expected, writes in ((1, 1, False), (2, 0, True)):
            with self.subTest(exit_code):
                validator = self.tmp / f"validator_{exit_code}.py"
                validator.write_text(f"import sys\nsys.exit({exit_code})\n", encoding="utf-8")
                target = self.tmp / f"target_{exit_code}"
                install.VALIDATOR = validator
                argv = ["install.py", "--agent", "claude", "--target", str(target), "--apply"]
                out = io.StringIO()
                with unittest.mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(out):
                    code = install.main()
                self.assertEqual(code, expected, out.getvalue())
                self.assertEqual(target.exists() and any(target.rglob("*")), writes, out.getvalue())
                self.assertIn("validation", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
