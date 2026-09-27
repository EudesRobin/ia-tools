# Hook — `validate-tool`

Lance `scripts/validate.py` à la fin de chaque tour de l'agent dans ce dépôt,
sous Claude Code comme sous Copilot CLI. Tant que le validateur est au rouge, le
hook empêche l'agent de rendre la main et lui renvoie les écarts à corriger.

C'est ce qui fait passer le validateur du statut de contrôle que l'on peut
oublier à celui de contrôle qui s'impose.

## Ce qu'il fait

- Se déclenche sur l'événement **`Stop`**, au moment où l'agent s'apprête à
  rendre la main.
- Lance `python scripts/validate.py` depuis la racine du projet, lue dans le
  champ `cwd` du payload, à défaut dans `CLAUDE_PROJECT_DIR`, à défaut
  le répertoire courant.
- **Vert** → code de sortie 0, sans affichage. Le tour se termine normalement.
- **Rouge** → il écrit sur la sortie standard l'objet JSON
  `{"decision": "block", "reason": "…"}`, qui porte les écarts, et se termine
  avec le code 0. Les deux agents hôtes reconnaissent cette forme : l'agent
  reçoit les écarts et reprend la main pour les corriger.

### Ce qu'il ne fait délibérément pas

- **Il ne s'exécute pas hors de ce dépôt.** Si `scripts/validate.py` est absent
  de la racine du projet, il se termine avec le code 0 sans rien afficher. C'est
  ce qui le rend inoffensif si son enregistrement venait à se retrouver dans une
  configuration globale.
- **Il ne boucle pas.** Quand le payload reçu indique qu'il a déjà bloqué
  la fin du tour en cours (`stop_hook_active`), il se termine avec le code 0 et
  laisse l'agent aller au bout de sa correction. Copilot CLI limite en outre à
  huit le nombre de blocages consécutifs.
- **Il ne bloque pas sur une anomalie d'environnement.** Si `python` est
  introuvable dans le PATH, il le signale et se termine avec un code non
  bloquant : c'est un problème de poste, pas un défaut du travail produit.
- **Il n'emploie pas le code 2.** Bloquant pour Claude Code, ce code n'est
  qu'un avertissement pour Copilot CLI.

## Installation

**Ce hook est local au dépôt et n'est pas distribué vers `{AGENT_DIR}`.** Il est
déjà enregistré dans deux fichiers versionnés, un par agent hôte :

| Agent hôte | Enregistrement |
|---|---|
| Claude Code | `.claude/settings.json`, événement `Stop` |
| Copilot CLI | `.github/hooks/validate-tool.json`, événement `Stop` |

Rien à installer : il s'active à l'ouverture d'une session dans ce répertoire.

Ce choix est délibéré. Un enregistrement dans la configuration globale d'un
agent hôte déclencherait ce hook dans **tous** les projets et y exécuterait le
`scripts/validate.py` de n'importe quel dépôt ouvert. L'enregistrement local
évite cela et laisse `{AGENT_DIR}/settings.json` intact, conformément au point
non négociable d'[AGENTS.md](../../AGENTS.md) relatif à ce fichier.

La procédure générale d'installation des outils est décrite dans
[SETUP.md](../../docs/SETUP.md) ; elle ne s'applique pas à ce hook.

## Configuration

Aucun paramètre. Le hook déduit la racine du projet du payload, avec
repli sur `CLAUDE_PROJECT_DIR`, fourni par Claude Code, puis sur le répertoire
courant.

## Limites

- **PowerShell 7 requis** (`pwsh`). Le script le déclare en tête ; sous
  PowerShell 5 il refusera de s'exécuter.
- **Il ne couvre que ce que `validate.py` sait contrôler** — front-matter, liens
  relatifs, cohérence de `docs/`, chemins locaux en dur, renvois des fichiers
  d'entrée vers `AGENTS.md`, et présence de la règle de suivi des tâches dans un
  outil multi-étapes. Le registre de rédaction et l'absence d'attribution d'IA
  restent des règles en prose, non vérifiables mécaniquement.
- **Le suivi des tâches n'est contrôlé que sur le texte de l'outil.** Le
  validateur vérifie qu'un outil *porte* la règle — en-tête et marqueurs —
  jamais qu'une session s'y tient. Il repère les outils par leur déroulé
  numéroté ou par la mention du suivi dans leur corps : un outil multi-étapes
  qui ne présente ni l'un ni l'autre lui échappe.
- Les messages sont écrits **sans accents** : ils transitent par la console,
  dont l'encodage par défaut sous Windows les corromprait.
