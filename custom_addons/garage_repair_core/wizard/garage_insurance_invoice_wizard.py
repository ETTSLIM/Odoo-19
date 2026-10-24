# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError


class GarageInsuranceInvoiceWizard(models.TransientModel):
    _name = 'garage.insurance.invoice.wizard'
    _description = "Assistant de Facturation Scindée Sinistre & Assurance"

    claim_id = fields.Many2one('garage.insurance.claim', string="Dossier Sinistre", required=True)
    claim_number = fields.Char(related='claim_id.claim_number', readonly=True)
    license_plate = fields.Char(related='claim_id.license_plate', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    # Compagnie d'Assurance
    insurance_id = fields.Many2one(related='claim_id.insurance_id', string="Compagnie d'Assurance", readonly=True)
    insurance_ice = fields.Char(related='insurance_id.ice', string="ICE Compagnie", readonly=True)

    # Client Assuré
    customer_id = fields.Many2one(related='claim_id.customer_id', string="Client / Assuré", readonly=True)
    customer_cin = fields.Char(related='customer_id.cin', string="CIN Assuré", readonly=True)

    # Journal & Date
    journal_id = fields.Many2one('account.journal', string="Journal des Ventes", required=True,
                                 domain=[('type', '=', 'sale')],
                                 default=lambda self: self.env['account.journal'].search([('type', '=', 'sale')], limit=1))
    invoice_date = fields.Date(string="Date de Facturation", default=fields.Date.context_today, required=True)

    # Montants de l'Accord Expert
    expert_accord_amount_ttc = fields.Monetary(string="Montant Accord Expert (TTC)", compute='_compute_default_amounts', store=True, readonly=False)

    # Découpage Scindé
    insurance_net_ttc = fields.Monetary(string="Prise en Charge Compagnie (TTC)", compute='_compute_default_amounts', store=True, readonly=False)
    insurance_net_ht = fields.Monetary(string="Prise en Charge Compagnie (HT)", compute='_compute_ht_amounts', store=True, readonly=False)

    customer_share_ttc = fields.Monetary(string="Franchise & Vétusté Client (TTC)", compute='_compute_default_amounts', store=True, readonly=False)
    customer_share_ht = fields.Monetary(string="Franchise & Vétusté Client (HT)", compute='_compute_ht_amounts', store=True, readonly=False)

    # Options Client
    generate_customer_invoice = fields.Boolean(string="Émettre Facture / Reçu pour la Franchise Client", default=True)

    @api.depends('claim_id')
    def _compute_default_amounts(self):
        for wizard in self:
            claim = wizard.claim_id
            if claim:
                wizard.expert_accord_amount_ttc = claim.expert_accord_amount_ttc
                wizard.insurance_net_ttc = claim.insurance_net_payable
                wizard.customer_share_ttc = claim.customer_payable
            else:
                wizard.expert_accord_amount_ttc = 0.0
                wizard.insurance_net_ttc = 0.0
                wizard.customer_share_ttc = 0.0

    @api.depends('insurance_net_ttc', 'customer_share_ttc')
    def _compute_ht_amounts(self):
        for wizard in self:
            wizard.insurance_net_ht = round(wizard.insurance_net_ttc / 1.20, 2) if wizard.insurance_net_ttc else 0.0
            wizard.customer_share_ht = round(wizard.customer_share_ttc / 1.20, 2) if wizard.customer_share_ttc else 0.0

    def action_generate_split_invoices(self):
        """Crée simultanément la facture d'assurance et la facture/reçu de franchise client."""
        self.ensure_one()
        claim = self.claim_id
        if not claim:
            raise UserError(_("Aucun dossier sinistre associé."))

        if self.insurance_net_ht <= 0 and self.customer_share_ht <= 0:
            raise UserError(_("Le montant total accordé est nul ou invalide."))

        # Recherche de la TVA 20%
        tax = self.env.ref('garage_repair_core.tax_tva_20_sale', raise_if_not_found=False)
        if not tax:
            tax = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', 20)], limit=1)
        tax_cmd = [Command.set([tax.id])] if tax else []

        created_invoices = []

        # 1. Facture Compagnie d'Assurance
        if self.insurance_net_ht > 0:
            insurance_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.insurance_id.id,
                'journal_id': self.journal_id.id,
                'invoice_date': self.invoice_date,
                'narration': f"Prise en charge Sinistre N° {claim.claim_number} - Immatriculation: {claim.license_plate} - Véhicule: {claim.vehicle_id.name}",
                'invoice_line_ids': [
                    Command.create({
                        'name': f"Prise en charge Travaux Carrosserie & Peinture - Sinistre N° {claim.claim_number} (Accord {claim.expert_cabinet_id.name or 'Expert'}) - {claim.vehicle_id.name} [{claim.license_plate}]",
                        'quantity': 1.0,
                        'price_unit': self.insurance_net_ht,
                        'tax_ids': tax_cmd,
                    })
                ],
            }
            insurance_invoice = self.env['account.move'].create(insurance_vals)
            claim.insurance_invoice_id = insurance_invoice.id
            created_invoices.append(insurance_invoice.id)

        # 2. Facture ou Reçu Client (Franchise & Vétusté)
        customer_invoice = False
        if self.generate_customer_invoice and self.customer_share_ht > 0:
            customer_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.customer_id.id,
                'journal_id': self.journal_id.id,
                'invoice_date': self.invoice_date,
                'narration': f"Franchise contractuelle & vétusté - Sinistre N° {claim.claim_number} ({claim.insurance_id.name}) - Immat: {claim.license_plate}",
                'invoice_line_ids': [
                    Command.create({
                        'name': f"Quote-part franchise / vétusté sur Sinistre N° {claim.claim_number} - {claim.vehicle_id.name} [{claim.license_plate}]",
                        'quantity': 1.0,
                        'price_unit': self.customer_share_ht,
                        'tax_ids': tax_cmd,
                    })
                ],
            }
            customer_invoice = self.env['account.move'].create(customer_vals)
            claim.customer_invoice_id = customer_invoice.id
            created_invoices.append(customer_invoice.id)

        # Mise à jour de l'état du sinistre
        claim.write({'state': 'invoiced'})

        # Liaison avec l'ordre de réparation si présent et dénouement fiscal des pièces officielles
        target_inv = claim.insurance_invoice_id or customer_invoice
        if claim.repair_order_id and target_inv:
            ro = claim.repair_order_id
            ro.write({
                'official_invoice_id': target_inv.id,
                'billing_channel': 'insurance',
            })
            for part in ro.garage_parts_lines.filtered(lambda p: p.source_type == 'official' and not p.is_officially_cleared):
                part._ensure_outgoing_stock_move()
                if part.parts_bl_line_id:
                    part.parts_bl_line_id.qty_cleared_officially += part.qty
                part.write({
                    'is_officially_cleared': True,
                    'official_invoice_id': target_inv.id,
                })

        claim.message_post(body=Markup(_(
            "<b>Facturation Scindée Émise avec Succès !</b><br/>"
            "• Facture Compagnie (%s) : <b>%s MAD TTC</b><br/>"
            "• Facture / Franchise Client (%s) : <b>%s MAD TTC</b>"
        )) % (
            self.insurance_id.name, self.insurance_net_ttc,
            self.customer_id.name, self.customer_share_ttc if customer_invoice else 0.0
        ))

        # Affichage des factures créées
        if len(created_invoices) == 1:
            return {
                'name': _("Facture Émise"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': created_invoices[0],
                'view_mode': 'form',
            }
        else:
            return {
                'name': _("Factures Scindées Sinistre"),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_invoices)],
            }
