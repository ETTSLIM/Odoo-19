# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _

class GaragePartsBL(models.Model):
    _name = 'garage.parts.bl'
    _description = "Bon de Réception Pièces Fournisseur (BL Achat)"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_bl desc, id desc'

    name = fields.Char(string="N° BL Fournisseur", required=True, tracking=True,
                       help="Numéro mentionné sur le bon de livraison papier du fournisseur de pièces")
    supplier_id = fields.Many2one('res.partner', string="Fournisseur de Pièces", required=True, tracking=True,
                                  domain="['|', ('is_parts_supplier', '=', True), ('supplier_rank', '>', 0)]")
    supplier_ice = fields.Char(related='supplier_id.ice', string="ICE Fournisseur", readonly=True)
    date_bl = fields.Date(string="Date du BL", default=fields.Date.context_today, required=True)

    # Imputation directe à un véhicule ou Ordre de Réparation
    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule Destinataire", tracking=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string="Immatriculation", store=True)
    repair_order_id = fields.Many2one('repair.order', string="Ordre de Réparation lié", tracking=True)

    # Destination du Stock (Opérationnel vs Fiscal)
    stock_destination = fields.Selection([
        ('operational', 'Stock Opérationnel (Atelier / BL)'),
        ('official', 'Stock Fiscal Déclaré (Facture Fournisseur)'),
    ], string="Destination Stock", default='operational', required=True, tracking=True,
       help="Opérationnel: Pièces achetées sur BL au comptoir. Officiel: Pièces avec facture fournisseur officielle et TVA.")

    # Lignes d'articles achetés
    line_ids = fields.One2many('garage.parts.bl.line', 'bl_id', string="Articles Pièces")

    # Montant total d'achat
    currency_id = fields.Many2one('res.currency', string="Devise",
                                  default=lambda self: self.env.company.currency_id)
    total_amount = fields.Monetary(string="Total Achat BL", compute='_compute_total_amount', store=True, tracking=True)

    # Statut du BL et Rapprochement Facture Officielle
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('received', 'Réceptionné Atelier'),
        ('invoiced', 'Rapproché Facture Officielle'),
        ('cancel', 'Annulé'),
    ], string="Statut", default='draft', tracking=True)

    official_invoice_id = fields.Many2one('account.move', string="Facture Fournisseur Récapitulative", copy=False,
                                          help="Facture officielle du fournisseur regroupant ce BL en fin de mois")

    @api.depends('line_ids.subtotal')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped('subtotal'))

    @api.onchange('repair_order_id')
    def _onchange_repair_order_id(self):
        if self.repair_order_id and self.repair_order_id.vehicle_id:
            self.vehicle_id = self.repair_order_id.vehicle_id

    def _get_or_create_product_for_line(self, line):
        """Assure l'existence d'un article storable Odoo pour permettre les mouvements de stock réels."""
        if line.product_id:
            return line.product_id
        Product = self.env['product.product']
        prod = Product.search([('name', '=', line.name)], limit=1)
        if not prod:
            prod = Product.create({
                'name': line.name,
                'standard_price': line.unit_cost,
                'list_price': line.suggested_sale_price or (line.unit_cost * 1.3),
                'is_storable': True,
            })
        line.product_id = prod.id
        return prod

    def action_receive(self):
        """Valide la réception physique des pièces, génère les mouvements de stock réels Odoo et impute à l'OR."""
        self.write({'state': 'received'})
        
        supp_loc = self.env.ref('stock.stock_location_suppliers', raise_if_not_found=False)
        if not supp_loc:
            supp_loc = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)

        dest_loc_ref = 'garage_repair_core.location_stock_official' if self.stock_destination == 'official' else 'garage_repair_core.location_stock_operational'
        dest_loc = self.env.ref(dest_loc_ref, raise_if_not_found=False)

        for record in self:
            # 1. Générer les mouvements de stock réels vers le bon emplacement (Fiscal ou Opérationnel)
            for line in record.line_ids:
                prod = record._get_or_create_product_for_line(line)
                if dest_loc and supp_loc and prod and not line.stock_move_id:
                    move = self.env['stock.move'].create({
                        'product_id': prod.id,
                        'product_uom': prod.uom_id.id,
                        'product_uom_qty': line.qty,
                        'location_id': supp_loc.id,
                        'location_dest_id': dest_loc.id,
                        'price_unit': line.unit_cost,
                    })
                    move._action_confirm()
                    move._action_assign()
                    move.quantity = line.qty
                    move.picked = True
                    move._action_done()
                    line.stock_move_id = move.id

            # 2. Si un ordre de réparation est lié, synchroniser les pièces vers l'OR
            if record.repair_order_id:
                for line in record.line_ids:
                    self.env['garage.repair.part.line'].create({
                        'repair_id': record.repair_order_id.id,
                        'product_id': line.product_id.id if line.product_id else False,
                        'name': line.name,
                        'qty': line.qty,
                        'cost_price': line.unit_cost,
                        'sale_price': line.suggested_sale_price or (line.unit_cost * 1.3),
                        'source_type': record.stock_destination,
                        'parts_bl_line_id': line.id,
                    })
                # Auto-validation des pièces disponibles sur la fiche de réception
                if record.repair_order_id.reception_id and record.repair_order_id.reception_id.stock_status != 'pieces_dispo':
                    record.repair_order_id.reception_id.action_mark_parts_available()

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_repair_order(self):
        self.ensure_one()
        return {
            'name': _("Ordre de Réparation"),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': self.repair_order_id.id,
            'view_mode': 'form',
        }

    def action_view_vehicle(self):
        self.ensure_one()
        return {
            'name': _("Véhicule"),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle',
            'res_id': self.vehicle_id.id,
            'view_mode': 'form',
        }


class GaragePartsBLLine(models.Model):
    _name = 'garage.parts.bl.line'
    _description = "Ligne de BL Pièces Fournisseur"

    bl_id = fields.Many2one('garage.parts.bl', string="BL Parent", ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string="Article Catalogue")
    name = fields.Char(string="Désignation / Réf OEM", required=True)
    qty = fields.Float(string="Quantité", default=1.0)
    currency_id = fields.Many2one(related='bl_id.currency_id')
    unit_cost = fields.Monetary(string="Prix d'Achat Unitaire (Coût)", required=True)
    suggested_sale_price = fields.Monetary(string="Prix Vente Suggéré")
    subtotal = fields.Monetary(string="Sous-total", compute='_compute_subtotal', store=True)

    # Traçabilité Mouvements & Anti-Double-Usage Fiscale
    stock_move_id = fields.Many2one('stock.move', string="Mouvement Stock Entrant", readonly=True)
    qty_cleared_officially = fields.Float(string="Qté Déclarée Fiscale", default=0.0, readonly=True,
                                          help="Quantité sortie sur facture fiscale officielle (Anti-Double-Emploi)")
    qty_remaining_official = fields.Float(string="Solde Fiscal Disponible", compute='_compute_qty_remaining', store=True,
                                          help="Quantité officielle en attente de sortie légale")
    is_fully_cleared = fields.Boolean(string="Totalement Déclaré", compute='_compute_qty_remaining', store=True)

    # Champs État du Stock Magasin & Rayon
    supplier_id = fields.Many2one(related='bl_id.supplier_id', string="Fournisseur", store=True, readonly=True)
    date_bl = fields.Date(related='bl_id.date_bl', string="Date BL", store=True, readonly=True)
    stock_destination = fields.Selection(related='bl_id.stock_destination', string="Destination Stock", store=True, readonly=True)
    state = fields.Selection(related='bl_id.state', string="Statut BL", store=True, readonly=True)
    repair_part_line_ids = fields.One2many('garage.repair.part.line', 'parts_bl_line_id', string="Allocations Atelier")
    qty_allocated_workshop = fields.Float(string="Qté Allouée Atelier", compute='_compute_shelf_stock_quantities', store=True)
    qty_available_shelf = fields.Float(string="Qté Disponible en Rayon", compute='_compute_shelf_stock_quantities', store=True)

    @api.depends('qty', 'bl_id.state', 'repair_part_line_ids.qty', 'repair_part_line_ids.is_officially_cleared', 'qty_cleared_officially')
    def _compute_shelf_stock_quantities(self):
        for line in self:
            allocated = sum(line.repair_part_line_ids.mapped('qty'))
            uncleared_allocated = sum(
                line.repair_part_line_ids.filtered(lambda p: not p.is_officially_cleared).mapped('qty')
            )
            total_committed = uncleared_allocated + line.qty_cleared_officially
            line.qty_allocated_workshop = max(allocated, total_committed)
            if line.bl_id and line.bl_id.state in ('received', 'invoiced'):
                line.qty_available_shelf = max(0.0, line.qty - total_committed)
            else:
                line.qty_available_shelf = 0.0

    @api.depends('qty', 'qty_cleared_officially')
    def _compute_qty_remaining(self):
        for line in self:
            rem = max(0.0, line.qty - line.qty_cleared_officially)
            line.qty_remaining_official = rem
            line.is_fully_cleared = (rem <= 0.001)

    @api.depends('qty', 'unit_cost')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.qty * line.unit_cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.unit_cost = self.product_id.standard_price
            self.suggested_sale_price = self.product_id.list_price or (round(self.product_id.standard_price * 1.30, 2) if self.product_id.standard_price else 0.0)

    @api.onchange('unit_cost')
    def _onchange_unit_cost(self):
        for line in self:
            if line.unit_cost and not line.suggested_sale_price:
                line.suggested_sale_price = round(line.unit_cost * 1.30, 2)

    def action_open_parent_bl(self):
        self.ensure_one()
        return {
            'name': _("Bon de Réception Pièces Fournisseur"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.parts.bl',
            'res_id': self.bl_id.id,
            'view_mode': 'form',
        }

    def action_open_catalog_product(self):
        self.ensure_one()
        if not self.product_id:
            self.bl_id._get_or_create_product_for_line(self)
        form_view = self.env.ref('garage_repair_core.view_garage_product_template_form', raise_if_not_found=False)
        return {
            'name': _("Fiche Article Catalogue"),
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'res_id': self.product_id.product_tmpl_id.id,
            'view_mode': 'form',
            'views': [(form_view.id, 'form')] if form_view else [(False, 'form')],
        }


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _default_garage_sale_taxes(self):
        tax = self.env.ref('garage_repair_core.tax_tva_20_sale', raise_if_not_found=False)
        if not tax:
            tax = self.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('amount', '=', 20.0)], limit=1)
        return [Command.set(tax.ids)] if tax else False

    def _default_garage_purchase_taxes(self):
        tax = self.env.ref('garage_repair_core.tax_tva_20_purchase', raise_if_not_found=False)
        if not tax:
            tax = self.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('amount', '=', 20.0)], limit=1)
        return [Command.set(tax.ids)] if tax else False

    taxes_id = fields.Many2many(default=_default_garage_sale_taxes)
    supplier_taxes_id = fields.Many2many(default=_default_garage_purchase_taxes)

    oem_reference = fields.Char(string="Réf OEM Constructeur", index=True,
                                help="Référence d'origine constructeur ou équipementier (Bosch, Valeo, Purflux, etc.)")
    vehicle_compatibility = fields.Char(string="Motorisations & Véhicules Compatibles",
                                        help="Ex: Dacia Logan/Sandero 1.5 dCi, Renault Clio 4, Peugeot 208 1.6 HDi...")
    shelf_location_note = fields.Char(string="Emplacement Rayon / Casier",
                                      help="Ex: Rayon A - Étagère 2 - Casier Filtres")

    qty_stock_operational = fields.Float(string="Stock Rayon Atelier (BL)",
                                         compute='_compute_garage_double_stock', store=False)
    qty_stock_official = fields.Float(string="Stock Fiscal Déclaré",
                                      compute='_compute_garage_double_stock', store=False)

    margin_amount = fields.Monetary(string="Marge Unitaire HT", compute='_compute_garage_margin', currency_field='currency_id')
    margin_rate = fields.Float(string="Taux de Marge (%)", compute='_compute_garage_margin')

    garage_bl_line_ids = fields.Many2many('garage.parts.bl.line', string="Historique Achats BL",
                                          compute='_compute_garage_traceability')
    bl_line_count = fields.Integer(string="Achats BL", compute='_compute_garage_traceability')

    garage_repair_part_ids = fields.Many2many('garage.repair.part.line', string="Consommations Atelier",
                                              compute='_compute_garage_traceability')
    repair_part_count = fields.Integer(string="Sorties OR", compute='_compute_garage_traceability')

    @api.depends('list_price', 'standard_price')
    def _compute_garage_margin(self):
        for tmpl in self:
            margin = (tmpl.list_price or 0.0) - (tmpl.standard_price or 0.0)
            tmpl.margin_amount = margin
            tmpl.margin_rate = (margin / tmpl.list_price * 100.0) if tmpl.list_price and tmpl.list_price > 0 else 0.0

    @api.onchange('standard_price')
    def _onchange_garage_standard_price(self):
        if self.standard_price and not self.list_price:
            self.list_price = round(self.standard_price * 1.35, 2)

    def _compute_garage_traceability(self):
        BLLine = self.env['garage.parts.bl.line']
        PartLine = self.env['garage.repair.part.line']
        for tmpl in self:
            prod_ids = tmpl.product_variant_ids.ids
            if prod_ids:
                bl_lines = BLLine.search([('product_id', 'in', prod_ids)], order='id desc')
                ro_lines = PartLine.search([('product_id', 'in', prod_ids)], order='id desc')
                tmpl.garage_bl_line_ids = bl_lines
                tmpl.bl_line_count = len(bl_lines)
                tmpl.garage_repair_part_ids = ro_lines
                tmpl.repair_part_count = len(ro_lines)
            else:
                tmpl.garage_bl_line_ids = BLLine
                tmpl.bl_line_count = 0
                tmpl.garage_repair_part_ids = PartLine
                tmpl.repair_part_count = 0

    def action_create_restock_bl(self):
        """Ouvre un nouveau Bon de Réception Fournisseur pré-rempli avec cet article."""
        self.ensure_one()
        variant = self.product_variant_id
        return {
            'name': _("Nouvel Approvisionnement BL - %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.parts.bl',
            'view_mode': 'form',
            'context': {
                'default_line_ids': [Command.create({
                    'product_id': variant.id,
                    'name': self.name,
                    'qty': 1.0,
                    'unit_cost': self.standard_price or 0.0,
                    'suggested_sale_price': self.list_price or round((self.standard_price or 0.0) * 1.35, 2),
                })],
            },
        }

    def action_view_bl_lines(self):
        self.ensure_one()
        return {
            'name': _("Entrées BL - %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.parts.bl.line',
            'view_mode': 'list,form',
            'domain': [('product_id', 'in', self.product_variant_ids.ids)],
        }

    def action_view_repair_usages(self):
        self.ensure_one()
        ro_ids = self.garage_repair_part_ids.mapped('repair_id').ids
        return {
            'name': _("Ordres de Réparation utilisant %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', ro_ids)],
        }

    def _compute_garage_double_stock(self):
        loc_op = self.env.ref('garage_repair_core.location_stock_operational', raise_if_not_found=False)
        loc_of = self.env.ref('garage_repair_core.location_stock_official', raise_if_not_found=False)
        for tmpl in self:
            op_qty = 0.0
            of_qty = 0.0
            prod_ids = tmpl.product_variant_ids.ids
            if prod_ids:
                if loc_op:
                    quants_op = self.env['stock.quant'].search([
                        ('product_id', 'in', prod_ids),
                        ('location_id', 'child_of', loc_op.id)
                    ])
                    op_qty = sum(quants_op.mapped('quantity'))
                if loc_of:
                    quants_of = self.env['stock.quant'].search([
                        ('product_id', 'in', prod_ids),
                        ('location_id', 'child_of', loc_of.id)
                    ])
                    of_qty = sum(quants_of.mapped('quantity'))

                if not op_qty and not of_qty:
                    lines = self.env['garage.parts.bl.line'].search([
                        ('product_id', 'in', prod_ids),
                        ('bl_id.state', 'in', ('received', 'invoiced'))
                    ])
                    op_qty = sum(lines.filtered(lambda l: l.stock_destination == 'operational').mapped('qty_available_shelf'))
                    of_qty = sum(lines.filtered(lambda l: l.stock_destination == 'official').mapped('qty_available_shelf'))

            tmpl.qty_stock_operational = op_qty
            tmpl.qty_stock_official = of_qty


class ProductProduct(models.Model):
    _inherit = 'product.product'

    oem_reference = fields.Char(related='product_tmpl_id.oem_reference', string="Réf OEM Constructeur",
                                store=True, readonly=False)
    qty_stock_operational = fields.Float(string="Stock Rayon Atelier (BL)",
                                        compute='_compute_product_double_stock', store=False)
    qty_stock_official = fields.Float(string="Stock Fiscal Déclaré",
                                     compute='_compute_product_double_stock', store=False)

    def _compute_product_double_stock(self):
        loc_op = self.env.ref('garage_repair_core.location_stock_operational', raise_if_not_found=False)
        loc_of = self.env.ref('garage_repair_core.location_stock_official', raise_if_not_found=False)
        for prod in self:
            op_qty = 0.0
            of_qty = 0.0
            if loc_op:
                quants_op = self.env['stock.quant'].search([
                    ('product_id', '=', prod.id),
                    ('location_id', 'child_of', loc_op.id)
                ])
                op_qty = sum(quants_op.mapped('quantity'))
            if loc_of:
                quants_of = self.env['stock.quant'].search([
                    ('product_id', '=', prod.id),
                    ('location_id', 'child_of', loc_of.id)
                ])
                of_qty = sum(quants_of.mapped('quantity'))

            if not op_qty and not of_qty:
                lines = self.env['garage.parts.bl.line'].search([
                    ('product_id', '=', prod.id),
                    ('bl_id.state', 'in', ('received', 'invoiced'))
                ])
                op_qty = sum(lines.filtered(lambda l: l.stock_destination == 'operational').mapped('qty_available_shelf'))
                of_qty = sum(lines.filtered(lambda l: l.stock_destination == 'official').mapped('qty_available_shelf'))

            prod.qty_stock_operational = op_qty
            prod.qty_stock_official = of_qty
