# AGENTS.md — ia-tools

Dépôt public d'outils pour agents de code (skills, agents, hooks, status
lines), installés dans le dossier racine de chaque agent hôte, noté
`{AGENT_DIR}` : `~/.claude/` pour Claude Code, `~/.copilot/` pour Copilot CLI.
Ce fichier est la **seule source d'instructions qui fasse autorité** dans le
dépôt ; [CLAUDE.md](./CLAUDE.md) et
[.github/copilot-instructions.md](./.github/copilot-instructions.md) ne font
qu'y renvoyer.

## Lecture préalable obligatoire

Avant toute action dans ce dépôt, lire la table de routage
[`docs/DOC_MAP.md`](./docs/DOC_MAP.md). Toute action s'entend au sens large :
planifier, créer ou modifier un fichier, relire un document ou du code,
répondre à une question, committer, lancer une commande, installer des outils.
Quand une tâche est déléguée à un sous-agent, lui transmettre cette consigne.
La table rattache chaque tâche au document qui la régit et indique la conduite
à tenir quand aucun ne s'applique ; elle fait partie de ces instructions. Seule
exception à cette lecture préalable : l'installation ou la mise à jour des
outils locaux, entièrement régie par la section suivante.

## ARRÊT — installation ou mise à jour des outils locaux

**S'arrêter avant toute action** quand l'utilisateur demande d'installer, de
mettre à jour, de déployer ou de synchroniser des outils. Le merge intelligent
est réalisé par `scripts/install.py`, que l'agent conduit en trois temps :

1. lancer son audit, `python scripts/install.py`, et montrer son résumé tel
   quel ;
2. recueillir les choix de l'utilisateur : `--all` pour les cas sûrs, ou les
   identifiants qu'il retient, et un choix `depot` ou `local` par conflit ;
3. lancer la commande `apply` qu'indique le résumé, avec ces choix.

La procédure complète figure dans [SETUP.md](./docs/SETUP.md) §2, à consulter
seulement si la sortie du script ne suffit pas. Ne rien copier à la main, ne
jamais écrire de script temporaire de comparaison et ne pas lire le contenu des
fichiers comparés.

## Definition of Done — boucle de vérification

Une modification n'est terminée que lorsque toutes les conditions propres à son
type de fichier, énumérées ci-dessous, sont remplies. Chaque contrôle —
validateur, test, `zizmor`, intégration continue — se mène en boucle : le
lancer, lire le résultat obtenu, corriger les défauts relevés, puis le relancer
jusqu'à ce qu'il soit au vert.

Tant qu'une condition n'est pas remplie, ne pas passer à une autre tâche, ne
pas proposer de commit, ne pas annoncer la modification comme faite. Ne jamais
contourner l'échec d'un contrôle en supprimant ou en affaiblissant ce contrôle.

- **Document Markdown** — chaque lien relatif ajouté ou modifié mène à une
  cible existante ; le registre ([CONVENTIONS.md](./docs/CONVENTIONS.md) §1.9)
  et le vocabulaire ([VOCABULARY.md](./docs/VOCABULARY.md)) sont respectés ; le
  document a été relu par l'agent `relecture-fr` et les écarts signalés ont été
  corrigés. Pour un nouveau fichier sous `docs/`, la checklist
  [CONVENTIONS.md](./docs/CONVENTIONS.md) §6 est en outre déroulée.
- **Skill, agent, hook, status line** — `python scripts/validate.py` est au
  vert et la checklist [CONVENTIONS.md](./docs/CONVENTIONS.md) §5 est
  entièrement cochée ; pour une status line, `python tests/test_statusline.py`
  est également au vert.
- **Script** (`scripts/*.py`, `tests/*.py`, `skills/**/*.py`,
  `hooks/**/*.ps1`, `statuslines/**/*.ps1`) — le script a été lancé en
  situation réelle d'utilisation et sa sortie a été lue ; tout contrôle ajouté
  ou modifié a d'abord été observé en échec sur un cas construit pour échouer.
  Le test `tests/test_<script>.py`, s'il existe, est au vert ; pour
  `validate.py`, `check_commit_msg.py` et `changelog.py`, ce cas est inscrit
  dans le test.
- **Workflow** (`.github/workflows/*.yml`) — `zizmor --offline
  .github/workflows` est au vert, et l'intégration continue a été observée au
  vert sur la *pull request*.

[CONTRIBUTING.md](./docs/CONTRIBUTING.md) §3 précise ce que contrôlent le
validateur, les hooks git et l'intégration continue, et ce qu'aucun mécanisme
ne contrôle.

## Git

Avant de committer ou d'ouvrir une PR, lire
[CONTRIBUTING.md](./docs/CONTRIBUTING.md), qui traite notamment de la branche
protégée, des hooks git à activer, de l'absence d'attribution d'IA et de la
validation de l'outil par l'utilisateur avant tout commit et tout push. Si la
skill `pull-request` est installée, c'est elle qui mène la livraison.

## Registre

Toute documentation et toute skill de ce dépôt sont rédigées en français, dans
un registre formel et factuel, y compris dans un nouveau fichier et quelle que
soit la langue de la demande ([CONVENTIONS.md](./docs/CONVENTIONS.md) §1.9).
