# Odoo 19 Developer & MCP Reference Guide

Ce guide sert d'ancre documentaire et technique pour le pilotage d'Odoo 19 dans cet environnement.

---

## 1. Commandes de Contrôle de la Base de Données (depuis le terminal hôte)

Comme Odoo tourne sous Docker Compose, nous avons le contrôle direct et complet sur la base PostgreSQL et le runtime Odoo :

### A. Accès Direct PostgreSQL (`psql`)
```bash
# Se connecter à la base de données
docker compose exec db psql -U odoo -d postgres

# Lister les bases existantes
docker compose exec db psql -U odoo -c "\l"

# Créer directement une base sans démo depuis le terminal
docker compose exec web odoo -d garage_db -i base,l10n_ma --without-demo=all --stop-after-init
```

### B. Shell Interactif Python Odoo
```bash
# Ouvrir le REPL Odoo Python pour inspecter n'importe quel modèle en direct
docker compose exec web odoo shell -d garage_db
```

### C. Mise à jour et validation à chaud d'un module custom
```bash
# Mettre à jour et valider le schéma de garage_repair_core
docker compose exec web odoo -d garage_db -u garage_repair_core --stop-after-init
```

### D. Consultation des Logs en Temps Réel
```bash
docker compose logs -f web
```

---

## 2. Standards Invariants Odoo 19

### Vues & Frontend (OWL 2)
* **Vues Kanban** : 
  * `<t t-name="card">` est **strictement obligatoire** sous `<templates>`.
  * `<t t-name="kanban-box">` est **déprécié et interdit** (provoque l'erreur Owl `Missing 'card' template`).
  * L'élément `<article>` généré par le moteur Owl gère nativement le clic (`onGlobalClick`) et l'aspect visuel de carte.
* **Vues en Liste** : Remplacement standardisé de `<tree>` par `<list>`.
* **Modificateurs XML** : Utiliser `invisible="expr"`, `readonly="expr"`, `required="expr"` directement sur les balises (la syntaxe `attrs="..."` et `states="..."` est retirée).
* **Accessibilité** : 
  * Toute icône `<i class="fa ...">` doit avoir un attribut `title="..."` ou `aria-label="..."`.
  * Tout bloc d'alerte `<div class="alert alert-*">` doit comporter un attribut explicite `role="alert"` ou `role="status"`.

### ORM Python & Données
* **Relations ORM modernes** : Utiliser `from odoo import Command` avec `Command.create()`, `Command.update()`, `Command.delete()`, `Command.set()`, `Command.clear()`, `Command.link()`. Ne plus utiliser les tuples bruts `(0, 0, ...)`, `(6, 0, ...)`.
* **Sécurité & Droits d'Accès** : Tout modèle déclaré (`models.Model` ou `models.TransientModel`) **doit obligatoirement** posséder sa règle dans `security/ir.model.access.csv`.
* **Manifeste** : Tout fichier XML (vue, wizard, rapport, data) doit être référencé dans la section `data` de `__manifest__.py`.

---

## 3. Emplacement du Code Source Officiel Odoo 19 (Vérité Terrain)

Pour inspecter n'importe quel module ou composant standard Odoo 19 :
* Dans le conteneur Docker : `/usr/lib/python3/dist-packages/odoo/addons/`
* Exemples de référence : `fleet`, `repair`, `account`, `stock`, `web`
