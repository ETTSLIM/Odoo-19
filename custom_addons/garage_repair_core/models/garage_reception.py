# -*- coding: utf-8 -*-
import json
import re
import base64
import os
import requests
import uuid
from markupsafe import Markup
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError
from .whatsapp_gateway import send_garage_whatsapp, normalize_morocco_phone
from .garage_workshop_workflow import SPECIALTY_BLUEPRINTS, WORKSHOP_BLUEPRINTS, _build_stage2_subtask_defs

class GarageReception(models.Model):
    _name = 'garage.reception'
    _description = 'Fiche de Réception & Check-in Atelier'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_reception desc, id desc'

    def _default_stage_id(self):
        stage = self.env['garage.workshop.stage'].search([('code', '=', 'reception')], limit=1)
        if not stage:
            stage = self.env['garage.workshop.stage'].search([], order='sequence, id', limit=1)
        return stage.id if stage else False

    name = fields.Char(string="Référence", required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'))
    active = fields.Boolean(string="Actif", default=True, tracking=True)
    date_reception = fields.Datetime(string="Date & Heure d'entrée", default=fields.Datetime.now, required=True, tracking=True)
    estimated_completion_date = fields.Datetime(string="Date Estimée de Restitution", tracking=True,
                                                help="Estimation communiquée au client sur son portail de suivi")

    # Véhicule & Client
    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule", required=True, tracking=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string="Immatriculation", store=True)
    vehicle_model_name = fields.Char(string="Modèle Véhicule", compute='_compute_vehicle_model_name', store=True)
    customer_id = fields.Many2one('res.partner', string="Client / Propriétaire", required=True, tracking=True,
                                  context={'default_partner_role': 'customer_individual'})
    customer_phone = fields.Char(related='customer_id.phone', string="Téléphone / WhatsApp", readonly=False)

    # Workflow 7 Étapes Canoniques (Native Odoo 19)
    stage_id = fields.Many2one(
        'garage.workshop.stage', string="Étape Atelier",
        default=_default_stage_id, tracking=True, index=True,
        group_expand='_read_group_stage_ids'
    )
    stage_sequence = fields.Integer(related='stage_id.sequence', string="Séquence Étape", store=True, index=True)

    # 6 Spécialités d'Atelier (Blueprints)
    specialty = fields.Selection([
        ('mecanique', "Mécanique Générale & Moteur"),
        ('carrosserie', "Tôlerie, Carrosserie & Peinture"),
        ('electricite', "Électricité & Diagnostic OBD"),
        ('entretien', "Entretien Rapide & Freinage"),
        ('climatisation', "Climatisation & Refroidissement"),
        ('pneumatique', "Pneumatiques & Géométrie 3D"),
    ], string="Spécialité Atelier", default='mecanique', required=True, tracking=True)

    # Opérateur Actif & Compte Tablette PIN
    current_operator_id = fields.Many2one('garage.workshop.operator', string="Dernier Intervenant (Tablette)", tracking=True)

    # Gamme de Travaux & Checklist par Étape
    task_ids = fields.One2many('garage.reception.task', 'reception_id', string="Sous-tâches Atelier")
    checklist_total_count = fields.Integer(string="Nb. Total Tâches", compute='_compute_checklist_progress', store=True)
    checklist_done_count = fields.Integer(string="Tâches Réalisées", compute='_compute_checklist_progress', store=True)
    checklist_progress = fields.Float(string="Progression Atelier (%)", compute='_compute_checklist_progress', store=True)

    can_toggle_workshop_tasks = fields.Boolean(compute='_compute_can_toggle_workshop_tasks', string="Peut modifier les tâches atelier")

    # Pipeline Diagnostic ➔ Stock / Magasinier ➔ Devis (Section 4 happy-faraday)
    diagnostic_parts_note = fields.Text(string="Note Diagnostic & Pièces Demandées au Stock", tracking=True,
                                        help="Notes techniques internes pour le magasinier (Strictement masquées sur le portail client).")
    stock_status = fields.Selection([
        ('attente_diag', "Attente Diagnostic"),
        ('envoye_stock', "Transmis au Stock"),
        ('devis_pret', "Devis Chiffré"),
        ('attente_pieces', "En Commande"),
        ('pieces_partielles', "Réception Partielle"),
        ('pieces_dispo', "Pièces Disponibles"),
        ('cloture', "Stock Clôturé"),
    ], string="Statut Stock & Magasinier", default='attente_diag', tracking=True)

    # Gestion Sinistre & Expertise (happy-faraday Section 5 & 8)
    is_assurance = fields.Boolean(string="Dossier Sinistre / Assurance", default=False, tracking=True)
    statut_expertise = fields.Selection([
        ('attente_passage', "Attente Passage Expert"),
        ('devis_envoye', "Devis Transmis Assurance"),
        ('accord_valide', "Accord Expert Validé"),
        ('accord_rectifie', "Accord Rectifié / Complémentaire"),
        ('contre_visite', "Contre-Visite Requise"),
    ], string="Statut Expertise Assurance", default='attente_passage', tracking=True)

    custom_todo_json = fields.Text(string="Tâches Dynamiques IA (JSON)", help="Liste des micro-tâches spécifiques détectées par l'IA.")

    auto_whatsapp_notify = fields.Boolean(string="Notification WhatsApp Auto", default=True,
                                          help="Transmet automatiquement un message WhatsApp au client à chaque changement d'étape majeur.")

    # État lors du check-in
    odometer_in = fields.Integer(string="Kilométrage d'entrée (km)", tracking=True)
    fuel_level = fields.Selection([
        ('0', '0% (Réserve)'),
        ('25', '25% (1/4)'),
        ('50', '50% (1/2)'),
        ('75', '75% (3/4)'),
        ('100', '100% (Plein)'),
    ], string="Niveau de Carburant", default='50', required=True, tracking=True)

    # Constat Carrosserie & Effets personnels
    bodywork_notes = fields.Text(string="État Carrosserie (Rayures, Chocs, Éléments manquants)")
    valuable_items = fields.Char(string="Objets de valeur laissés à bord")

    # Motif de la visite
    symptoms = fields.Text(string="Motif de Visite / Symptômes signalés", required=True, tracking=True)
    diagnostic_notes = fields.Text(string="Constat Technique Initial")

    # Assignation
    receptionist_id = fields.Many2one('res.users', string="Réceptionniste", default=lambda self: self.env.user)
    mechanic_id = fields.Many2one('res.users', string="Mécanicien Assigné", tracking=True)

    # Statut du cycle de vie atelier (Synchronisé avec stage_id)
    state = fields.Selection([
        ('draft', 'Réception'),
        ('diagnostic', 'Diagnostic'),
        ('quoted', 'Devis'),
        ('in_repair', 'En Atelier'),
        ('qc', 'Contrôle'),
        ('ready', 'Prêt'),
        ('delivered', 'Restitué'),
        ('cancel', 'Annulé'),
    ], string="Statut", default='draft', tracking=True)

    # Jeton sécurisé pour le suivi client en direct (sans mot de passe)
    tracking_token = fields.Char(string="Jeton de Suivi Client", copy=False, readonly=True)

    # Ordre de réparation Odoo & Sinistre
    repair_order_id = fields.Many2one('repair.order', string="Ordre de Réparation lié", copy=False)
    claim_id = fields.Many2one('garage.insurance.claim', string="Dossier Sinistre lié", copy=False)
    claim_state = fields.Selection(related='claim_id.state', string="Statut Sinistre", readonly=True)

    # Indicateurs Financiers & Suivi Devis / Facturation (Synchronisés avec repair_order_id)
    currency_id = fields.Many2one('res.currency', string="Devise", compute='_compute_currency_id')
    ro_amount_total_ttc = fields.Monetary(related='repair_order_id.amount_total_ttc', string="Total Réparation", readonly=True)
    ro_amount_paid = fields.Monetary(related='repair_order_id.amount_paid', string="Total Encaissé", readonly=True)
    ro_amount_residual = fields.Monetary(related='repair_order_id.amount_residual', string="Reste à Régler", readonly=True)
    ro_payment_status = fields.Selection(related='repair_order_id.payment_status', string="Statut Règlement", readonly=True)
    ro_client_approval_status = fields.Selection(related='repair_order_id.client_approval_status', string="Accord Devis", readonly=True)
    ro_is_invoiced_officially = fields.Boolean(related='repair_order_id.is_invoiced_officially', string="Facturé Officiellement", readonly=True)

    @api.depends('repair_order_id.currency_id')
    def _compute_currency_id(self):
        default_curr = self.env.company.currency_id
        for rec in self:
            rec.currency_id = rec.repair_order_id.currency_id or default_curr

    @api.depends('vehicle_id', 'vehicle_id.model_id', 'vehicle_id.model_id.brand_id')
    def _compute_vehicle_model_name(self):
        for rec in self:
            if rec.vehicle_id:
                brand = rec.vehicle_id.model_id.brand_id.name or ''
                model = rec.vehicle_id.model_id.name or ''
                rec.vehicle_model_name = f"{brand} {model}".strip() or rec.vehicle_id.name or _("Véhicule")
            else:
                rec.vehicle_model_name = False

    # Photos associées à la réception / check-in
    attachment_ids = fields.Many2many(
        'ir.attachment', 'garage_reception_attachment_rel',
        'reception_id', 'attachment_id',
        string="Photos de Check-in & Chocs"
    )
    carte_grise_ids = fields.Many2many(
        'ir.attachment', 'garage_reception_carte_grise_rel',
        'reception_id', 'attachment_id',
        string="Carte Grise (R/V)"
    )
    permis_ids = fields.Many2many(
        'ir.attachment', 'garage_reception_permis_rel',
        'reception_id', 'attachment_id',
        string="Permis de Conduire (R/V)"
    )
    constat_ids = fields.Many2many(
        'ir.attachment', 'garage_reception_constat_rel',
        'reception_id', 'attachment_id',
        string="Constat Amiable"
    )
    attachment_count = fields.Integer(string="Photos", compute='_compute_attachment_count')
    photos_grid_html = fields.Html(
        string="Galerie Photos & Documents",
        compute='_compute_photos_grid_html',
        sanitize=False
    )
    repair_order_count = fields.Integer(string="Ordres de Réparation", compute='_compute_repair_order_count')
    claim_count = fields.Integer(string="Sinistres", compute='_compute_claim_count')
    diagnostic_log_ids = fields.One2many('garage.diagnostic.log', 'reception_id', string="Historique Audios & Diagnostics")
    diagnostic_log_count = fields.Integer(string="Nb. Audios", compute='_compute_diagnostic_log_count')
    damage_item_ids = fields.One2many('garage.damage.item', 'reception_id', string="Éléments Endommagés")
    damage_item_count = fields.Integer(string="Nb. Dégâts", compute='_compute_damage_item_count')

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Affiche les 7 étapes de manière fluide et ordonnée en vue Kanban."""
        return self.env['garage.workshop.stage'].search([])

    @api.depends_context('uid')
    def _compute_can_toggle_workshop_tasks(self):
        user = self.env.user
        is_allowed = user._is_superuser() or user.has_group('garage_repair_core.group_garage_manager') or user.has_group('garage_repair_core.group_garage_mechanic')
        for rec in self:
            rec.can_toggle_workshop_tasks = is_allowed

    @api.depends('task_ids.is_done', 'task_ids.state')
    def _compute_checklist_progress(self):
        for rec in self:
            total = len(rec.task_ids)
            done = len(rec.task_ids.filtered(lambda t: t.is_done or t.state == '1_done'))
            rec.checklist_total_count = total
            rec.checklist_done_count = done
            rec.checklist_progress = (done / total * 100.0) if total > 0 else 0.0

    def _compute_attachment_count(self):
        for rec in self:
            all_atts = rec.attachment_ids | rec.carte_grise_ids | rec.permis_ids | rec.constat_ids
            rec.attachment_count = len(all_atts)

    @api.depends('attachment_ids', 'carte_grise_ids', 'permis_ids', 'constat_ids')
    def _compute_photos_grid_html(self):
        """Génère une grille compacte et fluide de toutes les photos avec prévisualisation modale plein écran sans téléchargement."""
        for rec in self:
            all_items = []
            seen_ids = set()

            def _append(att, label, badge_style):
                if att.id and att.id not in seen_ids:
                    seen_ids.add(att.id)
                    all_items.append({
                        'id': att.id,
                        'name': att.name or _("Photo"),
                        'label': label,
                        'badge_style': badge_style,
                        'url': f"/web/image/{att.id}",
                    })

            for a in rec.carte_grise_ids:
                _append(a, "Carte Grise", "bg-primary text-white")
            for a in rec.permis_ids:
                _append(a, "Permis", "bg-info text-dark")
            for a in rec.constat_ids:
                _append(a, "Constat", "bg-warning text-dark")
            for a in rec.attachment_ids:
                _append(a, "Inspection", "bg-secondary text-white")

            if not all_items:
                rec.photos_grid_html = Markup(
                    '<div class="text-center p-3 text-muted border rounded bg-light">'
                    '<i class="fa fa-camera fa-2x mb-2 d-block opacity-50" title="Aucune photo"/>'
                    '<span>Aucune photo ou document numérisé pour cette réception.</span>'
                    '</div>'
                )
                continue

            cards = []
            modals = []
            for item in all_items:
                aid = item['id']
                aname = item['name']
                lbl = item['label']
                bst = item['badge_style']
                aurl = item['url']
                mid = f"recPhotoModal_{rec.id}_{aid}"

                cards.append(
                    f'<div class="col">'
                    f'  <div class="card h-100 shadow-sm border text-center p-1" style="cursor: pointer;"'
                    f'       data-bs-toggle="modal" data-bs-target="#{mid}">'
                    f'    <div style="height: 95px; overflow: hidden; background: #212529; display: flex; align-items: center; justify-content: center;" class="rounded mb-1">'
                    f'      <img src="{aurl}" alt="{aname}" style="max-height: 100%; max-width: 100%; object-fit: cover;" class="rounded"/>'
                    f'    </div>'
                    f'    <div>'
                    f'      <span class="badge {bst} text-truncate d-block" style="font-size: 0.70rem;" title="{aname}">{lbl}</span>'
                    f'      <span class="text-muted text-truncate d-block" style="font-size: 0.68rem;" title="{aname}">{aname}</span>'
                    f'    </div>'
                    f'  </div>'
                    f'</div>'
                )

                modals.append(
                    f'<div class="modal fade" id="{mid}" tabindex="-1" aria-hidden="true">'
                    f'  <div class="modal-dialog modal-dialog-centered modal-lg">'
                    f'    <div class="modal-content shadow-lg">'
                    f'      <div class="modal-header py-2">'
                    f'        <h6 class="modal-title fw-bold text-dark"><i class="fa fa-picture-o text-primary me-2"/>{aname} ({lbl})</h6>'
                    f'        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>'
                    f'      </div>'
                    f'      <div class="modal-body text-center p-2 bg-dark">'
                    f'        <img src="{aurl}" alt="{aname}" style="max-height: 80vh; max-width: 100%; object-fit: contain; border-radius: 4px;"/>'
                    f'      </div>'
                    f'      <div class="modal-footer py-1 d-flex justify-content-between">'
                    f'        <a href="{aurl}?download=true" class="btn btn-sm btn-outline-secondary"><i class="fa fa-download me-1"/>Télécharger original</a>'
                    f'        <button type="button" class="btn btn-sm btn-primary" data-bs-dismiss="modal">Fermer</button>'
                    f'      </div>'
                    f'    </div>'
                    f'  </div>'
                    f'</div>'
                )

            html_output = (
                f'<div class="row row-cols-2 row-cols-sm-3 row-cols-md-4 row-cols-lg-6 g-2">'
                f'{"".join(cards)}'
                f'</div>'
                f'{"".join(modals)}'
            )
            rec.photos_grid_html = Markup(html_output)

    def _compute_repair_order_count(self):
        for rec in self:
            rec.repair_order_count = 1 if rec.repair_order_id else 0

    def _compute_claim_count(self):
        for rec in self:
            rec.claim_count = 1 if rec.claim_id else 0

    @api.depends('diagnostic_log_ids')
    def _compute_diagnostic_log_count(self):
        for rec in self:
            rec.diagnostic_log_count = len(rec.diagnostic_log_ids)

    @api.depends('damage_item_ids')
    def _compute_damage_item_count(self):
        for rec in self:
            rec.damage_item_count = len(rec.damage_item_ids)

    def action_view_diagnostic_logs(self):
        self.ensure_one()
        return {
            'name': _("Diagnostics Vocaux & Audios"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.diagnostic.log',
            'view_mode': 'list,form',
            'domain': [('reception_id', '=', self.id)],
            'context': {'default_reception_id': self.id},
        }

    def action_view_damage_items(self):
        self.ensure_one()
        return {
            'name': _("Éléments Endommagés & Carrosserie"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.damage.item',
            'view_mode': 'list,form',
            'domain': [('reception_id', '=', self.id)],
            'context': {'default_reception_id': self.id},
        }

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'name': _("Galerie Photos & Documents"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.photo.gallery.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reception_id': self.id,
                'default_category_filter': 'all',
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garage.reception') or _('Nouveau')
            if not vals.get('tracking_token'):
                vals['tracking_token'] = uuid.uuid4().hex[:12]
            if vals.get('claim_id'):
                vals['is_assurance'] = True
        records = super().create(vals_list)
        for record in records:
            if record.vehicle_id and record.odometer_in:
                record.vehicle_id.odometer = record.odometer_in
            # Génère automatiquement la gamme d'atelier si aucune tâche n'est définie
            if not record.task_ids:
                record.action_generate_specialty_checklist()
            if record.diagnostic_parts_note and record.stock_status in ('attente_diag', False):
                record.action_send_note_to_stock()
            # Auto-initiation immédiate du dossier sinistre si marqué assurance
            if record.is_assurance and not record.claim_id:
                try:
                    record.action_create_or_view_claim()
                except Exception as ce:
                    _logger.warning("Erreur lors de l'auto-création du sinistre: %s", ce)
        return records

    def write(self, vals):
        if vals.get('claim_id'):
            vals['is_assurance'] = True

        # 1. Synchronisation bidirectionnelle stage_id <-> state
        if 'stage_id' in vals and vals['stage_id']:
            new_stage = self.env['garage.workshop.stage'].browse(vals['stage_id'])
            if new_stage.mapped_state:
                vals['state'] = new_stage.mapped_state

        # 2. Interlock Sinistre & Devis (Safety Interlock happy-faraday Section 5 & 8)
        if 'stage_id' in vals and not self.env.context.get('bypass_interlock'):
            target_stage = self.env['garage.workshop.stage'].browse(vals['stage_id'])
            if target_stage and target_stage.sequence >= 40:  # Étape 4 (Travaux Atelier) ou supérieure
                for rec in self:
                    # Règle Sinistre Assuré
                    if rec.claim_id or rec.is_assurance:
                        if rec.claim_id:
                            if rec.claim_id.state not in ('accord_approved', 'in_repair', 'repaired'):
                                raise UserError(_(
                                    "INTERLOCK DE SÉCURITÉ SINISTRE :\n\n"
                                    "Impossible d'avancer le véhicule vers '%s' (Étape 4+) !\n"
                                    "Le dossier sinistre %s est actuellement à l'état '%s'.\n"
                                    "L'accord de l'expert automobile et la validation formelle de l'assuré sont obligatoires avant le démontage et les travaux.",
                                    target_stage.name, rec.claim_id.claim_number, rec.claim_id.state
                                ))
                            if rec.claim_id.client_accord_status != 'approved':
                                raise UserError(_(
                                    "ACCORD ASSURÉ OBLIGATOIRE :\n\n"
                                    "L'expert a émis son rapport, mais l'assuré n'a pas encore validé la franchise/vétusté sur son portail WhatsApp/Web."
                                ))
                        elif rec.statut_expertise != 'accord_valide':
                            raise UserError(_(
                                "ACCORD EXPERT OBLIGATOIRE :\n\n"
                                "Ce dossier est marqué Sinistre/Assurance. L'accord formel de l'expert d'assurance (Statut: Accord validé) est obligatoire avant les travaux d'atelier."
                            ))

        old_stages = {rec.id: rec.stage_id for rec in self} if 'stage_id' in vals else {}

        res = super().write(vals)

        # 3. Synchronisation des sous-tâches si l'étape a changé
        if 'stage_id' in vals and not self.env.context.get('skip_subtask_sync'):
            for rec in self:
                rec._sync_subtasks_with_parent_stage(rec.stage_sequence)

        # 4. Synchronisation de l'état du Repair Order Odoo standard
        if 'stage_id' in vals and not self.env.context.get('skip_ro_sync'):
            for rec in self:
                ro = rec.repair_order_id
                if ro and ro.exists():
                    target_seq = rec.stage_sequence
                    if 40 <= target_seq < 60 and ro.state in ('draft', 'confirmed'):
                        try:
                            if hasattr(ro, 'action_repair_start'):
                                ro.with_context(skip_ro_sync=True).action_repair_start()
                            else:
                                ro.with_context(skip_ro_sync=True).write({'state': 'under_repair'})
                        except Exception:
                            pass
                    elif target_seq >= 60 and ro.state == 'under_repair':
                        try:
                            if hasattr(ro, 'action_repair_end'):
                                ro.with_context(skip_ro_sync=True).action_repair_end()
                            else:
                                ro.with_context(skip_ro_sync=True).write({'state': 'done'})
                        except Exception:
                            pass

        # 5. Notification WhatsApp automatique si l'étape a avancé
        if 'stage_id' in vals:
            for rec in self:
                old_stage = old_stages.get(rec.id)
                new_stage = rec.stage_id
                if old_stage and new_stage and old_stage != new_stage and new_stage.sequence > old_stage.sequence:
                    if rec.auto_whatsapp_notify:
                        rec._notify_customer_stage_change(old_stage, new_stage)

        # 6. Transmission automatique au stock dès saisie d'une note de pièces
        if 'diagnostic_parts_note' in vals and vals.get('diagnostic_parts_note') and not self.env.context.get('skip_stock_note_sync'):
            for rec in self:
                if rec.stock_status in ('attente_diag', False):
                    try:
                        rec.with_context(skip_stock_note_sync=True).action_send_note_to_stock()
                    except Exception:
                        pass

        # 7. Auto-initiation du dossier sinistre si activé
        if vals.get('is_assurance'):
            for rec in self:
                if rec.is_assurance and not rec.claim_id:
                    try:
                        rec.action_create_or_view_claim()
                    except Exception as ce:
                        _logger.warning("Erreur auto-initiation sinistre: %s", ce)

        return res

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            if self.vehicle_id.customer_id:
                self.customer_id = self.vehicle_id.customer_id
            if self.vehicle_id.odometer:
                self.odometer_in = self.vehicle_id.odometer

    def _get_tracking_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        return f"{base_url.rstrip('/')}/garage/tracking/{self.tracking_token}"

    def action_generate_specialty_checklist(self, custom_todo_tasks=None, replace_existing=False):
        """Génère la checklist micro-tâches complète (Étapes 1 à 6) selon la spécialité et l'assurance.
        Intègre les micro-tâches dynamiques [Étape 4 • مخصصة] issues de l'interprétation IA du diagnostic.
        """
        self.ensure_one()
        blueprint = SPECIALTY_BLUEPRINTS.get(self.specialty or 'mecanique')
        if not blueprint:
            return False

        stages_by_seq = {s.sequence: s for s in self.env['garage.workshop.stage'].search([])}
        Task = self.env['garage.reception.task']

        if replace_existing and self.task_ids:
            tasks_to_remove = self.task_ids.filtered(lambda t: t.state != '1_done' and not t.is_done)
            tasks_to_remove.unlink()

        existing_names = set(self.task_ids.mapped('name'))

        # Extraction des tâches personnalisées IA
        clean_custom = []
        if custom_todo_tasks:
            clean_custom = [t.strip() for t in custom_todo_tasks if t and t.strip()]
        elif self.custom_todo_json:
            try:
                parsed = json.loads(self.custom_todo_json)
                if isinstance(parsed, list):
                    clean_custom = [str(t).strip() for t in parsed if str(t).strip()]
            except Exception:
                clean_custom = [t.strip() for t in self.custom_todo_json.split('\n') if t.strip()]

        effective_assurance = bool(self.is_assurance or self.claim_id)
        stage2_defs = _build_stage2_subtask_defs(is_assurance=effective_assurance)

        all_defs = []

        # Étape 1 : Réception & Diagnostic initial
        for s in blueprint['subtasks']:
            if s['stage_seq'] == 10:
                all_defs.append(s)

        # Étape 2 : Devis & Accord (2A, 2B, + 2C si assurance)
        all_defs.extend(stage2_defs)

        # Étape 3 : Commande & Attente Pièces
        for s in blueprint['subtasks']:
            if s['stage_seq'] == 30:
                all_defs.append(s)

        # Étape 4 : Travaux Atelier (4A..4D du blueprint + tâches dynamiques [Étape 4 • مخصصة])
        for s in blueprint['subtasks']:
            if s['stage_seq'] == 40:
                all_defs.append(s)

        if clean_custom:
            for idx, c_text in enumerate(clean_custom):
                all_defs.append({
                    'stage_seq': 40,
                    'name': f"[Étape 4 • مخصصة] {c_text}",
                    'hours': 2.0,
                    'description': f"Tâche personnalisée issue du diagnostic mécanicien / IA (#{idx + 1}) : {c_text}",
                    'is_ai_dynamic': True,
                })

        # Étape 5 : Contrôle Qualité & Finition
        for s in blueprint['subtasks']:
            if s['stage_seq'] == 50:
                all_defs.append(s)

        # Étape 6 : Préparation & Livraison
        for s in blueprint['subtasks']:
            if s['stage_seq'] == 60:
                all_defs.append(s)

        created_tasks = []
        current_stage_seq = self.stage_sequence or 10
        first_in_current_stage = True

        for idx, sub_def in enumerate(all_defs):
            task_name = sub_def['name']
            if task_name in existing_names:
                continue

            stage_seq = sub_def['stage_seq']
            stage = stages_by_seq.get(stage_seq)
            if not stage:
                stage = self.env['garage.workshop.stage'].search([('sequence', '<=', stage_seq)], order='sequence desc', limit=1)
            if not stage:
                stage = self.stage_id

            # Calcul de l'état initial
            if stage_seq < current_stage_seq:
                st_state = '1_done'
            elif stage_seq == current_stage_seq:
                if first_in_current_stage:
                    st_state = '01_in_progress'
                    first_in_current_stage = False
                else:
                    st_state = '04_waiting_normal'
            else:
                st_state = '04_waiting_normal'

            created_tasks.append({
                'reception_id': self.id,
                'stage_id': stage.id,
                'sequence': (stage_seq * 10) + idx,
                'name': task_name,
                'description': sub_def.get('description', ''),
                'planned_hours': sub_def.get('hours', 0.5),
                'is_ai_dynamic': bool(sub_def.get('is_ai_dynamic', False)),
                'state': st_state,
                'is_done': (st_state == '1_done'),
            })

        if created_tasks:
            Task.create(created_tasks)

        self.message_post(body=Markup(_(
            "<b>Gamme d'Atelier Initialisée :</b> %d micro-opérations générées pour la spécialité <b>%s</b> (Dossier Assurance: %s, Tâches IA: %d)."
        ) % (len(created_tasks), blueprint['name'], "Oui" if effective_assurance else "Non", len(clean_custom))))
        return True

    def _sync_subtasks_with_parent_stage(self, target_stage_seq):
        """Synchronise l'état des sous-tâches lors d'un déplacement de Grande Étape."""
        self.ensure_one()
        first_in_target = True
        for task in self.task_ids.sorted(lambda t: (t.sequence, t.id)):
            sub_seq = task.stage_sequence
            curr_state = task.state

            if target_stage_seq >= 70:
                new_state = '1_done'
            elif sub_seq == 30 and self.stock_status == 'pieces_partielles':
                new_state = '01_in_progress'
            elif sub_seq < target_stage_seq:
                new_state = '1_done'
            elif sub_seq == 20 and target_stage_seq == 20:
                has_devis = self.stock_status in ('devis_pret', 'attente_pieces', 'pieces_dispo', 'pieces_partielles')
                if "2A" in task.name:
                    new_state = '1_done' if (curr_state == '1_done' or has_devis) else '01_in_progress'
                elif "2B" in task.name:
                    if curr_state == '1_done':
                        new_state = '1_done'
                    elif has_devis:
                        new_state = '01_in_progress'
                    else:
                        new_state = '04_waiting_normal'
                else:
                    new_state = curr_state
            elif sub_seq == target_stage_seq:
                if curr_state == '1_done':
                    new_state = '1_done'
                elif first_in_target:
                    new_state = '01_in_progress'
                    first_in_target = False
                else:
                    new_state = curr_state
            else:
                new_state = curr_state

            if curr_state != new_state:
                task.with_context(auto_workflow_sync=True).write({
                    'state': new_state,
                    'is_done': (new_state == '1_done'),
                })

    def action_send_note_to_stock(self):
        """Transmet la note de pièces au magasinier et fait basculer le statut vers 'envoye_stock'."""
        self.ensure_one()
        note = (self.diagnostic_parts_note or self.diagnostic_notes or self.symptoms or "").strip()
        if not note:
            raise UserError(_("Veuillez renseigner les pièces ou symptômes demandés dans 'Note Diagnostic & Pièces' avant d'envoyer au stock."))

        self.write({
            'stock_status': 'envoye_stock',
        })

        # Marquer la tâche Étape 1 comme terminée
        stage1_tasks = self.task_ids.filtered(lambda t: t.stage_sequence == 10)
        for t in stage1_tasks:
            t.with_context(auto_workflow_sync=True).write({'state': '1_done', 'is_done': True})

        # Active la micro-tâche 2A (Chiffrage du Devis)
        task_2a = self.task_ids.filtered(lambda t: "2a" in t.name.lower() or "chiffrage" in t.name.lower())
        if task_2a:
            task_2a.with_context(auto_workflow_sync=True).write({'state': '01_in_progress', 'is_done': False})

        self.message_post(body=Markup(_(
            "<b>Note Diagnostic Transmise au Stock (Magasinier) :</b><br/>%s<br/>"
            "<i>Statut Stock mis à jour : Transmis au Stock. Micro-tâche [Étape 2A • Devis] activée.</i>"
        ) % note.replace("\n", "<br/>")))
        return True

    def action_mark_devis_ready(self):
        """Action du Magasinier / Facturation : indique que le chiffrage est prêt."""
        self.ensure_one()
        self.write({'stock_status': 'devis_pret'})

        # Si encore à l'étape 1 Réception, avance vers l'étape 2 (Devis & Accord) maintenant que le chiffrage est prêt
        if self.stage_sequence <= 10:
            stage_devis = self.env['garage.workshop.stage'].search([('sequence', '=', 20)], limit=1)
            if stage_devis:
                self.write({'stage_id': stage_devis.id})

        # Marquer 2A comme fait
        task_2a = self.task_ids.filtered(lambda t: "2a" in t.name.lower() or "chiffrage" in t.name.lower())
        for t in task_2a:
            t.with_context(auto_workflow_sync=True).write({
                'state': '1_done',
                'is_done': True,
                'completed_date': fields.Datetime.now()
            })

        # Activer 2B (Accord Client) et 2C (Accord Expert si assurance)
        task_2b = self.task_ids.filtered(lambda t: "2b" in t.name.lower() or "accord client" in t.name.lower())
        if task_2b and task_2b.state != '1_done':
            task_2b.with_context(auto_workflow_sync=True).write({'state': '01_in_progress'})

        task_2c = self.task_ids.filtered(lambda t: "2c" in t.name.lower() or "accord expert" in t.name.lower())
        if task_2c and task_2c.state != '1_done':
            task_2c.with_context(auto_workflow_sync=True).write({'state': '01_in_progress'})

        self.message_post(body=Markup(_(
            "<b>Chiffrage Devis Prêt :</b> Le magasinier a complété le chiffrage des pièces.<br/>"
            "<i>Micro-tâche 2A validée. Micro-tâches 2B (Accord Client) et 2C (Accord Expert) en attente de signature.</i>"
        )))
        return True

    def action_mark_parts_available(self):
        """Action du Magasinier : indique que toutes les pièces sont physiquement à l'atelier."""
        self.ensure_one()
        self.write({'stock_status': 'pieces_dispo'})

        # Marquer la tâche Étape 3 Pièces comme réalisée
        stage3_tasks = self.task_ids.filtered(lambda t: t.stage_sequence == 30)
        for t in stage3_tasks:
            t.with_context(auto_workflow_sync=True).write({
                'state': '1_done',
                'is_done': True,
                'completed_date': fields.Datetime.now()
            })

        # Si l'accord client (2B) et l'accord expert (2C si assurance) sont validés, avance vers l'Étape 4
        stage2_pending = self.task_ids.filtered(lambda t: t.stage_sequence == 20 and t.state != '1_done')
        if not stage2_pending and self.stage_sequence < 40:
            stage_travaux = self.env['garage.workshop.stage'].search([('sequence', '=', 40)], limit=1)
            if stage_travaux:
                self.write({'stage_id': stage_travaux.id})

        self.message_post(body=Markup(_("✅ <b>Pièces Disponibles à l'Atelier :</b> Les pièces sont réceptionnées et remises aux techniciens.")))
        return True

    def submit_supplementary_diagnostic(self, note, technician_name="Chef d'Atelier"):
        """Enregistre un diagnostic complémentaire pendant le démontage en atelier et active la tâche 2D."""
        self.ensure_one()
        clean_note = (note or "").strip()
        if not clean_note:
            return False

        curr_time = fields.Datetime.now().strftime("%d/%m/%Y %H:%M")
        old_note = self.diagnostic_parts_note or ""
        self.diagnostic_parts_note = f"{old_note}\n\n[Diagnostic Complémentaire {curr_time} - {technician_name}] :\n{clean_note}".strip()
        self.stock_status = 'envoye_stock'

        # Création ou activation de la sous-tâche 2D Devis Complémentaire
        task_2d = self.task_ids.filtered(lambda t: "2d" in t.name.lower() or "complémentaire" in t.name.lower())
        if not task_2d:
            stage_2 = self.env['garage.workshop.stage'].search([('sequence', '=', 20)], limit=1) or self.stage_id
            self.env['garage.reception.task'].create({
                'reception_id': self.id,
                'stage_id': stage_2.id,
                'sequence': 240,
                'name': "[Étape 2D • Devis Complémentaire] إعداد دوڤي تكميلي لقطع إضافية (Devis Complémentaire)",
                'hours': 0.5,
                'description': f"Chiffrage complémentaire pour pièces découvertes au démontage : {clean_note}",
                'state': '01_in_progress',
                'is_done': False,
            })
        else:
            task_2d.with_context(auto_workflow_sync=True).write({'state': '01_in_progress', 'is_done': False})

        self.message_post(body=Markup(_(
            "⚠️ <b>Diagnostic Complémentaire Relevé par %s :</b><br/>%s<br/>"
            "<i>Note transmise au magasinier. Micro-tâche [Étape 2D • Devis Complémentaire] initialisée.</i>"
        ) % (technician_name, clean_note.replace('\n', '<br/>'))))
        return True

    def process_ai_diagnostic(self, audio_base64=None, raw_note="", custom_todos=None, is_assurance=None,
                               workshop_type=None, stage_id=None, is_hidden_damage=False, operator_id=None,
                               audio_filename=None):
        """Interprète le diagnostic mécanicien (audio ou texte Darija/Français) avec Gemini Flash ou le parseur heuristique,
        résout les auto-corrections orales contextuelles du mécanicien (ex: revirement de décision au cours de la parole),
        crée un enregistrement d'audit dans garage.diagnostic.log (3 formats : audio, transcription, micro-tâches magasinier),
        enregistre les dégâts constatés dans garage.damage.item,
        et injecte les micro-tâches de façon non destructive dans l'Atelier sans écraser les tâches terminées."""
        self.ensure_one()
        transcription = (raw_note or "").strip()
        transcription_summary = ""
        extracted_tasks = []
        extracted_damage_items = []
        detected_assurance = bool(is_assurance)
        detected_specialty = workshop_type or ""
        detected_hidden_damage = bool(is_hidden_damage)

        gemini_api_key = os.environ.get('GEMINI_API_KEY') or self.env['ir.config_parameter'].sudo().get_param('garage.gemini_api_key', '')

        aud_mime = "audio/mp4"
        clean_b64 = None
        if audio_base64:
            clean_b64 = audio_base64.split(",")[-1].strip()
            try:
                aud_bytes = base64.b64decode(clean_b64)
                if aud_bytes.startswith(b"\x1a\x45\xdf\xa3"):
                    aud_mime = "audio/webm"
                elif aud_bytes.startswith(b"OggS"):
                    aud_mime = "audio/ogg"
                elif aud_bytes.startswith(b"RIFF"):
                    aud_mime = "audio/wav"
            except Exception:
                pass

        if (clean_b64 or transcription) and gemini_api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
                prompt = (
                    "CRITICAL AUTOMOTIVE WORKSHOP FOREMAN & MOROCCAN DARIJA EXPERT PROTOCOL:\n"
                    "You are the Master Automotive Workshop Foreman (Chef d'Atelier). "
                    "Analyze attentively this mechanic voice diagnostic spoken in Moroccan Darija (العربية الدارجة المغربية) and French automotive jargon.\n\n"
                    "1. MOROCCAN DARIJA AUTOMOTIVE VOCABULARY REFERENCE:\n"
                    "   - 'vidange' -> Vidange huile moteur + filtres (5W30, 5W40, 10W40)\n"
                    "   - 'plaqat / plaquettes' -> Plaquettes de frein avant/arrière\n"
                    "   - 'diskat / disques' -> Disques de frein\n"
                    "   - 'amortisourat / amortisseurs' -> Amortisseurs avant/arrière\n"
                    "   - 'rotule / tirant / bras / silentbloc' -> Éléments de suspension et direction\n"
                    "   - 'cremaillere' -> Crémaillère de direction\n"
                    "   - 'radiateur / kaytayer l-ma / skhona' -> Radiateur de refroidissement / fuite liquide\n"
                    "   - 'jwan kylas' -> Joint de culasse et surfaçage\n"
                    "   - 'kit embrayage / plateau / disque / butee' -> Kit embrayage\n"
                    "   - 'courroie distribution / chaine' -> Kit distribution et pompe à eau\n"
                    "   - 'parchoc / pare-choc' -> Pare-chocs avant / arrière\n"
                    "   - 'l-aile' -> Aile avant / arrière\n"
                    "   - 'capot' -> Capot moteur\n"
                    "   - 'malle / coffre' -> Coffre arrière\n"
                    "   - 'pneus / rwayed' -> Pneumatiques (changement, géométrie, parallélisme)\n"
                    "   - 'batterie / alternateur / démarreur' -> Circuit électrique de démarrage et charge\n"
                    "   - 'clim / gaz' -> Climatisation et recharge gaz\n\n"
                    "2. ACTION RESOLUTION & MID-SPEECH SELF-CORRECTIONS:\n"
                    "   - 'nbdlo / badal / khassou tbdil / jdid' -> action='replace', requires_new_part=true\n"
                    "   - 'ghir n-repariw / n-souwdew / n-sabghouh / bla ma n-bdlouh' -> action='repair', requires_new_part=false\n"
                    "   - 'n-verifiw / n-qellbo / chouf / controle' -> action='inspect', requires_new_part=false\n"
                    "   - 'vidange / graissage / recharge' -> action='service', requires_new_part=true\n"
                    "   - Resolve hesitations: if the speaker says 'khassna nbdlo parchoc la machi nbdloh ghir nrepariwh', resolve to REPAIR pare-chocs.\n\n"
                    "3. TASK GRANULARITY (MANDATORY):\n"
                    "   Every individual work item or replaced component MUST be a separate, distinct task in 'tasks'. Never group distinct parts together into a vague sentence.\n\n"
                    "Extract STRICTLY JSON matching this schema:\n"
                    "{\n"
                    "  \"transcription\": \"Exact verbatim transcript in Arabic script (الدارجة المغربية) and French terms\",\n"
                    "  \"transcription_summary\": \"Concise professional French synthesis of the technician assessment\",\n"
                    "  \"tasks\": [\n"
                    "    {\n"
                    "      \"name\": \"Concise French task title (e.g. Remplacement plaquettes de frein avant)\",\n"
                    "      \"action\": \"replace\" | \"repair\" | \"service\" | \"inspect\",\n"
                    "      \"component\": \"Target component name in French\",\n"
                    "      \"requires_new_part\": true | false,\n"
                    "      \"rectification_note\": \"Explanation of any mid-speech hesitation resolved\",\n"
                    "      \"labor_hours\": 1.0\n"
                    "    }\n"
                    "  ],\n"
                    "  \"damaged_items\": [\n"
                    "    {\n"
                    "      \"name\": \"Component name\",\n"
                    "      \"zone\": \"front_bumper\"|\"rear_bumper\"|\"hood\"|\"trunk\"|\"fender_fl\"|\"fender_fr\"|\"fender_rl\"|\"fender_rr\"|\"door_fl\"|\"door_fr\"|\"door_rl\"|\"door_rr\"|\"roof\"|\"windshield\"|\"optics\"|\"mechanical_chassis\"|\"interior\"|\"other\",\n"
                    "      \"damage_type\": \"scratch\"|\"dent\"|\"crack\"|\"severely_deformed\"|\"missing\"|\"fluid_leak\",\n"
                    "      \"severity\": \"light\"|\"medium\"|\"heavy\",\n"
                    "      \"action_type\": \"repair\"|\"replace\"|\"paint_only\"|\"inspect\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"is_assurance\": true | false,\n"
                    "  \"is_hidden_damage\": true | false,\n"
                    "  \"workshop_type\": \"carrosserie\" | \"mecanique\" | \"electricite\" | \"entretien\" | \"climatisation\" | \"pneumatique\"\n"
                    "}"
                )

                parts = []
                if clean_b64:
                    parts.append({"inline_data": {"mime_type": aud_mime, "data": clean_b64}})
                if transcription:
                    prompt = f"{prompt}\n\nAdditional technician notes: {transcription}"
                parts.append({"text": prompt})

                payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {
                        "temperature": 0.0,
                        "response_mime_type": "application/json"
                    }
                }
                res = requests.post(url, json=payload, timeout=25)
                if res.status_code == 200:
                    text_resp = res.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '{}')
                    m = re.search(r'\{.*\}', text_resp, re.DOTALL)
                    if m:
                        p_data = json.loads(m.group(0))
                        transcription = p_data.get('transcription', transcription)
                        transcription_summary = p_data.get('transcription_summary', '')
                        if p_data.get('tasks'):
                            extracted_tasks = p_data['tasks']
                        if p_data.get('damaged_items'):
                            extracted_damage_items = p_data['damaged_items']
                        if p_data.get('is_assurance'):
                            detected_assurance = True
                        if p_data.get('is_hidden_damage'):
                            detected_hidden_damage = True
                        if p_data.get('workshop_type'):
                            detected_specialty = p_data['workshop_type']
            except Exception as e:
                _logger.warning("IA Gemini Audio warning: %s. Using heuristic parser.", e)
                if self.id and isinstance(self.id, int):
                    self.message_post(body=Markup(_("<i>Avertissement IA Gemini Audio : %s. Utilisation du parseur heuristique.</i>") % str(e)))

        # Fallback si pas de tâches extraites via Gemini
        clean_text = f"{transcription}\n{raw_note}".strip()
        if not extracted_tasks:
            lines = list(custom_todos or [])
            if not lines and clean_text:
                lines = [l.strip() for l in re.split(r'[\n،,•\-]+', clean_text) if len(l.strip()) >= 3]
            for l in lines[:8]:
                act = 'replace' if any(w in l.lower() for w in ['nbdlo', 'badal', 'remplacer', 'changement', 'neuf']) else 'repair'
                req_part = (act == 'replace')
                extracted_tasks.append({
                    'name': l,
                    'action': act,
                    'component': l.split()[-1] if l.split() else 'Organe',
                    'requires_new_part': req_part,
                    'rectification_note': '',
                    'labor_hours': 1.0,
                })

        # Spécialité & Assurance fallback
        if not detected_specialty and clean_text:
            low_text = clean_text.lower()
            for w_key, w_info in WORKSHOP_BLUEPRINTS.items():
                if any(kw in low_text for kw in w_info['keywords']):
                    detected_specialty = w_key
                    break

        if is_assurance is None and clean_text:
            low_text = clean_text.lower()
            assurance_keywords = ['assurance', 'sinistre', 'expert', 'constat', 'تأمين', 'لاصيرانص', 'أصيرانص', 'خبير', 'سينيستر']
            if any(k in low_text for k in assurance_keywords):
                detected_assurance = True

        # 1. Création de l'enregistrement persistant garage.diagnostic.log (uniquement si persistant en base)
        diagnostic_log = False
        log_tasks = []
        is_persisted = bool(self.id and isinstance(self.id, int))

        if is_persisted:
            effective_stage = stage_id and self.env['garage.workshop.stage'].browse(stage_id) or self.stage_id
            diag_log_vals = {
                'reception_id': self.id,
                'operator_id': operator_id,
                'stage_id': effective_stage.id if effective_stage else False,
                'audio_file': clean_b64 if clean_b64 else False,
                'audio_filename': audio_filename or 'diagnostic_audio.mp3',
                'audio_mimetype': aud_mime,
                'transcription_raw': transcription,
                'transcription_summary': transcription_summary or transcription,
                'is_hidden_damage': detected_hidden_damage,
                'state': 'submitted_to_stock',
            }
            diagnostic_log = self.env['garage.diagnostic.log'].create(diag_log_vals)

            # 2. Création des lignes de micro-tâches du log
            for t in extracted_tasks:
                t_name = t.get('name') or _('Opération Atelier')
                t_act = t.get('action') if t.get('action') in ('replace', 'repair', 'service', 'inspect') else 'repair'
                t_comp = t.get('component', '')
                t_req = bool(t.get('requires_new_part', False))

                # Filtrage sémantique strict : Ne jamais étiqueter un service d'entretien comme une pièce détachée
                is_service = any(kw in t_name.lower() for kw in [
                    'vidange', 'purge', 'graissage', 'réglage', 'reglage', 'parallélisme',
                    'parallelisme', 'contrôle', 'controle', 'diagnostic', 'géométrie',
                    'geometrie', 'nettoyage', 'équilibrage', 'equilibrage'
                ])
                if is_service:
                    t_req = False
                    if t_act == 'replace':
                        t_act = 'service'

                t_note = t.get('rectification_note', '')
                t_hours = float(t.get('labor_hours') or 1.0)
                log_task = self.env['garage.diagnostic.log.task'].create({
                    'log_id': diagnostic_log.id,
                    'name': t_name,
                    'action': t_act,
                    'component': t_comp,
                    'requires_new_part': t_req,
                    'rectification_note': t_note,
                    'labor_hours': t_hours,
                    'hourly_rate': 150.0,
                    'is_validated': False,
                })
                log_tasks.append(log_task)

            # 3. Création des damage items si détectés
            for dmg in extracted_damage_items:
                d_name = dmg.get('name') or _('Élément Endommagé')
                d_zone = dmg.get('zone') or 'front_bumper'
                d_type = dmg.get('damage_type') or 'dent'
                d_sev = dmg.get('severity') or 'medium'
                d_act = dmg.get('action_type') or 'repair'
                self.env['garage.damage.item'].create({
                    'reception_id': self.id,
                    'name': d_name,
                    'zone': d_zone,
                    'damage_type': d_type,
                    'severity': d_sev,
                    'action_type': d_act,
                    'discovery_stage': 'disassembly' if detected_hidden_damage else 'intake',
                })

            # 4. Mise à jour des valeurs sur la réception
            vals = {}
            if detected_specialty and detected_specialty in WORKSHOP_BLUEPRINTS:
                vals['specialty'] = detected_specialty
            if detected_assurance or self.claim_id:
                vals['is_assurance'] = True

            if transcription_summary or transcription:
                vals['diagnostic_notes'] = transcription_summary or transcription
            if extracted_damage_items:
                vals['bodywork_notes'] = "\n".join([f"- {d.get('name')} ({d.get('zone', 'autre')})" for d in extracted_damage_items])

            todo_titles = [t.name for t in log_tasks]
            if todo_titles:
                vals['custom_todo_json'] = json.dumps(todo_titles, ensure_ascii=False)
                vals['diagnostic_parts_note'] = "\n".join([f"- {t.name}" for t in log_tasks])
                vals['stock_status'] = 'envoye_stock'

            if vals:
                self.write(vals)

            # 5. Injection NON-DESTRUCTIVE des micro-tâches dans l'atelier (sans écraser les tâches terminées)
            if todo_titles:
                self.action_generate_specialty_checklist(custom_todo_tasks=todo_titles, replace_existing=False)

            # 6. Traitement des dégâts masqués / Avenant
            if detected_hidden_damage and self.claim_id:
                amendment = self.env['garage.insurance.amendment'].create({
                    'claim_id': self.claim_id.id,
                    'diagnostic_log_id': diagnostic_log.id,
                    'name': _("Avenant Dégâts Masqués (Diag %s)") % diagnostic_log.name,
                    'reason': 'hidden_part',
                    'description': transcription_summary or transcription or _("Dégât masqué découvert au démontage."),
                    'parts_amount_untaxed': 0.0,
                    'labor_amount_untaxed': sum(t.labor_hours * 150.0 for t in log_tasks),
                    'state': 'draft',
                })
                self.claim_id.message_post(body=Markup(_(
                    "<b>Alerte Dégât Masqué :</b> Avenant initialisé <b>%s</b>."
                ) % amendment.name))

            # 7. Transmission automatique au stock
            if self.diagnostic_parts_note:
                self.action_send_note_to_stock()
        else:
            todo_titles = [t.get('name') or _('Opération Atelier') for t in extracted_tasks]

        return {
            'status': 'ok',
            'log_id': diagnostic_log.id if diagnostic_log else False,
            'log_name': diagnostic_log.name if diagnostic_log else '',
            'transcription': transcription,
            'transcription_summary': transcription_summary,
            'todo_tasks': todo_titles,
            'is_assurance': self.is_assurance if is_persisted else (detected_assurance or bool(is_assurance)),
            'specialty': self.specialty if is_persisted else (detected_specialty or 'mecanique'),
            'is_hidden_damage': detected_hidden_damage,
        }

    def action_open_ai_diagnostic_wizard(self):
        """Ouvre l'assistant de Diagnostic IA et saisie vocale pour le Mécanicien / Chef d'Atelier."""
        self.ensure_one()
        return {
            'name': _("Diagnostic IA & Tâches Dynamiques Atelier"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.ai.diagnostic.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reception_id': self.id,
                'default_specialty': self.specialty,
                'default_is_assurance': self.is_assurance,
                'default_stage_id': self.stage_id.id,
                'default_raw_note': self.diagnostic_notes or self.symptoms or '',
            }
        }

    def action_create_or_view_repair_order(self):
        """Ouvre ou crée l'ordre de réparation associé en transférant les opérations d'atelier."""
        self.ensure_one()
        if not self.repair_order_id:
            labor_commands = []
            # Ne transférer que les vraies interventions mécaniques/carrosserie (Étape 4 personnalisée ou Diag IA)
            # Exclure strictement les tâches administratives (Devis 2A, Accord 2B, Commande 3, Contrôle 5, Livraison 6)
            real_tasks = self.task_ids.filtered(
                lambda t: t.stage_sequence == 40 and (t.is_ai_dynamic or t.diagnostic_task_id)
            )
            # Récupérer les identifiants de tâches déjà gérées dans les logs diagnostiques
            diag_task_ids = set()
            for log in self.diagnostic_log_ids:
                diag_task_ids.update(log.task_line_ids.ids)

            for t in real_tasks:
                if t.diagnostic_task_id and t.diagnostic_task_id.id in diag_task_ids:
                    # Sera synchronisé proprement par action_sync_from_validated_diagnostic()
                    continue
                labor_commands.append(Command.create({
                    'name': t.name,
                    'hours': t.planned_hours or 1.0,
                    'hourly_rate': 0.0,  # Non chiffré tant que le magasinier / chef n'a pas validé le devis
                    'work_type': 'mechanic' if self.specialty != 'carrosserie' else 'bodywork',
                }))

            ro = self.env['repair.order'].create({
                'vehicle_id': self.vehicle_id.id,
                'partner_id': self.customer_id.id,
                'reception_id': self.id,
                'tracking_token': self.tracking_token,
                'odometer_order': self.odometer_in,
                'claim_id': self.claim_id.id if self.claim_id else False,
                'billing_channel': 'insurance' if self.is_assurance or self.claim_id else 'direct',
                'garage_labor_lines': labor_commands,
            })
            self.repair_order_id = ro.id

            if self.claim_id and not self.claim_id.repair_order_id:
                self.claim_id.repair_order_id = ro.id

            # Synchronisation automatique des pièces et opérations du diagnostic validé si présent
            ro.action_sync_from_validated_diagnostic()

        return {
            'name': _("Ordre de Réparation %s", self.repair_order_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': self.repair_order_id.id,
            'view_mode': 'form',
        }

    def action_open_magasinier_devis_cockpit(self):
        """Action rapide Magasinier : Ouvre le chiffrage de l'ordre de réparation avec accès direct aux pièces et audios."""
        self.ensure_one()
        if not self.repair_order_id:
            self.action_create_or_view_repair_order()
        return {
            'name': _("Cockpit Magasinier • Chiffrage Devis %s", self.repair_order_id.name or self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': self.repair_order_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'active_reception_id': self.id,
            }
        }

    def action_create_or_view_claim(self):
        """Ouvre ou crée le dossier sinistre lié à cette réception."""
        self.ensure_one()
        if not self.claim_id:
            default_insurance = self.env['res.partner'].search([('is_insurance_company', '=', True)], limit=1)
            claim = self.env['garage.insurance.claim'].create({
                'claim_number': _("SIN-%s") % (self.name or "NOUVEAU"),
                'vehicle_id': self.vehicle_id.id,
                'customer_id': self.customer_id.id,
                'insurance_id': default_insurance.id if default_insurance else False,
                'reception_id': self.id,
                'repair_order_id': self.repair_order_id.id if self.repair_order_id else False,
                'damage_notes': f"{self.bodywork_notes or ''}\n{self.symptoms or ''}".strip(),
                'attachment_ids': [Command.set(self.attachment_ids.ids)],
                'carte_grise_ids': [Command.set(self.carte_grise_ids.ids)],
                'permis_ids': [Command.set(self.permis_ids.ids)],
                'constat_ids': [Command.set(self.constat_ids.ids)],
            })
            self.claim_id = claim.id
            self.is_assurance = True
            if self.repair_order_id and not self.repair_order_id.claim_id:
                self.repair_order_id.claim_id = claim.id
        return {
            'name': _("Dossier Sinistre %s", self.claim_id.claim_number),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.insurance.claim',
            'res_id': self.claim_id.id,
            'view_mode': 'form',
        }

    def action_view_repair_order(self):
        """Ouvre l'ordre de réparation associé à cette fiche de réception."""
        self.ensure_one()
        if not self.repair_order_id:
            return self.action_create_or_view_repair_order()
        return {
            'name': _("Ordre de Réparation"),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': self.repair_order_id.id,
            'view_mode': 'form',
        }

    def action_reception_send_whatsapp_quote(self):
        """Délègue l'envoi du devis WhatsApp à l'ordre de réparation lié."""
        self.ensure_one()
        if not self.repair_order_id:
            raise UserError(_("Veuillez d'abord créer ou lier un ordre de réparation."))
        return self.repair_order_id.action_send_whatsapp_quote()

    def action_reception_open_payment_wizard(self):
        """Ouvre l'assistant de caisse / encaissement au guichet lié à l'ordre de réparation."""
        self.ensure_one()
        if not self.repair_order_id:
            raise UserError(_("Veuillez d'abord créer ou lier un ordre de réparation."))
        return self.repair_order_id.action_open_payment_recovery_wizard()

    def action_reception_print_bl(self):
        """Génère et imprime le Bon de Travail / BL Atelier depuis la fiche réception."""
        self.ensure_one()
        if not self.repair_order_id:
            raise UserError(_("Veuillez d'abord créer ou lier un ordre de réparation."))
        return self.repair_order_id.action_generate_bl()

    def action_reception_open_billing_wizard(self):
        """Ouvre l'assistant de conversion en facture fiscale officielle lié à l'ordre de réparation."""
        self.ensure_one()
        if not self.repair_order_id:
            raise UserError(_("Veuillez d'abord créer ou lier un ordre de réparation."))
        return self.repair_order_id.action_open_billing_wizard()

    def action_open_pin_wizard(self):
        """Ouvre l'assistant de validation par code PIN pour la tablette partagée de l'atelier."""
        self.ensure_one()
        return {
            'name': _("Pointage Opérateur & Validation par PIN"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.operator.pin.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_reception_id': self.id,
                'default_stage_id': self.stage_id.id,
            }
        }

    # =========================================================================
    # ACTIONS DU PROTOCOLE HÉRO UNIQUE (1 BOUTON D'AVANCEMENT PAR ÉTAPE)
    # =========================================================================

    def action_advance_to_quote(self):
        """Étape 10 -> Étape 20 : Valide l'accueil et transmet le véhicule au magasinier pour chiffrage."""
        self.ensure_one()
        stage_20 = self.env['garage.workshop.stage'].search([('sequence', '=', 20)], limit=1)
        if stage_20:
            self.write({'stage_id': stage_20.id})
        if self.stock_status in (False, 'attente_diag'):
            self.write({'stock_status': 'envoye_stock'})
        stage10_tasks = self.task_ids.filtered(lambda t: t.stage_sequence == 10)
        for t in stage10_tasks:
            t.with_context(auto_workflow_sync=True).write({
                'state': '1_done',
                'is_done': True,
                'completed_date': fields.Datetime.now()
            })
        self.message_post(body=Markup(_("<b>Accueil terminé :</b> Le véhicule est transmis au Magasinier pour chiffrage du devis.")))
        return True

    def action_advance_to_accord(self):
        """Étape 20 -> Étape 30 : Le devis est prêt, passe à l'étape d'accord client / assurance."""
        self.ensure_one()
        stage_30 = self.env['garage.workshop.stage'].search([('sequence', '=', 30)], limit=1)
        if stage_30:
            self.write({'stage_id': stage_30.id})
        self.message_post(body=Markup(_("<b>Chiffrage Devis Prêt :</b> Dossier transmis pour validation de l'accord client / assurance.")))
        return True

    def action_advance_to_repair(self):
        """Étape 30 -> Étape 40 : L'accord est validé, démarre officiellement les travaux atelier."""
        self.ensure_one()
        stage_40 = self.env['garage.workshop.stage'].search([('sequence', '=', 40)], limit=1)
        if stage_40:
            self.write({'stage_id': stage_40.id})
        if self.repair_order_id and self.repair_order_id.state in ('draft', 'confirmed'):
            try:
                if hasattr(self.repair_order_id, 'action_repair_start'):
                    self.repair_order_id.action_repair_start()
                else:
                    self.repair_order_id.action_validate()
            except Exception:
                pass
        self.message_post(body=Markup(_("<b>Travaux Atelier Démarrés :</b> Réparations mécaniques / carrosserie en cours.")))
        return True

    def action_advance_to_control(self):
        """Étape 40 -> Étape 50 : Travaux terminés, passe en contrôle qualité."""
        self.ensure_one()
        stage_50 = self.env['garage.workshop.stage'].search([('sequence', '=', 50)], limit=1)
        if stage_50:
            self.write({'stage_id': stage_50.id})
        stage40_tasks = self.task_ids.filtered(lambda t: t.stage_sequence == 40 and t.state != '1_done')
        for t in stage40_tasks:
            t.with_context(auto_workflow_sync=True).write({
                'state': '1_done',
                'is_done': True,
                'completed_date': fields.Datetime.now()
            })
        self.message_post(body=Markup(_("<b>Travaux Atelier Achevés :</b> Le véhicule entre en Contrôle Qualité final.")))
        return True

    def action_advance_to_ready(self):
        """Étape 50 -> Étape 60 : Contrôle qualité validé, véhicule prêt pour restitution."""
        self.ensure_one()
        stage_60 = self.env['garage.workshop.stage'].search([('sequence', '=', 60)], limit=1)
        if stage_60:
            self.write({'stage_id': stage_60.id})
        stage50_tasks = self.task_ids.filtered(lambda t: t.stage_sequence == 50 and t.state != '1_done')
        for t in stage50_tasks:
            t.with_context(auto_workflow_sync=True).write({
                'state': '1_done',
                'is_done': True,
                'completed_date': fields.Datetime.now()
            })
        self.message_post(body=Markup(_("<b>Contrôle Qualité Validé :</b> Le véhicule est marqué PRÊT pour restitution au client.")))
        return True

    def _check_and_auto_advance_stage(self, completed_stage, operator=False):
        """Vérifie si toutes les micro-tâches de l'étape sont achevées et avance automatiquement."""
        self.ensure_one()
        if not completed_stage:
            return False

        stage_tasks = self.task_ids.filtered(lambda t: t.stage_id == completed_stage)
        if stage_tasks and all(t.is_done or t.state == '1_done' for t in stage_tasks):
            # Recherche de la prochaine étape
            next_stage = self.env['garage.workshop.stage'].search(
                [('sequence', '>', completed_stage.sequence)],
                order='sequence, id', limit=1
            )
            if next_stage:
                # Interlock Sinistre si entrée dans l'étape 4
                if next_stage.sequence >= 40 and (self.is_assurance or self.claim_id):
                    if self.claim_id and (self.claim_id.state not in ('accord_approved', 'in_repair', 'repaired') or self.claim_id.client_accord_status != 'approved'):
                        return False
                    elif not self.claim_id and self.statut_expertise != 'accord_valide':
                        return False

                # Gate Stock : bloquer l'entrée en Travaux si les pièces sont toujours en attente de diagnostic
                if next_stage.sequence >= 40 and completed_stage.sequence < 40:
                    if self.stock_status == 'attente_diag':
                        return False

                op_name = operator.name if operator else (self.current_operator_id.name if self.current_operator_id else "Opérateur")
                self.write({'stage_id': next_stage.id})
                self.message_post(body=Markup(_(
                    "<b>Avancement Automatique d'Étape :</b> Toutes les opérations de l'étape <b>%s</b> ont été complétées avec succès par <b>%s</b>.<br/>"
                    "Le véhicule passe automatiquement à l'étape : <b>%s</b>."
                ) % (completed_stage.name, op_name, next_stage.name)))
                return True
        return False

    def _notify_customer_stage_change(self, old_stage, new_stage):
        """Envoie une notification WhatsApp rassurante et professionnelle au client avec lien magique."""
        self.ensure_one()
        phone = self.customer_phone or (self.customer_id and self.customer_id.phone)
        if not phone:
            return

        tracking_url = self._get_tracking_url()
        client_name = self.customer_id.name or "Client"
        plate = self.license_plate or "votre véhicule"

        msg = (
            f"🚗 *Garage Pro - Suivi des Travaux*\n\n"
            f"Bonjour {client_name},\n"
            f"Votre véhicule *{plate}* vient de franchir une nouvelle étape :\n"
            f"👉 *{new_stage.name}*\n\n"
            f"Suivez en direct l'avancement technique de l'atelier sur votre espace sécurisé :\n"
            f"{tracking_url}\n\n"
            f"Nos équipes restent à votre entière disposition."
        )

        send_garage_whatsapp(self.env, phone, msg)

    def action_send_whatsapp_tracking(self):
        """Construit et envoie la notification WhatsApp avec le lien de suivi sécurisé."""
        self.ensure_one()
        phone = self.customer_phone or (self.customer_id and self.customer_id.phone)
        if not phone:
            raise UserError(_("Le client n'a aucun numéro de téléphone renseigné."))

        tracking_url = self._get_tracking_url()
        client_name = self.customer_id.name or "Client"
        plate = self.license_plate or "votre véhicule"

        msg = (
            f"Bonjour {client_name},\n\n"
            f"Votre véhicule *{plate}* est bien pris en charge chez *Garage Pro*.\n\n"
            f"Suivez l'avancement des réparations en direct, les photos de l'atelier et votre devis sur votre lien sécurisé :\n"
            f"{tracking_url}\n\n"
            f"Notre équipe reste à votre entière disposition."
        )

        success, info, wa_link = send_garage_whatsapp(self.env, phone, msg)
        self.message_post(body=Markup(_("<b>Notification WhatsApp transmise :</b> %s<br/>Lien de suivi : <a href='%s' target='_blank'>Portail Client</a>") % (info, tracking_url)))

        if wa_link and ("wa.me" in wa_link or "whatsapp.com" in wa_link):
            return {'type': 'ir.actions.act_url', 'url': wa_link, 'target': 'new'}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("WhatsApp Envoyé"),
                'message': _("Notification transmise avec succès à %s", phone),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_open_tracking_portal(self):
        """Ouvre le portail client dans un nouvel onglet pour prévisualisation."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self._get_tracking_url(),
            'target': 'new',
        }

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})
            if rec.repair_order_id and rec.repair_order_id.state in ('draft', 'under_repair', 'confirmed'):
                try:
                    rec.repair_order_id.action_repair_cancel()
                except Exception:
                    rec.repair_order_id.write({'state': 'cancel'})
            if rec.claim_id and rec.claim_id.state not in ('paid', 'closed'):
                rec.claim_id.write({'state': 'cancel'})

    def action_reset_draft(self):
        stage_1 = self.env['garage.workshop.stage'].search([('code', '=', 'reception')], limit=1)
        if not stage_1:
            stage_1 = self.env['garage.workshop.stage'].search([], order='sequence, id', limit=1)
        for rec in self:
            rec.write({
                'state': 'draft',
                'active': True,
                'stage_id': stage_1.id if stage_1 else rec.stage_id.id,
            })

    def unlink(self):
        for rec in self:
            if rec.repair_order_id and rec.repair_order_id.state in ('draft', 'cancel'):
                rec.repair_order_id.unlink()
            if rec.claim_id and rec.claim_id.state in ('draft', 'cancel'):
                rec.claim_id.unlink()
        return super().unlink()
