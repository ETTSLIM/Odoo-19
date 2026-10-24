---
description: Strict Odoo 19 Development Standards and Invariants
globs: ["custom_addons/**/*", "config/**/*"]
---

# Strict Odoo 19 Development Standards & Verification Protocol

Whenever developing, generating, or refactoring code in this Odoo 19 project, strictly adhere to the following standards. Never rely on obsolete conventions from Odoo 12–17.

---

## 1. Views & Frontend Architecture

### A. Kanban Views (OWL 2)
* **MANDATORY**: Inside `<kanban><templates>`, the root template **MUST** be `<t t-name="card">` (or `<t t-name="card" class="...">`).
* **STRICTLY FORBIDDEN**: `<t t-name="kanban-box">`. In Odoo 19, `KanbanArchParser` will throw `Error: Missing 'card' template.` and crash the entire UI.
* **Card Container**: The `<article>` element created by Owl Kanban already acts as the card container with click handler (`onGlobalClick`). Do not add redundant outer wrappers with duplicate borders or `oe_kanban_global_click`.

### B. List Views
* **MANDATORY**: Use `<list string="...">` for list views.
* **FORBIDDEN**: Legacy `<tree>` views.

### C. Modifiers & Attributes
* **MANDATORY**: Use `invisible="expression"`, `readonly="expression"`, `required="expression"` directly on `<field>`, `<button>`, or `<group>`.
* **FORBIDDEN**: The deprecated `attrs="{'invisible': ...}"` and `states="..."` syntax.

### D. Accessibility & Icons
* Any `<i>` fontawesome element must have a `title="..."` or `aria-label="..."`.
* Any `<div class="alert alert-*">` must have an explicit `role="alert"` or `role="status"`. Do not use sub-classes starting with `alert-` (like `alert-heading`) on inner elements without role.

---

## 2. Python ORM & Data Architecture

### A. Relational Commands (One2many & Many2many)
* **MANDATORY**: Import `from odoo import Command` and use:
  - `Command.create({'field': val})` instead of `(0, 0, {...})`
  - `Command.update(id, {'field': val})` instead of `(1, id, {...})`
  - `Command.delete(id)` instead of `(2, id, 0)`
  - `Command.unlink(id)` instead of `(3, id, 0)`
  - `Command.link(id)` instead of `(4, id, 0)`
  - `Command.clear()` instead of `(5, 0, 0)`
  - `Command.set([id1, id2])` instead of `(6, 0, [ids])`
* In XML evaluation attributes (`eval="[...]"`), standard Odoo tuple expressions like `[(4, ref(...))]` remain valid.

### B. Security & ACLs
* Every newly introduced model (`models.Model` or `models.TransientModel`) **MUST** have an entry in `security/ir.model.access.csv`.
* In Odoo 19, any model lacking an ACL rule triggers warnings and blocks access for non-superusers.

### C. Manifest File (`__manifest__.py`)
* Every newly created view or data XML file must be registered under the `'data'` list in `__manifest__.py`.

---

## 3. Mandatory Pre-Flight Verification Protocol

Before completing any task that modifies or adds views, models, or wizards:
1. **Source Cross-Check**: Inspect official Odoo 19 modules inside the running container (`/usr/lib/python3/dist-packages/odoo/addons/`) to verify modern patterns against living code.
2. **Schema & Upgrade Check**: Execute module upgrade to compile and validate XML architectures:
   ```bash
   docker exec odoo19_garage odoo -u <module_name> -d garage_db --stop-after-init
   ```
   Ensure zero errors and zero accessibility/syntax warnings.
3. **View Compilation Test**: Run a Python test in the container:
   ```bash
   docker exec odoo19_garage python3 -c "import odoo; from odoo.modules.registry import Registry; from odoo import api; odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'garage_db']); reg = Registry('garage_db'); cr = reg.cursor(); env = api.Environment(cr, 1, {}); env['<model.name>'].get_views([(False, '<view_type>')]); cr.close()"
   ```
