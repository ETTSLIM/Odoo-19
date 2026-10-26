# -*- coding: utf-8 -*-
{
    'name': 'Garage Repair Pro - Socle Atelier, Workflow 7 Étapes, Double Comptabilité & Sinistres',
    'version': '19.0.5.0.0',
    'category': 'Automotive/Garage',
    'summary': 'Workflow 7 Étapes, Pointage Opérateurs PIN Tablette, Gestion des Sinistres, Double Stock & Portail Client',
    'description': """
        Module professionnel pour Atelier Automobile / Garage au Maroc:
        ================================================================
        * Workflow Canonique 7 Étapes Atelier (Réception, Devis, Pièces, Atelier, Contrôle, Prêt, Livré)
        * 6 Spécialités Atelier & Checklists d'Opérations (Mécanique, Carrosserie, Électricité, Entretien, Clim, Pneu)
        * Pointage Opérateurs par Code PIN sur Compte Tablette Partagé d'Atelier
        * Avancement Automatique d'Étape dès que les micro-opérations sont validées
        * Pipeline Diagnostic ➔ Stock Magasinier ➔ Chiffrage Devis
        * Interlock de Sécurité Sinistre (Accord Expert & Validation Client obligatoires avant travaux)
        * Gestion des Sinistres Assurances & Cabinets d'Expertise Automobile (Wafa, RMA, Sanlam, AXA, Salmi)
        * Dossier Photo de Choc et Rapport d'Expertise Automobile Officiel (PDF normé)
        * Portail de Suivi Client en direct sur Smartphone via lien magique sans mot de passe
        * Validation en 1-Clic du devis client avec bascule immédiate en atelier
        * Passerelle WhatsApp API pour notifications automatiques à chaque étape
        * Double Stock : Stock Opérationnel (Physique) vs Stock Fiscal Déclaré
        * Moteur d'Équivalence Fiscale Hybride avec pilotage des pourcentages (Prestations / Fournitures)
        * Double flux Vente : Bon de Travail / BL Atelier convertible en Facture Fiscale Officielle (TVA 20%)
        * Double flux Achat : Bons de Réception Pièces (BL Fournisseurs) et imputation au coût de revient véhicule
        * Calcul automatique de la rentabilité réelle atelier
    """,
    'author': 'Senior Odoo Architect',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'fleet',
        'repair',
        'account',
        'stock',
    ],
    'data': [
        'security/garage_security.xml',
        'security/ir.model.access.csv',
        'data/stock_data.xml',
        'data/tax_data.xml',
        'data/ir_sequence_data.xml',
        'data/insurance_data.xml',
        'data/workshop_workflow_data.xml',
        'report/report_work_order_bl.xml',
        'report/report_insurance_claim_expert.xml',
        'report/report_insurance_franchise_receipt.xml',
        'data/mail_template_expert.xml',
        'wizard/garage_billing_wizard_views.xml',
        'wizard/garage_insurance_invoice_wizard_views.xml',
        'wizard/garage_payment_recovery_wizard_views.xml',
        'wizard/garage_stock_picker_wizard_views.xml',
        'wizard/garage_operator_pin_wizard_views.xml',
        'wizard/garage_ai_diagnostic_wizard_views.xml',
        'wizard/garage_photo_gallery_wizard_views.xml',
        'views/portal_tracking_templates.xml',
        'views/garage_diagnostic_log_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/garage_reception_views.xml',
        'views/garage_workshop_stage_views.xml',
        'views/res_partner_views.xml',
        'views/garage_insurance_claim_views.xml',
        'views/garage_repair_order_views.xml',
        'views/garage_parts_purchase_views.xml',
        'views/garage_ui_kit_views.xml',
        'views/res_users_views.xml',
        'views/res_config_settings_views.xml',
        'views/garage_tablet_pairing_views.xml',
        'views/menus.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
