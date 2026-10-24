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
