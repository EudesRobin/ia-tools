# AGENTS.md — ia-tools

Dépôt public d'outils pour agents de code (skills, agents, hooks, status
lines), installés dans la racine de chaque agent hôte, notée `{AGENT_DIR}` :
`~/.claude/` pour Claude Code, `~/.copilot/` pour Copilot CLI. Ce fichier est
la **seule source d'instructions faisant autorité** dans le dépôt ;
[CLAUDE.md](./CLAUDE.md) et
[.github/copilot-instructions.md](./.github/copilot-instructions.md) ne font
qu'y renvoyer.

## Lecture préalable obligatoire

Avant toute action dans ce dépôt — planifier, créer ou modifier un fichier,
relire un document ou du code, répondre à une question, committer, lancer une
commande, installer des outils, déléguer une tâche à un sous-agent, à qui cette
consigne est transmise —, lire la table de routage
[`docs/DOC_MAP.md`](./docs/DOC_MAP.md). Elle rattache chaque tâche au document
qui la régit et indique la conduite à tenir quand aucun ne s'applique ; elle
fait partie de ces instructions.

## ARRÊT — installation ou mise à jour des outils locaux

**S'arrêter avant toute action** quand l'utilisateur demande d'installer, de
mettre à jour, de déployer ou de synchroniser des outils, et suivre
[SETUP.md](./docs/SETUP.md) section par section. Le merge intelligent est porté
par `scripts/install.py` : lancer l'audit, faire confirmer le périmètre et les
agents hôtes avant `--apply`, arbitrer chaque conflit avec l'utilisateur. Ne
rien copier à la main, ne jamais écrire de script temporaire de comparaison.

## Definition of Done

Une modification n'est terminée que lorsque la boucle de son type de fichier est
au vert : lancer → observer → corriger → relancer. **Rouge → pas fait** : ne pas
passer à autre chose, ne pas proposer de commit, ne pas dire « c'est fait » ;
ne pas contourner un échec en supprimant ou en affaiblissant la vérification en
cause.

- **Document Markdown** — aucun lien relatif nouveau ou modifié ne mène nulle
  part ; registre ([CONVENTIONS.md](./docs/CONVENTIONS.md) §1.9) et vocabulaire
  ([VOCABULARY.md](./docs/VOCABULARY.md)) respectés ; document relu par l'agent
  `relecture-fr`, écarts appliqués. Pour un nouveau fichier sous `docs/`, la
  checklist [CONVENTIONS.md](./docs/CONVENTIONS.md) §6 est en outre déroulée.
- **Skill, agent, hook, status line** — `python scripts/validate.py` au vert et
  checklist [CONVENTIONS.md](./docs/CONVENTIONS.md) §5 complète ; pour une
  status line, `python tests/test_statusline.py` au vert.
- **Script** (`scripts/*.py`, `tests/*.py`, `skills/**/*.py`,
  `hooks/**/*.ps1`, `statuslines/**/*.ps1`) — lancé sur une invocation réelle,
  sortie effective lue ; toute vérification ajoutée ou modifiée vue en rouge
  sur un cas volontairement cassé. Le test
  `tests/test_<script>.py`, quand il existe, est au vert ; pour
  `validate.py` et `check_commit_msg.py`, le cas cassé y est inscrit.
- **Workflow** (`.github/workflows/*.yml`) — `zizmor --offline
  .github/workflows` au vert, et exécution de l'intégration continue observée
  au vert sur la *pull request*.

Ce que contrôlent le validateur, les hooks git et l'intégration continue, et ce
qu'aucun mécanisme ne contrôle : [CONTRIBUTING.md](./docs/CONTRIBUTING.md) §3.

## Git

Avant de committer ou d'ouvrir une *pull request*, lire
[CONTRIBUTING.md](./docs/CONTRIBUTING.md) : branche protégée, hooks git à
activer, absence d'attribution d'IA, outil validé par l'utilisateur avant tout
commit et tout push. La skill `pull-request`, si elle est installée, mène la
livraison.

## Registre

Toute documentation ou skill rédigée dans ce dépôt reste en français, formelle
et factuelle, y compris dans un nouveau fichier et quelle que soit la langue de
la demande ([CONVENTIONS.md](./docs/CONVENTIONS.md) §1.9).
