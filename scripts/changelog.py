#!/usr/bin/env python3
"""Journal des modifications CHANGELOG.md (docs/CONTRIBUTING.md section 4).
Outillage du depot, jamais installe.

Trois modes :
  (sans option)            controle la structure de CHANGELOG.md ;
  --version X.Y.Z          affiche la section de cette version (notes de la
                           Release GitHub) ;
  --require-entry BASE..HEAD refuse une plage qui modifie skills/, agents/,
                           hooks/, statuslines/ ou scripts/install.py sans
                           modifier CHANGELOG.md
                           (integration continue, sur une pull request).

Structure controlee : premiere section '## [Non publie]', sans date ; puis des
sections '## [X.Y.Z] - AAAA-MM-JJ', versions strictement decroissantes, dates
valides et non croissantes ; rubriques '### ' prises dans ALLOWED_HEADINGS, dans cet
ordre, sans doublon, chacune avec au moins une entree '- '.

Les messages sont volontairement sans accents : ce script s'affiche dans une
console PowerShell (docs/PREREQUIS.md, section « Encodage de la console »).

Usage : python scripts/changelog.py [--version X.Y.Z | --require-entry BASE..HEAD]
Code de sortie : 0 si conforme, 1 sinon ou sur erreur d'usage, 2 si git est
absent.
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILENAME = "CHANGELOG.md"

# Rubriques admises, dans l'ordre impose (docs/CONTRIBUTING.md section 4.2).
ALLOWED_HEADINGS = (
    "💥 Action requise",
    "🚀 Nouveautés",
    "🔄 Modifications",
    "⏳ Obsolescences",
    "🔥 Suppressions",
    "🐛 Corrections",
    "🔒 Sécurité",
    "📝 Documentation",
    "🧹 Maintenance",
)
UNRELEASED = "Non publié"

VERSION_RE = re.compile(r"^## \[(?P<name>[^\]]+)\](?: - (?P<date>\S+))?\s*$")
NUMBER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Chemins dont la modification exige une entree du journal.
WATCHED_PATHS = ("skills/", "agents/", "hooks/", "statuslines/", "scripts/install.py")


def parse_sections(text: str) -> list[dict]:
    """Sections '## [...]' : nom, date, ligne du titre, lignes du corps."""
    out: list[dict] = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            m = VERSION_RE.match(line)
            out.append({
                "name": m["name"] if m else line[3:].strip(),
                "date": m["date"] if m else None,
                "line": n,
                "valid": bool(m),
                "body": [],
            })
        elif out and not re.match(r"^\[[^\]]+\]:\s", line):
            out[-1]["body"].append((n, line))
    return out


def structure_issues(text: str) -> list[str]:
    out: list[str] = []
    parsed = parse_sections(text)
    if not parsed:
        return [f"{FILENAME} : aucune section '## [...]'"]
    if parsed[0]["name"] != UNRELEASED or parsed[0]["date"]:
        out.append(f"{FILENAME}:{parsed[0]['line']} : la premiere section doit etre '## [{UNRELEASED}]', sans date")
    previous = None
    for s in parsed:
        where = f"{FILENAME}:{s['line']}"
        if not s["valid"]:
            out.append(f"{where} : titre de section non conforme, attendu '## [X.Y.Z] - AAAA-MM-JJ'")
            continue
        if s is not parsed[0]:
            if not NUMBER_RE.match(s["name"]):
                out.append(f"{where} : version '{s['name']}' non conforme, attendu X.Y.Z")
                continue
            try:
                date = datetime.date.fromisoformat(s["date"] or "")
            except ValueError:
                out.append(f"{where} : date absente ou invalide, attendu AAAA-MM-JJ")
                continue
            key = (tuple(int(x) for x in s["name"].split(".")), date)
            if previous and not (key[0] < previous[0] and key[1] <= previous[1]):
                out.append(f"{where} : version ou date non decroissante")
            previous = key
        out += heading_issues(s)
    return out


def heading_issues(s: dict) -> list[str]:
    out: list[str] = []
    rank = -1
    seen: list[tuple[int, str, int]] = []  # (ligne, rubrique, nombre d'entrees)
    for n, line in s["body"]:
        if line.startswith("### "):
            title = line[4:].strip()
            if title not in ALLOWED_HEADINGS:
                out.append(f"{FILENAME}:{n} : rubrique non prevue '{title}'")
                continue
            if ALLOWED_HEADINGS.index(title) <= rank:
                out.append(f"{FILENAME}:{n} : rubrique '{title}' en double ou hors de l'ordre prevu")
            rank = max(rank, ALLOWED_HEADINGS.index(title))
            seen.append((n, title, 0))
        elif line.startswith("- ") and seen:
            n0, title, k = seen[-1]
            seen[-1] = (n0, title, k + 1)
        elif line.startswith("- "):
            out.append(f"{FILENAME}:{n} : entree hors rubrique")
    out += [f"{FILENAME}:{n} : rubrique '{t}' sans entree" for n, t, k in seen if k == 0]
    return out


def version_notes(text: str, version: str) -> str | None:
    """Corps de la section d'une version, sans lignes vides de bord."""
    for s in parse_sections(text):
        if s["name"] == version:
            return "\n".join(l for _, l in s["body"]).strip()
    return None


def changed_files(commit_range: str) -> list[str]:
    base, _, head = commit_range.partition("..")
    return subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()


def main() -> int:
    p = argparse.ArgumentParser(prog="changelog.py")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--version", metavar="X.Y.Z", help="afficher la section de cette version")
    mode.add_argument("--require-entry", metavar="BASE..HEAD", help="plage d'une pull request")
    try:
        args = p.parse_args()
    except SystemExit as exc:  # argparse sort en 2 ; le code 2 est reserve a l'environnement
        return 1 if exc.code else 0

    if args.require_entry:
        try:
            changed = changed_files(args.require_entry)
        except FileNotFoundError:
            print("changelog.py : git introuvable dans le PATH", file=sys.stderr)
            return 2
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip().splitlines()[0] if exc.stderr.strip() else exc
            print(f"changelog.py : plage illisible '{args.require_entry}' ({detail})", file=sys.stderr)
            return 1
        tools = [f for f in changed if f.startswith(WATCHED_PATHS)]
        if tools and FILENAME not in changed:
            print(
                f"changelog.py : {len(tools)} fichier(s) d'outil modifie(s) sans entree dans "
                f"{FILENAME} (docs/CONTRIBUTING.md section 4.2) : {', '.join(tools[:5])}",
                file=sys.stderr,
            )
            return 1
        return 0

    path = ROOT / FILENAME
    if not path.is_file():
        print(f"changelog.py : {FILENAME} manquant", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")

    if args.version:
        body = version_notes(text, args.version)
        if not body:
            print(f"changelog.py : section '{args.version}' absente ou vide dans {FILENAME}", file=sys.stderr)
            return 1
        # Emojis et accents : l'encodage par defaut d'une console PowerShell les corromprait.
        sys.stdout.reconfigure(encoding="utf-8")
        print(body)
        return 0

    errors = structure_issues(text)
    for e in errors:
        print(f"changelog.py : {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
