---
name: setup-harness
description: >-
  Configurer le harnais d'un projet (boucle de vérification : lancer, tester,
  vérifier) dans son fichier d'instructions — AGENTS.md, CLAUDE.md ou
  copilot-instructions.md. À utiliser quand l'utilisateur demande de mettre en
  place ou de configurer la boucle de feedback, le harnais ou le DoD
  (Definition of Done) du projet, d'indiquer dans AGENTS.md ou CLAUDE.md
  comment lancer et tester le projet, ou demande « comment vérifier que ça
  marche » pour un projet.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Edit
  - Write
  - Bash(git diff:*)
---

# Configurer le harnais d'un projet

Amorce la section « Harnais » du fichier d'instructions **du projet** (pas des
instructions globales de l'utilisateur) : le bloc lancer / tester / vérifier qui
permet de prouver qu'un changement fonctionne réellement, plutôt que de conclure
sur la seule absence d'erreur.

**Fichier cible**, par ordre de préférence :

- `AGENTS.md` à la racine du projet, s'il existe : c'est le fichier commun aux
  agents hôtes ;
- à défaut, le fichier d'instructions de l'agent hôte qui exécute la skill :
  `CLAUDE.md` pour Claude Code, `.github/copilot-instructions.md` pour Copilot
  CLI ;
- si `AGENTS.md` est absent et que seul existe le fichier d'un autre agent
  hôte, ce fichier ou un nouvel `AGENTS.md` : signaler la situation et
  soumettre ce choix à l'utilisateur en phase 3 ;
- si le fichier retenu se réduit à un renvoi, le fichier visé par ce renvoi.

## Suivi de progression — impératif

Cette skill est une tâche en cinq phases : la règle de suivi des tâches
s'applique. Créer la liste ci-dessous **avant la phase 1**, et la ré-afficher en
entier à chaque changement d'état, avec les marqueurs `[ ]` non commencée, `[~]`
en cours, `[x]` terminée, `[-]` abandonnée, cette dernière avec une raison
courte sur la même ligne. Plusieurs `[~]` simultanées seulement si les étapes
sont réellement menées en parallèle. Quand la session expose son propre outil
de liste de tâches, c'est cet outil qui est employé et qui fait l'affichage ;
sinon le bloc est écrit dans la réponse. Aucun des deux suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : détecter la stack et le fichier cible du projet courant
- [ ] Phase 2 : proposer le fichier cible et le bloc Harnais rempli
- [ ] Phase 3 : obtenir l'accord explicite de l'utilisateur
- [ ] Phase 4 : écrire le bloc dans le fichier cible du projet
- [ ] Phase 5 : vérifier l'écriture dans le fichier cible

La phase 3 est une vérification : elle ne passe à `[x]` que sur l'accord
explicite de l'utilisateur, pas sur la présentation du bloc. Sans accord, ne pas
passer à la phase 4. La phase 5 est une vérification : elle ne passe à `[x]`
qu'après relecture du fichier écrit, le résultat étant nommé
(`[x] Phase 5 : vérifier l'écriture — section unique, reste du fichier inchangé`).

## Instructions

1. **Détecter la stack et le fichier cible** du projet courant :
   - retenir d'abord les commandes que le projet déclare lui-même, dans cet
     ordre : intégration continue (`.github/workflows/`, `.gitlab-ci.yml`…),
     cibles d'un `Makefile`, `scripts` de `package.json`, `README` ou
     `CONTRIBUTING` ;
   - à défaut, les déduire du manifeste (`pyproject.toml`, `Cargo.toml`,
     `go.mod`, `pom.xml`, `build.gradle`…), en employant le wrapper présent
     (`gradlew`, `mvnw`) et le gestionnaire de paquets désigné par le
     lockfile ;
   - repérer l'information utile par une recherche ciblée (bloc `"scripts"`,
     `spring-boot-starter`) plutôt que de lire un manifeste en entier ;
   - plusieurs stacks (front-end et back-end, monorepo) → une ligne par
     composant sous chaque rubrique du bloc (**Lancer**, **Tester**,
     **Vérifier**) ;
   - rien de reconnu → demander à l'utilisateur comment ce projet se lance et
     se teste ;
   - déterminer le fichier cible (voir ci-dessus) et y lire toute section
     `## Harnais` ou section équivalente déjà présente.

2. **Proposer** le fichier cible et un bloc Harnais rempli avec les commandes
   détectées, à partir du template ci-dessous — **impératif** : reproduire sa
   structure et son paragraphe final tels quels, ne remplacer que les valeurs
   `<…>`. Si une section Harnais existe déjà, présenter la différence avec
   elle.

   ```markdown
   ## Harnais — boucle de vérification

   Comment prouver qu'un changement fonctionne dans **ce** projet :

   - **Lancer** : `<commande pour démarrer ou exécuter l'application>`
   - **Tester** : `<commande de tests>`
   - **Vérifier** : <comment observer qu'un changement fait ce qu'il doit —
     parcourir le scénario réel, pas seulement lancer les tests>

   Une modification n'est pas terminée tant que **Tester** n'est pas au vert et
   que le comportement attendu à l'étape **Vérifier** n'a pas été observé sur
   le scénario réel. Lancer, lire l'échec, corriger, relancer — ne pas conclure
   « c'est fait » sur la seule absence d'erreur, ni sur des commandes terminées
   dont le résultat n'a pas été observé.
   ```

   Pour **Vérifier**, ne pas se contenter de « les tests passent » : décrire
   comment observer le comportement réel (parcourir le scénario concerné — page
   dans le navigateur, appel API, sortie CLI sur un cas concret).

   Exemple — projet avec `pyproject.toml`, point d'entrée `outil` et dossier
   `tests/` :

   ```markdown
   - **Lancer** : `python -m outil convertir exemple.csv`
   - **Tester** : `pytest`
   - **Vérifier** : lancer la conversion sur `exemple.csv` et constater que
     `exemple.json` contient une entrée par ligne du fichier source
   ```

   Le paragraphe final du template est un **DoD (*Definition of Done*) formulé
   comme une boucle de vérification** : le reproduire tel quel, ne pas le réduire à une simple consigne
   « vérifier avant de conclure ».

3. **Faire confirmer** les commandes et le fichier cible par l'utilisateur avant
   d'écrire le bloc — corriger les commandes ou le fichier cible si
   l'utilisateur les juge faux ou incomplets.

4. **Écrire** le bloc dans le fichier cible du projet, sans jamais réécrire en
   entier un fichier existant :
   - Fichier déjà présent → ajouter ou mettre à jour uniquement la section
     `## Harnais — boucle de vérification`, sans modifier le reste du fichier.
   - Aucun fichier d'instructions dans le projet → créer celui de l'agent hôte
     avec uniquement cette section.

5. **Vérifier l'écriture.** Relire le fichier cible : la section
   `## Harnais — boucle de vérification` y figure une seule fois, avec les
   commandes validées en phase 3, et le reste du fichier est inchangé, ce que
   montre `git diff -- <fichier>` quand le projet est versionné. Écart →
   corriger le fichier, puis reprendre cette vérification. Indiquer ensuite à
   l'utilisateur le fichier modifié, en précisant que ce harnais vaut pour ce
   seul projet.

## Règles

- Ne jamais écrire dans les instructions globales de l'utilisateur
  (`{AGENT_DIR}/…`) : le harnais vit dans le projet.
- Ne rien écrire sans l'accord explicite obtenu en phase 3.
- Ne modifier que la section `## Harnais — boucle de vérification` du fichier
  cible.
- Nommer une variable d'environnement nécessaire au lancement, jamais sa
  valeur.

## Limites

- Les commandes proposées sont lues dans le projet, pas exécutées : la skill
  ne garantit pas qu'elles passent.
- Une section de vérification déjà présente sous un autre titre n'est reconnue
  que si l'agent la repère à la lecture du fichier cible.
