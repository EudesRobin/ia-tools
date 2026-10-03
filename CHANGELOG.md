# Journal des modifications

Les changements notables de chaque version, du point de vue de qui installe les
outils. Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
avec des rubriques repérées par un emoji et rapprochées des préfixes de commit ;
la numérotation des versions et la liste des rubriques sont décrites dans
[CONTRIBUTING.md](docs/CONTRIBUTING.md#4-publier-une-version).

## [Non publié]

### 📝 Documentation

- `AGENTS.md` ne porte plus que les règles utiles à presque toute session ; la
  contribution — hooks git, commits, *pull requests*, contrôles automatiques,
  publication d'une version — est décrite dans `docs/CONTRIBUTING.md`.

### 🧹 Maintenance

- Intégration continue : chaque contrôle s'exécute même si un contrôle
  antérieur échoue ; les workflows sont analysés par `zizmor` ; les messages de
  commit ainsi que le titre et la description d'une *pull request* sont
  contrôlés ; chaque écart s'affiche en annotation sur le diff.
- `scripts/install.py` est couvert par des tests sur une cible temporaire, pour
  Claude Code et Copilot CLI.
- Journal des modifications `CHANGELOG.md`, contrôlé par `scripts/changelog.py` ;
  une *pull request* qui modifie un outil ou `scripts/install.py` doit y
  ajouter une entrée, et le push d'un tag de version crée la Release GitHub avec
  la section de cette version.

## [1.2.0] - 2026-10-02

### 🚀 Nouveautés

- Skill `pull-request` : commit, branche de travail, push et *pull request*
  GitHub par `gh`, selon les conventions et le template de PR du projet, à
  défaut selon des conventions et un template embarqués.

## [1.1.0] - 2026-10-01

### 🚀 Nouveautés

- Status line `usage-session` pour Claude Code : remplissage du contexte et
  quotas affichés en permanence, sans appel au modèle.

### 📝 Documentation

- Règle relative à `settings.json` précisée pour Copilot CLI.

## [1.0.0] - 2026-09-27

### 🚀 Nouveautés

- Skills `clean-android-tv` et `setup-harness`.
- Agents `audit-docs` et `relecture-fr`.
- Hook `validate-tool`, enregistré localement dans le dépôt.
- `scripts/install.py` : installation et mise à jour par merge intelligent pour
  Claude Code et Copilot CLI.

### 🧹 Maintenance

- `scripts/validate.py`, ses tests, l'intégration continue et les hooks git
  `pre-commit` et `commit-msg`, pour contribuer au dépôt.

[Non publié]: https://github.com/EudesRobin/ia-tools/compare/1.2.0...HEAD
[1.2.0]: https://github.com/EudesRobin/ia-tools/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/EudesRobin/ia-tools/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/EudesRobin/ia-tools/releases/tag/1.0.0
