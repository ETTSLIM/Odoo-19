# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError

class GarageBillingWizard(models.TransientModel):
    _name = 'garage.billing.wizard'
    _description = "Assistant de Facturation Fiscale & Moteur d'Équivalence Hybride"

    repair_order_id = fields.Many2one('repair.order', string="Ordre de Réparation / BL", required=True)
    partner_id = fields.Many2one('res.partner', string="Client Facturé", required=True)
    customer_type = fields.Selection(related='partner_id.customer_type', readonly=True)
    customer_ice = fields.Char(related='partner_id.ice', string="ICE", readonly=True)
    customer_cin = fields.Char(related='partner_id.cin', string="CIN", readonly=True)

    journal_id = fields.Many2one('account.journal', string="Journal des Ventes", required=True,
                                domain=[('type', '=', 'sale')],
                                default=lambda self: self.env['account.journal'].search([('type', '=', 'sale')], limit=1))

    invoice_date = fields.Date(string="Date de Facture", default=fields.Date.context_today, required=True)

    tax_treatment = fields.Selection([
        ('add_tax', 'Ajouter TVA 20% en sus (Total Facture = Montant BL + 20%)'),
        ('included_tax', 'Prix du BL considéré TTC (Extraire TVA 20%)'),
    ], string="Traitement de la TVA", default='add_tax', required=True)

    # Pilotage interactif des pourcentages de substitution
    service_percentage = fields.Float(string="% Prestation / Forfait Technique", default=70.0)
    consumable_percentage = fields.Float(string="% Fournitures & Consommables Homologués", default=30.0)
    enable_smart_stock_clearance = fields.Boolean(string="Priorité : Déstocker les pièces fiscales réelles en attente", default=True,
                                                  help="Si coché, remplace les pièces non déclarées par de vraies pièces du stock fiscal en attente de sortie pour assainir les bilans fiscaux.")

    # Vue miroir Atelier Réel (Bon de Travail)
    ro_parts_line_ids = fields.One2many(related='repair_order_id.garage_parts_lines', string="Pièces Atelier Réel", readonly=True)
    ro_labor_line_ids = fields.One2many(related='repair_order_id.garage_labor_lines', string="Lignes Main-d'Œuvre Atelier", readonly=True)
    ro_untaxed_total = fields.Monetary(related='repair_order_id.amount_untaxed_total', string="Total Atelier HT", readonly=True)
    ro_tax_total = fields.Monetary(related='repair_order_id.amount_tax_total', string="TVA Atelier Réelle", readonly=True)
    ro_total_ttc = fields.Monetary(related='repair_order_id.amount_total_ttc', string="Total Atelier TTC", readonly=True)

    fiscal_pool_available_amount = fields.Monetary(string="Stock Fiscal en Magasin", compute='_compute_fiscal_pool')

    def _compute_fiscal_pool(self):
        for wizard in self:
            available_bl_lines = self.env['garage.parts.bl.line'].search([
                ('bl_id.state', 'in', ('received', 'invoiced')),
                ('bl_id.stock_destination', '=', 'official'),
                ('qty_available_shelf', '>', 0),
            ])
            wizard.fiscal_pool_available_amount = sum(
                bl.qty_available_shelf * (bl.suggested_sale_price or (bl.unit_cost * 1.3))
                for bl in available_bl_lines
            )

    # Chiffres clés du dossier atelier
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount_target_untaxed = fields.Monetary(string="Total Vente Atelier Convenu (HT)", compute='_compute_target_amount', store=True)
    amount_parts_operational = fields.Monetary(string="Pièces Non Déclarées à Substituer", compute='_compute_target_amount', store=True)
    amount_parts_official = fields.Monetary(string="Pièces Officielles Directes", compute='_compute_target_amount', store=True)
    amount_labor_real = fields.Monetary(string="Main-d'Œuvre Réelle", compute='_compute_target_amount', store=True)

    # Lignes d'équivalence éditables par le gérant
    line_ids = fields.One2many('garage.billing.wizard.line', 'wizard_id', string="Lignes de Facture Suggérées")

    # Contrôle d'équilibre financier au centime près
    amount_proposed_untaxed = fields.Monetary(string="Total Proposé (HT)", compute='_compute_balance')
    amount_difference = fields.Monetary(string="Écart d'Équilibre", compute='_compute_balance')
    is_balanced = fields.Boolean(string="Est Parfaitement Équilibré", compute='_compute_balance')

    @api.depends('repair_order_id', 'tax_treatment')
    def _compute_target_amount(self):
        for wizard in self:
            ro = wizard.repair_order_id
            if not ro:
                wizard.amount_target_untaxed = 0.0
                wizard.amount_parts_operational = 0.0
                wizard.amount_parts_official = 0.0
                wizard.amount_labor_real = 0.0
                continue

            target = ro.amount_untaxed_total
            op_parts = ro.amount_parts_operational
            off_parts = ro.amount_parts_official
            labor = ro.amount_labor_untaxed

            if wizard.tax_treatment == 'included_tax':
                target = round(target / 1.20, 2)
                op_parts = round(op_parts / 1.20, 2)
                off_parts = round(off_parts / 1.20, 2)
                labor = round(labor / 1.20, 2)

            wizard.amount_target_untaxed = target
            wizard.amount_parts_operational = op_parts
            wizard.amount_parts_official = off_parts
            wizard.amount_labor_real = labor

    @api.depends('line_ids.subtotal', 'amount_target_untaxed')
    def _compute_balance(self):
        for wizard in self:
            proposed = sum(wizard.line_ids.mapped('subtotal'))
            diff = round(wizard.amount_target_untaxed - proposed, 2)
            wizard.amount_proposed_untaxed = proposed
            wizard.amount_difference = diff
            wizard.is_balanced = (abs(diff) < 0.05)

    @api.onchange('service_percentage')
    def _onchange_service_percentage(self):
        self.consumable_percentage = max(0.0, 100.0 - self.service_percentage)
        self._populate_suggested_lines()

    @api.onchange('consumable_percentage')
    def _onchange_consumable_percentage(self):
        self.service_percentage = max(0.0, 100.0 - self.consumable_percentage)
        self._populate_suggested_lines()

    @api.onchange('repair_order_id', 'tax_treatment', 'enable_smart_stock_clearance')
    def _onchange_repair_order_id(self):
        self._populate_suggested_lines()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for wizard in records:
            if not wizard.line_ids and wizard.repair_order_id:
                wizard._populate_suggested_lines()
        return records

    def _populate_suggested_lines(self):
        """Génère la proposition de panachage équivalent selon le stock fiscal disponible et les pourcentages définis."""
        self.ensure_one()
        ro = self.repair_order_id
        if not ro:
            return

        lines = []
        base_sum = 0.0

        # 1. Pièces officielles directes du dossier (Non encore déclarées - Anti-Double-Usage)
        for part in ro.garage_parts_lines.filtered(lambda p: p.source_type == 'official' and not p.is_officially_cleared):
            pu = part.sale_price if self.tax_treatment == 'add_tax' else round(part.sale_price / 1.20, 2)
            base_sum += round(part.qty * pu, 2)
            lines.append(Command.create({
                'part_id': part.id,
                'line_category': 'declared_part',
                'name': f"[Pièce Homologuée] {part.name} ({ro.license_plate})",
                'quantity': part.qty,
                'price_unit': pu,
            }))

        # 2. Main-d'œuvre réelle (conservée 1:1)
        for labor in ro.garage_labor_lines:
            pu = labor.hourly_rate if self.tax_treatment == 'add_tax' else round(labor.hourly_rate / 1.20, 2)
            base_sum += round(labor.hours * pu, 2)
            lines.append(Command.create({
                'line_category': 'real_labor',
                'name': f"[MO] {labor.name} ({labor.hours}h - {ro.license_plate})",
                'quantity': labor.hours,
                'price_unit': pu,
            }))

        # 3. Pièces opérationnelles non déclarées -> Substitution intelligente
        op_parts = ro.garage_parts_lines.filtered(lambda p: p.source_type == 'operational')
        v_sub = sum(op_parts.mapped('subtotal'))
        if v_sub > 0:
            v_sub = max(0.0, round(self.amount_target_untaxed - base_sum, 2))
            remaining_v_sub = v_sub

            # A. Priorité : Déstocker les pièces du stock fiscal réel en attente de sortie (FIFO)
            if self.enable_smart_stock_clearance:
                available_bl_lines = self.env['garage.parts.bl.line'].search([
                    ('bl_id.state', 'in', ('received', 'invoiced')),
                    ('bl_id.stock_destination', '=', 'official'),
                    ('qty_available_shelf', '>', 0),
                ], order='id asc')

                for bl_l in available_bl_lines:
                    if remaining_v_sub <= 0:
                        break
                    unit_p = bl_l.suggested_sale_price or (bl_l.unit_cost * 1.3)
                    if self.tax_treatment == 'included_tax':
                        unit_p = round(unit_p / 1.20, 2)

                    if unit_p <= 0:
                        continue

                    max_qty = min(bl_l.qty_available_shelf, int(remaining_v_sub / unit_p))
                    if max_qty >= 1.0:
                        line_val = round(max_qty * unit_p, 2)
                        lines.append(Command.create({
                            'bl_line_id': bl_l.id,
                            'line_category': 'sub_official_stock',
                            'name': f"[Stock Fiscal Substitué] {bl_l.name} ({ro.license_plate})",
                            'quantity': max_qty,
                            'price_unit': unit_p,
                        }))
                        remaining_v_sub = round(remaining_v_sub - line_val, 2)

            # B. Solde résiduel -> Panachage forfaitaire Prestation & Consommables
            if remaining_v_sub > 0:
                srv_ratio = self.service_percentage / 100.0
                srv_amount = round(remaining_v_sub * srv_ratio, 2)
                csm_amount = round(remaining_v_sub - srv_amount, 2)  # Solde exact

                if srv_amount > 0:
                    lines.append(Command.create({
                        'line_category': 'sub_service',
                        'name': f"Forfait réfection, réglage et mise au point mécanique atelier ({ro.license_plate})",
                        'quantity': 1.0,
                        'price_unit': srv_amount,
                    }))

                if csm_amount > 0:
                    lines.append(Command.create({
                        'line_category': 'sub_consumable',
                        'name': f"Fournitures, ingrédients d'atelier et consommables homologués ({ro.license_plate})",
                        'quantity': 1.0,
                        'price_unit': csm_amount,
                    }))

        self.line_ids = [Command.clear()] + lines

    def action_create_invoice(self):
        self.ensure_one()
        ro = self.repair_order_id
        if not ro:
            raise UserError(_("Aucun ordre de réparation spécifié."))

        if not self.is_balanced:
            raise UserError(_("Le total des lignes proposées (%.2f MAD) ne correspond pas au total convenu du dossier (%.2f MAD). Écart: %.2f MAD. Veuillez équilibrer avant de valider.",
                              self.amount_proposed_untaxed, self.amount_target_untaxed, self.amount_difference))

        # Taxe TVA 20% Ventes
        sale_tax = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('amount', '=', 20.0),
        ], limit=1)

        tax_ids = [Command.link(sale_tax.id)] if sale_tax else []

        invoice_lines = []
        for line in self.line_ids:
            invoice_lines.append(Command.create({
                'name': line.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'tax_ids': tax_ids,
            }))

        # Création de la facture client
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'invoice_date': self.invoice_date,
            'narration': f"Facture fiscale émise pour le véhicule {ro.license_plate} - Dossier Atelier {ro.name} (BL: {ro.bl_number or 'Direct'})",
            'invoice_line_ids': invoice_lines,
        }

        invoice = self.env['account.move'].create(invoice_vals)

        # Mouvements réels de sortie de stock fiscal et Anti-Double Emploi
        cust_loc = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        if not cust_loc:
            cust_loc = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
        off_loc = self.env.ref('garage_repair_core.location_stock_official', raise_if_not_found=False)

        for line in self.line_ids:
            # 1. Pièce officielle directe de l'OR
            if line.part_id and line.part_id.source_type == 'official':
                if line.part_id.is_officially_cleared:
                    raise UserError(_("La pièce %s a déjà été déclarée sur une facture fiscale. Réutilisation interdite !", line.part_id.name))

                prod = line.part_id.product_id
                if prod and off_loc and cust_loc and not line.part_id.stock_move_id:
                    move = self.env['stock.move'].create({
                        'product_id': prod.id,
                        'product_uom': prod.uom_id.id,
                        'product_uom_qty': line.quantity,
                        'location_id': off_loc.id,
                        'location_dest_id': cust_loc.id,
                        'price_unit': line.price_unit,
                    })
                    move._action_confirm()
                    move._action_assign()
                    move.quantity = line.quantity
                    move.picked = True
                    move._action_done()
                    line.part_id.stock_move_id = move.id

                if line.part_id.parts_bl_line_id:
                    line.part_id.parts_bl_line_id.qty_cleared_officially += line.quantity

                line.part_id.write({
                    'is_officially_cleared': True,
                    'official_invoice_id': invoice.id,
                })

            # 2. Pièce de stock fiscal substituée
            elif line.bl_line_id:
                if line.bl_line_id.qty_available_shelf < line.quantity or line.bl_line_id.qty_remaining_official < line.quantity:
                    raise UserError(_("Le stock fiscal disponible pour %s est insuffisant. Réutilisation interdite !", line.bl_line_id.name))

                prod = line.bl_line_id.product_id
                if prod and off_loc and cust_loc:
                    move = self.env['stock.move'].create({
                        'product_id': prod.id,
                        'product_uom': prod.uom_id.id,
                        'product_uom_qty': line.quantity,
                        'location_id': off_loc.id,
                        'location_dest_id': cust_loc.id,
                        'price_unit': line.price_unit,
                    })
                    move._action_confirm()
                    move._action_assign()
                    move.quantity = line.quantity
                    move.picked = True
                    move._action_done()

                line.bl_line_id.qty_cleared_officially += line.quantity

        # Liaison avec l'Ordre de Réparation
        ro.write({
            'official_invoice_id': invoice.id,
            'billing_channel': 'official_invoice',
        })

        ro.message_post(body=Markup(
            f"<b>Facture Fiscale Officielle Générée avec Dénouement de Stock Réel :</b> "
            f"<a href=# data-oe-model=account.move data-oe-id={invoice.id}>{invoice.name or 'Brouillon'}</a>"
        ))

        return {
            'name': _("Facture Fiscale Déclarée"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }


class GarageBillingWizardLine(models.TransientModel):
    _name = 'garage.billing.wizard.line'
    _description = "Ligne de Substitution Fiscale Suggérée"

    wizard_id = fields.Many2one('garage.billing.wizard', ondelete='cascade', required=True)
    part_id = fields.Many2one('garage.repair.part.line', string="Pièce OR d'origine")
    bl_line_id = fields.Many2one('garage.parts.bl.line', string="Ligne BL Achat Stock Fiscal")

    line_category = fields.Selection([
        ('declared_part', 'Pièce Homologuée (Officielle OR)'),
        ('sub_official_stock', 'Pièce Fiscale Substituée (Sortie Réelle Atelier)'),
        ('real_labor', 'Main-d Œuvre Réelle'),
        ('sub_service', 'Forfait Réfection Technique (Prestation)'),
        ('sub_consumable', 'Fournitures & Consommables Homologués'),
    ], string="Type Fiscal", default='sub_service', required=True)

    name = fields.Char(string="Libellé Facture Fiscale", required=True)
    quantity = fields.Float(string="Qté", default=1.0)
    currency_id = fields.Many2one(related='wizard_id.currency_id')
    price_unit = fields.Monetary(string="Prix Unitaire (HT)", required=True)
    subtotal = fields.Monetary(string="Sous-total HT", compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = round(line.quantity * line.price_unit, 2)
