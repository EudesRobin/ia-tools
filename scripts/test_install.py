#!/usr/bin/env python3
"""Tests de scripts/install.py sur une cible temporaire (--target), pour chaque
agent hote : installation sur cible vide, idempotence, conflit sur edition
locale sans ecriture de l'outil concerne, settings.json jamais ecrit
(AGENTS.md, DoD des scripts ; docs/SETUP.md).

Usage : python scripts/test_install.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ("claude", "copilot")

# Outil de plusieurs fichiers, distribue a chaque agent hote sous le meme chemin.
OUTIL = "skills/clean-android-tv"
EDITE = f"{OUTIL}/SKILL.md"
SUPPRIME = f"{OUTIL}/paquets.md"


def installer(agent: str, cible: Path, *options: str) -> tuple[int, dict]:
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "install.py"),
         "--agent", agent, "--target", str(cible), "--json", *options],
        cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    try:
        rapport = json.loads(r.stdout)["agents"][agent]
    except (ValueError, KeyError):
        raise AssertionError(f"sortie --json illisible (code {r.returncode}) : {r.stdout}{r.stderr}")
    return r.returncode, rapport


def nombres(rapport: dict) -> dict:
    return {classe: len(sources) for classe, sources in rapport["classes"].items()}


class TestInstall(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cible_vide_puis_idempotence(self):
        for agent in AGENTS:
            with self.subTest(agent):
                cible = self.tmp / agent
                code, r = installer(agent, cible, "--apply")
                self.assertEqual(code, 0, r)
                self.assertTrue(r["ecrits"], f"{agent} : rien n'a ete ecrit")
                self.assertEqual(sorted(r["ecrits"]), sorted(r["classes"]["absent"]))
                # Le chemin cible depend de l'agent hote (agent .md ou .agent.md) :
                # seul le nombre de fichiers presents est compare.
                presents = [p for p in cible.rglob("*") if p.is_file()]
                self.assertEqual(len(presents), len(r["ecrits"]), f"{agent} : {presents}")
                code, r = installer(agent, cible)
                self.assertEqual(code, 0, r)
                n = nombres(r)
                self.assertGreater(n["identique"], 0)
                self.assertEqual(sum(v for k, v in n.items() if k != "identique"), 0, n)

    def test_conflit_bloque_l_outil(self):
        for agent in AGENTS:
            with self.subTest(agent):
                cible = self.tmp / agent
                installer(agent, cible, "--apply")
                edite, supprime = cible / EDITE, cible / SUPPRIME
                self.assertTrue(edite.is_file() and supprime.is_file(), f"{agent} : {OUTIL} non installe")
                edite.write_text("edition locale\n", encoding="utf-8")
                supprime.unlink()

                code, r = installer(agent, cible, "--apply")
                self.assertEqual(code, 1, f"{agent} : un conflit doit sortir en 1")
                self.assertIn(EDITE, r["classes"]["conflit"])
                self.assertIn("clean-android-tv", " ".join(r["outils_bloques"]))
                self.assertEqual(edite.read_text(encoding="utf-8"), "edition locale\n",
                                 f"{agent} : edition locale ecrasee")
                self.assertFalse(supprime.exists(), f"{agent} : fichier d'un outil bloque reecrit")
                self.assertNotIn(SUPPRIME, r["ecrits"])

    def test_settings_json_jamais_ecrit(self):
        for agent in AGENTS:
            with self.subTest(agent):
                cible = self.tmp / agent
                cible.mkdir()
                settings = cible / "settings.json"
                contenu = b'{\n  "model": "local"\n}\n'
                settings.write_bytes(contenu)
                code, r = installer(agent, cible, "--apply")
                self.assertEqual(code, 0, r)
                self.assertEqual(settings.read_bytes(), contenu, f"{agent} : settings.json modifie")


if __name__ == "__main__":
    unittest.main(verbosity=2)
