# Post-merge : nettoyer le dépôt local

Nettoyer le dépôt local une fois la PR mergée sur GitHub : revenir sur la
branche par défaut, la mettre à jour, retirer les worktrees et supprimer les
branches locales mergées. Le merge lui-même reste à la charge de
l'utilisateur.

## Suivi de progression — impératif

Tâche en cinq phases ; la règle de suivi des tâches s'applique. Créer la liste
ci-dessous avant la [phase 1](#1-établir-létat), et la ré-afficher en entier à
chaque changement d'état, avec les marqueurs `[ ]` non commencée, `[~]` en
cours, `[x]` terminée, `[-]` abandonnée ; une étape abandonnée porte une raison
courte sur la même ligne. Plusieurs `[~]` simultanées seulement si les étapes
sont réellement menées en parallèle. Quand la session expose son propre outil de
liste de tâches, c'est cet outil qui est employé et qui fait l'affichage ; sinon
le bloc est écrit dans la réponse. Aucun des deux suivis n'est un repli.

**Tâches**
- [ ] Phase 1 : établir l'état des branches mergées et des worktrees
- [ ] Phase 2 : présenter le plan et obtenir l'accord
- [ ] Phase 3 : mettre à jour la branche par défaut
- [ ] Phase 4 : retirer les worktrees et supprimer les branches retenues
- [ ] Phase 5 : vérifier l'état final

La [phase 5](#5-vérifier) est une vérification : elle ne passe à `[x]` qu'après
une nouvelle exécution du script, le résultat étant alors nommé
(`[x] Phase 5 : vérifier l'état final — <n> branche(s) supprimée(s)`).

## 1. Établir l'état

```text
python {AGENT_DIR}/skills/pull-request/etat_depot.py --post-merge
```

`branche`, `modifications` et `dernier_commit` décrivent le worktree principal,
où s'exécute le retour sur la branche par défaut. Relever :

- `branche : (HEAD detachee)` → s'arrêter et signaler le HEAD détaché à
  l'utilisateur : un changement de branche abandonnerait les commits qui ne
  sont portés par aucune branche.
- Valeur de `modifications` autre que `0 indexee(s), 0 non indexee(s), 0 non
  suivie(s)` → s'arrêter et présenter les modifications à l'utilisateur : un
  changement de branche les emporterait ou échouerait.
- `base_extraite : <chemin>` → la branche par défaut est extraite dans un autre
  worktree, où sa mise à jour doit se faire : signaler ce chemin à l'utilisateur et
  s'arrêter.
- `worktree_courant : lie` → la session se trouve dans un worktree secondaire.
  Les commandes des phases 3 et 4 visent le worktree principal par
  `git -C <racine_principale> …`, forme qui passe par une demande de
  confirmation. Le worktree de la session n'est pas retiré : son dossier est en
  cours d'utilisation.
- Chaque ligne `mergee : <branche> #<n> head=<etat> … worktree=<chemin>
  etat=<etat>` :
  - `head=identique` → la branche locale est exactement celle qui a été
    mergée : elle est supprimable ;
  - `head=en_retard` → la PR a reçu des commits ajoutés hors du dépôt local,
    suggestions appliquées sur GitHub par exemple ; aucun commit local n'est
    perdu, mais la branche n'est supprimée que sur demande explicite ;
  - `head=divergente commits_locaux=<n>` → la branche porte `<n>` commits
    absents de la PR mergée (`indetermine` quand le head de la PR n'est pas
    présent localement) : ne pas la supprimer.
- `non_mergees` → branches sans PR mergée : n'y pas toucher.

## 2. Présenter le plan

Retenir la branche de la PR que l'utilisateur a désignée ou, faute de
désignation, la branche courante du worktree principal, si elle est classée
`identique`.
Les autres branches `identique` sont proposées, pas incluses d'office.
Présenter :

- la mise à jour de la branche par défaut ;
- pour chaque branche retenue, son worktree éventuel et son état ;
- les branches laissées en place, avec leur raison : `en_retard`, `divergente`
  avec les commits locaux concernés, worktree de la session, worktree `verrouille`.

Un worktree à l'état `ignores:<n>` ou `modifie:<n>` → le signaler
explicitement : `git worktree remove` supprime sans avertir les fichiers
ignorés (`.env`, configuration locale, artefacts), et refuse un worktree
modifié. **Obtenir l'accord explicite de l'utilisateur** sur le plan avant la
[phase 3](#3-mettre-à-jour-la-branche-par-défaut).

Aucune branche retenue → passer la
[phase 4](#4-retirer-les-worktrees-et-supprimer-les-branches) à `[-]` avec sa
raison. Mener la phase 3 si l'utilisateur a demandé le retour
sur la branche par défaut ou sa mise à jour ; sinon s'arrêter.

## 3. Mettre à jour la branche par défaut

```text
git switch <base>
git pull --ff-only
```

Depuis un worktree secondaire, insérer `-C <racine_principale>` après `git`
dans chaque commande : `git -C <racine_principale> switch <base>`. Un
`pull --ff-only` refusé → lire le message : une branche locale qui a divergé
du dépôt distant → s'arrêter sans merge ni rebase, et signaler le refus à
l'utilisateur ; toute autre cause (branche sans suivi, erreur réseau) →
signaler le message tel quel.

## 4. Retirer les worktrees et supprimer les branches

Pour chaque branche retenue, dans cet ordre :

```text
git worktree remove <chemin>      # seulement si worktree=<chemin>
git branch -D <branche>
```

`git branch -D` est requis : après un merge par squash ou par rebase, le head
de la branche n'est pas un ancêtre de la base et `git branch -d` refuse de la
supprimer. La concordance des heads établie à la
[phase 1](#1-établir-létat) remplace la vérification d'ascendance qu'effectue
`git branch -d`. Un worktree `absent` se retire par `git worktree prune`. Un
`git worktree remove` refusé, quelle qu'en soit la cause → laisser le worktree
et la branche en place, et signaler le message à l'utilisateur.

Enfin, retirer les références des branches distantes supprimées :

```text
git fetch --prune
```

## 5. Vérifier

Relancer `etat_depot.py --post-merge`. Aucune branche supprimée ne doit plus
figurer dans la sortie, et `branche` doit valoir la branche par défaut. Un
écart → reprendre à la
[phase 4](#4-retirer-les-worktrees-et-supprimer-les-branches) pour la branche
en cause ; un second écart → s'arrêter et le présenter à
l'utilisateur. Indiquer ensuite `dernier_commit`, les branches supprimées et
celles laissées en place avec leur raison.

Session ouverte dans un worktree secondaire → inviter l'utilisateur à rouvrir
la session depuis `racine_principale` pour retirer ce worktree par un nouveau
post-merge.

## Règles

- Ne supprimer qu'une branche classée `head=identique` et retenue dans le plan
  accepté. Une branche `en_retard`, `divergente` ou non mergée n'est supprimée
  que sur demande explicite de l'utilisateur, après qu'il en a vu les commits
  locaux (`git log <pr_head>..<branche>` quand le head de la PR est présent
  localement).
- Ne jamais supprimer la branche par défaut, ni une branche distante.
- Ne pas faire de rebase des autres branches de travail sur la base mise à
  jour : une branche déjà poussée exigerait un push forcé.
