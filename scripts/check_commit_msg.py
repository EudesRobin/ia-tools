#!/usr/bin/env python3
"""Controle d'un message de commit, appele par le hook git commit-msg
(.githooks/commit-msg). Outillage du depot, jamais installe.

Verifie (CONVENTIONS.md section 1.5 et regles de style des commits) :
  - le sujet commence par un prefixe admis suivi de ': ' ;
  - le sujet ne se termine pas par un point ;
  - le message compte au plus 50 mots, sujet et corps compris ;
  - aucune attribution d'outil d'IA (Co-Authored-By, « Generated with »...).

Un commit de merge (« Merge ... ») n'est pas controle.

Trois modes :
  <fichier>             message d'un commit en cours (hook git commit-msg) ;
  --range <base>..<head> chaque commit de la plage, hors commits de merge
                        (integration continue, sur une pull request) ;
  --pr                  titre et description d'une pull request, lus dans les
                        variables d'environnement PR_TITLE et PR_BODY : seule
                        l'absence d'attribution d'IA y est controlee.

Dans l'integration continue (GITHUB_ACTIONS=true), chaque ecart est aussi emis
en annotation GitHub.

Usage : python scripts/check_commit_msg.py <fichier> | --range <base>..<head> | --pr
Code de sortie : 0 si tout est conforme, 1 sinon ou sur erreur d'usage, 2 si
git est absent.
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

PREFIXES = ("feat", "fix", "chore", "docs", "refactor", "test", "build", "revert")
MAX_WORDS = 50

PREFIX_RE = re.compile(rf"^({'|'.join(PREFIXES)}): \S")

# Attribution d'IA : un outil nomme sur une ligne Co-Authored-By ou « genere
# avec / par ». Un « genere par pandoc » reste admis.
AI_TOOLS = r"(claude|anthropic|copilot|openai|chatgpt|gpt-\d|gemini|\bia\b|\bai\b)"
ATTRIBUTION_RE = re.compile(
    rf"co-authored-by:[^\n]*{AI_TOOLS}|(generated|g[ée]n[ée]r[ée]e?s?) (with|by|avec|par)[^\n]*{AI_TOOLS}",
    re.IGNORECASE,
)

# Git ajoute sous cette ligne le diff d'un « commit --verbose » : a ignorer.
SCISSORS = "# ------------------------ >8"


def read_message(path: Path) -> str:
    raw = path.read_text(encoding="utf-8").split(SCISSORS)[0]
    lines = [l for l in raw.splitlines() if not l.startswith("#")]
    return "\n".join(lines).strip()


def issues(message: str) -> list[str]:
    if not message or message.startswith("Merge "):
        return []
    out = []
    subject = message.splitlines()[0].rstrip()
    if not PREFIX_RE.match(subject):
        out.append(f"sujet sans prefixe admis suivi de ': ' ({', '.join(PREFIXES)})")
    if subject.endswith("."):
        out.append("sujet termine par un point")
    words = len(message.split())
    if words > MAX_WORDS:
        out.append(f"{words} mots, maximum {MAX_WORDS} (sujet et corps compris)")
    if ATTRIBUTION_RE.search(message):
        out.append("attribution d'outil d'IA interdite (CONVENTIONS.md section 1.5)")
    return out


def range_issues(commit_range: str) -> list[str]:
    """Ecarts de chaque commit de la plage hors commits de merge, prefixes du sha court."""
    shas = subprocess.run(
        ["git", "rev-list", "--no-merges", "--reverse", commit_range],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    out = []
    for sha in shas:
        message = subprocess.run(
            ["git", "log", "-1", "--format=%B", sha],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout.strip()
        out += [f"{sha[:7]} : {e}" for e in issues(message)]
    return out


def pr_issues() -> list[str]:
    out = []
    for name, label in (("PR_TITLE", "titre"), ("PR_BODY", "description")):
        if ATTRIBUTION_RE.search(os.environ.get(name, "")):
            out.append(f"{label} de la pull request : attribution d'outil d'IA interdite (CONVENTIONS.md section 1.5)")
    return out


def main() -> int:
    p = argparse.ArgumentParser(prog="check_commit_msg.py")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("file", nargs="?", help="fichier du message (hook git commit-msg)")
    mode.add_argument("--range", metavar="BASE..HEAD", help="commits d'une pull request")
    mode.add_argument("--pr", action="store_true", help="titre et description (PR_TITLE, PR_BODY)")
    try:
        args = p.parse_args()
    except SystemExit as exc:  # argparse sort en 2 ; le code 2 est reserve a l'environnement
        return 1 if exc.code else 0
    try:
        if args.range:
            errors = range_issues(args.range)
        elif args.pr:
            errors = pr_issues()
        else:
            errors = issues(read_message(Path(args.file)))
    except FileNotFoundError:
        print("commit-msg : git introuvable dans le PATH", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"commit-msg : plage illisible '{args.range}' ({exc.stderr.strip().splitlines()[0]})", file=sys.stderr)
        return 1
    for e in errors:
        print(f"commit-msg : {e}", file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for e in errors:
            text = e.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=check_commit_msg.py::{text}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
