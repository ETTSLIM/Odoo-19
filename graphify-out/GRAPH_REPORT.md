# Graph Report - Odoo 19  (2026-10-27)

## Corpus Check
- 49 files · ~44,795 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 584 nodes · 772 edges · 80 communities (33 shown, 47 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `1f80ced6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- .write
- RepairOrder
- models/__init__.py
- ProductTemplate
- GaragePaymentRecoveryWizard
- GarageWorkshopTabletApiController
- FleetVehicle
- .action_open_ai_diagnostic_wizard
- ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS
- GarageReception
- GarageReceptionTask
- 1. Views & Frontend Architecture
- GarageBillingWizard
- 1. Commandes de Contrôle de la Base de Données (depuis le terminal hôte)
- navbar_subnav.js
- .write
- ResPartner
- ResUsers
- .action_reception_open_payment_wizard
- 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL
- GaragePhotoGalleryWizard
- .action_smart_whatsapp
- GarageTrackingController
- .action_create_or_view_repair_order
- ._read_group_stage_ids
- graphify — Universal P0 Invariant
- workflows/graphify.md
- .action_reception_open_billing_wizard
- .action_create_or_view_claim
- .create
- GarageInsuranceClaim
- .action_reception_print_bl
- onchange
- .action_mark_parts_partial
- .action_generate_specialty_checklist
- ._compute_can_toggle_workshop_tasks
- graphify — Universal P0 Invariant
- plan_fidelity.md
- .action_client_approve_expert
- GarageDiagnosticLog
- GarageRepairPartLine
- .action_send_whatsapp_quote
- .action_import_from_diagnostic_logs
- .action_mark_parts_available
- .action_client_approve
- .action_open_pin_wizard
- GarageRepairLaborLine
- GarageRepairPayment
- .action_repair_end
- .action_view_parts_bl
- .action_view_reception
- .action_generate_bl
- .action_open_billing_wizard
- .action_view_claim
- .action_open_payment_recovery_wizard
- .action_open_stock_picker_wizard
- .agents/rules/android_client.md
- .gemini/rules/android_client.md
- .create
- .action_open_split_invoicing_wizard
- .action_print_expert_report
- .action_print_franchise_receipt
- .action_view_amendments
- .action_view_attachments
- .action_view_invoices
- .action_view_reception
- .action_view_repair_order
- ._onchange_vehicle_id
- deploy_to_hetzner.sh
- Git Push & Remote Hostinger Staging Invariant
- GarageStockPickerWizard
- .submit_supplementary_diagnostic
- ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS
- GarageAiDiagnosticWizard
- cockpit_submodule_sync.md

## God Nodes (most connected - your core abstractions)
1. `GarageReception` - 63 edges
2. `GarageInsuranceClaim` - 40 edges
3. `RepairOrder` - 30 edges
4. `GarageWorkshopTabletApiController` - 18 edges
5. `_json_response()` - 17 edges
6. `FleetVehicle` - 17 edges
7. `GaragePhotoGalleryWizard` - 14 edges
8. `send_garage_whatsapp()` - 11 edges
9. `ProductTemplate` - 10 edges
10. `GarageBillingWizard` - 10 edges

## Surprising Connections (you probably didn't know these)
- None detected - all connections are within the same source files.

## Import Cycles
- None detected.

## Communities (80 total, 47 thin omitted)

### Community 0 - ".write"
Cohesion: 0.14
Nodes (6): GarageInsuranceAmendment, Transmet le dossier et photos à l'expert., Passe le dossier en examen / contre-visite expert., Ouvre un dialogue pour saisir un nouvel avenant pour pièces cachées., Valide le Bon d'Accord Définitif de l'Expert., Marque les réparations terminées.

### Community 2 - "models/__init__.py"
Cohesion: 0.07
Nodes (18): GarageDamageItem, depends, Notification WhatsApp au client l'informant de l'accord expert et du montant…, Ouvre un lien WhatsApp direct vers l'expert., Ouvre un lien WhatsApp direct vers le client adapté à l'état du sinistre., GarageUiKit, _build_stage2_subtask_defs(), GarageWorkshopOperator (+10 more)

### Community 3 - "ProductTemplate"
Cohesion: 0.07
Nodes (9): GaragePartsBL, GaragePartsBLLine, ProductProduct, ProductTemplate, depends, onchange, Ouvre un nouveau Bon de Réception Fournisseur pré-rempli avec cet article., Assure l'existence d'un article storable Odoo pour permettre les mouvements de… (+1 more)

### Community 4 - "GaragePaymentRecoveryWizard"
Cohesion: 0.18
Nodes (7): GaragePaymentRecoveryWizard, depends, model, onchange, Crée la ligne d'historique de règlement et met à jour l'ordre de réparation., Valide l'encaissement. Si paiement bancaire ou demande facture, ouvre le moteur…, Met à jour le CIN ou l'ICE du partenaire s'il a été saisi au guichet.

### Community 5 - "GarageWorkshopTabletApiController"
Cohesion: 0.19
Nodes (9): GarageWorkshopTabletApiController, _json_response(), route, Fournit la liste complète des étapes et des véhicules actifs à l'atelier pour…, Valide une action sur tablette via code PIN opérateur., Helper pour retourner une réponse HTTP JSON avec en-têtes CORS., _reception_to_subtasks(), _reception_to_vehicle_card() (+1 more)

### Community 6 - "FleetVehicle"
Cohesion: 0.10
Nodes (9): FleetVehicle, constrains, depends, onchange, Normalise et décompose une immatriculation marocaine en gérant : - Les…, Assemble la plaque au format standard marocain canonique : Numéro | Lettre |…, Décompose une plaque saisie manuellement (arabe ou latin) en ses composantes…, Affiche un nom de véhicule lisible et élégant sans doublon de marque ni de… (+1 more)

### Community 8 - "ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS"
Cohesion: 0.22
Nodes (8): 1. COMPREHENSIVE COMPONENT WATCHLIST & BANNED PATTERNS, 2. GROUND TRUTH ENGINE: THE LIVE ODOO 19 CONTAINER, 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL, 4. MANDATORY GIT PUSH PROTOCOL (HOSTINGER STAGING SYNC), ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS, Step 1: Automated Module Upgrade & Schema Validation, Step 2: Python ORM View Compilation Test, Step 3: Deprecated Pattern Grep Audit

### Community 9 - "GarageReception"
Cohesion: 0.10
Nodes (5): GarageReception, depends, Génère une grille 4 sous 4 des photos du véhicule, avec slots canoniques…, Génère une matrice 4x4 compacte des photos et documents d'accueil pour la barre…, Génère la liste en lecture seule des micro-tâches issues du diagnostic…

### Community 10 - "GarageReceptionTask"
Cohesion: 0.18
Nodes (6): GarageReceptionTask, model_create_multi, Vérifie que seul le Mécanicien / Chef d'Atelier ou le Gérant peut modifier les…, Bascule ou applique l'état de la micro-tâche avec contrôle de rôle, progression…, Alias rétro-compatible pour la tablette et les flux existants., Ouvre la vue modale détaillée de la sous-tâche.

### Community 11 - "1. Views & Frontend Architecture"
Cohesion: 0.17
Nodes (11): 1. Views & Frontend Architecture, 2. Python ORM & Data Architecture, 3. Mandatory Pre-Flight Verification Protocol, A. Kanban Views (OWL 2), A. Relational Commands (One2many & Many2many), B. List Views, B. Security & ACLs, C. Manifest File (`__manifest__.py`) (+3 more)

### Community 12 - "GarageBillingWizard"
Cohesion: 0.17
Nodes (6): GarageBillingWizard, GarageBillingWizardLine, depends, model_create_multi, onchange, Génère la proposition de panachage équivalent selon le stock fiscal disponible…

### Community 13 - "1. Commandes de Contrôle de la Base de Données (depuis le terminal hôte)"
Cohesion: 0.18
Nodes (10): 1. Commandes de Contrôle de la Base de Données (depuis le terminal hôte), 2. Standards Invariants Odoo 19, 3. Emplacement du Code Source Officiel Odoo 19 (Vérité Terrain), A. Accès Direct PostgreSQL (`psql`), B. Shell Interactif Python Odoo, C. Mise à jour et validation à chaud d'un module custom, D. Consultation des Logs en Temps Réel, Odoo 19 Developer & MCP Reference Guide (+2 more)

### Community 14 - "navbar_subnav.js"
Cohesion: 0.27
Nodes (7): _alignSubnavUnderActiveModule(), GARAGE_MODULE_SUBNAVS, onGarageSubnavPillClick(), onNavBarDropdownItemSelection(), setup(), _syncGarageSubnav(), _updateTopNavActiveDom()

### Community 15 - ".write"
Cohesion: 0.10
Nodes (10): Action du Magasinier / Facturation : indique que le chiffrage est prêt., Action Magasinier : indique que les premières pièces nécessaires sont arrivées…, Action du Magasinier : indique que toutes les pièces sont physiquement à…, Enregistre l'accord client directement depuis la réception et fait progresser…, Étape 10 -> Étape 20 : Valide l'accueil et transmet le véhicule au magasinier…, Étape 20 -> Étape 30 : Le devis est prêt, passe à l'étape d'accord client /…, Étape 30 -> Étape 40 : L'accord est validé, démarre officiellement les travaux…, Étape 40 -> Étape 50 : Travaux terminés, passe en contrôle qualité. (+2 more)

### Community 16 - "ResPartner"
Cohesion: 0.20
Nodes (4): constrains, depends, onchange, ResPartner

### Community 17 - "ResUsers"
Cohesion: 0.25
Nodes (3): depends, onchange, ResUsers

### Community 19 - "3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL"
Cohesion: 0.25
Nodes (7): 1. COMPREHENSIVE COMPONENT WATCHLIST & BANNED PATTERNS, 2. GROUND TRUTH ENGINE: THE LIVE ODOO 19 CONTAINER, 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL, ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS, Step 1: Automated Module Upgrade & Schema Validation, Step 2: Python ORM View Compilation Test, Step 3: Deprecated Pattern Grep Audit

### Community 20 - "GaragePhotoGalleryWizard"
Cohesion: 0.08
Nodes (9): GarageInsuranceInvoiceWizard, depends, Crée simultanément la facture d'assurance et la facture/reçu de franchise…, GarageOperatorPinWizard, model, GaragePhotoGalleryWizard, depends, GarageTabletPairingWizard (+1 more)

### Community 21 - ".action_smart_whatsapp"
Cohesion: 0.20
Nodes (5): Délègue l'envoi du devis WhatsApp à l'ordre de réparation lié., Envoie une notification WhatsApp rassurante et professionnelle au client avec…, Construit et envoie la notification WhatsApp avec le lien de suivi sécurisé., Ouvre le portail client dans un nouvel onglet pour prévisualisation., Action WhatsApp contextuelle intelligente selon l'étape actuelle du véhicule…

### Community 22 - "GarageTrackingController"
Cohesion: 0.28
Nodes (5): GarageTrackingController, route, API appelée en 1 clic par le client sur son smartphone pour valider le devis., API appelée en 1 clic par le client sur son smartphone pour valider l'avis de…, Affiche le portail de suivi en temps réel du véhicule sans authentification…

### Community 23 - ".action_create_or_view_repair_order"
Cohesion: 0.20
Nodes (5): Ouvre ou crée l'ordre de réparation associé sans forcer de lignes arbitraires., Action rapide Magasinier : Ouvre le chiffrage de l'ordre de réparation avec…, Ouvre l'ordre de réparation associé à cette fiche de réception., Importe et convertit en 1 clic les micro-tâches détectées par le diagnostic…, Ouvre le wizard de sélection de pièces du stock pour ce dossier.

### Community 35 - ".action_generate_specialty_checklist"
Cohesion: 0.25
Nodes (4): Génère la checklist micro-tâches complète (Étapes 1 à 6) selon la spécialité et…, Transmet la note de pièces au magasinier et fait basculer le statut vers…, Interprète le diagnostic mécanicien (audio ou texte Darija/Français) avec…, Réinitialise la checklist en purgeant les tâches non commencées d'une ancienne…

### Community 44 - "GarageDiagnosticLog"
Cohesion: 0.17
Nodes (6): GarageDiagnosticLog, GarageDiagnosticLogTask, depends, model_create_multi, onchange, Valide les micro-tâches sélectionnées par le magasinier et propage vers l'OR et…

### Community 45 - "GarageRepairPartLine"
Cohesion: 0.25
Nodes (4): GarageRepairPartLine, model_create_multi, Génère le mouvement réel de sortie de stock (Opérationnel ou Fiscal) lors de…, Restitue le stock physique en rayon si une ligne de pièce non facturée est…

### Community 46 - ".action_send_whatsapp_quote"
Cohesion: 0.29
Nodes (3): Action explicite du Magasinier : valide le chiffrage, passe la réception à…, Envoie le devis chiffré par WhatsApp avec bouton de validation 1-clic., Ouvre le portail client dans un nouvel onglet.

### Community 75 - "GarageStockPickerWizard"
Cohesion: 0.28
Nodes (4): GarageStockPickerWizard, GarageStockPickerWizardLine, model, onchange

### Community 77 - "ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS"
Cohesion: 0.22
Nodes (8): 1. COMPREHENSIVE COMPONENT WATCHLIST & BANNED PATTERNS, 2. GROUND TRUTH ENGINE: THE LIVE ODOO 19 CONTAINER, 3. MANDATORY 3-STEP PRE-FLIGHT VERIFICATION PROTOCOL, 4. MANDATORY GIT PUSH PROTOCOL (HOSTINGER STAGING SYNC), ODOO 19 ARCHITECTURAL LOCK & AGENT INVARIANTS, Step 1: Automated Module Upgrade & Schema Validation, Step 2: Python ORM View Compilation Test, Step 3: Deprecated Pattern Grep Audit

### Community 78 - "GarageAiDiagnosticWizard"
Cohesion: 0.25
Nodes (4): GarageAiDiagnosticWizard, onchange, Pré-remplit les tâches extraites si des lignes sont saisies., Lance l'interprétation IA et la création des micro-tâches dynamiques…

## Knowledge Gaps
- **44 isolated node(s):** `GARAGE_MODULE_SUBNAVS`, `ResConfigSettings`, `GarageStockPickerWizardLine`, `deploy_to_hetzner.sh script`, `CANONICAL ANDROID WORKSHOP TABLET CLIENT RULE & GRAPHIFY INVARIANT` (+39 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **47 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GarageReception` connect `GarageReception` to `.action_reception_print_bl`, `models/__init__.py`, `.action_generate_specialty_checklist`, `._compute_can_toggle_workshop_tasks`, `.action_open_ai_diagnostic_wizard`, `._onchange_vehicle_id`, `.submit_supplementary_diagnostic`, `.write`, `.action_open_pin_wizard`, `.action_reception_open_payment_wizard`, `.action_smart_whatsapp`, `.action_create_or_view_repair_order`, `._read_group_stage_ids`, `.action_reception_open_billing_wizard`, `.action_create_or_view_claim`, `.create`?**
  _High betweenness centrality (0.247) - this node is a cross-community bridge._
- **Why does `GarageInsuranceClaim` connect `GarageInsuranceClaim` to `.write`, `.action_open_split_invoicing_wizard`, `models/__init__.py`, `.action_print_expert_report`, `.action_print_franchise_receipt`, `.action_view_amendments`, `.action_view_attachments`, `.action_view_invoices`, `.action_view_reception`, `.action_view_repair_order`, `onchange`, `.action_client_approve_expert`, `.create`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `RepairOrder` connect `RepairOrder` to `models/__init__.py`, `.action_mark_parts_partial`, `GarageRepairPartLine`, `.action_send_whatsapp_quote`, `.action_import_from_diagnostic_logs`, `.action_mark_parts_available`, `.action_client_approve`, `GarageRepairLaborLine`, `.action_repair_end`, `.action_view_parts_bl`, `.action_view_reception`, `.action_generate_bl`, `.action_open_billing_wizard`, `.action_view_claim`, `.action_open_payment_recovery_wizard`, `.action_open_stock_picker_wizard`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **What connects `GARAGE_MODULE_SUBNAVS`, `ResConfigSettings`, `GarageStockPickerWizardLine` to the rest of the system?**
  _44 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `.write` be split into smaller, more focused modules?**
  _Cohesion score 0.14166666666666666 - nodes in this community are weakly interconnected._
- **Should `models/__init__.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06794871794871794 - nodes in this community are weakly interconnected._
- **Should `ProductTemplate` be split into smaller, more focused modules?**
  _Cohesion score 0.06890756302521009 - nodes in this community are weakly interconnected._