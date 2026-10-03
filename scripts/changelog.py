#!/usr/bin/env python3
"""Journal des modifications CHANGELOG.md (docs/CONTRIBUTING.md section 4).
Outillage du depot, jamais installe.

Trois modes :
  (sans option)            controle la structure de CHANGELOG.md ;
  --version X.Y.Z          affiche la section de cette version (notes de la
                           Release GitHub) ;
  --exige-entree BASE..HEAD refuse une plage qui modifie skills/, agents/,
                           hooks/, statuslines/ ou scripts/install.py sans
                           modifier CHANGELOG.md
                           (integration continue, sur une pull request).

Structure controlee : premiere section '## [Non publie]', sans date ; puis des
sections '## [X.Y.Z] - AAAA-MM-JJ', versions strictement decroissantes, dates
valides et non croissantes ; rubriques '### ' prises dans RUBRIQUES, dans cet
ordre, sans doublon, chacune avec au moins une entree '- '.

Les messages sont volontairement sans accents : ce script s'affiche dans une
console PowerShell (docs/PREREQUIS.md, section « Encodage de la console »).

Usage : python scripts/changelog.py [--version X.Y.Z | --exige-entree BASE..HEAD]
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
FICHIER = "CHANGELOG.md"

# Rubriques admises, dans l'ordre impose (docs/CONTRIBUTING.md section 4.2).
RUBRIQUES = (
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
NON_PUBLIE = "Non publié"

VERSION_RE = re.compile(r"^## \[(?P<nom>[^\]]+)\](?: - (?P<date>\S+))?\s*$")
NUMERO_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Chemins dont la modification exige une entree du journal.
SURVEILLES = ("skills/", "agents/", "hooks/", "statuslines/", "scripts/install.py")


def sections(texte: str) -> list[dict]:
    """Sections '## [...]' : nom, date, ligne du titre, lignes du corps."""
    out: list[dict] = []
    for n, ligne in enumerate(texte.splitlines(), 1):
        if ligne.startswith("## "):
            m = VERSION_RE.match(ligne)
            out.append({
                "nom": m["nom"] if m else ligne[3:].strip(),
                "date": m["date"] if m else None,
                "ligne": n,
                "valide": bool(m),
                "corps": [],
            })
        elif out and not re.match(r"^\[[^\]]+\]:\s", ligne):
            out[-1]["corps"].append((n, ligne))
    return out


def ecarts_structure(texte: str) -> list[str]:
    out: list[str] = []
    secs = sections(texte)
    if not secs:
        return [f"{FICHIER} : aucune section '## [...]'"]
    if secs[0]["nom"] != NON_PUBLIE or secs[0]["date"]:
        out.append(f"{FICHIER}:{secs[0]['ligne']} : la premiere section doit etre '## [{NON_PUBLIE}]', sans date")
    precedente = None
    for s in secs:
        lieu = f"{FICHIER}:{s['ligne']}"
        if not s["valide"]:
            out.append(f"{lieu} : titre de section non conforme, attendu '## [X.Y.Z] - AAAA-MM-JJ'")
            continue
        if s is not secs[0]:
            if not NUMERO_RE.match(s["nom"]):
                out.append(f"{lieu} : version '{s['nom']}' non conforme, attendu X.Y.Z")
                continue
            try:
                date = datetime.date.fromisoformat(s["date"] or "")
            except ValueError:
                out.append(f"{lieu} : date absente ou invalide, attendu AAAA-MM-JJ")
                continue
            cle = (tuple(int(x) for x in s["nom"].split(".")), date)
            if precedente and not (cle[0] < precedente[0] and cle[1] <= precedente[1]):
                out.append(f"{lieu} : version ou date non decroissante")
            precedente = cle
        out += ecarts_rubriques(s)
    return out


def ecarts_rubriques(s: dict) -> list[str]:
    out: list[str] = []
    rang = -1
    vues: list[tuple[int, str, int]] = []  # (ligne, rubrique, nombre d'entrees)
    for n, ligne in s["corps"]:
        if ligne.startswith("### "):
            titre = ligne[4:].strip()
            if titre not in RUBRIQUES:
                out.append(f"{FICHIER}:{n} : rubrique non prevue '{titre}'")
                continue
            if RUBRIQUES.index(titre) <= rang:
                out.append(f"{FICHIER}:{n} : rubrique '{titre}' en double ou hors de l'ordre prevu")
            rang = max(rang, RUBRIQUES.index(titre))
            vues.append((n, titre, 0))
        elif ligne.startswith("- ") and vues:
            n0, titre, k = vues[-1]
            vues[-1] = (n0, titre, k + 1)
        elif ligne.startswith("- "):
            out.append(f"{FICHIER}:{n} : entree hors rubrique")
    out += [f"{FICHIER}:{n} : rubrique '{t}' sans entree" for n, t, k in vues if k == 0]
    return out


def section(texte: str, version: str) -> str | None:
    """Corps de la section d'une version, sans lignes vides de bord."""
    for s in sections(texte):
        if s["nom"] == version:
            return "\n".join(l for _, l in s["corps"]).strip()
    return None


def fichiers_modifies(plage: str) -> list[str]:
    base, _, head = plage.partition("..")
    return subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()


def main() -> int:
    p = argparse.ArgumentParser(prog="changelog.py")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--version", metavar="X.Y.Z", help="afficher la section de cette version")
    mode.add_argument("--exige-entree", metavar="BASE..HEAD", help="plage d'une pull request")
    try:
        args = p.parse_args()
    except SystemExit as exc:  # argparse sort en 2 ; le code 2 est reserve a l'environnement
        return 1 if exc.code else 0

    if args.exige_entree:
        try:
            modifies = fichiers_modifies(args.exige_entree)
        except FileNotFoundError:
            print("changelog.py : git introuvable dans le PATH", file=sys.stderr)
            return 2
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.strip().splitlines()[0] if exc.stderr.strip() else exc
            print(f"changelog.py : plage illisible '{args.exige_entree}' ({detail})", file=sys.stderr)
            return 1
        outils = [f for f in modifies if f.startswith(SURVEILLES)]
        if outils and FICHIER not in modifies:
            print(
                f"changelog.py : {len(outils)} fichier(s) d'outil modifie(s) sans entree dans "
                f"{FICHIER} (docs/CONTRIBUTING.md section 4.2) : {', '.join(outils[:5])}",
                file=sys.stderr,
            )
            return 1
        return 0

    chemin = ROOT / FICHIER
    if not chemin.is_file():
        print(f"changelog.py : {FICHIER} manquant", file=sys.stderr)
        return 1
    texte = chemin.read_text(encoding="utf-8")

    if args.version:
        corps = section(texte, args.version)
        if not corps:
            print(f"changelog.py : section '{args.version}' absente ou vide dans {FICHIER}", file=sys.stderr)
            return 1
        # Emojis et accents : l'encodage par defaut d'une console PowerShell les corromprait.
        sys.stdout.reconfigure(encoding="utf-8")
        print(corps)
        return 0

    erreurs = ecarts_structure(texte)
    for e in erreurs:
        print(f"changelog.py : {e}", file=sys.stderr)
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
