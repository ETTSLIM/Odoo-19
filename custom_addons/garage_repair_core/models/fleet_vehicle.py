# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Nomenclature officielle NARSA (Ministère du Transport & Logistique)
# Correspondance Lettres Arabes -> Lettres Latines pour immatriculation marocaine
ARABIC_TO_LATIN_PLATE = {
    'أ': 'A', 'ا': 'A', 'آ': 'A', 'إ': 'A',
    'ب': 'B',
    'د': 'D',
    'ه': 'H', 'هـ': 'H', 'ة': 'H',
    'و': 'E',
    'ط': 'T',
    'ي': 'Y', 'ى': 'Y',
    'ك': 'K',
    'ل': 'L',
    'م': 'M',
    'ن': 'N',
    'ص': 'C',
    'ف': 'F',
    'ر': 'R',
    'س': 'S',
}

PLATE_LETTERS_SELECTION = [
    ('A', 'A (أ)'),
    ('B', 'B (ب)'),
    ('D', 'D (د)'),
    ('H', 'H (هـ)'),
    ('E', 'E (و)'),
    ('T', 'T (ط)'),
    ('Y', 'Y (ي)'),
    ('K', 'K (ك)'),
    ('L', 'L (ل)'),
    ('M', 'M (م)'),
    ('N', 'N (ن)'),
    ('C', 'C (ص)'),
    ('F', 'F (ف)'),
    ('R', 'R (ر)'),
    ('S', 'S (س)'),
]

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    # Types d'immatriculation pour couvrir tous les cas marocains et internationaux
    plate_type = fields.Selection([
        ('standard', 'Standard Marocain (Ex: 26 | B | 234556)'),
        ('ww', 'Garage / Transit WW (Ex: WW-123456)'),
        ('state', 'État / Services Publics (Ex: 123456-M)'),
        ('diplomatic', 'Corps Diplomatique / Consulaire (CD / CC / CMD)'),
        ('foreign', 'Immatriculation Étrangère / MRE / Autre'),
    ], string="Type d'immatriculation", default='standard', required=True)

    # Composantes pour le format standard marocain : Région | Lettre | Numéro (Ex: 26 | B | 234556)
    plate_region_part = fields.Char(string="Code Région", help="Code Préfecture / Province (ex: 26 Marrakech, 6 Casa-Anfa, 1 Rabat)")
    plate_letter_part = fields.Selection(PLATE_LETTERS_SELECTION, string="Série (Lettre)", help="Lettre de série normalisée NARSA (A à S)")
    plate_number_part = fields.Char(string="Numéro d'Ordre", help="Numéro d'ordre jusqu'à 6 chiffres (ex: 234556)")

    # Immatriculation calculée et stockée avec synchronisation bi-directionnelle
    license_plate = fields.Char(
        compute='_compute_license_plate',
        inverse='_inverse_license_plate',
        store=True,
        tracking=True,
        string="Immatriculation"
    )

    # Numéro de châssis / VIN normalisé
    vin_number = fields.Char(string="Numéro de Châssis (VIN)", size=17, copy=False,
                             help="Numéro d'identification du véhicule (17 caractères)")

    # Caractéristiques techniques atelier
    engine_code = fields.Char(string="Code Moteur", help="Ex: 1.6 TDI, 2.0 HDi, N47, 1.5 dCi")
    color_car = fields.Char(string="Couleur Carrosserie")
    transmission = fields.Selection(
        selection_add=[('robotized', 'Automatisée / Double Embrayage')],
        ondelete={'robotized': 'set null'}
    )

    # Propriétaire & Historique atelier
    customer_id = fields.Many2one('res.partner', string="Propriétaire / Client", tracking=True)
    reception_ids = fields.One2many('garage.reception', 'vehicle_id', string="Historique Réceptions")
    reception_count = fields.Integer(string="Nombre de réceptions", compute='_compute_reception_count')
    claim_ids = fields.One2many('garage.insurance.claim', 'vehicle_id', string="Dossiers Sinistres")
    claim_count = fields.Integer(string="Nb. Sinistres", compute='_compute_claim_count')
    repair_order_ids = fields.One2many('repair.order', 'vehicle_id', string="Ordres de Réparation")
    repair_order_count = fields.Integer(string="Nb. OR", compute='_compute_repair_order_count')

    @api.depends('plate_type', 'plate_region_part', 'plate_letter_part', 'plate_number_part')
    def _compute_license_plate(self):
        """Assemble la plaque au format canonique : Région | Lettre | Numéro (Ex: 26 | B | 234556)."""
        for vehicle in self:
            if vehicle.plate_type == 'standard':
                reg = (vehicle.plate_region_part or '').strip()
                let = (vehicle.plate_letter_part or '').strip()
                num = (vehicle.plate_number_part or '').strip()
                if reg and let and num:
                    vehicle.license_plate = f"{reg} | {let} | {num}"
                elif any([reg, let, num]):
                    parts = [p for p in [reg, let, num] if p]
                    vehicle.license_plate = " | ".join(parts)
            elif not vehicle.license_plate:
                vehicle.license_plate = False

    def _inverse_license_plate(self):
        """Décompose une plaque saisie manuellement en ses composantes Région / Lettre / Numéro."""
        for vehicle in self:
            if not vehicle.license_plate:
                continue
            plate = vehicle.license_plate.strip()
            if vehicle.plate_type == 'standard' and ('|' in plate or '-' in plate or ' ' in plate):
                parts = [p.strip() for p in re.split(r'[\s\|\-]+', plate) if p.strip()]
                if len(parts) == 3:
                    p1, p2, p3 = parts[0], parts[1], parts[2]
                    # Conversion arabe -> latin si présent
                    p2_latin = ARABIC_TO_LATIN_PLATE.get(p2, p2.upper())

                    # Cas 1 : Nouveau format standard Région | Lettre | Numéro (ex: 26 | B | 234556)
                    if p1.isdigit() and int(p1) <= 89 and p3.isdigit() and len(p3) >= len(p1):
                        vehicle.plate_region_part = p1
                        vehicle.plate_letter_part = p2_latin if p2_latin in dict(PLATE_LETTERS_SELECTION) else False
                        vehicle.plate_number_part = p3
                    # Cas 2 : Format hérité Numéro | Lettre | Région (ex: 45812 | A | 6)
                    elif p3.isdigit() and int(p3) <= 89 and p1.isdigit():
                        vehicle.plate_region_part = p3
                        vehicle.plate_letter_part = p2_latin if p2_latin in dict(PLATE_LETTERS_SELECTION) else False
                        vehicle.plate_number_part = p1

    def _compute_display_name(self):
        """Affiche un nom de véhicule lisible et élégant sans doublon de plaque."""
        for vehicle in self:
            brand = vehicle.model_id.brand_id.name or ''
            model = vehicle.model_id.name or ''
            model_info = f"{brand} {model}".strip() if (brand or model) else (vehicle.name or '')
            if vehicle.license_plate:
                vehicle.display_name = f"{model_info} • {vehicle.license_plate}" if model_info else vehicle.license_plate
            else:
                vehicle.display_name = model_info or vehicle.name or _("Nouveau Véhicule")

    @api.depends('reception_ids')
    def _compute_reception_count(self):
        for record in self:
            record.reception_count = len(record.reception_ids)

    @api.depends('claim_ids')
    def _compute_claim_count(self):
        for record in self:
            record.claim_count = len(record.claim_ids)

    @api.depends('repair_order_ids')
    def _compute_repair_order_count(self):
        for record in self:
            record.repair_order_count = len(record.repair_order_ids)

    @api.onchange('plate_type', 'plate_region_part', 'plate_letter_part', 'plate_number_part')
    def _onchange_standard_plate(self):
        """Met à jour l'immatriculation en temps réel dans le formulaire."""
        if self.plate_type == 'standard':
            parts = [p.strip() for p in [self.plate_region_part, self.plate_letter_part, self.plate_number_part] if p]
            if len(parts) == 3:
                self.license_plate = f"{parts[0]} | {parts[1]} | {parts[2]}"
            elif parts:
                self.license_plate = " | ".join(parts)

    @api.constrains('vin_number')
    def _check_vin_number(self):
        for record in self:
            if record.vin_number:
                clean_vin = re.sub(r'[\s\-]', '', record.vin_number).upper()
                if len(clean_vin) != 17:
                    raise ValidationError(_("Le numéro VIN (Châssis) doit comporter exactement 17 caractères alphanumériques. (Reçu: %s)", len(clean_vin)))

    def action_view_receptions(self):
        self.ensure_one()
        return {
            'name': _("Dossiers de Réception - %s", self.name or self.license_plate),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.reception',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_customer_id': self.customer_id.id},
        }

    def action_view_claims(self):
        self.ensure_one()
        return {
            'name': _("Dossiers Sinistres - %s", self.name or self.license_plate),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.insurance.claim',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_customer_id': self.customer_id.id},
        }

    def action_view_repair_orders(self):
        self.ensure_one()
        return {
            'name': _("Ordres de Réparation - %s", self.name or self.license_plate),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id, 'default_partner_id': self.customer_id.id},
        }
