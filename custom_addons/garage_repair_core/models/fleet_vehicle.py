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
    'ش': 'CH',
    'ج': 'J',
    'ح': 'H',
    'خ': 'KH',
    'ع': 'A',
    'غ': 'GH',
    'ق': 'Q',
    'ز': 'Z',
    'ت': 'T',
    'ث': 'TH',
    'ض': 'D',
    'ظ': 'Z',
}

LATIN_TO_ARABIC_PLATE = {
    'A': 'أ',
    'B': 'ب',
    'D': 'د',
    'H': 'هـ',
    'E': 'و',
    'W': 'و',
    'T': 'ط',
    'Y': 'ي',
    'K': 'ك',
    'L': 'ل',
    'M': 'م',
    'N': 'ن',
    'C': 'ص',
    'F': 'ف',
    'R': 'ر',
    'S': 'س',
    'CH': 'ش',
    'J': 'ج',
    'KH': 'خ',
    'Q': 'ق',
    'Z': 'ز',
}

EASTERN_ARABIC_DIGITS = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
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
    ('CH', 'CH (ش)'),
    ('J', 'J (ج)'),
    ('KH', 'KH (خ)'),
    ('Q', 'Q (ق)'),
    ('Z', 'Z (ز)'),
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

    # Composantes pour le format standard marocain : Numéro | Lettre | Région (Ex: 12345 | A | 6)
    plate_region_part = fields.Char(string="Code Région", help="Code Préfecture / Province (ex: 26 Marrakech, 6 Casa-Anfa, 1 Rabat)")
    plate_letter_part = fields.Selection(PLATE_LETTERS_SELECTION, string="Série (Lettre)", help="Lettre de série normalisée NARSA (A à Z)")
    plate_letter_arabic = fields.Char(string="Lettre Arabe", compute='_compute_plate_letter_arabic', store=True)
    plate_number_part = fields.Char(string="Numéro d'Ordre", help="Numéro d'ordre jusqu'à 6 chiffres (ex: 234556)")

    # Immatriculation calculée et stockée avec synchronisation bi-directionnelle
    license_plate = fields.Char(
        compute='_compute_license_plate',
        inverse='_inverse_license_plate',
        store=True,
        tracking=True,
        string="Immatriculation"
    )
    license_plate_display = fields.Char(
        string="Plaque Bilingue (Arabe/Latin)",
        compute='_compute_license_plate_display',
        store=True
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
    damage_item_ids = fields.One2many('garage.damage.item', 'vehicle_id', string="Historique Dégâts & Chocs")
    damage_item_count = fields.Integer(string="Nb. Dégâts", compute='_compute_damage_item_count')

    @classmethod
    def normalize_moroccan_plate(cls, plate_str):
        """Normalise et décompose une immatriculation marocaine en gérant :
        - Les caractères arabes (أ, ب, د, هـ, etc.) ou latins (A, B, D, etc.)
        - Les chiffres arabes orientaux (٠-٩) convertis en chiffres standards
        - Les différents séparateurs (| , - , / , espaces)
        - Les ordres Numéro-Lettre-Région ou Région-Lettre-Numéro
        Retourne (num_part, latin_letter, arabic_letter, region_part, canonical_plate)
        """
        if not plate_str:
            return '', '', '', '', ''
        s = str(plate_str).strip()
        for ar_d, la_d in EASTERN_ARABIC_DIGITS.items():
            s = s.replace(ar_d, la_d)

        # Remplacement direct des lettres arabes isolées ou entourées d'espaces/délimiteurs
        parts = [p.strip() for p in re.split(r'[\s\|\-\./]+', s) if p.strip()]
        if len(parts) >= 3:
            p1, p2, p3 = parts[0], parts[1], parts[2]
            p2_clean = p2.strip()
            latin_letter = ARABIC_TO_LATIN_PLATE.get(p2_clean, p2_clean.upper())
            arabic_letter = LATIN_TO_ARABIC_PLATE.get(latin_letter, p2_clean)

            # Cas 1 : Format standard Numéro | Lettre | Région (ex: 12345 | A | 6 ou 12345 | أ | 6)
            if p1.isdigit() and p3.isdigit() and int(p3) <= 89 and (int(p1) > 89 or len(p1) >= len(p3)):
                num = p1
                reg = p3
                canonical = f"{num} | {latin_letter} | {reg}"
                return num, latin_letter, arabic_letter, reg, canonical
            # Cas 2 : Format inversé Région | Lettre | Numéro (ex: 6 | A | 12345 ou 26 | B | 234556)
            elif p1.isdigit() and p3.isdigit() and int(p1) <= 89:
                reg = p1
                num = p3
                canonical = f"{num} | {latin_letter} | {reg}"
                return num, latin_letter, arabic_letter, reg, canonical

        # Si 1 seul bloc contenant une lettre au milieu (ex: 12345-A-6 ou 12345A6)
        m = re.match(r'^(\d{1,6})[\s\|\-]?([^\d\s\|\-]{1,3})[\s\|\-]?(\d{1,2})$', s)
        if m:
            p1, p2, p3 = m.group(1), m.group(2).strip(), m.group(3)
            latin_letter = ARABIC_TO_LATIN_PLATE.get(p2, p2.upper())
            arabic_letter = LATIN_TO_ARABIC_PLATE.get(latin_letter, p2)
            canonical = f"{p1} | {latin_letter} | {p3}"
            return p1, latin_letter, arabic_letter, p3, canonical

        return '', '', '', '', s

    @api.depends('plate_letter_part')
    def _compute_plate_letter_arabic(self):
        for vehicle in self:
            if vehicle.plate_letter_part:
                vehicle.plate_letter_arabic = LATIN_TO_ARABIC_PLATE.get(vehicle.plate_letter_part, '')
            else:
                vehicle.plate_letter_arabic = False

    @api.depends('plate_type', 'plate_number_part', 'plate_letter_part', 'plate_region_part')
    def _compute_license_plate_display(self):
        for vehicle in self:
            if vehicle.plate_type == 'standard' and vehicle.plate_number_part and vehicle.plate_letter_part and vehicle.plate_region_part:
                ar = LATIN_TO_ARABIC_PLATE.get(vehicle.plate_letter_part, '')
                if ar:
                    vehicle.license_plate_display = f"{vehicle.plate_number_part} | {ar} ({vehicle.plate_letter_part}) | {vehicle.plate_region_part}"
                else:
                    vehicle.license_plate_display = f"{vehicle.plate_number_part} | {vehicle.plate_letter_part} | {vehicle.plate_region_part}"
            else:
                vehicle.license_plate_display = vehicle.license_plate or ''

    @api.depends('plate_type', 'plate_region_part', 'plate_letter_part', 'plate_number_part')
    def _compute_license_plate(self):
        """Assemble la plaque au format standard marocain canonique : Numéro | Lettre | Région (Ex: 12345 | A | 6)."""
        for vehicle in self:
            if vehicle.plate_type == 'standard':
                reg = (vehicle.plate_region_part or '').strip()
                let = (vehicle.plate_letter_part or '').strip()
                num = (vehicle.plate_number_part or '').strip()
                if num and let and reg:
                    vehicle.license_plate = f"{num} | {let} | {reg}"
                elif any([num, let, reg]):
                    parts = [p for p in [num, let, reg] if p]
                    vehicle.license_plate = " | ".join(parts)
            elif not vehicle.license_plate:
                vehicle.license_plate = False

    def _inverse_license_plate(self):
        """Décompose une plaque saisie manuellement (arabe ou latin) en ses composantes Numéro / Lettre / Région."""
        valid_letters = dict(PLATE_LETTERS_SELECTION)
        for vehicle in self:
            if not vehicle.license_plate:
                continue
            plate = vehicle.license_plate.strip()
            if vehicle.plate_type == 'standard':
                num, lat_let, ar_let, reg, canonical = self.normalize_moroccan_plate(plate)
                if num and reg:
                    vehicle.plate_number_part = num
                    vehicle.plate_region_part = reg
                    vehicle.plate_letter_part = lat_let if lat_let in valid_letters else False

    def _compute_display_name(self):
        """Affiche un nom de véhicule lisible et élégant sans doublon de plaque avec affichage bilingue si disponible."""
        for vehicle in self:
            brand = vehicle.model_id.brand_id.name or ''
            model = vehicle.model_id.name or ''
            model_info = f"{brand} {model}".strip() if (brand or model) else (vehicle.name or '')
            plate_str = vehicle.license_plate_display or vehicle.license_plate
            if plate_str:
                vehicle.display_name = f"{model_info} • {plate_str}" if model_info else plate_str
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

    @api.depends('damage_item_ids')
    def _compute_damage_item_count(self):
        for record in self:
            record.damage_item_count = len(record.damage_item_ids)

    def action_view_damage_items(self):
        self.ensure_one()
        return {
            'name': _("Historique Dégâts & Chocs - %s", self.name or self.license_plate),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.damage.item',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

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
                if len(clean_vin) > 17 or len(clean_vin) < 5:
                    raise ValidationError(_("Le numéro VIN (Châssis) doit comporter entre 5 et 17 caractères alphanumériques. (Reçu: %s)", len(clean_vin)))

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
