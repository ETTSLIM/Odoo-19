# ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS

> [!CAUTION]
> ## 🚨 MANDATORY P0 INVARIANT: GRAPHIFY-FIRST PROTOCOL (ABSOLUTE PRIORITY) 🚨
> For ANY user question, investigation, bug diagnosis, data flow trace, or code modification regarding Odoo models, fields, views, actions, controllers, wizards, access rights (ACLs), reports, or OWL components:
> 1. **FIRST ACTION MUST BE GRAPHIFY**: The AI assistant MUST execute `graphify query "<question>"` or `graphify explain "<Model/Class/Symbol>"` via `run_command` BEFORE executing any file inspection (`read_file`, grep, or raw file scans) or answering.
> 2. **PROHIBITION ON RAW SPECULATION & HALLUCINATION**: Speculating on model inheritance (`_inherit`), relational links (`Many2one`, `One2many`, `Many2many`), view IDs, or legacy syntax without querying Graphify is STRICTLY FORBIDDEN. Graphify maps the exact AST call graph, class inheritance hierarchy, and inter-module relationships.
> 3. **SECONDARY TOOLS ONLY**: File reading (`read_file`) and grep searches are ONLY permitted as secondary steps to confirm or edit specific lines discovered and scoped by Graphify.
> 4. **FALLBACK & WIKI**: When `graphify-out/graph.json` exists, always prioritize `graphify query` / `explain` / `path`. If the CLI is ever missing, fall back to `graphify-out/GRAPH_REPORT.md` or `graphify-out/wiki/index.md`.
> 5. **MANDATORY POST-MODIFICATION AST SYNC & AUDIT**: After modifying or adding any Python model, XML view, or controller, immediately run `graphify update .` to synchronize the knowledge graph. Verify downstream dependencies with `graphify explain "<ModifiedSymbol>"` before running container verification.

> [!CAUTION]
> ## 🚨 MANDATORY P0 INVARIANT: ZERO-COMPROMISE PLAN FIDELITY & ATOMIC EXECUTION 🚨
> Whenever preparing a plan (`/plan`), reviewing an audit, or executing plan tasks:
> 1. **MANDATORY SKILL ACTIVATION**: The AI assistant MUST activate and adhere strictly to the **`plan-fidelity-auditor`** skill (`~/.gemini/config/skills/plan-fidelity-auditor/SKILL.md`).
> 2. **ZERO SCOPE DILUTION / COMPROMISE**:
>    - If an audit states `[COMBINE]`, substituting a cosmetic rename (e.g. adding numbers `1.` and `2.` to separate tabs) is **STRICTLY PROHIBITED**. `[COMBINE]` strictly means merging the elements into the same parent container (`<page>`, `<group>`, etc.).
>    - If an audit states `[ELIMINATE]`, the element must be completely removed or hidden with `invisible="1"`.
> 3. **MANDATORY VISUAL WIREFRAME**: Every plan modifying UI forms, tabs, or menus must provide an explicit ASCII wireframe mockup showing the human user experience before and after the change.
> 4. **PROGRAMMATIC ARCHITECTURAL ASSERTIONS**: Before declaring an execution complete, the assistant must run an active XPath/AST assertion script verifying exact element counts and parent-child container relationships.

> [!CAUTION]
> ## 🚨 MANDATORY P0 INVARIANT: COCKPIT SUBMODULE SYNCHRONIZATION (ZERO STRAY SUBMODULES) 🚨
> For ANY modification, addition, or refactoring of the Workshop Cockpit (`garage.reception`, `view_garage_reception_form` in `custom_addons/garage_repair_core/views/garage_reception_views.xml`):
> 1. **MANDATORY SKILL ACTIVATION**: The AI assistant MUST activate and adhere strictly to the **`cockpit-submodule-sync`** skill (`~/.gemini/config/skills/cockpit-submodule-sync/SKILL.md`).
> 2. **LIFECYCLE & DUAL-SURFACE GROUND TRUTH**:
>    - **Mobile Origin (90% of Build)**: Data coming from the Android mobile/tablet client (`workshop_tablet_api.py`, `happy-faraday`) drives **90% of the vehicle lifecycle**.
>    - **Surface A (Cockpit Command Deck)**: The 2-panel split view (`view_garage_reception_form` + `garage_cockpit_tabs.js`) is the eagle-eye control tower (`col-lg-4` Left Sidebar + `col-lg-8` Right Lifecycle Notebook Tabs: `tab_intake`, `tab_devis_active`, `tab_pieces_active`, `tab_travaux_active`, `tab_sinistre`, `tab_facturation_active`).
>    - **Surface B (Standalone Submodule Screens)**: Accessed via `navbar_subnav.js` (*Ordres de Travaux Actifs*, *Dossiers Sinistres*, *État du Stock Magasin*, *BL Fournisseurs*, *Journal Caisse Guichet*, *Factures Fiscales*, *Parc Véhicules*).
> 3. **PROHIBITION ON STRAY OR UX-ONLY MODIFICATIONS**:
>    - Modifying **Surface A (Cockpit)** without verifying and synchronizing **Surface B (Standalone Submodule Form/List/Kanban views + Wizards + Bidirectional ORM `write()` hooks)** is **STRICTLY FORBIDDEN**.
> 4. **MANDATORY 5-LAYER SUBMODULE RIPPLE MATRIX**: Before applying any change to the Cockpit, the assistant must trace and synchronize all 5 layers:
>    - **[L1] Android Tablet API**: `workshop_tablet_api.py` (`_reception_to_vehicle_card`, `_reception_to_vehicle_detail`, `api_checkin`, `api_voice_update`, `api_diagnostic`, `api_assurance`) & `happy-faraday`.
>    - **[L2] Cockpit Surface A**: `garage_reception.py`, `garage_reception_views.xml`, `garage_cockpit_tabs.js` (`_locked` / `_active` tabs & `stage_sequence` gates 10–70).
>    - **[L3] Submodule ORM & Bidirectional Sync**: Forward (Cockpit ➔ Submodule) & Reverse (Submodule ➔ Cockpit) across `repair.order`, `garage.insurance.claim`, `garage.parts.bl`, `garage.diagnostic.log`, `garage.damage.item`, `garage.reception.task`, `garage.repair.payment`, preserving anti-recursion context flags (`skip_ro_sync`, `skip_devis_sync`, `skip_subtask_sync`, `auto_workflow_sync`, `skip_stock_note_sync`, `skip_specialty_sync`).
>    - **[L4] Standalone Submodule Surface B**: `garage_repair_order_views.xml`, `garage_insurance_claim_views.xml`, `garage_parts_purchase_views.xml`, `garage_diagnostic_log_views.xml`, and `wizard/*.xml`.
>    - **[L5] External Outputs**: `portal_tracking.py`, `portal_tracking_templates.xml`, `whatsapp_gateway.py`, and QWeb PDF reports (`report_*.xml`).

> [!CAUTION]
> ## 🚨 MANDATORY P0 INVARIANT: ATOMIC GIT COMMIT & REMOTE PUSH PROTOCOL (HOSTINGER SYNC) 🚨
> For ANY code modifications, bug fixes, view enhancements, or architectural refactors:
> 1. **MANDATORY POST-VALIDATION GIT PUSH**: Immediately after completing local verification (3-Step Pre-Flight Protocol & AST Sync), the AI assistant MUST stage, commit with a semantic message, and push to `origin main` via `git push origin main`.
> 2. **ZERO UNPUSHED CODE**: Never leave modified files unstaged or unpushed at the end of a turn. The staging server on Hostinger (`hitanger` at 167.233.156.220) synchronizes with `origin main`; unpushed changes cause live desynchronization and break user verification.
> 3. **VERIFY REMOTE REFLECTION**: Always confirm that `git push` succeeded and that the remote branch has received the commit before reporting completion to the user.

> **CRITICAL DIRECTIVE FOR ALL AGENTS WORKING IN THIS REPOSITORY:**
> You are developing for **Odoo 19.0** running on **Python 3.12** and **PostgreSQL 16**.
> Older Odoo paradigms (Odoo 11–17) are **strictly forbidden**. Under no circumstances should you generate legacy syntax.
> Every component you touch must adhere to the modern Odoo 19 invariants outlined below.

---

## 1. COMPREHENSIVE COMPONENT WATCHLIST & BANNED PATTERNS

| Component / Subsystem | Modern Odoo 19 Standard (MANDATORY) | Deprecated / Legacy Pattern (STRICTLY BANNED) | Why It Breaks / Consequences |
| :--- | :--- | :--- | :--- |
| **Kanban Views** | `<t t-name="card">` | `<t t-name="kanban-box">` | `KanbanArchParser` throws `Missing 'card' template` and crashes UI. |
| **Kanban Clicks** | Native `<article>` container handles click (`onGlobalClick`). | `<div class="oe_kanban_global_click">` | Legacy class; creates duplicate borders/padding in modern themes. |
| **List Views** | `<list string="...">` | `<tree string="...">` | `<tree>` is obsolete; causes schema validation errors. |
| **XML Dynamic Attributes** | `invisible="condition"`, `readonly="condition"`, `required="condition"` | `attrs="{'invisible': ...}"` and `states="..."` | Removed in Odoo 17; causes view parsing crashes. |
| **Chatter** | `<chatter><field name="message_follower_ids"/><field name="activity_ids"/><field name="message_ids"/></chatter>` | `<div class="oe_chatter">` | Legacy structure; modern layout uses semantic `<chatter>`. |
| **ORM Relational Ops** | `from odoo import Command`<br>`Command.create({...})`<br>`Command.update(id, {...})`<br>`Command.delete(id)`<br>`Command.unlink(id)`<br>`Command.link(id)`<br>`Command.clear()`<br>`Command.set([ids])` | Tuples: `(0, 0, {...})`, `(1, id, {...})`, `(2, id, 0)`, `(3, id, 0)`, `(4, id, 0)`, `(5, 0, 0)`, `(6, 0, [ids])` | Raw tuple operations in Python are unreadable, error-prone, and deprecated in modern Odoo. |
| **Field Tracking** | `tracking=True` | `track_visibility='onchange'` or `'always'` | Deprecated in Odoo 14+; ignored or causes warnings. |
| **Field Indexing** | `index=True` | `select=True` | Obsolete field argument. |
| **Group By Queries** | `self.env['model']._read_group(domain, groupby, aggregates)` | `self.env['model'].read_group(...)` | `_read_group` is the modern, type-safe, high-performance API. |
| **High-Perf Queries** | `self.search_fetch(domain, field_names, limit=...)` | Looping `search()` then `read()` | Inefficient SQL queries. |
| **Security (ACLs)** | Every model (`Model` & `TransientModel`) **must** be declared in `ir.model.access.csv`. | Omitting wizards or transient models from ACL CSV. | In Odoo 19, missing ACL rules trigger compiler warnings and reject user access. |
| **Manifest Assets** | In `__manifest__.py` under `'assets': {'web.assets_backend': [...]}` | `views/assets.xml` or `<template id="assets_backend" inherit_id="...">` | `assets.xml` was removed in Odoo 15; will not load assets. |
| **JavaScript / UI** | Pure OWL v2 (`@odoo/owl` with `Component`, `useState`, `xml`) registered in `@web/core/registry`. | `Widget.extend()`, `include()`, OWL v1 classes. | Legacy widget architecture is completely removed. |
| **QWeb Templates** | `<t t-out="expression"/>` | `<t t-raw="expression"/>` | `t-raw` was removed for XSS security in Odoo 16+. |
| **View Accessibility** | Every `<i class="fa ...">` must have `title="..."` or `aria-label="..."`.<br>Every `<div class="alert alert-*">` must have `role="alert"` or `role="status"`. | Empty `<i>` icon tags and alerts without ARIA roles. | Odoo 19 view compiler logs accessibility validation warnings. |
| **Alert Inner Classes** | Do not use inner classes starting with `alert-` (like `alert-heading`) without a role. | `<h4 class="alert-heading">` inside alerts. | Odoo 19 regex `startswith('alert-')` flags inner elements as unlabelled alerts. |
| **Reports** | `<record id="..." model="ir.actions.report">` | Legacy `<report>` XML tag. | Deprecated XML tag removed from Odoo. |

---

## 2. GROUND TRUTH ENGINE: THE LIVE ODOO 19 CONTAINER

**NEVER GUESS SYNTAX FROM MEMORY.**
The official, living Odoo 19 source code is running locally in docker container `odoo19_garage`.
When creating or modifying any view, field, widget, or controller, use the command line to inspect standard Odoo 19 implementations:

* **Official Source Path**: `/usr/lib/python3/dist-packages/odoo/addons/`
* **Inspect standard Kanban views**:
  ```bash
  docker exec odoo19_garage grep -rn 't-name="card"' /usr/lib/python3/dist-packages/odoo/addons/<addon_name>/
  ```
* **Inspect standard List views**:
  ```bash
  docker exec odoo19_garage grep -rn '<list' /usr/lib/python3/dist-packages/odoo/addons/<addon_name>/
  ```
* **Inspect standard OWL components**:
  ```bash
  docker exec odoo19_garage find /usr/lib/python3/dist-packages/odoo/addons/web/static/src/ -name "*.js"
  ```

---

## 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL

Before presenting any code changes or declaring a task complete, you **MUST** run these 3 validation steps from the terminal:

### Step 1: Automated Module Upgrade & Schema Validation
Run the module upgrade command against the database:
```bash
docker exec odoo19_garage odoo -u <module_name> -d garage_db --stop-after-init 2>&1 | grep -iE "error|warning"
```
* **PASS CONDITION**: Zero `ERROR` entries and zero custom module `WARNING` entries (e.g. no missing ACLs, no accessibility warnings, no missing card templates).

### Step 2: Python ORM View Compilation Test
Verify that the Owl arch parser can successfully load all modified views:
```bash
docker exec odoo19_garage python3 -c '
import odoo
from odoo.modules.registry import Registry
from odoo import api
odoo.tools.config.parse_config(["-c", "/etc/odoo/odoo.conf", "-d", "garage_db"])
registry = Registry("garage_db")
with registry.cursor() as cr:
    env = api.Environment(cr, odoo.SUPERUSER_ID, {})
    for view_type in ["kanban", "list", "form"]:
        try:
            v = env["<model.name>"].get_views([(False, view_type)])
            print(f"[OK] {view_type} loaded successfully.")
        except Exception as e:
            print(f"[FAIL] {view_type}: {e}")
            raise
'
```

### Step 3: Deprecated Pattern Grep Audit
Run this quick audit on your custom addon directory to guarantee 0 legacy leakage:
```bash
grep -rnE 't-name="kanban-box"|<tree|attrs="|states="|track_visibility=|\(0, 0, ' custom_addons/
```
* **PASS CONDITION**: Zero matches.

---

## 4. MANDATORY GIT PUSH PROTOCOL (HOSTINGER STAGING SYNC)

Once local container verification (Steps 1–3) and AST sync (`graphify update .`) pass with 0 errors:
1. Stage all code and configuration changes:
   ```bash
   git add custom_addons/ ...
   ```
2. Commit with a concise semantic message:
   ```bash
   git commit -m "feat/fix: <description>"
   ```
3. Push to `origin main`:
   ```bash
   git push origin main
   ```
4. Verify remote push success so that Hostinger (`hitanger` at 167.233.156.220) immediately reflects the update.

