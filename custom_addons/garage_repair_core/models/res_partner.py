# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Différenciation nette Particulier vs Société
    customer_type = fields.Selection([
        ('particulier', 'Client Particulier (Sans ICE)'),
        ('company', 'Société / Entreprise (ICE Obligatoire)'),
    ], string="Type de Client Atelier", default=lambda self: 'company' if self.is_company else 'particulier')

    # Rôle unifié pour l'assistant et l'équipe atelier (Option 1)
    partner_role = fields.Selection([
        ('customer_individual', 'Client Particulier'),
        ('customer_company', 'Client Société / Flotte'),
        ('parts_supplier', 'Fournisseur de Pièces'),
        ('insurance_company', "Compagnie d'Assurance"),
        ('expert_cabinet', "Cabinet d'Expertise"),
    ], string="Rôle / Type de Contact",
       compute='_compute_partner_role',
       inverse='_inverse_partner_role',
       default='customer_individual',
       store=True,
       tracking=True,
       help="Rôle unifié et simplifié du contact pour l'atelier")

    # Identifiants légaux et fiscaux Marocains
    ice = fields.Char(string="ICE", size=15, help="Identifiant Commun de l’Entreprise (15 chiffres obligatoires pour les sociétés au Maroc)")
    identifiant_fiscal = fields.Char(string="Identifiant Fiscal (IF)", help="Numéro d'immatriculation fiscale")
    registre_commerce = fields.Char(string="Registre de Commerce (RC)", help="Numéro du registre de commerce")
    patente = fields.Char(string="Patente", help="Numéro de taxe professionnelle")
    cin = fields.Char(string="CIN", help="Carte d'Identité Nationale (Pour les clients particuliers marocains)")

    # Catégorisation métier atelier
    is_insurance_company = fields.Boolean(string="Compagnie d'Assurance", default=False,
                                          help="Cocher si ce contact est une compagnie d'assurance (ex: Wafa, RMA, Saham, AXA)")
    is_expert_cabinet = fields.Boolean(string="Cabinet d'Expertise", default=False,
                                      help="Cocher si ce contact est un cabinet ou expert automobile assermenté")
    is_parts_supplier = fields.Boolean(string="Fournisseur Pièces Auto", default=False,
                                       help="Cocher si ce partenaire est un comptoir ou grossiste de pièces détachées")

    # Véhicules associés
    vehicle_ids = fields.One2many('fleet.vehicle', 'customer_id', string="Véhicules Possédés")
    vehicle_count = fields.Integer(string="Nombre de Véhicules", compute='_compute_vehicle_count')

    @api.depends('is_parts_supplier', 'is_insurance_company', 'is_expert_cabinet', 'customer_type', 'is_company')
    def _compute_partner_role(self):
        for partner in self:
            if partner.is_parts_supplier:
                partner.partner_role = 'parts_supplier'
            elif partner.is_insurance_company:
                partner.partner_role = 'insurance_company'
            elif partner.is_expert_cabinet:
                partner.partner_role = 'expert_cabinet'
            elif partner.customer_type == 'company' or partner.is_company:
                partner.partner_role = 'customer_company'
            else:
                partner.partner_role = 'customer_individual'

    def _inverse_partner_role(self):
        for partner in self:
            role = partner.partner_role
            if role == 'customer_individual':
                partner.customer_type = 'particulier'
                partner.is_company = False
                partner.is_parts_supplier = False
                partner.is_insurance_company = False
                partner.is_expert_cabinet = False
            elif role == 'customer_company':
                partner.customer_type = 'company'
                partner.is_company = True
                partner.is_parts_supplier = False
                partner.is_insurance_company = False
                partner.is_expert_cabinet = False
            elif role == 'parts_supplier':
                partner.customer_type = 'company'
                partner.is_company = True
                partner.is_parts_supplier = True
                partner.is_insurance_company = False
                partner.is_expert_cabinet = False
                if hasattr(partner, 'supplier_rank') and partner.supplier_rank < 1:
                    partner.supplier_rank = 1
            elif role == 'insurance_company':
                partner.customer_type = 'company'
                partner.is_company = True
                partner.is_parts_supplier = False
                partner.is_insurance_company = True
                partner.is_expert_cabinet = False
            elif role == 'expert_cabinet':
                partner.customer_type = 'company'
                partner.is_company = True
                partner.is_parts_supplier = False
                partner.is_insurance_company = False
                partner.is_expert_cabinet = True

    @api.onchange('partner_role')
    def _onchange_partner_role(self):
        role = self.partner_role
        if role == 'customer_individual':
            self.customer_type = 'particulier'
            self.is_company = False
            self.is_parts_supplier = False
            self.is_insurance_company = False
            self.is_expert_cabinet = False
        elif role == 'customer_company':
            self.customer_type = 'company'
            self.is_company = True
            self.is_parts_supplier = False
            self.is_insurance_company = False
            self.is_expert_cabinet = False
        elif role == 'parts_supplier':
            self.customer_type = 'company'
            self.is_company = True
            self.is_parts_supplier = True
            self.is_insurance_company = False
            self.is_expert_cabinet = False
        elif role == 'insurance_company':
            self.customer_type = 'company'
            self.is_company = True
            self.is_parts_supplier = False
            self.is_insurance_company = True
            self.is_expert_cabinet = False
        elif role == 'expert_cabinet':
            self.customer_type = 'company'
            self.is_company = True
            self.is_parts_supplier = False
            self.is_insurance_company = False
            self.is_expert_cabinet = True

    @api.onchange('is_company')
    def _onchange_is_company_set_customer_type(self):
        if self.is_company:
            self.customer_type = 'company'
        else:
            self.customer_type = 'particulier'

    @api.depends('vehicle_ids')
    def _compute_vehicle_count(self):
        for partner in self:
            partner.vehicle_count = len(partner.vehicle_ids)

    @api.constrains('ice', 'customer_type', 'is_company')
    def _check_ice_format(self):
        for partner in self:
            # L'ICE n'est contrôlé que s'il est renseigné ou si c'est explicitement une société
            if partner.ice:
                clean_ice = partner.ice.strip()
                if not (clean_ice.isdigit() and len(clean_ice) == 15):
                    raise ValidationError(_("L'ICE pour '%s' doit comporter exactement 15 chiffres. Valeur saisie: %s", partner.name, partner.ice))
            elif partner.customer_type == 'company' and partner.is_company and not partner.is_parts_supplier and not partner.is_insurance_company:
                # Avertissement ou validation souple pour ne pas bloquer les brouillons, mais signaler l'exigence
                pass

    def action_view_vehicles(self):
        self.ensure_one()
        return {
            'name': _("Véhicules de %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'view_mode': 'list,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }
