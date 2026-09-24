#!/usr/bin/env python3
"""Validateur des sources d'ia-tools. Outillage du depot, jamais installe vers
~/.claude/.

Verifie, avant une installation (docs/SETUP.md) ou un commit :
  - chaque skills/<nom>/SKILL.md a un front-matter YAML valide avec name +
    description, et name == nom du dossier ;
  - chaque agents/<nom>.md a un front-matter YAML valide avec name +
    description, et name == nom du fichier ;
  - les contraintes de chargement du front-matter : name d'au plus 64 caracteres
    en minuscules/chiffres/traits d'union, description d'au plus 1024
    caracteres, aucune balise XML dans l'un ni l'autre ;
  - le corps de chaque SKILL.md et de chaque fichier d'agent compte moins de
    500 lignes ;
  - tout lien Markdown relatif mene a un fichier existant, et vers une
    ancre de section existante quand le lien en porte une ;
  - tout document de docs/ (recursif) est enregistre dans docs/DOC_MAP.md
    et porte son lien de retour ; toute entree de la table pointe vers un
    fichier existant ;
  - tout fichier Markdown suivi par git est reference par au moins un lien
    relatif depuis un autre fichier Markdown du depot (hors points d'entree et
    fichiers embarques exemptes) ;
  - aucun fichier suivi par git ne contient de chemin local en dur
    (C:\\Users\\<user reel>, /home/<user>) — seuls les placeholders <...> sont
    admis.

Les messages sont volontairement sans accents : ce script s'affiche dans une
console PowerShell, dont l'encodage par defaut corrompt les caracteres accentues
(voir docs/PREREQUIS.md, section « Encodage de la console »).

Usage : python scripts/validate.py
Code de sortie : 0 si tout passe, 1 sinon.
"""

import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print(
        "validate.py : le module 'pyyaml' est requis et absent.\n"
        "  Installer les dependances Python listees dans docs/PREREQUIS.md :\n"
        "    pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?\n)---\s*\n", re.DOTALL)

# Contraintes de chargement du front-matter (docs/qualite-outils.md, section 1).
# Un outil qui les enfreint est ignore silencieusement, sans message d'erreur.
NAME_MAX_LEN = 64
DESCRIPTION_MAX_LEN = 1024
NAME_RE = re.compile(r"[a-z0-9-]+")

# Corps de moins de 500 lignes (docs/qualite-outils.md, section 3) : au-dela, le
# detail se repartit dans des fichiers embarques plutot que de gonfler le document canonique.
BODY_MAX_LINES = 500

# Balise XML : volontairement etroit — le nom d'element doit commencer par une
# minuscule. Un placeholder <NOM_VARIABLE> (CONVENTIONS.md 1.2) est en
# majuscules et ne doit pas etre signale ici.
XML_TAG_RE = re.compile(r"</?[a-z][a-z0-9]*(\s[^>]*)?/?>")

# Liens Markdown [texte](cible). Les images, prefixees par '!', sont ignorees.
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# Protocoles et formes de cibles qui ne designent pas un fichier du depot.
EXTERNAL_LINK_RE = re.compile(r"^(https?:|mailto:|tel:|#|<)", re.IGNORECASE)

# Chemins locaux en dur a bannir (hors placeholders <...>).
LOCAL_PATH_PATTERNS = [
    re.compile(r"C:\\Users\\(?!<)[^\\\s]+"),
    re.compile(r"/home/(?!<)[^/\s]+"),
]

# Fichiers exemptes du controle "chemin en dur" (ils documentent le motif lui-meme).
# Chemins relatifs a la racine, pas des noms de base.
PATH_SCAN_EXCLUDE = {"scripts/validate.py"}

# Titre Markdown : "#{1,6} texte".
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)

# Fichiers Markdown exemptes du controle "aucun document orphelin" :
# points d'entree lus automatiquement (jamais navigues depuis un autre .md),
# et fichiers embarques references en prose plutot que par lien Markdown.
ORPHAN_SCAN_EXCLUDE = {
    "README.md",
    "CLAUDE.md",
}

# Suivi des taches (docs/qualite-outils.md, section 5). Le seuil est celui du
# declencheur de la regle elle-meme : trois etapes distinctes ou plus. En deca,
# le formalisme couterait plus qu'il ne rapporte et la regle ne s'applique pas.
PROGRESS_MIN_STEPS = 3

# Etape numerotee de premier niveau : "1. texte". Jusqu'a trois espaces
# d'indentation, tolerance Markdown avant qu'une ligne ne devienne un bloc de
# code. Les lignes du bloc de taches commencent par "- [", donc jamais captees.
NUMBERED_STEP_RE = re.compile(r"^ {0,3}\d+\.\s+\S", re.MULTILINE)

# En-tete affiche du bloc de suivi. Le point remplace l'accent : la comparaison se
# fait sur une forme normalisee, comme pour BACKLINK_RE.
PROGRESS_HEADING_RE = re.compile(r"\*\*T.ches\*\*")

# Les quatre marqueurs d'etat, exhaustifs et non negociables. Un outil qui porte
# la regle les nomme tous, y compris [-] qui n'apparait pas dans une liste
# initiale mais doit etre connu de l'agent qui abandonne une etape.
PROGRESS_MARKERS = ("[ ]", "[~]", "[x]", "[-]")

# Un outil qui evoque le suivi doit le porter en entier, meme si son deroule
# n'est pas numerote : c'est ce qui attrape une regle enoncee a moitie.
PROGRESS_MENTION_RE = re.compile(
    r"suivi de progression|suivi des t.ches|liste de t.ches", re.IGNORECASE
)

# Outils dont l'omission du suivi est deliberee et assumee. Vide aujourd'hui.
PROGRESS_SCAN_EXCLUDE: set[str] = set()

DOCS_DIR = "docs"
DOC_MAP = "DOC_MAP.md"
BACKLINK_MARKER = "Enregistre dans la table de routage"
# Le marqueur reel porte des accents ; on compare sur une forme normalisee.
BACKLINK_RE = re.compile(
    r"Enregistr.\s+dans\s+la\s+table\s+de\s+routage", re.IGNORECASE
)


def tracked_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return [ROOT / p for p in out.stdout.splitlines() if p.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, IsADirectoryError, FileNotFoundError):
        return None


def parse_frontmatter(text: str) -> tuple[dict | None, str | None]:
    """Retourne (champs, erreur). Le YAML est lu en mode strict."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, "front-matter absent"
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        detail = str(exc).replace("\n", " ")
        return None, f"front-matter YAML invalide ({detail})"
    if data is None:
        return None, "front-matter vide"
    if not isinstance(data, dict):
        return None, "front-matter : un bloc cle/valeur est attendu"
    return data, None


def check_frontmatter_fields(label: str, fm: dict, expected_name: str, errors: list[str]) -> None:
    name = fm.get("name")
    if name is None:
        errors.append(f"{label} : champ 'name' manquant")
    elif not isinstance(name, str) or not name.strip():
        errors.append(f"{label} : champ 'name' vide ou non textuel")
    else:
        if name != expected_name:
            errors.append(f"{label} : name='{name}' != '{expected_name}'")
        if len(name) > NAME_MAX_LEN:
            errors.append(
                f"{label} : name de {len(name)} caracteres, maximum {NAME_MAX_LEN}"
            )
        if not NAME_RE.fullmatch(name):
            errors.append(
                f"{label} : name '{name}' hors du jeu autorise"
                " (minuscules, chiffres, traits d'union)"
            )
        if XML_TAG_RE.search(name):
            errors.append(f"{label} : name contient une balise XML")

    description = fm.get("description")
    if description is None:
        errors.append(f"{label} : champ 'description' manquant")
    elif not isinstance(description, str) or not description.strip():
        errors.append(f"{label} : champ 'description' vide ou non textuel")
    else:
        if len(description) > DESCRIPTION_MAX_LEN:
            errors.append(
                f"{label} : description de {len(description)} caracteres,"
                f" maximum {DESCRIPTION_MAX_LEN}"
            )
        if XML_TAG_RE.search(description):
            errors.append(f"{label} : description contient une balise XML")


def check_skills(errors: list[str]) -> None:
    skills_dir = ROOT / "skills"
    if not skills_dir.is_dir():
        return
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        label = f"skills/{skill_dir.name}/SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{label} manquant")
            continue
        text = read(skill_md)
        if text is None:
            errors.append(f"{label} : illisible en UTF-8")
            continue
        fm, err = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{label} : {err}")
            continue
        check_frontmatter_fields(label, fm, skill_dir.name, errors)


def check_agents(errors: list[str]) -> None:
    agents_dir = ROOT / "agents"
    if not agents_dir.is_dir():
        return
    for agent_md in sorted(agents_dir.glob("*.md")):
        label = f"agents/{agent_md.name}"
        text = read(agent_md)
        if text is None:
            errors.append(f"{label} : illisible en UTF-8")
            continue
        fm, err = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{label} : {err}")
            continue
        check_frontmatter_fields(label, fm, agent_md.stem, errors)


def tool_docs() -> list[tuple[str, Path]]:
    """Les documents canoniques des outils : (libelle, chemin)."""
    docs: list[tuple[str, Path]] = []
    skills_dir = ROOT / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.is_file():
                docs.append((f"skills/{skill_dir.name}/SKILL.md", skill_md))
    agents_dir = ROOT / "agents"
    if agents_dir.is_dir():
        for agent_md in sorted(agents_dir.glob("*.md")):
            docs.append((f"agents/{agent_md.name}", agent_md))
    return docs


def check_body_size(errors: list[str]) -> None:
    for label, path in tool_docs():
        text = read(path)
        if text is None:
            continue
        m = FRONTMATTER_RE.match(text)
        body = text[m.end():] if m else text
        lines = len(body.splitlines())
        if lines > BODY_MAX_LINES:
            errors.append(
                f"{label} : corps de {lines} lignes, maximum {BODY_MAX_LINES}"
            )


def check_progress_tracking(errors: list[str]) -> None:
    """Un outil multi-etapes doit porter la regle de suivi des taches.

    Ne controle que la presence de la regle dans l'outil, pas la facon dont une
    session s'y tient : rien ici ne peut l'observer.
    """
    for label, path in tool_docs():
        if label in PROGRESS_SCAN_EXCLUDE:
            continue
        text = read(path)
        if text is None:
            continue
        m = FRONTMATTER_RE.match(text)
        body = text[m.end():] if m else text

        steps = len(NUMBERED_STEP_RE.findall(body))
        mentions = PROGRESS_MENTION_RE.search(body) is not None
        if steps < PROGRESS_MIN_STEPS and not mentions:
            continue

        raison = (
            f"deroule de {steps} etapes numerotees"
            if steps >= PROGRESS_MIN_STEPS
            else "le corps evoque le suivi des taches"
        )
        if not PROGRESS_HEADING_RE.search(body):
            errors.append(
                f"{label} : {raison}, en-tete '**Taches**' absent du bloc de suivi"
            )
        manquants = [mk for mk in PROGRESS_MARKERS if mk not in body]
        if manquants:
            errors.append(
                f"{label} : {raison}, marqueur(s) d'etat absent(s) "
                f"{' '.join(manquants)} — les quatre sont obligatoires"
            )


def markdown_links(text: str) -> list[str]:
    return LINK_RE.findall(text)


def slugify(heading: str) -> str:
    """Reproduit l'algorithme d'ancres de GitHub : retire la ponctuation,
    remplace chaque espace par un trait d'union sans fusionner les espaces
    consecutifs (un tiret cadratin entoure d'espaces produit un double
    tiret)."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    return s.replace(" ", "-")


def heading_anchors(text: str) -> set[str]:
    slugs: dict[str, int] = {}
    anchors: set[str] = set()
    for _, heading in HEADING_RE.findall(text):
        base = slugify(heading)
        n = slugs.get(base, 0)
        anchors.add(base if n == 0 else f"{base}-{n}")
        slugs[base] = n + 1
    return anchors


def check_relative_links(errors: list[str]) -> None:
    for path in tracked_files():
        if path.suffix.lower() != ".md":
            continue
        text = read(path)
        if text is None:
            continue
        rel = path.relative_to(ROOT).as_posix()
        for target in markdown_links(text):
            if EXTERNAL_LINK_RE.match(target):
                continue
            # Separer une ancre eventuelle : chemin.md#section
            cible, _, anchor = target.partition("#")
            if not cible:
                continue
            resolved = (path.parent / cible).resolve()
            if not resolved.exists():
                errors.append(f"{rel} : lien relatif mort '{target}'")
                continue
            if anchor:
                target_text = read(resolved)
                if target_text is not None and anchor not in heading_anchors(target_text):
                    errors.append(f"{rel} : ancre introuvable '{target}'")


def check_doc_map(errors: list[str]) -> None:
    docs_dir = ROOT / DOCS_DIR
    if not docs_dir.is_dir():
        return

    doc_map = docs_dir / DOC_MAP
    if not doc_map.is_file():
        errors.append(f"{DOCS_DIR}/{DOC_MAP} manquant")
        return

    map_text = read(doc_map)
    if map_text is None:
        errors.append(f"{DOCS_DIR}/{DOC_MAP} : illisible en UTF-8")
        return

    # Documents enregistres : cibles relatives de la table qui pointent dans docs/.
    registered: set[Path] = set()
    for target in markdown_links(map_text):
        if EXTERNAL_LINK_RE.match(target):
            continue
        cible = target.split("#", 1)[0]
        if not cible.endswith(".md"):
            continue
        registered.add((doc_map.parent / cible).resolve())

    for doc in sorted(docs_dir.rglob("*.md")):
        rel = doc.relative_to(ROOT).as_posix()
        if doc.name == DOC_MAP:
            continue
        if doc.resolve() not in registered:
            errors.append(f"{rel} : non enregistre dans {DOCS_DIR}/{DOC_MAP}")
        text = read(doc)
        if text is None:
            errors.append(f"{rel} : illisible en UTF-8")
            continue
        if not BACKLINK_RE.search(text):
            errors.append(
                f"{rel} : lien de retour absent"
                f' (attendu : "{BACKLINK_MARKER} : [{DOC_MAP}]({DOC_MAP}).")'
            )


def check_orphan_docs(errors: list[str]) -> None:
    md_files = [p for p in tracked_files() if p.suffix.lower() == ".md"]

    referenced: set[Path] = set()
    for path in md_files:
        text = read(path)
        if text is None:
            continue
        for target in markdown_links(text):
            if EXTERNAL_LINK_RE.match(target):
                continue
            cible = target.split("#", 1)[0]
            if not cible or not cible.endswith(".md"):
                continue
            referenced.add((path.parent / cible).resolve())

    for path in md_files:
        rel = path.relative_to(ROOT).as_posix()
        if rel in ORPHAN_SCAN_EXCLUDE:
            continue
        if path.resolve() not in referenced:
            errors.append(f"{rel} : aucun autre document Markdown ne le reference")


def check_no_hardcoded_paths(errors: list[str]) -> None:
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if rel in PATH_SCAN_EXCLUDE:
            continue
        text = read(path)
        if text is None:
            continue
        for pattern in LOCAL_PATH_PATTERNS:
            for match in pattern.finditer(text):
                errors.append(f"{rel} : chemin local en dur '{match.group(0)}'")


def main() -> int:
    errors: list[str] = []
    check_skills(errors)
    check_agents(errors)
    check_body_size(errors)
    check_progress_tracking(errors)
    check_relative_links(errors)
    check_doc_map(errors)
    check_orphan_docs(errors)
    check_no_hardcoded_paths(errors)

    if errors:
        print(f"validate.py : {len(errors)} probleme(s)\n")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("validate.py : OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
