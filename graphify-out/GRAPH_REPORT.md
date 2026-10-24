# Graph Report - Odoo 19  (2026-10-24)

## Corpus Check
- 38 files · ~29,645 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 441 nodes · 552 edges · 42 communities (27 shown, 15 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- GarageInsuranceClaim
- RepairOrder
- models/__init__.py
- ProductTemplate
- wizard/__init__.py
- GarageWorkshopTabletApiController
- FleetVehicle
- GarageBillingWizard
- GaragePaymentRecoveryWizard
- GarageReception
- GarageReceptionTask
- 1. Views & Frontend Architecture
- GarageTrackingController
- 1. Commandes de Contrôle de la Base de Données (depuis le terminal hôte)
- navbar_subnav.js
- .write
- ResPartner
- ResUsers
- 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL
- 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL
- 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL
- .action_send_whatsapp_tracking
- .process_ai_diagnostic
- .action_create_or_view_repair_order
- ._read_group_stage_ids
- .agents/rules/graphify.md
- workflows/graphify.md
- .action_create_or_view_claim
- .action_open_ai_diagnostic_wizard
- .action_open_pin_wizard
- .action_reception_open_billing_wizard
- .action_reception_open_payment_wizard
- .action_reception_send_whatsapp_quote
- ._compute_can_toggle_workshop_tasks
- ._onchange_vehicle_id
- .submit_supplementary_diagnostic
- ._sync_subtasks_with_parent_stage
- .gemini/rules/graphify.md

## God Nodes (most connected - your core abstractions)
1. `GarageReception` - 36 edges
2. `GarageInsuranceClaim` - 31 edges
3. `RepairOrder` - 22 edges
4. `GarageWorkshopTabletApiController` - 14 edges
5. `_json_response()` - 13 edges
6. `FleetVehicle` - 12 edges
7. `ProductTemplate` - 10 edges
8. `send_garage_whatsapp()` - 10 edges
9. `GarageBillingWizard` - 10 edges
10. `GaragePartsBL` - 9 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (42 total, 15 thin omitted)

### Community 0 - "GarageInsuranceClaim"
Cohesion: 0.05
Nodes (20): GarageInsuranceClaim, depends, model_create_multi, onchange, Affiche les photos de choc et documents du dossier sinistre., Ouvre la fiche de réception associée., Ouvre l'ordre de réparation associé., Affiche les avenants pour pièces masquées. (+12 more)

### Community 1 - "RepairOrder"
Cohesion: 0.05
Nodes (20): GarageRepairLaborLine, GarageRepairPartLine, GarageRepairPayment, depends, model_create_multi, onchange, Envoie le devis chiffré par WhatsApp avec bouton de validation 1-clic., Ouvre le portail client dans un nouvel onglet. (+12 more)

### Community 2 - "models/__init__.py"
Cohesion: 0.08
Nodes (15): GarageInsuranceAmendment, Notification WhatsApp au client l'informant de l'accord expert et du montant…, Ouvre un lien WhatsApp direct vers l'expert., GarageUiKit, _build_stage2_subtask_defs(), GarageWorkshopOperator, GarageWorkshopStage, constrains (+7 more)

### Community 3 - "ProductTemplate"
Cohesion: 0.07
Nodes (9): GaragePartsBL, GaragePartsBLLine, ProductProduct, ProductTemplate, depends, onchange, Ouvre un nouveau Bon de Réception Fournisseur pré-rempli avec cet article., Assure l'existence d'un article storable Odoo pour permettre les mouvements de… (+1 more)

### Community 4 - "wizard/__init__.py"
Cohesion: 0.07
Nodes (13): GarageAiDiagnosticWizard, onchange, Pré-remplit les tâches extraites si des lignes sont saisies., Lance l'interprétation IA et la création des micro-tâches dynamiques…, GarageInsuranceInvoiceWizard, depends, Crée simultanément la facture d'assurance et la facture/reçu de franchise…, GarageOperatorPinWizard (+5 more)

### Community 5 - "GarageWorkshopTabletApiController"
Cohesion: 0.22
Nodes (9): GarageWorkshopTabletApiController, _json_response(), route, Valide une action sur tablette via code PIN opérateur., Helper pour retourner une réponse HTTP JSON avec en-têtes CORS., Fournit la liste complète des étapes et des véhicules actifs à l'atelier pour…, _reception_to_subtasks(), _reception_to_vehicle_card() (+1 more)

### Community 6 - "FleetVehicle"
Cohesion: 0.12
Nodes (8): FleetVehicle, constrains, depends, onchange, Décompose une plaque saisie manuellement en ses composantes Région / Lettre /…, Affiche un nom de véhicule lisible et élégant sans doublon de plaque., Met à jour l'immatriculation en temps réel dans le formulaire., Assemble la plaque au format canonique : Région | Lettre | Numéro (Ex: 26 | B |…

### Community 7 - "GarageBillingWizard"
Cohesion: 0.17
Nodes (6): GarageBillingWizard, GarageBillingWizardLine, depends, model_create_multi, onchange, Génère la proposition de panachage équivalent selon le stock fiscal disponible…

### Community 8 - "GaragePaymentRecoveryWizard"
Cohesion: 0.18
Nodes (7): GaragePaymentRecoveryWizard, depends, model, onchange, Crée la ligne d'historique de règlement et met à jour l'ordre de réparation., Valide l'encaissement. Si paiement bancaire ou demande facture, ouvre le moteur…, Met à jour le CIN ou l'ICE du partenaire s'il a été saisi au guichet.

### Community 9 - "GarageReception"
Cohesion: 0.17
Nodes (4): GarageReception, depends, model_create_multi, Génère et imprime le Bon de Travail / BL Atelier depuis la fiche réception.

### Community 10 - "GarageReceptionTask"
Cohesion: 0.18
Nodes (6): GarageReceptionTask, model_create_multi, Vérifie que seul le Mécanicien / Chef d'Atelier ou le Gérant peut modifier les…, Bascule l'état de la micro-tâche avec contrôle de rôle, progression…, Alias rétro-compatible pour la tablette et les flux existants., Ouvre la vue modale détaillée de la sous-tâche.

### Community 11 - "1. Views & Frontend Architecture"
Cohesion: 0.17
Nodes (11): 1. Views & Frontend Architecture, 2. Python ORM & Data Architecture, 3. Mandatory Pre-Flight Verification Protocol, A. Kanban Views (OWL 2), A. Relational Commands (One2many & Many2many), B. List Views, B. Security & ACLs, C. Manifest File (`__manifest__.py`) (+3 more)

### Community 12 - "GarageTrackingController"
Cohesion: 0.22
Nodes (5): GarageTrackingController, route, API appelée en 1 clic par le client sur son smartphone pour valider l'avis de…, Affiche le portail de suivi en temps réel du véhicule sans authentification…, API appelée en 1 clic par le client sur son smartphone pour valider le devis.

### Community 13 - "1. Commandes de Contrôle de la Base de Données (depuis le terminal hôte)"
Cohesion: 0.18
Nodes (10): 1. Commandes de Contrôle de la Base de Données (depuis le terminal hôte), 2. Standards Invariants Odoo 19, 3. Emplacement du Code Source Officiel Odoo 19 (Vérité Terrain), A. Accès Direct PostgreSQL (`psql`), B. Shell Interactif Python Odoo, C. Mise à jour et validation à chaud d'un module custom, D. Consultation des Logs en Temps Réel, Odoo 19 Developer & MCP Reference Guide (+2 more)

### Community 14 - "navbar_subnav.js"
Cohesion: 0.29
Nodes (5): GARAGE_MODULE_SUBNAVS, onNavBarDropdownItemSelection(), setup(), _syncGarageSubnav(), _updateTopNavActiveDom()

### Community 15 - ".write"
Cohesion: 0.22
Nodes (3): Action du Magasinier / Facturation : indique que le chiffrage est prêt., Action du Magasinier : indique que toutes les pièces sont physiquement à…, Vérifie si toutes les micro-tâches de l'étape sont achevées et avance…

### Community 16 - "ResPartner"
Cohesion: 0.22
Nodes (4): constrains, depends, onchange, ResPartner

### Community 17 - "ResUsers"
Cohesion: 0.25
Nodes (3): depends, onchange, ResUsers

### Community 18 - "3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL"
Cohesion: 0.25
Nodes (7): 1. COMPREHENSIVE COMPONENT WATCHLIST & BANNED PATTERNS, 2. GROUND TRUTH ENGINE: THE LIVE ODOO 19 CONTAINER, 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL, ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS, Step 1: Automated Module Upgrade & Schema Validation, Step 2: Python ORM View Compilation Test, Step 3: Deprecated Pattern Grep Audit

### Community 19 - "3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL"
Cohesion: 0.25
Nodes (7): 1. COMPREHENSIVE COMPONENT WATCHLIST & BANNED PATTERNS, 2. GROUND TRUTH ENGINE: THE LIVE ODOO 19 CONTAINER, 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL, ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS, Step 1: Automated Module Upgrade & Schema Validation, Step 2: Python ORM View Compilation Test, Step 3: Deprecated Pattern Grep Audit

### Community 20 - "3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL"
Cohesion: 0.25
Nodes (7): 1. COMPREHENSIVE COMPONENT WATCHLIST & BANNED PATTERNS, 2. GROUND TRUTH ENGINE: THE LIVE ODOO 19 CONTAINER, 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL, ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS, Step 1: Automated Module Upgrade & Schema Validation, Step 2: Python ORM View Compilation Test, Step 3: Deprecated Pattern Grep Audit

### Community 21 - ".action_send_whatsapp_tracking"
Cohesion: 0.29
Nodes (3): Envoie une notification WhatsApp rassurante et professionnelle au client avec…, Construit et envoie la notification WhatsApp avec le lien de suivi sécurisé., Ouvre le portail client dans un nouvel onglet pour prévisualisation.

### Community 22 - ".process_ai_diagnostic"
Cohesion: 0.33
Nodes (3): Génère la checklist micro-tâches complète (Étapes 1 à 6) selon la spécialité et…, Transmet la note de pièces au magasinier et fait basculer le statut vers…, Interprète le diagnostic mécanicien (audio ou texte Darija/Français) avec…

## Knowledge Gaps
- **37 isolated node(s):** `GARAGE_MODULE_SUBNAVS`, `GarageWorkshopStage`, `ResConfigSettings`, `GarageStockPickerWizardLine`, `graphify` (+32 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GarageReception` connect `GarageReception` to `.action_reception_send_whatsapp_quote`, `._compute_can_toggle_workshop_tasks`, `models/__init__.py`, `._onchange_vehicle_id`, `.submit_supplementary_diagnostic`, `._sync_subtasks_with_parent_stage`, `.write`, `.action_send_whatsapp_tracking`, `.process_ai_diagnostic`, `.action_create_or_view_repair_order`, `._read_group_stage_ids`, `.action_create_or_view_claim`, `.action_open_ai_diagnostic_wizard`, `.action_open_pin_wizard`, `.action_reception_open_billing_wizard`, `.action_reception_open_payment_wizard`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Why does `GarageInsuranceClaim` connect `GarageInsuranceClaim` to `models/__init__.py`?**
  _High betweenness centrality (0.161) - this node is a cross-community bridge._
- **Why does `RepairOrder` connect `RepairOrder` to `models/__init__.py`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **What connects `GARAGE_MODULE_SUBNAVS`, `GarageWorkshopStage`, `ResConfigSettings` to the rest of the system?**
  _37 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `GarageInsuranceClaim` be split into smaller, more focused modules?**
  _Cohesion score 0.05053191489361702 - nodes in this community are weakly interconnected._
- **Should `RepairOrder` be split into smaller, more focused modules?**
  _Cohesion score 0.051418439716312055 - nodes in this community are weakly interconnected._
- **Should `models/__init__.py` be split into smaller, more focused modules?**
  _Cohesion score 0.0761904761904762 - nodes in this community are weakly interconnected._