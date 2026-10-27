# MANDATORY COCKPIT SUBMODULE SYNCHRONIZATION RULE

> [!CAUTION]
> ## 🚨 MANDATORY P0 INVARIANT: COCKPIT SUBMODULE SYNCHRONIZATION (ZERO STRAY SUBMODULES) 🚨
> For ANY modification, addition, or refactoring of the Workshop Cockpit (`garage.reception`, `view_garage_reception_form`):
> 
> 1. **MANDATORY SKILL ACTIVATION**:
>    The AI assistant MUST activate and execute the **`cockpit-submodule-sync`** skill (`~/.gemini/config/skills/cockpit-submodule-sync/SKILL.md`).
> 
> 2. **LIFECYCLE GROUND TRUTH**:
>    - The data coming from the Android mobile/tablet client (`workshop_tablet_api.py`, `happy-faraday`) builds and drives **90% of the vehicle lifecycle**.
>    - The Cockpit (accessible from *Véhicule Atelier*, side-by-side 2-panel split view) is the **eagle-eye command deck** that controls and monitors all submodules.
> 
> 3. **PROHIBITION ON STRAY OR UX-ONLY MODIFICATIONS**:
>    - Modifying Cockpit fields, tabs, or buttons without verifying and synchronizing the underlying submodules (`repair.order`, `garage.insurance.claim`, `garage.reception.task`, `garage.parts.purchase`, `garage.repair.payment`, `whatsapp.gateway`) is **STRICTLY FORBIDDEN**.
>    - Every Cockpit field must have an explicit data contract: ownership (`related=` vs stored), mutability (`inverse=` vs `readonly`), mobile ingestion parity, and stage interlock consistency.
> 
> 4. **MANDATORY 5-TEST SUBMODULE AUDIT**:
>    Before applying any change to the Cockpit, the assistant must document the 5 Submodule Parity Tests:
>    - [1] Ownership & Delegation Test
>    - [2] Bidirectional Mutability Test
>    - [3] Mobile Ingestion Parity Test
>    - [4] Lifecycle Interlock Test
>    - [5] Downstream Rollup & Computed Trigger Test
> 
> 5. **POST-MODIFICATION VALIDATION & STAGING SYNC**:
>    - Run the 3-Step Pre-Flight Protocol (module upgrade + ORM view compilation + deprecated grep).
>    - Run `graphify update .` to update the AST call graph.
>    - Immediately commit and push to `origin main` to sync Hostinger staging.
