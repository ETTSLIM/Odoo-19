# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError

class GarageStockPickerWizard(models.TransientModel):
    _name = 'garage.stock.picker.wizard'
    _description = "Assistant de Prélèvement de Pièces en Stock Magasin"

    repair_order_id = fields.Many2one('repair.order', string="Ordre de Réparation lié", required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    stock_filter = fields.Selection([
        ('all', 'Tout le Stock Disponible (Fiscal & Opérationnel)'),
        ('official', 'Stock Fiscal Déclaré Uniquement (Factures ICE)'),
        ('operational', 'Stock Opérationnel Uniquement (BL Atelier)'),
    ], string="Filtre Stock", default='all', required=True)

    line_ids = fields.One2many('garage.stock.picker.wizard.line', 'wizard_id', string="Pièces en Rayon")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        ro_id = res.get('repair_order_id') or ctx.get('default_repair_order_id')
        if not ro_id and ctx.get('active_model') == 'repair.order':
            ro_id = ctx.get('active_id')
            res['repair_order_id'] = ro_id

        # Charger les lignes de stock disponibles
        lines_data = self._get_available_stock_lines(res.get('stock_filter', 'all'))
        res['line_ids'] = lines_data
        return res

    def _get_available_stock_lines(self, filter_type='all'):
        domain = [('bl_id.state', 'in', ('received', 'invoiced'))]
        if filter_type == 'official':
            domain.append(('bl_id.stock_destination', '=', 'official'))
        elif filter_type == 'operational':
            domain.append(('bl_id.stock_destination', '=', 'operational'))

        bl_lines = self.env['garage.parts.bl.line'].search(domain, order='id desc')
        lines = []

        for bl_l in bl_lines:
            available_qty = bl_l.qty_available_shelf
            if available_qty > 0.001:
                suggested_sale = bl_l.suggested_sale_price or round(bl_l.unit_cost * 1.3, 2)
                lines.append(Command.create({
                    'bl_line_id': bl_l.id,
                    'qty_available': available_qty,
                    'qty_to_pick': 0.0,
                    'sale_price': suggested_sale,
                }))
        return lines

    @api.onchange('stock_filter')
    def _onchange_stock_filter(self):
        self.line_ids = [Command.clear()] + self._get_available_stock_lines(self.stock_filter)

    def action_apply_pick(self):
        self.ensure_one()
        ro = self.repair_order_id
        if not ro:
            raise UserError(_("Aucun Ordre de Réparation sélectionné."))

        lines_to_pick = self.line_ids.filtered(lambda l: l.qty_to_pick > 0)
        if not lines_to_pick:
            raise UserError(_("Veuillez saisir au moins une quantité à prélever (Qté > 0)."))

        PartLine = self.env['garage.repair.part.line']
        picked_summary = []

        for line in lines_to_pick:
            if line.qty_to_pick > line.qty_available:
                raise UserError(_(
                    "Quantité demandée (%.2f) supérieure au stock magasin disponible (%.2f) pour l'article '%s'.",
                    line.qty_to_pick, line.qty_available, line.name
                ))

            # Création de la ligne de pièce sur l'Ordre de Réparation
            PartLine.create({
                'repair_id': ro.id,
                'product_id': line.bl_line_id.product_id.id if line.bl_line_id.product_id else False,
                'name': line.name,
                'qty': line.qty_to_pick,
                'cost_price': line.unit_cost,
                'sale_price': line.sale_price,
                'source_type': line.stock_destination,
                'parts_bl_line_id': line.bl_line_id.id,
            })

            dest_label = "Stock Fiscal" if line.stock_destination == 'official' else "Stock Opérationnel"
            picked_summary.append(f"{line.qty_to_pick:.1f}x {line.name} (BL: {line.bl_name}, {dest_label})")

        # Notification dans le fil de discussion de l'OR
        ro.message_post(
            body=_("📦 <b>Prélèvement de Stock Magasin effectué :</b><br/>• %s") % ("<br/>• ".join(picked_summary)),
            message_type='comment',
            subtype_xmlid='mail.mt_note'
        )

        # Auto-synchronisation des pièces disponibles sur la fiche de réception
        if ro.reception_id and ro.reception_id.stock_status != 'pieces_dispo':
            ro.reception_id.action_mark_parts_available()

        return {'type': 'ir.actions.act_window_close'}


class GarageStockPickerWizardLine(models.TransientModel):
    _name = 'garage.stock.picker.wizard.line'
    _description = "Ligne d'Article Magasin à Piocher"

    wizard_id = fields.Many2one('garage.stock.picker.wizard', string="Assistant Parent", ondelete='cascade', required=True)
    bl_line_id = fields.Many2one('garage.parts.bl.line', string="Ligne BL Stock d'Origine", required=True)
    product_id = fields.Many2one(related='bl_line_id.product_id', string="Article Catalogue", readonly=True)
    name = fields.Char(related='bl_line_id.name', string="Désignation Pièce", readonly=True)
    bl_name = fields.Char(related='bl_line_id.bl_id.name', string="N° BL Fournisseur", readonly=True)
    supplier_name = fields.Char(related='bl_line_id.bl_id.supplier_id.name', string="Fournisseur", readonly=True)
    stock_destination = fields.Selection(related='bl_line_id.bl_id.stock_destination', string="Origine Fiscale", readonly=True)
    
    currency_id = fields.Many2one(related='wizard_id.currency_id')
    unit_cost = fields.Monetary(related='bl_line_id.unit_cost', string="Prix d'Achat (Coût)", readonly=True)
    qty_available = fields.Float(string="Disponible Magasin", readonly=True)
    qty_to_pick = fields.Float(string="Qté à Prélever", default=0.0)
    sale_price = fields.Monetary(string="Prix de Vente Unitaire", required=True)
