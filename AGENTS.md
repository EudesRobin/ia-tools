# AGENTS.md — ia-tools

Dépôt public d'outils pour agents de code (skills, agents, hooks), destinés à
être **installés / mis à jour** dans l'environnement local de chaque agent
hôte : `~/.claude/` pour Claude Code, `~/.copilot/` pour Copilot CLI. La
documentation désigne cette racine par le placeholder `{AGENT_DIR}`.

Ce fichier est la **seule source d'instructions faisant autorité** dans le
dépôt.
[CLAUDE.md](./CLAUDE.md) et
[.github/copilot-instructions.md](./.github/copilot-instructions.md) ne font
qu'y renvoyer.

## Lecture préalable obligatoire

Lire ce fichier, puis la table de routage
[`docs/DOC_MAP.md`](./docs/DOC_MAP.md), **avant** :

- de planifier une tâche ;
- de créer, modifier, renommer ou supprimer un fichier ;
- de répondre à une question sur le dépôt ou sur ses outils ;
- de relire du code ou un document ;
- de committer ou de rédiger une description de *pull request* ;
- de lancer un script ou une commande ;
- d'installer ou de mettre à jour des outils ;
- de déléguer une tâche à un sous-agent, à qui cette consigne est transmise.

Cette liste n'est pas limitative : toute action menée dans ce dépôt est précédée
de cette lecture.

La table de routage rattache chaque tâche au document qui la régit — y compris
l'écriture d'outils, qui **doit** suivre
[`docs/CONVENTIONS.md`](./docs/CONVENTIONS.md) — et indique la conduite à tenir
quand aucune règle ne s'applique. Elle fait partie de ces instructions ; ce
n'est pas du contexte facultatif.

## ARRÊT — installation ou mise à jour des outils locaux

**S'arrêter avant toute action** quand l'utilisateur demande d'**installer** ou
de **mettre à jour** des outils — « installe / mets à jour les skills / agents /
hooks / outils », « déploie cette skill en local », « synchronise mes outils ».
Suivre alors [SETUP.md](./docs/SETUP.md), section par section.

Le merge intelligent est porté par **`scripts/install.py`** : le lancer. Ne rien
copier à la main, ne jamais refaire la comparaison ni écrire un script
temporaire pour cela.

```powershell
python scripts/install.py            # audit : n'écrit rien
python scripts/install.py --apply    # écrit les cas sûrs
```

1. Lancer l'audit, qui n'écrit rien.
2. Annoncer le périmètre et les agents hôtes visés, puis les **faire
   confirmer** avant `--apply`. Une demande qui ne les précise pas (« mets à jour
   mes outils ») prend les valeurs par défaut du script : skills, agents et
   hooks, pour `claude` et `copilot`.
3. Lancer `--apply`, puis dérouler [SETUP.md](./docs/SETUP.md) §2. Skills → §3.
   Agents → §4. Hooks → §5.
4. Le script se termine avec le code `1` tant qu'un conflit subsiste. Un conflit
   s'arbitre avec l'utilisateur (`--diff <chemin>`), jamais unilatéralement.

Points non négociables (le détail est dans docs/SETUP.md ; cette duplication est
délibérée et déclarée dans [CONVENTIONS.md](./docs/CONVENTIONS.md) §1.8) :

- **Le dépôt est la source de vérité.** Un écart du type « le dépôt a évolué »
  se résout sans arbitrage : la version du dépôt est adoptée.
- **N'arbitrer que sur conflit non résoluble** : le fichier local porte une
  édition manuelle non reconstituable depuis le dépôt et les variables. Dans ce
  cas seulement : diff et choix laissé à l'utilisateur.
- **Ne jamais écraser `{AGENT_DIR}/settings.json` en bloc** : pour les hooks, ne
  fusionner que les entrées concernées.

## Definition of Done

Une modification n'est terminée que lorsque la boucle correspondant à son type
de fichier est au vert. Ce sont des **boucles**, pas des étapes finales : lancer
→ observer → corriger → relancer.

### Documents Markdown

Pas terminé tant qu'un lien relatif nouveau ou modifié ne mène nulle part, ou
que la rédaction s'écarte du registre ([CONVENTIONS.md](./docs/CONVENTIONS.md)
§1.9) ou du vocabulaire ([VOCABULARY.md](./docs/VOCABULARY.md)).

Un nouveau fichier sous `docs/` est un **document de fond** : dérouler aussi la
checklist [CONVENTIONS.md](./docs/CONVENTIONS.md) §6.

### Skills, agents, hooks

Pas terminé tant que **`python scripts/validate.py`** n'est pas au vert, et que
la checklist [CONVENTIONS.md](./docs/CONVENTIONS.md) §5 n'est pas complète.

**Rouge → pas fait.** Ne pas passer à autre chose, ne pas proposer de commit, ne
pas dire « c'est fait » : lire les écarts listés, corriger, relancer. Ne pas
contourner un échec — ne pas supprimer ni affaiblir la vérification en cause, ne
pas ignorer l'erreur.

### Scripts

`scripts/*.py`, `hooks/**/*.ps1` : pas terminé tant que le script n'a pas été
**lancé sur une invocation réelle** et sa sortie effective lue. Un contrôle
jamais vu en rouge n'est pas un contrôle : après avoir ajouté ou modifié une
vérification, la voir échouer au moins une fois sur un cas volontairement cassé.

### Ce qui n'est pas vérifié mécaniquement

`validate.py` et le hook `validate-tool` couvrent le front-matter et ses
contraintes de chargement (longueur de `name` et de `description`, jeu de
caractères, absence de balise XML), la taille du corps d'un outil, les liens
relatifs, la cohérence de `docs/`, les chemins locaux en dur et la présence des
renvois de `CLAUDE.md` et de `.github/copilot-instructions.md` vers ce fichier.
Ils vérifient en outre qu'un outil multi-étapes **porte** la règle de suivi des
tâches — en-tête `**Tâches**` et marqueurs `[ ]` `[~]` `[x]` `[-]` — sans rien
pouvoir dire de la façon dont une session s'y tient réellement.

Restent des règles en prose, que rien ne contrôle et qu'il faut donc appliquer
délibérément : le **registre de rédaction**, le **vocabulaire**, l'**absence
d'attribution d'IA**, la **qualité d'écriture d'un outil** (concision, latitude
laissée à l'agent, pertinence de la liste de phases fournie par un outil
multi-étapes), la **cohérence sémantique entre documents** (une affirmation d'un
document contredite par un autre échappe au validateur), et le **DoD des
scripts** ci-dessus — rien ne vérifie qu'un script modifié a été lancé, ni
qu'une vérification ajoutée a été vue en rouge.

## Git

Aucune attribution d'outil d'IA dans les commits ni les descriptions de *pull
request* : voir [CONVENTIONS.md](./docs/CONVENTIONS.md) §1.5, qui fait autorité.

## Registre

Toute documentation ou skill rédigée ici reste en français, formelle et
factuelle, y compris dans un nouveau fichier et quelle que soit la langue de la
demande. Les règles complètes — niveau de langue, termes retenus, exigences
plutôt qu'anecdotes, résultat plutôt que démarche — figurent dans
[CONVENTIONS.md](./docs/CONVENTIONS.md) §1.9 et
[VOCABULARY.md](./docs/VOCABULARY.md).
