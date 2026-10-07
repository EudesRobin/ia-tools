#!/usr/bin/env python3
"""Tests de skills/clean-android-tv/adb_tv.py, sans televiseur : un faux adb
renvoie des sorties enregistrees. Chaque controle de check-plan et de compare
est vu en rouge sur un cas volontairement casse (AGENTS.md, DoD des scripts).

Usage : python scripts/test_adb_tv.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "clean-android-tv" / "adb_tv.py"

FAKE_ADB = '''
import json, os, sys
args = sys.argv[1:]
if args[:1] == ["-s"]:
    args = args[2:]
fixtures = json.load(open(os.environ["FAKE_ADB_FIXTURES"], encoding="utf-8"))
key = " ".join(args)
if key not in fixtures:
    sys.stderr.write("error: commande non prevue : " + key)
    sys.exit(1)
sys.stdout.write(fixtures[key])
'''

ENABLED = [
    "android", "com.android.shell", "com.google.android.katniss",
    "com.google.android.tvlauncher", "com.tcl.tv", "com.android.providers.settings",
    "com.example.ime", "com.spocky.projengmenu",
]
DISABLED = ["com.google.android.backdrop"]

PREFERRED_THIRD_PARTY = """Preferred Activities User 0:
  Non-Data Actions:
      android.intent.action.MAIN:
        1a2b3c com.spocky.projengmenu/.ui.home.MainActivity filter 4d5e6f
          Action: "android.intent.action.MAIN"
          Category: "android.intent.category.HOME"
          Category: "android.intent.category.DEFAULT"
          mPref.mAlways=true
"""


# Format releve sur un TCL sous Android 8 : pas de « filter », mAlways avant les
# categories, et a false alors que l'accueil est bien declare.
PREFERRED_ANDROID_8 = """Database versions:
  Internal:
    sdkVersion=26
Preferred Activities User 0:
  Non-Data Actions:
      android.intent.action.MAIN:
        c671274 com.spocky.projengmenu/.ui.home.MainActivity
         mMatch=0x100000 mAlways=false
          Action: "android.intent.action.MAIN"
          Category: "android.intent.category.HOME"
          Category: "android.intent.category.DEFAULT"

App verification status:
"""


def pkgs(names):
    return "".join(f"package:{n}\n" for n in names)


def base_fixtures(**over):
    f = {
        "get-state": "device\n",
        "shell getprop ro.product.model": "Percee TV\n",
        "shell getprop ro.product.manufacturer": "TCL\n",
        "shell getprop ro.build.version.release": "8.0.0\n",
        "shell getprop ro.build.version.sdk": "26\n",
        "shell df -h /data": "Filesystem Size Used Avail Use% Mounted on\n"
                             "/dev/block/dm-2 5.2G 4.1G 1.1G 79% /data\n",
        "shell dumpsys meminfo": "Total RAM: 1,939,668K (status normal)\n"
                                 " Free RAM: 1,021,580K (  412,080K cached pss)\n"
                                 " ZRAM:   123,456K physical used for   456,789K in swap"
                                 " (1,048,572K total swap)\n",
        "shell dumpsys diskstats": "Data-Free: 1100000K / 5200000K total = 21% free\n",
        "shell dumpsys procstats --hours 24": "AGGREGATED OVER LAST 24 HOURS:\n"
            "  * com.tcl.versionUpdateApp / u0a45 / v12:\n"
            "         TOTAL: 100% (30MB-31MB-32MB/28MB-29MB-30MB over 20)\n"
            "  * com.google.android.katniss / u0a50 / v3:\n"
            "         TOTAL: 42% (10MB-11MB-12MB/9MB-9MB-10MB over 8)\n"
            "  * com.android.bluetooth / 1002 / v26:\n"
            "         TOTAL: 0,01% (8,1MB-9,3MB-11MB/6,9MB-8,0MB-9,3MB over 81)\n",
        "shell uptime": " 10:00:00 up 2 days,  3:12,  0 users,  load average: 1.0\n",
        "shell pm list packages -s": pkgs(ENABLED[:5]),
        "shell pm list packages -3": pkgs(ENABLED[5:]),
        "shell pm list packages -e": pkgs(ENABLED),
        "shell pm list packages -d": pkgs(DISABLED),
        "shell pm list packages": pkgs(ENABLED + DISABLED),
        "shell settings get secure default_input_method": "com.example.ime/.Ime\n",
        "shell dumpsys package preferred-activities": PREFERRED_THIRD_PARTY,
        "shell settings get secure enabled_accessibility_services": "null\n",
        "shell dumpsys package packages": "Packages:\n"
            "  Package [com.google.android.katniss] (abc):\n"
            "    lastUpdateTime=2000-01-01 00:00:00\n"
            "  Package [com.spocky.projengmenu] (def):\n"
            "    lastUpdateTime=2099-01-01 00:00:00\n",
        "shell dumpsys activity oom":
            "    Proc # 3: prev   F/S/LAST  trm: 0 12345:com.google.android.katniss/u0a50 (previous)\n"
            "    Proc # 5: svc    B/S/SVC   trm: 0 2345:com.tcl.versionUpdateApp/u0a45 (started-services)\n",
        "shell dumpsys jobscheduler": "  JOB #u0a45/7: 1a com.tcl.versionUpdateApp/.Job\n",
        "shell dumpsys activity services com.tcl.versionUpdateApp":
            "  * ServiceRecord{1 u0 com.tcl.versionUpdateApp/.Svc}\n",
        "shell dumpsys activity services com.google.android.katniss": "",
        "shell dumpsys package com.tcl.versionUpdateApp": "android.intent.action.BOOT_COMPLETED:\n",
        "shell dumpsys package com.google.android.katniss": "",
    }
    f.update(over)
    return f


class AdbTvTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.fake = self.dir / "fake_adb.py"
        self.fake.write_text(FAKE_ADB, encoding="utf-8")
        self.fixtures(base_fixtures())

    def tearDown(self):
        self.tmp.cleanup()

    def fixtures(self, data):
        path = self.dir / "fixtures.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        self.env = {**os.environ, "FAKE_ADB_FIXTURES": str(path), "PYTHONUTF8": "1"}

    def run_tv(self, *args, adb=None):
        res = subprocess.run(
            [sys.executable, str(SCRIPT), "--adb", str(adb or self.fake), *args],
            capture_output=True, text=True, env=self.env, encoding="utf-8",
        )
        return res.returncode, res.stdout + res.stderr

    def snapshot(self):
        code, out = self.run_tv("snapshot", "192.168.1.20", "--dir", str(self.dir))
        self.assertEqual(code, 0, out)
        return next(self.dir.glob("tcl-percee-tv-*.md"))

    def journal_with_lot(self, *rows):
        journal = self.snapshot()
        text = journal.read_text(encoding="utf-8")
        lot = "".join(f"| {g} | `{p}` | role | effet |\n" for g, p in rows)
        text = text.replace("| <groupe> | `<paquet>` | <rôle> | <effet> |\n", lot)
        journal.write_text(text, encoding="utf-8")
        return journal

    # ------------------------------------------------------------ snapshot

    def test_snapshot_writes_journal_and_compact_summary(self):
        code, out = self.run_tv("snapshot", "192.168.1.20", "--dir", str(self.dir))
        self.assertEqual(code, 0, out)
        journal = self.dir / next(self.dir.glob("tcl-percee-tv-*.md")).name
        text = journal.read_text(encoding="utf-8")
        for heading in ("## Appareil", "## État initial", "## Inventaire initial", "## Lot",
                        "## Actions", "## État final", "## Réactivation complète"):
            self.assertIn(heading, text)
        self.assertIn("package:com.google.android.katniss", text)
        self.assertIn("- Adresse : 192.168.1.20:5555", text)
        self.assertIn("/data : 79 %", out)
        self.assertNotIn("ALERTE", out)
        self.assertIn("statut normal", out)
        self.assertIn("100.0 %    31.0 Mo  com.tcl.versionUpdateApp", out)
        self.assertIn(" 42.0 %    11.0 Mo  com.google.android.katniss", out)
        self.assertIn("  0.0 %     9.3 Mo  com.android.bluetooth", out)  # virgule decimale
        self.assertIn("swap : 123,456K physical used for 456,789K in swap", out)
        self.assertLess(len(out.splitlines()), 20, "synthese trop longue")

    def test_snapshot_follows_skill_template(self):
        skill = (SCRIPT.parent / "SKILL.md").read_text(encoding="utf-8")
        block = skill.split("````markdown", 1)[1].split("````", 1)[0]
        headings = [l for l in block.splitlines() if l.startswith("## ")]
        self.assertGreater(len(headings), 5)
        text = self.snapshot().read_text(encoding="utf-8")
        for heading in headings:
            self.assertIn(heading, text, "template du journal de SKILL.md non suivi")

    def test_snapshot_alerts_on_full_storage(self):
        self.fixtures(base_fixtures(**{"shell df -h /data": "/dev/block/dm-2 5G 4.6G 0.4G 90% /data\n"}))
        code, out = self.run_tv("snapshot", "192.168.1.20", "--dir", str(self.dir))
        self.assertEqual(code, 0, out)
        self.assertIn("ALERTE", out)

    def test_snapshot_reads_data_mounted_under_user_0(self):
        # Releve sur un Shield sous Android 11.
        self.fixtures(base_fixtures(**{"shell df -h /data":
            "Filesystem Size Used Avail Use% Mounted on\n/dev/block/mmcblk0p32 12G 3.3G 8.1G 29% /data/user/0\n"}))
        code, out = self.run_tv("snapshot", "192.168.1.20", "--dir", str(self.dir))
        self.assertEqual(code, 0, out)
        self.assertIn("/data : 29 %", out)

    def test_snapshot_never_overwrites_journal(self):
        self.snapshot()
        code, out = self.run_tv("snapshot", "192.168.1.20", "--dir", str(self.dir))
        self.assertEqual(code, 1, out)
        self.assertIn("existe deja", out)

    def test_unauthorized_device_is_environment_error(self):
        self.fixtures(base_fixtures(**{"get-state": "unauthorized\n"}))
        code, out = self.run_tv("snapshot", "192.168.1.20", "--dir", str(self.dir))
        self.assertEqual(code, 2, out)
        self.assertIn("'unauthorized'", out)

    def test_missing_adb_is_environment_error(self):
        code, out = self.run_tv("residents", "192.168.1.20", "x", adb=self.dir / "absent.py")
        self.assertEqual(code, 2, out)
        self.assertIn("adb introuvable", out)

    # ----------------------------------------------------------- residents

    def test_residents_one_line_per_package(self):
        code, out = self.run_tv("residents", "192.168.1.20",
                                "com.tcl.versionUpdateApp", "com.google.android.katniss")
        self.assertEqual(code, 0, out)
        self.assertIn("com.tcl.versionUpdateApp : oom svc (started-services) ; ServiceRecord 1 ;"
                      " jobs 1 ; BOOT_COMPLETED oui", out)
        self.assertIn("com.google.android.katniss : oom prev (previous) ; ServiceRecord 0", out)

    # ---------------------------------------------------------- check-plan

    def test_check_plan_ok(self):
        journal = self.journal_with_lot(("Assistant", "com.google.android.katniss"),
                                        ("Lanceur", "com.google.android.tvlauncher"))
        code, out = self.run_tv("check-plan", str(journal))
        self.assertEqual(code, 0, out)
        self.assertIn("2 paquet(s) en 2 groupe(s)", out)

    def test_check_plan_broken_cases(self):
        cases = [
            ("com.tcl.tv", "paquet critique"),                    # paquets.md, paragraphe 2
            ("com.android.providers.settings", "paquet critique"),  # joker du paragraphe 1
            ("com.android.shell", "paquet critique"),
            ("com.example.ime", "methode de saisie active"),
            ("com.google.android.backdrop", "deja desactive"),
            ("com.absent.app", "absent de l'appareil"),
        ]
        for pkg, expected in cases:
            with self.subTest(pkg=pkg):
                for old in self.dir.glob("tcl-percee-tv-*"):
                    if old.is_file():
                        old.unlink()
                journal = self.journal_with_lot(("G", pkg))
                code, out = self.run_tv("check-plan", str(journal))
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)

    def test_check_plan_launcher_android_8_home(self):
        self.fixtures(base_fixtures(**{"shell dumpsys package preferred-activities": PREFERRED_ANDROID_8}))
        journal = self.journal_with_lot(("Lanceur", "com.google.android.tvlauncher"))
        code, out = self.run_tv("check-plan", str(journal))
        self.assertEqual(code, 0, out)

    def test_check_plan_launcher_still_home(self):
        self.fixtures(base_fixtures(**{"shell dumpsys package preferred-activities": ""}))
        journal = self.journal_with_lot(("Lanceur", "com.google.android.tvlauncher"))
        code, out = self.run_tv("check-plan", str(journal))
        self.assertEqual(code, 1, out)
        self.assertIn("accueil prefere = aucun declare", out)

    def test_check_plan_duplicate_package(self):
        journal = self.journal_with_lot(("A", "com.google.android.katniss"),
                                        ("B", "com.google.android.katniss"))
        code, out = self.run_tv("check-plan", str(journal))
        self.assertEqual(code, 1, out)
        self.assertIn("present deux fois", out)

    def test_check_plan_without_lot_section(self):
        journal = self.dir / "sans-lot-2026-01-01.md"
        journal.write_text("# Intervention\n\n## Appareil\n- Adresse : 192.168.1.20\n",
                           encoding="utf-8")
        code, out = self.run_tv("check-plan", str(journal))
        self.assertEqual(code, 1, out)
        self.assertIn("section '## Lot' absente", out)

    # ------------------------------------------------------------- compare

    def journal_with_actions(self):
        journal = self.snapshot()
        text = journal.read_text(encoding="utf-8").replace(
            "| `<paquet>` | `pm disable-user --user 0 <paquet>` | `pm enable <paquet>` |\n",
            "| `com.google.android.katniss` | `pm disable-user --user 0 com.google.android.katniss`"
            " | `pm enable com.google.android.katniss` |\n"
            "| `window_animation_scale` | `settings put global window_animation_scale 0.5`"
            " | `settings delete global window_animation_scale` |\n",
        )
        journal.write_text(text, encoding="utf-8")
        return journal

    def after_intervention(self, **over):
        enabled = [p for p in ENABLED if p != "com.google.android.katniss"]
        f = base_fixtures(**{
            "shell pm list packages -e": pkgs(enabled),
            "shell pm list packages -d": pkgs(DISABLED + ["com.google.android.katniss"]),
            "shell settings get global window_animation_scale": "0.5\n",
        })
        f.update(over)
        self.fixtures(f)

    def test_compare_no_gap(self):
        journal = self.journal_with_actions()
        self.after_intervention()
        code, out = self.run_tv("compare", str(journal))
        self.assertEqual(code, 0, out)
        self.assertIn("desactives : 1/1 conformes", out)
        self.assertIn("mis a jour depuis le journal : 1 - com.spocky.projengmenu", out)
        self.assertIn("aucun ecart", out)

    def test_compare_uninstalled_package_is_expected(self):
        journal = self.journal_with_actions()
        text = journal.read_text(encoding="utf-8").replace(
            "## Actions\n| Paquet ou réglage | Action | Restauration |\n|---|---|---|\n",
            "## Actions\n| Paquet ou réglage | Action | Restauration |\n|---|---|---|\n"
            "| android | `pm uninstall` (essai) | reinstallation |\n")
        journal.write_text(text, encoding="utf-8")
        self.after_intervention(**{"shell pm list packages": pkgs(ENABLED[1:] + DISABLED + ["com.google.android.katniss"])})
        code, out = self.run_tv("compare", str(journal))
        self.assertEqual(code, 0, out)
        self.after_intervention()
        code, out = self.run_tv("compare", str(journal))
        self.assertEqual(code, 1, out)
        self.assertIn("paquet desinstalle d'apres le journal, present : android", out)

    def test_compare_broken_cases(self):
        journal = self.journal_with_actions()
        cases = [
            ({"shell pm list packages -e": pkgs(ENABLED),
              "shell pm list packages -d": pkgs(DISABLED)}, "paquet reactive : com.google.android.katniss"),
            ({"shell settings get global window_animation_scale": "1.0\n"},
             "reglage global window_animation_scale : trouve '1.0', attendu '0.5'"),
            ({"shell pm list packages": pkgs(ENABLED[1:] + DISABLED + ["com.google.android.katniss"])},
             "paquet de l'inventaire absent de l'appareil : android"),
        ]
        for over, expected in cases:
            with self.subTest(expected=expected):
                self.after_intervention(**over)
                code, out = self.run_tv("compare", str(journal))
                self.assertEqual(code, 1, out)
                self.assertIn(expected, out)

    # --------------------------------------------------------------- probe

    def test_probe_open_and_refused(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        free = socket.socket()
        free.bind(("127.0.0.1", 0))
        closed_port = free.getsockname()[1]
        free.close()
        try:
            open_port = server.getsockname()[1]
            code, out = self.run_tv("probe", "127.0.0.1", "--ports", f"{open_port},{closed_port}")
            self.assertEqual(code, 0, out)
            self.assertIn(f"127.0.0.1:{open_port} ouvert", out)
            self.assertIn(f"127.0.0.1:{closed_port} refus", out)
            code, out = self.run_tv("probe", "127.0.0.1", "--ports", f"{closed_port}")
            self.assertEqual(code, 1, out)
            self.assertIn("adbd n'ecoute pas en TCP", out)
        finally:
            server.close()


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if result.wasSuccessful() else 1)
