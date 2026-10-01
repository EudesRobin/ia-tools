# Table de routage de la documentation

L'autorité de routage de ce dépôt : chaque tâche est rattachée au document
unique qui la régit, et cette table indique la conduite à tenir quand aucune
ligne ne couvre la tâche. [AGENTS.md](../AGENTS.md), atteint par chaque agent
hôte — directement ou par son fichier de renvoi —, en impose la lecture : cette
table fait partie de la chaîne d'instructions ; ce n'est pas du contexte
facultatif.

Certaines lignes pointent vers une **règle impérative**, à suivre
obligatoirement ; les autres pointent vers des documents de fond qui expliquent
*pourquoi* les règles sont ce qu'elles sont. La documentation propre à une
skill ou à un agent donné se trouve à côté de l'outil qu'elle décrit, pas ici
(voir [CONVENTIONS.md](CONVENTIONS.md) §6).

## Où chercher

| Avant de…                                                                         | Lire |
|-----------------------------------------------------------------------------------|------|
| Ajouter ou modifier un outil — skill, agent, hook, status line, script embarqué   | [CONVENTIONS.md](CONVENTIONS.md) — **à suivre obligatoirement** |
| Juger si un outil est *bien écrit* — concision, découpage, latitude laissée à l'agent, suivi de progression, évaluation | [qualite-outils.md](qualite-outils.md) |
| Rédiger ou reprendre un document, et hésiter sur un terme                         | [VOCABULARY.md](VOCABULARY.md) — **à suivre obligatoirement** |
| Rédiger un document, quel qu'il soit — niveau de langue, forme des énoncés        | [CONVENTIONS.md](CONVENTIONS.md) §1.9 — **à suivre obligatoirement** |
| Ajouter ou reprendre un document de fond sous `docs/`                             | [CONVENTIONS.md](CONVENTIONS.md) §6 — **checklist à dérouler** |
| Ajouter ou modifier un script d'outillage du dépôt sous `scripts/`                | [CONVENTIONS.md](CONVENTIONS.md) §7 — **à suivre obligatoirement** |
| Comprendre le hook du dépôt, son enregistrement pour chaque agent hôte et pourquoi il n'est pas distribué | [hooks/README.md](../hooks/README.md) |
| Installer ou mettre à jour les outils vers `{AGENT_DIR}` (Claude Code, Copilot CLI) | [SETUP.md](SETUP.md) — **procédure à suivre** |
| Publier une version du dépôt — choisir son numéro, poser son tag                  | [CONVENTIONS.md](CONVENTIONS.md) §8 — **procédure à suivre** |
| Vérifier ou installer un prérequis système (Python, Git, bibliothèques, `adb`, `pwsh`) | [PREREQUIS.md](PREREQUIS.md) |

Sept lignes portent une règle à appliquer, pas du contexte. La ligne consacrée
à l'écriture d'un outil est la plus dense : [CONVENTIONS.md](CONVENTIONS.md)
fixe l'arborescence et le nommage, la structure de `SKILL.md`, de `HOOK.md`, de
`STATUSLINE.md` et des fichiers d'agent, le front-matter, le moindre privilège
sur l'accès aux outils, le traitement des secrets et des chemins locaux, ainsi
que les checklists d'enregistrement. Il prévaut sur tout template par défaut
avec lequel il entrerait en contradiction.

[qualite-outils.md](qualite-outils.md) se place en dessous : il traite de la
**qualité** d'un outil — concision, découpage, latitude laissée à l'agent, suivi
de progression — là où `CONVENTIONS.md` traite de sa **structure**. À lire quand
la question est « cet outil est-il bien écrit ? » et non « où va ce fichier ? ».
`CONVENTIONS.md` l'emporte sur tout point où les deux divergent ; ces
divergences sont recensées au §10 de `qualite-outils.md`.

L'inventaire de ce que fait chaque outil figure dans [README.md](../README.md),
qui s'adresse à un lecteur humain et ne fait pas partie de la chaîne
d'instructions.

## Quand aucune ligne ne couvre la tâche

Si une tâche n'est couverte ni par une ligne ci-dessus, ni par une règle de
[AGENTS.md](../AGENTS.md), ne pas deviner en silence. Signaler le manque à
l'utilisateur et proposer où loger la règle absente — une nouvelle ligne dans
cette table, une nouvelle règle dans `AGENTS.md`, ou un nouveau document de fond
selon [CONVENTIONS.md](CONVENTIONS.md) §6 — avant de poursuivre.
