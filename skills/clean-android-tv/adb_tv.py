#!/usr/bin/env python3
"""Releves adb en lecture seule pour la skill clean-android-tv.

Chaque sous-commande lance elle-meme les commandes adb, ecrit les sorties
volumineuses dans des fichiers et n'affiche qu'une synthese compacte. Aucune
sous-commande ne modifie l'appareil.

Usage :
    python adb_tv.py probe <IP>
    python adb_tv.py snapshot <IP> --dir <dossier>
    python adb_tv.py residents <IP> <paquet> [<paquet> ...]
    python adb_tv.py check-plan <journal> [--ip <IP>]
    python adb_tv.py compare <journal> [--ip <IP>]

Option commune : --adb <executable> (par defaut : adb, cherche dans le PATH).

Codes de sortie : 0 vert ; 1 ecart constate ou commande en echec ;
2 anomalie d'environnement (adb absent, appareil non connecte, fichier
illisible).

Python >= 3.10, bibliotheque standard seule.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import re
import shutil
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAQUETS_MD = HERE / "paquets.md"

# Ports sondes : 5555 pour adbd en TCP, 6466 et 6467 pour le service de
# telecommande Android TV (reference-adb.md, section 2).
PROBE_PORTS = (5555, 6466, 6467)
# 3 s : Windows ne signale un refus qu'apres deux nouvelles tentatives, soit
# environ 2 s ; en deca, un refus serait pris pour une expiration. Les ports
# sont sondes en parallele : la sonde entiere reste sous 4 s.
PROBE_TIMEOUT_S = 3.0
# Delai maximal d'une commande adb : dumpsys procstats et dumpsys package
# packages depassent rarement quelques secondes, meme sur un appareil lent.
ADB_TIMEOUT_S = 120
# Seuil d'occupation de /data au-dela duquel le stockage explique le
# ralentissement (SKILL.md, phase 3).
DATA_ALERT_PCT = 85
# Nombre de processus affiches depuis procstats et d'applications mises a jour
# affichees par compare : au-dela, la synthese cesse d'etre compacte.
TOP_N = 10

EXIT_OK, EXIT_GAP, EXIT_ENV = 0, 1, 2

PKG_RE = re.compile(r"`([a-zA-Z][\w]*(?:\.[\w*]+)+)`")


class EnvError(Exception):
    """Anomalie d'environnement : code de sortie 2."""


# --------------------------------------------------------------------- adb

class Adb:
    def __init__(self, exe: str, ip: str | None = None):
        self.cmd = self._resolve(exe)
        self.serial = None
        if ip:
            self.serial = ip if ":" in ip else f"{ip}:5555"

    @staticmethod
    def _resolve(exe: str) -> list[str]:
        # Un executable .py est lance par l'interpreteur courant : c'est ainsi
        # que les tests substituent un faux adb, y compris sous Windows.
        if exe.endswith(".py"):
            if not Path(exe).is_file():
                raise EnvError(f"adb introuvable : {exe}")
            return [sys.executable, exe]
        found = shutil.which(exe)
        if not found:
            raise EnvError(f"adb introuvable dans le PATH ({exe}) : installer platform-tools")
        return [found]

    def run(self, *args: str, check: bool = True) -> str:
        cmd = [*self.cmd, *(["-s", self.serial] if self.serial else []), *args]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=ADB_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise EnvError(f"adb {' '.join(args)} : sans reponse apres {ADB_TIMEOUT_S:d} s")
        out = res.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
        if check and res.returncode != 0:
            err = res.stderr.decode("utf-8", errors="replace").strip() or out.strip()
            raise EnvError(f"adb {' '.join(args)} : code {res.returncode} ({err[:200]})")
        return out

    def shell(self, command: str) -> str:
        return self.run("shell", command)

    def require_device(self) -> None:
        state = self.run("get-state", check=False).strip() or "absent"
        if state != "device":
            raise EnvError(
                f"appareil {self.serial} dans l'etat '{state}', attendu 'device' :"
                " lancer adb connect puis faire accepter la cle RSA"
            )

    def packages(self, flag: str = "") -> set[str]:
        out = self.shell(f"pm list packages {flag}".strip())
        return {l[8:].strip() for l in out.splitlines() if l.startswith("package:")}

    def preferred_home(self) -> str | None:
        return parse_preferred_home(self.shell("dumpsys package preferred-activities"))

    def input_method(self) -> str | None:
        value = self.shell("settings get secure default_input_method").strip()
        return None if value in ("", "null") else value.split("/", 1)[0]


# ------------------------------------------------------------- analyseurs

def parse_preferred_home(text: str) -> str | None:
    """Paquet de l'accueil prefere sous category.HOME, ou None.

    Une entree mAlways=true l'emporte ; a defaut, la premiere entree HOME :
    sous Android 8, l'accueil declare par set-home-activity peut porter
    mAlways=false. L'en-tete d'entree se termine par « filter <id> » selon
    la version, et mAlways precede ou suit les categories.
    """
    head = re.compile(r"^\s+[0-9a-f]+ ([\w.]+)/\S+(?:\s+filter\s+\S+)?\s*$")
    blocks: list[list] = []  # [paquet, is_home, always]
    inside = False
    for line in text.splitlines():
        if line.startswith("Preferred Activities"):
            inside = True
            continue
        if not inside:
            continue
        if line and not line.startswith(" "):
            break
        m = head.match(line)
        if m:
            blocks.append([m.group(1), False, False])
        elif blocks and "android.intent.category.HOME" in line:
            blocks[-1][1] = True
        elif blocks and "mAlways=true" in line:
            blocks[-1][2] = True
    homes = [b for b in blocks if b[1]]
    always = [b for b in homes if b[2]]
    return (always or homes or [[None]])[0][0]


def parse_meminfo(text: str) -> dict[str, str]:
    info = {}
    for key in ("Total RAM", "Free RAM", "ZRAM"):
        m = re.search(rf"^\s*{key}:\s*(.+)$", text, re.MULTILINE)
        if m:
            info[key] = re.sub(r"\(\s+", "(", " ".join(m.group(1).split()))
    if "Total RAM" in info:
        status = re.search(r"\(status (\w+)\)", info["Total RAM"])
        info["status"] = status.group(1) if status else "inconnu"
        info["Total RAM"] = info["Total RAM"].split("(")[0].strip()
    if "Free RAM" in info:
        info["Free RAM"] = info["Free RAM"].split("(")[0].strip()
    return info


def parse_df_pct(text: str) -> int | None:
    # /data, ou /data/user/0 sous Android 11 (montage lie).
    for line in text.splitlines():
        m = re.search(r"(\d+)%\s+(/data\S*)\s*$", line)
        if m:
            return int(m.group(1))
    return None


def number(text: str) -> float:
    """Nombre au format de la locale de l'appareil : '8,1' comme '8.1'."""
    return float(text.replace(",", "."))


def parse_procstats_top(text: str, n: int = TOP_N) -> list[tuple[float, float, str]]:
    """(presence %, PSS moyen en Mo, processus), classes par memoire ponderee
    par la presence : beaucoup de processus persistants sont a 100 %."""
    head = re.compile(r"^\s*\*\s+(\S+)\s+/\s+\S+\s+/\s+v\S*:")
    total = re.compile(r"^\s*TOTAL:\s*([\d.,]+)%(?:\s*\(([\d.,]+)(K|M|G)B-([\d.,]+)(K|M|G)B-)?")
    scale = {"K": 1 / 1024, "M": 1.0, "G": 1024.0}
    best: dict[str, tuple[float, float]] = {}
    current = None
    for line in text.splitlines():
        m = head.match(line)
        if m:
            current = m.group(1)
            continue
        m = total.match(line)
        if m and current:
            pss = number(m.group(4)) * scale[m.group(5)] if m.group(4) else 0.0
            pct = number(m.group(1))
            if pct * pss >= best.get(current, (0.0, 0.0))[0] * best.get(current, (0.0, 0.0))[1]:
                best[current] = (pct, pss)
            current = None
    ranked = sorted(best.items(), key=lambda kv: (-kv[1][0] * kv[1][1], kv[0]))
    return [(pct, pss, name) for name, (pct, pss) in ranked[:n]]


def parse_oom_state(text: str, pkg: str) -> list[str]:
    """Etiquettes oom des processus du paquet (fore, svc, prev, cch-empty...)."""
    states = []
    line_re = re.compile(r"(?:Proc|PERS)\s*#\s*\d+:\s*(\S+).*?\d+:([\w.:]+)/\S+\s*\(([^)]*)\)")
    for line in text.splitlines():
        m = line_re.search(line)
        if m and (m.group(2) == pkg or m.group(2).startswith(pkg + ":")):
            states.append(f"{m.group(1)} ({m.group(3)})")
    return states


def kebab(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "appareil"


# ------------------------------------------------------ paquets critiques

def load_critical() -> tuple[list[str], set[str]]:
    """Motifs critiques et lanceurs, lus dans paquets.md (jamais recopies ici).

    Critiques : identifiants du tableau du paragraphe 1 et lignes classees
    « Critique » des tableaux du paragraphe 2. Lanceurs : lignes du tableau
    du paragraphe 1 dont le role commence par « Lanceur » ; ils ne sont
    critiques que tant qu'aucun autre accueil n'est declare.
    """
    try:
        text = PAQUETS_MD.read_text(encoding="utf-8")
    except OSError as exc:
        raise EnvError(f"{PAQUETS_MD.name} illisible a cote du script ({exc})")
    sec1 = re.search(r"^## 1\..*?(?=^## 2\.)", text, re.DOTALL | re.MULTILINE)
    sec2 = re.search(r"^## 2\..*?(?=^## 3\.)", text, re.DOTALL | re.MULTILINE)
    if not sec1 or not sec2:
        raise EnvError(f"{PAQUETS_MD.name} : paragraphes 1 et 2 introuvables")
    critical: list[str] = []
    launchers: set[str] = set()
    for row in table_rows(sec1.group(0)):
        if len(row) < 2:
            continue
        pkgs = PKG_RE.findall(row[0])
        if row[1].startswith("Lanceur"):
            launchers.update(pkgs)
        else:
            critical += pkgs
    for row in table_rows(sec2.group(0)):
        if len(row) >= 2 and row[1].startswith("Critique"):
            critical += PKG_RE.findall(row[0])
    # Canal adb lui-meme : critique quoi qu'il arrive a paquets.md.
    critical.append("com.android.shell")
    return critical, launchers


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and not re.match(r"^\|[\s|:-]+\|$", s):
            rows.append([c.strip() for c in s.strip("|").split("|")])
    return rows


def is_critical(pkg: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(pkg, p) for p in patterns)


# ----------------------------------------------------------------- journal

class Journal:
    def __init__(self, path: Path):
        self.path = path
        try:
            self.lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise EnvError(f"journal illisible : {path} ({exc})")

    def section(self, title: str) -> list[tuple[int, str]]:
        """Lignes (numero, texte) de la section '## <title>', sans son titre."""
        out, inside = [], False
        for i, line in enumerate(self.lines, 1):
            if line.startswith("## "):
                inside = line[3:].strip().startswith(title)
                continue
            if inside:
                out.append((i, line))
        return out

    def rows(self, title: str) -> list[tuple[int, list[str]]]:
        """Lignes de tableau de la section, sans en-tetes ni lignes de template.

        Une section peut porter plusieurs tableaux (un par groupe) : l'en-tete
        est la ligne que suit la ligne de separation.
        """
        lines = self.section(title)
        sep = re.compile(r"^\s*\|[\s|:-]+\|\s*$")
        rows = []
        for k, (i, line) in enumerate(lines):
            nxt = lines[k + 1][1] if k + 1 < len(lines) else ""
            r = table_rows(line)
            if r and "<" not in line and not sep.match(nxt):
                rows.append((i, r[0]))
        return rows

    def field(self, label: str) -> str | None:
        for line in self.lines:
            m = re.match(rf"^- {re.escape(label)} : (.+)$", line)
            if m and "<" not in m.group(1):
                return m.group(1).strip()
        return None

    def ip(self) -> str | None:
        return self.field("Adresse")

    def date(self) -> dt.date | None:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", self.lines[0] if self.lines else "")
        m = m or re.search(r"(\d{4}-\d{2}-\d{2})", self.path.name)
        return dt.date.fromisoformat(m.group(1)) if m else None

    def inventory(self) -> set[str]:
        pkgs, fence = set(), False
        for _, line in self.section("Inventaire initial"):
            if line.startswith("```"):
                fence = not fence
            elif fence and line.startswith("package:"):
                pkgs.add(line[8:].strip())
        return pkgs


def strip_code(cell: str) -> str:
    return cell.replace("`", "").strip()


# ------------------------------------------------------------- commandes

def probe_port(ip: str, port: int) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(PROBE_TIMEOUT_S)
    try:
        sock.connect((ip, port))
        return "ouvert"
    except ConnectionRefusedError:
        return "refus"
    except (socket.timeout, TimeoutError):
        return "expiration"
    except OSError as exc:
        return f"erreur ({exc.strerror or exc})"
    finally:
        sock.close()


def cmd_probe(args) -> int:
    with ThreadPoolExecutor(max_workers=len(args.ports)) as pool:
        states = pool.map(lambda p: probe_port(args.ip, p), args.ports)
    results = dict(zip(args.ports, states))
    for port, state in results.items():
        print(f"{args.ip}:{port} {state}")
    adb_port = args.ports[0]
    state = results[adb_port]
    if state == "refus":
        print("=> l'hote repond mais adbd n'ecoute pas en TCP : reseau et VPN hors de cause"
              " (reference-adb.md, section 3)")
    elif state == "expiration":
        print("=> l'hote ne repond pas : adresse erronee ou changee, segment distinct ou filtrage"
              " (arp -a, reference-adb.md, section 2)")
    if any(results.get(p) == "ouvert" for p in args.ports[1:]):
        print("=> service de telecommande present : un appareil Android TV repond a cette adresse")
    return EXIT_OK if state == "ouvert" else EXIT_GAP


def cmd_snapshot(args) -> int:
    adb = Adb(args.adb, args.ip)
    adb.require_device()
    model = adb.shell("getprop ro.product.model").strip() or "inconnu"
    maker = adb.shell("getprop ro.product.manufacturer").strip()
    # Le nom du journal porte le constructeur : « Percee TV » seul ne dit pas TCL.
    if maker and not model.lower().startswith(maker.lower()):
        model = f"{maker} {model}"
    release = adb.shell("getprop ro.build.version.release").strip()
    sdk = adb.shell("getprop ro.build.version.sdk").strip()
    today = dt.date.today().isoformat()
    folder = Path(args.dir)
    journal = folder / f"{kebab(model)}-{today}.md"
    raw_dir = folder / f"{journal.stem}-releves"
    if journal.exists():
        print(f"{journal} existe deja : rien n'est ecrit (choisir un autre dossier)")
        return EXIT_GAP

    raw = {
        "df-data.txt": adb.shell("df -h /data"),
        "meminfo.txt": adb.shell("dumpsys meminfo"),
        "diskstats.txt": adb.shell("dumpsys diskstats"),
        "procstats-24h.txt": adb.shell("dumpsys procstats --hours 24"),
        "uptime.txt": adb.shell("uptime"),
    }
    counts = {f: adb.packages(f) for f in ("-s", "-3", "-e", "-d")}
    inventory = adb.shell("pm list packages -e")

    pct = parse_df_pct(raw["df-data.txt"])
    mem = parse_meminfo(raw["meminfo.txt"])
    top = parse_procstats_top(raw["procstats-24h.txt"])
    uptime = raw["uptime.txt"].strip()

    raw_dir.mkdir(parents=True, exist_ok=True)
    for name, content in raw.items():
        (raw_dir / name).write_text(content, encoding="utf-8")
    journal.write_text(journal_template(
        model, release, sdk, adb.serial, today, pct, mem, uptime, inventory, raw_dir.name
    ), encoding="utf-8")

    data = f"{pct} %" if pct is not None else "non lu (voir df-data.txt)"
    print(f"journal : {journal}")
    print(f"releves bruts : {raw_dir}")
    print(f"modele : {model} - Android {release} (SDK {sdk})")
    print(f"/data : {data}" + (f"  ALERTE : au-dela de {DATA_ALERT_PCT:d} %, le stockage"
                                 " explique le ralentissement" if pct and pct > DATA_ALERT_PCT else ""))
    print(f"memoire : Total {mem.get('Total RAM', '?')} (statut {mem.get('status', '?')}),"
          f" Free {mem.get('Free RAM', '?')}")
    print(f"swap : {mem.get('ZRAM', 'non lu')}")
    print(f"uptime : {uptime}")
    print("paquets : " + ", ".join(f"{f} {len(p)}" for f, p in counts.items()))
    if top:
        print(f"procstats 24 h, {len(top)} premiers (presence x PSS moyen) :")
        for pct_total, pss, name in top:
            print(f"  {pct_total:5.1f} %  {pss:6.1f} Mo  {name}")
    else:
        print("procstats : format non reconnu, lire procstats-24h.txt")
    return EXIT_OK


def journal_template(model, release, sdk, serial, today, pct, mem, uptime, inventory, raw_name):
    # Reprend le template imperatif du journal de SKILL.md : modifier les deux ensemble.
    data = f"{pct} %" if pct is not None else "non lu"
    return "\n".join([
        f"# Intervention {kebab(model)} — {today}",
        "",
        "## Appareil",
        f"- Modèle : {model} — Android {release} (SDK {sdk})",
        f"- Adresse : {serial}",
        "",
        "## État initial",
        f"- `/data` : {data}",
        f"- Mémoire : Total RAM {mem.get('Total RAM', '?')} ({mem.get('status', '?')}),"
        f" Free RAM {mem.get('Free RAM', '?')}, swap {mem.get('ZRAM', '?')}, uptime {uptime}",
        "- Processus résidents : <paquet — état oom>, …",
        f"- Relevés bruts : `{raw_name}/`",
        "",
        "## Inventaire initial — `pm list packages -e`",
        "```",
        inventory.strip(),
        "```",
        "",
        "## Lot",
        "| Groupe | Paquet | Rôle réel | Ce que la désactivation retire |",
        "|---|---|---|---|",
        "| <groupe> | `<paquet>` | <rôle> | <effet> |",
        "",
        "## Actions",
        "| Paquet ou réglage | Action | Restauration |",
        "|---|---|---|",
        "| `<paquet>` | `pm disable-user --user 0 <paquet>` | `pm enable <paquet>` |",
        "",
        "## État final",
        "- Accueil déclaré : <activité, ou lanceur d'origine>",
        "- Réglages d'activité en background : <paquet — vérifié ou non vérifié>",
        "",
        "## Réactivation complète",
        "<commandes inverses, puis marche à suivre depuis les menus du téléviseur>",
        "",
    ])


def cmd_residents(args) -> int:
    adb = Adb(args.adb, args.ip)
    adb.require_device()
    oom = adb.shell("dumpsys activity oom")
    jobs = adb.shell("dumpsys jobscheduler")
    for pkg in args.packages:
        states = parse_oom_state(oom, pkg) or ["aucun processus"]
        services = adb.shell(f"dumpsys activity services {pkg}").count("* ServiceRecord{")
        njobs = sum(1 for l in jobs.splitlines() if "JOB #" in l and pkg in l)
        boot = "oui" if "BOOT_COMPLETED" in adb.shell(f"dumpsys package {pkg}") else "non"
        print(f"{pkg} : oom {', '.join(states)} ; ServiceRecord {services} ; jobs {njobs} ;"
              f" BOOT_COMPLETED {boot}")
    return EXIT_OK


def cmd_check_plan(args) -> int:
    journal = Journal(Path(args.journal))
    if not journal.section("Lot"):
        print(f"{journal.path} : section '## Lot' absente, attendue avant la phase 6")
        return EXIT_GAP
    rows = journal.rows("Lot")
    if not rows:
        print(f"{journal.path} : section '## Lot' sans ligne de paquet")
        return EXIT_GAP
    critical, launchers = load_critical()
    adb = Adb(args.adb, args.ip or journal.ip())
    adb.require_device()
    enabled, disabled = adb.packages("-e"), adb.packages("-d")
    ime, home = adb.input_method(), adb.preferred_home()

    errors, seen, groups = [], set(), {}
    for line, row in rows:
        if len(row) < 2:
            errors.append(f"{journal.path.name}:{line} : ligne incomplete, attendu 'Groupe | Paquet | ...'")
            continue
        group, pkg = row[0], strip_code(row[1])
        where = f"{journal.path.name}:{line} : {pkg}"
        if pkg in seen:
            errors.append(f"{where} : present deux fois dans le lot")
        seen.add(pkg)
        groups.setdefault(group, []).append(pkg)
        if pkg in disabled:
            errors.append(f"{where} : trouve 'deja desactive', attendu 'active'")
        elif pkg not in enabled:
            errors.append(f"{where} : trouve 'absent de l'appareil', attendu 'active'")
        if is_critical(pkg, critical):
            errors.append(f"{where} : trouve 'paquet critique (paquets.md)', attendu 'non critique'")
        if pkg == ime:
            errors.append(f"{where} : trouve 'methode de saisie active', attendu 'autre paquet'")
        if pkg in launchers and home in (None, pkg):
            errors.append(f"{where} : trouve 'accueil prefere = {home or 'aucun declare'}',"
                          " attendu 'autre accueil declare par set-home-activity'")
    if errors:
        print(f"check-plan : {len(errors)} ecart(s), lot non applicable")
        for e in errors:
            print(f"  {e}")
        return EXIT_GAP
    print(f"check-plan : OK - {len(seen)} paquet(s) en {len(groups)} groupe(s)")
    for group, pkgs in groups.items():
        print(f"  {group} : {', '.join(pkgs)}")
    return EXIT_OK


def cmd_compare(args) -> int:
    journal = Journal(Path(args.journal))
    adb = Adb(args.adb, args.ip or journal.ip())
    adb.require_device()
    inventory = journal.inventory()
    if not inventory:
        raise EnvError(f"{journal.path} : inventaire initial introuvable ou vide")
    actions = journal.rows("Actions")
    want_disabled, uninstalled, settings, appops = set(), set(), [], []
    for _, row in actions:
        if len(row) < 2:
            continue
        action = [a.strip("\"'") for a in strip_code(row[1]).split()]
        if action[:2] == ["adb", "shell"]:
            action = action[2:]
        if action[:2] == ["pm", "disable-user"]:
            want_disabled.add(action[-1])
        elif action[:2] == ["pm", "uninstall"]:
            # Paquet en fin de commande, a defaut en premiere colonne.
            named = [a for a in action[2:] if PKG_RE.fullmatch(f"`{a}`")]
            uninstalled.add(named[-1] if named else strip_code(row[0]))
        elif action[:2] == ["settings", "put"] and len(action) >= 5:
            settings.append((action[2], action[3], action[4]))
        elif action[:3] == ["cmd", "appops", "set"] and len(action) >= 6:
            appops.append((action[3], action[4], action[5]))

    enabled, disabled, every = adb.packages("-e"), adb.packages("-d"), adb.packages()
    gaps = []
    for pkg in sorted(want_disabled):
        if pkg in enabled:
            gaps.append(f"paquet reactive : {pkg}")
        elif pkg not in every:
            gaps.append(f"paquet desinstalle : {pkg}")
    for pkg in sorted(inventory - every - uninstalled):
        gaps.append(f"paquet de l'inventaire absent de l'appareil : {pkg}")
    for pkg in sorted(uninstalled & every):
        gaps.append(f"paquet desinstalle d'apres le journal, present : {pkg}")
    for pkg in sorted(enabled - inventory - want_disabled):
        gaps.append(f"paquet nouveau ou reactive hors journal : {pkg}")
    for ns, key, value in settings:
        now = adb.shell(f"settings get {ns} {key}").strip()
        if value[:1] in ("+", "-"):
            # Liste modifiee element par element (location_providers_allowed).
            present = value[1:] in now.split(",")
            if present != (value[0] == "+"):
                gaps.append(f"reglage {ns} {key} : trouve '{now}', attendu '{value}' applique")
        # Une liste videe par settings put "" se relit comme null.
        elif now != value and {now, value} != {"", "null"}:
            gaps.append(f"reglage {ns} {key} : trouve '{now}', attendu '{value}'")
    for pkg, op, mode in appops:
        now = adb.shell(f"cmd appops get {pkg} {op}")
        if mode not in now:
            gaps.append(f"appops {pkg} {op} : trouve '{now.strip()[:80]}', attendu '{mode}'")
    declared = journal.field("Accueil déclaré")
    home = adb.preferred_home()
    if declared and home and home not in declared:
        gaps.append(f"accueil : trouve '{home}', attendu '{declared}'")

    since = journal.date()
    updated = []
    if since:
        current = None
        for line in adb.shell("dumpsys package packages").splitlines():
            m = re.match(r"^\s*Package \[([\w.]+)\]", line)
            if m:
                current = m.group(1)
                continue
            m = re.match(r"^\s*lastUpdateTime=(\d{4}-\d{2}-\d{2})", line)
            if m and current and dt.date.fromisoformat(m.group(1)) > since:
                updated.append(current)
                current = None

    print(f"journal : {journal.path.name} ({since or 'date inconnue'})")
    print(f"uptime : {adb.shell('uptime').strip()}")
    print(f"desactives : {len(want_disabled & disabled)}/{len(want_disabled)} conformes au journal")
    print(f"accueil prefere : {home or 'aucun declare'}")
    acc = adb.shell("settings get secure enabled_accessibility_services").strip()
    print(f"services d'accessibilite : {acc or 'null'}")
    if updated:
        shown = ", ".join(sorted(updated)[:TOP_N])
        more = f" (+{len(updated) - TOP_N})" if len(updated) > TOP_N else ""
        print(f"mis a jour depuis le journal : {len(updated)} - {shown}{more}")
    if gaps:
        print(f"compare : {len(gaps)} ecart(s)")
        for g in gaps:
            print(f"  {g}")
        return EXIT_GAP
    print("compare : aucun ecart")
    return EXIT_OK


# -------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    p = argparse.ArgumentParser(description="Releves adb en lecture seule (clean-android-tv)")
    p.add_argument("--adb", default="adb", help="executable adb (defaut : adb du PATH)")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("probe", help="sonder les ports adb et telecommande")
    s.add_argument("ip")
    s.add_argument("--ports", type=lambda v: [int(x) for x in v.split(",")],
                   default=list(PROBE_PORTS), help="ports, le premier etant celui d'adb")
    s.set_defaults(func=cmd_probe)

    s = sub.add_parser("snapshot", help="releve initial et creation du journal")
    s.add_argument("ip")
    s.add_argument("--dir", required=True, help="dossier du journal")
    s.set_defaults(func=cmd_snapshot)

    s = sub.add_parser("residents", help="resident ou en cache, par paquet")
    s.add_argument("ip")
    s.add_argument("packages", nargs="+")
    s.set_defaults(func=cmd_residents)

    s = sub.add_parser("check-plan", help="verifier la section '## Lot' du journal")
    s.add_argument("journal")
    s.add_argument("--ip", help="adresse, a defaut celle du journal")
    s.set_defaults(func=cmd_check_plan)

    s = sub.add_parser("compare", help="comparer l'appareil au journal")
    s.add_argument("journal")
    s.add_argument("--ip", help="adresse, a defaut celle du journal")
    s.set_defaults(func=cmd_compare)

    args = p.parse_args(argv)
    try:
        if args.command in ("check-plan", "compare") and not (args.ip or Journal(Path(args.journal)).ip()):
            raise EnvError("adresse introuvable dans le journal ('- Adresse : ...') : passer --ip")
        return args.func(args)
    except EnvError as exc:
        print(f"{args.command} : {exc}")
        return EXIT_ENV


if __name__ == "__main__":
    sys.exit(main())
