## Contexte

<!-- Le problème ou le besoin auquel répond la PR, en une à trois phrases ; PR ou issues liées (#n). -->

## Changements

- <!-- Changement significatif, formulé du point de vue de qui installe les outils. -->

## Vérification

<!-- Retirer une case dont le point est sans objet pour la modification ; la case de `scripts/validate.py` vaut pour toute modification et demeure. Ne cocher une case conservée qu'une fois son point effectivement vérifié : une case vide signale un point applicable mais non réalisé ; la section « Détail » indique pourquoi il ne l'a pas été. -->

- [ ] `python scripts/validate.py` passe
- [ ] Les tests `tests/test_*.py` concernés passent ; tout contrôle ajouté ou modifié a d'abord été observé en échec sur un cas construit pour échouer
- [ ] Outil modifié installé par `scripts/install.py` dans chaque agent hôte concerné, puis essayé en situation réelle avant le commit
- [ ] Passages modifiés relus par l'agent `relecture-fr`, écarts corrigés
- [ ] Entrée ajoutée au journal des modifications (modification de `skills/`, `agents/`, `hooks/`, `statuslines/` ou `scripts/install.py`)
- [ ] `zizmor --offline .github/workflows` passe (workflow modifié)

Détail :

- <!-- Commande lancée ou essai réel, et résultat observé. -->
