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
MAX_MOTS = 50

PREFIX_RE = re.compile(rf"^({'|'.join(PREFIXES)}): \S")

# Attribution d'IA : un outil nomme sur une ligne Co-Authored-By ou « genere
# avec / par ». Un « genere par pandoc » reste admis.
OUTILS_IA = r"(claude|anthropic|copilot|openai|chatgpt|gpt-\d|gemini|\bia\b|\bai\b)"
ATTRIBUTION_RE = re.compile(
    rf"co-authored-by:[^\n]*{OUTILS_IA}|(generated|g[ée]n[ée]r[ée]e?s?) (with|by|avec|par)[^\n]*{OUTILS_IA}",
    re.IGNORECASE,
)

# Git ajoute sous cette ligne le diff d'un « commit --verbose » : a ignorer.
CISEAUX = "# ------------------------ >8"


def lire_message(path: Path) -> str:
    brut = path.read_text(encoding="utf-8").split(CISEAUX)[0]
    lignes = [l for l in brut.splitlines() if not l.startswith("#")]
    return "\n".join(lignes).strip()


def ecarts(message: str) -> list[str]:
    if not message or message.startswith("Merge "):
        return []
    out = []
    sujet = message.splitlines()[0].rstrip()
    if not PREFIX_RE.match(sujet):
        out.append(f"sujet sans prefixe admis suivi de ': ' ({', '.join(PREFIXES)})")
    if sujet.endswith("."):
        out.append("sujet termine par un point")
    mots = len(message.split())
    if mots > MAX_MOTS:
        out.append(f"{mots} mots, maximum {MAX_MOTS} (sujet et corps compris)")
    if ATTRIBUTION_RE.search(message):
        out.append("attribution d'outil d'IA interdite (CONVENTIONS.md section 1.5)")
    return out


def ecarts_range(plage: str) -> list[str]:
    """Ecarts de chaque commit de la plage hors commits de merge, prefixes du sha court."""
    shas = subprocess.run(
        ["git", "rev-list", "--no-merges", "--reverse", plage],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    out = []
    for sha in shas:
        message = subprocess.run(
            ["git", "log", "-1", "--format=%B", sha],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout.strip()
        out += [f"{sha[:7]} : {e}" for e in ecarts(message)]
    return out


def ecarts_pr() -> list[str]:
    out = []
    for nom, libelle in (("PR_TITLE", "titre"), ("PR_BODY", "description")):
        if ATTRIBUTION_RE.search(os.environ.get(nom, "")):
            out.append(f"{libelle} de la pull request : attribution d'outil d'IA interdite (CONVENTIONS.md section 1.5)")
    return out


def main() -> int:
    p = argparse.ArgumentParser(prog="check_commit_msg.py")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("fichier", nargs="?", help="fichier du message (hook git commit-msg)")
    mode.add_argument("--range", metavar="BASE..HEAD", help="commits d'une pull request")
    mode.add_argument("--pr", action="store_true", help="titre et description (PR_TITLE, PR_BODY)")
    try:
        args = p.parse_args()
    except SystemExit as exc:  # argparse sort en 2 ; le code 2 est reserve a l'environnement
        return 1 if exc.code else 0
    try:
        if args.range:
            erreurs = ecarts_range(args.range)
        elif args.pr:
            erreurs = ecarts_pr()
        else:
            erreurs = ecarts(lire_message(Path(args.fichier)))
    except FileNotFoundError:
        print("commit-msg : git introuvable dans le PATH", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"commit-msg : plage illisible '{args.range}' ({exc.stderr.strip().splitlines()[0]})", file=sys.stderr)
        return 1
    for e in erreurs:
        print(f"commit-msg : {e}", file=sys.stderr)
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for e in erreurs:
            texte = e.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error title=check_commit_msg.py::{texte}")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
