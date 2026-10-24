# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GaragePaymentRecoveryWizard(models.TransientModel):
    _name = 'garage.payment.recovery.wizard'
    _description = "Guichet d'Encaissement & Dénouement Règlement"

    repair_order_id = fields.Many2one('repair.order', string="Ordre de Réparation / BL", required=True)
    partner_id = fields.Many2one(related='repair_order_id.partner_id', string="Client", readonly=True)
    license_plate = fields.Char(related='repair_order_id.license_plate', string="Immatriculation", readonly=True)
    currency_id = fields.Many2one(related='repair_order_id.currency_id')

    # Informations Fiscales Modifiables au Guichet
    customer_type = fields.Selection(related='partner_id.customer_type', readonly=True)
    customer_cin = fields.Char(string="CIN Client (Particulier)", store=False)
    customer_ice = fields.Char(string="ICE Société (15 chiffres)", store=False)

    # Chiffres du Dossier
    amount_total = fields.Monetary(string="Total Réparation", compute='_compute_amounts')
    amount_already_paid = fields.Monetary(string="Déjà Encaissé", compute='_compute_amounts')
    amount_residual = fields.Monetary(string="Reste à Payer", compute='_compute_amounts')

    # Saisie Encaissement
    payment_amount = fields.Monetary(string="Montant Encaissé Aujourd'hui", required=True)
    payment_method = fields.Selection([
        ('cash', 'Espèces (Caisse Atelier - BL Interne)'),
        ('tpe', 'TPE / Carte Bancaire (Traçable sur Compte Bancaire)'),
        ('cheque', 'Chèque Bancaire (Traçable sur Compte Bancaire)'),
        ('transfer', 'Virement Bancaire (Traçable sur Compte Bancaire)'),
    ], string="Mode de Règlement", default='cash', required=True)

    transaction_ref = fields.Char(string="N° Chèque / Réf Ticket TPE / Réf Virement")
    bank_name = fields.Char(string="Banque Émettrice (ex: Attijari, BCP, BMCE, CIH)")
    client_requested_invoice = fields.Boolean(string="Le client exige une Facture Fiscale Officielle (TVA 20%)", default=False)

    # Détection Traçabilité Bancaire & Obligation Fiscale
    is_bank_traceable = fields.Boolean(string="Est Traçable Bancairement", compute='_compute_compliance')
    requires_official_invoice = fields.Boolean(string="Exige Facture Fiscale", compute='_compute_compliance')
    is_missing_tax_id = fields.Boolean(string="Identifiant Fiscal Manquant", compute='_compute_compliance')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ro_id = res.get('repair_order_id') or self.env.context.get('default_repair_order_id')
        if ro_id:
            ro = self.env['repair.order'].browse(ro_id)
            partner = ro.partner_id
            if partner:
                res['customer_cin'] = partner.cin or ''
                res['customer_ice'] = partner.ice or ''
            res['payment_amount'] = ro.amount_residual or (ro.amount_total_ttc if ro.billing_channel == 'official_invoice' else ro.amount_untaxed_total)
        return res

    @api.depends('repair_order_id')
    def _compute_amounts(self):
        for wizard in self:
            ro = wizard.repair_order_id
            if ro:
                target = ro.amount_total_ttc if ro.billing_channel == 'official_invoice' else ro.amount_untaxed_total
                wizard.amount_total = target
                wizard.amount_already_paid = ro.amount_paid
                wizard.amount_residual = max(0.0, target - ro.amount_paid)
            else:
                wizard.amount_total = 0.0
                wizard.amount_already_paid = 0.0
                wizard.amount_residual = 0.0

    @api.depends('payment_method', 'client_requested_invoice', 'customer_cin', 'customer_ice', 'partner_id')
    def _compute_compliance(self):
        for wizard in self:
            traceable = wizard.payment_method in ('tpe', 'cheque', 'transfer')
            wizard.is_bank_traceable = traceable
            wizard.requires_official_invoice = traceable or wizard.client_requested_invoice

            missing = False
            if wizard.requires_official_invoice and wizard.partner_id:
                cin = wizard.customer_cin or wizard.partner_id.cin
                ice = wizard.customer_ice or wizard.partner_id.ice
                if wizard.customer_type == 'company' and not ice:
                    missing = True
                elif wizard.customer_type == 'individual' and not cin:
                    missing = True
            wizard.is_missing_tax_id = missing

    @api.onchange('payment_method')
    def _onchange_payment_method(self):
        if self.payment_method in ('tpe', 'cheque', 'transfer'):
            self.client_requested_invoice = True

    def _sync_partner_tax_id(self):
        """Met à jour le CIN ou l'ICE du partenaire s'il a été saisi au guichet."""
        self.ensure_one()
        partner = self.repair_order_id.partner_id
        if partner:
            vals = {}
            if self.customer_cin and self.customer_cin != partner.cin:
                vals['cin'] = self.customer_cin.strip().upper()
            if self.customer_ice and self.customer_ice != partner.ice:
                vals['ice'] = self.customer_ice.strip()
            if vals:
                partner.write(vals)

    def _create_payment_record(self):
        """Crée la ligne d'historique de règlement et met à jour l'ordre de réparation."""
        self.ensure_one()
        ro = self.repair_order_id
        if not ro:
            raise UserError(_("Aucun ordre de réparation lié."))

        if self.payment_amount <= 0:
            raise UserError(_("Veuillez renseigner un montant d'encaissement supérieur à zéro."))

        self._sync_partner_tax_id()

        # Enregistrement du règlement
        payment = self.env['garage.repair.payment'].create({
            'repair_id': ro.id,
            'amount': self.payment_amount,
            'payment_method': self.payment_method,
            'transaction_ref': self.transaction_ref,
            'bank_name': self.bank_name,
            'cashier_id': self.env.user.id,
        })

        method_labels = dict(self._fields['payment_method'].selection)
        method_name = method_labels.get(self.payment_method, self.payment_method)

        ro.message_post(
            body=Markup(
                "<b>Règlement Encaissé au Guichet :</b> %s MAD par <b>%s</b> (Réf: %s) par %s."
            ) % (f"{self.payment_amount:,.2f}", method_name, self.transaction_ref or 'S/Réf', self.env.user.name)
        )

        # Auto-livraison du véhicule si la réparation est achevée et entièrement soldée
        ro._compute_financial_totals()
        if ro.reception_id and ro.payment_status == 'paid' and ro.state == 'done':
            stage_delivered = self.env['garage.workshop.stage'].search([('sequence', '=', 70)], limit=1)
            if stage_delivered and ro.reception_id.stage_sequence < 70:
                ro.reception_id.write({'stage_id': stage_delivered.id})

        return payment

    def action_confirm_payment(self):
        """Valide l'encaissement. Si paiement bancaire ou demande facture, ouvre le moteur fiscal."""
        self.ensure_one()
        ro = self.repair_order_id
        self._create_payment_record()

        # Si le règlement est bancaire traçable ou facture demandée, et que l'OR n'est pas encore facturé officiellement
        if self.requires_official_invoice and not ro.official_invoice_id:
            return ro.action_open_billing_wizard()

        # Sinon, simple encaissement caisse ou OR déjà facturé
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Encaissement Enregistré"),
                'message': _("Règlement de %.2f MAD enregistré avec succès.", self.payment_amount),
                'type': 'success',
                'sticky': False,
            }
        }
