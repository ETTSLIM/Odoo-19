# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class GarageDamageItem(models.Model):
    _name = 'garage.damage.item'
    _description = "Élément Endommagé & Inventaire Carrosserie"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'discovery_stage desc, id desc'

    name = fields.Char(string="Désignation Élément", required=True, tracking=True)
    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", required=True, ondelete='cascade', tracking=True)
    claim_id = fields.Many2one('garage.insurance.claim', related='reception_id.claim_id', string="Dossier Sinistre", store=True, readonly=True)
    repair_order_id = fields.Many2one('repair.order', related='reception_id.repair_order_id', string="Ordre de Réparation", store=True, readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', related='reception_id.vehicle_id', string="Véhicule", store=True, readonly=True)

    zone = fields.Selection([
        ('front_bumper', 'Pare-chocs Avant'),
        ('rear_bumper', 'Pare-chocs Arrière'),
        ('hood', 'Capot Moteur'),
        ('trunk', 'Malle / Hayon Arrière'),
        ('fender_fl', 'Aile Avant Gauche'),
        ('fender_fr', 'Aile Avant Droite'),
        ('fender_rl', 'Aile Arrière Gauche'),
        ('fender_rr', 'Aile Arrière Droite'),
        ('door_fl', 'Porte Avant Gauche'),
        ('door_fr', 'Porte Avant Droite'),
        ('door_rl', 'Porte Arrière Gauche'),
        ('door_rr', 'Porte Arrière Droite'),
        ('roof', 'Pavillon / Toit'),
        ('windshield', 'Pare-brise / Vitrage'),
        ('optics', 'Optiques / Phares / Feux'),
        ('mechanical_chassis', 'Organe Mécanique / Train Roulant'),
        ('interior', 'Habitacle / Tableau de Bord'),
        ('other', 'Autre Élément'),
    ], string="Zone Véhicule", default='front_bumper', required=True, tracking=True)

    damage_type = fields.Selection([
        ('scratch', 'Rayure / Éraflure'),
        ('dent', 'Bosse / Enfoncement léger'),
        ('crack', 'Fissure / Cassure'),
        ('severely_deformed', 'Déformation Majeure / Plié'),
        ('missing', 'Élément Manquant / Détruit'),
        ('fluid_leak', 'Fuite de Fluide'),
    ], string="Type de Dégât", default='dent', required=True, tracking=True)

    severity = fields.Selection([
        ('light', 'Léger / Superficiel'),
        ('medium', 'Moyen / Redressable'),
        ('heavy', 'Grave / Remplacement Obligatoire'),
    ], string="Gravité", default='medium', required=True, tracking=True)

    action_type = fields.Selection([
        ('repair', 'Réparation / Redressage'),
        ('replace', 'Remplacement Neuf'),
        ('paint_only', 'Peinture / Retouche Seule'),
        ('inspect', 'Contrôle Démontage'),
    ], string="Action Préconisée", default='repair', required=True, tracking=True)

    discovery_stage = fields.Selection([
        ('intake', 'Réception Initiale (Visuel)'),
        ('lift', 'Inspection sur Pont'),
        ('disassembly', 'Démontage Atelier (Dégât Masqué)'),
    ], string="Moment de Découverte", default='intake', required=True, tracking=True)

    is_hidden_damage = fields.Boolean(string="Dégât Masqué", compute='_compute_is_hidden_damage', store=True)

    photo_ids = fields.Many2many(
        'ir.attachment', 'garage_damage_item_attachment_rel',
        'damage_id', 'attachment_id',
        string="Photos du Choc / Dégât"
    )
    photo_count = fields.Integer(string="Nb. Photos", compute='_compute_photo_count')

    notes = fields.Text(string="Observations Pratiques")

    expert_decision = fields.Selection([
        ('pending', 'En Attente Accord'),
        ('approved', 'Validé par l\'Expert'),
        ('rejected', 'Refusé par l\'Expert'),
    ], string="Décision Expert", default='pending', tracking=True)

    @api.depends('discovery_stage')
    def _compute_is_hidden_damage(self):
        for rec in self:
            rec.is_hidden_damage = (rec.discovery_stage == 'disassembly')

    @api.depends('photo_ids')
    def _compute_photo_count(self):
        for rec in self:
            rec.photo_count = len(rec.photo_ids)
