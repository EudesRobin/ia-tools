#!/usr/bin/env python3
"""Journal des modifications et version a publier, pour la skill release.

Lit le journal au format Keep a Changelog du depot courant et les tags git,
puis, selon le mode :
  (sans option)      releve l'etat : section non publiee et ses rubriques,
                     derniere version, dernier tag, numero propose ;
  --close X.Y.Z      clot la section non publiee sous la version X.Y.Z, ouvre
                     une section non publiee vide et met a jour les liens de
                     comparaison ;
  --notes X.Y.Z      affiche le corps de la section X.Y.Z (notes de Release).

Usage :
    python journal_version.py [--close X.Y.Z [--date AAAA-MM-JJ] | --notes X.Y.Z]
                              [--file <journal>] [--git <executable>]

Codes de sortie : 0 etat releve ou operation faite ; 1 erreur d'usage ou
operation refusee ; 2 anomalie d'environnement (git absent, hors d'un depot
git, journal introuvable).

Python >= 3.10, bibliotheque standard seule.
"""

from __future__ import annotations

import argparse
import datetime
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

CMD_TIMEOUT_S = 30

# Emplacements du journal, dans l'ordre de recherche.
CHANGELOG_FILES = ("CHANGELOG.md", "docs/CHANGELOG.md", "CHANGES.md", "HISTORY.md")

# Rubrique -> niveau d'incrementation. Les titres sont compares sans emoji,
# sans accents et sans casse ; une rubrique absente de la table est signalee.
MAJOR, MINOR, PATCH = "majeur", "mineur", "correctif"
HEADING_LEVELS = {
    MAJOR: ("removed", "breaking", "breaking changes", "action requise",
            "suppressions", "supprime", "changements incompatibles"),
    MINOR: ("added", "changed", "deprecated", "features", "nouveautes", "ajoute",
            "modifications", "modifie", "obsolescences", "obsolete"),
    PATCH: ("fixed", "security", "documentation", "docs", "maintenance",
            "corrections", "corrige", "securite", "performance", "chore"),
}
LEVEL_RANK = {PATCH: 0, MINOR: 1, MAJOR: 2}

SECTION_RE = re.compile(
    r"^## +(?:\[(?P<bracket>[^\]]+)\]|(?P<plain>\S+))(?: +[-–] +(?P<date>\d{4}-\d{2}-\d{2}))?\s*$")
VERSION_RE = re.compile(r"^(?P<prefix>v?)(?P<num>\d+\.\d+\.\d+)$")
LINK_RE = re.compile(r"^\[(?P<name>[^\]]+)\]:\s*(?P<url>\S+)\s*$")
COMPARE_RE = re.compile(r"^(?P<head>\S+/compare/)(?P<prev>\S+?)\.\.\.HEAD$")
ENTRY_RE = re.compile(r"^[-*] +\S")
TAGS_TRIGGER_RE = re.compile(r"^\s*tags\s*:", re.MULTILINE)

EXIT_OK, EXIT_USAGE, EXIT_ENV = 0, 1, 2


class EnvError(Exception):
    """Anomalie d'environnement : code de sortie 2."""


class Refused(Exception):
    """Operation refusee : code de sortie 1."""


class Git:
    def __init__(self, exe: str):
        if exe.endswith(".py"):  # faux git des tests
            if not Path(exe).is_file():
                raise EnvError(f"git introuvable : {exe}")
            self.cmd = [sys.executable, exe]
        else:
            found = shutil.which(exe)
            if not found:
                raise EnvError(f"git introuvable dans le PATH ({exe})")
            self.cmd = [found]

    def value(self, *args: str) -> str | None:
        try:
            res = subprocess.run([*self.cmd, *args], capture_output=True, timeout=CMD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise EnvError(f"git {' '.join(args)} : sans reponse apres {CMD_TIMEOUT_S:d} s")
        if res.returncode != 0:
            return None
        return res.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n").strip()


def normalize(title: str) -> str:
    """Titre de rubrique sans emoji, sans accents, en minuscules."""
    text = unicodedata.normalize("NFKD", title)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z ]", " ", text)
    return " ".join(text.lower().split())


def heading_level(title: str) -> str | None:
    key = normalize(title)
    for level, names in HEADING_LEVELS.items():
        if key in names:
            return level
    return None


def parse(text: str) -> tuple[list[dict], list[tuple[int, str, str]]]:
    """Sections '## ' (nom, date, ligne, rubriques, corps) et definitions de
    liens [nom]: url (indice de ligne, nom, url)."""
    sections: list[dict] = []
    links: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.split("\n")):
        m = LINK_RE.match(line)
        if m:
            links.append((i, m["name"], m["url"]))
            continue
        m = SECTION_RE.match(line)
        if m:
            sections.append({"name": m["bracket"] or m["plain"], "date": m["date"],
                             "bracket": m["bracket"] is not None, "index": i,
                             "headings": [], "body": []})
            continue
        if line.startswith("## "):
            sections.append({"name": line[3:].strip(), "date": None, "bracket": False,
                             "index": i, "headings": [], "body": []})
            continue
        if not sections:
            continue
        s = sections[-1]
        s["body"].append(line)
        if line.startswith("### "):
            s["headings"].append([line[4:].strip(), 0])
        elif ENTRY_RE.match(line) and s["headings"]:
            s["headings"][-1][1] += 1
    return sections, links


def version_key(name: str) -> tuple[int, int, int] | None:
    m = VERSION_RE.match(name)
    return tuple(int(x) for x in m["num"].split(".")) if m else None


def unreleased(sections: list[dict]) -> dict | None:
    """La section non publiee : la premiere, si son nom n'est pas une version."""
    if sections and version_key(sections[0]["name"]) is None:
        return sections[0]
    return None


def bump(base: tuple[int, int, int], level: str) -> tuple[tuple[int, int, int], str]:
    major, minor, patch = base
    if level == MAJOR and major == 0:
        return (0, minor + 1, 0), "version 0.y.z : un changement incompatible incremente MINEUR"
    if level == MAJOR:
        return (major + 1, 0, 0), ""
    if level == MINOR:
        return (major, minor + 1, 0), ""
    return (major, minor, patch + 1), ""


def fmt(v: tuple[int, int, int]) -> str:
    return ".".join(str(x) for x in v)


def semver_tags(git: Git) -> list[str]:
    out = git.value("tag", "--list", "--sort=-v:refname")
    return [t for t in (out or "").splitlines() if VERSION_RE.match(t.strip())]


def find_changelog(root: Path, explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        path = path if path.is_absolute() else root / path
        if not path.is_file():
            raise EnvError(f"journal introuvable : {explicit}")
        return path
    for name in CHANGELOG_FILES:
        if (root / name).is_file():
            return root / name
    raise EnvError(f"aucun journal parmi {', '.join(CHANGELOG_FILES)}")


def release_workflows(root: Path) -> list[str]:
    folder = root / ".github" / "workflows"
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob("*.y*ml")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if TAGS_TRIGGER_RE.search(text):
            found.append(path.name)
    return found


def state(root: Path, path: Path, git: Git) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    sections, links = parse(text)
    lines: list[tuple[str, str]] = [("journal", path.relative_to(root).as_posix())]
    # Dossier git : les notes de la Release y sont ecrites, hors de l'arbre de travail.
    git_dir = git.value("rev-parse", "--absolute-git-dir")
    lines.append(("git_dir", Path(git_dir).as_posix() if git_dir else "indetermine"))
    pending = unreleased(sections)
    lines.append(("section_non_publiee", pending["name"] if pending else "absente"))

    level, unknown, total = None, [], 0
    if pending:
        parts = []
        for title, count in pending["headings"]:
            total += count
            parts.append(f"{title} ({count})")
            lvl = heading_level(title)
            if lvl is None:
                unknown.append(title)
            elif count and (level is None or LEVEL_RANK[lvl] > LEVEL_RANK[level]):
                level = lvl
        lines.append(("rubriques", ", ".join(parts) or "aucune"))
        lines.append(("entrees", str(total)))
        if unknown:
            lines.append(("rubriques_inconnues", ", ".join(unknown)))

    versions = [s for s in sections if version_key(s["name"])]
    last = versions[0] if versions else None
    lines.append(("derniere_version", f"{last['name']} ({last['date'] or 'sans date'})" if last else "aucune"))
    tags = semver_tags(git)
    lines.append(("dernier_tag", tags[0] if tags else "aucun"))
    prefix = "v" if tags and tags[0].startswith("v") else ""
    lines.append(("prefixe_tag", prefix or "aucun"))
    if last:
        tag = prefix + VERSION_RE.match(last["name"])["num"]
        lines.append(("tag_pose", f"{'oui' if tag in tags else 'non'} ({tag})"))

    bases = [k for k in (version_key(last["name"]) if last else None,
                         version_key(tags[0]) if tags else None) if k]
    if not total:
        lines.append(("proposition", "aucune (section non publiee vide ou absente)"))
    elif not bases:
        lines.append(("proposition", "1.0.0 (premiere version ; 0.1.0 si l'API n'est pas stable)"))
    else:
        base = max(bases)
        lvl = level or PATCH
        new, note = bump(base, lvl)
        reason = f"{lvl} depuis {fmt(base)}"
        lines.append(("proposition", f"{fmt(new)} ({reason}{' ; ' + note if note else ''})"))

    unreleased_link = next((u for _, n, u in links if pending and n == pending["name"]), None)
    if unreleased_link and COMPARE_RE.match(unreleased_link):
        lines.append(("liens", "comparaison"))
    else:
        lines.append(("liens", "presents, hors modele de comparaison" if links else "aucun"))
    lines.append(("workflow_release", ", ".join(release_workflows(root)) or "aucun"))
    return lines


def close(root: Path, path: Path, git: Git, version: str, date: str) -> list[tuple[str, str]]:
    new = version_key(version)
    if new is None or VERSION_RE.match(version)["prefix"]:
        raise Refused(f"version '{version}' non conforme, attendu X.Y.Z sans prefixe")
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        raise Refused(f"date '{date}' invalide, attendu AAAA-MM-JJ")
    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    sections, links = parse(text)
    pending = unreleased(sections)
    if pending is None:
        raise Refused("aucune section non publiee en tete du journal")
    if not any(count for _, count in pending["headings"]):
        raise Refused(f"section '{pending['name']}' sans entree : rien a publier")
    versions = [version_key(s["name"]) for s in sections if version_key(s["name"])]
    tags = semver_tags(git)
    # Les tags comptent : une version deja taguee n'est jamais superieure.
    known = versions + [version_key(t) for t in tags]
    if known and new <= max(known):
        raise Refused(f"{version} n'est pas superieure a {fmt(max(known))}, "
                      "derniere version du journal ou des tags")
    prefix = "v" if tags and tags[0].startswith("v") else ""

    lines = text.split("\n")
    heading = f"## [{version}] - {date}" if pending["bracket"] else f"## {version} - {date}"
    at = pending["index"]
    lines[at + 1:at + 1] = ["", heading]

    links_state = "aucun"
    for i, name, url in links:
        if name != pending["name"]:
            continue
        m = COMPARE_RE.match(url)
        if not m:
            links_state = "non mis a jour (lien hors modele de comparaison)"
            break
        i += 2  # deux lignes inserees plus haut
        tag = prefix + version
        lines[i] = f"[{name}]: {m['head']}{tag}...HEAD"
        lines.insert(i + 1, f"[{version}]: {m['head']}{m['prev']}...{tag}")
        links_state = "mis a jour"
        break

    path.write_bytes(newline.join(lines).encode("utf-8"))
    return [("cloture", f"{version} - {date}"), ("section_non_publiee", f"{pending['name']} (vide)"),
            ("liens", links_state)]


def notes(path: Path, version: str) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    sections, _ = parse(text)
    for s in sections:
        if s["name"] in (version, "v" + version):
            body = "\n".join(s["body"]).strip()
            if body:
                return body
    raise Refused(f"section '{version}' absente ou vide")


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # erreur d'usage : code 1, pas 2
        self.print_usage(sys.stderr)
        sys.stderr.write(f"journal_version.py : {message}\n")
        sys.exit(EXIT_USAGE)


def main(argv: list[str] | None = None) -> int:
    p = Parser(description="Journal des modifications et version a publier (release)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--close", metavar="X.Y.Z", help="clore la section non publiee")
    mode.add_argument("--notes", metavar="X.Y.Z", help="afficher la section d'une version")
    p.add_argument("--date", default=datetime.date.today().isoformat(),
                   help="date de la version close (defaut : aujourd'hui)")
    p.add_argument("--file", help="journal, relatif a la racine du depot (defaut : recherche)")
    p.add_argument("--git", default="git", help="executable git (defaut : git du PATH)")
    args = p.parse_args(argv)
    # Emojis et accents des rubriques : sortie en UTF-8 quelle que soit la console.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        git = Git(args.git)
        root_raw = git.value("rev-parse", "--show-toplevel")
        if not root_raw:
            raise EnvError("le dossier courant n'est pas dans un depot git")
        root = Path(root_raw)
        path = find_changelog(root, args.file)
        if args.notes:
            print(notes(path, args.notes))
            return EXIT_OK
        lines = close(root, path, git, args.close, args.date) if args.close else state(root, path, git)
    except EnvError as exc:
        print(f"erreur : {exc}", file=sys.stderr)
        return EXIT_ENV
    except Refused as exc:
        print(f"refus : {exc}", file=sys.stderr)
        return EXIT_USAGE
    width = max(len(key) for key, _ in lines)
    for key, value in lines:
        print(f"{key.ljust(width)} : {value}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
