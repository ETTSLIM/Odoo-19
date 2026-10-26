# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError

class GarageDiagnosticLog(models.Model):
    _name = 'garage.diagnostic.log'
    _description = "Journal de Diagnostic Vocal & Multi-Audio"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string="Référence", required=True, copy=False, readonly=True, default=lambda self: _('Nouveau'))
    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", required=True, ondelete='cascade', tracking=True)
    vehicle_id = fields.Many2one('fleet.vehicle', related='reception_id.vehicle_id', string="Véhicule", store=True, readonly=True)
    license_plate = fields.Char(related='reception_id.license_plate', string="Immatriculation", store=True, readonly=True)
    repair_order_id = fields.Many2one('repair.order', related='reception_id.repair_order_id', string="Ordre de Réparation", store=True, readonly=True)
    claim_id = fields.Many2one('garage.insurance.claim', related='reception_id.claim_id', string="Dossier Sinistre", store=True, readonly=True)
    
    operator_id = fields.Many2one('garage.workshop.operator', string="Intervenant / Opérateur", tracking=True)
    stage_id = fields.Many2one('garage.workshop.stage', string="Étape d'Intervention", tracking=True)
    stage_sequence = fields.Integer(related='stage_id.sequence', string="Séquence Étape", store=True)

    audio_file = fields.Binary(string="Fichier Audio", attachment=True)
    audio_filename = fields.Char(string="Nom du Fichier Audio", default="diagnostic_audio.mp3")
    audio_mimetype = fields.Char(string="Type MIME", default="audio/mp4")
    audio_player_html = fields.Html(string="Lecteur Audio", compute='_compute_audio_player_html', sanitize=False)

    transcription_raw = fields.Text(string="Transcription Verbatim (Darija / Français)")
    transcription_summary = fields.Text(string="Synthèse / Notes Contextuelles")

    task_line_ids = fields.One2many('garage.diagnostic.log.task', 'log_id', string="Micro-tâches & Fournitures")
    task_count = fields.Integer(string="Nb. Tâches", compute='_compute_task_counts', store=True)
    validated_task_count = fields.Integer(string="Nb. Tâches Validées", compute='_compute_task_counts', store=True)

    is_hidden_damage = fields.Boolean(string="Dégât Masqué (Démontage)", default=False, tracking=True,
                                      help="Si activé, déclenche automatiquement la notification assurance et l'étape 2D.")
    
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted_to_stock', 'Transmis Magasinier'),
        ('validated', 'Validé par Magasinier'),
        ('invoiced', 'Intégré à l\'OR'),
    ], string="Statut", default='submitted_to_stock', tracking=True)

    @api.depends('audio_file', 'audio_filename', 'audio_mimetype')
    def _compute_audio_player_html(self):
        for rec in self:
            if rec.audio_file and rec.id:
                fname = rec.audio_filename or 'diagnostic.mp3'
                mime = rec.audio_mimetype or 'audio/mp4'
                audio_src = f"/web/content/garage.diagnostic.log/{rec.id}/audio_file/{fname}"
                rec.audio_player_html = Markup(
                    f'<div class="o_garage_audio_player p-2 border rounded bg-white shadow-sm">'
                    f'  <div class="d-flex align-items-center mb-1 text-muted small">'
                    f'    <i class="fa fa-headphones me-1" title="Audio"/>'
                    f'    <span>Fichier : <strong>{fname}</strong></span>'
                    f'  </div>'
                    f'  <audio controls="controls" preload="metadata" style="width: 100%; height: 38px;">'
                    f'    <source src="{audio_src}" type="{mime}"/>'
                    f'    Votre navigateur ne prend pas en charge la lecture audio HTML5.'
                    f'  </audio>'
                    f'</div>'
                )
            else:
                rec.audio_player_html = Markup(
                    '<div class="p-2 border rounded bg-light text-muted small">'
                    '  <i class="fa fa-info-circle me-1" title="Aucun enregistrement audio"/>'
                    '  Aucun enregistrement audio rattaché.'
                    '</div>'
                )

    @api.depends('task_line_ids', 'task_line_ids.is_validated')
    def _compute_task_counts(self):
        for rec in self:
            rec.task_count = len(rec.task_line_ids)
            rec.validated_task_count = len(rec.task_line_ids.filtered(lambda t: t.is_validated))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garage.diagnostic.log') or _('Nouveau')
        return super().create(vals_list)

    def action_submit_to_stock(self):
        self.ensure_one()
        self.write({'state': 'submitted_to_stock'})
        self.reception_id.message_post(body=Markup(_(
            "<b>Diagnostic Vocal %s transmis au Magasinier</b> : %d tâches détectées."
        ) % (self.name, self.task_count)))
        return True

    def action_validate_and_apply_to_ro(self):
        """Valide les micro-tâches sélectionnées par le magasinier et propage vers l'OR et l'Atelier."""
        self.ensure_one()
        reception = self.reception_id
        if not reception:
            raise UserError(_("Aucune fiche de réception associée à ce diagnostic."))

        # S'assurer qu'un Ordre de Réparation existe
        ro = reception.repair_order_id
        if not ro:
            ro_action = reception.action_create_or_view_repair_order()
            ro = reception.repair_order_id

        # Target stage for workshop micro-tasks
        stage = self.stage_id
        if not stage:
            # Par défaut, étape 40 (Travaux Atelier) ou étape active de la réception
            stage = self.env['garage.workshop.stage'].search([('sequence', '=', 40)], limit=1) or reception.stage_id

        tasks_to_apply = self.task_line_ids.filtered(lambda t: t.is_validated)
        if not tasks_to_apply:
            raise UserError(_("Aucune micro-tâche n'est cochée comme validée par le magasinier."))

        part_commands = []
        labor_commands = []
        workshop_tasks_vals = []

        # Déterminer la séquence maximale des tâches existantes pour conserver l'ordre
        existing_seq = 10
        if reception.task_ids:
            existing_seq = max(reception.task_ids.mapped('sequence') or [10]) + 5

        for t in tasks_to_apply:
            # 1. Pièce détachée si requis
            if (t.requires_new_part or t.product_id) and ro:
                part_vals = {
                    'repair_id': ro.id,
                    'name': t.name or (t.product_id.display_name if t.product_id else _("Pièce Neuve")),
                    'product_id': t.product_id.id if t.product_id else False,
                    'qty': t.product_qty or 1.0,
                    'cost_price': t.cost_price or (t.product_id.standard_price if t.product_id else 0.0),
                    'sale_price': t.unit_price or (t.product_id.list_price if t.product_id else 0.0),
                    'source_type': 'operational',
                }
                new_part = self.env['garage.repair.part.line'].create(part_vals)
                t.created_part_line_id = new_part.id

            # 2. Main-d'œuvre si heures > 0
            if (t.labor_hours > 0 or not t.requires_new_part) and ro:
                labor_vals = {
                    'repair_id': ro.id,
                    'name': f"{t.name} ({t.component or 'Opération'})",
                    'work_type': 'bodywork' if reception.specialty == 'carrosserie' else 'mechanic',
                    'hours': t.labor_hours or 1.0,
                    'hourly_rate': t.hourly_rate or 150.0,
                    'hourly_cost': 50.0,
                }
                new_labor = self.env['garage.repair.labor.line'].create(labor_vals)
                t.created_labor_line_id = new_labor.id

            # 3. Sous-tâche Atelier (conservant les tâches antérieures terminées)
            task_instruction = f"Action : {t.action.upper()} • Organe : {t.component or 'Standard'}"
            if t.rectification_note:
                task_instruction += f"\nNote Contextuelle : {t.rectification_note}"

            w_task_vals = {
                'reception_id': reception.id,
                'stage_id': stage.id,
                'name': f"[Diag {self.name}] {t.name}",
                'description': task_instruction,
                'planned_hours': t.labor_hours or 0.5,
                'is_ai_dynamic': True,
                'diagnostic_task_id': t.id,
                'is_hidden_damage': self.is_hidden_damage,
                'sequence': existing_seq,
                'state': '04_waiting_normal',
            }
            existing_seq += 5
            created_w_task = self.env['garage.reception.task'].with_context(auto_workflow_sync=True).create(w_task_vals)
            t.created_task_id = created_w_task.id

        # 4. Traitement des dégâts masqués / Avenant Sinistre
        if self.is_hidden_damage and reception.claim_id:
            claim = reception.claim_id
            parts_total = sum(t.unit_price * t.product_qty for t in tasks_to_apply if t.requires_new_part or t.product_id)
            labor_total = sum(t.labor_hours * t.hourly_rate for t in tasks_to_apply if t.labor_hours > 0)
            
            amendment = self.env['garage.insurance.amendment'].create({
                'claim_id': claim.id,
                'name': _("Avenant Dégâts Masqués - Diag %s") % self.name,
                'reason': 'hidden_part',
                'description': _("Dégâts cachés découverts au démontage / diagnostic :\n%s") % (self.transcription_summary or self.transcription_raw or ""),
                'parts_amount_untaxed': parts_total,
                'labor_amount_untaxed': labor_total,
                'state': 'draft',
            })
            claim.message_post(body=Markup(_(
                "<b>Alerte Dégât Masqué (Étape 2D) :</b> Nouvel avenant généré <b>%s</b> (+%s MAD HT)."
            ) % (amendment.name, amendment.total_untaxed)))

        self.write({'state': 'invoiced'})
        reception.message_post(body=Markup(_(
            "<b>Cockpit Magasinier :</b> Diagnostic <b>%s</b> validé. "
            "%d opérations et pièces injectées dans l'Ordre de Travail et le Kanban Atelier."
        ) % (self.name, len(tasks_to_apply))))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Diagnostic Validé & Appliqué"),
                'message': _("%d micro-tâches ont été synchronisées avec succès.", len(tasks_to_apply)),
                'sticky': False,
                'type': 'success',
            }
        }


class GarageDiagnosticLogTask(models.Model):
    _name = 'garage.diagnostic.log.task'
    _description = "Micro-tâche & Requisition du Diagnostic Vocal"
    _order = 'id asc'

    log_id = fields.Many2one('garage.diagnostic.log', string="Journal Diagnostic", required=True, ondelete='cascade')
    name = fields.Char(string="Opération / Action", required=True)
    action = fields.Selection([
        ('replace', 'Remplacement Pièce'),
        ('repair', 'Réparation / Redressage'),
        ('service', 'Entretien / Révision'),
        ('inspect', 'Contrôle / Diagnostic'),
    ], string="Nature Opération", default='repair', required=True)
    component = fields.Char(string="Organe Cible")
    requires_new_part = fields.Boolean(string="Pièce Requise", default=False)
    rectification_note = fields.Char(string="Résolution Auto-Correction")

    product_id = fields.Many2one('product.product', string="Article Magasin (Stock)")
    product_qty = fields.Float(string="Qté Pièce", default=1.0)
    currency_id = fields.Many2one(related='log_id.reception_id.currency_id')
    unit_price = fields.Monetary(string="Prix Vente HT (MAD)", default=0.0)
    cost_price = fields.Monetary(string="Prix Achat HT (MAD)", default=0.0)

    labor_hours = fields.Float(string="Heures MO (h)", default=1.0)
    hourly_rate = fields.Monetary(string="Taux MO (MAD/h)", default=150.0)

    is_validated = fields.Boolean(string="Validé Magasinier", default=True)

    created_task_id = fields.Many2one('garage.reception.task', string="Sous-tâche Atelier", readonly=True)
    created_part_line_id = fields.Many2one('garage.repair.part.line', string="Ligne Pièce OR", readonly=True)
    created_labor_line_id = fields.Many2one('garage.repair.labor.line', string="Ligne MO OR", readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.unit_price = self.product_id.list_price
            self.cost_price = self.product_id.standard_price
            self.requires_new_part = True
            if not self.name or self.name == _("Nouvelle Opération"):
                self.name = self.product_id.display_name
