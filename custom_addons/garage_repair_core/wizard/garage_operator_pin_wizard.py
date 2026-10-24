# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GarageOperatorPinWizard(models.TransientModel):
    _name = 'garage.operator.pin.wizard'
    _description = "Assistant de Validation Tablette Atelier par Code PIN"

    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", required=True)
    stage_id = fields.Many2one('garage.workshop.stage', string="Étape Courante", required=True)
    pin_code = fields.Char(string="Code PIN Opérateur (4 chiffres)", required=True, size=4,
                           help="Saisissez votre code PIN personnel à 4 chiffres.")

    action_type = fields.Selection([
        ('complete_stage_tasks', "Valider & Clôturer les opérations de l'étape"),
        ('send_diagnostic_note', "Transmettre Note Diagnostic & Pièces au Stock"),
        ('advance_stage', "Passer directement à l'étape suivante"),
    ], string="Action Atelier", default='complete_stage_tasks', required=True)

    diagnostic_note = fields.Text(string="Note Complémentaire / Pièces Demandées")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        reception_id = res.get('reception_id') or ctx.get('default_reception_id')
        if reception_id:
            rec = self.env['garage.reception'].browse(reception_id)
            res['reception_id'] = rec.id
            res['stage_id'] = rec.stage_id.id if rec.stage_id else ctx.get('default_stage_id')
            if rec.diagnostic_parts_note:
                res['diagnostic_note'] = rec.diagnostic_parts_note
        return res

    def action_confirm_pin(self):
        self.ensure_one()
        pin = (self.pin_code or "").strip()
        if not pin or len(pin) != 4 or not pin.isdigit():
            raise UserError(_("Veuillez saisir un code PIN valide composé de 4 chiffres."))

        # Recherche de l'opérateur correspondant
        operator = self.env['garage.workshop.operator'].search([('pin_code', '=', pin), ('active', '=', True)], limit=1)
        if not operator:
            raise UserError(_("Code PIN Incorrect : Aucun opérateur d'atelier ne correspond à ce code."))

        # Vérification des habilitations
        if not operator.verify_pin(pin, target_stage_id=self.stage_id.id):
            raise UserError(_(
                "Habilitation Insuffisante : L'opérateur '%s' (%s) n'est pas autorisé à intervenir sur l'étape '%s'.",
                operator.name, operator.role, self.stage_id.name
            ))

        rec = self.reception_id
        rec.current_operator_id = operator.id

        if self.action_type == 'complete_stage_tasks':
            stage_tasks = rec.task_ids.filtered(lambda t: t.stage_id == self.stage_id and not t.is_done)
            for t in stage_tasks:
                t.write({
                    'is_done': True,
                    'completed_by_operator_id': operator.id,
                    'completed_date': fields.Datetime.now(),
                })
            rec.message_post(body=_(
                "✅ <b>Pointage Opérateur PIN :</b> <b>%s</b> (%s) a validé %d opération(s) sur l'étape <b>%s</b>."
            ) % (operator.name, operator.role, len(stage_tasks), self.stage_id.name))
            # Déclenche la vérification d'avancement automatique
            rec._check_and_auto_advance_stage(self.stage_id, operator=operator)

        elif self.action_type == 'send_diagnostic_note':
            if self.diagnostic_note:
                rec.diagnostic_parts_note = self.diagnostic_note
            rec.action_send_note_to_stock()
            rec.message_post(body=_(
                "📨 <b>Note envoyée au Stock par :</b> <b>%s</b> (%s)"
            ) % (operator.name, operator.role))

        elif self.action_type == 'advance_stage':
            next_stage = self.env['garage.workshop.stage'].search(
                [('sequence', '>', self.stage_id.sequence)],
                order='sequence, id', limit=1
            )
            if next_stage:
                rec.write({'stage_id': next_stage.id})
                rec.message_post(body=_(
                    "⏩ <b>Étape Avancée Manuellement par PIN :</b> <b>%s</b> (%s) a basculé le véhicule vers <b>%s</b>."
                ) % (operator.name, operator.role, next_stage.name))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Pointage Validé"),
                'message': _("Opération validée avec succès par %s.", operator.name),
                'sticky': False,
                'type': 'success',
            }
        }
