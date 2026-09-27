#!/usr/bin/env python3
"""Controle d'un message de commit, appele par le hook git commit-msg
(.githooks/commit-msg). Outillage du depot, jamais installe.

Verifie (CONVENTIONS.md section 1.5 et regles de style des commits) :
  - le sujet commence par un prefixe admis suivi de ': ' ;
  - le sujet ne se termine pas par un point ;
  - le message compte au plus 50 mots, sujet et corps compris ;
  - aucune attribution d'outil d'IA (Co-Authored-By, « Generated with »...).

Un commit de fusion (« Merge ... ») n'est pas controle.

Usage : python scripts/check_commit_msg.py <fichier du message>
Code de sortie : 0 si le message est conforme, 1 sinon.
"""

import re
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


def main() -> int:
    if len(sys.argv) != 2:
        print("usage : python scripts/check_commit_msg.py <fichier>", file=sys.stderr)
        return 1
    erreurs = ecarts(lire_message(Path(sys.argv[1])))
    for e in erreurs:
        print(f"commit-msg : {e}", file=sys.stderr)
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
