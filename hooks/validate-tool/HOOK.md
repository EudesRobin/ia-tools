# Hook — `validate-tool`

Lance `scripts/validate.py` à la fin de chaque tour de Claude dans ce dépôt. Si
le validateur est au rouge, le hook empêche Claude de rendre la main et lui
renvoie les écarts à corriger.

C'est ce qui fait passer le validateur du statut de contrôle que l'on peut
oublier à celui de contrôle qui s'impose.

## Ce qu'il fait

- Se déclenche sur l'événement **`Stop`**, au moment où Claude s'apprête à
  rendre la main.
- Lance `python scripts/validate.py` depuis la racine du projet.
- **Vert** → code de sortie 0, sans affichage. Le tour se termine normalement.
- **Rouge** → il se termine avec un code de sortie bloquant et écrit les écarts
  sur la sortie d'erreur. Claude les reçoit et reprend la main pour corriger.

### Ce qu'il ne fait délibérément pas

- **Il ne s'exécute pas hors de ce dépôt.** Si `scripts/validate.py` est absent
  du répertoire courant, il se termine avec le code 0 sans rien afficher. C'est
  ce qui le rend inoffensif si son enregistrement venait à se retrouver dans une
  configuration globale.
- **Il ne boucle pas.** Quand la charge utile reçue indique qu'il a déjà bloqué
  la fin du tour en cours (`stop_hook_active`), il se termine avec le code 0 et
  laisse Claude aller au bout de sa correction.
- **Il ne bloque pas sur une anomalie d'environnement.** Si `python` est
  introuvable dans le PATH, il le signale et se termine avec un code non
  bloquant : c'est un problème de poste, pas un défaut du travail produit.

## Installation

**Ce hook est local au dépôt et n'est pas distribué vers `~/.claude/`.** Il est
déjà enregistré dans le `.claude/settings.json` versionné du dépôt : rien à
installer, il s'active à l'ouverture d'une session dans ce répertoire.

Ce choix est délibéré. Un enregistrement dans le `~/.claude/settings.json`
global déclencherait ce hook dans **tous** les projets et y exécuterait le
`scripts/validate.py` de n'importe quel dépôt ouvert. L'enregistrement local
évite cela et laisse le `settings.json` global intact, conformément au point non
négociable de [CLAUDE.md](../../CLAUDE.md) relatif à `~/.claude/settings.json`.

La procédure générale d'installation des outils est décrite dans
[SETUP.md](../../docs/SETUP.md) ; elle ne s'applique pas à ce hook.

## Configuration

Aucun paramètre. Le hook déduit la racine du projet de la variable
`CLAUDE_PROJECT_DIR` fournie par Claude Code, avec repli sur le répertoire
courant.

## Limites

- **PowerShell 7 requis** (`pwsh`). Le script le déclare en tête ; sous
  PowerShell 5 il refusera de s'exécuter.
- **Il ne couvre que ce que `validate.py` sait contrôler** — front-matter, liens
  relatifs, cohérence de `docs/`, chemins locaux en dur, et présence de la règle
  de suivi des tâches dans un outil multi-étapes. Le registre de rédaction et
  l'absence d'attribution d'IA restent des règles en prose, non vérifiables
  mécaniquement.
- **Le suivi des tâches n'est contrôlé que sur le texte de l'outil.** Le
  validateur vérifie qu'un outil *porte* la règle — en-tête et marqueurs —
  jamais qu'une session s'y tient. Il repère les outils par leur déroulé
  numéroté ou par la mention du suivi dans leur corps : un outil multi-étapes
  qui ne présente ni l'un ni l'autre lui échappe.
- Les messages sont écrits **sans accents** : ils transitent par la console,
  dont l'encodage par défaut sous Windows les corromprait.
