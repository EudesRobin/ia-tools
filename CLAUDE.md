# CLAUDE.md — ia-tools

Dépôt public d'outils Claude (skills, agents, hooks), destinés à être
**installés / mis à jour** sur un environnement local (`~/.claude/`).

> **Avant d'agir, consulter [`docs/DOC_MAP.md`](./docs/DOC_MAP.md).** Elle
> rattache chaque tâche au document qui la régit — y compris l'écriture d'outils,
> qui **doit** suivre [`docs/CONVENTIONS.md`](./docs/CONVENTIONS.md) — et définit
> quoi faire quand aucune règle ne s'applique. Elle fait partie de ces
> instructions, ce n'est pas du contexte facultatif.

## Installation / mise à jour des outils

Quand l'utilisateur demande d'**installer** ou de **mettre à jour** des outils
Claude — « installe / mets à jour les skills / agents / hooks / outils »,
« déploie cette skill en local », « synchronise mes outils » — suivre
[SETUP.md](./docs/SETUP.md), section par section.

Le merge intelligent est porté par **`scripts/install.py`** : le lancer, ne
jamais refaire la comparaison ni écrire un script temporaire pour cela.

```powershell
python scripts/install.py            # audit : n'écrit rien
python scripts/install.py --apply    # écrit les cas sûrs
```

- Demande qui ne précise pas le périmètre (« mets à jour mes outils ») →
  périmètre par défaut du script : skills, agents et hooks. **Annoncer ce
  périmètre et le faire confirmer** avant `--apply`, puis dérouler
  [SETUP.md](./docs/SETUP.md) §2.
- Skills → §3. Agents → §4. Hooks → §5.
- Le script se termine avec le code `1` tant qu'un conflit subsiste. Un conflit
  s'arbitre avec l'utilisateur (`--diff <chemin>`), jamais unilatéralement.

Points non négociables (le détail est dans docs/SETUP.md ; cette duplication est
délibérée et déclarée dans [CONVENTIONS.md](./docs/CONVENTIONS.md) §1.8) :

- **Le dépôt est la source de vérité.** Un écart du type « le dépôt a évolué »
  se résout sans arbitrage : la version du dépôt est adoptée.
- **N'arbitrer que sur conflit non résoluble** : le fichier local porte une
  édition manuelle non reconstituable depuis le dépôt et les variables. Dans ce
  cas seulement : diff et choix laissé à l'utilisateur.
- **Ne jamais toucher `~/.claude/settings.json` en bloc** : pour les hooks, ne
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
relatifs, la cohérence de `docs/` et les chemins locaux en dur. Ils vérifient en
outre qu'un outil multi-étapes **porte** la règle de suivi des tâches — en-tête
`**Tâches**` et marqueurs `[ ]` `[~]` `[x]` `[-]` — sans rien pouvoir dire de la
façon dont une session s'y tient réellement.

Restent des règles en prose, que rien ne contrôle et qu'il faut donc appliquer
délibérément : le **registre de rédaction**, le **vocabulaire**, l'**absence
d'attribution d'IA**, la **qualité d'écriture d'un outil** (concision, latitude
laissée à l'agent, pertinence de la liste de phases fournie par un outil
multi-étapes), la **cohérence sémantique entre documents** (une affirmation d'un
document contredite par un autre échappe au validateur), et le **DoD des
scripts** ci-dessus — rien ne vérifie qu'un script modifié a été lancé, ni
qu'une vérification ajoutée a été vue en rouge.

## Git

Aucune attribution d'outil d'IA dans les commits ni les descriptions de PR :
voir [CONVENTIONS.md](./docs/CONVENTIONS.md) §1.5, qui fait autorité.

## Registre

Toute documentation ou skill rédigée ici reste formelle et factuelle. Les règles
complètes — niveau de langue, termes retenus, exigences plutôt qu'anecdotes,
résultat plutôt que démarche — figurent dans
[CONVENTIONS.md](./docs/CONVENTIONS.md) §1.9 et
[VOCABULARY.md](./docs/VOCABULARY.md).
