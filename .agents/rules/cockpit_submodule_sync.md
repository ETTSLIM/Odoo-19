# MANDATORY COCKPIT SUBMODULE SYNCHRONIZATION RULE

> [!CAUTION]
> ## 🚨 MANDATORY P0 INVARIANT: COCKPIT SUBMODULE SYNCHRONIZATION (ZERO STRAY SUBMODULES) 🚨
> For ANY modification, addition, or refactoring of the Workshop Cockpit (`garage.reception`, `view_garage_reception_form` in `custom_addons/garage_repair_core/views/garage_reception_views.xml`):
> 
> 1. **MANDATORY SKILL ACTIVATION**:
>    The AI assistant MUST activate and execute the **`cockpit-submodule-sync`** skill (`~/.gemini/config/skills/cockpit-submodule-sync/SKILL.md`).
> 
> 2. **LIFECYCLE & DUAL-SURFACE GROUND TRUTH**:
>    - **Mobile Origin (90% of Build)**: Data coming from the Android mobile/tablet client (`workshop_tablet_api.py`, `happy-faraday`) drives 90% of the vehicle lifecycle (Check-in, OCR, 4x4 Photos, Darija Voice Diagnostic, Subtasks, Mechanic PIN sign-offs).
>    - **Cockpit Command Deck (Surface A)**: The 2-panel split view (`view_garage_reception_form` + `garage_cockpit_tabs.js`) is the eagle-eye control tower (`col-lg-4` Left Sidebar Identity/Finance + `col-lg-8` Right Lifecycle Notebook Tabs `tab_intake`, `tab_devis_active`, `tab_pieces_active`, `tab_travaux_active`, `tab_sinistre`, `tab_facturation_active`).
>    - **Standalone Submodule Views (Surface B)**: Accessed via `navbar_subnav.js` (*Ordres de Travaux Actifs*, *Dossiers Sinistres*, *État du Stock Magasin*, *BL Fournisseurs*, *Journal Caisse Guichet*, *Factures Fiscales*, *Parc Véhicules*).
> 
> 3. **PROHIBITION ON STRAY OR UX-ONLY MODIFICATIONS**:
>    - Modifying **Surface A (Cockpit)** without verifying and synchronizing **Surface B (Standalone Submodule Form/List/Kanban views + Wizards + Bidirectional ORM `write()` hooks)** is **STRICTLY FORBIDDEN**.
>    - Before writing code, the assistant MUST produce the **5-Layer Submodule Ripple Matrix**:
>      - **[L1] Android Tablet API**: `workshop_tablet_api.py` (`_reception_to_vehicle_card`, `_reception_to_vehicle_detail`, `api_checkin`, `api_voice_update`, `api_diagnostic`, `api_assurance`) & `happy-faraday`.
>      - **[L2] Cockpit Surface A**: `garage_reception.py`, `garage_reception_views.xml`, `garage_cockpit_tabs.js` (`_locked` / `_active` tabs & `stage_sequence` gates 10–70).
>      - **[L3] Submodule ORM & Bidirectional Sync**: Forward (Cockpit ➔ Submodule) & Reverse (Submodule ➔ Cockpit) across `repair.order`, `garage.insurance.claim`, `garage.parts.bl`, `garage.diagnostic.log`, `garage.damage.item`, `garage.reception.task`, `garage.repair.payment`, preserving anti-recursion context flags (`skip_ro_sync`, `skip_devis_sync`, `skip_subtask_sync`, `auto_workflow_sync`, `skip_stock_note_sync`, `skip_specialty_sync`).
>      - **[L4] Standalone Submodule Surface B**: `garage_repair_order_views.xml`, `garage_insurance_claim_views.xml`, `garage_parts_purchase_views.xml`, `garage_diagnostic_log_views.xml`, and `wizard/*.xml`.
>      - **[L5] External Outputs**: `portal_tracking.py`, `portal_tracking_templates.xml`, `whatsapp_gateway.py`, and QWeb PDF reports (`report_*.xml`).
> 
> 4. **MULTI-MODEL PRE-FLIGHT VERIFICATION & STAGING SYNC**:
>    - Run `get_views()` compilation across BOTH `garage.reception` AND all connected submodules (`repair.order`, `garage.insurance.claim`, `garage.parts.bl`, `garage.diagnostic.log`, `garage.damage.item`, `garage.repair.payment`).
>    - Run `graphify update .` and immediately commit & push to `origin main`.
