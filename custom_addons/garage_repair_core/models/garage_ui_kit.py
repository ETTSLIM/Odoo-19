# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _

class GarageUiKit(models.TransientModel):
    _name = 'garage.ui.kit'
    _description = 'Garage Pro Design System & UI Kit Debugger'

    name = fields.Char(string="Titre du Test", default="Spécimen Composants Design System UI Kit")

    # Workflow Statusbar Specimen
    stage_demo = fields.Selection([
        ('reception', 'Réception'),
        ('devis', 'Devis & Accord'),
        ('pieces', 'Commande Pièces'),
        ('travaux', 'Travaux Atelier'),
        ('controle', 'Contrôle Qualité'),
        ('prete', 'Véhicule Prêt'),
        ('livree', 'Livré & Clôturé'),
    ], string="Étape Atelier", default='devis')

    # 1. Inputs classiques
    char_input = fields.Char(string="Champ Texte Simple", default="Valeur éditable standard")
    char_required = fields.Char(string="Champ Requis Rempli", default="Champ obligatoire rempli")
    char_empty_required = fields.Char(string="Champ Requis Vide")
    char_readonly = fields.Char(string="Champ Lecture Seule", readonly=True, default="Texte figé non modifiable")
    integer_input = fields.Integer(string="Nombre Entier", default=1250)
    float_input = fields.Float(string="Nombre Décimal", default=84.50)

    # 2. Monétaire & Devise (Normalisé en MAD / DH)
    def _default_currency_id(self):
        mad = self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'MAD')], limit=1)
        return mad.id if mad else self.env.company.currency_id.id

    currency_id = fields.Many2one('res.currency', string="Devise", default=_default_currency_id)
    monetary_input = fields.Monetary(string="Montant Monétaire", currency_field='currency_id', default=4500.0)

    # 3. Dates
    date_input = fields.Date(string="Sélecteur Date", default=fields.Date.context_today)
    datetime_input = fields.Datetime(string="Date & Heure", default=fields.Datetime.now)

    # 4. Relations Many2one & Many2many
    partner_id = fields.Many2one('res.partner', string="Client / Partenaire (Many2one)", default=lambda self: self.env.user.partner_id)
    
    def _default_vehicle_id(self):
        return self.env['fleet.vehicle'].search([], limit=1).id

    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule Atelier", default=_default_vehicle_id, help="Sélection d'un véhicule")

    def _default_tag_ids(self):
        tags = self.env['res.partner.category'].search([], limit=2)
        if not tags:
            tag1 = self.env['res.partner.category'].create({'name': 'Client VIP', 'color': 1})
            tag2 = self.env['res.partner.category'].create({'name': 'Flotte Pro', 'color': 2})
            tags = tag1 + tag2
        return [Command.set(tags.ids)] if tags else False

    tag_ids = fields.Many2many('res.partner.category', string="Tags & Badges (M2M)", default=_default_tag_ids)

    # 5. Sélections & Listes déroulantes
    selection_dropdown = fields.Selection([
        ('opt1', 'Option Alpha (Recommandée)'),
        ('opt2', 'Option Bêta (Standard)'),
        ('opt3', 'Option Gamma (Avancée)'),
    ], string="Menu Déroulant (Selection)", default='opt1')

    # 6. Radio & Segmented Controls
    fuel_level_demo = fields.Selection([
        ('0', '0% (Réserve)'),
        ('25', '25% (1/4)'),
        ('50', '50% (1/2)'),
        ('75', '75% (3/4)'),
        ('100', '100% (Plein)'),
    ], string="Segmented Control (Radio Horizontal)", default='25')

    vertical_radio = fields.Selection([
        ('urgent', 'Intervention Prioritaire / Urgence'),
        ('normal', 'Intervention Standard Planifiée'),
        ('maintenance', 'Maintenance Préventive'),
    ], string="Boutons Radio Verticaux", default='urgent')

    # 7. Booleans & Toggles
    boolean_checkbox = fields.Boolean(string="Case à Cocher (Checkbox 18x18)", default=True)
    boolean_toggle = fields.Boolean(string="Interrupteur à Bascule (Toggle)", default=True)

    # 8. Indicateurs, KPIs & Progression
    progress_val = fields.Float(string="Barre de Progression", default=65.0)
    stock_status_badge = fields.Selection([
        ('dispo', 'Pièces Disponibles'),
        ('attente', 'En Attente Fournisseur'),
        ('alerte', 'Rupture de Stock'),
    ], string="Badge de Statut", default='dispo')

    # 9. Plaque Marocaine
    license_plate_demo = fields.Char(string="Immatriculation Marocaine", default="26 | B | 234556")
    license_plate_casa = fields.Char(string="Immatriculation Casablanca", default="6 | A | 45812")

    # 10. Texte long
    text_multiline = fields.Text(string="Zone de Texte Multi-lignes", default="Observation technique :\nContrôle complet des freins, disques et rotules effectué.")

    def action_test_primary(self):
        return True

    def action_test_secondary(self):
        return True
